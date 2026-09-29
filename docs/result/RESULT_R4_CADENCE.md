# RESULT_R4_CADENCE — Phần 1 (profile lượt) + Phần 2 (giá trị nhịp 1' của R4)

Pre-reg: `docs/prereg/PREREG_R4_CADENCE.md` (commit `4017d12`, chốt **TRƯỚC** khi chạy số).
Nhánh `module`, Java HEAD = `68a2836` (không đổi code Java trong task này).
Sim **trên Kaggle** (bundle `sim-x1-2021-bundle`, jar `sim-jar-r4cad` = dd8d063 sha256 `8d93dad9…`,
**Java-identical** HEAD `68a2836`), 0 sim Oracle. DEV ≤ 2025-12-31 (2026 = HOLDOUT).

---

# PHẦN 1 — PROFILE 1 LƯỢT SELECTOR (chỉ đọc code + log hiện có, KHÔNG restart)

Nguồn log: `/home/ubuntu/shadow_c3/app/logs/full.log` (2026-09-29). Lượt selector mẫu:
`Start 09:47:58.229 → Finish 09:51:52.081`. Code: `DetectEntrySignal2TradeNormal.java`.

## 1.1 Bảng thời gian (một lượt selector, nhịp 15')

| bước | mốc (log) | thời gian | nhãn |
|---|---|---|---|
| **đọc dữ liệu** (Aerospike `readDataForSymbols` + tính market level) | 09:47:58.229 → 09:48:00.045 | **~1,8 s** | [ĐO] |
| **FUNDING predict** (feature extract + cross-sectional + ONNX batch) | 09:48:00.045 → 09:51:52.048 | **~232 s** (~94 %) | [ĐO] |
| **S1 score** (score 664 coin) | 09:51:52.048 | **~0** (nap OI 12,5 s **1 lần/giờ**) | [ĐO] |
| **net015 + map** (`buildValueMap`) | 09:51:52.048 → 09:51:52.073 | **~25 ms** | [ĐO] |
| **gate + entry** | 09:51:52.073 → 09:51:52.081 | **~8 ms** | [ĐO] |
| **TỔNG** | 09:47:58.229 → 09:51:52.081 | **~234 s (3 m 54 s)** | [ĐO] |

- **Universe thật** = **664 symbol** (`[log] symbols:664`); trước đó 644, sau 669 — dao động theo giờ. [ĐO]
- Số "~228 s" của brief MASTER khớp (94 % ở FUNDING predict toàn universe, `PLAN_CASCADE_ENTRY.md`). [ĐO]

## 1.2 FUNDING predict — tuần tự hay batch? bao nhiêu model/coin?

- **BATCH — KHÔNG tuần tự từng coin.** `FundingOnnxInferenceManager.predictBatch(featureArrays)` nhận
  **1 lô = toàn universe** (664×45), gọi `session.run` **1 lần**. [SUY LUẬN — đọc code]
- **1 model duy nhất** (`Funding_Classifier_Final.onnx`, 45 feature, classifier trả `float[][]` prob).
  [ĐO — code `FundingOnnxInferenceManager`; `NUM_FEATURES=45`]. `SelectorOnnxInferenceManager` (4 model 4h/12h/24h/72h,
  TASK-109) **KHÔNG wire** vào đường live `DetectEntrySignal2TradeNormal`. [SUY LUẬN]
- Vòng lặp per-coin (664) là **FEATURE EXTRACT** (`fundingExtractor.extractFeatures`) + **OI lookup**
  (`liveOiProvider.lookup`), KHÔNG phải predict ONNX. [SUY LUẬN — đọc code]

## 1.3 IO hay CPU?

- **Đọc dữ liệu gốc (Aerospike) = ~1,8 s** [ĐO] — phần IO "chính thức" (đọc ticker 1m cho mọi symbol).
- **232 s còn lại = CPU + IO nội tại:**
  - **Feature extract = CPU** [SUY LUẬN]: `HistoryManager` ring-buffer **in-memory** (update O(1) mỗi phút),
    `calculateReturn`/`getRsi14`/`getVolumeZScore`/… quét ring ≤1440 nến — không đọc Aerospike per-coin.
  - **OI lookup = IO** [SUY LUẬN]: `LiveOiFeatProvider.lookup` → `getMetricMap242` đọc **5 set OI/coin từ
    Aerospike-242 (103.157.218.242:3222)**; `liveOiProvider.clear()` **mỗi tick** ⇒ đọc lại toàn bộ 664 coin mỗi lượt.
  - **ONNX batch = nhanh** [SUY LUẬN]: tree-ensemble 262 MB, trần ~2,7k rows/s (`docs/decisions/0005-tran-inference-funding.md`)
    ⇒ 664 coin ≈ **0,25 s**.
- **Verdict: [SUY LUẬN] nút thắt = feature extract (CPU) + OI lookup (IO)**, KHÔNG phải ONNX. Cần instrument thêm
  (timer SLF4J quanh từng khối) mới tách chính xác CPU-vs-IO trong 232 s — chưa đo được bằng log hiện có.

## 1.4 Feature nào đổi theo phút / giờ / 8h?

Từ `FundingOnnxInferenceManager.extractFeaturesToArray` (45 feature):

| nhóm | feature | chu kỳ đổi | cache hiện tại |
|---|---|---|---|
| **FUNDING** (coinFundingRate, basketFundingAvg, fundingRateAvg24H, fundingRateTrend, fundingPercentileCoin, fundingZCoin, fundingPersistence, fundingSum24h, fundingAbs) | 9–10 | **8 h** (settlement funding) | **ĐÃ cache** (`FundingDeepCache` theo settlement key) [SUY LUẬN] |
| **OI/LS/taker** (oiDelta24h, oiZ, lsGlobal, lsToptrader, takerBuyRatio) | 5 | **1 h** (pipeline 242 push theo giờ) | **chưa** — `clear()` mỗi tick ⇒ đọc lại [SUY LUẬN] |
| **S1** (9 feature, 1h close) | 9 | **1 h** | nap OI 12,5 s **1 lần/giờ**, score cache trong giờ [ĐO] |
| **per-minute** (momentum 1H/4H/24H, rsi, distFromLow24H, volatilityShock, volumeZ/trend, price structure, microstructure ret15m/rvol15m/volumeZ5m/closePos15m/wick15m, cross-sectional rank) | ~30 | **1 phút** | không (tính lại mỗi tick) [SUY LUẬN] |

## 1.5 Ước lượng tốc độ đạt được (mục tiêu full universe < 45 s)

- **(i) Predict song song N thread trên 4 core:** feature extract per-coin **độc lập** ⇒ song song gần tuyến tính,
  nhưng trần **4 core** + shared `HistoryManager`/`FundingCrossSectional` (mutate in-place). Ước **~3–4×** ⇒
  **232 s → ~60–75 s** [SUY LUẬN]. **KHÔNG đủ <45 s một mình.**
- **(ii) Batch predict 1 lần/model cả universe:** **ĐÃ LÀM** (`predictBatch` 1 lô). **≈ 0 gain** (ONNX chỉ ~0,25 s).
  [SUY LUẬN]
- **(iii) Cache/incremental feature chỉ đổi theo giờ:** funding (8h) **đã cache**; **OI (5/45) đổi 1h nhưng đang đọc lại
  mỗi tick** ⇒ cache OI theo giờ loại IO OI. Per-minute (~30/45) vẫn phải tính. Ước **~1,3–1,5× thêm** [SUY LUẬN].
- **Kết hợp (i)+(iii): ~4–5× ⇒ ~45–55 s** — **sát trần, không chắc <45 s**, và (i) song song phá tính
  **byte-determinism** (rủi ro lệch parity, xem runbook §7 GPU/nthread). [SUY LUẬN]
- ⚠️ ADR-0005: tinh chỉnh inference trên 1 node **≤1,1×** — nhưng nút thắt của live là **feature extract/OI**, khác
  nút thắt WFO của ADR (inference). Không mâu thuẫn, nhưng tinh thần "đừng yak-shave single-node" vẫn áp.

---

# PHẦN 2 — SIM ĐO GIÁ TRỊ NHỊP 1' (Kaggle, k=1)

Kernel `sim-r4-cad-c0`/`sim-r4-cad-c1` (bundle `sim-x1-2021-bundle`, jar `sim-jar-r4cad` sha256 `8d93dad9…`,
Java-identical HEAD `68a2836`), `sim_end_date=20251231` (date_last 20251230). 0 sim Oracle.

## 2.0 Kiểm hợp lệ (cổng DỪNG)

| cổng | yêu cầu | đo được | kết |
|---|---|---|---|
| **Parity C0** | `md5 = 06fd6e9aa9c916945b2cf12310b337ff`, n 2027, eq 104 489 | md5 **06fd6e9aa9c916945b2cf12310b337ff**, n **2027**, eq **104 489** | **PASS** |
| **Jar đúng** | kernel `JAR_SHA256=8d93dad9…` | `8d93dad9…` | **PASS** |
| **MTM C0 ≡ R4** | dd_total −16,42 · UW 164,7 | dd −16,42 · UW 164,7 | **PASS** |

## 2.1 Bảng chính (k=1, INFL=1.0 — single comparison; as-is phí base)

| arm | n | equity | CAGR% | ddPhút | UW | q*% | top-1% | conc% | Calmar_MTM | T1 | T2 | T3 | T4 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **C0** (=R4, nhịp 1') | 2 027 | 104 489 | 27,53 | −16,42 | 164,7 | 21,7 | 19,38 | 5,30 | 1,676 | PASS | PASS | ref | ref |
| **C1** (selector 15') | 1 287 | 75 535 | 18,65 | −14,68 | 167,7 | 26,3 | 14,76 | 5,01 | **1,271** | PASS | PASS | PASS | **FAIL** |

- **C1 FAIL T4**: `Calmar_MTM 1,271 < 0,90×1,676 = 1,509`. `conc 5,01 ≤ 5,30` ✓; `n` (mục tiêu chính) = **1 287 = 63,5 % C0**.
- **T3 PASS (chất lượng từng lệnh KHÔNG tệ, thậm chí NHỈNH)**: `win% +1,59 pp` (≥ −2,0) · `TSloss% −2,07 pp` (≤ +2,5) —
  C1 bỏ bớt lệnh nhiễu ở nhịp 1' ⇒ **win cao hơn, TSloss thấp hơn** C0. CI block-72h: `win% [−0,58, +3,93]` ·
  `TSloss% [−4,65, +0,18]` — không âm ngoài 0.

## 2.2 CÂU HỎI CHÍNH — nhịp 15' giữ bao nhiêu % n và Calmar của R4?

| thước | C0 (1') | C1 (15') | **giữ lại** |
|---|---|---|---|
| `n` | 2 027 | 1 287 | **63,5 %** |
| `Calmar_MTM` | 1,676 | 1,271 | **75,8 %** |
| `CAGR` | 27,53 | 18,65 | 67,8 % |
| `equity` cuối | 104 489 | 75 535 | 72,3 % |

⇒ **Nhịp 15' MẤT 36,5 % `n` và 24,2 % `Calmar`** của R4. **Kỹ thuật 1' ĐÁNG LÀM** (mất quá nhiều nếu giữ 15').

## 2.3 Bảng theo quý/năm — chỗ nhịp 15' cắt lệnh

Loss **tập trung ở leg SELECTOR** (BD/DCA nguyên vẹn — đúng cơ chế `SIM_ENTRY_SAMPLE_MIN` chỉ lọc PREDICT_SYMBOL_TRADE):

| năm | n C0 | n C1 | Δn | sel C0→C1 | BD C0→C1 |
|---|---|---|---|---|---|
| 2021 | 247 | 210 | −37 | 215→178 | 32→32 |
| 2022 | 357 | 277 | −80 | 326→250 | 20→20 |
| 2023 | 223 | **91** | **−132** | 174→**42** | 49→49 |
| 2024 | 581 | **329** | **−252** | 509→**258** | 71→71 |
| 2025 | 619 | **380** | **−239** | 521→**288** | 76→76 |

- Loss **tăng theo thời gian** (2021 −15 % → 2024/2025 −43 %/−39 %) — universe càng lớn (591+ coin), selector càng có
  nhiều tín hiệu **fire-and-fade giữa 2 mốc 15'**, nhịp 1' càng có giá trị.

## 2.4 Verdict (theo luật)

- **Parity C0 PASS** (06fd6e9a) ⇒ jar/profile/engine không lệch bit nào khi thêm `SIM_ENTRY_SAMPLE_MIN=15`.
- **C1 KHÔNG phải ứng viên** (FAIL T4 Calmar) — C1 chỉ là **ĐO LƯỜNG** giá trị nhịp 1', không phải đề xuất thay R4.
- **Kết luận**: nhịp 1' giữ **+36,5 % n / +24,2 % Calmar** so 15' ⇒ **đáng làm kỹ thuật 1'** (chuyển sang Phần 3 — PLAN).
