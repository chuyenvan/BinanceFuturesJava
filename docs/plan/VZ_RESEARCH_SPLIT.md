# VZ_RESEARCH_SPLIT — vai trò các năm dữ liệu VZ (chốt TRƯỚC khi ai nhìn dữ liệu mới)

MASTER 2026-10-14. Áp cho mọi nghiên cứu dùng cột/nguồn MỚI của kho VZ (taker flow, basis, metrics 5m, funding theo phút, aggev).

| Năm | Vai trò | Được làm |
|---|---|---|
| 2024 | **KHÁM PHÁ** | Mô tả, profile theo thời gian sự kiện, thử giả thuyết tự do. Mọi phép thử ghi vào sổ `docs/research/VZ_EXPLORE_LEDGER.md` (đếm số phép thử). Không kết luận GO từ 2024. |
| 2022, 2023, 2025 | **XÁC NHẬN** | Chỉ chạy giả thuyết đã pre-reg (từ khám phá 2024), 1 lần, luật GO chốt trước; báo từng năm. |
| 2021 | Bền vững (phụ) | Báo kèm, không quyết định (metrics alt chỉ từ ~2021-12). |
| 2026-01→09 | HOLDOUT ĐÃ DÙNG | Không dùng để chọn/tune. Chỉ báo mô tả sau khi đã GO. |
| 2020 (`…-2020s`) | KHO NIÊM PHONG | Theo BACKCAST_RESERVOIR.md; 1 lần/ý tưởng; chỉ phần giá/funding (không metrics). |

Luật:
- Trước khi khám phá: E1 (bộ đo sự kiện) phải tái lập một kết quả đã biết trên 2024 (vd. số chân/sự kiện sập K24 EXEC năm 2024, chi phí bucket) — đây là kiểm công cụ, không phải phép thử giả thuyết.
- Khám phá 2024 tối đa 5 họ giả thuyết; mỗi họ ≤ 8 biến thể; chọn ≤ 3 giả thuyết sang pre-reg. Số phép thử trong sổ dùng để nở CI (√(2 ln k)) ở pre-reg xác nhận.
- Lợi nhuận luôn tính SAU chi phí vào bucket EXEC (thực) + phí; báo cả bản stress.
- Không dùng 2022/2023/2025 để "xem thử" trước pre-reg.
