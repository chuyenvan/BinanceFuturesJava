# PREREG — RESET RULE Phase 3: ĐỘ BỀN ỨNG VIÊN `R4` (2026-09-29)

Chốt **TRƯỚC** khi tính bất kỳ số kết quả nào. Nội dung = `PLAN_OPENCLAW_BASELINE_RESET_20260928.md` §Phase 3 +
`PLAN_OPENCLAW_ADDENDUM_20260928.md` §D5, dùng lại tiêu chí của **`docs/prereg/PREREG_INCUMBENT_ROBUST.md`**
(MASTER đã soạn cho incumbent; ở đây áp nguyên lên `R4`). Executor chỉ điền §7 (cách chạy/đường dẫn); **KHÔNG đổi
tiêu chí** sau khi thấy số (mọi thay đổi = AMENDMENT có lý do, commit trước khi xem số bị ảnh hưởng).

**0 sim Java · 0 train · DEV ≤ 2025-12-31 · tuyệt đối KHÔNG chạm dữ liệu/năm 2026** (`HOLDOUT_UNSEAL` để Phase 4).
Không sửa Java, không chạm production/`242`/ONNX/LIVE, không push file dữ liệu. Mọi phép dưới đây là **MÔ TẢ / kiểm
độ bền**, KHÔNG phải chọn cấu hình: đối tượng và ngưỡng **đã khoá trước**.

---

## 0. ĐỐI TƯỢNG + BƯỚC 0 (kiểm hợp lệ, FAIL ⇒ DỪNG)

Đối tượng **khoá trước** (từ `RESULT_RESET_RULE_P2.md` @`47a9d90`):

| nhãn | run artifact | cấu hình | cost artifact |
|---|---|---|---|
| **`R4`** (ứng viên) | `kaggle_sim/out/p2-r4-base` | `SIM_F_BASE ×0,5` · `SELECTOR_RANK_TOPK 16` · `SIM_GATE_DYN_SCALE 1.55` | base `0,112 %/vòng` |
| **`R4`** @stress | `kaggle_sim/out/p2-r4-stress` | y hệt | stress `0,150 %/vòng` |
| **`B*`** = `R0` (chuẩn, incumbent) | `kaggle_sim/out/p2-r0-base` | `SIM_F_BASE ×1` · `K 8` · `gate 1.70` | base `0,112 %/vòng` |
| **`B*`** @stress | `kaggle_sim/out/p2-r0-stress` | y hệt | stress `0,150 %/vòng` |

Nền chung cả 4: `KEEPLEG0` + `CONC_CAP_PERCOIN 15%` + nhịp 1'. Số tham chiếu đã công bố (P2): `R4` n `2027`,
equity `104 489`/`103 351`; `B*` n `1086`, equity `126 108`/`124 685`. **`pnl` trong `printDone.csv` ĐÃ ở đúng cost
của run ⇒ KHÔNG hiệu chỉnh phí** (driver `as-is`, tức `legacy 0,008` ép = cost thật của artifact).

**Bước 0 (cổng DỪNG):**
1. `printDone.csv` `R4`/`B*` tồn tại · `n` khớp `2027`/`1086` · equity `sim.out` khớp bảng trên.
2. `R4` @base và @stress **byte-giống nhau phần cấu trúc leg** (`level` counts: PREDICT `1745`, BIG_DOWN `248`,
   DCA `34`); lệch ⇒ DỪNG.
3. **Harness thoát (cho T4):** `python3 research/exitfit/parity.py` trên T170 phải in **`VERDICT: PASS`**
   (ngưỡng y `PREREG_EXIT_FIT`: status ≥99.0%, phút thoát trùng ≥97.0%, |Δ PnL| ≤1USDT ≥95%). FAIL ⇒ DỪNG, T4 = "KHÔNG CHẤM ĐƯỢC".
4. **0 đọc file 2026**: mọi ngày đọc ≤ `20251230`.

---

## 1. T1 — EPISODE JACKKNIFE (MASTER chốt)

**Episode (chốt):** các NGÀY LỊCH (GMT+7 theo cột thời điểm VÀO — `start`) có ≥1 leg; nối 2 ngày liên tiếp cách nhau
**≤ 2 ngày trống** thành 1 episode. PnL episode = Σ `pnl` (đã đúng cost) các leg VÀO trong episode. *Giống định nghĩa
`episode_drop3` (`reset_rule_score.py`) và `PREREG_INCUMBENT_ROBUST` §1.*

Báo cho **`R4` và `B*`**, ở **cả base và stress**:
- số episode, %PnL top-1/3/5/10, và hạng của episode chứa `2025-10-09..13`.
- Sau khi **BỎ top-1 / top-3 / top-5** episode (xếp giảm dần): `ΣPnL_còn`, `CAGR_còn`
  (`= ((35000+ΣPnL_còn)/35000)^(1/Y)−1`, `Y` = số năm span equity ngày), và `Calmar_còn = CAGR_còn/|maxDD_còn|`
  với `maxDD_còn` = maxDD của đường equity dựng lại `35000 + cumΣPnL_còn` (theo ngày ra lệnh).

**Tiêu chí (chốt):** `R4` **PASS T1** ⇔ bỏ top-3 **VÀ** top-5 episode đều `ΣPnL_còn > 0` **VÀ**
`Calmar_còn(top-3) ≥ Calmar_còn(top-3) của B*`. Ngược lại **FAIL T1** (khai rõ cái nào trượt).
Ngoài ra báo nhãn mô tả của `PREREG_INCUMBENT_ROBUST` §1 ({BỀN / MONG MANH / TRUNG GIAN}) để đối chiếu.

## 2. T2 — BOOTSTRAP CỤM EPISODE (5000 rep, seed `20260928`)

1. **Đơn đối tượng (CI Calmar):** resample episode **có hoàn lại** (khối = episode + các ngày trống theo sau; thêm 1
   khối "đầu kỳ" PnL 0 nếu `D0 < ngày đầu episode 1`), `K` = số khối; mỗi rep rút `K` khối đều. `ΣPnL_rep`;
   `CAGR_rep = ((35000+ΣPnL_rep)/35000)^(365.25/Σngày)−1`; dựng đường `35000 + cumΣPnL_rep` theo thứ tự khối rút →
   `maxDD_rep` (`min(eq/cummax−1)`, gồm cả điểm xuất phát `35000`); `Calmar_rep = CAGR_rep/|maxDD_rep|`.
   `np.random.default_rng(20260928)`, **5000 rep**, CI percentile 2.5/97.5. Báo CI `ΣPnL`, CI `Calmar`, `P(ΣPnL ≤ 0)`.
2. **Paired (CI chênh `R4 − B*`):** dùng **một lưới khối CHUNG** = episode dựng trên **hợp** ngày-vào của `R4` và `B*`
   (nối ≤2 ngày trống); gán mỗi leg vào khối chứa ngày-vào của nó; mỗi rep rút `K` khối **dùng CÙNG chỉ số rút cho cả
   hai arm** → `Calmar_rep(R4)`, `Calmar_rep(B*)`, chênh. Cùng seed/reps. Báo CI chênh.

**Tiêu chí (chốt):** `R4` **PASS T2** ⇔ CI95 `Calmar` **không chứa 0** (cận dưới > 0). Chênh `R4−B*` **chứa 0** ⇒
gọi đúng tên: **biên `R4` trên `B*` KHÔNG phân giải được (nhiễu)** (không tính là FAIL T2, nhưng là cờ đỏ Phase 4).

## 3. T3 — DSR (Bailey & López de Prado 2014) — độ phân tán SR từ run DEV cùng cửa sổ

Theo nguyên `PREREG_INCUMBENT_ROBUST` §6.3. Equity NGÀY = `b + unP` theo regex `c3_rates` từ `logs/sim.out` (không có
thì `sim.out.gz`), bỏ trùng ngày giữ dòng cuối. **Pool** = mọi run trực tiếp trong `/home/ubuntu/java/devrun/*` và
`/home/ubuntu/kaggle_sim/out/*` thỏa: ngày đầu `20210701` **VÀ** ngày cuối `20251230` **VÀ** ≥1640 điểm; run trùng chuỗi
equity gộp làm 1. `R4`/`B*` (base) luôn trong pool. `r_t = eq_t/eq_{t−1}−1`; `SR` = mean/std(ddof=1) theo NGÀY (báo
kèm `×√365`); skew/kurt (scipy Pearson). `V[SR]` = variance(ddof=1) SR ngày giữa các run; `ρ̄` = tương quan Pearson
ngoài đường chéo (cùng trục ngày); `N_eff = N/(1+(N−1)ρ̄)`;
`SR0 = √V·((1−γ)Φ⁻¹(1−1/N)+γΦ⁻¹(1−1/(N·e)))`, `γ=0.5772156649`;
`DSR = Φ((SR−SR0)·√(T−1)/√(1−skew·SR+(kurt−1)/4·SR²))`. Báo **`R4` và `B*`** cho `N ∈ {5, 10, 50, 200, 448}` + `N_eff`
(chính) + `N` thật của pool, kèm `PSR(SR0=0)`. **Biến thể bổ sung (mô tả):** pool thu hẹp = **5 arm `p2` @cùng cost base**.

**Tiêu chí (chốt):** `R4` **PASS T3** ⇔ `DSR ≥ 0.95` ở **cả** `N_eff` (chính) **và** `N=5` (= k khoá trước của Phase 2).

## 4. T4 — PLACEBO: "cùng phút vào, coin NGẪU NHIÊN" (harness replay thoát của `RESULT_EXIT_FIT`)

Leg = dòng `level == PREDICT_SYMBOL_TRADE` của `R4` @base (**kỳ vọng 1745**). `t0` = `start` (GMT+7 → UTC ms),
`margin` = cột `margin`, `symbolPred` = của leg. Đo 1 leg đơn (không DCA/merge, không funding):
`entry = close nến 1m tại t0`, `qty = margin/entry`, `gross = qty·(priceTP−entry)/margin`, `net_f = gross − f`,
`f = 0.006` (chính) và `0.008` (phụ). Luật thoát = **P0 engine `exit_engine.simulate`** (arm `0.07`, định `HIGH`,
`gap=min(peak·0.5, cap 0.03/0.08 theo symbolPred>0.29)`, ratchet liên tục, time-stop 168h, delist guard, `OPEN_AT_END`).

- **THẬT** = coin thật đo bằng **cùng engine/luật** (để THẬT/P1 cùng một thước). Báo kèm `pnl/margin` thực của sim (chỉ tham chiếu).
- **P1 (placebo)** = **GIỮ ĐÚNG PHÚT VÀO** `t0_i`, thay coin bằng coin ngẫu nhiên từ **universe đủ điều kiện tại `t0_i`**:
  symbol đuôi `USDT` có nến tại đúng phút `t0_i`; đã xuất hiện trong dữ liệu **≤ `t0_i − 30 ngày`** (quét từ `2021-06-01`;
  có mặt `2021-06-01` ⇒ coi là niêm yết ≤ `2021-06-01`); **KHÔNG** đang được `R4` giữ tại `t0_i` (giữ = có cụm
  `(sym,end)` với `leg_đầu.start ≤ t0_i < end`); coin thật tự động bị loại. Mỗi leg `i` rút `D` lần
  (`coin = eligible(t0_i)[⌊u·n⌋]`).
- **RNG:** `np.random.default_rng(20260928)`; thứ tự sinh cố định theo leg (i tăng dần), `D` biến thể.
  **`D` chốt sau đo tốc độ chunk đầu** (ghi log): `D = 200` nếu ước tính CPU ≤ 90 phút & RAM ≤ 6GB; nếu vượt ⇒ `D = 100`.
- **Chỉ tính P1** (không P2): D5 chốt placebo = "cùng phút vào, coin ngẫu nhiên".
- **CI:** bootstrap **khối 72h theo phút vào** (NREP 2000, seed `20260905`) cho `net_f`/leg: chênh `THẬT − P1` (paired
  theo khối) và điểm `mean(THẬT) − mean(P1)`. Báo cả 2 mức phí.
- **Thước phụ (mô tả):** `wl_ratio`, `tf_5`, `loss_mean`, `conc_5` (`tail_robust_rulers` định nghĩa) cho THẬT vs P1.

**Tiêu chí (chốt):** `R4` **PASS T4** ⇔ `mean(net_f)` THẬT **>** `mean(net_f)` P1 **VÀ** CI95 chênh (`THẬT − P1`) **không chứa 0**
(điểm > 0, cận dưới > 0), ở **mức phí chính** `f=0.006`. `f=0.008` báo kèm (không dùng để PASS/FAIL).

## 5. LUẬT KẾT LUẬN (chốt TRƯỚC)

- **`R4` xứng đáng lên Phase 4 (holdout 2026)** ⇔ **PASS CẢ 4 test** ở **@base**, và **KHÔNG FAIL** (PASS hoặc trung tính)
  cùng test ở **@stress** (tức trạng thái 4 test @stress giống @base, hoặc chỉ khác ở chiều *không làm xấu* kết luận).
- **Ngược lại ⇒ KHUYẾN NGHỊ TRẢ VỀ GIỮ `B*`** (không lên Phase 4 ở lượt này).
- Cờ đỏ bắt buộc nêu rõ dù PASS: (a) CI chênh `R4−B*` **chứa 0** (biên `+0,7…0,95 %` là nhiễu); (b) `gate 1.55` **nới nhẹ**.
- Kết luận phải DỨT KHOÁT theo số, không "vừa…vừa".

## 6. NGUỒN SỐ + ĐỐI CHIẾU ĐÃ CÔNG BỐ

`RESULT_RESET_RULE_P2.md` (`R4` là arm DUY NHẤT qua 4 tầng @base+stress; biên Calmar `+0,95 %`/`+0,71 %`),
`RESULT_EXIT_FIT.md` (harness PASS; T170 md5 `efb793e2`), `PREREG_INCUMBENT_ROBUST.md` §1–§4 (định nghĩa 4 test).

## 7. CHI TIẾT KỸ THUẬT (executor điền — cách chạy, KHÔNG đổi tiêu chí)

- Script: `research/analysis/reset_rule_p3.py` (T1–T3 + T4), dùng lại `research/analysis/reset_rule_score.py`
  (`load_legs/load_daily/episode_drop3/tail_metrics`) và `research/exitfit/exit_engine.py` (`simulate`, đã PASS parity).
  Cache placebo (nến 1m) **ngoài repo**: `/home/ubuntu/rr_p3_cache/` (tự dọn).
- Dữ liệu 1m: `/home/ubuntu/kaggle_data_hpo/ticker_YYYYMMDD.bin.gz` (nguồn sim, `TICKER_SOURCE=file`), parse `jbin.py`.
- Trung gian/output: JSON `docs/result/reset_rule_p3.json` (nhỏ) + doc `docs/result/RESULT_RESET_RULE_P3.md`.
- Tài nguyên: `nice -n 10`, `free -g` check trước; output tool nhỏ. 0 run/0 train trên Oracle.

## 8. NGUỒN DỰ BÁO (ghi trước, để đối chiếu — KHÔNG dùng chọn)

1. **T1:** `R4` khả năng **PASS** (P2 đã báo "bỏ top-3 episode > 0 mọi arm"); câu hỏi là top-5 và `Calmar_còn` vs `B*`.
2. **T2:** kỳ vọng CI chênh `R4−B*` **CHỨA 0** (biên < 1 %) ⇒ biên là nhiễu (đúng cảnh báo P2 §7.1).
3. **T3:** nghi ngờ `DSR` **thấp** (nếu `V[SR]` lớn do pool trộn nhiều cấu hình yếu) ⇒ có thể FAIL.
4. **T4:** kỳ vọng THẬT **>** P1 nếu "chọn coin" có giá trị; nếu chênh ~0 ⇒ giá trị đến từ TIMING/coin-chọn khác biệt.
