# DIAG_SCORE72H — vì sao **ĐIỂM 72h = NaN**, và **đường RẺ NHẤT** để có điểm 72h

**Ngày:** 2026-09-25 · **Nhánh:** `module` · **Loại:** ĐIỀU TRA (đọc + đo, **KHÔNG train, KHÔNG sim,
KHÔNG job Oracle, KHÔNG đụng ONNX/LIVE**)
**Nguồn:** `docs/result/RESULT_MODEL_RULER.md` §10.5 / §12.7 / §13.4 (chỗ đánh dấu "thiếu hạ tầng")
· **KHÔNG push**

---

## 0. TRẢ LỜI NGẮN (4 câu)

1. **72h = slot 3** của bản ghi 26 B (`ts, symId, p4h, p12h, p24h, p72h`) — tức `z[:,2]` trong dtype
   Python; `WfoDataset.horizonIdx = 3`.
2. **NaN vì HẠ TẦNG, không phải vì số xấu** — nhưng lý do chính xác **không** phải "write_bin ghi 3 NaN"
   như một lỗi riêng: cả họ trainer `net015` **CHỈ có MỘT head (4h)** (`y = retEnd_4h > thr`), nên
   **không tồn tại đầu 72h để ghi**; `write_bin` chỉ điền NaN cho 3 slot còn lại. Đo lại **toàn bộ**
   (không lấy mẫu): 5 arm (`45deploy`, `A45`, `A44`, `V0`, `V5`) = **179.031.895** bản ghi, `z` NaN
   **100,000 %** ở cả 3 slot, `p` NaN **0,0000 %**.
3. **PREDICT-ONLY: KHÔNG LÀM ĐƯỢC.** Không arm nào có model head 72h (`model_f*_4h.json` là **tất cả**
   những gì được lưu; `A44`/`A45` thậm chí **không lưu model**). Muốn có điểm 72h ⇒ **PHẢI TRAIN**
   đầu 72h cho 4 arm. **Job này DỪNG ở đây, không tự train** (đúng ràng buộc), kèm thiết kế pre-reg §5.
4. **Verdict hiện tại KHÔNG đổi và KHÔNG PHỤ THUỘC 72h**: điều kiện (i) `h=4h` đã **0/3** cho **cả**
   `A44` và `V0` (`RESULT_MODEL_RULER` §13.3) ⇒ dù (ii) ở 72h ra gì cũng **không thể đảo `NOT GO`**.

---

## 1. Giải phẫu bản ghi bins: **72h là slot mấy?**

Bản ghi **26 B big-endian**: `>i8 ts` · `>i2 symId` · `>f4 p4h` · `>f4 p12h` · `>f4 p24h` · `>f4 p72h`.

| slot (0-based) | trường | dtype Python (`model_ruler.BIN_DT`) | horizon | `WfoDataset` |
|---:|---|---|---|---|
| 0 | `p` | `("p", ">f4")` | **4h** | `horizonIdx = 0` |
| 1 | `z[:,0]` | `("z", ">f4", 3)` | 12h | `horizonIdx = 1` |
| 2 | `z[:,1]` | | 24h | `horizonIdx = 2` |
| **3** | **`z[:,2]`** | | **72h** | **`horizonIdx = 3`** |

**Bằng chứng (đọc trực tiếp, không suy đoán):**
`WfoDataset.java:193` (comment format) · `:200` (`@param horizonIdx 0=4h,1=12h,2=24h,3=72h`) ·
`:245` `float p4 = getFloat(), p12 = ..., p24 = ..., p72 = ...; float pwin = horizonIdx == 0 ? p4 : ... : p72;`
· `research/analysis/model_ruler.py:64` `H_SLOT = {"4h":0,"12h":1,"24h":2,"72h":3}` + `:353` `slot = H_SLOT[horizon]`.

---

## 2. Vì sao NaN — 3 tầng, đã kiểm từng tầng

### 2.1 Cơ chế (nguyên nhân THẬT): họ trainer `net015` chỉ có **1 head**

| tầng | bằng chứng | hệ quả |
|---|---|---|
| nhãn | `g015_net_train_add.py:206-223` `load_labels()`: `col = "retEnd_4h" if mode=="net" else "maxFav_4h"`, lọc `nBars_4h >= NEED`; hằng số `:69` `H_BASE_MIN = {"4h": 240}`, `:70` `NEED = 16` | **cứng ở 4h** |
| train | cùng file `:373` **1** `xgb.XGBClassifier`/fold, `:380` lưu `model_f{fidx}_4h.json` | **1 head / model** |
| ghi | `write_bin` (`g015_net_train_add.py:256`, `g015_net_train.py:188`, `g72_train.py:157`, `g5/gate_topk_train.py:82`, `g5/g5_pool_train.py:164`) — cả 5 bản: `struct.pack(">qh4f", ts, sid, p, nan, nan, nan)` | slot 1–3 **luôn NaN**, kể cả khi model có head khác |

⇒ **NaN không phải "lỗi ghi"**: nó là **hệ quả tất yếu** của việc *không tồn tại đầu 72h*.
Ghi 3 NaN là **hành vi được ghi rõ là giữ nguyên** (`g015_net_train_add.py:16`: "mọi thứ khác
(nhãn, fold, purge, seed, hyperparam, **write_bin**) GIỮ Y NGUYÊN bản gốc").

### 2.2 Format **KHÔNG** phải giới hạn (đây là chỗ dễ kết luận sai)

Format đã đủ 4 horizon **và đã từng được dùng thật**:
- `ml/training/gen_funding_wf_predictions.py:395` `write_bin(path, key, preds)` ghi
  `>qh4f` với **4 xác suất THẬT** `p[0..3] = [preds[h] for h in H_LIST]`.
- `ml/funding_selector/train_funding_selector.py:29` `H_STEPS = {"4h":16,"12h":48,"24h":96,"72h":288}`
  (trainer **4 horizon** của họ legacy).
- Model **có head 72h** tồn tại thật: `ml/funding_selector/models_v1/model_72h.{ubj,onnx}` (+`metrics_72h.json`),
  `claudedata/models_v2/model_72h.*`, `java/simulator/model_wfo_last_72h.ubj`.
  **Nhưng KHÔNG dùng được cho luật GO**: họ này là **lineage khác + NHÃN khác** (`maxFav +6 %`,
  `base_rate = 0,6326`), không phải `retEnd_72h > 0,015`, và không phải 1 trong 5 arm.

### 2.3 Đo lại (toàn bộ file, không lấy mẫu) — chốt "NaN 100 %" bằng số

| bins dir (arm) | số bản ghi | `p` NaN | `z[:,0]`/`z[:,1]`/`z[:,2]` NaN |
|---|---:|---:|---|
| `/home/ubuntu/claudedata/predwf_G015x26` (`45deploy`) | 35.806.379 | 0,0000 % | 100 % / 100 % / **100 %** |
| `ruler_bins/g015p2-arm44-gpu/stage2/A45` | 35.806.379 | 0,0000 % | 100 % / 100 % / **100 %** |
| `ruler_bins/g015p2-arm44-gpu/stage2/A44` | 35.806.379 | 0,0000 % | 100 % / 100 % / **100 %** |
| `ruler_bins/g015p2-stage2-featvar-gpu/stage2/V0` | 35.806.379 | 0,0000 % | 100 % / 100 % / **100 %** |
| `ruler_bins/g015p2-stage2-featvar-gpu/stage2/V5` | 35.806.379 | 0,0000 % | 100 % / 100 % / **100 %** |

### 2.4 ⚠️ MINI-ERRATA (đính chính phạm vi câu "MỌI bins" ở §12.7/§13.4)

Câu "`z` = NaN 100 % ở **MỌI** bins trong repo" **đúng cho họ `net015`/thước ruler**, nhưng **sai nếu
hiểu là mọi thư mục bins trên máy**: quét 91 thư mục `predict_wf_*.bin`, **12 thư mục có `z` KHÁC NaN**:

| dir | dạng `z` |
|---|---|
| `/home/ubuntu/val_pred` | **3 slot THẬT** và khác `p`: mean `p`=0,4000 · z1=0,4685 · z2=0,5060 · z3=0,5348 (đúng dạng 4 horizon) |
| `claudedata/predict_wf_ev2`, `claudedata/wf_pred*`, `selector_pred_out/trim` | `z[:,i] == p` (writer copy `p` vào cả 3 slot) |
| `orchestrator/tools/_predict_wf_oiz75` | `z != NaN` |
| `predwf_t1_*` | model nhãn `1{maxFav_72h>=0.06}` (chân `L_f72` của `T1_LABEL3`) nhưng điểm ghi vào **slot 0**, slot 3 vẫn NaN; **và** `p_mean` của `f4`/`f4q`/`f72` **gần trùng khít** (0,41971642 / 0,41971648 / 0,41971651) dù 3 nhãn khác nhau ⇒ **nghi bins 3 chân dùng chung một nguồn điểm**; **chưa lý giải**, KHÔNG dùng làm bằng chứng 72h |

⇒ Với luật GO: **không đổi kết luận** (5 arm + deploy đều NaN slot 3), nhưng cách viết "MỌI bins" nên
sửa thành "mọi bins **của 5 arm + bản deploy**" để không gây kết luận sai về sau.

---

## 3. Có head 72h nào dùng được cho 5 arm không? — KIỂM KÊ (trả lời: **KHÔNG**)

| arm | model đã lưu trên đĩa | có head 72h? |
|---|---|---|
| `45deploy` | `/home/ubuntu/claudedata/predwf_G015/model_f{0..17}_4h.json` | ❌ (chỉ `_4h`) |
| `A45`, `A44` | `ruler_bins/g015p2-arm44-gpu/stage2/A4*/` có **0** file `.json` model (chỉ bins + `net_train_summary.json`); bản đầy đủ chỉ nằm trên Kaggle output | ❌ (không có model) |
| `V0`, `V1`, `V5` | `claudedata/stage2_featvar_out/stage2/V*/model_f*_4h.json` | ❌ (chỉ `_4h`) |
| bất kỳ | tìm `*_72h.json` cho họ này trên toàn máy: **0 kết quả** | ❌ |

⇒ **predict-only BẤT KHẢ** cho cả 5 arm: không có tham số head 72h nào để nạp. (Kể cả nếu có, predict
lại cũng phải dựng lại ma trận feature 45/55 cột ⇒ chi phí gần bằng train.)

### 3.1 Thứ **gần miễn phí** đã có sẵn (nhưng KHÔNG đủ điều kiện (ii))

`net015_72h` = **anh-em 72h của `45deploy`** (cùng 45 feature, cùng `label-mode=net`, cùng `thr=0.015`,
cùng 16 fold, cùng seed 42) **ĐÃ TRAIN XONG 2026-09-06** — kernel `chuyendinh/g5-net015_72h`
(`/home/ubuntu/g5/kern/net015_72h/g5-net015_72h.py`, GPU), log: **`DONE 31.2 phút`**, xuất
`pool_net015_72h.parquet` (**6.554.089 dòng**, `ts,sym,p,fold`, 2022-01..2025-12).

**Nhưng không dùng để chốt (ii) được:**
1. Chỉ có **POOL prediction** (`--pool poolkeys_x1` = `cand_dev_x1`), **không phải toàn universe**:
   phủ theo fold rất lệch — fold 15 = 3.480.757/4.517.610 (77 %) nhưng fold 10 = 76.117/2.362.741 (**3,2 %**)
   ⇒ `lift@8`/`rank-IC` per-tick **không so được** với số 4h (140.238 tick × 255,2 coin/tick).
2. Chỉ **1 arm** (`45deploy`) ⇒ **không có** cặp ứng viên↔đối chứng ⇒ **KHÔNG đủ điều kiện (ii)**.
3. Kernel **không lưu model** (`g5_pool_train.py` không bật `--save-model`; Kaggle output chỉ có pool)
   ⇒ **không thể predict-only lại** cho full universe.

---

## 4. Kết luận đường đi: **(b) PHẢI TRAIN** (a không tồn tại)

Không có shortcut "predict-only". Đường rẻ nhất khả thi = **train 4 head 72h** cho `{A45, A44, V0, V5}`
và dùng `net015_72h` sẵn có (hoặc 1 run 31 phút) cho mốc `45deploy`.
**Job này DỪNG tại đây** theo ràng buộc "không train trong job này".

---

## 5. THIẾT KẾ PRE-REG (chưa chạy — chờ owner duyệt)

### 5.1 Sửa code (bắt buộc, tối thiểu, đúng như §10.7 đã đề xuất)
1. `research/pipeline/g015_net_train_add.py`: thêm `--label-h {4,72}`; trong `load_labels()`:
   `col = "retEnd_%dh" % h`, `nbc = "nBars_%dh" % h`, lọc `nBars_%dh >= h*60/15` (**288** khi h=72),
   `H_BASE = {4:240, 72:4320}`.
2. `write_bin(path, ts, sid, p, slot=0)`: ghi điểm vào **slot = 3** khi `h=72` (giữ 4h ⇒ slot 0,
   **hành vi cũ byte-identical**).
3. **KHÔNG** chạm `ONNX` / `NUM_FEATURES` / `extractFeatures45` / `shadow_c3` / LIVE; **KHÔNG** chạm 2026/`HoldoutSeal`.
4. **PURGE không phải đổi**: `PURGE_STEPS = 288` bước ×15m = **72h** đã sẵn (`g015_net_train_add.py:66-67`)
   ⇒ cửa sổ chống leak **đã đủ** cho nhãn 72h (không nới, không thu).

### 5.2 Chạy (chỉ Kaggle GPU — **0 job Oracle**, **0 sim**)

| # | kernel | phạm vi | chi phí ĐO ĐƯỢC (mốc 4h cùng kernel) | ước tính h=72 |
|---|---|---|---|---|
| K1 | `g015p2-arm44-gpu` (re-run) | `--arms "A45:;A44:36"`, 16 fold | **75,8 phút** / 2 arm (log `DONE (75.8 phut)`) | ~75,8 phút |
| K2 | `g015p2-stage2-featvar-gpu` (re-run, **thu hẹp**) | `--arms "V0:<drop V0>;V5:<drop V5>"` (drop list lấy **nguyên văn** từ `claudedata/stage2_featvar_out/kernel_log.txt`: `ARM V0: drop=[0,1,3,4,9,11,12,13,15,16,19,21,22,23,25,26,27,33,34,36,37,38,39,43,45,…,49]`, `ARM V5: drop=[0,1,3,4,9,11,12,13,15,16,19,21,22,23,25,26,27,33,34,36,37,38,39,43]`), 16 fold | **149,4 phút** / **6 arm** ⇒ ~24,9 phút/arm | ~50 phút |
| K3 (tùy chọn) | re-run `45deploy` 16 fold head 72h | 16 fold | kernel gốc `selector-15mtr-pred15-net015-gpu` | ~31 phút (mốc g5) |

**Tổng đường rẻ nhất ≈ 2,1 GPU-giờ** (K1+K2), **2 phiên kernel**; dùng K3 ⇒ ≈2,6 GPU-giờ (3 phiên).
Quota Kaggle GPU 30 h/tuần ⇒ **lọt**, nhưng vẫn là **quota + owner duyệt**, không tự chạy.
Đối chứng thay thế: dùng lại `net015_72h` (đã có) làm mốc — **khai rõ** là pool-subset nếu làm vậy.

### 5.3 Định nghĩa đo (chốt TRƯỚC khi chạy)
- Nhãn: `retEnd_72h > 0,015`; lọc `nBars_72h >= 288`; **16 fold giống hệt 4h**; cùng hyperparam/seed 42.
- Thước: `research/analysis/model_ruler.py --horizon 72h` (**không sửa code** — đã đọc đúng slot 3 + `retEnd_72h`),
  CI block-72h, `NREP=2000`, `seed=20260905`, `inflate(k)` với `k=2` (2 ứng viên `A44`,`V0`).
- Luật: **giữ nguyên** `≥2/3` ở M1/M2/M3 **và** "không chỉ số nào Δ<0 ngoài CI ở 72h" — **KHÔNG nới ngưỡng**.

### 5.4 ⚠️ Kỳ vọng KHAI TRƯỚC (để không tự lừa)
1. **Base rate 72h ≈ 0,39–0,46** (đo trên 3 file dev, lọc `nBars_72h≥288`: 2022Q1 = **0,4378**,
   2024Q1 = **0,4600**, 2025Q1 = **0,3304**; `PREREG_G5`/g5-proxy khai **0,3932**) so với **0,1849** của 4h
   ⇒ `lift@K` **sẽ NHỎ hơn** và **Δ sẽ NHỎ hơn** (nền đã khai ở `RESULT_MODEL_RULER` §10.7).
2. **Cảnh báo "PASS RỖNG"**: proxy độc lập cho thấy model nhãn 72h **gần như không xếp hạng được**
   (`rank-IC(net015_72h) = −0,01277` vs `net015_4h = +0,14412`, `RESULT_GATE_H72` §1.1) ⇒ Δ(72h) **dễ nằm
   trong CI vì KHÔNG CÓ TÍN HIỆU**, chứ không phải vì arm tốt. Vì thế: **(ii) PASS ở 72h KHÔNG phải bằng
   chứng GO**, và (ii) **không thể đảo** (i) đã fail. Phải in kèm `n_tick(72h)` và `Δ` thô để người đọc
   thấy độ lớn ~0.
3. **`net@8` (72h) PHẢI báo kèm** (chi phí round-trip `0,008` là hằng số; horizon dài hơn ⇒ "cửa sổ" lớn hơn).
4. **`n_tick(72h) < 140.238`** là kỳ vọng (nhãn 72h cần 288 bar ⇒ mất ~3 ngày cuối mỗi kỳ + cuối cửa sổ)
   ⇒ phải báo `n_tick(72h)` thật và **ghép cặp trên tập tick CHUNG** giữa các arm (không so số của 2 tập khác nhau).
5. Bằng chứng tầng hệ thống **đã có, cùng chiều XẤU**: sim 48 tháng `G5_net015_72h` (win% −9,30 ngoài CI,
   `TSloss%` +12,13) và `G1` offline (AUC −0,0299, CI **[−0,0459, −0,0145]**) — `docs/result/RESULT_GATE_H72.md` §1.2/§1.4.
   ⇒ Kỳ vọng trung thực: **72h không phải hướng hứa hẹn**; việc bổ sung điểm 72h là để **đóng khoảng trống
   hạ tầng** (đủ cổng cho vòng sau), **không** để tìm GO.

---

## 6. XÁC NHẬN (bắt buộc): verdict hiện tại **KHÔNG ĐỔI**

`RESULT_MODEL_RULER` §13.3: `A44` vs `{A45, 45deploy}` = **0/3** và `V0` vs `{V5, 45deploy}` = **0/3**
ở `h = 4h` (fail **cả 3 mức K** của M2) ⇒ **điều kiện (ii) ở 72h dù ra kết quả nào cũng KHÔNG thể
đảo `NOT GO`**; verdict hiện tại **hoàn toàn không phụ thuộc** 72h.

---

## 7. MỤC KHÔNG ĐỌC ĐƯỢC / CHƯA KIỂM (ghi rõ, không suy diễn)

1. **Không** chạy được `model_ruler --horizon 72h` cho 5 arm ⇒ **không có bảng 5 arm × h=72h (đạt ?/3)**
   và **không có Δ vs 2 đối chứng** ở 72h — đúng như thiết kế (không bịa số, không lấy `p4h` thay 72h).
2. **Không** có argv/kernel script đầy đủ của `g015p2-stage2-featvar-gpu` trên máy (chỉ có
   `claudedata/stage2_featvar_out/kernel_log.txt`); drop-list V0/V5 lấy **từ log**, **không** xác minh được
   dataset version của phiên đó.
3. **Không** đo được ma trận phủ pool/fold của `net015_72h` ngoài 2 fold đã đọc trong log.
4. **Dị thường chưa lý giải:** `predwf_t1_f4`, `predwf_t1_f4q`, `predwf_t1_f72` (3 chân nhãn *khác nhau*: `1{maxFav_4h>=0.06}`, rel5 của `maxFav_4h`, `1{maxFav_72h>=0.06}` — `docs/experiment/T1_LABEL3.md` §2) lại có `p` **gần trùng khít** (mean 0,41971642 / 0,41971648 / 0,41971651; khác ≤1 ULP; sha256 KHÁC nhau) — trong khi base rate của 3 nhãn là 14,14 % / rel5 / **65,71 %**, không thể cho cùng phân bố điểm. ⇒ **nghi bins 3 chân dùng chung một nguồn điểm (hoặc bước `build_map.py` đè `p`)**. Cần người tạo (T1_LABEL3) xác nhận trước khi tin bất kỳ bins `predwf_t1_*` nào. Không ảnh hưởng 5 arm.
5. **Không** kiểm được `WfoDataset` end-to-end với slot 3 (cần chạy Java — ngoài phạm vi; đã đọc code, chưa chạy).

## ERRATA (2026-09-25) — dị thường `p` ở `predwf_t1_*` ĐÃ LÝ GIẢI, **KHÔNG PHẢI LỖI**

§2.4 và §4-ý-4 (nghi `build_map.py` đè `p`) — **đã kiểm byte-level và lý giải**:
`docs/diag/DIAG_BINS_P_OVERWRITE.md` (commit `927bb44`).

`build_map.py:44` chỉ đè **slot 0 (`p4h`)** bằng **rank-map**, và **GIỮ NGUYÊN multiset `P(win)`
trong từng tick** — đúng hợp đồng đã chốt ở `docs/prereg/PREREG_T1.md` §3.2. Bằng chứng: multiset
`p0` theo tick trùng **87.547/87.547 = 100,0000 %** với cả 4 đối chiếu; `corr(rank p0, rank score)`
chéo chính = **−1,000000**; "`p_mean` gần trùng" chỉ là **nhiễu thứ tự cộng float32**.
⇒ **Không phải lỗi, không cần sửa số.**
