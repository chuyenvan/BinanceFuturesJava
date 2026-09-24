# RESULT_ARM44 — BỎ ĐÚNG **1** CỘT `rvol15m` (45 → 44): train + SIM + chấm trên KEEPLEG0

**Ngày:** 2026-09-25 · **Nhánh:** `module` · **Trạng thái:** ĐO XONG (train + sim 3 kênh + MTM mốc phút + chấm)
**Tiền đăng ký (chốt TRƯỚC, commit trước khi push kernel):** `docs/prereg/PREREG_ARM44.md` — commit **`7eb4c2b`**
**Code:** `7eb4c2b` (pre-reg + `stage2` block cho `fs_v1_44.json`) · **`98269a8`** (`make_arm44_kernel.py` ·
`arm44_sim.py` · `arm44_score.py` · `arm44_ruler45.py`)
**Kernel:** `chuyendinh/g015p2-arm44-gpu` (train, GPU) · `sim-a44-moc` · `sim-a44-a45` · `sim-a44-a44` · `sim-a44-mtm`
**Cửa sổ:** DEV `2021-07-01 .. 2025-12-30` (16 fold OOS 2022+ và 2 fold 2021) · **KHÔNG** chạm
2026/`HoldoutSeal` · **KHÔNG** chạm ONNX/`NUM_FEATURES`/`extractFeatures45`/`shadow_c3` · **KHÔNG** push git
**Chi phí Kaggle:** 1 kernel GPU **79,0 phút** (train) + 4 kernel CPU (**0 quota**) · **KHÔNG** chạy Java/sim trên Oracle

---

## 0. TRẢ LỜI NGẮN

Nền = **FLATGRID KEEPLEG0**; 3 kênh **cùng một cấu hình, chỉ khác thư mục bins** (`WFO_FUNDING_PRED_DIR`).

| kênh | vector | n | equity | SumPnL | maxDD **phút** | UW phút (ngày) | 5 rate vs MỐC | quyết định |
|---|---|---:|---:|---:|---:|---:|---|---|
| **MỐC** (45 feat, deploy) | 45 | 1.085 | 103.083 | 68.083 | −19,96 % | 147,2 | — | mốc |
| **A45** (retrain 45 — *đối chứng chẩn đoán*) | 45 | 1.086 | 95.031 | 60.031 | −20,31 % | 156,0 | 0 TỐT / **1 XẤU** | (không phải ứng viên) |
| **A44** (45 − `rvol15m`) | **44** | 1.103 | 106.250 | 71.250 | **−19,44 %** | **92,6** | **0 TỐT / 0 XẤU** | **NULL** |

- **KẾT LUẬN theo luật §5 pre-reg ⇒ GIỮ 45.** `A44` **không** thoả điều kiện "≥ 2 rate ngoài CI cùng hướng
  TỐT" (đo được **0/5**), nên **không** đủ căn cứ để đổi mốc — dù `A44` **PASS hết rào cứng §7** và
  `maxDD`/`UW` mốc phút **không xấu hơn** MỐC (thực ra tốt hơn: −19,44 % vs −19,96 %; 92,6 vs 147,2 ngày).
- **Bỏ `rvol15m` có làm hệ thống TỆ ĐI không?** — **Ở TẦNG SIM/CHẤT LƯỢNG LỆNH + RÀO RỦI RO: KHÔNG đo được
  tệ đi** (0 rate ngoài CI **cả hai chiều**; `n` +1,7 %; PnL +3,2 k USDT; rào §7 PASS mọi năm). **Nhưng ở
  TẦNG THƯỚC CỦA CHÍNH SELECTOR thì CÓ**: `Δrank-IC(A44−A45) = +0,001965 [+0,001231, +0,002645]` và
  `Δlift@8 = −0,003075 [−0,004005, −0,002141]` — **cả hai ngoài CI 0, đều bất lợi cho A44** ⇒ cột này
  **load-bearing ở kênh XẾP HẠNG** (khớp `DIAG_RVOL15M`: nó đo độ lớn/fat-tail), mà kênh xếp hạng **không**
  được SIM nhìn thấy (sim lấy thứ tự coin từ **S1**, chỉ lấy từ model **multiset `P(win)` cho gate**).
- **Multiplicity:** `k = 1` (đúng **1** ứng viên so MỐC) ⇒ `inflate(1) = 1.0`, CI **không** nở rộng; độ rộng
  quyết định dùng **legacy 1.21** (hằng số có sẵn `gd92xexit_score.LEGACY`, **không** bịa hệ số) — và
  `inflate(2) = 1,17741 < 1.21` nên độ rộng này **đã bao** cả gia đình 2 kênh `{A45, A44}`.

---

## 1. CỔNG — đạt hết (điều kiện đọc số)

| cổng | kết quả |
|---|---|
| **P0** mapper | **863** (≥ 800) ở **cả 3** kernel sim ✓ |
| **P1** MỐC = mốc Kaggle | md5 `printDone.csv` = **`99e42b75cf1a2142f9cd14dc72e371ba`** ✓ · **n = 1.085** ✓ · equity **103.083** ✓ — **PASS kể cả khi bật `CONC_CAP_PERCOIN=15 %`** (dự đoán Q1 **ĐÚNG**) |
| **P2** dựng lại funding byte-faithful | `md5_funding` MỐC = **`8e57d900d5c54c744bfcaf5c9b27fc93`** ✓ · `binsSha256` MỐC = **`407e2aba…`** ✓ (cả 3 kênh: `fold_count = 18`, `fundingCount = 2.301.065`) |
| **P3** đồng nhất dữ liệu | `md5_market`/`md5_pred` = `4ab691c908fc…` / `5dd6bb4c3f98…` **ở cả 3 kênh** (copy nguyên byte từ bundle) ✓ · `sc_sha256` = `2618fe1a0235…` (cùng ranker S1) ✓ |
| **P4** MTM mốc phút tái lập | MỐC: minute maxDD **−19,96 %**, UW **147,2 ngày** = **đúng số đã công bố** của KEEPLEG0 (`RESULT_INTRADAY_DD` §3.1) ✓ · 4 cổng nghiệm thu `s3_intraday` PASS ở **cả 3 kênh** (V1 ≤ 1 USDT: 0,18 / −0,02 / 0,33 · V2-rel ≤ 0,05 %: 0,0129 / 0,0139 / 0,0127 % · V3 ≤ 1 %: 0,001 % · V5 ≤ 0,1 pp: 0,001) |
| **P5** jar | sha256 `2c2f8aef78c98470fdc3b0d464edd7ec2c604a7589985b1f4211c1da05fcdca0` (cả 3 kênh) ✓ |

---

## 2. TRAIN ARM 44 — `CROSS_ARM_OK` PASS

`g015_net_train_add.py` (**không** `--add-feats` ⇒ `NF=45`, hành vi gốc), `--arms "A45:;A44:36"`,
16 fold DEV, seed 42, `device=cuda`, xgboost 3.2.0, **1 lần dựng ma trận**, `TRAIN_MINUTES = 79,0`.

- **`CROSS_ARM_OK = True`**: `n_train`/`pos`/`spw`/`n_oos` của **A44 khớp TUYỆT ĐỐI A45 ở cả 16 fold**
  (`mismatch = {}`). ⇒ bỏ 1 cột **không** đổi tập dòng/nhãn/split (đúng cơ chế `--drop-cols`).
- `num_feature` = **45 (A45) / 44 (A44)**; `drop_cols` = `[]` / `[36]`.
- **Đối chiếu độc lập (cùng nguồn hạ tầng Kaggle)**: fold `20220101` cho `n_train = 3.730.472`,
  `pos = 0,26989`, `spw = 2,705276`, `n_oos = 1.123.854` — **khớp từng con số** bảng `RESULT_STAGE2_TRAIN` §1
  (dự đoán Q2 **ĐÚNG**). `spw` tăng 2,705276 → **4,287861** theo expanding (đúng quy luật đã ghi).
- **Trainer sha256** `c0bedf5abe0c84b8…` (nhúng nguyên văn trong kernel) · 16 `model_f<fidx>_4h.json` +
  16 `predict_wf_<cutoff>.bin` mỗi arm (fidx theo vị trí trong `CUT_DATES`, khớp theo **cutoff**).

---

## 3. CƠ CHẾ + CHẤT LƯỢNG LỆNH

| kênh | n | win% | TSloss% | mP\|SM | mP\|SL | meanP | hold_med (h) | turn (lệnh/ngày) | Σfunding | ΣPnL | Σfund/ΣPnL |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| MỐC | 1.085 | 88,20 | 10,32 | **7,961** | −19,300 | **5,147** | 5,0 | 0,660 | −2.359 | 68.083 | −3,46 % |
| A45 | 1.086 | 88,12 | 10,22 | 7,887 | −21,362 | 4,897 | 4,8 | 0,661 | −2.472 | 60.031 | −4,12 % |
| A44 | 1.103 | 88,58 | 9,79 | 7,935 | −20,590 | 5,142 | 5,4 | 0,671 | −2.874 | 71.250 | −4,03 % |

- **Vì sao 3 kênh khác nhau (kênh GATE):** `symbolPred` (= `1−P(win)`) lệch hệ thống giữa các model ⇒
  `dyn_thr = SIM_MIN_MOMENTUM_15M · max(MIN, symbolPred/0,15 · MULT)` lệch ⇒ số lệnh lệch
  (`n`: 1.085 / 1.086 / 1.103). Đây là **kênh HIỆU CHUẨN của model**, khớp `RESULT_G4`.
- **2021H2 GIỐNG HỆT TUYỆT ĐỐI ở cả 3 kênh** (149 lệnh / +4.273 / +12,21 % / maxDD phút −11,05 %) — đúng
  thiết kế (2 fold 2021 dùng chung bins của MỐC) ⇒ khác biệt **chỉ** đến từ **16 fold 2022+**.

---

## 4. 5 RATE + CI (ghép cặp block-72h, 2.000 rep, seed 20260905) — cách xử lý `k = 1` nói RÕ

`k = 1` ⇒ `c3_rates.inflate(1) = 1,0` **vô nghĩa** về mặt nở rộng ⇒ báo **CẢ HAI** độ rộng: CI **gốc**
(`×1,0`) và **legacy `1,21`** (`gd92xexit_score.LEGACY` — hằng số dùng ở **mọi** vòng trước, **không** phải
hệ số dựng thêm ở vòng này). **"Ngoài CI" = ngoài CẢ HAI** ⇒ thực chất ngoài **1,21** (bảo thủ).

| so | win% | TSloss% | mP\|SM | mP\|SL | meanP | TỐT/XẤU |
|---|---|---|---|---|---|---|
| **A44 − MỐC (CHÍNH)** | +0,374 [−1,212; +2,249] | −0,531 [−2,586; +1,175] | −0,025 [−0,451; +0,450] | −1,290 [−5,479; +2,629] | −0,004 [−0,615; +0,705] | **0 TỐT / 0 XẤU** |
| **A45 − MỐC** *(chẩn đoán — nền nhiễu retrain)* | −0,081 [−1,735; +1,395] | −0,102 [−1,619; +1,476] | −0,074 [−0,362; +0,184] | **−2,063 [−4,527; −0,064]** | −0,249 [−0,806; +0,181] | 0 TỐT / **1 XẤU** |
| **A44 − A45** *(hiệu ứng THUẦN của việc bỏ 1 cột)* | +0,455 [−1,217; +2,631] | −0,430 [−2,764; +1,515] | +0,048 [−0,409; +0,546] | +0,772 [−3,426; +5,054] | +0,245 [−0,535; +1,166] | 0 TỐT / 0 XẤU |

- **Điểm quan trọng nhất:** kênh **đối chứng retrain** (A45 — cùng kernel, cùng seed, cùng ma trận, **cùng
  45 cột**) lại có **1 rate XẤU ngoài CI** (`mP|SL`). Nghĩa là **nền nhiễu retrain/máy** đã đủ lớn để tạo ra
  một chênh lệch "đo được" — nên `A44 ≈ MỐC` (0/5) **không** được đọc thành "bỏ cột là an toàn", mà đọc
  thành **"SIM không phân biệt được 44 vs 45 ở tầng chất lượng lệnh"**.
- `mP|SL` có CI rộng nhất (±5 USDT) vì số lệnh STOP_LOSS ít.
- `n` và `mMargin` **không** phải quality rate (dự đoán Q7: `n` lệch +1,7 % < 20 % ✓;
  `Σfund/ΣPnL` trải −3,46 … −4,12 % = 0,66 pp < 5 pp ✓).

---

## 5. RÀO CỨNG `RISK_APPETITE.md` §7 — **theo năm** VÀ **toàn kỳ** (maxDD/UW trên MTM MỐC PHÚT)

| kênh | maxDD phút toàn kỳ | UW phút (ngày) | maxDD phút P=bar.low | quý xấu nhất | năm âm | conc 1 coin | **RÀO (năm + toàn kỳ)** |
|---|---:|---:|---:|---:|---:|---:|---|
| MỐC | −19,96 % *(ngày −11,21 %)* | 147,2 | −24,16 % | −1,08 % | 0 | 7,12 % | **PASS** |
| A45 | −20,31 % *(ngày −10,57 %)* | 156,0 | −24,49 % | −3,02 % | 0 | 7,21 % | **PASS** |
| A44 | **−19,44 %** *(ngày −8,48 %)* | **92,6** | −23,31 % | −0,32 % | 0 | 10,02 % | **PASS** |

Theo năm (`maxDD_phút% / UW_phút ngày / ret% / qmin%`, ngưỡng 40 % · 250 · ≥ −20 % · ≥ 0):

| kênh | 2021H2 | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|
| MỐC | −11,05/37,0/+12,21/+4,44 P | −15,43/74,0/+12,59/−1,08 P | −5,03/64,4/+34,96/−0,37 P | −12,16/91,5/+32,13/−0,92 P | −19,96/129,0/+30,81/+1,27 P |
| A45 | −11,05/37,0/+12,21/+4,44 P | −15,36/103,2/+12,37/−1,14 P | −5,36/87,1/+28,23/−0,13 P | −13,69/117,7/+27,94/−3,02 P | −20,31/128,9/+31,25/+1,28 P |
| A44 | −11,05/37,0/+12,21/+4,44 P | −15,75/74,2/+17,86/+2,77 P | −3,46/47,5/+37,74/+0,27 P | −12,18/85,0/+35,99/−0,32 P | −19,44/92,6/+22,55/+1,19 P |

- Chuỗi NGÀY che mất **7,3–8,8 pp** drawdown (MỐC −11,21 % ngày vs −19,96 % phút) — đúng như `RESULT_INTRADAY_DD`.
- `A44` **không xấu hơn** MỐC ở `maxDD`/`UW` mốc phút (điều kiện (4) của luật §5: **thoả**).
- **PASS toàn bộ** ⇒ rào rủi ro **không** phải chỗ phá vỡ (giống vòng Stage 3).

---

## 6. BẢNG PnL CHI TIẾT THEO NĂM (n + PnL USDT) + TOTAL

| kênh | 2021H2 | 2022 | 2023 | 2024 | 2025 | **TOTAL** | equity cuối |
|---|---|---|---|---|---|---|---|
| MỐC | 149 / +4.273 | 196 / +4.943 | 126 / +15.376 | 281 / +19.210 | 333 / +24.282 | **1.085 / +68.083** | 103.083 |
| A45 | 149 / +4.273 | 190 / +4.858 | 133 / +12.458 | 278 / +15.813 | 336 / +22.629 | **1.086 / +60.031** | 95.031 |
| A44 | 149 / +4.273 | 197 / +7.014 | 127 / +17.468 | 286 / +22.943 | 344 / +19.553 | **1.103 / +71.250** | 106.250 |

- **`equity` KHÔNG phải tiêu chí** (`AGENT_RUNBOOK` §0). `A44` cao hơn MỐC **+3,2 k USDT** và cao hơn
  **A45 +11,2 k** — nhưng vì **0 rate ngoài CI**, đây **không** được coi là "tốt hơn".
- Chênh PnL của `A44` so MỐC tập trung ở **2022–2024** (+2,1 / +2,1 / +3,7 k) và **kém hơn ở 2025**
  (−4,7 k) — cùng dạng "đổi vị trí năm" đã thấy ở vòng Stage 3 ⇒ **không** đọc thành cải thiện.

---

## 7. THƯỚC CỦA CHÍNH SELECTOR — rank-IC cross-section + top-8 lift@8 (16 fold OOS)

Định nghĩa y vòng Stage 2 (`p0` vs `retEnd_4h`, chỉ tick ≥ 2 coin, `THR = 0,015`).
Ruler của **A44/A45** đo **trong kernel** từ bins **giá trị** của chính arm; ruler của **45 bản deploy**
(`claudedata/predwf_G015x26`, 16 fold) đo **offline trên Oracle** bằng **đúng đoạn code đó** + **đúng file
nhãn đó** (đã kiểm: 20 file `.pb` của dataset `chuyendinh/funding-label-15m` **trùng tên, trùng byte, và
md5 trùng** với `/home/ubuntu/label_15m`) — *provenance khai báo rõ, không trộn vào 1 cột*.

| kênh | n_tick | số coin/tick | rank-IC | CI 72h | lift@8 | CI 72h |
|---|---:|---:|---:|---|---:|---|
| 45 deploy (tham chiếu) | 140.238 | 255,2 | −0,051110 | — | +0,110510 | — |
| A45 (retrain 45) | 140.238 | 255,2 | −0,051061 | [−0,054141, −0,047824] | +0,110850 | [+0,105269, +0,116330] |
| A44 (44 cột) | 140.238 | 255,2 | **−0,049096** | [−0,052062, −0,045881] | **+0,107775** | [+0,102423, +0,113185] |

| so (ghép cặp theo tick) | Δrank-IC | Δlift@8 | ngoài 0? |
|---|---|---|---|
| A45 − 45deploy | +0,000050 [−0,000279, +0,000426] | +0,000340 [−0,000332, +0,001004] | không (retrain **tái lập được**) |
| **A44 − 45deploy** | **+0,002014 [+0,001289, +0,002724]** | **−0,002735 [−0,003666, −0,001747]** | **CÓ — cả hai, ĐỀU BẤT LỢI cho A44** |
| **A44 − A45** (*thuần bỏ 1 cột*) | **+0,001965 [+0,001231, +0,002645]** | **−0,003075 [−0,004005, −0,002141]** | **CÓ — cả hai, ĐỀU BẤT LỢI cho A44** |

- `rank-IC` của mọi kênh đều **ÂM** (momentum/vol dài hạn tương quan âm với `retEnd_4h`) ⇒ "tệ hơn" =
  |IC| **nhỏ hơn** = `ΔIC` **dương hơn**. `A44` mất **0,00197** độ lớn IC và **0,00308** lift@8.
- **A45 ≈ 45deploy** trên ruler ⇒ phép retrain **trung thực ở tầng xếp hạng** ⇒ chênh lệch của `A44`
  **không** quy cho retrain/máy mà quy cho **việc bỏ cột** (dự đoán Q6 **ĐÚNG**: khác biệt — nếu có —
  **bất lợi** cho A44).

---

## 8. ĐỐI CHIẾU DỰ ĐOÁN KHOÁ TRƯỚC (pre-reg §6 — KHÔNG sửa pre-reg sau khi xem số)

| # | Dự đoán (chốt trước) | Kết quả |
|---|---|---|
| Q1 | P1 PASS **kể cả khi bật `CONC_CAP_PERCOIN`** | **ĐÚNG** (md5 `99e42b75…`, 1.085 leg, 103.083) |
| Q2 | `CROSS_ARM_OK` PASS + fold `20220101` khớp `RESULT_STAGE2_TRAIN` §1 | **ĐÚNG** (khớp tuyệt đối 16 fold) |
| Q3 | **A44 ≈ MỐC** ở 5 rate (0 rate ngoài CI, hoặc ≤ 1 và không phải `mP\|SM`/`meanP`) | **ĐÚNG** (0/5) |
| Q4 | Nền nhiễu retrain **A45 ≈ MỐC** (0 rate ngoài CI) | **SAI** — A45 có **1 XẤU** (`mP\|SL`) |
| Q5 | Cả 3 kênh PASS rào cứng §7 | **ĐÚNG** |
| Q6 | Ruler: nếu có khác biệt thì **bất lợi cho A44** | **ĐÚNG** (cả 2 metric ngoài CI, đều bất lợi) |
| Q7 | `n` lệch < 20 %; `Σfund/ΣPnL` lệch < 5 pp | **ĐÚNG** (+1,7 %; 0,66 pp) |

> **Q4 SAI là kết quả chẩn đoán quan trọng nhất của vòng này**: vòng Stage 2/3 từng cảnh báo "đối chứng nhiễu
> cũng thắng y như feature thật"; ở đây hiện tượng **tương tự nhưng ngược chiều** — **đối chứng retrain cũng
> "thua" y như arm cần kiểm chứng**. Hệ quả đọc số: mọi chênh lệch `A44 ↔ MỐC` **nhỏ hơn hoặc bằng** nền
> nhiễu retrain ⇒ **không** được quy cho cột `rvol15m`; chỉ chênh lệch `A44 ↔ A45` (cùng phiên) mới đọc được,
> và nó **không** ra ngoài CI ở bất kỳ rate nào.

---

## 9. KẾT LUẬN THEO LUẬT §5 + TRẢ LỜI

| kênh | n | TỐT/5 | XẤU/5 | rào năm | rào toàn kỳ | maxDD/UW ≤ MỐC | **quyết định** |
|---|---:|---:|---:|---|---|---|---|
| **A44** | 1.103 | 0 | 0 | PASS | PASS | **CÓ** | **NULL ⇒ GIỮ 45** |
| A45 *(chẩn đoán)* | 1.086 | 0 | 1 | PASS | PASS | không | — |

**(1) Bỏ đúng `rvol15m` có làm hệ thống tệ đi không?**
- **Theo SIM (thước CHÍNH của pre-reg): KHÔNG đo được tệ đi.** 0/5 rate ngoài CI **cả hai chiều**, rào cứng
  §7 PASS mọi năm + toàn kỳ, `maxDD`/`UW` mốc phút **tốt hơn** MỐC. Về mặt "chất lượng lệnh + rủi ro",
  `A44 ≈ MỐC` — nhưng đúng nghĩa **"không phân biệt được"**, **không** phải "tốt hơn" (equity cao hơn là
  **info**, và `n` lệch +1,7 %).
- **Theo THƯỚC CỦA CHÍNH SELECTOR: CÓ tệ đi, và đo được** (`rank-IC` và `lift@8` **đều ngoài CI**, đều bất
  lợi cho A44, kể cả khi so với **đối chứng retrain cùng phiên** A45). ⇒ `rvol15m` **có** giá trị thật, nằm ở
  **kênh xếp hạng/định thời** — kênh mà SIM **không** nhìn thấy vì SIM lấy **thứ tự coin từ S1** và chỉ lấy
  từ model **multiset `P(win)` cho gate** (giới hạn đã khai báo ở `RESULT_STAGE3_SIM` §7.2).
- Hai thước **không** mâu thuẫn: chúng đo hai kênh khác nhau; chỗ duy nhất chúng "chạm" nhau (gate calibration)
  cho 0/5.

**(2) GIỮ 44 hay GIỮ 45? ⇒ GIỮ 45.** Luật §5 đòi **≥ 2 rate ngoài CI cùng hướng TỐT**; đo được **0**.
Không có căn cứ để đổi mốc, trong khi **có** bằng chứng bất lợi ở thước selector. Giữ nguyên 45 như đang chạy.

**(3) Có tự tích hợp / đổi ONNX không? ⇒ KHÔNG (và vòng này KHÔNG làm).** Đổi `NUM_FEATURES = 45 → 44` +
`extractFeatures45` + re-export `Funding_Classifier_Final.onnx` = **đụng đường LIVE**, cần **owner duyệt
riêng** kèm kế hoạch rollback. Vòng này chỉ tạo **bins offline**; `shadow_c3/` không bị chạm.

---

## 10. GIỚI HẠN / KHAI BÁO SAI LỆCH (ghi rõ, không giấu)

1. **2 fold 2021 dùng bins của MỐC cho MỌI kênh** (arm chỉ có 16 fold 2022+) ⇒ kết luận chỉ nói về
   **16 fold 2022+**; 2021H2 byte-identical giữa 3 kênh (đã kiểm bằng số ở §3/§6).
2. **Kênh đo là kênh HIỆU CHUẨN/GATE**, không phải kênh CHỌN COIN (`c4_build_map s1a2x1` giữ thứ tự coin = S1
   và chỉ thay multiset `P(win)`). Đây chính là lý do SIM NULL trong khi ruler selector xấu đi — **không**
   được đọc thành "bỏ cột vô hại".
3. **A44 khác MỐC 2 thứ**: (a) bỏ 1 cột **và** (b) **train lại** (cùng recipe/seed/fold/device). Vòng này
   **tách được** phần lớn nhờ kênh **A45** (retrain 45 cùng kernel): `A44 − A45` là hiệu ứng thuần của cột.
4. **`maxDD`/`UW` phút** là **MỘT quan sát lịch sử**, không có CI (không bootstrap được cho cực trị).
5. **`k = 1`** đã khai báo trước; các so sánh `A45−MỐC` và `A44−A45` là **chẩn đoán**, báo cùng độ rộng
   **1,21** (đã bao `inflate(2) = 1,17741`), **không** dùng để "GIỮ/ĐỔI".
6. **`CONC_CAP_PERCOIN=15 %`** đã bật trong cả 3 kênh (đúng `profiles/t170_flat_keepleg0.properties`); đo được
   là **no-op** (P1 vẫn PASS) ⇒ không cần chạy lại cấu hình không cap (nhánh fallback của pre-reg §1.3
   **không phải dùng**).
7. **Không** chạy: 2026/`HoldoutSeal`, `juice`, V0/V1/V5 của vòng trước, ONNX/`NUM_FEATURES`/`shadow_c3`,
   không push git.
8. **Ruler 45 deploy** đọc từ bins **giá trị** `claudedata/predwf_G015x26` trên Oracle (offline, thuần Python);
   ruler A44/A45 đọc trong kernel. Nhãn **cùng nguồn** (md5 trùng 2/2 file kiểm mẫu; 20/20 trùng tên + byte).
   Ruler **không** thay thế sim (đã ghi ở `RESULT_STAGE2_TRAIN` §8).

---

## 11. NƠI LƯU ARTIFACT

| gì | ở đâu |
|---|---|
| `printDone.csv` + `sim.out` + `result.json` 3 kênh | `/home/ubuntu/kaggle_sim/out/sim-a44-{moc,a45,a44}/` (kéo từ kernel) |
| MTM mốc phút 3 kênh + cổng nghiệm thu | `/home/ubuntu/kaggle_sim/out/sim-a44-mtm/mtm_result.json` (+ `.../run_*/`) |
| Bảng chấm điểm đầy đủ | `/home/ubuntu/kaggle_sim/out/arm44_score.json` · `arm44_score.txt` (bản gốc `/tmp/arm44_score.{json,txt}`) |
| Report train (cross_arm, metric, từng fold) | `/home/ubuntu/kaggle_sim/out/arm44-train/arm44_train_report.json` + `stage2/A4{4,5}/…` |
| Per-tick ruler (A45/A44) + ruler 45 deploy | `/home/ubuntu/kaggle_sim/out/a44out/{A45,A44,45deploy}_perfold_ticks.parquet` + `arm44_ruler45.json` |
| Kernel | `chuyendinh/g015p2-arm44-gpu` · `sim-a44-{moc,a45,a44}` · `sim-a44-mtm` |
| Bins 2 arm (nguồn sim; KHÔNG tải về) | kernel `chuyendinh/g015p2-arm44-gpu` → `stage2/A4{4,5}/predict_wf_*.bin` |
| Thời gian | train GPU **79,0 phút** · mỗi sim CPU ~**30 phút** (3 kernel **song song**) · MTM **543 s** |
| Chi phí | **GPU 1,3 h** (duy nhất phần tính quota) · CPU kernel **0 quota** · **không** chạy gì trên Oracle ngoài Python offline |

*Sinh bởi `research/analysis/arm44_score.py` (chấm) + `research/analysis/arm44_ruler45.py` (ruler 45 deploy).*
