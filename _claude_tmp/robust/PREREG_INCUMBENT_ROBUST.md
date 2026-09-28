# PREREG — INCUMBENT ROBUST: edge incumbent có thật/bền không, và đến từ TIMING hay SELECTION (2026-09-28)

Chốt TRƯỚC khi tính bất kỳ số kết quả nào. Nội dung tiêu chí = MASTER chốt (nguyên văn §1–§5). Executor chỉ điền
§6 "cách chạy/đường dẫn/chi tiết kỹ thuật" — KHÔNG đổi tiêu chí. Đây là phép MÔ TẢ / kiểm độ bền, KHÔNG phải chọn
cấu hình; không đổi định nghĩa sau khi thấy số (mọi thay đổi = AMENDMENT có lý do, commit trước khi xem số bị ảnh hưởng).
0 sim Java. DEV ≤ 2025-12-31, không chạm dữ liệu 2026. Không push.

## 0. Đối tượng + bước 0 (kiểm hợp lệ, FAIL ⇒ dừng)

| nhãn | run | kỳ vọng |
|---|---|---|
| KEEPLEG0 nhịp 1' (incumbent) | `/home/ubuntu/java/devrun/FG_KEEPLEG0` | printDone md5 `99e42b75cf1a2142f9cd14dc72e371ba`, n 1085, eq 103083 |
| T170 (nền cũ) | `/home/ubuntu/java/devrun/X1_GS_T170_2021` | md5 `efb793e2468ca3a7318da0f0ad23d4fc`, n 1089, eq 111070 |
| sel15 | `/home/ubuntu/kaggle_sim/out/cd-sel15` | n 744, eq 71718 (md5 không công bố — ghi lại md5 đo được) |

eq = `b` dòng `BudgetManagerSimple: Update` cuối trong `logs/sim.out` (và `result.json` nếu có).

## 1. R1 — EPISODE JACKKNIFE (MASTER chốt)
Định nghĩa episode (chốt): gộp các ngày lịch (GMT+7 theo cột thời điểm VÀO lệnh) có ≥1 leg vào, nối các ngày cách
nhau ≤2 ngày trống thành 1 episode; PnL episode = Σ pnl USDT các leg VÀO trong episode. Báo: số episode, %PnL từ
top-1/3/5/10 episode, PnL tổng và CAGR (xấp xỉ: equity_cuối_mới = 35000 + Σpnl còn lại, trên cùng số năm) sau khi bỏ
top-1/3/5/10 episode. Tiêu chí mô tả chốt: "BỀN" nếu bỏ top-3 episode vẫn PnL>0 VÀ mọi năm còn ≥0 trên leg còn lại;
"MONG MANH" nếu bỏ top-3 đã ≤0.

## 2. R2 — BOOTSTRAP THEO CỤM EPISODE (MASTER chốt)
Resample episode có hoàn lại (bao gồm cả khoảng không lệnh ⇒ resample theo khối = episode + các ngày trống theo sau
nó), 5000 rep, seed 20260928; báo CI 95% của tổng PnL & CAGR, P(Σpnl ≤ 0).

## 3. R3 — DSR (Bailey & López de Prado 2014) (MASTER chốt)
Sharpe ngày của incumbent (từ equity ngày b+unP trong sim.out, như c3_rates), skew/kurt; phương sai SR giữa các cấu
hình lấy từ TOÀN BỘ run DEV có equity ngày trong /home/ubuntu/java/devrun/* và /home/ubuntu/kaggle_sim/out/* (cùng
cửa sổ 2021-07..2025-12; loại run khác cửa sổ); N hiệu dụng = N/(1+(N−1)ρ̄) với ρ̄ = tương quan trung bình return
ngày giữa các run (và báo thêm các cận N=10/50/200/448). Báo DSR cho KEEPLEG0 1', T170, sel15.

## 4. R4 — PLACEBO TIMING vs SELECTION (MASTER chốt)
Dùng harness replay thoát thuần Python của EXIT_FIT, phải PASS lại parity như doc trước khi dùng. Cho mỗi leg
PREDICT_SYMBOL_TRADE của KEEPLEG0 1' (và sel15 nếu có dữ liệu): (P1) GIỮ PHÚT VÀO, thay coin bằng coin ngẫu nhiên
từ universe đủ điều kiện tại phút đó (có dữ liệu 1m, đã niêm yết ≥30 ngày, loại coin đang giữ); (P2) phút ngẫu nhiên
đều trong cửa sổ DEV + coin ngẫu nhiên (đối chứng không-timing). Cùng size = margin leg gốc, cùng luật thoát
(arm +7% → trailing, time-stop 168h, phí 0.6%/vòng mức chính và 0.8% phụ). ≥200 lần rút (seed 20260928; nếu tài
nguyên cho phép 500). Phân rã: SELECTION = mean net/leg(thật) − mean(P1); TIMING = mean(P1) − mean(P2); CI bằng
bootstrap khối 72h theo phút vào (NREP 2000, seed 20260905). Báo cả 4 thước chuẩn (wl_ratio, tf_5, loss_mean,
conc_5) cho thật/P1/P2. Nếu R4 cần >6GB RAM hoặc >90 phút CPU Oracle ⇒ chuyển sang Kaggle CPU hoặc giảm số lần rút
xuống 100 và ghi rõ.

## 5. DỰ BÁO MASTER (ghi trước)
R1 MONG MANH hoặc sát ngưỡng (cửa sổ 2025-10-09..13 ~41% lãi 2025); R4 TIMING > SELECTION (selection ~0 trong CI).

## 6. CHI TIẾT KỸ THUẬT (executor điền — cách chạy, không đổi tiêu chí)

Script: `research/analysis/incumbent_robust_r123.py` (R1/R2/R3), `research/analysis/incumbent_robust_r4.py` (R4),
`research/analysis/incumbent_robust_fastexit.py` (engine thoát vector hoá 1-leg + cổng đối chiếu với
`research/exitfit/exit_engine.py`). Trung gian: `/home/ubuntu/claude_audit_0928/robust/`. Output:
`docs/result/RESULT_INCUMBENT_ROBUST.md` + `docs/result/RESULT_INCUMBENT_ROBUST.json`.

### 6.1 R1 (chi tiết)
- Leg = MỌI dòng `printDone.csv` (mọi `level`). Ngày vào = phần ngày của cột `start` (`YYYYMMDD HH:MM`, sim đã ép
  GMT+7). PnL = cột `pnl` (đã trừ phí + funding; khớp `b_final` theo `RESULT_INTRADAY_DD` V1).
- Episode: sort các ngày vào khác nhau; hai ngày liên tiếp d_i, d_{i+1} cùng episode ⇔ d_{i+1} − d_i ≤ 3 ngày (≤2 ngày
  trống ở giữa).
- Top-k = k episode có PnL LỚN NHẤT (xếp giảm dần). %PnL top-k = Σ top-k / Σ toàn bộ.
- CAGR = ((35000 + Σpnl còn lại)/35000)^(1/Y) − 1, Y = (ngày cuối − ngày đầu của chuỗi equity ngày sim.out).days/365.25
  (khuôn `c3_rates.stats`). Báo kèm CAGR gốc (bỏ 0) theo cùng công thức để đối chiếu.
- "Mọi năm còn ≥0": PnL theo NĂM của ngày vào (GMT+7) của các leg còn lại, năm 2021..2025, mỗi năm ≥ 0.
- Nhãn: BỀN / MONG MANH theo §1; trường hợp còn lại (bỏ top-3 PnL>0 nhưng có năm <0) ghi "TRUNG GIAN (không BỀN,
  không MONG MANH)". Chạy cho cả 3 đối tượng; nhãn chính = KEEPLEG0.
- Báo kèm (mô tả): episode chứa 2025-10-09..13 đứng hạng mấy và % PnL.

### 6.2 R2 (chi tiết)
- Trục ngày D0 = 2021-07-01 .. D_end = ngày cuối chuỗi equity sim.out (GMT+7). Khối: [ngày đầu episode i, ngày đầu
  episode i+1 − 1] (khối cuối tới D_end); nếu D0 < ngày đầu episode 1, thêm 1 khối "đầu kỳ" PnL 0 gồm các ngày đó.
  K = số khối. Mỗi rep rút K khối đều, có hoàn lại; Σpnl, Σngày; CAGR_rep = ((35000+Σpnl)/35000)^(365.25/Σngày) − 1
  (equity ≤ 0 ⇒ −100%). `np.random.default_rng(20260928)`, 5000 rep, CI percentile 2.5/97.5. Cả 3 đối tượng.
- Xấp xỉ cộng dồn (không compound) — cùng khuôn R1.

### 6.3 R3 (chi tiết)
- Equity ngày = b + unP theo regex `c3_rates.RX`, bỏ trùng ngày giữ dòng cuối. Nguồn: `logs/sim.out`, nếu không có thì
  `logs/sim.out.gz` của mọi thư mục con trực tiếp trong 2 gốc.
- Giữ run nếu ngày đầu = 20210701 VÀ ngày cuối = 20251230 (cửa sổ incumbent) VÀ ≥ 1640 điểm. Run có chuỗi equity
  TRÙNG HỆT nhau (parity rerun) gộp làm 1 (không phải thử nghiệm khác nhau). 3 đối tượng luôn nằm trong pool.
- r_t = eq_t/eq_{t−1} − 1 (ngày). SR = mean/std(ddof=1) theo NGÀY (không annualize; báo kèm ×√365). skew =
  `scipy.stats.skew(bias=False)`, kurt = Pearson (`fisher=False, bias=False`). T = số return ngày.
- V[SR] = phương sai (ddof=1) SR ngày giữa các run trong pool. ρ̄ = trung bình tương quan Pearson ngoài đường chéo của
  return ngày giữa các run (cùng trục ngày). N = số run pool; N_eff = N/(1+(N−1)ρ̄).
- SR0 = √V · ((1−γ)Φ⁻¹(1−1/N) + γΦ⁻¹(1−1/(N·e))), γ = 0.5772156649. DSR = Φ((SR−SR0)·√(T−1) /
  √(1 − skew·SR + (kurt−1)/4·SR²)). Báo cho N_eff và N ∈ {10, 50, 200, 448} (+ N thật của pool), kèm PSR(SR0=0).

### 6.4 R4 (chi tiết)
- **Cổng harness (bắt buộc, trước khi dùng):** (G1) `python3 research/exitfit/parity.py` trên T170 phải in
  `VERDICT: PASS` (ngưỡng như `PREREG_EXIT_FIT`). (G2) engine vector hoá 1-leg (`incumbent_robust_fastexit.py`, cùng
  hằng số/luật P0 của `exit_engine.py`: arm theo HIGH 1m, gap=min(peak·0.5, cap 0.03/0.08 theo symbolPred>0.29), bước
  0.005, SL ratchet liên tục (>entry), BLOCK_INTRABAR_LOOKAHEAD, khớp min(SL, open), time-stop 168h tại min(open,close),
  delist guard >2 ngày) phải khớp `exit_engine.simulate` trên (a) mọi cụm 1-leg của T170 trong `bars.pkl` và (b) ≥1000
  lần rút placebo (P1+P2) lấy mẫu ngẫu nhiên từ chính dữ liệu dùng để đo: status ≥ 99.5%, phút thoát trùng ≥ 99.5%,
  |Δ gross return| ≤ 1e-4 ở ≥ 99%. FAIL ⇒ dừng báo.
- Leg: dòng `level == PREDICT_SYMBOL_TRADE` (KEEPLEG0: kỳ vọng 817; sel15: 483). t0 = `start` (GMT+7 → UTC ms),
  margin = cột `margin`, symbolPred = cột `symbolPred` của leg (null ⇒ cap weak) — placebo dùng CÙNG symbolPred của
  leg gốc để "cùng luật thoát".
- Đo trên một leg đơn (không DCA/merge, không funding): entry = close nến 1m tại t0 (đã kiểm = entry CSV ở 100% cụm
  T170), qty = margin/entry. gross = qty·(priceTP − entry)/margin. net_f = gross − f, f = 0.006 (CHÍNH), 0.008 (phụ).
  "THẬT" = coin thật đo bằng cùng engine/luật (để P1/P2/thật cùng một thước). Báo kèm net thực tế sim (pnl/margin,
  có DCA/funding/phí 0.8%) chỉ để tham chiếu.
- Dữ liệu 1m: `/home/ubuntu/java/simulator/kaggle_data_hpo/daily/ticker_YYYYMMDD.bin.gz` (nguồn sim, file theo ngày
  UTC), parse bằng `research/analysis/jbin.py`. Trục dữ liệu dừng tại 2025-12-30 23:59Z (cuối chuỗi sim); leg chưa
  thoát ⇒ OPEN_AT_END tại close cuối (như sim). KHÔNG đọc file 2026.
- Universe đủ điều kiện tại phút t: symbol đuôi `USDT` có nến tại đúng phút t; ngày xuất hiện đầu tiên trong dữ liệu
  (quét từ 2021-06-01; có mặt 2021-06-01 ⇒ coi niêm yết ≤ 2021-06-01) ≤ t − 30 ngày; KHÔNG đang được run tương ứng
  giữ tại t (giữ = có cụm (sym,end) của printDone run đó với start_leg_đầu ≤ t < end). Coin thật của leg tự động bị
  loại (đang giữ tại t0).
- P1: mỗi leg i, mỗi lần rút d: coin = eligible(t0_i)[⌊u·n⌋]. P2: phút t ~ đều trên các phút [2021-07-01 00:00 GMT+7,
  2025-12-30 23:59Z]; coin = eligible(t)[⌊u·n⌋] (loại coin run đang giữ tại t); nếu n=0 thì rút lại phút. P2 gắn với
  leg i chỉ qua margin_i và symbolPred_i.
- RNG: `np.random.default_rng(20260928)`; thứ tự sinh cố định: KEEPLEG0 [u_P1 (n×D), t_P2 (n×D), u_P2 (n×D)] rồi
  sel15 cùng thứ tự. D = 500 nếu ước tính CPU ≤ 90 phút và RAM ≤ 6GB; nếu không thì D = 200; nếu vẫn vượt ⇒ D = 100
  (hoặc Kaggle) và ghi rõ. Quyết định D dựa trên đo tốc độ chunk đầu (trước khi tổng hợp số), ghi vào log.
- Phân rã (theo net_f, đơn vị return/leg; kèm USDT/leg = ×margin_i): P1̄_i = mean_d net(P1_{i,d}); SELECTION =
  mean_i(thật_i − P1̄_i); TIMING = mean_i(P1̄_i) − mean(P2 gộp tất cả i,d); TỔNG = mean(thật) − mean(P2).
- CI 95% (percentile): khối 72h = ⌊(t0 − t0_min)/72h⌋ theo phút vào leg; NREP 2000, `default_rng(20260905)`: rút có
  hoàn lại số khối = số khối khác nhau → SELECTION_b = mean các leg trong khối rút của (thật − P1̄). TIMING_b =
  mean P1̄ trên CÙNG khối rút − mean P2 trên khối rút độc lập của pool P2 (khối 72h theo phút vào P2,
  `default_rng(20260906)`). Không inflate (phép mô tả, 1 phân rã/đối tượng).
- 4 thước chuẩn (định nghĩa `tail_robust_rulers.py`, trên net_f/leg gộp): wl_ratio = mean(net>0)/mean(|net<0|);
  tf_5 = mean sau khi bỏ ⌈5%·N⌉ leg lớn nhất; loss_mean = mean(net | net<0) (số âm); conc_5 = Σ top ⌈5%·N⌉ / Σ net.
  Cho thật / P1 (gộp n×D) / P2 (gộp n×D), cả 2 mức phí.
- Đọc kết quả (mô tả): "SELECTION ~0" nếu CI SELECTION chứa 0; "TIMING > SELECTION" nếu điểm TIMING > điểm
  SELECTION; báo thêm CI có tách nhau hay không.
- Tài nguyên: 1 tiến trình chính + tối đa 3 worker parse, `nice -n 10`, kiểm `free -g` trước (available ≥ 10G),
  RAM mục tiêu ≤ 6GB; báo CPU-phút thực tế.
