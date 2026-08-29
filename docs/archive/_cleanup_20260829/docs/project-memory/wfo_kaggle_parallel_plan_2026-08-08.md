# RÀ TRẠNG THÁI DỮ LIỆU WFO + KẾ HOẠCH CHẠY SONG SONG TRÊN KAGGLE — 2026-08-08

> ⚠️ **Độ tươi số liệu**: bridge tới máy Uni RỚT lúc ~18:0x, KHÔNG đo lại live được khi viết doc này.
> Trạng thái dữ liệu = đo trong phiên ~17:00 ICT 08/08 (CE còn sống) + docs project. Kiến trúc/validate
> lấy từ code+docs (không đổi theo giờ). Mọi ô đánh `[verify]` phải đo lại khi bridge lên.
> Nguồn: `wfo_data_flow_architecture.md`, `wfo_data_status.md`, `wfo_label_merge_bug.md`,
> `wfo_rerun_2026-08-08_ce.md`, `ticker_2026_h1_format_and_build.md`, `wfo_decisions_2026-08-08.md`.

## 0. Kết luận một dòng

Muốn chạy WFO **song song trên Kaggle với predict sẵn** thì phải xong một CHUỖI TUẦN TỰ trước đã:
`label (đang chạy lại) → push Kaggle → selector-predict-1m regenerate predict_wf → build_ds trên
Oracle (đọc Aerospike live) → validate + sign → push dataset → LÚC ĐÓ mới fanout 5 kernel Kaggle`.
Điểm nghẽn không nằm ở khâu song song — nằm ở `build_ds` (bước Oracle serial, đọc live) và ở label
đang export lại. Fanout Kaggle bản thân nó đã proven (parity w6 khớp Oracle).

---

## 1. LUỒNG WFO — hai chỗ chạy trên Kaggle, đừng lẫn

```
[Aerospike 242/Oracle live]
   │  (export tools Java, chạy TRÊN Oracle)
   ├─ ExportFundingLabel      → funding_label_1m.csv (7 horizon)      ─┐
   ├─ ExportFeaturesForPython → ff_*.bin.gz/.t1c.gz (40 feat/coin)    ─┤
   ├─ ExportFundingOiPerCoin  → oi_percoin_full.bin (5 feat)          ─┤ push
   └─ DumpSymbolMapCsv        → symbol_map.csv                        ─┘  Kaggle
                                                                          │
   ╔══ KAGGLE STAGE 1: selector-predict-1m (1 kernel, COMPUTE train) ══╗ │
   ║ gen_funding_wf_predictions.py: merge tool1+OI+label theo (symId,ts)║◄┘
   ║ train XGBoost walk-forward (expanding, purge 72h, FIRST=20230101)  ║
   ║ 4 horizon {4h,12h,24h,72h}, chỉ maxFav, WIN=0.06                   ║
   ║ → predict_wf_YYYYMMDD.bin (1 file/fold, 26B rec, 4 pred/horizon)   ║
   ╚═══════════════════════════════════════════════════════════════════╝
                                     │ kaggle_output (tải về Oracle)
   [build_ds — WfoDataset.java, chạy TRÊN Oracle, đọc Aerospike LIVE]
     gộp: market_data(live) + gate pred(live ai_pred_market_gate_wfo) + predict_wf(Kaggle)
     env: WFO_SEL_HORIZON_IDX=0 (4h), WFO_SET_PRED=ai_pred_market_gate_wfo
     → wfo_ds_LF_1m_..._h4h_v1/ = market.bin + pred.bin + funding.bin + manifest.txt
                                     │
     validate_canonical_wfo.py (leak-guard 2023-01-01, off-grid, NaN-frac) → gate_sign (người)
                                     │ push dataset lên Kaggle
   ╔══ KAGGLE STAGE 2: WFO fanout (5 kernel SONG SONG, "predict sẵn") ══╗
   ║ mỗi kernel chạy subset của 16 window trên FILE dataset            ║
   ║ pred.bin ĐÃ có sẵn selector prediction → KHÔNG train lại selector ║
   ║ WFO chỉ tối ưu GENOME chiến lược (entry/exit/sizing) trên pred cố ║
   ║ định → backtest 1-phút qua ticker file (TICKER_SOURCE=file)       ║
   ╚═══════════════════════════════════════════════════════════════════╝
```

**"Chạy final với predict sẵn" = STAGE 2.** `pred.bin` trong dataset chính là "predict sẵn": selector
prediction đã bake vào, WFO không sinh lại mỗi fold (đó là điểm khiến fanout rẻ + song song được).
STAGE 1 (sinh predict_wf) hiện là **1 kernel duy nhất chạy tuần tự các fold** — nếu chậm thì đây là
nghẽn serial TRƯỚC khi tới song song, có thể tách fold ra nhiều kernel nhưng CHƯA làm.

---

## 2. TRẠNG THÁI TỪNG DỮ LIỆU (cập nhật ~17:00 ICT 08/08, đè lên bản 06:25)

| Dữ liệu | Vai trò trong luồng | Trạng thái | Chi tiết |
|---|---|---|---|
| **Label 1m** | input STAGE 1 | 🟡 **ĐANG EXPORT LẠI** | job `label_export_funding_label_1m.csv`, jar VÁ `gatecount_gate_20260808.jar`, 4 luồng, start 17:17, ETA ~06:00–07:30 09/08. Bản cũ hỏng đã cách ly `label_ds_1m_BROKEN_20260808`. Verify tự động 07:00 sáng mai (trigger đã đặt). |
| **tool1 features** | input STAGE 1 | 🟢 **22/22 quý trên Kaggle** | local đã convert T1C2 + push + xoá. `funding-tool1-features-1m`. ⚠️ 2024Q2/Q3 vẫn **T1C1** (f20/f24/f26 sai số ~1e-2); nguồn `.bin.gz` 2024Q2 đã xoá → sửa phải re-export từ Aerospike. |
| **OI per-coin** | input STAGE 1 | 🟡 CÓ, coverage chưa verify | `funding-oi-percoin` 3.2 GB, `oi_percoin_full.bin` + `symbol_map.csv`. `[verify]` coverage từng coin/khoảng. |
| **symbol_map.csv** | input STAGE 1 + snapshot STAGE 2 | 🟢 | trong `funding-oi-percoin`, 863 symId. Đã vá lỗ thiếu ~81 symId mới. |
| **Gate pred** | input build_ds | 🟢 | `funding-gate-wfo-pred`. `predReturn15M` sạch; `predRisk4H` từng rò rỉ — NAY `predRisk4H` đã bỏ khỏi `AIRejectFilter` (phiên trước), gate vẫn carry-forward cột này trong `wfo_gate_pred.csv` (thiết kế, không phải rác). |
| **Ticker 2021→2025** | input STAGE 2 (sim SL 1m) | 🟢 | `hpo-ticker-daily` 1826 file (v6 post ghost-clean 07-13). |
| **Ticker 2026-H1** | input STAGE 2 | 🟠 `[verify]` | `hpo-ticker-2026` (RIÊNG, không đụng daily). Phiên trước đang build ~6.7 GB; cần xác nhận kernel xong + dataset ready. THIẾU cái này thì sim 2026 fail-fast. |
| **Built dataset (pred sẵn)** | input STAGE 2 | 🔴 `[verify]` CHƯA CÓ | `wfo_ds_LF_1m_20260804_h4h_v1` — thấy trong pipeline JSON, CHƯA xác nhận build/push. Đây là artifact STAGE 2 cần, phụ thuộc label + predict_wf. |
| **jar + config file-mode** | runtime STAGE 2 | 🟢 | `java-run-lc` (config `TICKER_SOURCE=file`); jar leak-free `binance-futures-wfo-lf.jar`. |

**Hạ tầng (17:0x):** Oracle disk 67% (**~49 GB trống**), RAM 21/23 GB, 0→4 java proc (job label).
Kaggle quota **63.81/100 GB** (theo tin nhắn đầu phiên của Uni). `symbol_lifecycle` = 698 symbol.
`TICKER_SOURCE=aerospike` trên Oracle.

---

## 3. DỮ LIỆU CẦN CHO 1 KERNEL WFO SONG SONG (STAGE 2) + VALIDATE TƯƠNG ỨNG

Mỗi kernel Kaggle STAGE 2 phải **self-contained trên file** (parity đã verify: w6 file-ticker =
oosPnl 437.41 / wfe 1.2052 / trades 56 ≈ Oracle). Bộ dữ liệu tối thiểu:

| # | Cần gì | Nguồn | Cơ chế VALIDATE tương ứng |
|---|---|---|---|
| 1 | **Built dataset** market.bin + pred.bin + funding.bin + manifest.txt (pred.bin = predict sẵn) | build_ds trên Oracle → push Kaggle | `validate_canonical_wfo.py`: leak-guard `expect_leakfree=2023-01-01`, off-grid `%60000`, NaN-fraction. `sign=1` chỉ khi PASS toàn bộ. |
| 2 | **Ticker file** 2021→2026 | `hpo-ticker-daily` + `hpo-ticker-2026` (khai BOTH trong `dataset_sources`, symlink về `kaggle_data_hpo/`) | parity từng-ô vs Aerospike (2025-12-31: 847.995 ô, lệch 0). **TUYỆT ĐỐI không** `datasets version` lên `hpo-ticker-daily`. |
| 3 | **symbol_mapper snapshot** | bake `core_symbol_mapper` vào dataset (`KaggleDataLoader.loadSymbolMapperFile`, TASK-112c) | đóng dấu theo version dataset (truy nguyên thời điểm sync). id ≤ 999 (mảng klineArray=1000) và ≤ 863 hiện tại. |
| 4 | **config.properties** `TICKER_SOURCE=file` | `java-run-lc` | ⚠️ `TICKER_SOURCE` env là NO-OP — PHẢI nằm trong config file của dataset, không truyền env. |
| 5 | **jar** leak-free | `java-run-lc` / `binance-futures-wfo-lf.jar` | tên jar DUY NHẤT (tránh glob nhầm jar cũ). Đổi jar/config = bump version dataset. |
| 6 | **jobstore** (điều phối 16 window) | Aerospike `WfoJobStore` — HIỆN trỏ `226:3222 ns=ticker` | 🔴 226 đã quyết RETIRE (`REDESIGN_INFRA_20260804`). Chọn 1: (a) repoint `WFO_STATE_HOST`=Oracle:3222 public; (b) file-self-contained `VerifyOneWindow` (KHÔNG cần jobstore, 1 window/kernel). |

**Validate TẦNG CHẠY (áp cho mọi backtest, không riêng Kaggle):**
- `BacktestIntegrityGuard.assertProductionGrade()` cắm ở `simulatorWithInitEntry` — kiểm 4 thứ:
  `BLOCK_INTRABAR_LOOKAHEAD=true`, `APPLY_SLIPPAGE=true`, `SLIPPAGE_RATE>0`, `RATE_FEE>0`.
  ⚠️ Guard này **KHÔNG** kiểm funding, **KHÔNG** kiểm %MTM → "pass" ≠ số sạch (xem `INFRA_FACTS` mục
  SIMULATOR 5 fact: F0 không có đường thoát lỗ, F1 ddPct sai, F2 funding mặc định TẮT).
- **Preflight Gate** (`DATA_VALIDATION_FRAMEWORK`): 19 loại lỗi / 6 nhóm, fail-fast TRƯỚC HPO/WFO
  (gate coverage 2021-2022, leakage, MAE, ghost USDC…).
- **Sync Oracle→Kaggle ⇒ RE-VALIDATE theo baseline env đó** (`ValidationStamp` khoá theo
  (fingerprint md5, env)). KHÔNG tin stamp env gốc cho Kaggle.

**Validate DỮ LIỆU NGUỒN (đã có / cần):**
- Label: `countRowsInPb` vs tổng dòng partition; lệch ⇒ ERROR + giữ `.partN` + `exit 2`. PASS =
  exit 0 + không còn `.partN.pb` + 22 file quý + không quý 0-byte + ~636M dòng.
- tool1: từng-ô + vị trí NaN vs nguồn (≤5e-3 IQR); T1C2 reader đọc được cả `.bin.gz`/T1C1/T1C2.
- Gate feature+label: `gate-dataset-full` tự verify bằng SỐ DÒNG (emit khớp file — 2.889.623).

---

## 4. CHUỖI TRIỂN KHAI (thứ tự bắt buộc — cái gì chặn song song)

```
[TUẦN TỰ, không song song được]
1. Label export lại (ĐANG CHẠY, ETA sáng 09/08) ──► verify (trigger 07:00) ──► push funding-label-full-1m (version bump)
2. selector-predict-1m kernel: regenerate predict_wf   ← cần label MỚI + tool1 + OI + map (tất cả file Kaggle)
3. build_ds trên Oracle  ← đọc market_data LIVE + gate LIVE + predict_wf(Kaggle). SERIAL, 1 job Oracle.
4. validate_canonical_wfo.py + gate_sign (người duyệt)
5. push wfo_ds_LF_1m_..._h4h_v1 lên Kaggle
        │
[SONG SONG — lúc này mới bắt đầu]
6. wfo_fanout: 5 kernel Kaggle (+2 Oracle worker) chạy 16 window trên dataset. pred.bin = predict sẵn.
```

**Chặn song song / bẫy đã biết:**
1. 🔴 **build_ds đọc Aerospike LIVE** (market_data + gate) — chưa chuyển sang Kaggle-central
   (`REDESIGN` mục 5). Đây là bước Oracle SERIAL bắt buộc trước fanout; không né được kỳ này.
2. 🔴 **Kaggle KHÔNG inject env động** — mỗi trong 5 kernel phải HARDCODE flag vào `run_worker.py`
   TRƯỚC khi push (bài học bug `TS_RATCHET_DECOUPLED`: thiếu 1 dòng → flag mất âm thầm, byte-identical
   với run không flag). Grep tên flag trong launcher như checklist trước khi bấm fanout.
3. 🔴 **jobstore trỏ 226 (retire) + đang bẩn**: 16 window, 2 RUNNING stale ~5,8 ngày. Phải reset +
   quyết repoint Oracle:3222 hay dùng VerifyOneWindow file-mode.
4. **Fanout nặng PHẢI file-mode** — đừng để 5 kernel cùng đọc live Oracle:3222 (lặp sự cố 226:
   15GB RAM drop, 9/17 FAIL). Đọc live Oracle ≤2 kernel đồng thời.
5. **Kaggle**: 5 slot, 12h hard-kill, quota 63.81/100 GB — dataset push phải vừa. Tool batch cuối
   `main()` phải `System.exit(0)` (thiếu → kernel treo 12h mất output).
6. **≤3 job java nặng đồng thời trên Oracle** (bão hoà → reboot mất run).

---

## 5. RỦI RO CHẤT LƯỢNG SẼ LAN VÀO KẾT QUẢ SONG SONG (nêu trước, chưa xử)

1. **2026Q2 label có thể VẪN rỗng sau export lại.** Chẩn đoán cũ: nếu `symbol_lifecycle` build
   trước 04/2026 thì mọi coin `lastSeen < 04/2026` ⇒ `isAlive()` chặn ⇒ 0 anchor cho 2026Q2 dù
   ticker đủ. Job đang chạy nạp 698 symbol nhưng **CHƯA biết lastSeen của chúng tới đâu** →
   `[verify]` khi job xong: 2026Q2 có dòng không. Nếu rỗng → phải rebuild lifecycle tới 07/2026.
2. **tool1 2024Q2/Q3 là T1C1** (sai số ~1e-2 ở 3 cột funding) → chảy vào selector predict → pred.bin.
   Nếu 2 quý này nằm trong OOS window thì kết quả window đó nhiễm. Sửa = re-export 2024Q2 từ Aerospike.
3. **Cổ phiếu token hoá (AAPL/NVDA/TSLA…) đã quyết đưa vào universe** nhưng selector train 2021-2025
   chưa từng thấy asset class này + không chạy 24/7 → prediction cho các symbol này trong pred.bin gần
   như OOD/vô nghĩa kỳ này. "Rủi ro tính sau" (Uni chốt) — nhưng khi đọc kết quả fanout phải TÁCH
   nhóm này ra, đừng để nó bẩn metric tổng.
4. **`ExportFundingLabel` (và `ExportFeaturesForPythonTool`) log "HOÀN TẤT" + exit 0 sau IOException /
   khi BLOCKED** — lỗi che, đã làm pipeline canonical đi tiếp mù 3 lần. Guard jar mới chặn được lỗi
   jar cũ, KHÔNG chặn lỗi này. Verify phải dựa SỐ, không dựa dòng log "✅ Xong".
5. **OI coverage chưa verify** — nếu OI thủng khoảng nào thì `merge_asof` (tolerance 2h) lấp bằng giá
   trị cũ, feature OI của khoảng đó sai âm thầm.
6. **Oracle không phải git repo** → `wfo_build_ds` resolve `code_sha=unknown` → `WfoDataset.export()`
   THROW trên canonical path → phải truyền `code_sha` tường minh ở bước 3.

---

## 6. VIỆC ĐO LẠI NGAY KHI BRIDGE LÊN (checklist `[verify]`)

- [ ] Label job xong chưa + PASS 4 tiêu chí (exit0/không part/22 quý/không 0-byte) — trigger 07:00 lo.
- [ ] 2026Q2 label có dòng không (rủi ro #1).
- [ ] `hpo-ticker-2026` dataset đã ready trên Kaggle chưa (thiếu → sim 2026 fail-fast).
- [ ] `wfo_ds_LF_1m_20260804_h4h_v1` đã build/push chưa, hay phải build từ đầu.
- [ ] OI coverage per-coin.
- [ ] jobstore: quyết 226-repoint-Oracle vs VerifyOneWindow file-mode; reset state bẩn.
- [ ] Kaggle slot trống (`kaggle_slots`) + quota còn đủ push dataset mới.
