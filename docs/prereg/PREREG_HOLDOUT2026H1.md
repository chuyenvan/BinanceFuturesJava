# PREREG_HOLDOUT2026H1 — pre-registration holdout 2026H1 cho 3 cấu hình (HO1)

- Ngày chốt: 2026-10-08. Vai: agent HO1 (dựng holdout), MASTER chốt §7. Commit này đứng TRƯỚC mọi bước dựng input 2026 (B2–B8).
- Nền: `docs/plan/HOLDOUT2026_FEASIBILITY.md` (dc055783). Phương pháp: reaudit_1002 (pre-reg trước đo, không tune sau khi thấy số, inflate √(2 ln k)).
- **Seal 2026 vẫn ĐÓNG trong vòng HO1.** Vòng này chỉ dựng dữ liệu + parity trên cửa sổ DEV (≤ 2025-12-31). Không kernel nào chạy qua 2025-12-31; không tính bất kỳ số hiệu năng/PnL/tín hiệu/thống kê phân phối nào của 2026 — chỉ kiểm toàn vẹn (đếm, khoảng, md5, NaN). Mở seal + 48 kernel holdout = vòng sau, do MASTER/owner quyết.
- 3 cấu hình (tên dùng xuyên suốt): **B0** = K16 G2+FLAT3 (profile `r4_kg0_k16_f015_g155` + SIM_GATE_ROLLING_MODE=ratio, DAYS=90, PCT=0.999950829, TS_GIVEBACK_RATIO=1.0, SIM_TS_MAX_GAP=0.03, SIM_TS_MAX_GAP_WEAK=0.03); **K24** = B0 + SELECTOR_RANK_TOPK=24 + GATE_QUOTA_SKIP_WHEN_FULL=true; **M2** = K24 + override NSEL y hệt `nsel-m2-s*` (NSEL_ADD_ENABLED=true, NSEL_ADD_TOPK=32, SIM_NSEL_ADD_ROLLING_PCT=0.999915, SIM_NSEL_ADD_ROLLING_DAYS=90, SIM_NSEL_CORE_ADD=true, NSEL_CORE_ADD_MAX_PER_CLUSTER=1, NSEL_ADD_F1_MIN_BARRET=-0.01). Bản stress = thêm SIM_CRASH_ENTRY_PENALTY=0.01675.

## 1. Luật chấm (chép NGUYÊN VĂN từ MASTER)

- Cửa sổ 2026-01-01→2026-06-30 +07. Thước như NSEL_RESULT_A/B (n theo start, ΣPnL theo end, MTM phút). Bản CHÍNH = stress in-sim 1,675%; bản phí gốc = báo cáo. 8 seed ghép cặp. Hai scorer độc lập (như NSEL) + đối chiếu.
- E0 Edge sống: K24+skipFull có mean ΣPnL_S > 0 VÀ ≥ 6/8 seed > 0. FAIL ⇒ dừng mọi port/promotion, báo owner (cấp chiến lược).
- H-A (K24+skipFull vs B0 K16): XÁC NHẬN nếu mean ΔΣPnL_S ≥ 0 VÀ mean ΔmaxDD (MTM) ≥ −5pp. Không xác nhận ⇒ báo lại cho đánh giá shadow #2 (không tự đổi gì trên 242).
- H-B (NSEL M2 vs K24+skipFull): XÁC NHẬN nếu mean Δn ≥ +200 chân trong 6 tháng VÀ mean ΔΣPnL_S ≥ −10% × mean ΣPnL_S của K24 VÀ mean ΔmaxDD ≥ −8pp VÀ ≥ 5/8 seed ΔΣPnL_S ≥ −10% × ΣPnL_S K24 cùng seed. Không xác nhận ⇒ KHÔNG port live NSEL.
- Báo kèm (không vào luật): bootstrap MTM block-10d, theo tháng, phí gốc, inflate k=3.
- Kỳ vọng khai trước (MASTER): P(E0) ~70%; P(H-A) ~55%; P(H-B | E0) ~45%.

Ghi chú thực thi (không đổi luật): 8 seed = 42, 7, 13, 21, 99, 123, 777, 2024 (seed của model gate p15, như `gate-abl-seed7`/`gate-sb-*`). "_S" = bản stress. Scorer A/B được commit TRƯỚC khi tải output holdout; chấm một lần; chạy lại chỉ khi lỗi hạ tầng (rc≠ok, mapper < 800, timeout) với cfg y hệt.

## 2. Quyết định MASTER (§7 feasibility) — chốt

1. **Cửa sổ chấm:** 2026-01-01 00:00 → 2026-06-30 23:59 +07. Không kéo tới 08-05. `SIM_END_DATE=20260630`.
2. **Chạy LIÊN TỤC** từ `TIME_RUN=20210701` (như DEV) tới 2026-06-30. Phần ≤ 2025-12-31 của mỗi run phải khớp run DEV tương ứng (cổng toàn vẹn = mục 7).
3. **Một jar** `b7c89f09` (sha256 `b7c89f097241763bb240c24b411a66531b41dad12b1716f13237537386de62c2`, module `386c7cdc`, dataset `sim-jar-nsel`) cho cả 3 cấu hình B0 / K24 / M2.
4. **Dataset WFO 2026:** ghép Python (append). Cổng: bộ ghi Python tái sinh **đúng byte** `funding.bin` (md5 `8e57d900…`) và `market.bin` (md5 `4ab691c9…`) của DEV từ chính nguồn DEV TRƯỚC khi ghi đoạn 2026; phần ≤ 2025 COPY nguyên; manifest md5 mọi file; md5 ticker Kaggle ↔ Oracle phải khớp (sửa lệch hiện có trước).
5. **Gate 8 seed:** đúng recipe của từng seed DEV (seed 42 = recipe `fold_19`/`ml/gate/train_gate_fold.py`: XGBRegressor d4/n150/lr0,05/sub0,8/col0,8/mcw10/n_jobs4, 33 feat V3FULL, `label_oldbasket`; seed khác = recipe đã tạo `gate-abl-seed7`/`gate-sb-s*`, chỉ đổi `random_state`), cut 2026-01-01, purge 15′ như DEV. Assert ts train lớn nhất ≤ 2025-12-31 23:59 và glob nhãn train `202[1-5]`. Phần DEV của `pred.bin` mỗi seed giữ NGUYÊN byte (md5 đoạn DEV = md5 pred DEV seed đó).
6. **Symbol 2026 thiếu mapper/`exchange_info_pin`:** KHÔNG giao dịch (loại), đếm và liệt kê; không sửa mapper.
7. **Cổng parity (seal đóng)**: 3 kernel trên cửa sổ DEV (`SIM_END_DATE=20251231`) với dataset/bundle MỚI, jar `b7c89f09`:
   - **C1** B0 K16 (seed 42, phí gốc) vs run DEV B0 hiện hành `de-p1` (printDone md5 `650c386f0d0dfea334af9d55ca2f21d4`, n 2517, jar `7368be46`): so MỌI cột lệnh của printDone; chấp nhận khác cách in float cột volume như J-C. Mọi khác biệt khác ⇒ FAIL.
   - **C2** K24+skipFull (seed 42, phí gốc): printDone md5 == `gqsf-a1` `ad26fd55f0bb5db32038ec8b357cf8e7` (n 3541).
   - **C3** M2 stress (seed 42): printDone md5 == `nsel-m2-s42` `cbc067f717fa6bd06779c149d71e2e07` (n 7603).
   - **Hiệu chuẩn net015** cut20251231 vs G015x26 gốc trên DEV (mục 4). Nếu lệch làm đổi quyết định vào lệnh trên DEV > 1% số lệnh ⇒ DỪNG, báo MASTER.
   - PASS hết ⇒ DỪNG vòng HO1, báo MASTER. KHÔNG đẩy 48 kernel holdout.

## 3. Chi tiết thực thi đã chốt trước (HO1, không đổi sau khi thấy số)

- **Mép thời gian gate (chặt hơn DEV, khai trước):** recipe DEV cắt train theo cutoff 00:00 **UTC** (gồm 7 h đầu ngày +07 của quý OOS). Cho holdout, train gate seed s dùng `ts < SEAL − 15′` với SEAL = 2026-01-01 00:00 +07 ⇒ ts train lớn nhất ≤ 2025-12-31 23:44 +07; nhãn 15′ của dòng train cuối không chạm 2026. KHÔNG dùng `fold_19` ONNX (md5 `1f1e6fda…`, purge 0, cut UTC ⇒ chứa 2026-01-01 00:00–06:59 +07) và KHÔNG dùng bản `d37969ee…` (train tới 2025-12-31 23:44 UTC = 2026-01-01 06:44 +07) cho đoạn 2026.
- **Dòng pred.bin 2026:** đúng tập timestamp phút của store gate trong [SEAL, 2026-07-01 00:00 +07); loader 2026 `usecols` = `timestamp` + 33 cột V3FULL (KHÔNG đọc cột nhãn); cột `predRisk4H` 2026 điền theo đúng quy ước giá trị của đoạn DEV cuối (kiểm trên DEV trước), cột này không vào quyết định (nhánh RISK đã bỏ).
- **Cổng gate G-B2a:** seed 42 retrain theo mép trên, dự đoán 2025Q4 (DEV, in-sample) so `d37969ee…`: pearson ≥ 0,99 và spearman ≥ 0,99 (chỉ trên 2025Q4). **G-B2b:** md5 phần bản ghi DEV (byte [4, 4+16·n_DEV) — bỏ header 4 byte n) của pred.bin mới == md5 phần bản ghi của pred.bin DEV seed đó; header n = n_DEV + n_2026; bản ghi 2026 nối sau, ts tăng dần. **G-B2c:** meta ghi `train_ts_max`, n_train, seed, sha model; assert `train_ts_max < SEAL − 15′`.
- **net015 2026 (B3):** predict-only `model_f19_4h.json` (sha256 `83a5333df0f7b1271f90658e81b0e37f4e2b29e681b8d7a37a0526e2b855657d`, cut20251231, train tới 2025-12-27 16:45) trên Tool1 15′ 2026 theo mép DEV [20260101, 20260401) và [20260401, 20260701) +07. Cổng G-B3: cùng kernel tái hiện `predict_wf_20251001.bin` từ `model_f18_4h.json` (sha256 `56dd4a14…`) spearman 1,0 / max|Δ| ≤ 1,2e-7. Không dùng `predict_wf_20251231.bin` (mép lệch).
- **S1 2026 (B4):** `CLOSES_1H` 2026 (`closes1h_build.py`) → feat_v2 tới 2026-07-01 (Kaggle) → ledger (`X1_T1=2026-07-01`, pool = p15 seed 42 của B2, glob nhãn 2026 chỉ để xác định pool như DEV) → predict-only `s1a2x1_cut20251231.json` (sha256 `af706dc654c96f075caddc5f4153c768eec0732a28340cf9adbd6a6f791d8bf1`) → `x1_build_map` → `predict_wf_20260101.bin`, `predict_wf_20260401.bin`; thư mục bins mới = 18 file DEV (nguyên byte) + 2 file. Cổng: G-B4a feat_v2 đoạn ≤ 2025 == `feat_v2_x1` (equal_nan); G-B4b S1 predict 2025Q4 bằng model cut20251231 == ghi chép RESULT_S1REFRESH; G-B4c multiset P(win) từng tick == net015.
- **Ticker 2026 (B6):** dataset Kaggle mới từ Oracle `ticker_2026*.bin.gz` 20260101..20260630 (181 file) + manifest md5, md5 từng file Kaggle == Oracle. `ticker_min_days` holdout = 1826 + 181 = 2007.
- **Symbol 2026 (B6):** liệt kê symbol có trong ticker 2026H1 nhưng không có trong mapper Oracle (863) hoặc `exchange_info_pin.json` (so TÊN) ⇒ loại; báo số + danh sách; không sửa mapper.

## 4. Hiệu chuẩn net015 (đo trên DEV, chốt trước khi đo)

- Bối cảnh: giá trị bins (P(win) net015 gán lại theo hạng S1) vào sim qua `symbolPred`: (a) hệ số gate `factor = max(0,26787, sp/0,15·1,2876)` trong tỷ số r = p15/(factor·1,55) (GateRollingRatio); (b) bản lề trailing 0,29 (STRONG/WEAK). Với 3 cấu hình, TS_MAX_GAP = TS_MAX_GAP_WEAK = 0,03 ⇒ (b) không đổi hành vi; (a) là kênh chính.
- So sánh OOS công bằng: model cut20251231 (`f19`) trên 2025Q4 là in-sample ⇒ không dùng làm thước chính. Thước chính: `model_f18_4h` của CÙNG kernel GPU retrain (cut20251001, recipe y hệt f19) dự đoán 2025Q4 (OOS) — bins dựng lại bằng `x1_build_map` với S1 DEV — vs bins DEV gốc fold 20251001 (`predwf_map_s1a2_x1_2021`).
- **M-cal1 (mô tả):** phân vị P5/25/50/75/95 của sp gốc vs sp' trên mọi (tick, symbol) 2025Q4; tỉ lệ ≤ 0,29; tỉ lệ dưới kink 0,03121; median |log(factor'/factor)|.
- **M-cal2 (QUYẾT ĐỊNH, ngưỡng DỪNG):** tỉ lệ lệnh PREDICT vào trong 2025Q4 của B0 (de-p1/C1) đổi quyết định. Ưu tiên đo bằng kernel DEV seal-đóng (cấu hình C1, funding.bin có đoạn 2025Q4 thay bằng bins sp'): lệnh "đổi" = (symbol, phút vào) có ở run này mà không ở run kia, chia cho n lệnh 2025Q4 của C1. Nếu không dựng được kernel, dùng proxy tĩnh: dựng lại gate GDV2 (r, quantile cuộn 90 ngày PCT 0,999950829, warm-up 7 ngày, buffer = mọi ứng viên PREDICT top-K tại phút có p15) với sp và sp', đếm ứng viên đổi PASS/REJECT chia cho số ứng viên PASS (gốc). Ngưỡng: > 1% ⇒ DỪNG báo MASTER. Báo cả hai nếu có.
- f19 trên 2025Q4 (in-sample) chỉ báo mô tả, không vào ngưỡng.

## 5. Danh sách CẤM dùng (driver assert sha/md5 ∉ danh sách đen)

| Artifact | Định danh | Lý do |
|---|---|---|
| Gate `wfo_models/fold_20` (ONNX live 242/shadow) | md5 `8ec9975726270782692bfe00b39bd37f`, sha256 `d19fc8cddd9fb11778653e4b108bb52da92ea168117efac4a407c18c0f260474` | train 2021-01-01→2026-03-31 (gồm 2026Q1) |
| Gate `model_cut20260701` (`~/claude_master/1002/deploy242/model_cut20260701`) | md5 `b68563febe2a5b7e1bc4505340dfb841`, sha256 `9ba5b0b87b6609e0af232a7eb8f56476af1ef268bb12ff2ea978e3bfb3ae1ca9` | train tới 2026-06-30 |
| `claudedata/wfo_gate_pred_2026_H1.csv` | sha256 `4cc62c14f95fc74aa9f2cd7c2794a30291b0fdabf0dfceec81ae1edda162fdae` | Q2 sinh từ fold_20, chỉ seed 42, purge 0 |
| Gate `wfo_models/fold_19` cho đoạn 2026 | md5 `1f1e6fda8a8e3576f5f9759ce1c8b811` | cut 00:00 UTC, purge 0 ⇒ chứa 7 h đầu 2026 +07 |
| Gate Python cut20260101 `d37969ee…` cho đoạn 2026 | sha256 `d37969eefa93bf93865cd3de78618a4a5b899b6c22e5a06529e30c0c8aeab915` | train tới 2026-01-01 06:44 +07 (chỉ dùng làm thước G-B2a trên 2025Q4) |
| `kg015x26_cut20251231/.../out/predict_wf_20251231.bin` | sha256 `b40586a63925c602dd191130d7eab76ded4f24e98c9bde23d959c76f204b08eb` | mép lệch lịch DEV (chồng 1 ngày, thiếu 03-31) |
| Mọi ONNX/model live 242 / shadow_c3 | — | không chạm 242 ngoài đọc |
| NHÃN 2026: cột `label_*` store gate với ts ≥ SEAL; `ds_label15m/funding_label_2026*` | — | chỉ được dùng tồn-tại-nhãn để xác định pool S1 như DEV (R4); cấm train/đọc giá trị |
| `claudedata/devexport_202609/*`, `feat_dump` live | — | lượt export khác / ngoài cửa sổ |
| Kết quả bất kỳ của 2026 (PnL, phân phối p15/sp 2026, IC 2026) trong vòng HO1 | — | seal đóng |

Danh sách trắng: S1 `af706dc6…` (json), net015 `model_f19_4h.json` `83a5333d…`, 8 model gate mới (meta ghi sha + `train_ts_max`), jar `b7c89f09…`.

## 6. Rủi ro rò rỉ / thiên lệch (khai trước, theo feasibility §6)

- **R1 (CAO, không gỡ được):** 2026H1 từng là VAL trước niêm phong 09-01: thiết kế gate/HPO/fold plan, hằng số HPO GA `AI_DYNAMIC_MIN/MULT` (~2026-05, range không truy được), feature, nhãn đều chốt khi 2026 đang được nhìn ⇒ kết quả holdout = **forward test có nhiễm tầng thiết kế**; chỉ dùng cho rào cứng + dấu ghép cặp giữa 3 cấu hình, không làm bằng chứng edge tuyệt đối.
- **R2 (CAO nếu sơ ý):** nhãn 2026 nằm sẵn trong store gate và `ds_label15m` ⇒ loader 2026 chỉ feature; assert train ts / glob nhãn `202[1-5]`.
- **R3 (CAO):** artifact train có 2026 (mục 5) ⇒ driver assert sha.
- **R4 (THẤP–TB):** pool S1 = coin có nhãn tại tick (availability look-ahead) — giữ y DEV, không đọc giá trị nhãn.
- **R5 (TB):** OI `create_time` — chỉ dùng file ghim `e3887f63`; nếu mép < 2026-06-30 phải dựng thêm theo OI_FIX_LOG §5 (khai báo trước khi dùng).
- **R6 (THẤP):** buffer gate 90 ngày + warm-up đầu 2026 = dữ liệu 2025 (chạy liên tục, hợp lệ).
- **R7 (TB):** mép fold net015 — predict lại theo mép +07; span ≤ 100 ngày, không chồng/khuyết.
- **R8 (TB):** hiệu chuẩn net015 retrain ≠ gốc ⇒ đo mục 4 trước mở seal.
- **R9 (TB):** model đông lạnh ≤ 2025 cho 2 quý (DEV refresh theo quý) — đối xứng 3 cấu hình; báo theo quý; không so mức tuyệt đối với DEV.
- **R10 (TB):** universe 2026 thiếu mapper/pin ⇒ loại (quyết định 6); ffill `CLOSES_1H` giữ y DEV.
- **R11 (TB):** ticker Kaggle 2026 md5 chưa khớp Oracle ⇒ dataset mới + manifest.
- **R12 (CAO):** rò kết quả trước khi khoá luật / chạy lại khi thấy số ⇒ scorer commit trước; `HOLDOUT_UNSEAL` chỉ trong `extra_env` của 48 kernel vòng sau; một lần.
- **R13 (CAO, diễn giải):** 3 cấu hình chọn trên DEV dùng 30+ lần; 8 seed chỉ đo nhiễu model; 6 tháng ≈ 1/9 DEV ⇒ inflate k=3 (√(2 ln 3) ≈ 1,48); thước SIZE = bootstrap return ngày MTM ghép cặp; không dùng ΔCalmar ledger-closed.
- **R14 (THẤP):** cửa sổ H1 không chồng 242 G2FLAT3 (deploy 08-17) / shadow (09-30).
- **R15 (mới, THẤP):** mép train gate holdout chặt hơn DEV ≤ 7 h 15′ (mục 3) — đối xứng 8 seed và 3 cấu hình.

## 7. Thứ tự + điểm dừng vòng HO1

B1 (commit này) → B2 gate 8 seed → B3 net015 2026 → B4 S1/bins 2026 → B5 dataset WFO append (cổng byte DEV) → B6 bundle + ticker 2026h1 + kiểm symbol → B8 parity C1–C3 + hiệu chuẩn net015 (seal đóng). Bất kỳ cổng FAIL ⇒ dừng bước đó, báo MASTER, không vá bằng tune. PASS hết ⇒ DỪNG, báo MASTER. Tiến độ ghi `docs/plan/HOLDOUT2026_PROGRESS.md`.

## ADDENDUM-1 (2026-10-09, MASTER chốt) — chi tiết kỹ thuật, KHÔNG đổi cửa sổ / luật chấm

Viết TRƯỚC khi có bất kỳ số hiệu năng / phân phối / tín hiệu 2026 nào được nhìn (seal vẫn ĐÓNG; đã sinh pred.bin 2026 của gate B2 nhưng chỉ đếm, NaN, md5).

1. **market.bin (G-B5m) = EXPLAINED, chấp nhận.** Set Aerospike `market_data_object` có 2 348 phút DEV trùng `time` (nhiều key, giá trị khác) ⇒ exporter Java last-wins theo thứ tự scan, không tất định; tái sinh Python lệch 8–9 bản ghi/lần, 0 lệch không giải thích được. Đoạn DEV giữ NGUYÊN byte market.bin DEV (md5 `4ab691c9…`), chỉ append 2026 (last-wins theo thứ tự scan, như Java). 2 phút 2026 mơ hồ (ts 1767440640000, 1773372060000) liệt kê trong manifest. Cổng thật = parity B8 trên DEV phải trùng.
2. **SIM_END_DATE=20260701** cho 48 kernel holdout (vòng sau): vòng lặp sim theo ngày UTC (`startTime = TIME_RUN 00:00 +07 + 7h`, dừng khi `startTime > endTime`), nên 20260630 sẽ dừng ở 2026-06-30 06:59 +07. Scorer cắt cửa sổ đúng 2026-01-01 00:00 → 2026-06-30 23:59 +07 (luật mục 1 không đổi). Dữ liệu market/ticker phủ tới hết ngày UTC 2026-06-30; pred/funding 2026 dừng ở 2026-07-01 00:00 +07.
3. **pred.bin:** pred.bin DEV có 420 dòng ≥ 2026-01-01 00:00 +07 (tới 2025-12-31 23:59 UTC, từ fold_18 / seed 42). Bản holdout bỏ 420 dòng này, thay bằng model mới cut 2026-01-01 +07 của chính seed đó; phần bản ghi ts < 2026-01-01 00:00 +07 nguyên byte. Không ảnh hưởng run DEV (sim DEV xử lý tới hết ngày UTC 2025-12-30). Cột predRisk4H 2026 = 0f (fallback `WFOGateRunner`; cột không vào quyết định).
4. **Pool S1 2026** = coin có bản ghi nhãn tại tick 15′ gate mở với `nBars_72h ≥ 288` (chỉ đọc `tEpochMs, symbol, nBars_72h`, KHÔNG đọc giá trị outcome). Cổng G-B4p trên 2025Q4: tập (symbol, tick) theo định nghĩa này phải trùng tập `g1lite.notna()` của ledger DEV ≥ 99% (Jaccard); không đạt ⇒ DỪNG báo MASTER.
5. **feat_v2 dựng theo cửa sổ trên Oracle** (9 feature KEEP của S1, cửa sổ ≤ 30 ngày, warm-up ≥ 31 ngày trước 2025-10-01). Cổng G-B4a: đoạn chồng 2025Q4 so `feat_v2_x1.parquet` — ô có lệch tương đối > 1e-6 (hoặc NaN lệch) chiếm > 0,1% số ô ⇒ DỪNG.
6. **net015 B3** chạy trên Oracle (không Kaggle), giữ lock, RSS ≤ 8G: OI đọc theo khối; file Tool1 chia quý UTC nên cửa sổ fold +07 đọc cả file quý trước. Thứ tự bản ghi trong 1 tick = sort ổn định (ts, symId) (pipeline gốc không xác định thứ tự tie). Cổng G-B3 giữ nguyên.
7. **funding.bin (G-B5f) PASS** byte (`8e57d900…`) bằng bộ ghi Python; bản holdout = 18 bins DEV + 2 bins 2026 trên lưới market holdout, assert đoạn ts < 2026-01-01 00:00 +07 trùng byte DEV.

## ADDENDUM-2 (2026-10-09, MASTER chốt — agent HO2) — cổng hiệu chuẩn + mở seal

Viết và commit TRƯỚC mọi bước HO2. **Tại thời điểm viết: CHƯA nhìn bất kỳ số 2026 nào** (không PnL, không phân phối p15/sp/net015/S1 2026, không printDone/equity 2026). Không đổi cửa sổ / luật chấm mục 1.

1. **C1 (B0 K16) = PASS.** 5 ô lệch (4 `volume` + 1 `quantity`, `docs/result/ho1/b8_diag.json`) có giá trị float32 trùng bit, chỉ khác cách in. Miễn trừ "cách in float" mở rộng cho MỌI cột khi giá trị float32 trùng bit (không chỉ cột volume). Mọi khác biệt khác vẫn FAIL.
2. **Cổng CAL (mục 4, M-cal2 > 1% lệnh DEV) bị đặt sai thước.** Lệch nhỏ mức ô (0,81% ô đổi phía bản lề 0,29; spearman 0,99495) bị khuếch đại thành lệch mức lệnh do phụ thuộc đường đi (vị thế/quota/cooldown), nên mọi lần retrain đều vượt 1% ⇒ ngưỡng không phân biệt được "model khác" với "artifact khác". Thay bằng:
   - **PHƯƠNG ÁN A (ưu tiên):** dùng ĐÚNG artifact model net015 G015x26 GỐC đã sinh bins DEV fold dự đoán 2025Q4 (fold 20251001, train ≤ 2025-09-30 theo lịch DEV) — KHÔNG retrain — predict-only 2026H1 (cùng feature Tool1 / pipeline / mép [20260101,20260401), [20260401,20260701) +07, rồi S1 + `x1_build_map` như B4). **Cổng A:** artifact đó predict lại 2025Q4 ⇒ bins (sau `x1_build_map` với S1 DEV) phải TRÙNG bins DEV fold 20251001 hiện có (byte, hoặc max|Δ| ≤ 1e-6 trên P(win)); đồng thời P(win) net015 thô 2025Q4 trùng nguồn DEV nếu nguồn đó còn. PASS ⇒ chứng minh đúng artifact + đúng pipeline. Hệ quả khai trước: model cũ hơn 3–9 tháng so với 2026H1 (thiên hướng bảo thủ, đối xứng 3 cấu hình).
   - **PHƯƠNG ÁN B (chỉ khi KHÔNG tìm được artifact gốc HOẶC cổng A FAIL):** giữ bins net015 retrain cut20251231 (`bins2026x/`, đã dựng ở HO1). Khai báo: hiệu ứng model lẫn vào mức tuyệt đối (E0); so sánh cấu hình (H-A, H-B) vẫn ghép cặp cùng bins.
   - Phương án được dùng sẽ ghi ở mục 5 dưới (ADDENDUM-2 §5) TRƯỚC khi đẩy kernel holdout. Tìm artifact + cổng A chỉ dùng dữ liệu DEV (≤ 2025-12-31); không so/nhìn giá trị 2026.
3. **Mở seal** sau khi: bins 2026 cuối cùng xong; dựng lại funding.bin/bundle nếu bins đổi (cổng: đoạn < 2026-01-01 +07 trùng byte DEV); chạy lại parity C1–C3 trên DEV (`SIM_END_DATE=20251231`) với bundle cuối, phải PASS như B8 (C1 theo miễn trừ §1; C2 md5 `ad26fd55`; C3 md5 `cbc067f7`). Rồi đẩy **48 kernel** = 3 cấu hình (B0 K16; K24+skipFull; K24+skipFull+NSEL M2 — override y hệt `nsel-m2-s*`) × 8 seed (42/7/13/21/99/123/777/2024, pred.bin holdout `ho26-pred-s*`) × {penalty 0 (`b`); `SIM_CRASH_ENTRY_PENALTY=0.01675` (`s`)}; jar `b7c89f09`; `SIM_END_DATE=20260701`; `ticker_min_days=2007`; dataset `wfo-ticker-2026h1` bản 2; khối TICKER26_MD5 trong kernel so tên `.bin` với md5 gunzip (phải 181/181, sai ⇒ kernel tự dừng trước sim). `HOLDOUT_UNSEAL` chỉ trong `extra_env` của 48 kernel này.
4. **Orchestrator nền trên Oracle** (`~/claude_master/1009/ho26/ho26_queue.py`, bản sao `research/analysis/ho26_queue.py`): state.json resume; tối đa 2 kernel song song; kiểm kernel đang chạy bằng Python API Kaggle; retry 1 lần chỉ khi lỗi hạ tầng (rc≠ok, mapper < 800, timeout) với cfg y hệt; parity tự động mỗi kernel: jar sha, override đúng cấu hình, pred md5 theo seed, TICKER26 181/181, n > 0, dòng `[CRASH-PENALTY]` SUMMARY đúng mức. Out `~/kaggle_sim/out/ho26-<cfg>-<b|s>-s<seed>` (cfg ∈ {b0,k24,m2}). Thứ tự xen kẽ theo seed (6 kernel của cùng seed liền nhau). `queue_status.tsv` chỉ ghi slug/status/md5/n/parity/giờ — KHÔNG eq/PnL, KHÔNG chấm, KHÔNG mở printDone/equity 2026 (việc của 2 scorer độc lập vòng sau, scorer commit trước khi đọc).
5. **Phương án net015 được dùng:** (điền trước khi đẩy kernel holdout).

### ADDENDUM-2 §2a (2026-10-09, trước khi đo cổng A — chưa nhìn số 2026, chưa chạy predict nào)

Kết quả tìm artifact (chỉ liệt kê file, không đọc giá trị):
- JSON gốc `claudedata/predwf_G015/model_f{0..17}_4h.json` (08-14) **không còn trên đĩa** Oracle (thư mục mất; find toàn đĩa không thấy); output kernel Kaggle gốc `selector-15mtr-pred15-net015-gpu` đã bị version lỗi ghi đè (G3_X26_RECOVERY §3.4). Dự đoán gốc `claudedata/predwf_G015x26/` cũng mất trên đĩa, NHƯNG có backup Kaggle `chuyendinh/predwf-g015x26-gate` v1 (MANIFEST sha256; fold 20251001 = `e03f0e58…`, 4 517 610 rec).
- **Artifact dùng cho PHƯƠNG ÁN A:** `/home/ubuntu/deploy_242_l3/models/g015x26_f15_cut20251001.onnx`, sha256 `7921ceaf2405049ddf2c23187264c34d6c95a38125f33c9ef3506f02f4e6dd8b` = ONNX export của CHÍNH booster gốc `predwf_G015/model_f15_4h.json` (fold cut20251001, cây y hệt; ONNX-vs-JSON max|d| 4,619e-7 trên 300k dòng, `research/analysis/g015x26_onnx_gate.py`). Không retrain. Thứ tự 45 input = `feature_order_net015.txt` (40 Tool1 + 5 OI) = `g015_net_train.build_matrix`.
- **Cổng A (chốt trước, chỉ DEV 2025Q4 [20251001, 20260101) +07):**
  - A0: sha256 backup Kaggle fold 20251001 == `e03f0e58…` (manifest G015X26_PROVENANCE §2).
  - A1 (artifact + feature): ONNX predict trên `build_rows` HO1 (Tool1 + OI merge_asof 2h + symbol_map) ⇒ tập khoá (ts,sym) == backup gốc VÀ max|Δp0| ≤ 1e-6 (mọi dòng).
  - A2c (đối chứng pipeline map): `x1_build_map` (S1 DEV `pred_s1a2x1`) trên CHÍNH file gốc backup ⇒ phải == bins DEV `predwf_map_s1a2_x1_2021/predict_wf_20251001.bin` (md5 `5ebae929…`) byte.
  - A2 (bins): giá trị ONNX xếp theo ĐÚNG thứ tự dòng của file gốc (thứ tự gốc không ổn định, chỉ tái hiện được bằng cách theo file gốc), `x1_build_map` S1 DEV ⇒ so bins DEV fold 20251001: khoá trùng, max|Δp0| ≤ 1e-6 mọi ô, p1..p3 trùng bit (NaN==NaN).
  - PASS = A0 ∧ A1 ∧ A2c ∧ A2. Bất kỳ FAIL ⇒ PHƯƠNG ÁN B (không vá, không đổi ngưỡng).
- **2026 theo phương án A:** cùng ONNX predict-only trên `build_rows` 2026 HO1 (mép [20260101,20260401), [20260401,20260701) +07, thứ tự ổn định (ts,symId) như ADDENDUM-1 §6) → `x1_build_map` với S1 2026 (`pred_ho26s1`, giữ nguyên HO1) → G-B4c multiset → loại 3 symbol (như B6) → funding.bin (đoạn < 2026-01-01 +07 == DEV byte) → bundle mới. Chỉ đếm/NaN/khoảng ts/sha cho 2026, không in thống kê giá trị.
