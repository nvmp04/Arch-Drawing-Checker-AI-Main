# JSON bộ tiêu chí (do BE sinh từ Excel)

Mẫu: `samples/criteria/ruleset-4sao.json` (response của BE `POST rules/import`, file Excel CHTK, sheet "4 SAO").

## 1. Cấu trúc

```jsonc
{ "data": [                                   // mỗi sheet Excel = một bộ rules
  { "id": "uuid", "name": "… — 4 SAO", "fileName": "…xlsx", "sheetName": "4 SAO",
    "ruleCount": 92, "uploadedAt": "ISO", "warnings": [ { "sourceRow", "code", "message" } ],
    "sections": [                             // 5 nhóm CHTK
      { "code": "1", "category": "facade", "title": "MẶT NGOÀI CÔNG TRÌNH",
        "rules": [
          { "id": "uuid", "ruleSetId": "uuid",
            "code": "1.4.1" | null,           // null = dòng biến thể (thường theo loại nhà)
            "parentCode": "1.4",
            "headings": ["Hệ cửa, kính & phụ kiện"],   // tiêu đề các nhóm cha — ngữ cảnh
            "title": "Cửa đi mở",
            "category": "facade",
            "checkType": null,                 // luôn null (D-08)
            "operator": "gte"|"lte"|"between"|"in-list"|null,
            "value": "1.1m" | null,            // chuỗi thô, có đơn vị
            "requirement": "- …\n- …",
            "requirementLines": ["…", "…"],   // ĐƠN VỊ KIỂM TRA của MAIN (D-09)
            "houseTypes": ["shophouse", …],
            "isActive": true, "sourceRow": 4 } ] } ] } ] }
```

## 2. Số liệu bộ "4 SAO"

- 92 rule · nhóm: facade 18, dimension 13, stair-ramp 9, structure 42, finishing 10.
- `operator`: null 62 · `gte` 26 · `lte` 2 · `between` 1 · `in-list` 1.
- `houseTypes`: 80 rule áp dụng cả 5 loại; còn lại là biến thể theo loại nhà (1.8, 1.9, 2.1.1, 2.1.2, 3.1…).
- `warnings`: "Villa" đứng riêng → hiểu là Single Villa; "Shop Semi Villa" không thuộc 5 loại → bỏ; mã sai thứ tự (4.4.2 sau 4.4.3); mã trùng (5.3.3).

## 3. Nhận xét quan trọng cho MAIN

1. **Rule có `operator`** (30) là ngưỡng số trực tiếp: chiều cao lan can ≥1.1m, cổng 1.2–2.6m, cote tầng 1, chiều cao tầng, chiều rộng lọt lòng phòng (2.2.x), thang (rộng/cao bậc, số bậc ∈ {17,18,21,22,25}), độ dốc hầm ≤18%, nhà xe ≥ 2.8×5.6m.
2. **Rule `operator = null` (62) vẫn chứa số bên trong `requirementLines`**: danh mục kích thước cửa (1.4.1–1.4.5, dạng "Cao x Rộng: 2800 x 1100mm"), "Chênh cao ngạch cửa Min 20 mm", "i ≥ 1.5%", "Vữa mác 75, trát dày 15 mm"… → phải tách từng dòng.
3. **Một rule lẫn nhiều loại kiểm tra** (vd. 5.3.1: số đo + hình học có điều kiện "ban công ≥6m²" + chủ quan "mất thẩm mỹ").
4. `value` là chuỗi có đơn vị lẫn lộn (`m`, `mm`, `%`, `a x b`, `a - b`, danh sách) — Q-03.
5. `code` không duy nhất và có thể null → định danh bằng `id` (Q-04).
6. Có dòng không kiểm được từ bản vẽ (4.4.x chống mối định kỳ, vận hành CĐT) → trả `unknown`/bỏ qua có lý do.
