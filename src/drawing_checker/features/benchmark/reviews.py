"""Người duyệt chấm kết quả từng dòng tiêu chí trên viewer debug → đáp án dùng lại cho mọi lần chạy sau.

Lưu `data/reviews/<mã hồ sơ>.jsonl` (MAIN_REVIEWS_DIR) (mã hồ sơ = 16 ký tự đầu SHA-256 của PDF), chỉ THÊM, không ghi đè: bấm
lại thì dòng mới thắng. Lưu **đáp án đúng** (không chỉ đúng/sai) để lần chạy sau — đổi prompt, đổi model, đo K lần —
chấm tự động được (D-20: cùng loại thao tác duyệt sẽ có trên web cho đối tác).
"""

import json
import re
import threading
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field

DOSSIER_ID = re.compile(r"^[0-9a-f]{16}$")


class Outcome(str, Enum):
    """Kết luận của một dòng theo 4 trạng thái của đối tác + "không áp dụng"."""

    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"
    PENDING = "pending"  # Cần kiểm tra
    NOT_APPLICABLE = "n/a"
    UNKNOWN = "unknown"  # hệ thống không ra kết luận (lỗi, chưa hỗ trợ)


class Verdict(str, Enum):
    CORRECT = "correct"  # kết luận + bằng chứng đúng
    WRONG = "wrong"  # kết luận sai → expected là kết luận đúng
    WRONG_LOCATION = "wrong-location"  # kết luận đúng, bằng chứng chỉ sai chỗ


class ReviewInput(BaseModel):
    rule_id: str = Field(alias="ruleId")
    code: str | None = None
    line_index: int = Field(ge=0, alias="lineIndex")
    line_text: str | None = Field(default=None, alias="lineText")
    verdict: Verdict
    predicted: Outcome  # kết luận hệ thống hiển thị lúc duyệt
    expected: Outcome  # đáp án đúng theo người duyệt
    note: str | None = Field(default=None, max_length=2000)
    run_id: str | None = Field(default=None, alias="runId")  # thư mục viewer
    model: str | None = None
    prompt_version: str | None = Field(default=None, alias="promptVersion")
    call_id: str | None = Field(default=None, alias="callId")
    blind: bool = False  # chấm khi đang ẩn kết luận của AI
    # Người chấm — MAIN ghi theo tên đăng nhập (chế độ chấm cho đối tác), không lấy từ trình duyệt.
    reviewer: str | None = Field(default=None, max_length=60)

    model_config = {"populate_by_name": True}


class ReviewStore:
    def __init__(self, directory: Path) -> None:
        self._dir = directory
        self._lock = threading.Lock()

    def path(self, dossier: str) -> Path:
        if not DOSSIER_ID.match(dossier):
            raise ValueError("Mã hồ sơ không hợp lệ")
        return self._dir / f"{dossier}.jsonl"

    def append(self, dossier: str, review: ReviewInput) -> dict:
        row = {"at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
               **review.model_dump(by_alias=True, mode="json")}
        with self._lock:
            p = self.path(dossier)
            p.parent.mkdir(parents=True, exist_ok=True)
            with p.open("a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        return row

    def latest(self, dossier: str) -> dict[tuple[str, int], dict]:
        """(ruleId, lineIndex) → lần duyệt cuối."""
        p = self.path(dossier)
        out: dict[tuple[str, int], dict] = {}
        if p.exists():
            for line in p.read_text(encoding="utf-8").splitlines():
                try:
                    row = json.loads(line)
                    out[(row["ruleId"], int(row["lineIndex"]))] = row
                except (json.JSONDecodeError, KeyError, ValueError):
                    continue
        return out


class PgReviewStore:
    """Cùng giao diện ReviewStore, lưu vào Postgres (Neon) — dùng trên Render, nơi ổ đĩa bị xóa khi dịch vụ ngủ (D-24).

    Một bảng chỉ thêm `ai_reviews(id, dossier, data)`; `data` = đúng một dòng của file jsonl.
    """

    _ddl = ("CREATE TABLE IF NOT EXISTS ai_reviews (id bigserial PRIMARY KEY, dossier text NOT NULL, "
            "data jsonb NOT NULL)")

    def __init__(self, url: str) -> None:
        self._url = url
        self._ready = False

    def _connect(self):
        import psycopg  # chỉ cần khi bật lưu Postgres

        conn = psycopg.connect(self._url, autocommit=True)
        if not self._ready:
            conn.execute(self._ddl)
            self._ready = True
        return conn

    def append(self, dossier: str, review: ReviewInput) -> dict:
        if not DOSSIER_ID.match(dossier):
            raise ValueError("Mã hồ sơ không hợp lệ")
        row = {"at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
               **review.model_dump(by_alias=True, mode="json")}
        with self._connect() as conn:
            conn.execute("INSERT INTO ai_reviews (dossier, data) VALUES (%s, %s::jsonb)",
                         (dossier, json.dumps(row, ensure_ascii=False)))
        return row

    def rows(self, dossier: str | None = None) -> list[tuple[str, dict]]:
        """Mọi dòng theo thứ tự ghi: (mã hồ sơ, dòng) — để xuất ra jsonl."""
        sql = "SELECT dossier, data FROM ai_reviews" + (" WHERE dossier = %s" if dossier else "") + " ORDER BY id"
        with self._connect() as conn:
            return [(d, data) for d, data in conn.execute(sql, (dossier,) if dossier else ())]

    def latest(self, dossier: str) -> dict[tuple[str, int], dict]:
        if not DOSSIER_ID.match(dossier):
            raise ValueError("Mã hồ sơ không hợp lệ")
        out: dict[tuple[str, int], dict] = {}
        for _, row in self.rows(dossier):
            out[(row["ruleId"], int(row["lineIndex"]))] = row
        return out


def score(predicted: dict[tuple[str, int], str], reviews: dict[tuple[str, int], dict],
          evidence_pages: dict[tuple[str, int], set[int]] | None = None) -> dict:
    """So kết luận của một lần chạy với đáp án đã duyệt. predicted: (ruleId, line) → Outcome.value."""
    rows = []
    for key, review in reviews.items():
        if key not in predicted:
            continue
        got, want = predicted[key], review["expected"]
        rows.append({"ruleId": key[0], "code": review.get("code"), "line": key[1], "expected": want, "got": got,
                     "locationWrong": review.get("verdict") == Verdict.WRONG_LOCATION.value and got == want})
    total = len(rows)
    correct = sum(1 for r in rows if r["expected"] == r["got"])
    confusion: dict[str, int] = {}
    for r in rows:
        k = f"{r['expected']}→{r['got']}"
        confusion[k] = confusion.get(k, 0) + 1
    return {
        "reviewed": total,
        "correct": correct,
        "accuracy": round(correct / total, 3) if total else None,
        "severeErrors": sum(1 for r in rows if {r["expected"], r["got"]} == {"pass", "fail"}),
        "locationWrong": sum(1 for r in rows if r["locationWrong"]),
        "confusion": dict(sorted(confusion.items())),
        "rows": rows,
    }
