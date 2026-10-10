# HO26 — Định nghĩa SCORER A (chốt TRƯỚC khi đọc output 2026)

- Ngày: 2026-10-10. Vai: SCORER A (chấm chính thức holdout 2026H1, chấm 1 lần). Pre-reg `docs/prereg/PREREG_HOLDOUT2026H1.md` (35d03784 + ADDENDUM-1 0e3282a6 + ADDENDUM-2 1682a311/2691816d/8fe35b23) §1. Luật KHÔNG đổi.
- Script `research/analysis/ho26_score_a.py`. File này + script commit TRƯỚC khi mở bất kỳ printDone/equity/result.json nào của `ho26-*` (tại thời điểm commit: chỉ đã liệt kê tên file/thư mục và đọc `queue_status.tsv` — slug/status/md5/n/parity, không eq/PnL).
- 0 sim, 0 Kaggle, 0 Java, 0 chạm 242/shadow. Thước MTM phút = `nsel_score_b` (cùng quy ước, import `TZ_MS`, `parse_min`, `TICKER`, `jbin`); Sharpe/Sortino/đợt = quy ước `coverage_m2_base` (DEV baseline Sharpe 1,80 / CAGR 27,6% / maxDD −22,9% đo bằng thước này).

## Run
- 48 run `~/kaggle_sim/out/ho26-<cfg>-<fee>-s<seed>`, cfg ∈ {b0, k24, m2}, fee ∈ {s = stress 1,675% in-sim (bản CHÍNH), b = phí gốc (báo kèm)}, seed ∈ {42, 7, 13, 21, 99, 123, 777, 2024}.
- Run hợp lệ khi: printDone + result.json tồn tại; `result.ok` = true; `n_trades` = số dòng printDone; queue (dòng cuối của slug) COMPLETE + PASS; md5 printDone = md5 queue; jar bắt đầu `b7c89f09`; override khớp cfg (b0: SELECTOR_RANK_TOPK rỗng/16, skipFull rỗng/false, NSEL tắt; k24: TOPK 24 + skipFull true, NSEL tắt; m2: TOPK 24 + skipFull true + NSEL_ADD_ENABLED true); penalty = 0,01675 (s) / 0 hoặc rỗng (b); `date_last` ≥ 20260630. Run không hợp lệ ⇒ seed đó loại khỏi CẢ cặp của luật dùng run đó.

## Cửa sổ và trục thời gian
- printDone `start`/`end` và dòng `Update` của log = giờ local +07; ticker = ms UTC (như nsel_score_b).
- Cửa sổ chấm W = [2026-01-01 00:00, 2026-07-01 00:00) +07 (= tới 2026-06-30 23:59 +07); 181 ngày, 260 640 phút. Trục phút gốc T0 = 2026-01-01 00:00 +07 = 2025-12-31 17:00 UTC.
- Sim chạy liên tục 2021-07-01 → SIM_END_DATE 20260701; chỉ cắt cửa sổ khi chấm.

## Chỉ số mỗi run (y như NSEL)
- n = số dòng printDone (mọi loại chân) có `start` ∈ W.
- ΣPnL = Σ pnl các dòng printDone có `end` ∈ W (penalty đã nằm trong giá vào in-sim ⇒ KHÔNG trừ post-hoc).
- Equity MTM phút E(m) = equity_start (result.json) + Σ pnl dòng có end < T0 + Σ pnl realized ghi trọn tại phút `end` (end ≥ T0, tích luỹ) + unrealized Σ q·(close1m(m) − entry) cho chân mở (start ≤ m < end), q = margin/entry; thiếu giá: ffill trong ngày UTC, trước giá đầu ngày ⇒ entry (unrealized 0), đếm lại.
- Equity đầu cửa sổ E0 = E(T0) (MTM tại 2026-01-01 00:00 +07 của chính run); equity cuối E1 = E(2026-06-30 23:59 +07).
- ROI cửa sổ = E1/E0 − 1 (%). maxDD = min_m E(m)/max_{T0≤u≤m} E(u) − 1 trên phút trong W (đỉnh tính từ đầu cửa sổ), %.
- Return ngày r_d = E(23:59 +07 ngày d)/E(23:59 ngày d−1) − 1 (ngày đầu so E0), 181 giá trị. Sharpe = mean/sd(ddof 1)·√365; Sortino = mean/√mean(min(r,0)²)·√365; rf = 0. CAGR năm hoá = (E1/E0)^(365,25/181) − 1. Tỉ lệ holdout/DEV: Sharpe/1,80; CAGR/27,6; maxDD/(−22,9).
- ROI theo tháng = E(23:59 ngày cuối tháng)/E(cuối tháng trước, tháng 1 dùng E0) − 1; quý tương tự (Q1 = tới 31/3, Q2 = 1/4 → 30/6). n tháng theo start, ΣPnL tháng theo end.
- % ngày có lệnh = % ngày (+07) trong W có ≥ 1 dòng start. Đợt = cụm ngày có lệnh, tách khi ≥ 3 ngày liền không có lệnh vào (EP_GAP 3, = coverage_m2_base). Khoảng trống dài nhất = số ngày liền không lệnh vào. % thời gian có vị thế = % phút W có ≥ 1 chân mở.

## Ghép cặp và luật (bản CHÍNH = fee s; không đổi)
- Δ = cfg − cfg so sánh, cùng seed, cùng fee. Tóm tắt: mean, sd, min, max, số seed Δ>0, cận dưới một phía mean − t(0,95; n−1)·sd/√n và bản inflate (× √(2 ln 3) ≈ 1,482, k = 3 cấu hình).
- E0: k24-S mean ΣPnL_S > 0 VÀ ≥ 6/8 seed ΣPnL_S > 0.
- H-A (k24 vs b0): mean ΔΣPnL_S ≥ 0 VÀ mean ΔmaxDD ≥ −5pp (ΔmaxDD = maxDD_k24 − maxDD_b0, pp; âm = DD sâu hơn).
- H-B (m2 vs k24): mean Δn ≥ +200 VÀ mean ΔΣPnL_S ≥ −0,10 × mean ΣPnL_S(k24) VÀ mean ΔmaxDD ≥ −8pp VÀ ≥ 5/8 seed có ΔΣPnL_S ≥ −0,10 × ΣPnL_S(k24 cùng seed). Áp dụng nguyên văn kể cả khi ΣPnL_S(k24) âm (ngưỡng khi đó dương). Mean ΣPnL_S(k24) lấy trên đúng tập seed hợp lệ của H-B.
- Ngưỡng đếm seed (6, 5) là tuyệt đối; nếu seed bị loại vẫn giữ 6 / 5.

## Báo kèm (không vào luật)
- Bản phí gốc (fee b): cùng mọi chỉ số + cùng biểu thức luật (chỉ mô tả).
- Bootstrap MTM ngày block-10d ghép cặp: X_s,d = ΔE ngày (cfg) − ΔE ngày (so sánh), d = 181 ngày (ngày đầu so E0); thống kê = mean_s Σ_d X_s,d (= Δ(E1 − E0) MTM, USD); block 10 ngày, NREP 2000, seed 20260905; CI95 raw + inflate √(2 ln 3); p5; P(≤0). Cặp: k24−b0, m2−k24 (cả s và b).
- Theo tháng/quý (mean Δ), % ngày có lệnh, số đợt, Sharpe/Sortino và tỉ lệ holdout/DEV.

## Tự kiểm
- Equity cuối: E(phút của dòng `Update` cuối trong sim.out có ngày = date_last) vs `result.equity_final`: |lệch| ≤ 0,01% (báo từng run); kèm lệch E(m) vs b+unP mọi dòng Update trong trục tính (median/max).
- n: `n_trades` result == số dòng printDone.
- Phần trước 2026 của `ho26-k24-s-s42` vs `nsel-nen-s42` (cùng cấu hình DEV): mọi dòng Update có ngày ≤ 20251231 chung giữa 2 run (số lệch, max |Δ(b+unP)|), equity Update 20251230/20251231; dòng printDone có end < 20251230 07:00 so như multiset mọi cột chung (chỉ DEV / chỉ HO). Báo lệch, không sửa.
- Dry-run đường code (`--dryrun-dev`) chạy trên run DEV nsel-nen/nsel-m2 cửa sổ 2025H1 trước khi chấm; output ở thư mục làm việc, không vào docs. Sửa lỗi script sau commit (nếu có) chỉ là lỗi hạ tầng/code, ghi chú trong RESULT; định nghĩa/luật không đổi.
