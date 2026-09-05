# G1 — Tầng đặt GIÁ TRỊ gate có nên chuyển sang horizon 72h không?

Phép đo **OFFLINE thuần**. Pre-reg `docs/PREREG_G1.md` commit **`f931265`**,
`docs/PREREG_G1_SIM.md` commit **`6519c22`** — cả hai chốt **trước** khi thấy bất kỳ số nào.
Không chạy Java sim (cổng chặn), không VAL, không GPU, không push.
Script: `research/pipeline/g72_train.py`, `research/analysis/g1_repro_check.py`,
`research/analysis/g1_horizon_eval.py`. Log `/home/ubuntu/g72/{g4repro,g72,eval}.log`.

## Trả lời một câu

**NULL, và là null CÓ HƯỚNG NGƯỢC — không phải null thiếu power.** `G72` (đúng pipeline G015,
đổi duy nhất nhãn thành `maxFav_72h >= 0.07`) xếp hạng **kém hơn** `G4_repro` (nhãn
`maxFav_4h >= 0.06`) **ngay trên chính outcome 72h mà nó được train**:
AUC `0.6259` vs `0.6558`, hiệu `−0.0299` với CI95 `[−0.0459, −0.0145]` **nằm trọn dưới 0**,
`P(d>0) = 0.0000`, dấu **nhất quán cả 3 năm**. Cổng GO/NO-GO **FAIL** ⇒ **không chạy sim nào**
(0/2 run đã cấp phép).

Pre-reg §1 đã cảnh báo trước rằng H1 "gần như hiển nhiên đúng" vì `G72` được train trên chính họ
nhãn dùng để chấm. **Cảnh báo đó SAI, và sai ở dấu.** Ghi lại đúng như vậy.

## 1. Cổng REPRO — PASS tuyệt đối

`g72_train.py` chạy với **mặc định** (`G72_LABEL_H=4`, `G72_WIN=0.06`) so với
`/home/ubuntu/predwf_G015_v2/` (baseline tái lập được của G015, `docs/G015_PROVENANCE.md`).

| đại lượng | kết quả |
|---|---|
| bản ghi so sánh | **15,536,189** (10 fold, khớp theo `(ts, symId)`) |
| **`spearman(pred_mới, pred_gốc)`** | **`1.00000000`** (ngưỡng pre-reg 0.99) |
| `max\|Δp\|` từng fold | **0.000e+00** (10/10) |
| sha256 byte-identical | **10/10 fold** |
| `np.array_equal` toàn bộ | **True** |
| `rho` với `g1lite` trên pool | **0.18991** — khớp `G015_PROVENANCE §0` tới 5 chữ số |
| thời gian | 37.6 phút, 4 core CPU |

⇒ **Đổi nhãn là biến duy nhất thay đổi.** Mọi khác biệt bên dưới không thể quy cho pipeline.
Đây là cổng quan trọng nhất và nó đóng chặt.

## 2. Hai model — chỉ khác nhãn

| | `G4_repro` | `G72` |
|---|---|---|
| nhãn | `maxFav_4h >= 0.06` | `maxFav_72h >= 0.07` |
| lọc đủ bar | `nBars_4h >= 16` | `nBars_72h >= 288` |
| dòng nhãn dùng train (toàn DEV+2021) | 19,305,536 | 19,191,588 |
| base rate nhãn | **0.0449** | **0.4041** |
| `rho(pred, g1lite)` trên pool | 0.18991 | 0.16092 |
| thời gian | 37.6 phút | 36.5 phút |

Giống hệt: 45 feature, `XGBClassifier(n_estimators=400, max_depth=5, lr=0.05, subsample=0.8,
colsample_bytree=0.8, min_child_weight=20, eval_metric=auc, tree_method=hist, n_jobs=4,
random_state=42)`, `scale_pos_weight=(1−pos)/pos` (cùng **công thức**), 10 cutoff
`20220101..20240401`, OOS 3 tháng, **purge 72h**, TZ +7h, CPU.
sha256 bins `G72`: `/home/ubuntu/g72/G72_MANIFEST.sha256`.

## 3. GIAI ĐOẠN 1 — bảng kết quả + CI

Tập chấm: `pool_dev.parquet`, **n = 15,442,092** dòng OOS DEV. Join nhãn 72h
(`nBars_72h >= 288`) đạt **100.00%** — không mất dòng nào. `base(Y72) = 0.3636`.
**304 khối 72h.** Block bootstrap 2000 rep, `seed = 20260906`, common random numbers,
CI95 percentile **đã nhân độ rộng ×1.21** (`docs/COV_RESULT.md`).
Sai số do rời rạc hoá 4096 bin khi tính AUC: **6.1e-08 / 3.5e-08** — không đáng kể.

| # | thước | `G4_repro` | `G72` | hiệu `G72 − G4` | CI95 ×1.21 của hiệu | `sd_boot` |
|---|---|---|---|---|---|---|
| **M1** | **AUC vs `Y72`** | **0.655768** | **0.625899** | **−0.029869** | **[−0.045848, −0.014465]** | 0.006592 |
| M2 | spearman vs `Y72` | 0.259558 | 0.209787 | −0.049771 | [−0.076282, −0.024282] | 0.010949 |
| M3 | spearman vs `g1lite` | 0.189910 | 0.160925 | −0.028985 | [−0.057946, **+0.001325**] | 0.012465 |

CI95 ×1.21 của từng điểm: `AUC_G4` [0.6360, 0.6748] · `AUC_G72` [0.6020, 0.6491] ·
`SP_G4_Y72` [0.2274, 0.2902] · `SP_G72_Y72` [0.1706, 0.2479] ·
`SP_G4_g1lite` [0.1526, 0.2256] · `SP_G72_g1lite` [0.1146, 0.2046].

`P(d_AUC > 0) = 0.0000` trên 2000 rep.

### 3.1 POST-HOC mô tả — KHÔNG có trong pre-reg, KHÔNG đổi phán quyết

AUC theo năm, chỉ để trả lời "một năm có kéo cả kết quả không":

| năm | n | base | AUC `G4_repro` | AUC `G72` | `d` |
|---|---|---|---|---|---|
| 2022 | 4,644,009 | 0.3729 | 0.654130 | 0.620927 | **−0.033203** |
| 2023 | 6,404,327 | 0.3377 | 0.650676 | 0.618106 | **−0.032570** |
| 2024 | 4,393,756 | 0.3914 | 0.661069 | 0.633394 | **−0.027675** |

**Dấu nhất quán 3/3 năm**, biên độ gần bằng nhau. Không có năm nào kéo kết quả.

## 4. CỔNG GO/NO-GO — **FAIL**

Điều kiện pre-reg §6: `AUC(G72) > AUC(G4_repro)` **VÀ** CI của hiệu không chứa 0.

- Điều kiện (1): **KHÔNG ĐẠT** — `G72` thấp hơn 0.0299.
- Điều kiện (2): CI **không chứa 0**, nhưng nằm **trọn phía âm**.

⇒ **NULL. Dừng. Không chạy sim.** `docs/PREREG_G1_SIM.md` **đã không được thực thi**:
**0/2** sim run được cấp phép đã chạy; `G1_parity` và `G1_g72` **không tồn tại**;
không có số parity, không có số PRIMARY, không có số equity nào để báo cáo.

## 5. Phán quyết

**Giả thuyết "tầng đặt giá trị gate đang chạy sai horizon, train lại ở 72h thì tốt hơn" bị
BÁC BỎ ở dạng đã phát biểu** — không phải vì thiếu power, mà vì đo được hiệu **ngược dấu**,
CI loại trừ 0 về phía âm, nhất quán cả 3 năm, trên chính outcome mà biến thể mới được train.

**`predwf_G015x26` giữ nguyên vai trò thang giá trị gate. Không có gì thay đổi trong C2b.**

### 5.1 Điều này bác bỏ cái gì, và KHÔNG bác bỏ cái gì

**Bác bỏ:** "lấy đúng recipe G015, đổi nhãn sang `maxFav_72h >= 0.07`, được model gate tốt hơn".
Đúng một mệnh đề đó, và bác bỏ dứt khoát.

**KHÔNG bác bỏ:** "horizon là trục có tác dụng". Phép đo này chỉ chạm **một** họ nhãn, **một**
ngưỡng (0.07), **một** kiến trúc. Nó không nói gì về ngưỡng khác, về nhãn liên tục thay vì nhị
phân, hay về việc hiệu chuẩn ngưỡng gate theo phân vị của chính S1 (`C2B_SPEC §1` — hướng vẫn mở).

### 5.2 Giả thuyết cơ chế — CHƯA ĐO, không được trích như kết luận

Base rate nhảy **0.0449 → 0.4041**. Nhãn 4h/6% chọn ra một lớp **hiếm và sắc** (cú bật mạnh
trong 4 giờ); nhãn 72h/7% gần một phép tung đồng xu và nhiều khả năng bị **biến động chung**
giải thích phần lớn — thứ mà 45 feature đã biểu diễn sẵn, nên còn ít cấu trúc để tách.
**Đây là giả thuyết, không phải phép đo.** Muốn kiểm thì phải pre-reg riêng.

### 5.3 Hai điều bất lợi cho `G4_repro` mà nó vẫn thắng

Ghi ra vì chúng làm kết quả **mạnh hơn**, không yếu hơn:
1. `purge = 72h` giữ nguyên cho cả hai. Với `G4_repro` thì purge **dài hơn horizon nhãn 18 lần**
   (thừa, mất dữ liệu train); với `G72` thì purge **vừa khít** horizon. Bất lợi nghiêng về `G4_repro`.
2. `G72` mất ít dòng nhãn hơn ở khâu lọc đủ bar? Không — ngược lại: 19.19M vs 19.31M, `G72` **mất
   nhiều hơn** 113,948 dòng. Bất lợi nhỏ này nghiêng về `G72`, đã tính vào.

Sau khi trừ cả hai, dấu vẫn không đổi.

## 6. GIÁ TRỊ HẠ TẦNG — kết luận RIÊNG, không trộn với phán quyết §5

Mục này độc lập với PRIMARY và **không** được dùng để biện minh cho việc nhận `G72` vào baseline.

**Đúng:** `predwf_G015x26` — thang giá trị gate mà C2b đang thật sự chạy — **không tái lập được**
(mất bản export Tool1 2021, `docs/G015X26_PROVENANCE.md §1`), là **single point of failure**:
mất thư mục đó là mất gate của C2b vĩnh viễn, chỉ còn bản backup Kaggle.

**Nhưng phải nói chính xác cái gì gỡ được nút đó:** là **`predwf_G015_v2`**, không phải `G72`.
Job hôm nay cung cấp **xác nhận độc lập thứ ba** rằng pipeline G015 là deterministic —
`g72_train.py` chạy từ đầu, trên scratch mới, ra **byte-identical 10/10** với `predwf_G015_v2`
(§1). Trước đó chỉ có 2 lần chạy trong cùng một job (`G015_PROVENANCE §0`).

**Đính chính một cách đọc sai cần chặn:** `predwf_G015_v2` **cũng không có** bin nào trước
`20220101` — y hệt `G015x26`. Khác biệt **không** nằm ở độ phủ đang có, mà ở chỗ v2
**tái lập được nên train lại được**: `build_features` đã đọc Tool1 2021 và nhãn 2021 đã có
(`funding_label_2021*.pb`), nên mở DEV về 2021 chỉ là **thêm cutoff vào `CUT_DATES`**.
Với `G015x26` thì không có đường nào làm việc đó.

`G72` **không đóng góp gì thêm** cho lập luận hạ tầng này: nó cùng pipeline, cùng khả năng tái
lập, nhưng xếp hạng kém hơn. Giữ nó lại không mua thêm bảo hiểm nào.

## 7. GIỚI HẠN PHÉP ĐO

1. **Window overlap — caveat bắt buộc.** Động cơ ban đầu của job này là bảng "so horizon trên
   970 lệnh thật" (4h `+0.258`/`0.747`, 24h `+0.396`/`0.875`, 72h `+0.474`/`0.928`). Bảng đó
   **bị nhiễm window overlap**: ROI hiện thực hoá tới **168h** nên nhãn 72h dùng chung nhiều
   đường giá hơn nhãn 4h, làm tương quan với ROI phồng lên một cách cơ học.
   `docs/LABEL_ROI2_RESULT.md` mục 2 **đã bị retract vì đúng lý do này**.
   Bảng đó **không được** trích làm bằng chứng "72h tốt hơn"; ở job này nó chỉ là **động cơ**.
   Phép đo trong §3 **không** dùng ROI thật và **không** dùng bảng đó.
2. **§3 không miễn nhiễm overlap, nhưng overlap không lái được HIỆU.** `Y72` của các dòng cách
   nhau < 72h dùng chung đường giá ⇒ các dòng **không độc lập**. Đó chính là lý do CI được tính
   bằng block bootstrap khối 72h (`n_eff` ~ **304 khối**, không phải 15.4M dòng) và nhân ×1.21.
   Quan trọng: overlap tác động **giống hệt nhau** lên cả `G4_repro` lẫn `G72` vì hai model chấm
   trên **cùng một tập dòng, cùng một `Y72`** ⇒ nó làm CI rộng ra, **không** tạo ra dấu của hiệu.
3. **Đây là single realization của DEV.** `n_eff` tỉ lệ với **độ dài lịch sử**, không với tần
   suất lấy mẫu (`docs/F4_TIMING.md`). Lấy mẫu mịn hơn không mua thêm power.
4. **Không có bằng chứng P&L.** Cổng chặn trước sim nên **không có** số parity, PRIMARY hay
   equity. AUC/spearman là thước **danh mục không giao dịch được**; một model AUC cao hơn chưa
   chắc kiếm tiền hơn sau khi qua `build_map` + gate + exit. Kết luận §5 vì vậy giới hạn ở
   **tầng xếp hạng**, không phải tầng lợi nhuận.
5. **Định nghĩa thước đo được chốt trước và có xấp xỉ.** AUC tính trên điểm số đã rời rạc hoá
   4096 bin phân vị (sai số đo được ~6e-08); spearman tính bằng Pearson trên **rank toàn mẫu cố
   định**, không tính lại rank trong từng rep bootstrap. Cả hai đã ghi ở `PREREG_G1 §5` trước khi
   chạy.
6. **`Constants.diedSymbol` vẫn nằm trong feature `f3/f4/f5` của cả hai model** (danh sách delist
   hardcode = future info, `AGENT_RUNBOOK §5`). Nó nhiễm **cả hai** phía như nhau nên không lái
   được hiệu, nhưng làm mức AUC tuyệt đối của **cả hai** lạc quan hơn thực tế.
7. **Không đo ngưỡng khác 0.07.** Chọn 0.07 vì khớp `SIM_RATE_PROFIT_STOP_MARKET`; đó là lựa
   chọn có lý do, không phải lựa chọn tối ưu. Quét ngưỡng **sẽ là** một cuộc thi mới và phải
   pre-reg riêng — không được suy ra từ job này.

## 8. Dọn dẹp / hiện trạng đĩa

- `rm -rf /home/ubuntu/g72/scratch_a /home/ubuntu/g72/scratch_b` (feature matrix tạm).
- Xoá 10 file `.bin` của `G4_repro` (byte-identical với `predwf_G015_v2`, dư thừa) và của `G72`
  (null, tái lập được từ `g72_train.py` + `G72_MANIFEST.sha256`).
- **Giữ:** `pred_pool.npy` của cả hai (62 MB/bản, để chấm lại không cần train 75 phút),
  `rebuild_summary.json`, `G72_MANIFEST.sha256`, `g1_repro.json`, `g1_eval.json`.
- **KHÔNG chạm** `predwf_G015x26/`, `predwf_G015_v2/`, `predwf_map_s1a2/`, `devrun/`.

## 9. Tái lập job này

```bash
R=/home/ubuntu/src/BinanceFuturesJava
# cong REPRO
OUT_DIR=/home/ubuntu/g72/G4_repro SCRATCH=<scratch> python3 $R/research/pipeline/g72_train.py
python3 $R/research/analysis/g1_repro_check.py /home/ubuntu/g72/G4_repro /home/ubuntu/predwf_G015_v2
# bien the 72h
OUT_DIR=/home/ubuntu/g72/G72 SCRATCH=<scratch> G72_LABEL_H=72 G72_WIN=0.07 \
  python3 $R/research/pipeline/g72_train.py
# cham diem
python3 $R/research/analysis/g1_horizon_eval.py /home/ubuntu/g72/G4_repro /home/ubuntu/g72/G72
```
Môi trường: python 3.10, xgboost 3.2.0, **CPU** (`n_jobs=4`), Oracle. GPU BỊ CẤM.
