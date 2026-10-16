# VZ R2 — bookDepth tại tick vào đợt, khám phá 2024 (MASTER 2026-10-16)

Pre-reg `docs/prereg/PREREG_VZ_R2_BOOKDEPTH.md` (44f7c0ce + addendum 1 d8871cd3). Code `research/vz/r2/r2_bookdepth.py`.
Mẫu: chân sim `gqsf-a1` (K24+skipFull) thuộc đợt ≥ 6 chân, năm 2024 UTC: **626 chân / 44 đợt / 26 ngày**. bookDepth Vision UM 1 147 file (100 % tải được).

## Kiểm dữ liệu
V1 causal PASS (snapshot ≤ t_dec, trễ trung vị 29 s) · V3 phủ 100 % · V2 gốc FAIL (69,6 % ≤ 1 % so close) ⇒ addendum 1: mid ∈ [low, high] 2 nến = 100 % PASS; lệch do nến sập đi nhiều % trong 30 s cuối phút.

## Kết quả (4 phép thử, ledger 50 → 54)
| phép | thước | giá trị | CI95 (bootstrap ngày) | ứng viên? |
|---|---|---|---|---|
| T1 F1 bid −1 % / trung vị 24h | IC trong đợt | **+0,065** (spread nửa trên − dưới +1,11 %/chân) | [−0,010; +0,164] | KHÔNG (CI chứa 0) |
| T2 F2 imbalance ±1 % | IC trong đợt | +0,055 (+0,96 %) | [−0,042; +0,165] | KHÔNG |
| T3 F3 bid −5 % / trung vị 24h | IC trong đợt | −0,012 (−0,25 %) | [−0,080; +0,054] | KHÔNG |
| T4 trung vị F1 đợt ↔ ret đợt | Spearman qua đợt | +0,069 | [−0,188; +0,462] | KHÔNG |

## Đọc
- Không ứng viên theo pre-reg. F1/F2 cùng dấu cơ chế (bid còn dày / bid lấn ask ⇒ chân tốt hơn) nhưng n = 44 đợt ⇒ power thấp; T4 (veto đợt) gần như không có thông tin.
- Giới hạn chính: 1 năm, 1 seed; sổ lệnh trễ ~30 s so giá quyết định (ở nến sập là cũ).
- Muốn đi tiếp phải tăng n bằng cách gộp 2023 + 2025 vào KHÁM PHÁ (đốt nốt các năm đó) và chỉ còn HO 2026 để xác nhận — chưa làm, chờ quyết định.
