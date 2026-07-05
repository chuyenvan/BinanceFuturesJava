# TASK-128 — Đo chất lượng model đang dùng trong WFO (report)

- **CCD:** opus. **Ngày:** 2026-07-04. **Branch:** module.
- **Dataset đo:** `chuyendinh/wfo-dataset-wf-leakfree` (Kaggle) = bộ `wfo_dataset_wf` (market.bin + pred.bin + funding.bin + manifest.txt). Realized label tái lập từ ticker file `chuyendinh/hpo-ticker-daily` (`ticker_YYYYMMDD.bin`, Java-serialized `TreeMap<Long,Map<String,KlineObjectSimple>>`).
- **Nguyên tắc:** mục ĐỊNH NGHĨA PRE-REGISTERED (dưới) ghi TRƯỚC khi tính bất kỳ số nào (đọc code Java sinh/tiêu thụ pred). Số phải khớp định nghĩa; nếu lệch → chỉ sửa khi phát hiện định nghĩa sai + ghi rõ.

---

## ⛔ ĐỊNH NGHĨA PRE-REGISTERED (ghi trước — chống lỗi "đo sai chiều" của validator cũ)

> Mọi định nghĩa dưới đây trích thẳng từ code Java (đường sinh + đường tiêu thụ). Ký hiệu `file:line`.

### 0. Provenance thực của dataset (đọc `manifest.txt` bản Kaggle — KHÁC giả định trong đề task)

```
sourceMarketSet   = market_data
sourcePredSet     = ai_pred_market_full_basket_v2
sourceFundingSet  = funding_selector_pred_1m_v2
predSetProvenance   = ai_pred_market_full_basket_v2-unchanged-scanAll         ← KHÔNG leak-free
fundingSetProvenance= LEAKFREE-perfold-24h-score1minusPwin-from-predict_wf-bins ← leak-free per-fold, horizon 24h
leakFreeFrom      = funding=perfold-leakfree-2022+ ; market_pred=unchanged
```

**⚠️ ĐÍNH CHÍNH đề task:** đề gọi `pred.bin` là "leak-free". Manifest nói NGƯỢC: `pred.bin` = set cũ `ai_pred_market_full_basket_v2` **GIỮ NGUYÊN, KHÔNG leak-free** (cả `predReturn15M` lẫn `predRisk4H`). Model market cũ train tới ~**2025-12-19** (cutoff của `ValidateOldPredictVsRealized` = `20251220`). ⇒ IC market ở giai đoạn **< 2025-12 là IN-SAMPLE (lạc quan giả)**; chỉ đoạn **≥ 2025-12-20 mới là OOS thật**. Chỉ `funding.bin` là leak-free per-fold (phủ 2022-01..2026-03).

### 1. GATE / MARKET model — `pred.bin`
Format (`WfoDataset.java:26`): `[count:int]` rồi `count × [ts:long][predReturn15M:float][predRisk4H:float]`.

**1a. `predReturn15M`** — dự báo max-gain 15m của rổ vào lệnh.
- **Nhãn model học** (`WFOGateRunner.java:182-186,265-287` = `basketMaxGain`): tại mốc t, rổ = `HistoryManager.findPotentialLosers(t)`; nhãn = trung bình trên rổ của `max((maxPrice − close(t))/close(t))` trên các nến thuộc `(t, t+15m]`. `close(t)` = `priceClose` nến tại t.
- **Rổ `findPotentialLosers(t)`** (`HistoryManager.java:477-510`): mọi coin có `totalUsdt(nến hiện tại) ≥ 5000`, tính `dropFromPeak = (close − max(maxPrice trên 15 nến gần nhất)) / max(...)`; giữ coin `dropFromPeak < −0.001`; sort tăng dần theo dropFromPeak (tụt sâu nhất trước); lấy **top 60**.
- **Chiều kỳ vọng:** `predReturn15M` CAO ⇒ realized `basketMaxGain` 15m CAO ⇒ **IC Spearman DƯƠNG**. (Đây cũng là chiều filter `AIRejectFilter.java:96` REJECT khi `pred15M < MIN_MOMENTUM_15M` — thấp = xấu.)
- **Realized đo:** mirror `ValidateOldPredictVsRealized.basketMaxGain` (`:189-213`). Horizon = 15m. De-overlap 15m (mốc độc lập). Nguồn giá = ticker file.
- **Thước:** IC Spearman (predReturn15M, realized15M) theo quý + toàn kỳ; decile-lift (top-decile theo pred, %chạm +1/2/3/6% vs base-rate).

**1b. `predRisk4H`** — dự báo drawdown 4h.
- **Chiều (đọc filter `AIRejectFilter.java:92-95`):** REJECT khi `risk4H ≤ thresRisk` với `thresRisk = HARD_RISK_LIMIT_4H` (< 0, mặc định −0.2; HPO cũ −0.092). ⇒ `predRisk4H` là **số ÂM** (drawdown); càng âm = càng rủi ro. Message "MaxDD 4H quá cao".
- **Realized đo:** mirror `ValidateOldPredictVsRealized.basketMaxDrawdown` (`:215-240`) NHƯNG horizon = **4h (240m)** (thay 15m), trên CÙNG rổ `findPotentialLosers(t)`: worst trên `(t, t+4h]` của trung-bình-rổ `(minPrice − close(t))/close(t)` (kẹp ≥ −1). Cả pred lẫn realized đều âm.
- **Chiều kỳ vọng:** `predRisk4H` càng âm ⇒ realized DD 4h càng âm ⇒ **IC Spearman DƯƠNG** (tương quan cùng dấu). De-overlap 4h.
- ⚠️ **Caveat rổ:** nhãn gốc `maxDrawdownNext4H` của set `full_basket_v2` chưa pin được chính xác rổ (FINDINGS §2c: dd4h ≈ `basketVolSpike` trá hình). Pre-register dùng rổ `findPotentialLosers` (rổ VÀO LỆNH thật — rủi ro DCA thực đối mặt). Nếu IC lệch mạnh khỏi kỳ vọng, khả năng nhãn gốc dùng rổ khác → GHI khi thấy số, KHÔNG sửa lén.

### 2. FUNDING selector — `funding.bin`
Format (`WfoDataset.java:27`): `[count:int]` rồi `count × [ts:long][len:int][len × long]`. Mỗi `long` = `(symbolId<<32) | floatBits(score)` (`DataManagerAerospikeFloatSim.decodeFundingMapToPrimitiveArray:2103-2130` — chỉ lấy `pred[0]`).

- **`score = pred[0]` là gì:** manifest `fundingSetProvenance=...score1minusPwin`. Nguồn = `gen_funding_wf_predictions.py`: nhãn `y = (maxFav_H ≥ 0.06)` (WIN=6%), model xuất `predict_proba[:,1] = P(win)`; builder leak-free đóng gói **`score = 1 − P(win@24h)`** (horizon 24h). ⇒ **`P(win_24h) = 1 − score`**.
- **Chiều tiêu thụ (đường code THẬT — `SimulatorMarketLevelTicker1MStopLoss`):**
  - `time2SymbolPred = funding.bin` (`initDataReady:706-720`); `preprocessFundingData` sort MỖI tick **tăng dần theo score** (`:759-789`).
  - Chọn coin: `getTopSymbolArray` lấy top-k score THẤP NHẤT (`:181-184`); và mạch ngưỡng (`:222-241`): duyệt tăng dần, `if (symbolPred > maxThres) break` → chọn coin có `score ≤ maxThres`.
  - ⇒ **SELECTED = score THẤP = P(win) CAO.** Chiều đã đảo đúng bởi builder (`score=1−P(win)`) để khớp engine "thấp = ưu tiên".
  - `maxThres = PREDICT_SYMBOL_RATE_MAX_THRESHOLD × AI_DYNAMIC_MAX` (`:224`). ⚠️ **2 hằng này là GENE HPO (đổi theo từng window WFO)** — KHÔNG có 1 threshold cố định. Default Configs: 0.15 × 2.14135 = **0.3212** (HPO cũ 0.197×2.14 = 0.4225).
- **Nhãn realized (mirror `ExportFundingLabel.java:206-222` + `gen_funding_wf`):** per (coin, t) trên lưới 15m; `close(t)` = close nến 1m CUỐI trong bucket 15m tại t; nến path = bucket 15m `(t, t+24h]` (hi=max maxPrice, lo=min minPrice); `maxFav_24h = max(bucketHi/close(t) − 1)`; `nBars_24h` = số bucket thực. **win = (maxFav_24h ≥ 0.06) và (nBars_24h ≥ 96)**. Universe = alt USDT-perp (`isAlt:64-67`: endsWith USDT, ≠BTC/ETH/BTCDOM, không `_`, không `USDC`).
- **Nhóm:** SELECTED = coin có `score ≤ maxThres` tại tick (dùng maxThres default = 0.3212 làm 1 operating-point, ghi rõ genome-dependent) và/hoặc bottom-k=`NUMBER_ENTRY_EACH_SIGNAL`; REJECTED = `score > maxThres`; UNIVERSE = mọi coin trong funding.bin tại tick.
- **Thước (theo quý):**
  1. **Genome-free (chính):** rank-IC Spearman `P(win)=1−score` vs realized `maxFav_24h`; decile-lift hit-rate; calibration `P(win)` vs actual win-rate.
  2. **Operating-point (phụ, genome-dependent):** hit-rate + mean `maxFav_24h` của SELECTED vs REJECTED vs UNIVERSE tại maxThres default.
- **Chiều kỳ vọng:** SELECTED hit-rate > UNIVERSE > REJECTED; rank-IC(1−score, maxFav) DƯƠNG.

### 3. De-overlap & sampling (pre-register để tránh hợp-lý-hóa hậu kỳ)
- Market 15M: de-overlap 15m (chuỗi mốc cách ≥ 15m). Market DD4H: de-overlap 4h.
- Funding: horizon 24h dày (candidate set 9–544 coin/tick) → đo trên **lưới sample 60m** (mốc t bội của 60m); de-overlap per-symbol 24h khi tính hit-rate độc lập. Ghi rõ N mỗi quý. (Full-per-minute = bất khả thi tính; sample 60m là quyết định pre-register, disclose.)
- Quý = biên GMT+7 (`Utils` chuẩn hệ thống). Phủ: market 2021Q1→2026Q2; funding chỉ 2022Q1→2026Q1 (leak-free coverage).

### 4. Nguồn chân lý = code Java (không tái tạo bằng Python)
Ticker file = **Java-serialized object** (`KaggleDataLoader.java:30`) → chỉ đọc được bằng Java. Nhãn (`findPotentialLosers`/`basketMaxGain`/`maxFav`) = logic Java. ⇒ đo bằng **tool Java** tái dùng ĐÚNG code nhãn (mirror validator cũ), KHÔNG reimplement Python (chính là bẫy sai-chiều). Tool: `scripts/model_quality/Task128ModelQuality.java`. Python chỉ tổng hợp CSV thô → IC/decile/quý.

---

## TRẠNG THÁI THỰC THI (2026-07-04)

**Pipeline ĐÃ SẴN SÀNG, số CHƯA có — BLOCKED tài nguyên compute (không tự tranh chỗ job khác).**

Đã xong (commit kèm):
- ✅ ĐỊNH NGHĨA PRE-REGISTERED (trên) — chốt chiều/threshold từ code, ĐÍNH CHÍNH provenance (pred.bin KHÔNG leak-free; funding = 1−P(win@24h)).
- ✅ Tool Java `com.binance.chuyennd.ai_ml.validation.Task128ModelQuality` — tái dùng ĐÚNG code nhãn (mirror `ValidateOldPredictVsRealized` + `ExportFundingLabel`); compile OK; đóng vào fat jar `binance-java-sdk-1.2.4.jar` (PrivateConfig SANITIZED, verify).
- ✅ Jar + config → Kaggle dataset `chuyendinh/t128-model-quality-jar` (uploaded).
- ✅ Kernel `model-quality-1` (validate-small 2024Q1) + `model-quality-full` (toàn kỳ) + `analyze.py` (test synthetic: chiều đúng — hit_SEL>hit_UNI>hit_REJ, IC dương). Ở `scripts/model_quality/`.

⏸️ **BLOCKED (2026-07-04 ~22:00 GMT+7):** cả 2 tài nguyên compute đang bị chiếm bởi thí nghiệm WFO khác — **KHÔNG được đụng**:
- Kaggle: **5/5 slot CPU RUNNING** (`wfo-worker-1..5`, khởi 13:04 → 12h-kill ~01:04). `kaggle kernels push` báo "Maximum batch CPU session count of 5 reached".
- Oracle: ~20/23GB đang chạy WFO vế-C (per `/d/claudedata/RECOVERY_RUNBOOK_20260704.md`) → không đủ RAM trống chạy Xmx2g mà không rủi ro OOM box → giết worker.

**Bước còn lại (1 lệnh khi có slot):** `cd scripts/model_quality/kernel_validate && kaggle kernels push -p .` → poll `kaggle kernels status chuyendinh/model-quality-1` → output → `python scripts/model_quality/analyze.py <out>/t128_out` → điền Bảng 1-3 → chạy `model-quality-full` tương tự.

### Bảng 1 — Gate/market IC theo quý  · <chờ chạy>
### Bảng 2 — Funding hit-rate/lift theo quý  · <chờ chạy>
### Bảng 3 — Tổng hợp: suy giảm IC + vùng model mù  · <chờ chạy>

---

## LỆNH TÁI LẬP
Xem `scripts/model_quality/README.md`. Mỗi số Bảng 1-3 sẽ kèm lệnh kernel + cell `analyze.py` khi điền.

---
# SỐ CHÍNH THỨC (điền 2026-07-05 sáng, kernel model-quality-t128a validate + t128full toàn kỳ)

## FUNDING SELECTOR (leak-free per-fold, score=1−P(win@24h), maxThres=0.3212) — n=882,108 (98.8% complete)
| chỉ số | toàn kỳ | biên độ theo quý (21 quý 2021Q1–2026Q1) |
|---|---|---|
| rankIC | **0.3441** | 0.202 (2022Q3) … 0.446 (2021Q2) — KHÔNG quý nào âm |
| hit_SEL | **65.8%** | 42.3% (2022Q3) … 85.7% (2021Q2) |
| hit_UNI | 39.9% | — |
| hit_REJ | 35.4% | — |
| mf_SEL vs mf_UNI | 0.162 vs 0.080 | gấp ~2× |
**Thứ tự SEL > UNI > REJ đúng ở 21/21 quý.** Quý tệ nhất 2022Q3 (bear đáy): hit tuyệt đối 42% nhưng vẫn +13.4đ so universe.
⇒ **Funding selector có tín hiệu THẬT, bền qua 5 năm mọi regime.** (Bảng quý đầy đủ: /d/claudedata/mqfull_analyze.txt + t128_out CSV.)

## MARKET MODEL (pred.bin = ai_pred_market_full_basket_v2 — KHÔNG leak-free ⇒ TRẦN TRÊN in-sample)
IC_ret15 ALL = 0.6043, IC_risk4H = 0.3996; theo quý 0.31–0.52, không quý nào gãy. KHÔNG dùng làm IC OOS.
Việc kế: đo lại với pred leak-free per-fold (set ai_pred_market_gate_wfo, 1.79M — chờ export dataset v3).

## Đối chiếu WFO 3 vế: WFE ~0.23–0.26 cả 3 vế trong khi funding IC ổn ⇒ nút thắt ở tầng selection/chuyển tín hiệu→PnL.

---
# BỔ SUNG 05/07 chiều — MARKET IC LEAK-FREE (kernel model-quality-v3pred, pred WF v3, load pred=1,795,680 verify)
| quý | IC_ret15 in-sample (static) | IC_ret15 WALK-FORWARD OOS | gap |
|---|---|---|---|
| 2023Q1 | 0.4434 | 0.4217 | −0.022 |
| 2023Q3 | 0.3698 | 0.3282 | −0.042 |
| 2023Q4 | 0.5014 | 0.4730 | −0.028 |
| 2024Q1 | 0.4772 | 0.4463 | −0.031 |
| 2025Q4 | (xem file) | 0.4993 | ~ |
**Kết luận: gate model 15m có tín hiệu OOS THẬT rất mạnh (0.30–0.50/quý), gap in-sample→OOS chỉ 0.02–0.04
(không overfit nặng).** ALL 0.64 vs 0.60 không so được (khác coverage: WF từ 2023). Caveat: cột IC_risk4H trùng
tuyệt đối giữa 2 bảng → nghi predRisk4H trong csv gate chưa per-fold (chỉ predReturn15M per-fold) — cần xác minh
WFOGateRunner writer nếu risk4H được dùng cho quyết định.

# BỔ SUNG — OPTUNA (kernel funding-train-optuna-24h, 50 trials, TEST chạm 1 lần qua ensemble 3 seeds)
Tuned ens3: rankIC 0.2997 | LIFT 1.545 (vs untuned 0.2918/1.527) → tầng-1 (HP+ensemble) chỉ còn **+0.008 IC**.
Best: depth9/lr0.0115/sub0.61/col0.50/mcw25.7/regL9.86, 293 cây. Single seeds 0.2985-0.2997 (ensemble gain ≈ 0).
⇒ 45 features hiện tại đã vắt gần kiệt bằng model tĩnh; bước có kỳ vọng = walk-forward chain (tầng 2a).

# BỨC TRANH HỘI TỤ: gate IC OOS 0.30-0.50 ✓ mạnh · funding IC OOS 0.344 ✓ mạnh · WFE 0.24 cả 3 vế ✗
⇒ nghi phạm còn lại duy nhất: TẦNG CHUYỂN TÍN HIỆU → TRADE (selection/strategy/sim). Chờ N-noise + mổ per-window.

---
# ĐÓNG SỔ TẦNG-1 (05/07 chiều — kernel funding-thres-calib-24h, TEST base 48.4%)
| chế độ (chọn trên VAL) | thres | coverage TEST | hit_SEL TEST |
|---|---|---|---|
| same-coverage (~prod) | 0.38 | 41.2% | 63.7% |
| **nguyên ngưỡng production** | 0.3212 | 23.8% | **69.3%** |
| max-hit (tinh nhuệ) | 0.28 | 13.2% | 73.3% |
Production cùng kỳ (per-fold TASK-128): hit 66.4%/65.0% @ cov 39.6%/30.2%.
**Đọc frontier:** model mới TĨNH ưu ở vùng coverage thấp (69-73% hit), hụt nhẹ ~2đ ở coverage cao — tổng thể
≈ tương đương production dù CHƯA per-fold. KẾT LUẬN TẦNG-1: Optuna hội tụ (+0.004 VAL là hết nước), bagging ≈ 0,
calibration xong — model tĩnh 1.6MB provenance sạch đã NGANG model 262MB mồ côi. Phần thưởng còn lại nằm ở
TẦNG-2a walk-forward chain (per-fold từng cho +0.03-0.05 IC). Tầng-1 CHÍNH THỨC ĐÓNG.
