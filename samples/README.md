# Dữ liệu mẫu

| File | Nguồn |
|---|---|
| `criteria/ruleset-4sao.json` | Response BE `POST rules/import` với `TIEU CHI CHTK NHA O THAP TANG_gui CDS.xlsx` (bản sao `D:\Downloads\response_1790518856429.json`) |
| `ground-truth/pn2-dn-reviewer-comments.json` | Comment người kiểm tra, trích tự động bằng so chữ giữa hai PDF. `boundingBox` theo % trang, gốc trên-trái. **Cần làm sạch thủ công** trước khi dùng cho benchmark |

PDF không commit (nặng ~20MB, tài liệu nội bộ). Đường dẫn trên máy dev:

- `D:\Downloads\tieuchuan\PN2.DN-Ban ve mau demo test AI.pdf` — bản gốc
- `D:\Downloads\tieuchuan\PN2.DN-Ban ve mau demo test AI - comment check.pdf` — bản có comment
- `D:\Downloads\tieuchuan\TIEU CHI CHTK NHA O THAP TANG_gui CDS.xlsx` — tiêu chí gốc
