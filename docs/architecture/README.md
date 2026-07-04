# docs/architecture/ — Tài liệu kiến trúc

Folder chứa **mọi tài liệu kiến trúc** của hệ thống BinanceFuturesJava.

## File hiện có

| File | Mô tả | Nguồn sự thật |
|---|---|---|
| `roadmap_tong.html` | Lộ trình kiểm chứng 6 Bước tổng quan (Bước 0–5) + trạng thái | `docs/ROADMAP.md` |
| `roadmap_wfo.html` | Lộ trình WFO chi tiết: 5 giai đoạn GĐ0–GĐ4 · TASK 112–122 · 3 vế so sánh · critical path | `docs/insights/WFO_ROADMAP.md` |
| `wfo_architecture.html` | Kiến trúc WFO 6 lớp + lộ trình GĐ0–GĐ4 | `docs/insights/WFO_ROADMAP.md` §3a |
| `system_architecture_all.html` | Toàn hệ thống: 4 node + luồng dữ liệu live→WFO | `docs/PIPELINE_PROVENANCE.md`, `docs/db/aerospike-226.md`, `docs/KAGGLE_RULES.md`, `docs/insights/WFO_ROADMAP.md` |

## Quy ước

- **Mỗi file HTML là snapshot** của kiến trúc tại thời điểm cập nhật. Ghi rõ ngày ở cuối file.
- Màu trạng thái: **xanh lá** = xong ✅ · **vàng** = đang làm 🔄 · **đỏ** = chưa làm ❌
- Khi trạng thái thay đổi: cập nhật attribute `data-status` trong HTML (xem hướng dẫn cuối mỗi file).
- File mới: thêm vào bảng trên.

## Cách cập nhật trạng thái nhanh

Tìm component cần cập nhật bằng `Ctrl+F` theo tên, sửa:
- `data-status="done"` → xanh lá
- `data-status="wip"` → vàng
- `data-status="todo"` → đỏ

Sau khi sửa: cập nhật dòng `Cập nhật lần cuối` ở cuối file HTML, commit theo quy ước project.
