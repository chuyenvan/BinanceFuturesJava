# PREREG_OFI_MONEY — OFI candidate co **TAO RA GIA TRI TIEN** khong (dưới trần gross 70 % CỨNG + phí 0,6 %/vòng)?

**Ngày:** 2026-09-26 · **Nhánh:** `module` · **Trạng thái:** CHỐT **TRƯỚC** khi đọc bất kỳ số tiền nào của vòng này.
**Kế thừa (đọc để bối cảnh, KHÔNG đọc lại số):** `docs/RESULT_S1_FREE_OFI_V3_MULTISEED.md` (`34d50c7`) ·
`docs/result/RESULT_PNL_RULER.md` (`acb88bd`) · `docs/result/RESULT_MONEY_RANKER.md` (`4a94c36`) ·
`docs/decisions/DECISION_GROSS_CAP70_FEE06.md` · `docs/runbooks/RISK_APPETITE.md` §8 · `docs/result/RESULT_CAP70_FEE06.md` (`844ca68`).

---

## 0. CÂU HỎI (1 câu, dứt khoát)

OFI V3 candidate (`KEEP9` + `ofi_1h` + `aggr_buy_ratio_1h`) **có tạo ra GIÁ TRỊ TIỀN ngoài CI** không —
hay chỉ là **"thắng ở tầng ĐO LƯỜNG, 0 ở tầng TIỀN"** (đúng như 2 vòng trước: `RESULT_PNL_RULER`,
`RESULT_MONEY_RANKER`)?

**Bối cảnh đã biết (dùng tin, KHÔNG đo lại):** ở tầng **selector**, OFI V3 multi-seed **PASS**
(pooled 3 seed mới Δedge5 **+1,76 pp** [+0,005009,+0,031524]`*`; Δrank-IC **+0,002579**`*`; noise NULL 4/4;
seed 42 tái lập 0,0 tuyệt đối). **Nhưng** "kỹ năng XẾP HẠNG ≠ kỹ năng TIỀN" — 2 vòng tiền trước: **0 chỉ số
KINH TẾ DƯƠNG ngoài CI**.

---

## 1. ĐỐI TƯỢNG — điểm lấy từ ĐÂU (cùng nguồn hạ tầng)

| tên | định nghĩa | nguồn điểm (per `(ts,sym)`) |
|---|---|---|
| **`candidate`** | `KEEP9` + `ofi_1h` + `aggr_buy_ratio_1h` | kernel `chuyendinh/ofi-v3-ms-s{43,44,45}` → `pred_ofi_candidate_v2.parquet` |
| **`baseline_fresh`** | model **CÙNG seed, KHÔNG có 2 cột OFI** (đối chứng bắt buộc) | kernel **cùng 3** → `pred_baseline_fresh.parquet` |
| **`noise_ofi_check`** | candidate nhưng `ofi_1h` thay bằng nhiễu (cùng NaN-mask) | kernel **cùng 3** → `pred_ofi_noise_v2.parquet` |

- **Điểm CHÍNH = ensemble 3 seed MỚI 43/44/45** = trung bình theo `(ts,sym)` — đúng tập bằng chứng
  dùng cho verdict multi-seed. **Điểm PHỤ = từng seed riêng (42, 43, 44, 45)** để kiểm bền vững.
- Tất cả 3 đối tượng dùng **cùng file nhãn, cùng tick, cùng hàm CI, cùng seed bootstrap** ⇒ **cùng nguồn
  hạ tầng**; so sánh là **ghép cặp theo tick**.
- **KHÔNG** train lại, **KHÔNG** chạy lại exit engine, **KHÔNG** chạy Java/sim. Chỉ tải 3 output kernel
  (~145 MB/kernel: 3 `pred_*.parquet` + json + log), chấm, rồi **xoá ngay**.

## 2. THƯỚC TIỀN + POOL (đường RE — dùng lại, KHÔNG build lại)

- **Nhãn tiền:** `/home/ubuntu/mr_kaggle/ds_mr_labels/label_b_pnl.parquet` — `y = gross` của **luật thoát**
  (arm +7 % / ratchet / WEAK `cap=0,03` / time-stop 168 h, 1 leg, không funding). `309.024` dòng = **9.657 tick
  × 32** (`sha256 1d42b7f6…`). Cột `net` (`= gross − 0,008`) **KHÔNG dùng**; mọi mức phí áp **sau**.
- **Pool `P32`** = top-32 **S1** mỗi tick (do **S1** định nghĩa — xem §6 thiên lệch).
- **Đặt điểm lên pool:** với mỗi `tick`, xếp hạng **32 coin của pool** theo điểm của từng đối tượng, lấy
  **`top-K`** (`rank < K`), lấy `gross` của luật thoát. Phủ điểm đã kiểm: **100 %** cặp `(ts,symId)` của pool
  đều có điểm cho cả 3 đối tượng (kiểm ở tầng cấu trúc, không phải số kết quả).
- **`K ∈ {8, 10, 12, 16, 32}`** (như `cap70_fee06.py`); **`K = 8` là `K` vận hành** (kết luận `RESULT_CAP70_FEE06`:
  giữ `K = 8`).

## 3. CHỈ SỐ (chốt trước — dùng NGUYÊN định nghĩa `cap70_fee06.py` / `mr_pnl_score.py`)

Với mỗi đối tượng × `K` × `f` (`f ∈ {0 ; 0,004 ; **0,006** ; 0,008}`, `f` = **phí/vòng**, đơn vị phân số):

| ký hiệu | định nghĩa | vai trò |
|---|---|---|
| `net_coin(K,f)` | `mean_t MEAN_{i∈topK}(gross_i − f)` | **MỨC** (%/vòng) |
| `net_tick(K,f)` | `mean_t SUM_{i∈topK}(gross_i − f)` | **MỨC** (net/tick) |
| **`net_gr1dv(K,f)`** | `SUM_i(gross_i − f) / SUM_t e_t`, `e_t` = số **vị thế** đang mở tại `t` (theo `ts`→`exit_ts`) | **CHỈ SỐ QUYẾT ĐỊNH** (net trên 1 đơn vị gross-exposure; **bất biến size**) |

**Δ = ghép cặp theo tick** giữa 2 đối tượng, **cùng `K`, cùng `f`**, trên **tick chung**:
`Δnet_coin`, `Δnet_tick`, `Δnet_gr1dv`. Kiểm chứng đại số (đã biết): `Δnet_coin ≡ Δgross` **độc lập `f`**
(phí là hằng số mỗi vòng trên cùng rổ) — vòng này **kiểm lại bằng số** trên cả 3 cặp, kỳ vọng lệch `0,00e+00`.

## 4. ÁP TRẦN gross **70 %** — ĐÚNG 2 CÁCH (báo CẢ BA hệ số)

Neo **POST-HOC** (kế thừa `RESULT_K_SWEEP` §5 / `RESULT_CAP70_FEE06` §5): `gross_anchor_t = 100 · 0,02 · d_t`
với `d_t` = số **coin PHÂN BIỆT** đang mở tại `t`. `s0 = 0,02` (≡ 2,0 % equity/lệnh).

| cách | size | hệ quả |
|---|---|---|
| **(A) theo TB** | `s_A = 70 / gross_TB` | `TB = 70 %`; **max có thể > 70 %** |
| **(B95) theo p95** | `s_B95 = 70 / gross_p95` | `p95 = 70 %`; max còn vượt |
| **(Bmax) theo TỪNG TICK** | `s_Bmax = 70 / gross_max` | **mọi tick ≤ 70 %** (đúng "CỨNG") |

`net/tick SAU size (%equity/tick) = 100 · 0,02 · s · net_tick(K,f)` — báo **cả 3 cách**.
`net_coin` và `net_gr1dv` là **bất biến size** ⇒ báo nguyên (mức size **không** ảnh hưởng `Δ` của 2 chỉ số này).

## 5. CI + LUẬT QUYẾT ĐỊNH (chốt TRƯỚC, không nới sau khi thấy số)

- **CI:** block **72 h**, `NREP = 2000`, `SEED = 20260905`, dùng **NGUYÊN** `model_ruler.ci_mean` →
  `stage2_score.block_boot_mean` + `c3_rates` (`BLOCK_H=72`, `NREP=2000`, `SEED=20260905`). Cùng **một** `BI`
  cho mọi đối tượng ⇒ **paired**.
- **`k` (multiplicity):** `k = 5` **CHÍNH** (= số `K` trong lưới, đúng tiền lệ `cap70_fee06`) ⇒
  `inflate(5) = 1,7941`. **Bắt buộc báo thêm** `k = 2` (`1,1774`, chỉ `K=8` × 1 đối chứng) và
  `k = 10` (`2,1459`, 5 `K` × 2 đối chứng) để thấy độ nhạy.
- **`*` = NGOÀI CI** = `lo > 0` **hoặc** `hi < 0` ở **cả** `raw` **và** `k`-inflated.

### LUẬT "CÓ GIÁ TRỊ TIỀN" (điều kiện CẦN, đủ để verdict = THẮNG)

Ở **`f = 0,006`**, **dưới trần 70 %** (đúng cả 3 cách A/B95/Bmax), tại **`K = 8`**:

> `Δnet_gr1dv(candidate − baseline_fresh)` **ngoài CI** **VÀ**
> `Δnet_gr1dv(candidate − noise_ofi_check)` **ngoài CI**, **cùng chiều DƯƠNG** (ở `k = 5` CHÍNH).

- **Chỉ số QUYẾT ĐỊNH = `net_gr1dv`** (bất biến size nên không thể "cứu" bằng cách chọn cách áp trần).
- **Không** tính là "có giá trị tiền" nếu: chỉ 1 trong 2 đối chứng ngoài CI; hoặc chỉ `net_coin`/`net_tick`
  ngoài CI mà `net_gr1dv` trong CI; hoặc chỉ ngoài CI ở `k = 2` mà không ở `k = 5`/`k = 10`
  (**ghi rõ là "chỉ ở `k=2`"**).
- **MỨC dương KHÔNG phải kỹ năng:** `net_coin > 0` ngoài CI là **MỨC của RỔ (S1 + luật thoát)**, **KHÔNG**
  được gọi là "candidate kiếm được tiền" (di sản `RESULT_PNL_RULER` §6.2, `RESULT_CAP70_FEE06` §1).
- **KIỂM HỢP LỆ (bắt buộc):** `Δ(candidate − baseline_fresh)` phải **ĐỒNG THỜI ĐƯỢC ĐỌC CÙNG** với
  một Δ "trung tính về mặt cấu trúc" để chứng minh thước không "mù". Vòng này dùng: `Δ(a)` giữa **2 đối
  chứng khác nhau** thì **không có**; thay bằng **(a) `noise − candidate` phải KHÔNG dương ngoài CI** (nếu
  nhiễu THẮNG candidate ⇒ HARNESS NGHI NGỜ, verdict không được công bố) và **(b)** `Δnet_coin` phải **≡ `Δgross`**
  **độc lập `f`** (lệch `0,00e+00`) — nếu không ⇒ lỗi mô hình phí.

## 6. ⚠️ KHAI BÁO THIÊN LỆCH (bắt buộc) — "pool do S1 định nghĩa"

`P32` = **top-32 S1**. Nếu `candidate` chọn coin **ngoài** `P32` thì đường RE này **đánh giá THẤP** candidate
(không có nhãn cho coin đó). Phải làm **ít nhất một** trong hai:

- **(B1) Đo tỷ lệ trùng nhau — LUÔN LÀM:** với mỗi tick, lấy **global top-K của candidate** (trên 621 symbol
  có điểm) rồi đo **% nằm NGOÀI `P32`**. Ngưỡng chốt trước: **nếu `top-8` của candidate nằm ngoài `P32`
  > 10 %** ⇒ kết luận **BẮT BUỘC** gắn cờ **"KHÔNG ĐO ĐƯỢC hết"** (con số RE là **cận dưới** bị thiên lệch,
  không được đọc là "candidate dở").
- **(B2) Mở rộng pool — CHỈ LÀM NẾU QUA CỔNG CHI PHÍ:** pool mới = `S1 top-32` ∪ `candidate top-K` ∪
  `baseline top-K`; build lại nhãn luật thoát cho **coin MỚI** (exit engine Python trên **Kaggle**, KHÔNG
  Oracle). **CỔNG CHI PHÍ chốt trước: ước lượng > 2 giờ/fold ⇒ DỪNG**, ghi rõ, quay về B1.
  Ước lượng dựa trên `cost_report.json` của kernel `mr-labelb-cpu` (đã công bố ở `RESULT_MONEY_RANKER` §6.1:
  fold đầu **12,5 phút**, 15 fold **165,7 phút**, 4,3–25,6 phút/fold) **× tỷ lệ coin/tick mở rộng**.

## 7. TRẢ LỜI BẮT BUỘC (định dạng output)

1. `candidate` có `Δnet` **ngoài CI** vs `baseline_fresh` **VÀ** vs `noise_ofi_check` ở `f = 0,006`,
   dưới trần 70 % không?
2. Nếu **KHÔNG** ⇒ kết luận dứt khoát: *OFI là tín hiệu TĂNG SELECTOR nhưng **không quy ra tiền*** — và nói
   rõ **đây là lần thứ mấy** (đếm: `RESULT_PNL_RULER` (1) · `RESULT_MONEY_RANKER` (2) · vòng này (3)).
3. Nếu **CÓ** ⇒ mạnh bao nhiêu, ở `K` nào, và **khuyến nghị có đáng đưa vào lộ trình tích hợp không** (kèm
   cảnh báo: **thêm 2 feature = 47 cột = ĐỤNG ONNX/LIVE, cần owner duyệt riêng**).

## 8. KỶ LUẬT + NGOÀI PHẠM VI

- **KHÔNG** tự tích hợp · **KHÔNG** nới ngưỡng · **KHÔNG** gọi "có giá trị tiền" khi CI chứa 0 · so sánh phải
  **cùng nguồn hạ tầng**.
- **NGOÀI PHẠM VI (KHÔNG làm, KHÔNG biện luận kết quả bằng chúng):** `claude-run`; Java/sim trên Oracle; chạm
  `2026`/`HoldoutSeal`/`ONNX`/`LIVE`; train lại model; sweep hyperparameter; đổi luật thoát; funding; DCA/de-dup
  live; model hoá margin-call.
- **GIỚI HẠN PHẢI KHAI:** nhãn (b) là **WEAK `cap=0,03`, 1 leg, không funding, bỏ 6,9 % cặp**; `P32` do S1
  định nghĩa (**§6**); `gross` là **quy đổi POST-HOC** neo 2,0 %/lệnh trên coin phân biệt; `net/tick` sau size
  là **MÔ HÌNH**, không phải equity LIVE.
- **Vòng này CHỈ chấm ĐIỂM đã có.** Nếu đọc thấy số khác kỳ vọng ⇒ **KHÔNG** sửa luật, chỉ ghi nhận.

---

**Đóng băng:** mọi lựa chọn ở trên (đối tượng · ensemble seed · pool · `K` · phí · 3 cách áp trần · chỉ số
quyết định · `k` · điều kiện verdict · ngưỡng B1 10 % · cổng B2 2 h/fold) được chốt **TRƯỚC** khi chấm.
