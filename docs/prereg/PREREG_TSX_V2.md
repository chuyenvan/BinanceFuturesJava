# PREREG_TSX_V2 — biến thể thoát SAU mốc 168h cho cụm được hoãn (X14), chấm bằng replay trên DEV

Ngày 2026-10-22. Viết + commit TRƯỚC khi tính bất kỳ biến thể nào. Công cụ: replay engine Phase A (commit `1c90b233`, validate 1 364/1 364 cụm hoãn, 4 299/4 299 cụm cắt 168h). Không HO 2026 / 2020 cho chọn lựa; không đụng 242/shadow; không REST.

## 0. Trung thực
- Mọi kết quả ở đây là IN-SAMPLE: X14 (−30 %/30 ngày) sinh từ chẩn đoán trên chính DEV; DEEP (40b12804) và Phase A (1c90b233) đã cho thấy:
  kênh "cắt ở 504h" ~0 edge, 06/2024 âm, 45 % ngày ON sát ngưỡng, ngày OFF sát ngưỡng giữ H504 +1,1k/seed, và X14 direct theo tertile ρ
  (ρ cao đóng góp lớn nhất ⇒ B2 dự kiến bất lợi). Các họ biến thể dưới đây do MASTER cố định trước Phase A; ở đây chỉ chốt định nghĩa chính xác.
- Trial ledger (họ TS_MKT_EXT): X14 = 1 thử trước đó. Lần này 14 ô mới: B1 ×2, B2 ×2, B3 ×2, B4 ×8 (ô −0,30/30 = base, không đếm). Tổng 15.
- Kỳ vọng trước: P(có ứng viên B1–B3 qua đủ 5 điều kiện) thấp (~10–20 %); hiệu ứng nhỏ so với nhiễu đường đi (chỉ ~9 đợt có cụm hoãn).

## 1. Thước đo
- Quần thể: mọi cụm của run X14 (`tsx-x14-*`, 8 seed DEV) chạm mốc 168h (tuổi ≥ 168h+1'): 4 323 cụm. Leg/qty từ printDone X14.
- PnL_V(c) = replay luật V trên cụm c (engine Phase A, tick-normalize bật, funding Vision, LIT funding 0).
- **Δ_V(c) = PnL_V(c) − PnL_X14(c)**; direct ΔPnL/seed = Σ_c theo seed. Δ so P0: Δ^P0_V = PnL_V − PnL_cut168 (P0 trên leg X14).
- BỎ QUA lãi kép, slot, vốn khoá, lệnh vào mới (ghi rõ). Biến thể giữ lâu hơn X14 nguồn ⇒ không có DCA mới sau thoát X14 (đóng băng).
- Cụm "bị ảnh hưởng": phút thoát hoặc PnL khác X14 (|Δ| > 1e-9).

## 2. Biến thể (chính xác)
Ký hiệu: EOD(d) = ALT_EW (cumsum log-ret 1m `edge_attr/index.npz`) cuối ngày UTC d; ON_base(D) ⟺ exp(EOD(D−1) − max EOD(D−31..D−1)) − 1 ≤ −0,30, D ∈ [2021-07-01, 2025-12-31] (= 214 ngày, sha c79ef302). Hoãn ở tick t (cụm chưa arm, tuổi > 168h) ⟺ eligible(c) ∧ tuổi ≤ trần ∧ ON(ngày UTC của t); ngược lại cắt min(open, close) như sim.
- **Base X14**: ON_base, trần 504h, eligible ≡ đúng.
- **B1a / B1b** (trần giữ tổng): trần 336h / 420h (tuổi ≤ 336·60 / 420·60 phút). 504h = base.
- **B2a / B2b** (lọc idiosyncratic): eligible(c) ⟺ ρ(c) ≤ k, k = 1,5 / 2,5. ρ như Phase A §A2c: loss = 1 − P_mark/F (F giá leg đầu, P_mark = min(open, close) nến mốc), mkt = 1 − exp(EW(mark) − EW(t0)) (EW phút ≤ t), ρ = loss/mkt; loss ≤ 0 ⇒ ρ = 0 (eligible); mkt ≤ 0 ∧ loss > 0 ⇒ ρ = +∞ (không eligible). Đánh giá 1 lần tại mốc.
- **B3a / B3b** (thoát khi hồi, theo ngày — nhân quả, cùng cơ chế "cờ tắt"): ON_B3(D) = ON_base(D) ∧ reb(D) < r, reb(D) = exp(EOD(D−1) − min_{d∈[F_D−1, D−1]} EOD(d)) − 1, F_D = ngày đầu của chuỗi ngày ON_base liên tiếp chứa D. r = 0,10 / 0,20. Cụm đang hoãn bị cắt ở tick đầu ngày không ON_B3.
- **B4** (bề mặt, KHÔNG chọn): ON_{thr,L}(D) ⟺ exp(EOD(D−1) − max EOD(D−1−L..D−1)) − 1 ≤ thr, thr ∈ {−0,25; −0,30; −0,35}, L ∈ {20; 30; 45} ngày; trần 504h. (−0,30; 30) ≡ base.

## 3. Báo cáo mỗi biến thể
Δ direct/seed (8 giá trị, TB, số seed > 0), số cụm ảnh hưởng/seed, Δ theo đợt, leave-one-episode-out, CI bootstrap theo đợt, Δ đợt LUNA và 06/2024, Δ^P0.
- **Đợt** = 25 đợt Phase A (khoảng liên tiếp của ON_{−0,25;45} nối khoảng hở ≤ 3 ngày; danh sách trong `phaseA.json`). Cụm gán theo ngày UTC của mốc. LUNA = đợt 2022-04-27..2022-07-06; 06/2024 = đợt 2024-06-18..2024-07-26.
- Δ_e = TB 8 seed của Σ Δ trong đợt e. LOO_e = Δ_tổng − Δ_e.
- Bootstrap: đơn vị = đợt có ≥ 1 cụm bị ảnh hưởng (bất kỳ seed) với biến thể đó; thống kê = Σ Δ_e trên mẫu lặp có hoàn lại cùng số đợt; 10 000 lần, RNG seed 20261022; CI95 percentile. (Cụm ngoài mọi đợt — không thể bị ảnh hưởng vì cần ngày ON — kiểm = 0.)

## 4. Luật chọn (cố định) — chỉ B1–B3
Ứng viên ⟺ (i) Δ > 0 ở 8/8 seed; (ii) LOO_e > 0 với MỌI đợt e; (iii) cận dưới CI95 bootstrap theo đợt > 0; (iv) Δ_LUNA ≥ −0,20·|D_LUNA| và Δ_06/2024 ≥ −0,20·|D_0624|, với D = X14 direct của đợt (Phase A: LUNA +1 625 ⇒ ngưỡng −325; 06/2024 −249 ⇒ ngưỡng −50, USD/seed); (v) ô còn lại cùng họ có Δ TB > 0 (họ chỉ có 2 ô ngoài base ⇒ "vùng lân cận dương" = cả hai ô dương).
Nhiều ứng viên ⇒ ít tham số nhất (đều 1) ⇒ Δ TB lớn nhất. Không ứng viên ⇒ giữ X14, không thử thêm ô.
**B4**: báo lưới 3×3 Δ (so X14) và Δ^P0 (so cắt 168h). Plateau dương quanh base ⟺ base và 4 ô kề (−0,25/30, −0,35/30, −0,30/20, −0,30/45) đều có Δ^P0 TB > 0 VÀ 8/8 seed > 0. Không đạt ⇒ ghi CẢNH BÁO, không đổi luật. Không chọn ô B4 dù tốt hơn.

## 5. Kiểm trước khi báo (fail ⇒ dừng)
K1 replay base = `pnl_x14` Phase A (max|Δ| ≤ 1e-6) và = printDone X14 (1e-3); K2 B4(−0,30; 30) ≡ base (Δ = 0 mọi cụm); K3 B1 trần 504 ≡ base; K4 B3 r = +∞ ≡ base; K5 B2 k = +∞ ≡ base; K6 số ngày ON mỗi ô B4 và B3 ghi ra; K7 không cụm nào OPEN cuối cửa sổ. (K2–K5 là kiểm, không đếm vào ledger.)

## 6. Ghi trước
- Ứng viên (nếu có) CHỈ là ứng viên in-sample. Xác nhận bắt buộc: (1) sim Java đầy đủ DEV 8 seed (lãi kép/slot); (2) HO 2026 chỉ MÔ TẢ (2026 rất ít cụm hoãn, không cụm 504h); (3) có thể kho 2020 một lần — quyết định owner.
- Mọi thay đổi chỉ vào v1.2; không đổi shadow/X14 đang chạy.
