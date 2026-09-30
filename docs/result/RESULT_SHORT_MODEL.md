# RESULT_SHORT_MODEL — MODEL RIÊNG cho SHORT: LABEL NGƯỢC + CẮT CỨNG (train Kaggle, 0-sim)

Ngày: **2026-09-30**, branch `module`, repo `/home/ubuntu/src/BinanceFuturesJava`.
Pre-reg: **`docs/prereg/PREREG_SHORT_MODEL.md`** (commit **`5f2b245a`**, chốt **TRƯỚC** mọi phép đo;
sau đó **không sửa thiết kế**). Kernel: **`chuyendinh/sm-train-gpu` v2** (GPU; sinh bởi
`research/kaggle/short_model/make_sm_kernels.py`). Chấm: `research/analysis/short_model_score.py`
+ `research/analysis/short_model_judge.py` (luật §7 áp **cơ học**). Số: `RESULT_SHORT_MODEL.json`
(+ `RESULT_SHORT_MODEL_full.json`, `RESULT_SHORT_MODEL_train.json`).

**Tuân thủ:** **train CHỈ trên KAGGLE** (không chạy Java/sim trên Oracle; không dùng CPU lớn) ·
**0-sim** (mô hình cắt cứng = tính offline từ aggregate `.pb`, KHÔNG phải sim Java) · **KHÔNG sửa
`.java`** · KHÔNG chạm production/242/ONNX/LIVE · KHÔNG push file dữ liệu (bins ở lại Kaggle) ·
**DEV ≤ 2025-12-31** · không chạm 2026.

---

## 0. KẾT LUẬN (một dòng)

> **`NO-GO/NULL`** theo **luật khóa §7**: **A PASS** — model nhãn ngược có **TÍN HIỆU THẬT**
> (`rank-IC = +0,0519`, **cả 3 seed ngoài CI** raw *và* ×1,21; gấp **2,4×** độ lớn IC của model
> LONG cùng feature); **B FAIL** — net sau cắt cứng **dương ở điểm ước lượng** (`+0,41 %/lệnh` ở
> **C=+30 %**, 1,11 M lệnh) nhưng **CI raw chứa 0** và **chỉ 2/4 năm dương** (2023 **−0,59 %**,
> 2024 −0,11 %). ⇒ **chưa đủ để build đường SELL**. **Lần đầu tiên hướng short có điểm ước lượng
> DƯƠNG**, nhưng **không bền** ⇒ ghi nhận, **không đề xuất build** ở vòng này.

---

## 1. THIẾT KẾ (đúng pre-reg, không đổi sau khi thấy số)

- **KHÁC vòng trước**: vòng này **train MODEL RIÊNG** với **NHÃN NGƯỢC** (không đảo dấu một model
  long có sẵn như `RESULT_SHORT_FEASIBILITY` `5241ba56`).
- **Nhãn ngược (khóa)**: `y_short = 1[retEnd_72h ≤ −0,015]` (mirror của long `y_long = 1[retEnd_72h ≥ +0,015]`).
  **KHÔNG** dùng `1 − y_long` (phủ định của tăng ≠ sự kiện giảm). Base rate DEV: **short 44,69 %**,
  long 39,32 % (39,25 M dòng có nhãn) ⇒ **giảm phổ biến hơn tăng** ở ngưỡng ±1,5 %/72h.
- **Feature dùng NGUYÊN**: ma trận **45 feature selector** (`extractFeatures45` = 40 cột Tool1-15m +
  5 cột OI), **y hệt** ma trận model long production (`g015_net_train_add.py::build_matrix`;
  39 589 971 dòng × 45 cột). **KHÔNG thêm feature mới**, KHÔNG đổi extractor.
- **Cùng fold/purge/seed/hyperparam** như recipe: 16 fold `20220101..20251001`, purge 72h,
  `XGBClassifier(binary:logistic)`, nest 400, depth 5, lr 0,05, subsample/colsample 0,8, `hist`.
- **Đối chứng gương**: arm **LONG** cùng ma trận/cùng fold (seed 42), nhãn `+0,015`.
- **k = 3 seed** cho SHORT (`42, 7, 13`); LONG 1 seed (`42`).

**Train (Kaggle, 1 kernel, ma trận build 1 lần ~3 phút, cache giữa 4 arm):**

| arm | nhãn | seed | phút | n_oos/fold |
|---|---|---|---|---|
| `SHORT42` | `ndown` (≤ −1,5 %) | 42 | 44,8 | 1,12 M → 4,52 M (16 fold) |
| `SHORT7` | `ndown` | 7 | 37,0 | idem |
| `SHORT13` | `ndown` | 13 | 38,1 | idem |
| `LONG42` | `net` (≥ +1,5 %) | 42 | 41,1 | idem |

Trainer sha256 `950cc8a7…` (đúng bản đã commit có `--label-mode ndown`). Chấm in-kernel 5,7 phút.

---

## 2. A — TÍN HIỆU (rank-IC + decile): **PASS**

OOS hợp nhất 16 fold: **35 450 551 dòng**, **139 381 tick**, join bins ↔ nhãn `.pb` theo `(ts,symId)`.

| arm | `rank-IC` = `Spearman(score, −retEnd_72h)` | CI raw | ngoài CI | by-seed |
|---|---|---|---|---|
| **SHORT42** | **+0,05187** | [+0,0453, +0,0584] | ✅ raw & ×1,21 | — |
| **SHORT7** | **+0,05088** | [+0,0446, +0,0574] | ✅ raw & ×1,21 | — |
| **SHORT13** | **+0,05287** | [+0,0465, +0,0594] | ✅ raw & ×1,21 | — |
| **SHORT (mean-seed)** | **+0,05187** | — | ✅ | 3/3 seed cùng dấu |
| LONG42 (đối chứng) | **−0,02133** | [−0,0272, −0,0155] | ✅ (đúng dấu) | — |

**Decile (SHORT42, theo score trong tick; d9 = "short-mạnh" nhất):**

| d | d0 | d1 | d2 | d3 | d4 | d5 | d6 | d7 | d8 | **d9** |
|---|---|---|---|---|---|---|---|---|---|---|
| `retEnd_72h` | −0,0006 | −0,0005 | −0,0010 | −0,0011 | −0,0013 | −0,0013 | −0,0012 | −0,0014 | −0,0015 | **−0,0032** |
| net short (sau cost 0,112 %) | −0,0005 | −0,0006 | −0,0001 | −0,0001 | +0,0001 | +0,0002 | +0,0001 | +0,0003 | +0,0004 | **+0,0021** |

- **Đúng hướng NGUỘC**: d9 (short-mạnh) có `retEnd` **âm nhất** (−0,32 %), d0 gần 0; **đơn điệu ~tăng
  dần theo score**. Nhưng **biên hẹp**: spread d9−d0 chỉ **+0,26 %/72h** ⇒ net decile d9 chỉ **+0,21 %**.
- Tập chọn thật (top-K=8, ~8 coin/tick ⇒ ~3 % đuôi) mạnh hơn decile: **gross +0,446 %/lệnh**.

**⇒ A PASS**: nhãn ngược tạo **kỹ năng xếp hạng thật**, **bền 3 seed**, và **mạnh hơn hẳn** model
LONG cùng feature (0,052 vs 0,021) — tức xu hướng **GIẢM dễ dự báo cross-section hơn TĂNG** ở 72h.

---

## 3. B — KINH TẾ + CẮT CỨNG: **FAIL**

Tập chọn **top-K=8/tick** (gương `K_SEL=8`); **1,114 M lệnh**, net = `pnl − 0,112 %` (base; stress
0,150 % báo kèm); **funding KHÔNG credit** (conservative).

| chế độ | net seed42 | net seed7 | net seed13 | **net mean-seed** | cut-rate | CI raw (seed42) | ngoài CI | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **KHÔNG cắt** | +0,334 % | +0,331 % | +0,349 % | **+0,338 %** | 0 % | [−0,346 %, +0,990 %] | ❌ | +1,22 | **−0,30** | **−0,37** | +0,80 |
| **CẮT +30 %** | +0,386 % | +0,420 % | +0,421 % | **+0,409 %** | **10,0 %** | [−0,175 %, +0,948 %] | ❌ | +1,17 | **−0,59** | **−0,11** | +1,18 |
| **CẮT +50 %** | +0,321 % | +0,352 % | +0,354 % | **+0,342 %** | 4,4 % | [−0,288 %, +0,919 %] | ❌ | +1,13 | **−0,54** | **−0,22** | +1,01 |
| **CẮT +90 %** | +0,246 % | +0,280 % | +0,270 % | **+0,265 %** | 1,5 % | [−0,416 %, +0,865 %] | ❌ | +1,11 | **−0,40** | **−0,31** | +0,67 |

- **Net DƯƠNG ở mọi mức cắt (mean-seed)** — lần đầu hướng short cho điểm ước lượng dương sau phí.
  **Tốt nhất = CẮT +30 %** (+0,409 %/lệnh), hơn KHÔNG cắt (+0,338 %).
- **NHƯNG** mọi mức đều **FAIL luật B**: CI raw **chứa 0** (kể cả ×1,21) và **chỉ 2/4 năm dương**.
  Năm âm nặng nhất = **2023** (−0,4…−0,6 %), 2024 cũng âm nhẹ.

**ĐUÔI TRÁI + CƠ CHẾ "CHẠY" (đúng câu hỏi chủ):**

| | KHÔNG cắt | CẮT +30 % | CẮT +50 % | CẮT +90 % |
|---|---|---|---|---|
| **max lỗ/lệnh** (short) | **−1 499 %** (coin +15× trong 72h) | **−30 %** | **−50 %** | **−90 %** |
| **p99 lỗ** (1 % xấu nhất) | −66,4 % | **−30,0 %** | **−50,0 %** | **−90,0 %** |
| tỉ lệ bị cắt | 0 % | **10,0 %** (111 533/1,114 M) | 4,4 % | 1,5 % |

⇒ **Cơ chế "chạy" THẬT SỰ bị chặn**: không cắt thì đuôi trái **vô hạn** (−1 499 %, đúng lo ngại của
owner); cắt cứng **chặn đúng bằng C** (max lỗ = p99 lỗ = −C). **Đánh đổi**: cắt +30 % tốn ~**10 % số
lệnh** nhưng **tăng** net (vì 10 % đó nếu không cắt thì lỗ sâu hơn −30 %); cắt +50/+90 % **giảm** net
(gross bị cắt nhiều hơn phần đuôi tiết kiệm) ⇒ **+30 % là mức tốt nhất trong 3 mức khóa**.

---

## 4. ĐỐI CHIẾU ĐỐI XỨNG với LONG (cùng feature/fold/seed): **BẤT ĐỐI XỨNG**

| | SHORT (nhãn ngược) | LONG (gương) |
|---|---|---|
| `rank-IC` | **+0,0519** (ngoài CI) | −0,0213 (ngoài CI) |
| net top-K8 (hướng của arm) | **+0,334 %** (CI chứa 0) | **−0,009 %** (≈0) |
| "đảo dấu model long" (short pick của LONG) | — | **−0,215 %** |

- **KHÔNG đối xứng**: cùng feature, **nhãn ngược cho IC mạnh gấp ~2,4×** và **net dương**, còn
  nhãn long cho net **≈ 0** ở 72h.
- **Nhưng "đảo dấu model long" vẫn ÂM (−0,215 %)** — tái lập định tính `RESULT_SHORT_FEASIBILITY`
  (đảo dấu ⇒ âm). ⇒ Giá trị **đến từ RETRAIN với nhãn ngược**, **không** đến từ flip.
- ⇒ Có **cơ sở cho bất đối xứng**: hướng GIẢM có cấu trúc dự báo được tốt hơn hướng TĂNG, nhưng
  **phần thị trường trả cho nó vẫn không vượt được ngưỡng bền vững** (CI + năm).

---

## 5. TRẢ LỜI (4 câu bắt buộc)

### (1) Model label-ngược có TÍN HIỆU không? — **CÓ (tầng thống kê), MẠNH HƠN LONG.**
`rank-IC = +0,0519` (mean-seed; 3/3 seed, **ngoài CI** raw **và** ×1,21, `n_tick = 139 381`);
decile đơn điệu đúng dấu (d9 `retEnd` −0,32 %). So với LONG cùng feature: **+0,0519 vs −0,0213**
(độ lớn gấp **2,4×**). ⇒ **KHÔNG còn là "flip vô nghĩa"**: nhãn ngược tạo kỹ năng riêng.

### (2) Sau CẮT CỨNG, lệnh short có NET > 0 không? Mức nào tốt nhất? — **DƯƠNG ở điểm ước lượng, nhưng KHÔNG bền.**
- **+30 %: +0,409 %/lệnh** (mean-seed; seed lẻ +0,386/+0,420/+0,421 %) — **tốt nhất**; cut-rate 10,0 %.
- +50 %: +0,342 % (4,4 %) · +90 %: +0,265 % (1,5 %) · không cắt: +0,338 %.
- **NHƯNG** mọi mức: **CI raw chứa 0** và **2/4 năm dương** ⇒ **FAIL luật B** (không "net > 0 ngoài CI
  & ≥3/4 năm").

### (3) Đuôi trái bị chặn bao nhiêu %? Cơ chế "chạy" có bị chặn thật không? — **CÓ, chặn đúng bằng C.**
Không cắt: max lỗ **−1 499 %**, p99 lỗ **−66,4 %** (đuôi squeeze). Cắt cứng: **max lỗ = p99 lỗ = −C**
(−30 %/−50 %/−90 %) ⇒ **cơ chế "chạy" bị chặn thật**, đổi lại mất net (−0,05…−0,13 pp ở +30/+50/+90 %
so với mức tốt nhất) và 1,5–10 % số lệnh bị cắt. Đúng đề xuất owner (+90 %) vẫn hoạt động, nhưng
**+30 % là mức tốt nhất** trong 3 mức khóa.

### (4) KẾT LUẬN DỨT KHOÁT: **`NO-GO/NULL`**
- **A PASS** (IC ngoài CI, 3 seed) **nhưng B FAIL** (CI chứa 0; 2/4 năm) ⇒ theo **luật khóa §7**
  (A **VÀ** B): **NO-GO**, **không vùng xám** ⇒ **KHÔNG đề xuất build đường SELL vòng này**.
- **Điểm mới so với các vòng NO-GO trước**: đây là **lần đầu** hướng short cho **điểm ước lượng
  dương** (+0,41 %/lệnh net, 1,11 M lệnh) **và** cắt cứng chứng minh được chặn đuôi. Cái thiếu là
  **bền vững** (CI + 2023/2024 âm), **không** phải "không có tín hiệu".
- **Nếu muốn đi tiếp (bước 2 tối thiểu, CHỈ khi có yêu cầu mới)**: (i) điều tra **vì sao 2023 âm**
  (regime/alt-season) và kiểm **cửa sổ cắt + trailing** (chưa thử); (ii) đo **funding** (hiện KHÔNG
  credit — có thể là tailwind nhỏ) và **thanh khoản/borrow**; (iii) **CHỈ sau khi** vượt được ngưỡng
  bền vững mới bàn build 647–890 dòng Java đường SELL. **Không dựng code trước khi có bằng chứng.**

---

## 6. GIỚI HẠN (nói rõ)

1. **Mô hình cắt cứng là XẤP XỈ từ aggregate `.pb`**: dùng `maxFav_72h` ⇒ giả định "đã cắt" khi đỉnh
   chạm C, **không** mô hình thứ tự trong nến (path) ⇒ cận **bảo thủ về phía cắt** (lỗ đúng C). Không
   mô hình **liquidation / borrow / funding dấu** ⇒ mọi số short là **cận trên lạc quan**.
2. **Selection top-K=8/tick** là gương K của long; **chưa** quét K khác / sizing / portfolio.
3. **CI raw chứa 0** nhưng **chưa** kiểm ghép cặp vs một đối chứng short "chuẩn" (không tồn tại) —
   luật §7 đã khóa theo CI tuyệt đối nên không đổi verdict.
4. **Chỉ 1 horizon (72h)**; 24h chỉ là báo phụ **chưa** làm. Gate-33 và S1-9 **chưa** train riêng (§7).
5. **Deviation hạ tầng đã khai**: kernel v1 **lỗi** (nhúng snapshot trainer **trước khi sửa bug**
   `ndown` ⇒ `No objects to concatenate`); đã **regenerate + push v2** (trainer sha256 `950cc8a7…`).
   Số trong doc **hoàn toàn từ v2**.
6. Mọi số là **mô tả quá khứ DEV**, không phải cam kết forward.

---

## 7. VIỆC BỎ + LÝ DO (khớp §8 pre-reg)

| # | việc | trạng thái | lý do |
|---|---|---|---|
| 1 | Train riêng gate-33 | ⛔ BỎ | extractor khác, cần dataset mới ⇒ vi phạm §1.3; để sau nếu arm 45 vượt ngưỡng bền vững |
| 2 | Train riêng S1-9 (`feat_v2`) | ⛔ BỎ | schema `feat_v2` không có trên Kaggle; push dataset mới ⇒ vi phạm §1.3 |
| 3 | Horizon 24h/12h là arm quyết định | ⛔ BỎ | khóa h=72h |
| 4 | liquidation/borrow/funding dấu | ⛔ BỎ | dữ liệu hiện có không mô hình được |
| 5 | Tune threshold/feature/hyperparam | ⛔ BỎ | cấm theo luật vòng này |

---

## 8. SẢN PHẨM + TUÂN THỦ

| File | Nội dung |
|---|---|
| `docs/prereg/PREREG_SHORT_MODEL.md` | chốt trước (commit `5f2b245a`) |
| `docs/result/RESULT_SHORT_MODEL.md` | file này |
| `docs/result/RESULT_SHORT_MODEL.json` | số tổng hợp (nhỏ) |
| `docs/result/RESULT_SHORT_MODEL_full.json` | bảng chấm đầy đủ (mọi decile/cut/CI) |
| `docs/result/RESULT_SHORT_MODEL_train.json` | báo cáo train 4 arm (phút, n_oos, objective) |
| `research/pipeline/g015_net_train_add.py` | +`--label-mode ndown` (mặc định cũ nguyên) |
| `research/analysis/short_model_score.py` | chấm in-kernel (rank-IC/decile/cắt cứng/CI) |
| `research/analysis/short_model_judge.py` | áp luật §7 cơ học → `VERDICT` |
| `research/kaggle/short_model/make_sm_kernels.py` | sinh kernel Kaggle |

- **Train CHỈ trên Kaggle** (`chuyendinh/sm-train-gpu` v2, GPU); **KHÔNG** chạy Java/sim trên Oracle.
- **0-sim** · KHÔNG sửa `.java` · KHÔNG chạm production/242/ONNX/LIVE · KHÔNG push file dữ liệu.
- **DEV ≤ 2025-12-31**; không chạm 2026.
