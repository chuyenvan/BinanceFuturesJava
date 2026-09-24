# PREREG_STAGE2_FEATVAR — chốt TRƯỚC: 6 biến thể train thêm feature (Stage 2)

**Ngày chốt:** 2026-09-24 · **Chi nhánh:** `module` · **Trạng thái:** CHỐT TRƯỚC — chưa train
**Tiền đề (đã đóng băng):** `docs/result/RESULT_PRESCREEN_FEAT.md` (commit `d0809e0`) — 5 feature PASS,
toàn nhóm A. **Đường train đã xác minh:** `docs/plan/PREP_STAGE2_TRAIN.md` (commit `2231738`).
**Phạm vi:** Stage 2 = **train + predict + build bins** trên **Kaggle**. **KHÔNG** sim ở vòng này (sim là Stage 3,
cần pre-reg/duyệt riêng). DEV only · **không chạm 2026 / HoldoutSeal** · **không push** · không chạm ONNX/LIVE.

> Luật của vòng này: **chốt TRƯỚC rồi mới chạy.** Mọi thứ dưới đây (biến thể · chỉ số · CI · k · luật quyết
> định · dự đoán khoá trước) **không được sửa sau khi xem số**. Pre-reg này phải được **COMMIT trước** khi
> push kernel train đầu tiên lên Kaggle.

---

## 0. Câu hỏi

21 keeper (mốc) có **được cải thiện** (theo thước của CHÍNH SELECTOR, không phải gain) khi **thêm** 5 feature
mới đã PASS Stage 0 không? Và cái được đo là **nội dung feature** hay chỉ là **"thêm cột + thêm mask NaN"**?

Hai câu đó phải trả lời **cùng một vòng**: V0 (mốc) · V1 (thêm cả 5) · V5 (thêm 5 cột **nhiễu** cùng mask).

---

## 1. SÁU BIẾN THỂ (chốt, không thêm không bớt)

Mốc = **21 keeper** = `fs_v2_21.json` (GIU 22 theo `EVAL_SELECTOR_FEATURES.md §6.3`, **bỏ `#36 rvol15m`**
theo quyết định của owner). Vector 45 cột ⇒ **bỏ 24 cột** bằng `--drop-cols` (**không sửa code**,
không đổi tập dòng/nhãn/split/purge — `PREP_STAGE2_TRAIN.md §2.1`).

24 cột bỏ (DÙNG CHUNG cho cả 6 biến thể):
`0,1,3,4,9,11,12,13,15,16,19,21,22,23,25,26,27,33,34,36,37,38,39,43`

Cột MỚI **append vào CUỐI vector** (append-only, `PREP_STAGE2_TRAIN.md §2.2` §3.3):

| idx | cột | nguồn |
|---|---|---|
| 45 | `rvol7d` | prefeat (1h bars từ 1m OHLCV) |
| 46 | `mom30d` | prefeat (15m bars) |
| 47 | `mom7d` | prefeat (15m bars) |
| 48 | `daysSinceHigh30D` | prefeat (15m bars) |
| 49 | `oi_delta7d` | prefeat (OI 5m, cột 0) |
| 50–54 | `noise_*` | **sinh trong kernel**, N(0,1), **NaN đúng đúng mask** của 45–54 tương ứng |

| id | vector | số cột | `--drop-cols` thêm | mục đích |
|---|---|---:|---|---|
| **V0** | 21 keeper | 21 | `45..54` | **MỐC / control** — bắt buộc, chạy **cùng buổi, cùng kernel, cùng seed** |
| **V1** | 21 + cả 5 | 26 | `50..54` | đề xuất chính |
| **V2** | 21 + `{mom7d,mom30d}` | 23 | `45,48,49,50..54` | nhóm momentum dài hạn thuần |
| **V3** | 21 + `{rvol7d}` | 22 | `46,47,48,49,50..54` | **người thay `rvol15m` vừa bỏ** |
| **V4** | 21 + `{daysSinceHigh30D,oi_delta7d}` | 23 | `45,46,47,50..54` | 2 feature ÍT TRÙNG nhất (rho 0,320 / 0,259) |
| **V5** | 21 + 5 + 5 nhiễu | 31 | (không thêm) | **đối chứng nhiễu**, cùng số cột & cùng mask như V1 |

**File version (mới, không sửa file cũ):**

| biến thể | file | n_features |
|---|---|---:|
| V0 | `research/pipeline/featuresets/fs_v4_21.json` | 21 |
| V1 | `research/pipeline/featuresets/fs_v5_26.json` | 26 |
| V2 | `research/pipeline/featuresets/fs_v6_23.json` | 23 |
| V3 | `research/pipeline/featuresets/fs_v7_22.json` | 22 |
| V4 | `research/pipeline/featuresets/fs_v8_23.json` | 23 |
| V5 | `research/pipeline/featuresets/fs_v9_31.json` | 31 |

- **TUYỆT ĐỐI KHÔNG sửa `fs_v2_21.json`** (quy tắc `featuresets/README.md` §1: thêm/bớt cột ⇒ VERSION MỚI).
  Sinh lại bằng `python3 gen_featuresets.py`; `fs_v4_reserved.json`/`fs_v5_reserved.json` (khung TRỐNG) đã
  được **gỡ** (`git rm`) vì 2 slot đó nay dùng thật cho v4..v9 — không mất thông tin nào (chúng rỗng).
- Cột index **≥ 45 chỉ tồn tại ở đường OFFLINE Stage 2** (`g015_net_train_add.py --add-feats`). **KHÔNG**
  đụng `SelectorOnnxInferenceManager.NUM_FEATURES = 45`, `extractFeatures45`, `Funding_Classifier_Final.onnx`
  hay thư mục `shadow_c3` (`PREP_STAGE2_TRAIN.md §3.2`).

---

## 2. FOLD (số fold HỢP LỆ cho vòng này)

- Đường train = expanding WFO, `OOS_MONTHS = 3`, `PURGE_STEPS = 288` (72h), `TZ = +7h`,
  `seed = 42`, XGB `n_estimators 400 / depth 5 / lr 0,05 / sub 0,8 / colsample 0,8 / mcw 20`,
  `scale_pos_weight = (1-pos)/pos` **theo từng fold**, `device = cuda` (Kaggle GPU), xgboost **3.2.0**.
- ⚠️ **Vòng này chạy 16 fold DEV** = `20220101 … 20251001`. **KHÔNG** chạy `20260101`/`20260401`
  (2 fold đó nằm **TRÊN HoldoutSeal 2026-01-01** — `PREP_STAGE2_TRAIN.md §1.2`, `featuresets/README.md`).
  Lý do: **cấm chạm 2026**. 16 fold này cũng **đúng bằng 16 bins** mà `run_c4_sim.sh` cần cho Stage 3.
- **Số fold hợp lệ cho mọi kết luận = 16.** Nếu chỉ kịp một phần ⇒ chạy theo thứ tự ưu tiên
  **V0 → V5 → V1**, và **ghi rõ** phần còn lại chưa chạy (không suy diễn kết quả thiếu).
- Ghi tên model theo **CUTOFF**, không theo số `f<i>` (bẫy `CUT_DATES`, `PREP_STAGE2_TRAIN.md §1.2`).

---

## 3. TIÊU CHÍ CHẤM (chốt TRƯỚC)

### (a) Thước của SELECTOR — rank-IC cross-section + top-8

- **Chỉ số chính:** `rank-IC` = Spearman **cross-section** giữa `p0` (bins, = P(win) 4h) và `retEnd_4h`,
  tính **trên từng tick**, rồi lấy trung bình qua các tick OOS (đúng công thức đã dùng ở vòng prescreen,
  `research/analysis/prescreen_eval.py`). Tính **trên OOS của từng fold** và **gộp toàn bộ 16 fold DEV**.
- **Chỉ số phụ (bắt buộc):** `top-8 hit` và `lift@8` = (hit-rate của 8 coin có `p0` cao nhất trong tick)
  − (hit-rate trung bình của tick đó). Trung bình qua tick. Đây là proxy của cái sim thật sự dùng.
- **KHÔNG dùng gain/`weight`** để phán xử (bài học `DIAG_RVOL15M.md §D`).
- **KHÔNG dùng decile-edge làm tiêu chí** (Stage 0: 0/20 có CI ngoài 0) — chỉ ghi kèm làm thông tin.
- Số dòng `n_train` / `pos` / `spw` / `n_oos` **phải KHỚP TUYỆT ĐỐI với V0** cho cả 5 biến thể.
  Thêm cột **không** được đổi tập dòng (merge phải là **LEFT**, `j` asserted). Lệch ⇒ **DỪNG**, đó là
  **lỗi cơ chế**, không phải kết quả.

### (b) Khi có sim (Stage 3, KHÔNG chạy ở vòng này)

5 rate (`n` chỉ để tham chiếu, **không** phải quality rate): `win%`, `TSloss%`, `mP|SM`, `mP|SL`, `meanP` —
và **rào cứng** `docs/runbooks/RISK_APPETITE.md §7` (2026-09-24, lần 2):
`maxDD`/năm ≤ **40%** · quý xấu nhất ≥ **−20%** · `UW` ≤ **250** ngày · tập trung 1 coin ≤ **15%** equity ·
**không** năm âm; ngưỡng bằng chứng giữ nguyên **≥ 2 rate ngoài CI**.
`maxDD` **phải** đo bằng **MTM mốc phút** (`RESULT_INTRADAY_DD.md`, `RISK_APPETITE §7.3`).

### (c) CI

- **Không hardcode hệ số.** CI lấy bằng **`research/analysis/x1_rates.py --k <số vòng>`** (script từ chối
  chạy nếu thiếu `--k`; hệ số = `sqrt(2 ln k)`), tức **cùng chuẩn** `AUDIT_CI_INFLATE_STANDARDIZATION`.
- Ở Stage 2 (chưa sim) rank-IC/lift dùng **cùng máy bootstrap**: block **72h**, **2000 rep**,
  **seed 20260905** (`research/analysis/c3_rates.py`), hệ số nở **lấy từ `c3_rates.inflate(k)`** —
  **không viết lại hằng số**.
- **`k = 6`** cho vòng này (xem (e)). Hệ số sẽ in ra trong log/kết quả.

### (d) Đối chứng nhiễu — BẮT BUỘC, cùng ĐÚNG NaN-mask

Theo `PREREG_FEAT_ABLATION.md §2` + bài học `RESULT_S1_FREE_OFI.md §4.1` (đối chứng nhiễu **thuần** cùng mask
**cũng "thắng"** +1,69pp):

- 5 cột `noise_*`: giá trị ngẫu nhiên tại mọi dòng, **NaN đúng đúng những dòng** cột thật tương ứng NaN.
  **Không** cần chuẩn hoá thang (cây chỉ quan tâm thứ tự) — chỉ cần **mask**.
- **Assert bằng số TRƯỚC khi train:** `isnan(noise_j) == isnan(real_j)` trên **100%** dòng, cho cả 5 cột.
  Mask lệch ⇒ **sửa, KHÔNG train**.
- V5 = đối chứng của V1 (**cùng 31 cột nếu tính cả nhiễu/V1 là 26**, cùng mask, nội dung ngẫu nhiên).

### (e) Multiplicity — `k = 6`

6 biến thể ⇒ **`k = 6`**, hệ số nở = `sqrt(2 ln 6) = 1,8930`, ghi rõ trong pre-reg **và** trong kết quả.
`k` này **không** được nới sau khi xem số. (Stage 3 nếu chạy 6 biến thể × sim thì `k` **cộng dồn** thành
`k = 6` cho vòng rank-IC **và** `k = 6` riêng cho vòng sim rate — hai họ chỉ số khác nhau, khai báo riêng.)

---

## 4. LUẬT QUYẾT ĐỊNH (chốt TRƯỚC)

Một biến thể `X ∈ {V1..V4}` chỉ được **GIỮ** khi thoả **CẢ HAI**:

1. **HƠN V0** — `Δrank-IC(X − V0)` có **CI (đã nở `k=6`) KHÔNG chứa 0** và **cùng dấu dương**;
   **VÀ**
2. **KHÁC V5** — `Δrank-IC(X − V5)` có **CI (đã nở `k=6`) KHÔNG chứa 0** và **cùng dấu dương**.

- Điều kiện (2) là cái tách "**thêm tin hiệu**" khỏi "**thêm cột + thêm mask**".
- `top-8 lift@8` báo cáo song song, **cùng luật** (CI nở `k=6`, ngoài 0, cùng dấu) nhưng **không** thay
  thế điều kiện rank-IC (chỉ là xác nhận).
- V0 và V5 là **mốc/đối chứng**, không phải ứng viên — không "giữ" chúng.
- **Không có biến thể nào thoả cả (1) và (2) ⇒ kết luận `NULL`** (giữ nguyên 21 keeper). Đây là **kết cục
  mặc định được mong đợi** — mọi vòng thêm feature trước đây đều NULL, và Stage 0 đã cho 0/20 decile-edge
  ngoài 0.
- **Không** được "nới" luật, **không** được đổi chỉ số chính, **không** được thêm biến thể sau khi thấy số.

---

## 5. DỰ ĐOÁN KHOÁ TRƯỚC

| # | Dự đoán | Cách kiểm |
|---|---|---|
| P1 | **V5 (nhiễu) sẽ KHÔNG hơn V0** ngoài CI ở rank-IC | `Δrank-IC(V5−V0)` CI nở chứa 0 |
| P2 | `Δrank-IC(V1−V5)` **nhỏ hơn** `Δrank-IC(V1−V0)`; nếu V1 "thắng" thì phần lớn là do **thêm cột/mask** | so 2 chênh lệch |
| P3 | Kết cục **NULL** cho cả 4 ứng viên (V1..V4) ở luật §4 | bảng §4 |
| P4 | `n_train/pos/spw/n_oos` **khớp tuyệt đối** giữa 6 biến thể | assert trong `net_train_summary.json` |
| P5 | V3 (`rvol7d` thay `rvol15m`) là ứng viên **sáng nhất** trong 4 (Stage 0: rank-IC −0,0482, mạnh nhất) — nhưng vẫn dự đoán **không** vượt §4 | bảng §4 |

**Nếu P1 sai** (nhiễu cùng mask cũng "thắng" ngoài CI) ⇒ **toàn bộ vòng này là NULL/không đo được**,
giữ nguyên 21 keeper, và **phải** điều tra subset-selection-bias trước khi tin bất kỳ "thắng" nào.

---

## 6. ARTIFACT + NƠI LƯU (để Stage 3 dùng lại)

- Model: `model_f<fidx>_4h.json` (16 fold) — ghi vào thư mục **riêng cho từng biến thể**, **KHÔNG** ghi đè
  `/home/ubuntu/claudedata/predwf_G015/model_f*_4h.json` (bản deploy 2026-08-14).
- Bins: `predict_wf_<cutoff>.bin` (16 bin, 26 B/rec, big-endian `>q h 4f`, `p0` = 4h) — thư mục riêng.
- `net_train_summary.json` mỗi biến thể (giữ `drop_cols`, `keep_idx`, `num_feature`, `n_train/pos/spw/n_oos`).
- Bản sao model + bins **backup** ở nơi ghi rõ trong `docs/result/RESULT_STAGE2_TRAIN.md`.
- **KHÔNG push** git; **KHÔNG** copy gì vào `shadow_c3/`.

---

## 7. VIỆC KHÔNG LÀM TRONG VÒNG NÀY

1. **KHÔNG sim** (`run_c4_sim.sh` / Java / Oracle) — sim là **Stage 3**, cần pre-reg + duyệt riêng.
2. **KHÔNG chạm 2026** (2 fold `20260101`/`20260401` + mọi dữ liệu 2026) — HoldoutSeal.
3. **KHÔNG** đụng ONNX/`NUM_FEATURES`/`extractFeatures45`/`shadow_c3` — đường LIVE.
4. **KHÔNG** thêm nhóm B (regime thị trường) — 0/8 vượt tiêu chí (c); muốn thử phải là vòng
   tương tác/timing **riêng**, tính vào `k` mới.
5. **KHÔNG** thêm biến thể `corrToBtc` coin-level (đã ghi ở `RESULT_PRESCREEN_FEAT §4.1` là việc vòng sau).
6. **KHÔNG** chạy Java/sim trên Oracle (shadow LIVE đang chạy).

---

## 8. Ràng buộc hạ tầng

**Luật runbook: so sánh phải CÙNG NGUỒN HẠ TẦNG.** Toàn bộ vòng này **Kaggle ↔ Kaggle** (6 biến thể
**trong CÙNG một kernel/buổi**, cùng phiên bản xgboost 3.2.0, cùng `device=cuda`, cùng seed) — **không** trộn
Oracle. V0 **bắt buộc** chạy cùng kernel với các biến thể còn lại (`PREP_STAGE2_TRAIN.md §6.1`).

---

*Chốt TRƯỚC bởi: subagent Stage 1+2 (phiên chính `agent:main:main`) · commit hash ghi ở báo cáo cuối.*
