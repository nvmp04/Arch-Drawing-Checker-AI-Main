# Eval AI bằng agent đóng vai model

**Dành cho model AI đọc file này.** Người dùng đưa một file PDF bản vẽ → bạn chạy eval ngay theo 5 bước dưới đây, rồi báo cáo kết quả.

Quy tắc:
- **Không sửa file code nào.** Chỉ chạy các script có sẵn trong `scripts/`.
- **Không gọi API AI trả phí.** Phần "model" do một agent con sạch đóng vai.
- **Bạn không tự chấm.** Bạn đã đọc tài liệu dự án nên không còn "sạch" → việc chấm giao cho agent con (bước 2).
- Chạy mọi lệnh tại thư mục gốc của repo.

Thiếu đường dẫn PDF thì hỏi người dùng. Đặt thư mục lượt `RUN = data/ai-agent/run-<YYYYMMDD-HHMM>` (thư mục mới, không dùng lại `run1`, `run2`).

## Bước 1 — Xuất đầu vào

```bash
python scripts/export_agent_inputs.py "<PDF>" <RUN>
```

Kết quả: `<RUN>/system.txt`, `schema.json`, `digest.txt`, `requests.jsonl` (mỗi dòng một rule: `key` + `prompt`), `meta.json`. In ra mã hồ sơ và số rule — ghi lại.

## Bước 2 — Giao cho agent con sạch

Tạo **một agent con mới, không truyền ngữ cảnh**: không cho nó đọc `AGENTS.md`, `docs/`, `data/reviews/` hay bất cứ gì ngoài `<RUN>`. Giao nguyên văn (thay `<RUN>`):

```text
Bạn đóng vai model chấm bản vẽ kiến trúc. Chỉ đọc 4 file trong <RUN>:
- system.txt: vai trò + quy tắc, tuân theo tuyệt đối.
- schema.json: định dạng câu trả lời.
- digest.txt: chữ trên bản vẽ — nguồn bằng chứng DUY NHẤT.
- requests.jsonl: mỗi dòng có "key" và "prompt".

Với TỪNG dòng của requests.jsonl: đọc prompt, trả lời đúng schema.json (object có mảng "lines", đủ mọi
line_index được hỏi; evidence_ids là mã khối có thật trong digest.txt, ví dụ "p9-28"), ghi vào
<RUN>/answers/<key>.json.

Làm đủ mọi dòng, không bỏ, không gộp. Không đọc file nào ngoài <RUN>. Không dùng hiểu biết bên ngoài
digest.txt để khẳng định trên bản vẽ có / không có thứ gì. Xong thì báo số file đã ghi.
```

Agent con dừng giữa chừng → so `key` trong `requests.jsonl` với tên file trong `<RUN>/answers/`, giao tiếp các key còn thiếu (cùng lời giao việc trên, thêm danh sách key).

Không tạo được agent con → dừng, bảo người dùng mở **một phiên chat mới hoàn toàn**, chỉ cho phiên đó thấy `<RUN>`, dán lời giao việc trên; xong thì quay lại bước 3.

## Bước 3 — Nhập câu trả lời

```bash
python scripts/import_agent_answers.py <RUN>
```

Phải in `Thiếu: không. Lỗi JSON: không.` Nếu có rule thiếu hoặc lỗi JSON → quay lại bước 2 chỉ cho các rule đó, rồi chạy lại bước 3.

## Bước 4 — Chấm

```bash
python scripts/run_ai_eval.py "<PDF>" --replay --calls-dir data/ai-agent/calls --max-rules 0
```

- Không thêm `--no-table-grid` (chỉ dùng khi phát lại lượt cũ `run1`, `run2`).
- Script tự so với kết quả kỹ sư đã duyệt ở `data/reviews/<mã hồ sơ>.jsonl` nếu có. Không có file đó → chỉ có kết luận của AI, không có độ chính xác (ghi rõ điều này trong báo cáo).
- Xem kết quả trên viewer: `python -m uvicorn drawing_checker.app:app --port 8000` → `http://localhost:8000/debug/inspect/` (lượt mới tên `eval-<thời gian>-...`).

## Bước 5 — Báo cáo cho người dùng

- Mã hồ sơ, số rule / số dòng tiêu chí đã chấm.
- Độ chính xác trên các dòng kỹ sư đã duyệt, số lỗi nghiêm trọng (Đạt ↔ Không đạt), số dòng sai vị trí — hoặc "chưa có kết quả duyệt".
- Thư mục kết quả trong `data/ai/eval/` và tên lượt trên viewer.
- Số token agent con đã dùng (tham khảo: ~260–275k cho 92 rule PN2).

So với một lượt trước (tùy chọn):

```bash
python scripts/compare_ai_runs.py data/ai/eval/<lần A>/run-1.json data/ai/eval/<lần B>/run-1.json
```
