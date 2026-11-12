# PREREG_R1_S1_ABLATION — ADDENDUM 1 (2026-11-10, TRƯỚC khi chạy bất kỳ kernel nào, chưa nhìn số)

1. **Sửa câu chữ G-FULL (lỗi soạn thảo).** Bản gốc §4 ghi "trên pool cũ, A3 phải trùng A0 từng cell". Điều này sai về cơ chế:
   - A0 chỉ hoán vị P(win) **trong nhóm có điểm S1**.
   - A3 hoán vị trên **toàn bộ** tick.
   - Vì vậy cell P(win) của A3 khác A0 ngay cả trên pool cũ.

   G-FULL thay bằng:
   - (a) ≥ 99 % dòng (tick, coin) có P(win) hữu hạn nhận được điểm S1;
   - (b) trên pool cũ, **điểm S1** của A3 trùng `pred_s1a2x1.parquet` (≥ 99,9 % dòng ghép được, max|Δ| ≤ 1e-6);
   - (c) G-SAN: multiset P(win) mỗi tick và vị trí NaN giữ nguyên tuyệt đối.
2. **Cách áp lọc A1 trong B0' (A3):** không có code sim nào cho A1, nên lọc bằng **hạ hạng**.
   - Coin thuộc A1-loại, cùng coin không có điểm S1 (feature toàn NaN), nhận phần P(win) **nhỏ nhất** của tick.
   - Giữ multiset, nên thang gate không đổi; coin bị hạ coi như không bao giờ vào top-24/top-2.
   - Danh sách A1 lấy từ `UniverseA1Classifier` (TRADFI/INDEX/PREMARKET) trên exchangeInfo 2026-10-27 (`v12/fixtures`). Symbol đã delist không có trong exchangeInfo thì coi là crypto.
   - A3 do đó là "S1FULL + A1" = B0' của test tương đương. Phần A1 đóng góp vào Δ được báo riêng: đếm leg A0 trên symbol A1-loại.
3. **Model S1 fold DEV:** dựng lại bằng `x1_s1_save_all_folds.py` với feature `feat_v2_x1_keep9.parquet`, vì `featv2/feat_v2_x1.parquet` gốc đã mất. G-S1R đạt bit-exact cho 16/16 fold (spearman 1, maxd 0, top8 100 %).
4. **HO 2026 của A3 lùi sau DEV.** Cần dựng feature S1 tháng 2026-01 → 2026-10 (keep9 chỉ tới 2026-01-01). HO vẫn chỉ để mô tả, không thay đổi tiêu chí nào.
5. Không đổi tiêu chí C1/C2/C-LIVE, seed, metric.
