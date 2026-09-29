# RESULT — FEAT_CUT_RVOL15M (cắt feature rvol15m trên nền G2+FLAT3): DỪNG ở cổng tầng model

Pre-reg: `docs/prereg/PREREG_FEAT_CUT_RVOL15M.md` (md5 `445c4528ea322d38476f7a48f9bcb35d`, commit `76d9ba06`, chốt TRƯỚC khi có số).
Executor: Claude Opus 4.8 (agent). Số thô: `docs/result/RESULT_FEAT_CUT_RVOL15M.json`. Code: `research/analysis/featcut_model_tier.py`, `featcut_gain.py`, `featcut_assemble.py`.
DEV ≤ 2025-12-31 (16 fold OOS 2022-01..2025-12). Không đụng 2026 / 242 / shadow-c3. Không ghi đè data dir đang dùng.

## 0. KẾT LUẬN (rủi ro trước)

1. **Cổng tầng model: KÉM RÕ ⇒ DỪNG, KHÔNG sim** (đúng luật pre-reg). M_cut (44 cột) mất |rank-IC| và lift@8 so với M_base (45 cột, chính là bins B0 đang dùng), CI block-72h nằm hẳn phía bất lợi ở cả hai thước. ⇒ **GIỮ rvol15m** ở tầng model.
2. 🔴 **Điểm mơ hồ của pre-reg (phải MASTER xác nhận):** rank-IC của `p0` ÂM ở cả 16 fold cho cả 3 model. Câu chữ "CI ΔrankIC không âm ngoài 0" đọc theo dấu THÔ (IC_cut − IC_base = **+0,0020**, CI [+0,0013, +0,0027] dương) sẽ thành "TỐT hơn rõ ⇒ sim + P3" — ngược hẳn. Tôi đọc theo **chất lượng = −IC (|IC| lớn = tốt)**, vì (a) IC âm là cấu trúc ở mọi fold/model, (b) **lift@8 (không phụ thuộc dấu) cùng chiều: −0,0027 [−0,0037, −0,0017]**, (c) vòng ARM44 cũ đã đọc như vậy. Nếu MASTER muốn đọc khác, số thô đầy đủ ở JSON. Lưu ý: hướng đọc này KHÔNG chọn sau khi thấy kết quả của quyết định mới — số A44 đã có từ 09-25 và MASTER đã biết (pre-reg §BỐI CẢNH); nhưng vẫn là một diễn giải luật sau sự kiện, nên khai rõ.
3. 🔴 **Giới hạn cổng (không được đọc thành "cắt rvol15m chắc chắn tệ ở sim"):** tầng model đo thước selector (xếp hạng `p0` net015). SIM lấy **thứ tự coin từ S1**, chỉ lấy từ model này multiset `P(win)` cho **gate** (RESULT_ARM44 §10.2). Ở nền T170 cũ: tầng model xấu đi đo được nhưng **sim NULL** (0/5 rate ngoài CI, maxDD/UW không xấu hơn). Cổng này vì vậy **chặn đúng phép đo mà sim cũ thấy vô hại**. Trên nền G2 gate rộng (n ~2.500) chưa ai đo lại — **sim C_cut không chạy** ⇒ câu hỏi "gate rộng có đổi verdict sim?" **CHƯA TRẢ LỜI**.
4. FLAT3 đã chốt vào B0: parity **650c386f0d0dfea334af9d55ca2f21d4 PASS (n 2517, eq 131 908)**.

## 1. BƯỚC 0 — chốt FLAT3 (`profiles/g2_flat3.properties`)

= `r4_kg0_k16_f015_g155` + gate ratio (`SIM_GATE_ROLLING_MODE=ratio`, `DAYS=90`, `PCT=0.999950829`) + FLAT3 (`TS_GIVEBACK_RATIO=1.0`, `SIM_TS_MAX_GAP=0.03`, `SIM_TS_MAX_GAP_WEAK=0.03`), giữ `SIM_RATE_PROFIT_STOP_MARKET=0.07`.
Sinh bằng `mk_g2_flat3.py` (đối chiếu key-by-key với `prof_run.properties` của kernel `trail2-g2-flat3`: 30 key, diff = {}).
Validate: sim đúng file profile này trên Kaggle (kernel `chuyendinh/sim-g2flat3-val`; bundle `sim-x1-2021-bundle`, jar `sim-jar-gdv2` sha `7368be46…`, profile đưa qua dataset nhỏ `sim-prof-g2flat3`, `SIM_END_DATE=20251231`).
**KẾT QUẢ: PASS.** printDone md5 = 650c386f0d0dfea334af9d55ca2f21d4 (= FLAT3 vòng 2 `trail2-g2-flat3`), n 2517, equity 131 908, symbol_mapper 863, jar 7368be46edb3fa387a41585bea18feb81ab812ebabdc9ff245f6d25947a82d6a, `PROFILE_HASH` c47b73f3133521a1 (trùng vòng 2). File profile đã được commit ở `a1008f35` (trước khi validate; bản sinh lại byte-identical với HEAD, nên KHÔNG có commit profile mới) — parity này xác nhận đúng file đó. Baseline B0 = `profiles/g2_flat3.properties`.

## 2. TẦNG MODEL — rank-IC WFO, ghép cặp, CI block-72h (2000 rep, seed 20260905, k=1 ⇒ inflate 1.0)

**Tái dùng artifact A44 (KHÔNG retrain):** 16 bin `predict_wf_*` A44/A45 trong `~/ruler_bins/g015p2-arm44-gpu/stage2/` + per-tick ruler `~/kaggle_sim/out/a44out/*_perfold_ticks.parquet` (140.238 tick, 16 fold, ≥2 coin/tick, THR 0,015, nhãn `retEnd_4h`).
**Kiểm khớp giao thức WFO hiện tại** (train < cutoff − 72h purge, expanding, seed 42, n_estimators 400, depth 5, lr 0,05, nhãn net015 thr 0,015, xgboost 3.2.0 GPU — cùng recipe `g015x26_train.py`/F0):
- `n_train/pos/spw/n_oos` 16 fold khớp tuyệt đối A45↔A44 (`CROSS_ARM_OK`) và khớp `RESULT_STAGE2_TRAIN` §1.
- Đối chứng retrain A45 (cùng 45 cột) ≈ deploy: ΔIC −0,00005 [−0,00043, +0,00028], Δlift@8 +0,00034 [−0,00033, +0,00100] (chứa 0); top-10 gain của A45 vs 45 gốc trùng ≤0,2pp (mục 3). ⇒ giao thức khớp, không cần retrain. Giới hạn: A45 là retrain GPU, không byte-identical với 45 gốc (đã biết từ F0).

M_base = **45 gốc `predwf_G015x26`** (đúng bins B0 dùng) [CHÍNH]; A45 = retrain cùng phiên [chẩn đoán]; M_cut = **A44**.
Định hướng: q = −IC (IC âm ở cả 16 fold, cả 3 model). Δq = q_cut − q_base.

| so (ghép cặp) | Δq = −ΔrankIC | CI95 | Δlift@8 | CI95 | đọc |
|---|---|---|---|---|---|
| **A44 − 45 gốc [CHÍNH]** | **−0,002014** | [−0,002724, −0,001289] | **−0,002735** | [−0,003666, −0,001747] | **KÉM rõ (cả 2)** |
| A44 − A45 (thuần bỏ cột, cùng phiên) | −0,001965 | [−0,002645, −0,001231] | −0,003075 | [−0,004005, −0,002141] | KÉM rõ (cả 2) |
| A45 − 45 gốc (nền nhiễu retrain) | −0,000050 | [−0,000426, +0,000279] | +0,000340 | [−0,000332, +0,001004] | không khác biệt |

Mean rank-IC: 45 gốc −0,051110 · A45 −0,051061 · A44 −0,049096. Mean lift@8: 0,11051 · 0,11085 · 0,10778. Mất ≈ 3,9% |IC| và 2,5% lift@8 (nhỏ về độ lớn nhưng ngoài CI).
Nhất quán theo fold: A44 kém hơn ở **14/16 fold** (Δq<0) và **15/16 fold** (Δlift@8<0); CI per-fold của Δq nằm hẳn dưới 0 ở 9/16 fold, không fold nào hẳn trên 0.

| fold | IC 45 gốc | IC A45 | IC A44 | Δq A44−gốc [CI95 block-72h] | Δlift@8 |
|---|---|---|---|---|---|
| 20220101 | −0,0471 | −0,0499 | −0,0452 | −0,0018 [−0,0062, +0,0024] | −0,0037 |
| 20220401 | −0,0354 | −0,0366 | −0,0376 | +0,0022 [−0,0021, +0,0069] | −0,0000 |
| 20220701 | −0,0450 | −0,0438 | −0,0419 | −0,0030 [−0,0067, +0,0006] | −0,0000 |
| 20221001 | −0,0393 | −0,0403 | −0,0365 | −0,0028 [−0,0054, −0,0002] | +0,0033 |
| 20230101 | −0,0546 | −0,0527 | −0,0512 | −0,0034 [−0,0065, −0,0002] | −0,0030 |
| 20230401 | −0,0687 | −0,0682 | −0,0678 | −0,0009 [−0,0037, +0,0018] | −0,0042 |
| 20230701 | −0,0318 | −0,0314 | −0,0320 | +0,0001 [−0,0033, +0,0036] | −0,0027 |
| 20231001 | −0,0450 | −0,0451 | −0,0445 | −0,0006 [−0,0034, +0,0022] | −0,0057 |
| 20240101 | −0,0623 | −0,0624 | −0,0592 | −0,0031 [−0,0057, −0,0005] | −0,0033 |
| 20240401 | −0,0453 | −0,0444 | −0,0414 | −0,0039 [−0,0063, −0,0017] | −0,0047 |
| 20240701 | −0,0524 | −0,0521 | −0,0500 | −0,0025 [−0,0044, −0,0005] | −0,0040 |
| 20241001 | −0,0654 | −0,0641 | −0,0613 | −0,0041 [−0,0066, −0,0017] | −0,0034 |
| 20250101 | −0,0669 | −0,0675 | −0,0649 | −0,0020 [−0,0039, −0,0002] | −0,0042 |
| 20250401 | −0,0461 | −0,0461 | −0,0431 | −0,0030 [−0,0048, −0,0011] | −0,0039 |
| 20250701 | −0,0516 | −0,0518 | −0,0498 | −0,0018 [−0,0036, −0,0000] | −0,0028 |
| 20251001 | −0,0612 | −0,0608 | −0,0597 | −0,0015 [−0,0033, +0,0003] | −0,0012 |

Đây là **cùng phép đo** ARM44 (09-25) tính lại độc lập từ per-tick parquet: khớp từng chữ số (+0,002014 [+0,001289, +0,002724] dạng dấu thô). Multiplicity: k=1 (một ablation) ⇒ không nở CI; đây là lần thử thứ ~30 trên cùng DEV.

## 3. Gain top-10 — feature nào hấp thụ rvol15m

Importance `gain` (gain TRUNG BÌNH mỗi split — đúng thước 34,09% của DIAG_RVOL15M; 16 fold DEV, `total_gain` để đối chiếu). Model 45 gốc dùng f0..f15 (f16/f17 là cutoff 2026 — không đọc).

| M_base 45 gốc (gain) | % | M_cut A44 (gain) | % |
|---|---|---|---|
| **rvol15m** | **34,23** | distFromHigh24H | 17,03 |
| distFromHigh24H | 6,84 | oi_delta24h | 9,87 |
| oi_delta24h | 6,12 | distFromLow24H | 9,56 |
| distFromLow24H | 3,74 | oi_z | 3,99 |
| taker_buy | 2,77 | taker_buy | 3,73 |
| ret15m | 2,68 | momentum1H | 3,71 |
| momentum24H | 2,34 | ret15m | 3,66 |
| relStrengthBtc24H | 2,13 | rateDown15MAvg | 3,27 |
| oi_z | 2,11 | momentum4H | 3,11 |
| momentum4H | 1,98 | momentum24H | 2,88 |

- A45 (retrain) 34,30% ≈ 45 gốc 34,23%; top-10 trùng thứ tự ⇒ retrain trung thực (mục 2).
- **Hấp thụ** (A44 − A45, pp): distFromHigh24H +10,06 · distFromLow24H +5,75 · oi_delta24h +3,94 · momentum1H +2,51 · oi_z +1,92 · rateDown15MAvg +1,82 · momentum4H +1,08 · taker_buy +0,93 · ret15m +0,90. Ba feature đầu (vị trí trong biên 24h + thay đổi OI) nhận ~20pp/34pp: là proxy biên độ/biến động, nhưng **không thay thế trọn** — IC/lift vẫn mất ngoài CI. (`total_gain` kể chuyện khác: rvol15m 28,05%, hạng 2 là basketFundingAvg 12,7% — hạng-1 rvol15m vững ở cả hai thước.)
- Diễn giải cơ chế: [SUY LUẬN] rvol15m mã hóa độ lớn/fat-tail (khớp DIAG_RVOL15M); cắt nó buộc cây dùng proxy thô hơn ⇒ xếp hạng kém đi một chút chứ không sập.

## 4. So sánh với verdict A44 cũ (nền T170) — BẮT BUỘC

| | A44 cũ (T170/KEEPLEG0, gate hẹp, n≈1.100, phí legacy) | Vòng này (nền G2+FLAT3, gate rộng, n≈2.500, nhịp 1', phí base) |
|---|---|---|
| Tầng model (Δq / Δlift@8) | −0,00197 / −0,00308 (ngoài CI, bất lợi) | **cùng artifact, cùng số** −0,00201 / −0,00274 (vs 45 gốc); −0,00197 / −0,00308 (vs A45) |
| Tầng sim | 0/5 rate ngoài CI, PnL +3,2k, maxDD/UW không xấu hơn ⇒ NULL | **KHÔNG chạy** (cổng chặn) |
| Quyết định | GIỮ 45 | GIỮ 45 |

- Tầng model **không phụ thuộc gate/nền** (chỉ đo model ↔ nhãn) nên kết quả trùng cũ là hiển nhiên, **không** phải bằng chứng mới. Phần "gate rộng có đổi kết luận không" nằm ở tầng sim — chưa đo.
- [SUY LUẬN, chưa kiểm] lý do sim cũ NULL (sim chỉ dùng multiset P(win) cho gate, thứ tự coin từ S1) vẫn đúng ở G2 (gate ratio W90 cũng chỉ đọc P(win)) ⇒ nhiều khả năng sim G2 cũng NULL; gate rộng chỉ khuếch đại nhiễu hiệu chuẩn (n lệch ±vài %). Cần đo mới kết luận.

## 5. Việc treo / khuyến nghị

1. **Chọn hướng đọc dấu IC** (mục 0.2) — MASTER xác nhận; nếu đọc khác, sim là bắt buộc.
2. Nếu MASTER muốn trả lời "gate rộng G2 có đổi verdict sim" dù cổng model chặn: amendment pre-reg (gán nhãn exploratory, không đổi verdict tầng model). Hạ tầng sẵn: bins A44 (`~/ruler_bins/g015p2-arm44-gpu/stage2/A44`) + `research/analysis/s3_kernel.py`/`arm44_sim.py` (dựng lại funding.bin byte-faithful, map S1) — cần sửa 3 chỗ: jar từ `sim-jar-gdv2`, profile `g2_flat3` (dataset `sim-prof-g2flat3`), kèm kênh `moc` để parity 650c386f. Ước ~30–45 phút Kaggle CPU/arm, 0 quota. **Chưa làm.**
3. 2 fold 2021 không có A44 (16 fold 2022+ only) — kết luận chỉ nói 2022+.
4. Đây là test #~30 trên cùng DEV; effect nhỏ (≈4% |IC|) nhưng nhất quán 14/16 fold.
