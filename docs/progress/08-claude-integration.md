# 08 · Nối Claude API vào lõi (2026-10-09)

Quyết định: D-22. Người dùng: hạn mức **5 USD/tháng**, "đưa AI thật vào". AI không tự gọi API — mọi lần gọi thật do người dùng chạy.

## Đã làm (MAIN)

| File | Nội dung |
|---|---|
| `features/semantic/digest.py` | Bản tóm tắt chữ của hồ sơ gửi AI: mã khối `p<trang>-<i>`, khung tên, tiêu đề hình/bảng, bảng viết tắt, đặc điểm hồ sơ, mã layer (gợi ý). Lược khối chỉ có số. Chia vùng kiểu XY-cut (khe cột 8×, khe dải 4× cỡ chữ trung vị — đo trên PN2 trang 5). Cùng đầu vào → cùng chuỗi. |
| `features/semantic/provider.py` | Giao diện chung `LlmProvider`: `ClaudeProvider` (structured outputs, cache bản tóm tắt, `fallbacks: "default"` cho Opus/Sonnet), `ReplayProvider`, `FakeProvider`; `CallStore` ghi mỗi lần gọi thật. |
| `features/semantic/budget.py` | Bảng giá, tính USD theo token thật, sổ chi tiêu tháng + chặn khi vượt hạn mức. |
| `features/semantic/service.py` | Prompt hệ thống (cổng áp dụng, M1–M7, 4 trạng thái, quy tắc trích dẫn), lược đồ JSON, hậu kiểm → `LineResult` + bằng chứng polygon. |
| `features/semantic/factory.py`, `config.py` | `MAIN_AI_PROVIDER=off|claude|replay` (mặc định off), model, effort, hạn mức, API key. |
| `features/analyses/service.py` | AI kiểm các dòng rule engine "chưa hỗ trợ"; chi phí + lỗi ghi vào tab "Kiểm tra" của viewer. |
| `scripts/run_ai_eval.py` | Chạy khô (ước tính, xem bản tóm tắt), tạo CSV đáp án, `--live` (hỏi xác nhận), `--replay`, `--repeat K` (độ ổn định), `--truth` (độ chính xác, lỗi Đạt↔Không đạt, trúng trang). |
| `tests/test_semantic_ai.py` | 16 test, chỉ model giả / client giả. Tổng 86 test đạt. |

## Số đo được (không tốn tiền)

- Bản tóm tắt PN2: 121.871 ký tự ≈ 61k token (ước lượng 2 ký tự/token), 4.013 khối gửi, 4.514 khối số lược, 52 layer có chữ.
- Bộ rule mẫu: 92 rule / 230 dòng. Ước tính một lần chạy cả bộ (giả định 2.500 token ra / lần gọi): Opus 5.5 ~6,7 USD · Sonnet 5.5 ~3,9 · Haiku 5.5 ~0,2. Nhóm 5.x (10 rule / 50 dòng): Opus ~1,0 · Sonnet ~0,55 · Haiku ~0,03.

## Giới hạn đã biết

- Chỉ chữ: chưa có lưới bảng / đường dẫn ghi chú từ nét vẽ → trong bảng, chữ của một ô nhiều dòng có thể xen với ô bên cạnh. Lần đo đầu là **mốc so sánh**; phần hình học (drawing-knowledge.md) sẽ được đo lại so với mốc này.
- Không có bằng chứng polygon cho dòng "Cần kiểm tra" chỉ có trang nên xem (ghi trong lý do).
- Kết quả AI chưa gửi BE (findings v1 chưa làm).
- Chưa đo token thật — số trên là ước lượng; sổ chi tiêu sẽ cho số thật sau lần chạy đầu.

## Người dùng cần làm để chạy lần đầu

1. Đối tác đồng ý gửi chữ trên bản vẽ ra Anthropic API.
2. Anthropic Console: tạo API key, **đặt giới hạn chi tiêu 5 USD/tháng**.
3. `.env` của MAIN: `MAIN_ANTHROPIC_API_KEY=...` (giữ `MAIN_AI_PROVIDER=off` khi chỉ chạy script).
4. Tạo + điền đáp án: `python scripts/run_ai_eval.py "<PN2.pdf>" --codes 5 --make-truth samples/ground-truth/pn2-truth.csv`.
5. Chạy: `python scripts/run_ai_eval.py "<PN2.pdf>" --codes 5 --live --truth samples/ground-truth/pn2-truth.csv`.

## 2026-10-09 (chiều) — chạy cả PN2 bằng agent Claude Code + duyệt trên viewer

- Gọi API thật: key xác thực được nhưng tài khoản Console **chưa có credit** (gói Claude Code không dùng chung với API) → chưa tốn tiền.
- Thay thế miễn phí: một agent Claude Code **sạch** (không lịch sử hội thoại, chỉ đọc system + bản tóm tắt + 92 prompt — đúng đầu vào của API) đóng vai Opus 5.5, ghi `data/ai-agent/run1/answers/`. `scripts/import_agent_answers.py` → kho phát lại riêng `data/ai-agent/calls` (`source: claude-code-agent`). Khác API: không có structured outputs ép lược đồ, một agent làm tuần tự cả 92 rule.
- Kết quả thô 230 dòng: not_applicable 89 · needs_review 69 · pass 45 · warning 14 · fail 13. Sau hậu kiểm: **cả 13 "fail" thành Cảnh báo** vì model tự cho tin cậy 0.5–0.75 < 0.8 — nhiều ca trùng comment người kiểm tra (trần cemboard ≠ thạch cao chống ẩm 9 mm; kính lan can 10 mm ≠ 10.76 mm; lưới thép D6@200 ≠ D4@250-300). Cần xem lại cách model tự chấm tin cậy sau khi có kết quả duyệt.
- Duyệt: tab "Kiểm tra" của viewer có Đúng / Sai vị trí / Sai → kết luận đúng / ghi chú / chấm mù; API `GET|POST /debug/reviews/<mã hồ sơ>` (chỉ khi `MAIN_INSPECT_ENABLED`), lưu `data/reviews/<mã hồ sơ>.jsonl` (chỉ thêm). `run_ai_eval.py` tự chấm mọi lần chạy theo file này (bỏ CSV đáp án).

## 2026-10-19 — prompt v2 (đầu ra rút gọn) + lượt agent thứ 2

- Lượt 1 tốn ~273k token agent. Ước lượng phân rã: đọc bản tóm tắt ~70–90k (chữ IN HOA có dấu tách token kém), mã khối + layer ~15–20k, **đầu ra 230 dòng ~80–100k** (đắt nhất khi trả tiền API: token ra = 5× token vào). Người dùng chọn giảm phần đầu ra trước (mục 1); nén bản tóm tắt + gửi theo trang liên quan để sau; `count_tokens` (miễn phí) chỉ gọi khi người dùng cho phép.
- `PROMPT_VERSION = judge-rule/v2`: giới hạn độ dài từng trường (scope/requirement/found ≤ 12 từ, reason ≤ 40 từ, dòng not_applicable chỉ ghi applicability_reason), tối đa 5 mã khối bằng chứng. Đổi prompt → khóa bản ghi mới, lượt 1 không bị đè.
- Script mới: `scripts/export_agent_inputs.py` (xuất đầu vào cho agent), `scripts/compare_ai_runs.py` (so hai lần chạy: % cùng kết luận, lật Đạt↔Không đạt, độ dài đầu ra).
- Lượt 2: agent sạch, cùng bản tóm tắt, prompt v2 → `data/ai-agent/run2`, viewer `eval-20261019-005535-claude-opus-5-5`, kết quả `data/ai/eval/20261019-005535/`.
  - **Token agent: 261k** (lượt 1: 273k, −4%) — phần đọc bản tóm tắt chiếm đa số nên rút gọn đầu ra ít tác động tổng.
  - **Đầu ra: 105.266 ký tự JSON** (lượt 1: 134.644, −22%; gồm cả tên trường lặp lại — phần chữ thật giảm nhiều hơn). Khi trả tiền API, token ra là phần đắt nhất → tiết kiệm thật ~20%.
  - **Nhất quán giữa hai lượt: 215/230 dòng cùng kết luận (93%), 0 lật Đạt↔Không đạt.** 15 dòng đổi, phần lớn giữa Cần kiểm tra ↔ Đạt / Cảnh báo / Không áp dụng. Lưu ý: hai lượt khác prompt nên đây chưa phải đo độ ổn định thuần.
  - Thô lượt 2: not_applicable 90 · needs_review 68 · pass 43 · warning 22 · fail 7 → sau hậu kiểm chỉ **1 Không đạt** còn lại (6 ca tin cậy < 0.8 bị hạ Cảnh báo) — cùng vấn đề tin cậy thấp như lượt 1.

## Việc đang dở (cho phiên sau)

1. Người dùng duyệt kết quả trên viewer (cần bật MAIN: `python -m uvicorn drawing_checker.app:app --port 8000`). Có kết quả duyệt → chạy `run_ai_eval.py --replay --calls-dir data/ai-agent/calls --max-rules 0 --no-viewer --no-table-grid` để có độ chính xác thật (**từ 2026-10-19 phải có `--no-table-grid`**: lượt 1–2 dùng bản tóm tắt chỉ chữ, kho phát lại khóa theo nội dung).
2. Model tự cho tin cậy thấp (0.5–0.75) cho các ca Không đạt đúng → bị hạ thành Cảnh báo. Xem lại hướng dẫn chấm tin cậy trong prompt **sau khi** có số liệu duyệt.
3. Nạp credit Console khi cần gọi API thật (luồng web cho đối tác); lần gọi thật đầu tiên cho số token chính xác → sửa ước tính `estimate_tokens` (2 ký tự/token có thể thấp).
4. Hình học (`geometry`): ✅ lưới bảng (2026-10-19, `progress/10-table-grid.md`) · ☐ đường dẫn ghi chú. ☐ Đo lại so với mốc chỉ-chữ: lượt agent 3 với bản có lưới (`export_agent_inputs.py` mặc định có lưới) → `compare_ai_runs.py` với lượt 2 + chấm theo kết quả duyệt.
5. ✅ findings v1 (2026-10-19, D-23, `progress/09-findings-v1.md`).
