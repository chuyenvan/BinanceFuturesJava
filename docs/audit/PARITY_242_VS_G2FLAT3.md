# PARITY_242_VS_G2FLAT3 — 242 (PAPER) có chạy đúng `G2 + FLAT3` không? (READ-ONLY + parity từng tầng)

- **Ngày:** 2026-10-01 (GMT+7). **Task:** kiểm 242 vs baseline `profiles/g2_flat3.properties`.
- **Đường vào 242:** `ssh -p 2222 -i ~/.ssh/id_rsa_chuyennd root@103.157.218.242` (`3stech.vn`, app `/home/chuyennd/java/v_t_m`).
- **Mode 242:** **PAPER** — `SHADOW_NO_PUSH=true`, `LIVE_PROFILE=c3_shadow`, `PAPER_EQUITY=35000`.
- **Ràng buộc đã giữ:** **CHỈ ĐỌC** trên 242 (0 file sửa, 0 restart, 0 kill); không đụng ONNX/secret; không in secret;
  **0 sim/0 train trên Oracle**; 2026 = **HOLDOUT** (chỉ DOC audit-only); DEV ≤ 2025-12-31. `df -h` nhẹ.
- **Nguồn đối chiếu:** `profiles/g2_flat3.properties`, `docs/result/RESULT_GDV2_P3.md`, `RESULT_RESET_RULE_P2.md`,
  `RESULT_TRAIL2_G2.md`, `RESULT_GATE_ROOTCAUSE.md`, `RESULT_FEATDIFF_PASS2.md`, `AUDIT_SELECTOR_MODEL_PARITY.md`,
  `docs/plan/PLAN_G2_LIVE_PORT.md`, `docs/audit/PROBE_242_20261001.md`, `DEPLOY_242_OI_INPLACE_20260930.md`.

---

## 0. KẾT LUẬN NGẮN (4 câu)

1. **242 KHÔNG chạy `G2`.** Toàn bộ key gate rolling **VẮNG** trong `conf/env.sh` và `config.properties`
   (`grep GATE_ROLLING conf/ config.properties` ⇒ rc=1; log `GATE-RATIO` = **0 dòng**). `LiveGateRollingRatio.isOn()=false`
   ⇒ gate rơi vào nhánh **fixed-scale** `thrBase = MIN_MOMENTUM_15M = 0.008` (`AIRejectFilter.java:78,82`).
   ⇒ đúng như nghi ngờ của owner: **gate là fixed, KHÔNG phải rolling**.
2. **242 cũng KHÔNG chạy `FLAT3`.** Thiếu `TS_GIVEBACK_RATIO=1.0` (đang ăn default **0.5** = dạng T0) và `SIM_TS_MAX_GAP=0.03`
   (đang ăn default **0.08**). Exit đang chạy là **T0 (0.5 / 0.08 / 0.03)**, không phải FLAT3 (1.0 / 0.03 / 0.03).
3. **Lệch config kèm theo:** `SIM_GATE_DYN_SCALE` **1.70** (profile 1.55) · `SIM_RATE_PROFIT_STOP_MARKET` **0.05** (profile 0.07) ·
   `DCA_GRID_WEIGHTS` **1,0,0,0** (profile `1,1,1,1` = KEEPLEG0) · thiếu `SIM_F_BASE` (ăn default 0.03 vs 0.015),
   `CONC_CAP_PERCOIN_*`, `SIM_RATE_FEE/SIM_SLIPPAGE_RATE`.
4. **Parity dữ liệu:** ở **cùng phút** p15 LIVE ≈ DEV (0.9426 % vs 0.9484 %, Δ0.0058 pp) ⇒ pipeline KHÔNG cắt đuôi;
   nhưng **thang đo TUYỆT ĐỐI** lệch mạnh (live max 1.67–2.30 % vs dev max 12.26 %) ⇒ gate **fixed** không thể hiệu chuẩn
   ⇒ `n_pass=0`. G2 (quantile trên tỉ số `r`) **bất biến thang đo** — đó chính là cơ chế sửa, mà 242 đang thiếu.

---

## 1. VIỆC 1 — 242 CÓ CHẠY ĐÚNG `G2 + FLAT3`? (bảng key-by-key)

**Cách đọc:** 242 chỉ là PAPER/shadow (`c3_shadow`); key "SIM_*" ở 242 là nhánh code live đọc qua `Cfg.get` (env→properties).
`khop` = giá trị trùng profile · `LECH` = khác giá trị · `THIEU` = không khai (ăn default Java).
Nguồn 242: `conf/env.sh` + `config.properties` (chỉ key non-secret) đọc 2026-10-01 10:4x.

| # | nhóm | key (profile `g2_flat3`) | profile | 242 | kết |
|---|---|---|---|---|---|
| 1 | gate | `SIM_GATE_ROLLING_MODE` | `ratio` | **không có** | **THIEU** |
| 2 | gate | `SIM_GATE_ROLLING_DAYS` | `90` | **không có** | **THIEU** |
| 3 | gate | `SIM_GATE_ROLLING_PCT` | `0.999950829` | **không có** | **THIEU** |
| 4 | gate | `LIVE_GATE_ROLLING_MODE/PCT/DAYS` (key LIVE thật, `LiveGateRollingRatio.java:24-26,73,78,89`) | — | **không có** | **THIEU** |
| 5 | gate | `SIM_GATE_DYN_SCALE` | `1.55` | `1.70` | **LECH** |
| 6 | gate | `SIM_MIN_MOMENTUM_15M` | `0.008` | `0.008` | khop |
| 7 | exit | `TS_GIVEBACK_RATIO` (FLAT3=1.0) | `1.0` | không có → default **0.5** (`Configs.java:184`) | **LECH (T0)** |
| 8 | exit | `SIM_TS_MAX_GAP` (FLAT3=0.03) | `0.03` | không có → default **0.08** (`Configs.java:140`) | **LECH** |
| 9 | exit | `SIM_TS_MAX_GAP_WEAK` (FLAT3=0.03) | `0.03` | không có → default **0.03** | khop (tình cờ) |
| 10 | exit | `SIM_RATE_PROFIT_STOP_MARKET` | `0.07` | `0.05` | **LECH** |
| 11 | exit | `SIM_TS_GIVEBACK` (=1) | `1` | không có | **THIEU** |
| 12 | exit | `SIM_LOSER_TIME_STOP_HOURS` | `168` | không có | **THIEU** |
| 13 | selector | `SELECTOR_RANK_TOPK` | `16` | `16` | khop |
| 14 | selector | `SELECTOR_ONLY_ENTRY` | `0` | không có (default) | ~khop |
| 15 | sizing | `SIM_F_BASE` | `0.015` | không có → default **0.03** (`Configs.java:155`) | **LECH (x2)** |
| 16 | sizing | `CAPITAL_START` | `35000` | `PAPER_EQUITY=35000` (key LIVE) | ~khop |
| 17 | sizing | `DCA_GRID_SCALE` | `6.0` | không có | ~ (default) |
| 18 | sizing | `DCA_GRID_WEIGHTS` (KEEPLEG0) | `1,1,1,1` | **`1,0,0,0`** | **LECH** |
| 19 | sizing | `TIER_FLAT` | `1` | `1` | khop |
| 20 | risk | `CONC_CAP_PERCOIN_ENABLED/PCT` | `true/0.15` | không có → **TAT** | **THIEU** |
| 21 | fee | `SIM_RATE_FEE` | `0.000982` | không có → default `0.002` (`Configs.java:103`) | **THIEU** |
| 22 | fee | `SIM_SLIPPAGE_RATE` | `0.000067` | không có → default `0.003` (`Configs.java:117`) | **THIEU** |
| 23 | fix | `SIM_FIX_B1/B2/B3` | `true` | không có | **THIEU** |
| 24 | breaker | `SIM_BREAKER_MODE` | `OFF` | không có | **THIEU** |
| 25 | nhịp | `SIM_ENTRY_SAMPLE_MIN` | `1` | không có; có `LIVE_ENTRY_GRID_MIN=1` | ~tương đương |

**Key 242 THÊM (không có trong `g2_flat3`):** `LIVE_PROFILE=c3_shadow`, `SHADOW_NO_PUSH=true`,
`ENTRY_CASCADE=0`, `OI_LIVE_REFRESH_MODE=inplace`, `SELECTOR_TIER1_NET015=true`, `TRAIL_HINGE_NET015=true`,
`SIM_TS_PROFIT_MULTIPLIER=3.0`, `TS_PRED_GAP=1`, `MARKET_SCAN_MIN=1`, `MARKET_SCAN_PRIORITY=1`, `LIVE_FEAT_DUMP=3000`,
`SHADOW_C3_DIR`.

> **1 CÂU (VIỆC 1):** **KHÔNG.** 242 là **biến thể T0-fixed**: gate **fixed-scale** (`MIN_MOMENTUM_15M` × 1.70, thiếu TOÀN BỘ key rolling)
> + exit **T0 (0.5/0.08/0.03)** + sizing khác (`F_BASE` default 0.03, `DCA_GRID_WEIGHTS=1,0,0,0`,
> `RATE_PROFIT_STOP_MARKET=0.05`, thiếu `CONC_CAP`, thiếu phí base) — **không phải `G2 + FLAT3`**.

---

## 2. VIỆC 2 — MÔ TẢ PIPELINE THỰC TẾ ĐANG CHẠY (242, có file:line)

```
DATA → FEATURE → GATE → SELECTOR → ENTRY → SIZING → EXIT → RISK
```

1. **DATA** — `BinanceDataIngestor` (cwd riêng `/home/chuyennd/java/collectData`) ghi kline/1m; app trade đọc ticker 1m.
   OI live nạp **inplace** (`OI_LIVE_REFRESH_MODE=inplace`, `Configs.OI_*`; xem `DEPLOY_242_OI_INPLACE_20260930.md:34`).
2. **FEATURE** — 2 bộ: **gate 33 feature** (model entry `OnnxInferenceManager` 33 feat; mirror `LiveFeatureDump.java:29,199`,
   dump ra `feat_dump/*.csv.gz`) và **selector 45 feature** (`SelectorOnnxInferenceManager.NUM_FEATURES=45`, `:15-16,26`).
   Trên 242 dùng net015 (`SELECTOR_TIER1_NET015=true` → `SelectorTier1Source.java`).
3. **GATE** — `DetectEntrySignal2TradeNormal.createOrderBuyRequest(...)` `:908,933` → `AIRejectFilter.entryGate(...)`
   (`AIRejectFilter.java:63-95`) → `EntryGate.threshold(thrBase, sp)` (`EntryGate.java`: `thr = thrBase*max(0.26787,(sp/0.15)*1.2876)*GATE_DYN_SCALE`).
   Trên 242: `LiveGateRollingRatio.isOn()=false`, `GateRollingRatio.isOn()=false` ⇒ **`thrBase=0.008` fixed**
   (`AIRejectFilter.java:78,82`). Log: `[GATE] ... base=0.00800 thr=[0.03441..0.04473] n_pass=0`.
4. **SELECTOR** — `S1RankerLive` + `Net015ValueLive` + `LiveBuildMap` (rank S1); `SELECTOR_RANK_TOPK=16` giữ **top-16**;
   `MARKET_SCAN_MIN=1` ⇒ **có nhịp tách**: SELECTOR 15' vs MARKET-LEVEL (BIG_DOWN/DCA) 1' (`Configs.java:431-444`;
   header `[CADENCE-SPLIT-V2]`).
5. **ENTRY** — 3 sleeve: **PREDICT_SYMBOL_TRADE** (gate đóng/mở), **BIG_DOWN**, **DCA_LEVEL1**
   (`DetectEntrySignal2TradeNormal.java:347,361,382,482`); `ENTRY_CASCADE=0` (không cascade); `LIVE_ENTRY_GRID_MIN=1`.
6. **SIZING** — `Configs.F_BASE` (242 ăn default **0.03**) × throttle × `DCA_GRID_SCALE` × `w[i]/Σw` (`w=1,0,0,0` ⇒ chỉ level-1);
   budget = equity/`NUMBER_ORDER_BUDGET`.
7. **EXIT** — trailing: `TS_MAX_GAP`/`TS_MAX_GAP_WEAK` + `TS_GIVEBACK_RATIO` (242 ăn default **0.5/0.08/0.03**);
   `RATE_PROFIT_STOP_MARKET=0.05`; nhánh shadow C3 thêm `TrailHingeSource` (`TRAIL_HINGE_NET015=true`) +
   `ShadowBookC3` (would-CLOSE/ledger), `SIM_TS_PROFIT_MULTIPLIER=3.0`.
8. **RISK** — `CONC_CAP_PERCOIN_*` **TẮT** trên 242 (default); breaker OFF; `SHADOW_NO_PUSH=true` ⇒ **không đặt lệnh thật**.

---

## 3. VIỆC 3 — PARITY TỪNG TẦNG (mảnh nhỏ, reuse tooling)

**Mảnh nhỏ dùng lại (0 sim mới):** 242 `feat_dump/*.csv.gz` (33 feature LIVE, 2026-09-28→10-01) · `full.log` 242 ·
`wfo_ds_x1_2021/pred.bin` (DEV export, ≤2025) · tooling `research/analysis/featdiff_pass2.py`, `featdiff_pass2_p15.py`,
`md_inline.py` (đã chạy ở `RESULT_FEATDIFF_PASS2.md`, ghép cặp **CÙNG PHÚT**). *2026 chỉ DOC audit-only.*

| tầng | giá trị LIVE (242) | giá trị BACKTEST (DEV/sim) | lệch | kết luận |
|---|---|---|---|---|
| **FEATURE** | 33 feat dump live; `momentum1M/15M` tái tạo inline | `pred.bin`/export DEV | corr `momentum1M 0.9949` · `momentum15M 0.9995`, mean khớp 6 chữ số; vài feat lệch **giá trị** tại cùng phút (volatility15M/1H/termStructure, volumeSpike, basketVolSpike, volumeRatioUpDown, funding×3, rsi14/basketRsi14, btcDominance, trendConsistency) | **GIỐNG (đo được)** — tổng hiệu ứng lên p15 ≤ 0.006 pp; **không feat nào cắt đuôi** (`RESULT_FEATDIFF_PASS2` §3,4) |
| **GATE** — cùng phút | p15 live **0.9426 %** (mean, n=556 cặp) | p15 DEV tái tạo **0.9484 %** | **Δ0.0058 pp** | **GIỐNG tại cùng phút** |
| **GATE** — thang tuyệt đối | p15 live max **1.67 %** (24h) · **2.30 %** (12/08–27/09) | p15 DEV max **12.261 %** (p99 1.308) | `D=11.26` (không 1 thừa số) | **LỆCH HÌNH DẠNG (đuôi bị cắt)** |
| **GATE** — ngưỡng áp thật | `thr`=[**3.03 %..4.51 %**] (base 0.008 × 1.70) | sim R4 fixed: n_pass **1819**/35.49M (pass ~5.1e-5); G2: n **2509** | LIVE **0 pass** vs sim >0 | **LỆCH** (đuôi p15 live không chạm thr) |
| **SELECTOR** | `symbolPred` net015-raw (~0.295–0.383 cho top-16) | sim net015-mapped (mean 0.4971) | LiveBuildMap có test byte-parity (`AUDIT_SELECTOR_MODEL_PARITY` §1); **chú ý**: nếu chạy đường FundingClf thì lệch **+0.25 mean** | **~GIỐNG** (đường c3_shadow net015); lệch nếu model khác |
| **ENTRY** | `n_cand=8/16`, **`n_pass=0` TỪ 12/09 08:15** ⇒ **0 entry** | G2 `n=2509`, R4 `n=2027` (4.5 năm) | 0 vs hàng nghìn | **LỆCH HOÀN TOÀN** — hệ quả gate đóng |
| **EXIT** | **không đo được** (0 lệnh từ 12/09; ledger rỗng — `PROBE_242_20261001` §2) | FLAT3 `n=2517`, armed p95 14.5, Calmar 1.940 | — | **KHÔNG ĐO ĐƯỢC** (bị gate chặn trước) |

**Đọc bảng:** tầng **FEATURE** và **GATE-tại-cùng-phút** parity TỐT ⇒ **không có lỗi pipeline**. Lệch nằm ở
**thang đo TUYỆT ĐỐI của p15** (đuôi live bị cắt) + **chế độ gate** ⇒ tầng ENTRY lệch hoàn toàn (0 vs >0).

---

## 4. VIỆC 4 — TRẢ LỜI + ĐỀ XUẤT

**(1) 242 có chạy đúng `G2 + FLAT3` không?** → **KHÔNG.** Key lệch/thiếu:
- Gate: **thiếu TOÀN BỘ** `*_GATE_ROLLING_*` (SIM lẫn LIVE) ⇒ fixed-scale thay vì rolling.
- Exit: **thiếu** `TS_GIVEBACK_RATIO=1.0` (đang 0.5) + `SIM_TS_MAX_GAP=0.03` (đang 0.08) ⇒ **T0** thay vì **FLAT3**.
- Khác: `SIM_GATE_DYN_SCALE` 1.70 (≠1.55); `SIM_RATE_PROFIT_STOP_MARKET` 0.05 (≠0.07); `DCA_GRID_WEIGHTS` 1,0,0,0 (≠1,1,1,1);
  thiếu `SIM_F_BASE`, `CONC_CAP_PERCOIN_*`, `SIM_RATE_FEE/SIM_SLIPPAGE_RATE`, `SIM_FIX_B1/B2/B3`.

**(2) Tầng nào LỆCH giữa live và backtest (số cụ thể)?**
- Lệch **THẬT** ở **GATE/ENTRY**: live `n_pass=0` (2794/2794 dòng `[GATE]`, từ 12/09) vs sim R4 `1819`, G2 `2509`.
- Lệch **thang đo**: p15 live max 1.67–2.30 % vs DEV max 12.261 % (`D=11.26`).
- Tầng FEATURE và GATE-cùng-phút: **không lệch đáng kể** (Δp15 0.0058 pp; corr momentum ≥0.9949).

**(3) Lệch đó có giải thích `n_pass=0` không? (cơ chế)** → **CÓ, hai nguyên nhân cộng hưởng:**
- (a) **Chế độ gate sai (config 242):** thiếu key rolling ⇒ `thrBase = MIN_MOMENTUM_15M` **tuyệt đối** ⇒
  `thr = 0.008 × factor × 1.70` = **3.03–4.51 %**, nằm **trên cả p100 của p15 live** (max 1.67 %/24h) ⇒ 0 pass.
- (b) **Vì sao rolling sẽ khác:** G2 đặt `r = p15/(factor·gs)` và `pass ⇔ r ≥ q_t` (`LiveGateRollingRatio.java:120-128`,
  `EntryGate.threshold`). `pass ⇔ p15 ≥ q_t·factor·gs` ⇒ **`gs`/thang đo p15 TRIỆT TIÊU** ⇒ G2 **bất biến thang đo**,
  tự hiệu chuẩn theo phân phối p15 **của chính live** — đúng cơ chế sửa lỗi lệch thang đo (a).
- ⇒ Cả hai điều cùng đúng: (i) lệch p15 live↔dev **có thật** (nguyên nhân gốc đã biết), và (ii) **242 không bật
  G2** nên mất chính cơ chế khử lệch đó. *Lưu ý:* `SIM_GATE_DYN_SCALE` 1.70 **vô hại khi G2 BẬT** (bị triệt tiêu
  trong `r`), nhưng **có hại khi G2 TẮT** như hiện tại (làm thr càng cao).

**(4) Đề xuất TỐI THIỂU (chỉ ĐỌC, trình bày — KHÔNG tự làm trên 242):**
- **Để 242 chạy ĐÚNG `G2 + FLAT3`** (sửa config, cần restart — ngoài quyền read-only của task này):
  `conf/env.sh` thêm `LIVE_GATE_ROLLING_MODE=ratio`, `LIVE_GATE_ROLLING_PCT=0.999950829`, `LIVE_GATE_ROLLING_DAYS=90`,
  `TS_GIVEBACK_RATIO=1.0`, `SIM_TS_MAX_GAP=0.03`, `SIM_TS_MAX_GAP_WEAK=0.03`; đổi `SIM_GATE_DYN_SCALE` 1.70→1.55,
  `SIM_RATE_PROFIT_STOP_MARKET` 0.05→0.07. (Jar đang chạy `c389b4be…` **ĐÃ CÓ** `LiveGateRollingRatio`/`GateRollingBuffer`
  — kiểm bằng `grep -a` central-dir: 2/2/2 hit ⇒ **không cần build lại**, chỉ thêm key + restart.)
- **Để parity pass (nếu lệch dữ liệu):** nguồn/thang đo p15 live là gốc (đã có `RESULT_GATE_ROOTCAUSE`, phương án A đóng);
  **KHÔNG** "mở gate" bằng `SIM_GATE_DYN_SCALE` (hạ 1.0 vẫn ≥2.0 % > max p15 live 1.67 % ⇒ vô hiệu).
- **Cảnh báo:** bật G2 trên 242 chỉ chuyển `n_pass` từ **0 → rất nhỏ nhưng khác 0** (pct=1−4.9e-5 ⇒ ~4.9e-5 ứng viên pass);
  cần theo dõi ledger C3 tích luỹ (`open>0`, `realized≠0`) để xác nhận máy ghi paper hoạt động lại.

---

## 5. MỤC BỎ / KHÔNG LÀM (khai RÕ)

- **Bỏ** chạy sim/WFO/Java mới: parity dùng lại artifact+tooling đã có (0 sim Oracle; Kaggle không cần vì không có Java mới).
- **Bỏ** `mvn test`/build jar trên Oracle (nặng đĩa 96 %; xem `DEPLOY_*` — agent khác phụ trách).
- **Bỏ** đo tầng EXIT live: **không có lệnh nào từ 12/09** ⇒ không có dữ liệu thoát lệnh để so (ghi rõ "không đo được").
- **Bỏ** sửa bất kỳ file nào trên 242 (ràng buộc cứng read-only) — mọi thay đổi chỉ **trình bày** ở §4.
- **Không** dùng 2026 để chọn/tune; chỉ DOC audit-only.
