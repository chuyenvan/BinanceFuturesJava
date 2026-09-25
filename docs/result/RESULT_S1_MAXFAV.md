# RESULT_S1_MAXFAV — Đổi NHÃN của đường S1 sang họ `maxFav` (`K = 3` nhãn), 1 vòng đối chứng

**Ngày:** 2026-09-25 · **Nhánh:** `module` · **Pre-reg:** `docs/prereg/PREREG_S1_MAXFAV.md` (`e68fcd2`,
viết TRƯỚC khi đọc số) · **KHÔNG push.**
**Phạm vi:** DEV only, **16 fold** như mọi vòng trước (`2021-12-31 .. 2025-12-31`; nhãn cắt `< 2026-01-01`).
**KHÔNG** chạm ONNX deploy / `NUM_FEATURES` / `extractFeatures45` / đường LIVE / `HoldoutSeal`.

---

## 0. KẾT LUẬN NGẮN (3 câu trả lời bắt buộc)

1. **Thước NHÃN:** CÓ cải thiện, **nhưng KHÔNG đạt luật §5(A)** (0/3 arm PASS). Cải thiện chỉ ở **mức
   top-8** (`glift8`/`netm8`) và **không đồng thời** ở `ic`/`pacc` so với **cả hai** đối chứng.
   `MFC4` mạnh nhất ở thước nhãn (`glift8` +0,0864/+0,1086 vs A45 +0,0789/+0,0990; Δ vs A45 **ngoài CI
   ở CẢ 5 chỉ số** trên `g1lite72`, **cả 5 ngoài CI** trên `lab72`) nhưng **trượt `ic`/`pacc` vs `V5`**
   (Δ trong CI) ⇒ không PASS.
2. **Thước TIỀN:** **KHÔNG.** Ở **trục KINH TẾ** (`Δglift8`, `Δnetm8`), **0/3 arm** có Δ ngoài CI so với
   **CẢ HAI** đối chứng; `netm8` của cả 3 arm **vẫn ÂM** (−0,0063 / −0,0042 / −0,0085 so với A45 −0,0049
   và 45deploy −0,0053). Có cải thiện **trục THỨ TỰ** (`ic`/`pacc`/`dec_mono` ngoài CI vs cả 2 đối
   chứng) ở `MFB72` (`money72`: Δic +0,0105`*`/+0,0204`*`, Δpacc +0,0038`*`/+0,0074`*`) và một phần ở
   `MFC72` — **nhưng không chuyển thành tiền** (§4). Trên **PnL luật thoát**: Δglift8 **trong CI** cho cả
   2 arm; `MFC72` **KÉM** cả 4 đối chứng (−0,0015…−0,0020).
3. **Kết luận dứt khoát:** **KHÔNG đáng đổi nhãn trainer, KHÔNG đổi model.** `MFC4` là ca rõ nhất của
   "kỹ năng nhãn ≠ kỹ năng tiền": **đứng nhất ở cả 2 thước NHÃN** và **đứng bét ở thước TIỀN**
   (Δ vs A45 **âm ngoài CI trên CẢ 5 chỉ số**, `netm8` −0,0085 = tệ nhất). **GIỮ NGUYÊN** ONNX
   `s1a2x1_cut20251001.onnx` / nhãn `g1lite` / 45 feature. ⚠️ Không có cơ sở nào để chạm đường LIVE.
   **Đây là BƯỚC CUỐI của trục "đổi nhãn"** (đã thử: `g1lite` (deploy) · `retEnd_h` · PnL luật thoát ·
   `maxFav` trần × 3 horizon/ngưỡng — **tất cả NULL ở trục tiền**).

---

## 1. ĐÃ LÀM GÌ (đúng pre-reg, không lệch)

| mục | thực hiện |
|---|---|
| nhãn (i) `MFC72` | `y = maxFav_72h` LIÊN TỤC (`--label-mode maxfav --label-h 72 --label-kind cont`) — `XGBRegressor(reg:squarederror)` |
| nhãn (ii) `MFB72` | `y = (maxFav_72h ≥ 0,07)` (`--label-kind bin --thr 0.07`) — `XGBClassifier(binary:logistic)` |
| nhãn (iii) `MFC4` | `y = maxFav_4h` LIÊN TỤC (`--label-h 4 --label-kind cont`) |
| đặc trưng | 45 cột, **KHÔNG** thêm/bớt |
| fold / seed | 16 fold `20220101..20251001`, purge 72h, `seed 42 / nest 400`, hyperparam y nguyên |
| cơ chế | **chỉ THÊM option** dùng các cờ đã có của `load_labels` — **không sửa** đường `bin` cũ |
| code chạy | kernel nhúng **đúng code đã commit** (`trainer sha256 e8765b493ed8aadd…`) |

**Xác nhận nhãn TẠI CHỖ (log kernel, chống nhầm cột):** `Label 72h (maxfav kind=cont): 39.251.704 dòng
| mean=0,090258` · `Label 72h (maxfav kind=bin thr=0.0700): 39.251.704 dòng | mean=0,409334` ·
`Label 4h (maxfav kind=cont): 39.614.851 dòng | mean=0,018746`.
⇒ khớp **đúng dự đoán khai trước** (§8: ~0,08 / ~0,39) và **KHÁC HẲN** đường cũ
(`retEnd_72h` mean < 0; `retEnd_4h>0,015` base 0,2699) ⇒ **nhãn đã đổi thật**, không dán nhãn sai.

## 2. CHI PHÍ / NƠI CHẠY

- **KAGGLE GPU** (`chuyendinh/mf-train-gpu`, private, 3 arm trong **1 session**):
  `MFC72 40,7′` + `MFB72 42,1′` + `MFC4 41,0′` = **123,8 phút GPU**; tổng wall-time kernel **≈ 132′** (< 12h cap).
- Oracle chỉ bước **NHẸ**: chấm (đọc bins + `.pb`, không train/sim/Java).
- **1 kernel DƯ (hedge)** đã push lúc 22:25 khi kernel chính chạy quá lâu (`mf-train2-gpu`, chỉ `MFC72`) —
  dùng làm **kiểm tính lặp lại giữa 2 session Kaggle** (§9). Không train gì trên Oracle.

## 3. ARTIFACT (đường dẫn RÕ)

| gì | ở đâu |
|---|---|
| bins + model + summary 3 arm | `/home/ubuntu/mfout/mf/{MFC72,MFB72,MFC4}/predict_wf_<cutoff>.bin` + `model_f*.json` + `net_train_summary.json` (≈ 2,7 GB) |
| log kernel | `/home/ubuntu/mfout/mf-train-gpu.log.gz` |
| report train (minutes/sha_bin/n_train/n_oos) | `/home/ubuntu/mfout/mf_train_report.json` |
| JSON chấm 2 thước | `docs/result/s1_maxfav_score.json` |
| JSON chấm PnL luật thoát | `docs/result/s1_maxfav_pnl.json` |
| kernel sinh artifact | `research/kaggle/s1_maxfav/make_mf_kernels.py` |
| driver chấm | `research/analysis/s1_maxfav_score.py` (+ `mr_pnl_score.py` thêm cờ `--slot3-arms`) |

`sha_bin` fold đầu/cuối: `MFC72 1be21031…/a468a172…` · `MFB72 e56f507b…/a889589c…` · `MFC4 0a7b3566…/1292c52a…`.

---

## 4. BẢNG CHÍNH — 2 THƯỚC (mean; `*` = ngoài **CẢ HAI** độ rộng raw + honest `inflate(k=3)` = **1,482304**)

### 4.1 THƯỚC NHÃN — `y = g1lite` (nhãn live ranker) và `y = maxFav_72h` (CHẠM)

| arm | `ic` | `pacc` | `dec_mono` | `glift8` | `netm8` |
|---|---|---|---|---|---|
| **ruler `g1lite72`** (`n_tick = 140.237`) | | | | | |
| 45deploy | +0,0932`*` | +0,5307`*` | +0,5643`*` | +0,0786`*` | +0,0868`*` |
| A45 *(đối chứng retrain)* | +0,0931`*` | +0,5307`*` | +0,5645`*` | +0,0789`*` | +0,0871`*` |
| V5 *(đối chứng nhiễu)* | +0,0950`*` | +0,5312`*` | +0,5652`*` | +0,0736`*` | +0,0818`*` |
| V1 | +0,0944`*` | +0,5310`*` | +0,5655`*` | +0,0746`*` | +0,0828`*` |
| **MFC72** (`maxFav_72h` liên tục) | +0,0943`*` | +0,5312`*` | +0,5662`*` | **+0,0810`*`** | **+0,0892`*`** |
| **MFB72** (`≥0,07`) | +0,0884`*` | +0,5293`*` | +0,5611`*` | +0,0765`*` | +0,0848`*` |
| **MFC4** (`maxFav_4h`) | **+0,0984`*`** | **+0,5325`*`** | **+0,5689`*`** | **+0,0864`*`** | **+0,0946`*`** |
| **ruler `lab72`** (`y = maxFav_72h`) | | | | | |
| 45deploy | +0,2434`*` | +0,5847`*` | +0,6321`*` | +0,0988`*` | +0,1731`*` |
| A45 | +0,2429`*` | +0,5845`*` | +0,6322`*` | +0,0990`*` | +0,1733`*` |
| V5 | **+0,2601`*`** | **+0,5909`*`** | **+0,6395`*`** | +0,0946`*` | +0,1689`*` |
| V1 | +0,2596`*` | +0,5907`*` | +0,6402`*` | +0,0956`*` | +0,1698`*` |
| **MFC72** | +0,2267`*` | +0,5785`*` | +0,6295`*` | **+0,1016`*`** | **+0,1759`*`** |
| **MFB72** | +0,2195`*` | +0,5759`*` | +0,6223`*` | +0,0960`*` | +0,1703`*` |
| **MFC4** | +0,2570`*` | +0,5897`*` | +0,6420`*` | **+0,1086`*`** | **+0,1828`*`** |

### 4.2 THƯỚC TIỀN — `y = retEnd_72h` (gross; `netm8` đã trừ phí 0,008 trong `tick_metrics`)

| arm | `ic` | `pacc` | `dec_mono` | `glift8` | `netm8` |
|---|---|---|---|---|---|
| 45deploy | −0,0856`*` | +0,4701`*` | +0,4892`*` | +0,0039 | −0,0053 |
| A45 *(đối chứng retrain)* | −0,0851`*` | +0,4702`*` | +0,4898`*` | +0,0043 | −0,0049 |
| V5 *(đối chứng nhiễu)* | −0,0950`*` | +0,4666`*` | +0,4876`*` | +0,0032 | −0,0061 |
| V1 | −0,0957`*` | +0,4663`*` | +0,4880`*` | +0,0037 | −0,0055 |
| **MFC72** | −0,0808`*` | +0,4718`*` | +0,4896`*` | +0,0029 | **−0,0063** |
| **MFB72** | **−0,0746`*`** | **+0,4740`*`** | **+0,4900`*`** | **+0,0050** | **−0,0042** |
| **MFC4** | −0,0985`*` | +0,4655`*` | +0,4872`*` | +0,0007 | **−0,0085** |

> Đọc đúng: trên thước TIỀN, **`MFB72` nhích nhất** ở trục THỨ TỰ (`ic`/`pacc`/`dec_mono` cao nhất
> trong 7 arm) và `glift8` +0,0050 > A45 +0,0043 — **nhưng `netm8` vẫn ÂM** và **Δ không ngoài CI** (§5).

---

## 5. BẢNG Δ vs HAI ĐỐI CHỨNG BẮT BUỘC (`*` = ngoài CI raw + honest k=3; `+` = ngoài CI 1,21 legacy)

| Δ (ngoài CI ⇔ `*`) | `ic` | `pacc` | `dec_mono` | `glift8` | `netm8` |
|---|---|---|---|---|---|
| **`g1lite72`** | | | | | |
| MFC72 − A45 | +0,00114 | +0,00053 | +0,00169 | +0,00211 | +0,00211 |
| MFC72 − V5 | −0,00075 | +0,00001 | +0,00101 | **+0,00737`*`** | **+0,00737`*`** |
| MFB72 − A45 | −0,00474`*` | −0,00145`+` | −0,00344`*` | −0,00231 | −0,00231 |
| MFB72 − V5 | −0,00664`+` | −0,00197 | −0,00413`*` | +0,00295 | +0,00295 |
| **MFC4 − A45** | **+0,00531`*`** | **+0,00177`*`** | **+0,00440`*`** | **+0,00750`*`** | **+0,00750`*`** |
| MFC4 − V5 | +0,00342 | +0,00125 | **+0,00371`*`** | **+0,01276`*`** | **+0,01276`*`** |
| **`lab72`** | | | | | |
| MFC72 − A45 | −0,01620`*` | −0,00596`*` | −0,00280`+` | +0,00255 | +0,00255 |
| MFC72 − V5 | −0,03338`*` | −0,01237`*` | −0,01009`*` | **+0,00701`*`** | **+0,00701`*`** |
| MFB72 − A45 | −0,02334`*` | −0,00859`*` | −0,00994`*` | −0,00305 | −0,00305 |
| MFB72 − V5 | −0,04052`*` | −0,01500`*` | −0,01723`*` | +0,00141 | +0,00141 |
| **MFC4 − A45** | **+0,01408`*`** | **+0,00526`*`** | **+0,00974`*`** | **+0,00952`*`** | **+0,00952`*`** |
| MFC4 − V5 | −0,00309 | −0,00115 | +0,00245 | **+0,01397`*`** | **+0,01397`*`** |
| **`money72` (TIỀN)** | | | | | |
| MFC72 − A45 | +0,00426 | +0,00157 | −0,00018 | −0,00140 | −0,00140 |
| MFC72 − V5 | **+0,01413`*`** | **+0,00520`*`** | +0,00198 | −0,00028 | −0,00028 |
| **MFB72 − A45** | **+0,01051`*`** | **+0,00380`*`** | +0,00018 | +0,00072 | +0,00072 |
| **MFB72 − V5** | **+0,02037`*`** | **+0,00743`*`** | +0,00235 | +0,00184 | +0,00184 |
| MFC4 − A45 | −0,01343`*` | −0,00475`*` | −0,00261`*` | −0,00357`*` | −0,00357`*` |
| MFC4 − V5 | −0,00356 | −0,00113 | −0,00044 | −0,00246 | −0,00246 |

## 6. PnL LUẬT THOÁT (`label_b_pnl.parquet` 309.024 dòng — file **CÒN**, không build lại)

`gross8` = mức gross của top-8 trong pool (P32 = pool top-32 S1; P8 = pool top-8). Δ ghép cặp tick chung
`n = 9.658`, CI như trên.

| arm \| thước | `gross8` | `net@0,008` | Δglift8 vs A45 | Δglift8 vs V5 | `netm8`>0 ngoài CI? |
|---|---|---|---|---|---|
| 45deploy \| P32 | 1,327% | +0,527% | — | — | không |
| A45 \| P32 | 1,363% | +0,563% | — | — | không |
| V5 \| P32 | 1,319% | +0,519% | — | — | không |
| **MFC72 \| P32** | **1,165%** | **+0,365%** | −0,00162 (trong CI) | −0,00154 (trong CI) | **không** |
| **MFB72 \| P32** | **1,395%** | **+0,595%** | +0,00068 (trong CI) | +0,00076 (trong CI) | **không** |

⇒ Trên **PnL luật thoát**: **0** Δ kinh tế ngoài CI; `MFC72` **KÉM cả 4 đối chứng**; `MFB72` nhích
+0,0027…+0,0076pp so với A45 (điểm) nhưng **trong CI** và `net@0,008` 0,595% < **phí hoà vốn 1,395%**
⇒ **không có alpha xếp hạng** (khớp `RESULT_PNL_RULER` `acb88bd`).
`P8`: mọi Δ = 0,0 (pool = cả tick ⇒ `glift8 ≡ 0`, suy biến như đã khai báo).

## 7. KIỂM HỢP LỆ CỦA THƯỚC (§4 pre-reg — bắt buộc ~0)

| bước | `g1lite72` | `lab72` | `money72` |
|---|---|---|---|
| Δic(A45 − 45deploy) | −0,00003 | −0,00054 | +0,00048 |
| Δpacc(V5 − V1) | +0,00024 | +0,00017 | +0,00029 |
| Δglift8(A45 − 45deploy) | +0,00029 | +0,00023 | +0,00037 |
| Δglift8(V5 − V1) | −0,00097 | −0,00096 | −0,00055 |

⇒ **tất cả ~0 và KHÔNG ngoài CI** ở cả 3 thước ⇒ **thước hợp lệ** ⇒ kết luận NULL ở §5 **không** do thước bắt nhiễu.

## 8. LUẬT §5 — VERDICT (chốt trước, không nới ngưỡng)

| arm | §5(A) thước NHÃN (`g1lite72`/`lab72`) | §5(B) thước TIỀN (`money72`) |
|---|---|---|
| `MFC72` | **KHÔNG PASS** (Δic vs V5 = −0,00075 trong CI; Δic/Δpacc vs A45 **âm ngoài CI** trên `lab72`) | **KHÔNG PASS** (Δglift8/Δnetm8 **trong CI**, `netm8` = −0,0063 < 0) |
| `MFB72` | **KHÔNG PASS** (Δic/Δpacc/Δdec_mono **âm**, phần lớn ngoài CI) | **KHÔNG PASS** (Δglift8 +0,00072/+0,00184 **trong CI**; `netm8` = −0,0042 < 0) |
| `MFC4` | **KHÔNG PASS** (Δic/Δpacc vs V5 trong CI — dù Δ vs A45 **cả 5 chỉ số ngoài CI**) | **KHÔNG PASS** (Δ **âm**, phần lớn **ngoài CI**; `netm8` = −0,0085 < 0) |

## 9. KHAI TRƯỚC vs THỰC TẾ (kiểm trung thực)

| dự đoán (§8 pre-reg) | thực tế |
|---|---|
| Q1 (A) `MFC72` có thể PASS | **KHÔNG** — tăng `glift8`/`netm8` (nhất là vs V5, ngoài CI) nhưng `ic`/`pacc` không vượt cả 2 đối chứng |
| Q2 (A) `MFB72` PASS yếu hơn | **KHÔNG PASS** — còn **kém** `MFC72`/`MFC4` ở cả 2 ruler nhãn |
| Q3 (B) NULL ở mọi arm, `netm8` âm −0,006…−0,010 | **ĐÚNG** — `netm8` −0,0042/−0,0063/−0,0085; Δglift8/Δnetm8 trong CI |
| Q4 thước nhãn `g1lite` không vượt hệ thống | **ĐÚNG một phần** — `MFC4` vượt ở 5 chỉ số vs A45, nhưng không đồng thời vs V5 |
| Q5 Δ(A45−45deploy), Δ(V5−V1) ~ 0 | **ĐÚNG** (§7) |

**Phát hiện phải nói rõ (không được đọc thành tin tốt):** `MFC4` = **số 1 ở cả 2 thước NHÃN** và **số
bét ở thước TIỀN** (Δ vs A45 âm ngoài CI ở cả 5 chỉ số) ⇒ **hai thước GẦN NHƯ NGƯỢC DẤU**. Đây là bản
sao thứ 4 của cùng một hiện tượng (`RESULT_H72` §3, `RESULT_MONEY_RANKER`), tức **cải thiện "kỹ năng
nhãn" chỉ là KHỚP MỤC TIÊU TRAIN**, không phải thông tin mới. ⚠️ **Cấm** dùng bảng §4.1 để biện minh
đổi model.

## 10. MỤC BỎ + LÝ DO

- **Thước 4h đầy đủ cho `MFC4`** (`lab4`/`money4` + đối chứng 4h): **BỎ** — `MFC4` đã bị loại dứt khoát
  bởi thước TIỀN 72h (âm ngoài CI), không cần thêm bằng chứng; tiết kiệm ~4 lượt chấm đối chứng.
- **`rank:pairwise`/`lambdarank`** (cơ chế rank): **BỎ** — không thuộc vòng này (§9 pre-reg).
- **Sim/Java**: **KHÔNG chạy** — không cần, và bị cấm (shadow LIVE đang chạy).
- **Tích lặp lại giữa 2 session Kaggle**: hedge `mf-train2-gpu` (`MFC72`) push lúc kernel chính chạy
  > 2h; nếu hoàn tất sẽ đối chiếu `sha_bin` (§11).

## 11. TRẠNG THÁI ARTIFACT PHỤ

- Hedge `chuyendinh/mf-train2-gpu` (chỉ `MFC72`, cùng dataset/seed): **đang chạy** khi đóng vòng —
  **không** dùng cho kết luận nào ở trên. Nếu COMPLETE: đối chiếu `sha_bin` fold 20220101/20251001 với
  `1be21031…` / `a468a172…` (khớp ⇒ tính lặp lại giữa 2 session Kaggle; lệch ⇒ ghi nhận, **không** kết luận khoa học).
- Mọi số của vòng này đọc từ `docs/result/s1_maxfav_score.json` + `docs/result/s1_maxfav_pnl.json`.

## 12. ĐIỀU **KHÔNG** LÀM (đã giữ đúng)

1. KHÔNG chạm ONNX deploy / `NUM_FEATURES` / `extractFeatures45` / LIVE / `2026` / `HoldoutSeal`.
2. KHÔNG push git. 3. KHÔNG retrain đối chứng. 4. KHÔNG nới ngưỡng/luật sau khi đọc số.
5. KHÔNG tự tích hợp. 6. KHÔNG chạy bước nặng (train) trên Oracle.

## 13. PHÁT BIỂU CUỐI CỦA TRỤC

*Đổi nhãn KHÔNG tạo ra alpha xếp hạng quy ra tiền trên 45 feature hiện có*: 4 họ nhãn đã thử
(`g1lite` · `retEnd_h` · PnL luật thoát · `maxFav` trần) đều **NULL** ở trục kinh tế, `netm8` **luôn âm**,
và **cải thiện ở thước nhãn tỉ lệ NGHỊCH với kết quả ở thước tiền**. ⇒ **Bước sai là MỤC TIÊU/ĐẶC TRƯNG**,
không phải nhãn, ngưỡng hay mô hình. Vòng sau (khi owner yêu cầu) chỉ nên đi vào **(1) cơ chế rank
(`rank:pairwise`/`lambdarank` với `qid`)** và **(2) feature mới** — **không** tinh chỉnh hyperparam/ngưỡng
của 45 feature hiện có, và **không** đổi nhãn lần nữa.
