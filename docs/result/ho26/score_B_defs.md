# HO26 — định nghĩa scorer B (commit TRƯỚC khi đọc printDone/equity 2026)

Prereg: `docs/prereg/PREREG_HOLDOUT2026H1.md` (35d03784 + ADDENDUM-1 0e3282a6 + ADDENDUM-2 1682a311/2691816d/8fe35b23) §1 — luật KHÔNG đổi. Script: `research/analysis/ho26_score_b.py` (không import script phân tích nào; chỉ `research/analysis/jbin.py` đọc nến 1m `/home/ubuntu/kaggle_data_hpo/ticker_YYYYMMDD.bin.gz`, tuple (startTime,max,min,close,open,vol), close = tup[3]). Scorer B không đọc `HO26_RESULT_A*` trước khi xong số. Smoke test logic chỉ trên DEV (cửa sổ 2025-10, run `nsel-*`).

## Input
- 48 run `~/kaggle_sim/out/ho26-<cfg>-<b|s>-s<seed>`, cfg ∈ {b0, k24, m2}, seed ∈ {42,7,13,21,99,123,777,2024}; `storage/printDone.csv`, `result.json`, `logs/sim.out`.
- Ticker key = ms UTC epoch (file theo ngày UTC); symbol ticker = `<sym>USDT` ↔ printDone `sym`.

## Định nghĩa (y như NSEL scorer B)
- Thời gian printDone `start`/`end` = giờ +07 (kiểm thực nghiệm TZ: median |entry/close(start)−1| giả định +07 vs UTC).
- Cửa sổ W = [2026-01-01 00:00, 2026-07-01 00:00) +07 (= tới hết 2026-06-30 23:59 +07).
- n = số dòng printDone có `start` ∈ W. ΣPnL = Σ `pnl` dòng có `end` ∈ W (penalty đã in-sim).
- Chân mở ở phút m nếu start ≤ m < end; q = margin/entry; unrealized = side·q·(close1m(m) − entry), side = +1 BUY, −1 SELL. pnl ghi nhận tại phút `end`.
- Equity MTM phút: E(m) = 35000 + Σ pnl(end ≤ m) + Σ unrealized chân mở tại m. Thiếu giá: ffill trong thân chân, trước giá đầu tiên dùng entry; báo % phút-chân thiếu giá.
- E đầu = E(2026-01-01 00:00 +07); E cuối = E(2026-06-30 23:59 +07). ROI cửa sổ = E cuối/E đầu − 1.
- maxDD MTM = min_m (E(m)/max_{W0≤u≤m} E(u) − 1) trên các phút trong W (đỉnh tính từ đầu cửa sổ), %. ΔmaxDD (pp) = maxDD(arm) − maxDD(base) (âm = DD sâu hơn).
- Theo tháng (+07): ROI = E(đầu tháng sau hoặc 06-30 23:59)/E(đầu tháng) − 1; ΣPnL theo `end`, n theo `start` trong tháng.
- Ngày (+07): mốc P_j = E(W0 + j ngày), j = 0..180, mốc cuối = E cuối ⇒ 181 return ngày r_j. Sharpe = mean(r)/sd(r, ddof=1)·√365; Sortino = mean(r)/√mean(min(r,0)²)·√365; CAGR năm hoá = (1+ROI)^(365/181) − 1.
- % ngày có vào = số ngày +07 có ≥ 1 `start`/181; % ngày có vị thế = số ngày có ≥ 1 phút có chân mở/181; số đợt = số phút `start` phân biệt trong W.
- Ghép cặp theo seed: Δ = arm − base cùng seed và cùng phí.

## Luật (bản CHÍNH = stress `-s-`, chép từ prereg §1)
- E0: mean ΣPnL_S(k24) > 0 VÀ ≥ 6/8 seed ΣPnL_S(k24) > 0.
- H-A (k24 vs b0): mean ΔΣPnL_S ≥ 0 VÀ mean ΔmaxDD ≥ −5pp.
- H-B (m2 vs k24): mean Δn ≥ +200 VÀ mean ΔΣPnL_S ≥ −10%·mean ΣPnL_S(k24) VÀ mean ΔmaxDD ≥ −8pp VÀ ≥ 5/8 seed có ΔΣPnL_S ≥ −10%·ΣPnL_S(k24 cùng seed). (Áp nguyên văn kể cả khi ΣPnL_S(k24) âm.)

## Báo kèm (không vào luật)
- Bản phí gốc `-b-` cùng mọi chỉ số; Sharpe/Sortino/CAGR năm hoá/maxDD mỗi cfg, tỉ lệ holdout/DEV với DEV baseline stress (K24-S `nsel-nen`): Sharpe 1,80, CAGR 27,6%, maxDD −22,9% (R1/R9: không coi là bằng chứng edge tuyệt đối).
- Bootstrap MTM block-10d: chuỗi Δ$ ngày = (P_{j+1}−P_j)_arm − (..)_base mỗi seed; moving-block bootstrap L=10 ngày, 19 block, cắt về 181, CÙNG chỉ số ngày cho 8 seed; thống kê = mean_seed Σ_ngày Δ$; B=10000, rng seed 20261010; CI95 percentile, P(Δ>0); inflate k=3: điểm ± nửa-bề-rộng·√(2 ln 3) (×1,482). Cặp: k24−b0, m2−k24, m2−b0, cho cả s và b.
- Theo tháng; % ngày có lệnh; số đợt.

## Tự kiểm
1. Mỗi run: 35000 + Σ pnl toàn bộ printDone vs `result.json.equity_final` (≤ 0,01%); E MTM phút cuối lưới (2026-07-02 06:59 +07) vs equity_final; n dòng printDone == `n_trades`; số chân đóng sau cuối lưới.
2. Mỗi run: E(m) vs log `BudgetManagerSimple: Update D 07:00 => b:.. unP:..` (b+unP) tại các mốc D 07:00 +07 trong W: median/max |lệch| %.
3. md5(gunzip) 181 file ticker 2026-01-01..06-30 vs `~/claude_master/1003/ho1/ticker26_oracle_gunzip_md5.json`; key phút lẻ.
4. Phần trước 2026 của `ho26-k24-s-s42` vs `nsel-nen-s42` (DEV cùng cấu hình K24+skipFull stress): đếm dòng printDone trùng y hệt (end < 2025-12-31 07:00 +07 = mốc dừng sim DEV), chỉ-holdout/chỉ-DEV, chân holdout mở qua mốc; equity DEV (35000+Σpnl, result) vs holdout realized tại mốc và MTM 2025-12-31 23:59 +07. Báo lệch, không sửa.

## Tài nguyên
- Lưới close 1m float32 [W0 − 1 ngày, W1 + 31 h) cho hợp các symbol có chân chạm lưới (~0,5 GB); parse 3 process; giữ `~/claude_master/1002/oracle_heavy.lock` trong lúc parse; không ghi cache ra đĩa.
