# ENTRY-ALPHA — STATE & PLAYBOOK (chốt 2026-07-29, nối thêm 2026-07-30)

> Đọc TOP-TO-BOTTOM là hiểu: ĐANG Ở ĐÂU, TẠI SAO tới đây, LÀM GÌ TIẾP — không chỉ facts rời.
> Đây là doc nối-mạch chính cho session mới. Chi tiết số liệu: `gate_freq_ablation_20260727.md §A–§O`.
> Nguyên tắc xuyên suốt: đo-không-đoán · pre-register ngưỡng · verdict/PnL/commit thuộc Uni.

---

## 0.-1 CẬP NHẬT 2026-07-30 — ĐỌC TRƯỚC KHI XUỐNG §0 (verdict M gốc, vẫn ĐÚNG, không đổi)

> §0-§11 dưới đây là verdict M chốt 2026-07-29, KHÔNG bị phủ nhận. Đoạn này nối thêm 1 ngày làm
> việc: bước 1 của §6 NEXT đã xong, rồi phiên RẼ HƯỚNG sang exit-formula theo yêu cầu Uni, trước
> khi làm tới bước 2-3 gốc.

**Bước 1 (§6.1 gốc) — audit constraint `TOO_MUCH_CAPITAL_LOCK` + `TOO_FEW_TRADES` — XONG
(read-only).** Report đầy đủ: `reports/AUDIT_20260730_wfo_constraint_harness.md`. Tóm tắt:
- **L1 (bug thật, ordering inversion):** reject ramp `TOO_FEW_TRADES` ∈ (−100000, 0) nằm **cao
  hơn** mọi reject khác (`CAPITAL_LOCK` ≈ −100002) → giữa 2 genome bị reject, HPO chọn genome
  1-lệnh thay vì genome đang lãi nhiều lệnh.
- **L2 (cưỡng chế đánh lướt):** khi `CAPITAL_LOCK` bind hết sample trong 1 window, argmax rơi về
  "genome giữ vốn ít nhất" — Calmar bị loại khỏi bài toán chọn → **harness CHỦ ĐỘNG chọn genome
  đánh lướt** (6/17 gene HPO là exit param). Tức "đánh lướt" không chỉ do label 6%, mà bị fitness
  cưỡng chế — khớp đúng câu hỏi Uni đặt ra ngay sau khi đọc report này.
- **Định lượng:** 8/13 window non-w15 bị `CAPITAL_LOCK` loại, Σ net các window đó
  **+9 277.19 DƯƠNG TOÀN BỘ** — bằng chứng trực tiếp cho câu "harness loại nhầm window đang lãi"
  ở §2(i) bên dưới. Pre-register: sửa `CAPITAL_LOCK` riêng → 9/13 = 69.2%; + hạ sàn min-trade →
  10/13 = 76.9%.
- Đề xuất nới có nguyên tắc P0-P6 đã viết trong report — **CHƯA áp dụng**, chờ Uni chốt.

**Exit machine — 2 lỗ hổng cấu trúc mới, ngoài kế hoạch §6 gốc** (Uni hỏi giữa buổi về hành vi
"đánh lướt" ở tầng exit): `reports/EXIT_MACHINE_20260730_stop_schedule.md` PHẦN 1.
- Dead zone: sau arm (~1.03% cũ), SL đóng băng tới ratchet (~5.39% = arm×5.21847) — có bước nhảy
  siết chặt 41% NGAY tại điểm đó.
- `gap = min(peak×giveback, TS_MAX_GAP)` bị NGƯỢC dấu: tỉ lệ nhả lãi co lại khi lệnh lãi CÀNG
  lớn → cắt mất đuôi x2/x3. Cần `max(peak×giveback, minGap)`. **CHƯA sửa** (P6 riêng).

**RẼ HƯỚNG (07-30 tối, theo yêu cầu Uni):** đọc xong audit, Uni hỏi trực tiếp về "đánh lướt" ở
exit → phiên chuyển từ "làm tiếp §6 bước 2" sang điều tra + sửa exit-formula (min-rate SL,
ratchet). **Bước 2, 3 của §6 gốc (fix fitness mismatch, bỏ HPO argmax) VẪN CHƯA LÀM** — tạm dừng,
không phải bỏ.

**3 việc đã làm + commit (nhánh exit-formula):**
1. `3e66898` — `RATE_PROFIT_STOP_MARKET` 0.01032→0.03 (`Configs.java` production default + sàn
   gene `StrategyWfoTask.java` 0.020→0.03). Khớp *đúng* 1 sweep đã đo từ 2026-07-07 mà chưa từng
   được áp dụng: `reports/trailing_stop_sweep_139.md` (TASK-139) — nâng 0.01032→0.03032 cho PnL
   2.4×, calmar 2.3×, maxDD không đổi. Khuyến nghị đó nằm im 3 tuần trong report, chưa vào code.
2. `ccc05dc` — đồng bộ 2 gene range cũ (`WFORunner.java`, `SensitivityTool.java`) còn kẹt vùng
   cắt-non [0.012-0.025]/[0.005-0.025] → 0.03-0.05. Cả 2 KHÔNG nằm trên đường production (chỉ
   `StrategyWfoTask` được `orchestrator/pipelines/*.json` gọi) — sửa để hết là ví dụ sai.
3. `b203a78` — thêm `Configs.TS_RATCHET_DECOUPLED` (env, mặc định **false = hành vi cũ y
   nguyên**), bỏ hệ số `TS_PROFIT_MULTIPLIER` ở `updateTPSL` khi bật, xoá dead-zone giữa arm và
   ratchet. **Chưa bật thử — chưa có run nào đo tác động thật.**

**CHẶN — N=13 window confirm chưa bắn được.** Jar build+deploy xong
(`binance-exit003-20260730.jar`, md5 verify OK). Nhưng job store Aerospike dùng chung cho fanout
(`103.157.218.226:3222`) đang có `DONE=7 FAILED=9/16` (`EOFException` batch-read), KHÔNG cô lập
theo tag ở tầng Aerospike → bắn lại có thể đụng đúng 9 window đang fail, chưa rõ coordinator
retry sạch hay không. **Đã hỏi Uni cách xử lý, CHƯA có câu trả lời khi phiên trước kết thúc.**

**Nguồn đầy đủ:** `reports/HANDOFF_20260730_exit_min_ratchet.md`.

---

## 0. MỤC TIÊU & RÀNG BUỘC
- **Mục tiêu:** chiến lược **long-only retail ≥20%/năm robust**. Short đã chứng minh NOT_VIABLE (bottom-decile short lỗ) → chỉ còn long.
- **Production:** 2 process live trên 242 — **OFF-LIMITS, tuyệt đối không đụng**.
- **Compute:** Oracle (1 box, chạm qua `orchestrator/ce.cmd`, disk 89%) + Kaggle fleet (5 kernel CPU, đã self-contained `TICKER_SOURCE=file`).

## 1. KIẾN TRÚC CHIẾN LƯỢC (4 mảnh — hiểu để biết đang sửa cái nào)
- **SELECTOR:** cross-sectional ranker, chấm mỗi coin `P(win)` mỗi timestamp. `score = 1 − P(win)` (thấp = tốt). **ĐÃ validate: xsecIC 18/18 quý** — rank-skill là thật, không phải fluke.
- **GATE (lọc khi nào được vào lệnh) — 3 tầng absolute, đều nhạy regime:**
  1. `predict != null` coverage (Task 156, giết 2021/2022 vì thiếu pred).
  2. `MIN_MOMENTUM_15M` — momentum thị trường, là **gene HPO** range [0.010, 0.045].
  3. selector-score **absolute threshold** (leg `PREDICT_SYMBOL_TRADE`): `score > maxThres → cắt`, maxThres = `PREDICT_SYMBOL_RATE_MAX_THRESHOLD × AI_DYNAMIC_MAX ≈ 0.32` (Probe A).
- **EXIT:** trailing (nuôi lãi, DCA off) = exit DƯƠNG duy nhất. hard-SL/TP first-touch đã chết.
- **WFO/HPO HARNESS:** 17 window (train 12m IS + test 3m OOS). Mỗi window: HPO thử N genome, chọn best theo IS-fit, test OOS. `WFE = oosPnl/isPnl`. Pre-register PASS = WFE median ≥0.5 & %OOS-SUCCESS ≥70% & maxDD ≤50%.

## 2. HÀNH TRÌNH LÝ LUẬN (câu hỏi → thí nghiệm → kết quả → bước kế)
Đọc phần này để KHÔNG đề xuất lại cái đã loại.

**(a) Xuất phát:** WFO FAIL, 8/17 window ZERO_TRADES. Edge "có nhưng không monetize".

**(b) Edge có robust không?** track-a-lite (fixed SL/TP first-touch) âm hết; trailing WFO WFE median 0.24 + dồn hết vào w15 → *nhìn như* không robust.

**(c) 0.24 là bản chất hay artifact?** → gate ablation: hạ `MIN_MOMENTUM_15M` 0.023→0.010 → WFE nhảy **0.68**, %OOS 46→69%, PnL dàn khỏi w15. Fixed-genome cho 0.68–0.75, HPO cho 0.24. → **0.24 là HPO OVER-TIGHTENING artifact, KHÔNG phải edge chết.** Trần thật = **frequency/gate**, không phải exit. (Non-monotonic: gate→0 = BURN −55k, nên có sweet-spot ~0.010, KHÔNG bỏ gate.)

**(d) oi_z có giúp?** thử thay-gate: WFE~0, giết frequency (Q25 giết sạch 4 window). → **oi_z LOẠI dứt điểm.**

**(e) Tại sao zero-trade khi ranking vẫn hợp lệ? (Probe A)** leg selector always-on dùng **ABSOLUTE threshold**. Regime yếu → cả phân phối score dịch lên trên ngưỡng → 0 coin qua → zero-trade dù thứ hạng nội bộ vẫn đúng. → **giả thuyết: đổi RANK-based (top-K/timestamp) sẽ tự chuẩn hoá theo regime** (không starve lúc yếu, không flood lúc mạnh).

**(f) rank-K + N=30 fair-WFE:** K5 & K8 đều FAIL pre-register nhưng ở tiêu chí **đối nghịch** (K5 fail WFE 0.43 / breadth khá; K8 pass WFE 0.57 / breadth tệ 46%). HPO N=30 làm **TỆ hơn** fixed-genome (overfit w15 nặng hơn). → lúc này *nghiêng close*.

**(g) Uni phản biện (bước ngoặt):** "các quý khác vẫn nhiều tín hiệu tốt, chỉ là WFO/HPO kéo về w15 nên thành ít/no-trades". → **Probe C:** tính **PnL/lệnh** từng window → **w15 PnL/lệnh ≤ trung bình non-w15** ở mọi config → edge **RỘNG**, w15 to tuyệt đối chỉ vì **nhiều lệnh hơn** (nhiều cơ hội), không phải edge/lệnh trội. HPO argmax là thủ phạm bóp non-w15. Nhưng còn nghi **leakage** (fixed genome = param production, nguồn tune không rõ).

**(h) Step-2 (diệt leakage):** genome **đóng băng train CHỈ trên 2022** (không thể biết tương lai), apply forward w4-16. Kết quả: **11/13 window OOS non-w15 vừa winRate>50% vừa net dương sau phí**; net/trade non-w15 8.59 ≥ w15 7.97; w15 chỉ 28% Σnet. Nhánh A (frozen) **thắng** B (production) 2.34× → breadth **KHÔNG phải leakage**. → **VERDICT M.**

**(i) Bằng chứng cuối cho "harness là thủ phạm":** trong nhánh A, window fail ăn đúng `TOO_MUCH_CAPITAL_LOCK` (7) + `TOO_FEW_TRADES` (4) → **harness loại bỏ chính những window ĐANG LÃI**, không phải window đó vô edge.

## 3. ĐANG Ở ĐÂU — VERDICT M (1 đoạn)
**Selector có edge THẬT và TRẢI RỘNG nhiều quý.** Không phải gate hỏng, không phải selector kém, không phải "chỉ 1 quý w15 ăn may". Chính **WFO/HPO harness** — HPO argmax overfit w15 + fitness mismatch + constraint capital-lock/min-trades — **tự loại bỏ những quý đang lãi** và tạo ảo giác FAIL. → **KHÔNG đóng nhánh. KHÔNG build gate/model mới. Sửa harness.**

## 4. ĐÃ GIẾT (đừng thử lại) + lý do
| Thứ | Kết quả | Lý do đóng |
|---|---|---|
| hard-SL/TP first-touch | âm hết | SL bị quét bởi thọt-trước-bơm |
| short bottom-decile | NOT_VIABLE | coin điểm thấp vẫn tăng tuyệt đối |
| oi_z (veto-chồng + thay-gate) | WFE~0, giết frequency | frequency destroyer |
| endpoint (hard exit) | alpha~0 sau cost | rank skill không thành return ở endpoint |
| offset-sweep (bỏ top-rank) | net GIẢM đơn điệu | top-K CHÍNH LÀ edge, không phải fake-pump |
| gate <0.010 | tệ hơn 0.010 | sweet-spot ~0.010; gate→0 = BURN −55k |
| HPO N=30 argmax | overfit w15 (lặp 3×) | fixed/frozen genome generalize tốt hơn |

## 5. MENTAL MODELS (giữ để không đi lạc)
1. **HPO trên hệ này overfit vào window vol cao nhất (w15).** Fixed/frozen genome > HPO argmax. Đã lặp 3 lần (WFE-0.24-gate, K5-re-tune-tệ-hơn, K8-breadth-sụp).
2. **Σ absolute PnL là metric LỪA** — w15 (nhiều lệnh) nuốt phần còn lại. Phải nhìn **PnL/lệnh** và **per-window normalized**, không nhìn Σ$.
3. **"Nhiều tín hiệu" ≠ "nhiều lệnh".** Frequency probe: gate admission CÓ ở mọi window; lệnh bị cắt **downstream** bởi capital-lock/min-trades → đó là chỗ sửa.
4. **rank-K tự chuẩn hoá regime tốt hơn absolute threshold** (gate là lưỡi dao dốc ~exp: dịch tí là frequency đổi 10×).
5. **Leakage là rủi ro thật** khi dùng param production nguồn không rõ → mọi verdict "edge rộng" phải kiểm bằng genome frozen train-trên-past.

## 6. NEXT — LÀM GÌ (thứ tự rẻ→đắt, mỗi bước có gate dừng; KHÔNG làm cả 3 rồi mới test)

> **Trạng thái 2026-07-30 tối: bước 1 XONG, bước 2-3 CHƯA làm (tạm dừng, không phải bỏ) — xem
> §0.-1 để biết vì sao rẽ hướng và nhánh exit-formula đang tới đâu.** 2 nhánh đang mở song song,
> Uni chọn làm nhánh nào trước (không chạy 2 job nặng cùng lúc trên Oracle):

1. ~~**[READ-ONLY trước] Audit constraint `TOO_MUCH_CAPITAL_LOCK` + `TOO_FEW_TRADES`**~~ —
   **XONG** (`reports/AUDIT_20260730_wfo_constraint_harness.md`), xem §0.-1. Kết quả: L1
   (ordering bug) + L2 (fitness cưỡng chế đánh lướt) + định lượng 8/13 window bị loại nhầm.
   Đề xuất P0-P6 đã viết, CHƯA áp dụng.
2. **[CHƯA LÀM] Fix fitness mismatch (§K):** HPO CHỌN genome bằng `Calmar×factor` nhưng CHẤM bằng `raw-PnL-WFE` → genome được chọn không tối ưu cái ta đo. Align chọn=chấm; cân nhắc bật lại `posYearRatio≥0.80` (đang TẮT cho window 12 tháng).
3. **[CHƯA LÀM, chỉ nếu 1+2 chưa đủ]** bỏ per-window HPO argmax → genome gần-cố-định / regularized. Đây là thay đổi lớn nhất; argmax là nguồn gốc overfit w15.
4. **[CHƯA LÀM] Sau MỖI bước: N=30 full 13-window non-w15 confirm.** Mọi số verdict M hiện tại là **N=1 shape** → CHƯA production-ready cho tới khi N=30 pass trên harness đã sửa. Nếu đổi metric/fitness thì **re-pre-register + held-out** (chọn trên window lẻ, xác nhận chẵn) để tránh p-hacking.

**NHÁNH SONG SONG (exit-formula, mở ra từ 07-30 tối theo yêu cầu Uni — xem §0.-1):**
5. Giải quyết chặn N=13 confirm cho thay đổi min-rate 0.03 (job store Aerospike đang FAILED
   9/16 — kiểm tra lại trước, đừng bắn thẳng fanout 6-node).
6. Sau khi N=13 confirm chạy xong: bật thử `TS_RATCHET_DECOUPLED=true` — 1 confirm RIÊNG, đừng
   gộp 2 biến (min-rate + ratchet) vào 1 lần đo.
7. Sửa `gap = min(...)` → `max(...)` (giveback đảo dấu, P6 trong AUDIT doc) — chưa làm, việc
   cuối của nhánh exit.

## 7. CONFIG TỐT NHẤT HIỆN TẠI (điểm xuất phát khi sửa harness)
`MIN_MOMENTUM_15M=0.010` · oi_z **OFF** · selector **rank-K8** (top-8/timestamp) · exit **trailing** · **DCA off** · **funding-fee ON** (`SIM_APPLY_FUNDING`) · `TICKER_SOURCE=file` · dataset selector `wfo_ds_ret2wf_4h_ff`.

> ⚠️ **Cập nhật 07-30:** `RATE_PROFIT_STOP_MARKET` default đã đổi 0.01032→**0.03** (commit
> `3e66898`, xem §0.-1) — số này KHÔNG có trong bảng config verdict M gốc trên vì lúc đó là
> 0.01032. Bất kỳ WFO/confirm chạy SAU 07-30 tối đều dùng default mới, KHÔNG cần set env gì
> thêm. `TS_RATCHET_DECOUPLED` vẫn mặc định `false` (chưa đổi behavior).

## 8. HẠ TẦNG & VẬN HÀNH (xem `INFRA_FACTS.md` đầy đủ)
- Oracle: chạm CHỈ qua `ce.cmd` (Git-ssh, key id_rsa_chuyennd). ce gọi từ main hay treo → dùng agent/Desktop Commander hoặc `bg_run` detached, hoặc PowerShell timeout LỚN.
- **Job dài = FIRE-AND-FORGET:** launch detached → verify bước đầu pass → GHI logpath/marker → THOÁT. KHÔNG poll (đốt token).
- **KHÔNG chạy 2 WFO nặng cùng lúc trên Oracle** (1 box, disk 89%, lịch sử zombie JVM). Compute nặng → Kaggle fleet.
- Kaggle: clean venv `D:\claudedata\kaggle-clean-env` (kaggle==1.6.17). Pattern jobstore-free = `VerifyOneWindow`. **Mới: Kaggle geo-block Binance API → w16/2026 fail** (dùng Oracle cho window đụng 2026).

## 9. UNCOMMITTED CODE — ĐÃ RESOLVED 2026-07-30 (review bằng agent độc lập, sửa 5 vấn đề, rồi commit 9 lần tách bạch — không còn uncommitted từ giai đoạn verdict M gốc)
- `SELECTOR_RANK_TOPK` + `SELECTOR_RANK_OFFSET`, `GATE_COUNT_ONLY`, frozen-genome inject + 6
  metric mới (winRate/avgWin/avgLoss/profitFactor/oosCostPerTrade/medianTradePnl) +
  `SIM_APPLY_FUNDING` → đã commit `f1d201f` (+ vài commit review-fix đi kèm, xem `git log
  --oneline` quanh 07-30 sáng).
- `orchestrator/tools/stage1_frozen_derive.sh` + `stage2_frozen_ab.sh` (2 script SINH RA bằng
  chứng verdict M — trước đó KHÔNG nằm trong git, nghĩa là verdict M không tái lập được từ
  history) → đã commit `81c426f`.
- jar `binance-lf-frozen-1.0.0.jar` vẫn chỉ tồn tại trên Oracle (jar build không commit vào
  git, đúng convention) — driver script đã commit nên tái tạo được jar bất kỳ lúc nào.
- **Uncommitted MỚI phát sinh sau 07-30 (housekeeping, chưa dọn, không phải việc gấp):**
  `notebooklm_ready/` (9 file staged-deleted + nhiều file tên mới), `clamp_analyze.py` +
  `NEXT_SESSION_TODO_entry_alpha.md` (sai vị trí, ở root thay vì `docs/reports/`), vài file
  `orchestrator/_*` rác, 4 thư mục `orchestrator/kernels_sl4h/*`, 4 thư mục
  `ml/funding_selector/kaggle_*`. Chờ Uni quyết dọn hay giữ.

## 10. CAVEAT / LỖ HỔNG CÒN TREO
- Mọi PnL **trước step-2 CHƯA trừ funding-FEE** (chỉ có funding-selector feature). Step-2 đã bật fee thật.
- **w16 / 2026 forward chưa có evidence** (Kaggle geo-block + Oracle zero-trade). Đây là out-of-sample gần nhất, cần bù sau.
- Verdict M là **N=1 shape**, chưa N=30.
- avgLoss nhánh A khá béo (đuôi rủi ro, DCA-like) — phải nhìn kỹ khi confirm.
- **[MỚI 07-30]** N=13 confirm cho fix min-rate 0.03 **CHƯA CHẠY** — không có số thật nào xác
  nhận tác động của commit `3e66898` lên verdict M, chỉ có sweep TASK-139 cũ (không qua
  constraint harness V4 đầy đủ). Đừng coi 0.03 là "đã confirm" khi trả lời Uni.
- **[MỚI 07-30]** Job store Aerospike fanout (`103.157.218.226:3222`) đang FAILED 9/16 window,
  nguồn gốc chưa rõ, chưa test lại xem đã hết lỗi hay chưa — kiểm tra `wfo_status` TRƯỚC khi bắn
  bất kỳ job WFO nào (không riêng N=13 confirm).
- **[MỚI 07-30]** `TS_RATCHET_DECOUPLED=true` chưa được đo tác động thật lần nào (code mới thêm,
  mặc định OFF) — đừng suy diễn nó sẽ tốt hơn chỉ từ lý luận algebra.

## 11. NGUỒN (toàn bộ)
- `reports/gate_freq_ablation_20260727.md §A–§O` (chuỗi 15 experiment đầy đủ).
- `reports/HANDOFF_20260729_entry_alpha_harness.md` (bản nối-mạch ngắn).
- `reports/HANDOFF_20260727_entry_alpha.md` (giai đoạn trước).
- `D:\claudedata\`: `probe_a_report.md`, `probe_b_fitness.md`, `probe_c_w15_dissection.md`, `step2_final_verdict.md`, `gonogo_results.md`, `rank_k_sweep.md`, `freq_probe_table.md`.
- `docs/INFRA_FACTS.md`.
- **[MỚI 07-30]** `reports/AUDIT_20260730_wfo_constraint_harness.md` (audit bước 1, L1-L6+P0-P6).
- **[MỚI 07-30]** `reports/EXIT_MACHINE_20260730_stop_schedule.md` (algebra exit đầy đủ, 3 PHẦN).
- **[MỚI 07-30]** `reports/trailing_stop_sweep_139.md` (sweep min-rate gốc, 2026-07-07, TASK-139).
- **[MỚI 07-30]** `reports/HANDOFF_20260730_exit_min_ratchet.md` (nối-mạch nhánh exit-formula).
