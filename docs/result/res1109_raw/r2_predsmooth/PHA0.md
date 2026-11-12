# R2 PREDSMOOTH — PHA 0 (khảo sát + thiết kế, CHƯA chạy thí nghiệm) — 2026-11-09

Câu hỏi owner: thay predict "tại đúng phút trước đó" bằng trung bình predict 15′/1h/4h… có khác không?
Nhãn: [ĐO] = đã chạy/đọc số; [CODE] = đọc code (worktree `~/claude_master/v12/c3live`, HEAD a48cc56c); [MEM] = từ project memory; [SUY ĐOÁN].
Artefact pha 0 (chỉ đọc, nhẹ, qua flock): `r2ps_inspect_1109.py` → `inspect_1109.log`; `r2ps_proxy_1109.py` → `proxy_1109.log`; `r2ps_bins_1109.py` → `bins_1109.log` (cùng thư mục).

## 0. Đính chính khung câu hỏi (quan trọng nhất)
- **p15 KHÔNG phải predict theo symbol và KHÔNG dùng để xếp hạng.** p15 = XGB *market-level*, 1 số/phút
  (`predictionMap: TreeMap<Long, AiPredictionData>` key chỉ là thời gian — `SimulatorMarketLevelTicker1MStopLoss.java:76`;
  live `new AiPredictionData(timestamp, return15M, riskDrawdown4H)` — `DetectEntrySignal2TradeNormal.java:378-384`). [CODE]
- **Xếp hạng top-K24 dùng `symbolPred` = score selector S1 (bins `predict_wf_*.bin`, mốc 15′, forward-fill ra mọi phút)** —
  `Sim…:428-437` (`time2SymbolPred.get(time)` → `selectCands`), `:770-787` (top-K = K phần tử đầu đã sort). [CODE]
- **p15 chỉ đi vào GATE** (và điều kiện "có pred" cho mọi leg). Exit KHÔNG dùng p15: `TradeUtils.java:107-113` (giá trị bị bỏ qua, FROZEN v1). [CODE]
- `predictionSymbol` trên 242 = `symbol2FundingPred` (score selector theo symbol, ghi ở nhịp selector) — `DetectEntrySignal2TradeNormal.java:1098-1100`;
  p15 live được ghi riêng: Aerospike `saveAiPrediction1M` (`:382`) + file `storage/data/prediction/<ngày>/<ts>` (`:659`). [CODE]
- ⇒ "Trung bình p15" = **ĐỔI GATE (timing)**, không thể "giữ gate, chỉ đổi xếp hạng". Nếu owner thật ra muốn trung bình *score selector*
  (predictionSymbol) thì là đề tài KHÁC (xem §4 ghi chú). **MASTER cần xác nhận với owner đang hỏi cái nào.**

## 1. Selector/gate dùng predict nào lúc vào lệnh
### Sim (Kaggle, jar `SimulatorMarketLevelTicker1MStopLoss`)
- Vòng phút `time`; pool ứng viên = top-24 của `time2SymbolPred.get(time)` (`:428-437`), bỏ coin đang giữ trước gate (`:460`).
- `createOrderBUY`: `predict = predictionMap.get(ticker.startTime)` (`:1496`), null ⇒ return (`:1500-1503`);
  `bookFull` (skipFull) `:1513-1515`; `aiRejectFilter.entryGate(predict, symbolPred, PREDICT, bookFull, selRank)` `:1523-1524`.
- Gate: `AIRejectFilter.java:91-134` → `GateRollingRatio.threshold` (`GateRollingRatio.java:115-128`):
  `r = p15 / (max(0.26787, sp/0.15·1.2876)·gs)`; `q_t = GateRatioBuffer.addAndQuery` (`GateRatioBuffer.java:42-51`, quantile pct 0.999950829
  của r ứng viên trong [h−90d, h), tính lại mỗi giờ, warm-up 7d, `:72-82`) ⇒ PASS ⇔ `!(p15 < q_t·factor·gs)` (`EntryGate.java:184-199, 211-213`).
- Leg DCA_LEVEL1 cũng qua `entryGate` với `sp=null` ⇒ ngưỡng phẳng `MIN_MOMENTUM_15M`=0.008 trên CÙNG p15 (`AIRejectFilter.java:96, 114-121`). BIG_DOWN không qua gate (`Sim…:1506`). [CODE]
### Live (v1.2 c3-live = cùng `DetectEntrySignal2TradeNormal`, không có runtime entry riêng — `c3live/runtime` không gọi entryGate) [CODE]
- p15 tính mỗi tick từ feature snapshot (`:353-386`); entry: `new AiPredictionData(ticker.startTime, return15M, …)` → cùng `entryGate` (`:1208-1225`).
- Nhịp selector theo `LIVE_ENTRY_GRID_MIN` (`:156-168`, `:1524`); env 242 snapshot 10-03 có `LIVE_ENTRY_GRID_MIN=1` (`~/claude_master/1003/c3live/parity/out/242_env.txt`).
  Env v1.2 hiện tại KHÔNG kiểm (không vào 242). [ĐO snapshot cũ]
### Phút/lag
- Key p15 = `ticker.startTime` = mốc mở của nến 1′ VỪA ĐÓNG; lệnh vào ở `priceClose` của chính nến đó ⇒ **lag 0 phút đầy đủ** (p15 dùng dữ liệu tới close phút quyết định). Live tính sau khi phút đóng (guard chờ tới giây +20). [CODE; đồng bộ feature live↔backtest 100 % theo parity 10-20 — MEM]
### Feature của p15 đã có cửa sổ dài chưa?
- 33 feature V3FULL (`ml/gate/train_gate_fold.py:23-31`): momentum 1M/5M/15M/1H/4H/24H, volatility 1M/15M/1H/24H, basketMomentum 15M/1H, funding 24H, RSI14, lịch… ⇒ **model đã thấy cửa sổ 15′/1h/4h**; nhãn = TB max-upside 15′ của 60 coin losers. [CODE/MEM]
- GATE_ABLATION: G-RULE `−momentum15M` (1 cột) ≈ model 33 cột (ΔCAGR22 +3,0, CI rất rộng) ⇒ p15 về bản chất ≈ tín hiệu cửa sổ 15′. [MEM, RESULT_GATE_ABLATION.md]
- ACF p15 (pred.bin DEV, 2,50M phút) [ĐO]: lag1 0,963 · lag5 0,914 · lag15 0,832 · lag60 0,693 · lag240 0,563 ⇒ p15 đã khá mượt ở thang phút; mean15 gần như thừa về nhiễu, mean60/240 là đổi tín hiệu.

## 2. Dữ liệu predict lịch sử
- `pred.bin` = `[count:int]` + count×`[ts:long][p15:float][risk4h:float]` big-endian (`WfoDataset.java:26`), **độ phân giải 1 PHÚT**. [CODE+ĐO]
  - DEV `~/wfo_ds_x1_2021/pred.bin`: 2 500 260 phút, 2021-03-31 17:00Z → 2025-12-31 23:59Z, 0 gap, 0 NaN. [ĐO]
  - Bundle `sim-ho26a-bundle/pred.bin` (md5 22f69456 = `want_pred_base`): 2 760 442 phút tới 2026-06-30 16:59Z, 1 gap 39′. [ĐO]
  - 8 seed gate cho B0 hiện hành (`n4f-b0-*`, market `nt-chain-y26`): `pred_s{42,7,13,21,99,123,777,2024}` md5 482f764e/37982fd9/258bc7d9/6b3aff7f/0b5df665/635f1f59/b2231aa8/43abd92a — **chỉ trên Kaggle** (output kernel), phủ tới 2026-09-30; bản `~/claude_master/1003/ho1/gate/pred_s*` trên Oracle là bản CŨ khác md5. [ĐO]
- ⇒ **Đủ để tính mean 15/60/240 causal không lookahead, KHÔNG cần tính lại p15 trên Kaggle.** Biến đổi = numpy vài giây/seed (44 MB). Cơ chế thay pred có sẵn: khối `pred_ds` trong `run.py` (GATE_ABLATION; vd `~/kaggle_sim/a0p-x14-s42/run.py:139-180`, kiểm md5 + viết lại manifest).
- Score selector (bins): mốc 15′ (`predict_wf_20250401.bin`: 8 736 tick, Δ=900 000 ms), forward-fill ra phút (`WfoDataset.java:124-132, 289-300`). Top-24 giữ lại ~75 % giữa 2 mốc 15′ liên tiếp (cùng giờ 0,741, qua giờ 0,729). [ĐO]

## 3. Thí nghiệm tương tự trước đây (phân biệt với đường đã đóng)
| đề tài | đổi gì | kết quả | khác R2 ở đâu |
|---|---|---|---|
| ENTRY_CONFIRM A (3e17ba3e) | chờ nhịp +2 % sau đáy (trễ vào) | −27,7k/seed, 0/8 ⇒ ĐÓNG; "edge = vào ĐÚNG phút cực trị" | R2 không thêm điều kiện giá; nhưng mean p15 cũng gây TRỄ (xem proxy) ⇒ cùng rủi ro |
| MKT_UP/MKT_UP2/MD_STRAT/UP_TRIG | model/trigger hướng thị trường mới | ĐÓNG | R2 không thêm model, chỉ lọc thời gian p15 cũ |
| GATE_ABLATION G-H60 (36a60481) | nhãn gate 60′ (retrain) | ΔCAGR22 −2,78, NO-GO, giữ 15′ | H60 đổi NHÃN/model; R2 giữ model, đổi hậu xử lý |
| GATE-RECAL (`SIM_GATE_P15_Q`, EntryGate.java:72-155) | ngưỡng = quantile cuộn p15 | (đã thay bằng GDV2 ratio) | đổi ngưỡng, không làm mượt tín hiệu |
| R4_CADENCE C1 (`SIM_ENTRY_SAMPLE_MIN=15`) | selector 15′ thay 1′ | n −36,5 %, Calmar −24,2 % ⇒ giữ 1′ | gần nhất về tinh thần: thô hoá thời gian làm mất tín hiệu "fire-and-fade" |
| GATE_VZ (d2d1b090) | thêm 13 feature VZ vào gate | NO-GO | khác |
⇒ R2 CHƯA từng chạy, nhưng có 2 bằng chứng tiên nghiệm âm (ENTRY_CONFIRM, R4_CADENCE). Ledger: không trùng đường đã đóng.

### Proxy timing (market-level, KHÔNG phải gate thật; top 0,05 % phút toàn kỳ, đợt = cụm cách >60′) [ĐO, proxy_1109.log]
| arm | corr với P1 | số đợt | Jaccard phút | đợt P1 trúng | trễ trung vị (p25–p75) |
|---|---|---|---|---|---|
| P1 | 1 | 72 | 1 | 72/72 | 0 |
| mean15 | 0,939 | 33 | 0,522 | 33/72 | 9′ (6–23) |
| mean60 | 0,870 | 20 | 0,282 | 23/72 | 34′ (26–46) |
| mean240 | 0,782 | 6 | 0,111 | 10/72 | 92′ |
| EWMA hl15 | 0,917 | 19 | 0,408 | 22/72 | 18′ |
| max15 | 0,928 | 31 | 0,516 | 33/72 | 3′ (0–9) |
Ở 277 phút top 0,01 % (bundle): mean15/mean60/mean240 chỉ còn 0,83/0,42/0,21 × giá trị điểm [ĐO]. Gate thật dùng quantile cuộn nên **tự hiệu chỉnh số lần pass** (quota ~ giữ), cái đổi là **pass vào đợt nào và trễ bao lâu**. [SUY ĐOÁN: mean60/240 dồn pass sang các đợt giảm kéo dài, vào muộn ~0,5–1,5 h ⇒ kỳ vọng âm.]

## 4. Arm (≤5), định nghĩa chính xác
Tín hiệu `p̃(t)` thay `p15(t)` **chỉ trong nhánh PREDICT_SYMBOL_TRADE của gate** (tính r, nạp buffer, so ngưỡng); mọi thứ khác giữ nguyên.
Thứ tự: làm mượt p15 (market-level) → r = p̃/factor(sp) → buffer/q_t như cũ → pass. Xếp hạng (top-24 theo sp) KHÔNG đổi.
- **A0 = P1 (B0)**: `p̃(t)=p15(t)`.
- **A1 = MEAN15**: TB các p15 có ts ∈ [t−14′, t] (gồm t); cần ≥12/15 giá trị, thiếu ⇒ không có pred ⇒ không vào lệnh selector phút đó.
- **A2 = MEAN60**: như trên, [t−59′, t], cần ≥48/60.
- **A3 = MEAN240**: [t−239′, t], cần ≥192/240.
- **A4 = MAX15** (giả thuyết khác: "giữ cửa mở sau spike", trễ thấp theo proxy): max p15 trên [t−14′, t], cần ≥12/15. (EWMA bỏ: proxy nằm giữa MEAN15 và MEAN60, thừa.)
- Gate: GIỮ NGUYÊN cơ chế + tham số (pct 0.999950829, 90d, warm-up 7d, skipFull, DYN_*); q_t tự hiệu chỉnh theo phân phối r mới — đây là cách cô lập "đổi tín hiệu" mà không đổi quota. Không tune pct.
- DCA_LEVEL1 (ngưỡng 0,008 phẳng) và điều kiện "pred != null" của leg thị trường: GIỮ p15 điểm (cần code, xem §5 phương án B).
- Ghi chú ngoài phạm vi: nếu owner muốn TB *score selector* thì đó là đổi xếp hạng S1 (đường đã NULL nhiều lần, long_1003) — đề xuất tách đề tài.

## 5. Thiết kế đánh giá (để pre-register)
- **Hiện thực**: (A) không code — thay `pred.bin` bằng p̃ qua `pred_ds` (rẻ, nhưng đổi luôn gate DCA_LEVEL1 0,008); (B) key mới vd `SIM_GATE_P15_SMOOTH=<mode,W>` áp CHỈ ở `AIRejectFilter.entryGate` khi `predictSymbolTrade` (+ test, OFF byte-identical ff3ce513-kiểu, jar mới + A1 code). **Khuyến nghị B** (cô lập), hoặc A nếu prereg chấp nhận và báo cáo Δ số leg DCA_LEVEL1.
- **Cổng hợp lệ (trước khi chấm)**: G0 OFF byte-identical B0 (`n4f-b0-*`); G1 format p̃ (n, ts, risk4h byte-identical; md5 ghi manifest); G2 quota: n/năm và phút gate-mở/năm trong ±25 % B0 (như GATE_ABLATION); MTM `gvz_mtm.py` import trước, missing=0.
- **Tầng A (Oracle, offline, không PnL)**: `research/analysis/gate_offline.py` (~30 s/seed) chạy 5 arm × 8 seed (pred 8 seed tải từ Kaggle ~350 MB) — đo quota, Jaccard phút pass, trễ đợt. Xấp xỉ: tập coin đang giữ lấy từ printDone B0. Không dùng làm tiêu chí thành công.
- **Tầng B (Kaggle sim)**: DEV 2021-07-01→2025-12-31 (chấm CAGR22 = 2022–2025), HO 2026-01-01→2026-09-30 (đã dùng nhiều lần ⇒ chỉ xác nhận cùng dấu). 8 seed gate ghép cặp với B0 cùng seed (pred_s* của nt-chain-y26), cấu hình B0 y hệt `n4f-b0-*` (K24, skipFull, X14, A1, KILLSW_A40, SLEEVE off).
- **Metric**: CAGR22, maxDD MTM, Calmar MTM, n lệnh/năm, PnL/lệnh, UW, theo năm/quý; Jaccard lệnh với B0.
- **Tiêu chí chính**: ΔCAGR22 trung bình ghép cặp 8 seed > 0 với Holm (m=4 arm, α=0,05 một phía), VÀ ≥6/8 seed dương, VÀ ≥3/4 năm DEV dương, VÀ ΔmaxDD_MTM ≥ −2 pp, VÀ HO ΔPnL trung bình cùng dấu. Thiếu 1 ⇒ NO-GO.
- **MDE** [SUY ĐOÁN từ GQSF: Δ +2,81, CI t [+0,78;+4,83], n=8 ⇒ sd cặp ≈ 2,4 pp]: ~2,8 pp CAGR22 (α 0,05, power 0,8) không hiệu chỉnh; ~3,8 pp với Holm m=4. Nhiễu retrain 1 seed lên tới 5,3 pp (SEED7) ⇒ bắt buộc đủ 8 seed. CI seed KHÔNG phủ rủi ro thị trường (2022 quyết định thứ hạng) ⇒ báo thêm block-bootstrap 30d.
- **Futility (tiết kiệm)**: chạy seed 42/7/21/99 trước; arm nào ΔCAGR22 TB < −3 pp và ≤1/4 seed dương ⇒ dừng arm đó (khai trong prereg, không xem số arm khác).
- **Compute**: 1 kernel sim DEV+HO ≈ 54′ (n4f-b0-s7 `secs` 3 220) + overhead ⇒ ~1,1 h. Đủ 4 arm × 8 seed = 32 kernel ≈ 35 kernel-h ⇒ **~18 h wall với 2 kernel song song**, + MTM 4 batch ≈ 3 h ⇒ ~21 h; futility cắt còn ~12–21 h. Phương án B thêm 1 kernel G0. Oracle: build jar (B) ~10′, tầng A ~20′ CPU, tải pred ~350 MB, đĩa < 1 GB.

## 6. Rủi ro
- **Lookahead**: chỉ dùng cửa sổ trái-đóng gồm t (không `center=True`, không pandas rolling trên chuỗi đã sort sai, không bfill); ts theo thời gian thật (gap ⇒ thiếu, không nối index); test: đổi p15 tại t+1 không được đổi p̃(t). Nối fold WFO causal (mỗi quý model khác) — không leak nhưng tạo bậc ở ranh giới fold.
- **Độ trễ live**: cần p15 MỖI phút; phút FAIL-CLOSED/tick bị bỏ (pass selector chậm, restart) tạo lỗ ⇒ quy tắc ≥80 % phải giống hệt sim. Restart cần rehydrate W phút p15 (từ file `storage/data/prediction` hoặc Aerospike ai_pred_1m trên 242 — đọc, không ghi) nếu không mất tới 4 h gate với MEAN240.
- **Parity/triển khai**: q_t và buffer r đổi phân phối ⇒ seed buffer gate (đang chờ Vision 10-2026) và buffer 30–90 ngày live phải dựng lại cho arm thắng; parity dry (prereg 3c7dae05 + ADD1–4, V-OVL) phải thêm cột p̃ vào log [GATE-RATIO]. Không đụng go-live v1.2 hiện tại: mọi thay đổi chỉ vào v1.3 sau GO.
- **Đa kiểm định**: thêm 4 arm vào ledger họ GATE; Holm như trên.
- **Kỳ vọng tiên nghiệm**: âm cho MEAN60/MEAN240 (trễ 34–92′ theo proxy; ENTRY_CONFIRM/R4_CADENCE) — [SUY ĐOÁN]. MEAN15 ≈ thừa (ACF lag15 0,83, p15 ≈ momentum15M).
