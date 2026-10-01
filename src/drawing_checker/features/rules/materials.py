"""Từ điển vật liệu — dùng CHUNG cho câu tiêu chí và chữ trên bản vẽ (D-17).

Cùng một từ điển nhận ra vật liệu ở cả hai phía, nên danh sách vật liệu được phép suy ra từ chính câu tiêu chí
(vd. 5.1.1 "Tấm trần Silicat… Hoặc Tấm trần thạch cao…" → {silicate, gypsum}), không viết cứng trong checker.
Thứ tự có nghĩa: mẫu cụ thể đứng trước mẫu chung ("gỗ nhựa" trước "gỗ").
Danh sách tay, rút từ bộ PN2 + bộ tiêu chí 4 sao; mở rộng khi gặp bản vẽ mới. Sau này: embedding cho cách viết lạ.
"""

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Material:
    key: str
    label: str  # tên hiển thị tiếng Việt
    pattern: re.Pattern


MATERIALS: list[Material] = [
    Material("cemboard", "tấm cemboard (xi măng sợi)", re.compile(r"CEMBOARD|CEMENT\s*BOARD|XI MĂNG SỢI")),
    Material("silicate", "tấm silicat", re.compile(r"SILICA")),
    Material("gypsum", "thạch cao", re.compile(r"THẠCH CAO")),
    Material("wpc", "gỗ nhựa", re.compile(r"GỖ NHỰA|\bWPC\b")),
    Material("aluminium", "nhôm", re.compile(r"\bNHÔM\b")),
    Material("concrete", "bê tông", re.compile(r"BÊ TÔNG|\bBTCT\b")),
    Material("wood", "gỗ", re.compile(r"\bGỖ\b")),
    Material("raw", "để thô (không hoàn thiện)", re.compile(r"ĐỂ THÔ")),
]
BY_KEY = {m.key: m for m in MATERIALS}


def find_materials(text: str) -> list[str]:
    """Mọi vật liệu nhắc tới trong câu, theo thứ tự từ điển."""
    upper = text.upper()
    return [m.key for m in MATERIALS if m.pattern.search(upper)]


def main_material(text: str) -> str | None:
    """Vật liệu chính của một mô tả trên bản vẽ (mẫu cụ thể nhất khớp đầu tiên)."""
    found = find_materials(text)
    return found[0] if found else None


def label(key: str) -> str:
    return BY_KEY[key].label
