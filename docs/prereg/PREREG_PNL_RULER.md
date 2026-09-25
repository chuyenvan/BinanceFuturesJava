# PREREG_PNL_RULER — Chấm TRỰC TIẾP trên **PnL của LUẬT THOÁT** (thước TIỀN THẬT)

**Ngày chốt:** 2026-09-25 · **Nhánh:** `module` · **Trạng thái:** CHỐT TRƯỚC khi đọc số.
**Tiền đề (không diễn giải lại):** `docs/result/RESULT_MONEY_RANKER.md` (commit `4a94c36`) — nhãn
**(b) = PnL thật theo luật thoát** (arm +7 %, ratchet/trailing, time-stop 168h) **ĐÃ BUILD XONG**
(309.024 lượt sim, 165,7' CPU, cổng chi phí PASS). Vòng đó chấm 4 biến thể `MRA4`/`MRB8`/`MRB32` trên
**`y = retEnd_h`** (và `y = maxFav_4h`) ⇒ vượt `45deploy` ở tầng THỐNG KÊ nhưng `Δglift8`/`Δnetm8`
**TRONG CI**. **Chưa ai chấm trực tiếp trên chính `y = PnL_luật_thoát`.** Vòng này làm đúng việc đó.

---

## 1. CÂU HỎI (1 câu, trả lời được bằng CÓ/KHÔNG)

> Trên **thước PnL của luật thoát** (không phải `retEnd_h`), có mô hình nào có **LIFT KINH TẾ > 0 NGOÀI CI**
> so với **CẢ HAI** đối chứng (`A45` retrain, `V5` nhiễu) **VÀ** có **net dương ở mức phí HIỆN HÀNH 0,8 %/vòng**?

Phụ (bắt buộc, vì phí quyết định): **phí HOÀ VỐN** (break-even) là bao nhiêu %/vòng?

---

## 2. NHÃN (nguồn — DÙNG LẠI, **KHÔNG** build lại)

`y(t, sym) = gross` của **chính `research/exitfit/exit_engine.simulate`** (nhánh `pred = None` ⇒ WEAK
`cap = 0,03`), entry `E = close(t)`, 1 leg, arm +7 %, `BLOCK_INTRABAR_LOOKAHEAD`, time-stop 168h,
`gross = tp/E − 1`. Sinh bởi `research/pipeline/mr_label_build.py` (kernel Kaggle CPU `mr-labelb-cpu`).

| tệp (nguồn, `/tmp` — tệp tạm của vòng trước) | dòng | sha256 (đầu) |
|---|---|---|
| `/tmp/mrout/mrout/label_b_pnl.parquet` (**nguồn duy nhất**, đủ cột `gross`/`net`/`rank`) | **309.024** | `1d42b7f6…` |
| `/home/ubuntu/mr_kaggle/ds_mr_labels/label_b_K32.parquet` (bản sao `(ts,symId,y=gross−0,008)`; sha khớp `/tmp/mrout/mrout/label_b_K32.parquet`) | 309.024 | `f77b283c…` |
| `/tmp/mrout/mrout/label_b_K8.parquet` (`rank < 8`) | 77.256 | `e30a8eff…` |

**Chốt trước:** thước dùng `y = gross` (cột `gross`), **KHÔNG** dùng cột `net` (cột `net` = `gross − 0,008`
là **một** mức phí; mọi mức phí được áp **sau**, ở §5 — như vậy bảng phí không lệ thuộc dữ liệu cũ).
**Không funding** (đã khai ở nhãn (b)); đây **KHÔNG** phải equity của LIVE.

## 3. HAI THƯỚC (pool = tập có nhãn (b); pool KHÔNG do mô hình chấm quyết định)

| thước | tick = `ts` | số coin/tick | `top-8` theo điểm mô hình | vai trò |
|---|---|---|---|---|
| **`P32`** (CHÍNH) | pool top-32 S1 | **đúng 32** (đo được: 9.657 tick × 32) | **chọn thật** (32 → 8) | bảng QUYẾT ĐỊNH |
| **`P8`** (PHỤ) | pool top-8 S1 | **đúng 8** (9.657 × 8) | **suy biến** (`top-8` = cả tick ⇒ `glift8 ≡ 0`) | chỉ đọc `ic`/`pacc`/`dec_mono`/`dec_rho`/mức |

**Khai báo suy biến của `P8` (chốt trước):** trên `P8`, `glift8`/`lift8`(`prec8`) = 0 **theo cấu trúc**,
**KHÔNG** được đọc như "không có kỹ năng". Mọi kết luận về LIFT dùng **`P32`**.

## 4. CHỈ SỐ (nguyên `model_ruler.tick_metrics` — KHÔNG viết lại chỉ số nào)

`y` = `gross`; **`yb` = `(y > 0)`** (nhãn nhị phân "coin THẮNG gross" — khai báo trước, **không** dùng
`y > 0,015` của thước `retEnd` vì đơn vị khác hẳn).

- **Luật (bắt buộc):** `ic` · `pacc` · `dec_mono` (đều **bất biến với phí**) + `dec_rho`.
- **Kinh tế:** `glift8` = `mean(y | top-8) − mean(y | tick)` (**bất biến với phí** — phí là hằng số mỗi lượt)
  · `gross8` = `mean(y | top-8)` · `netm8(f)` = `gross8 − f` · `netbase(f)` = `mean(y | tick) − f`.
- **Phụ:** `auc8`, `auc8c`, `lift8`, `base` (`= mean(yb)`), `n8`.

## 5. BẢNG PHÍ (chốt trước — **4 mức**)

`f ∈ {0,000 (gross) · 0,004 · 0,008 (HIỆN HÀNH) · 0,012}` (đơn vị: phần của giá, round-trip).
Mốc `0,008 = RATE_FEE 0,002 + 2 × SLIPPAGE 0,003` (theo CODE `Configs.java`/`HPOFitnessCalculatorV4`,
`model_ruler.FEE_RT`). **Phí hoà vốn** của một rổ được chọn := **`mean(gross)` của rổ đó** (mức `f` tại đó
`net = 0`), báo cho **rổ `top-8` theo mô hình** và cho **rổ cả tick (pool)**.
Vì phí bằng nhau giữa các arm ⇒ **Δ`netm8` ≡ Δ`gross8` với MỌI `f`** (khai báo trước, không báo 2 lần như
2 bằng chứng).

## 6. ĐỐI CHỨNG + KIỂM HỢP LỆ (bắt buộc)

`45deploy` (không retrain) · `A45` (retrain) · `V5` (nhiễu) · `V1`. **Kiểm hợp lệ:** Δ`(A45 − 45deploy)` và
Δ`(V5 − V1)` phải **~0 và TRONG CI** ở 3 chỉ số LUẬT; nếu không ⇒ thước/ghép cặp có vấn đề, **phải khai**.
Δ ghép cặp **theo tick chung** (`model_ruler.delta`), không so 2 trung bình rời.

## 7. CI + ĐỘ RỘNG (chốt trước, không nới)

`ci_mean` → `stage2_score.block_boot_mean`, **khối 72h**, `c3_rates.NREP = 2000`, `SEED = 20260905`.
- **LUẬT dùng bản CHẶT `1,21`** (`LEGACY_CI_INFLATE` — hiện đang áp cho luật `§6` các vòng trước) ⇒ **không**
  bị coi là nới ngưỡng.
- **Phụ:** `inflate(k) = sqrt(2 ln k)` (đúng `x1_rates.py --k`): **`k = 3`** (3 mô hình mới) và **`k = 6`**
  (3 mô hình × 2 thước). Bảng in cả 3 độ rộng; **kết luận phải giống nhau ở cả 3**, nếu khác ⇒ khai rõ.

## 8. LUẬT TRẢ LỜI (chốt trước, **không** đổi sau khi đọc số)

1. **Có LIFT KINH TẾ** ⟺ trên `P32`: `Δglift8` (⟺ `Δgross8`) so **CẢ HAI** `A45` **và** `V5` **> 0 NGOÀI CI**
   (bản chặt 1,21) **VÀ** `glift8 > 0` ngoài CI (mức tuyệt đối).
2. **Có TIỀN** ⟺ thêm `netm8(0,008) > 0` ngoài CI (dương **ở mức phí hiện hành**).
3. **KHÔNG** được gọi "có tín hiệu kinh tế" nếu (1)/(2) không đạt; **KHÔNG** được dùng `pacc`/`ic` tăng để
   suy ra tiền (vòng trước đã cho thấy 2 thứ này tách rời).
4. **Cảnh báo diễn giải (chốt trước):** `gross8`/`netm8` **mức tuyệt đối** bao gồm **edge của CHIẾN LƯỢC**
   (pool S1 + luật thoát), **KHÔNG** phải kỹ năng của ranker ⇒ luôn đọc kèm `glift8` và Δ. Nếu `netm8 > 0`
   nhưng `glift8`/Δ trong CI ⇒ đó là **edge của rổ có sẵn**, không phải ranker kiếm được tiền.

## 9. HẠ TẦNG / KỶ LUẬT

- **KHÔNG** chạy Java/sim; **KHÔNG** build lại nhãn; **KHÔNG** train. Chỉ **đọc** bins đã có + 1 parquet nhãn
  ⇒ chấm thuần Python (`numpy`/`pandas`), **không** phải bước nặng về CPU; khối lượng đọc ≈ 6,5 GB chia
  16 fold (không giữ 2 fold cùng lúc).
- Guard RAM: kiểm `free -g` trước khi chạy; đỉnh mỗi fold ≪ RAM; nếu thiếu RAM ⇒ **chuyển Kaggle**, không cắt fold.
- `k = 3` mô hình × 2 thước là **cùng 1 họ giả thuyết**; không nhân thêm biến thể nào khác trong vòng này.
- Dev only · **KHÔNG** push · **KHÔNG** chạm ONNX/LIVE/2026/`HoldoutSeal`.
- **Bỏ (chốt trước):** `y = net` tại từng mức phí như một *thước thứ hai* (≡ thước gross + phép dịch hằng số);
  `MRA72` (ngoài 3 biến thể chốt của vòng này); mọi horizon khác; funding; `rank:pairwise`.
