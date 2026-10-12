# HO4 — Định nghĩa SCORER A (chốt TRƯỚC khi đọc printDone/equity 2026 của `ho4-*`)

- Ngày 2026-10-12. Vai: SCORER A (độc lập với scorer B, không trao đổi), chấm 1 lần holdout HO4 (dữ liệu sàn Vision). Pre-reg `docs/prereg/PREREG_HOLDOUT2026H1.md` §1 + ADDENDUM-5 `31e3c9e7` + ADDENDUM-6 `af6d6c94` (§6.2a `923d7643`, `95da70a9`) + ADDENDUM-7 `106dd923` (§7.5 `0b798c10`). Luật KHÔNG đổi. Bối cảnh `docs/result/ho4/HO4_P1.md`.
- Script `research/analysis/ho4_score_a.py` = thước `ho26_score_a.py` (scorer A HO26) mở rộng 3 cửa sổ, cfg b0/k24, thêm báo kèm HO4. File này + script commit TRƯỚC khi mở printDone / sim.out / result.json của `ho4-*` (tại thời điểm commit: chỉ đã đọc `queue_status.tsv` — slug/status/md5/n/parity — và liệt kê tên thư mục; không eq/PnL).
- 0 sim, 0 Kaggle, 0 Java, 0 chạm 242/shadow.

## Run
- 32 run `~/kaggle_sim/out/ho4-<cfg>-<fee>-s<seed>`, cfg ∈ {b0 = B0 K16, k24 = K24+skipFull}, fee ∈ {s = stress 1,675% in-sim (bản CHÍNH), b = phí gốc (báo kèm)}, seed ∈ {42, 7, 13, 21, 99, 123, 777, 2024}.
- Run hợp lệ khi: printDone + result.json tồn tại; `result.ok` = true; `n_trades` = số dòng printDone; `~/claude_master/1011/ho4p1/q/queue_status.tsv` (dòng CUỐI của slug) COMPLETE + PASS; md5 printDone = md5 queue; jar bắt đầu `b7c89f09`; override khớp cfg (b0: SELECTOR_RANK_TOPK rỗng/16, skipFull rỗng/false; k24: TOPK 24 + skipFull true; NSEL tắt ở cả hai); penalty 0,01675 (s) / 0 (b); `date_last` ≥ 20260930. Run không hợp lệ ⇒ seed đó loại khỏi mọi luật dùng run đó; ngưỡng đếm seed (6/8) tuyệt đối.

## Cửa sổ (+07) và trục
- **W9** = [2026-01-01 00:00, 2026-10-01 00:00) = 273 ngày (CHÍNH); **H1** = [01-01 00:00, 07-01 00:00) = 181 ngày; **Q3** = [07-01 00:00, 10-01 00:00) = 92 ngày. printDone `start`/`end`, dòng `Update` = giờ +07; giá = ms UTC.
- Trục phút gốc T0 = 2026-01-01 00:00 +07; trục MTM kéo tới phút Update cuối của `date_last` (≤ +2 ngày) chỉ để tự kiểm. Sim chạy liên tục 2021-07-01 → SIM_END_DATE 20261001; equity đầu MỖI cửa sổ = E MTM tại phút đầu cửa sổ của chính run.

## Chỉ số mỗi (run, cửa sổ) — y HO26 scorer A
- n = số dòng printDone (mọi loại chân) có `start` ∈ cửa sổ. ΣPnL = Σ pnl các dòng có `end` ∈ cửa sổ (penalty đã in-sim, KHÔNG trừ post-hoc).
- E(m) = equity_start + Σ pnl dòng end < T0 + Σ pnl realized ghi trọn tại phút `end` (tích luỹ) + unrealized Σ q·(close1m(m) − entry) chân mở (start ≤ m < end), q = margin/entry.
- **Giá close1m = Binance Vision `futures/um` klines 1m** (file monthly cho tháng ≤ 2026-09, daily sau đó; kiểm sha256 theo `.CHECKSUM`), là nguồn đã sinh ticker sim HO4 (ADDENDUM-5/6). Lý do không dùng file ticker: không còn trên Oracle (`~/kaggle_data_hpo` là symlink hỏng; không có `ticker_2026*` trên đĩa) và không tải từ Kaggle. Symbol trong `settle_tail_symbols` (`docs/result/ho4/ho4p1_excl26.json`): giá NaN từ phút đầu chuỗi quote_volume = 0 dài ≥ 1 440 phút kéo tới kline cuối (luật §6.2-2, tính trên dữ liệu Vision 2025-12 → 2026-10-03 tải về; xấp xỉ khai trước vì ranh giới kernel quý). Thiếu giá: ffill trong ngày UTC; trước giá đầu ngày ⇒ entry (unrealized 0); đếm lại. Cache `~/claude_master/1012/ho4sa_wd/ho4sa_px` (cache tự tạo, xoá được).
- ROI = E1/E0 − 1 (%). maxDD = min_m E(m)/max_{đầu cửa sổ ≤ u ≤ m} E(u) − 1 (đỉnh đặt lại tại đầu MỖI cửa sổ; Q3 đỉnh từ 2026-07-01 00:00).
- Return ngày r_d = E(23:59 ngày d)/E(23:59 ngày d−1) − 1 (ngày đầu so E0); Sharpe = mean/sd(ddof 1)·√365; Sortino = mean/√mean(min(r,0)²)·√365; rf = 0; CAGR năm hoá = (E1/E0)^(365,25/ND) − 1. Tỉ lệ so DEV baseline stress: Sharpe/1,80; CAGR/27,6; maxDD/(−22,9).
- Theo tháng: ROI tháng (E 23:59 ngày cuối tháng / cuối tháng trước, tháng đầu so E0); n theo start, ΣPnL theo end; quý (Q1/Q2/Q3). % ngày có lệnh (≥ 1 start); số đợt (tách khi ≥ 3 ngày liền không lệnh); % thời gian có vị thế.

## Luật (bản CHÍNH = fee s; áp RIÊNG cho W9, H1, Q3)
- **E0**: k24 mean ΣPnL_S > 0 VÀ ≥ 6/8 seed ΣPnL_S > 0.
- **H-A** (k24 vs b0, ghép theo seed): mean ΔΣPnL_S ≥ 0 VÀ mean ΔmaxDD ≥ −5pp (ΔmaxDD = maxDD_k24 − maxDD_b0, pp; âm = sâu hơn).
- H-B không chấm (m2 bỏ). Diễn giải khai trước (ADD-3 §3, ADD-5 R25): Q3 = xác nhận mù duy nhất; H1 và W9 chứa H1 đã nhìn (HO26) ⇒ không độc lập.

## Báo kèm (KHÔNG vào luật)
- Bản phí gốc (fee b): mọi chỉ số + cùng biểu thức luật (mô tả).
- Δ ghép cặp k24 − b0: mean, sd, min, max, số seed Δ > 0, cận dưới t95 một phía + bản inflate √(2 ln 3).
- Bootstrap MTM ngày block-10d (NREP 5000, seed 20261012), mỗi cửa sổ × fee: (i) `k24`: X_s,d = ΔE ngày của k24 ⇒ thống kê mean_s Σ_d X = mean (E1 − E0) MTM (USD; đại diện MTM của ΣPnL); (ii) `k24-b0`: X_s,d = ΔE_k24 − ΔE_b0. Báo obs, CI95 raw + inflate, p5, P(≤ 0).
- Độ tập trung (mỗi run × cửa sổ, tóm mean qua seed, fee s): ΔE ngày MTM; top-k (k = 1/3/5) = tổng k ngày ΔE lớn nhất (phần dương); tỉ trọng / (E1 − E0) (khi > 0) và / Σ ngày dương. Leave-one-month-out: bỏ pnl các dòng end ∈ tháng j ⇒ ΣPnL_S k24 (mean, số seed > 0) và Δ(k24 − b0) (mean, số seed > 0).
- Độ nhạy dữ liệu H1: HO4 `ho4-<cfg>-s-s<seed>` vs HO26 `ho26-<cfg>-s-s<seed>` (kline 242) cùng cfg/seed: ΣPnL H1 (end), n H1 (start), Δ = HO4 − HO26; trùng lệnh = số cặp ghép 1-1 tham lam theo thời gian cùng sym, |Δstart| ≤ 1′ (lệnh start ∈ H1) / max(n_HO4, n_HO26). Kiểm chéo: n/ΣPnL HO26 tính lại == `docs/result/ho26/HO26_RESULT_A.json`.

## Tự kiểm
- Equity cuối: E(phút dòng Update cuối của `date_last`) vs `result.equity_final`, |lệch| ≤ 0,01% mỗi run; lệch E(m) vs b+unP mọi dòng Update trong trục (median / max).
- `n_trades` == số dòng printDone.
- Phần trước 2026 `ho4-k24-s-s42` vs `ho26-k24-s-s42` (đầu vào ≤ 2025 trùng byte): mọi dòng Update ngày ≤ 20251231 chung (số lệch, max |Δ(b+unP)|); printDone end < 20260101 00:00 so multiset mọi cột chung (chỉ HO4 / chỉ HO26); tập (sym, start) lệnh start < mốc còn mở qua mốc. Phải trùng; báo lệch, không sửa.
- Giá: phút-chân thiếu giá, file (symbol, kỳ) không có trên Vision, (symbol, ngày) không có giá nào, phút-chân rơi vào đuôi settle.
- Dry-run `--dry` (sau commit) trên `ho26-{b0,k24}-s-*` cửa sổ H1 (số đã công bố ở HO26): kiểm đường code + so `HO26_RESULT_A.json` (n / ΣPnL phải trùng; ROI/maxDD lệch do giá Vision vs ticker 242 — báo). Sửa lỗi script sau commit chỉ là lỗi code/hạ tầng, ghi chú trong RESULT; định nghĩa/luật không đổi.
