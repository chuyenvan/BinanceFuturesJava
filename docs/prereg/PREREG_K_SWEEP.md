# PREREG_K_SWEEP — Nới `K` của luật vào lệnh (top-K theo S1 mỗi tick): 8 → 10 → 12 (+ quét thêm 16/32)

**Ngày chốt:** 2026-09-25 · **Nhánh:** `module` · **Trạng thái:** CHỐT TRƯỚC khi đọc số.
**Tiền đề (không diễn giải lại, dùng tin):**
- Hệ thống vào **top-K theo điểm S1 mỗi tick**; hiện hành **`K = 8`**. Câu hỏi của owner: **nới lên 10 / 12 thì sao**.
- **Nhãn (b) = PnL theo CHÍNH state machine thoát** (arm +7 % → trailing `gap = peak − min(peak×0,5, maxGap)`
  → time-stop 168h), **ĐÃ BUILD XONG**: `docs/result/RESULT_MONEY_RANKER.md` (`4a94c36`).
  Pool **P32 = top-32 coin theo S1 mỗi tick**, **9.657 tick × 32 coin = 309.024 dòng**.
- **Vì pool ĐÃ là top-32, `K = 8/10/12/16/32` cắt ra được TỪ CHÍNH POOL ĐÓ ⇒ KHÔNG cần chạy lại
  exit engine.** Đây là **đường RE** (ưu tiên), đúng ràng buộc "thuần Python offline, không train, không sim".
- Kết luận đã có (dùng tin): **alpha XẾP HẠNG = 0 ngoài CI** (`RESULT_PNL_RULER.md` `acb88bd`); con số
  **gross 1,27–1,56 %/vòng** thuộc về **rổ (S1) + LUẬT THOÁT**, không phải kỹ năng ranker. Vòng này hỏi
  câu **khác**: **nới K có làm RO trên một đơn vị gross exposure tốt hơn không**.

---

## 1. CÂU HỎI (một câu, trả lời được bằng CÓ/KHÔNG)

> Với **size bằng nhau mỗi coin** (mỗi lệnh cùng notional), **nới `K`** lên 10 / 12 (và 16 / 32 ở mức bối cảnh)
> có làm **net trên MỘT ĐƠN VỊ GROSS EXPOSURE** tốt hơn **`K = 8` NGOÀI CI** không — và có làm **lift tụt** không?

---

## 2. NGUỒN + CHỐT POOL (KHÔNG build lại)

| tệp | dòng | sha256 | ghi chú |
|---|---|---|---|
| `/tmp/mrout/mrout/label_b_pnl.parquet` | **309.024** | `1d42b7f6…` | **nguồn duy nhất**; cột `ts, symId, sym, rank, E, tp, gross, net, status, reason, exit_ts, hold_min, n_arm` |

**Kiểm cấu trúc ĐÃ làm TRƯỚC khi chốt (không phải đọc kết quả):** `9.657` tick × **đúng 32** coin/tick;
`rank` ∈ `[0, 31]` **đủ 0..31 mỗi tick**, `rank = 0` = **S1 tốt nhất**
(`RESULT_MONEY_RANKER` §: score S1 **thấp = tốt**); **0 null**; `exit_ts ≥ ts` mọi dòng.
`mean(gross)` pool = **+0,012678** (khớp `RESULT_PNL_RULER` §3 `gross_tick = 1,2677 %`).

**Chốt trước:** dùng cột **`gross`** (KHÔNG dùng cột `net`, vì `net = gross − 0,008` = **một** mức phí);
mọi mức phí áp **sau**. **Chọn `top-K` = `rank < K`** — KHÔNG xếp lại, KHÔNG đọc điểm, KHÔNG mô hình nào
được chấm ở vòng này. `K = 32` ⇒ **rổ = cả pool** ⇒ mọi `lift@32 ≡ 0` **theo cấu trúc** (khai báo trước,
KHÔNG đọc như "mất kỹ năng").

---

## 3. GIẢ ĐỊNH SIZE (⚠️ QUYẾT ĐỊNH KẾT QUẢ — khai rõ trước)

**Notional BẰNG NHAU mỗi coin** (mọi lệnh cùng size) ⇒ **nới `K` làm TĂNG gross exposure** (nhiều vị thế
đồng thời hơn). Vì vậy **BẮT BUỘC báo CẢ BA**, không được chỉ báo một cái:

| # | chỉ số | định nghĩa | vai trò |
|---|---|---|---|
| i | **`net_coin_K(f)`** | `mean_{t} mean_{i ∈ S_K(t)} (gross_i − f)` — **net/coin/vòng** (bình quân mỗi lệnh) | so sánh **công bằng từng lệnh** |
| ii | **`net_tick_K(f)`** | `mean_{t} Σ_{i ∈ S_K(t)} (gross_i − f)` — **net/tick** (tổng RO) | **kèm HỆ SỐ PHỐI** (gross exposure) |
| iii | **`net_gross_K(f)`** | **`net_tick_K(f) / Ē_K`** với `Ē_K = mean_t e_t` — **net trên MỘT ĐƠN VỊ gross exposure** | **← CHỈ SỐ QUYẾT ĐỊNH** |

`e_t = #{i ∈ S_K(t) : ts_i ≤ t < exit_ts_i}` = **số vị thế đang mở** tại tick `t` (987 khối giờ; đo tại
9.657 mốc `ts` của pool). `Ē_K` = gross exposure trung bình **theo đơn vị "1 notional"**.

**Vì sao (iii) là chỉ số quyết định (lập luận chốt trước, không phải post-hoc):** nếu **giữ NGUYÊN ngân sách
gross** (trần gross), thì size mỗi lệnh ở `K` phải co theo tỉ lệ `Ē_8/Ē_K`; khi đó PnL/tick co đúng theo
hệ số đó ⇒ **`net_tick_K/Ē_K` chính là PnL/tick khi gross được giữ cố định**. Nó là thước **chuẩn hoá duy
nhất** so sánh được giữa các `K` khi `e_t` khác nhau ~tuyến tính theo `K`.

**Neo quy đổi `%equity` (dùng tin, KHÔNG đo lại):** `profiles/F1_k16.properties:47` —
`BASE_BUDGET = CAPITAL_START / NUMBER_ORDER_BUDGET = 35.000/50 = 700 USDT/lệnh`; `config.properties:46`
`CAPITAL_START=35000` ⇒ **`s = 2,0 % equity/lệnh`**. Neo thứ hai (dùng tin): **gross hiện hành có lúc
54–58 %**. Hai neo này **KHÔNG khớp nhau trên sổ sim** (sim không de-dup, không trần gross ⇒ `Ē_8 = 410`
⇒ `410 × 2 % = 820 %`) ⇒ **kết luận bắt buộc phải đọc theo TỈ LỆ giữa các `K`**, và **cảnh báo**: nếu giữ
ngân sách gross như hiện hành thì size phải giảm — đó **chính là** lý do (iii) là thước quyết định.

**Mức phí (chốt trước, 4 mức, round-trip, phần của giá):** `f ∈ {0,000 (gross) · 0,004 · 0,008 (HIỆN HÀNH) ·
0,012}`. Mốc hiện hành `0,008 = RATE_FEE 0,002 + 2 × SLIPPAGE 0,003` (`model_ruler.FEE_RT`).
**Cấu trúc (chốt trước):** `Δ net_coin ≡ Δ gross_coin` và `Δ (net_tick/Ē) ≡ Δ (gross_tick/Ē − f/Ē)`
⇒ **bảng phí KHÔNG thể "cứu" một `K` kém** ở `f = 0`; nó chỉ đổi **mức**, đúng theo tinh thần vòng trước.

---

## 4. BỘ `K` (chốt trước)

- **CHÍNH:** `K ∈ {8, 10, 12}` (câu hỏi owner). **BỐI CẢNH:** `{16, 32}` (mức trần cấu trúc).
- Do đó **`k = 5` mức đã thử** ⇒ độ rộng quyết định **`inflate(k) = sqrt(2 ln 5) = 1,7941`**
  (đúng công thức `x1_rates.py --k`). Bảng in **cả** `raw95` **và** `inflate(5)`; kèm `1,21` (legacy, để
  so với các vòng trước) — **kết luận phải giống nhau ở cả 3**; nếu khác ⇒ **khai rõ**.

---

## 5. CI + BOOTSTRAP (chốt trước — không nới)

- **Khối 72h**, `NREP = 2000`, `SEED = 20260905` (`c3_rates`; `stage2_score.block_boot_mean`), tái dùng
  **nguyên** hàm cho các chuỗi **TRUNG BÌNH** (`net_coin`, `net_tick`, `lift`, `e_t`, `distinct_coin`).
- **`net_gross`** (tỉ số) dùng **bootstrap tỉ số ghép cặp trên CÙNG khối**: mỗi replicate rút `len(B)` khối
  (cùng `SEED`, cùng thứ tự) ⇒
  `R_K = Σ_{t∈boot} n_sum_t(K,f) / Σ_{t∈boot} e_t(K)`, và **`ΔR = R_K − R_8` trên **đúng cùng** replicate**;
  CI = percentile 2,5 / 97,5. Điểm ước lượng = `Σ_t/Σ_t` toàn mẫu (**tỉ số của tổng**, không phải trung bình
  của tỉ số) — chốt trước để không chọn sau.
- **Độ nhạy (chốt trước):** bản **mẫu số cố định** `r_t = n_sum_t(K,f)/Ē_K^toànmẫu` ⇒ chuỗi tuyến tính, chạy
  `MR.delta` ghép cặp tick chung như các vòng trước. **Nếu 2 bản lệch nhau ở dấu/ngoài-CI ⇒ phải khai.**

---

## 6. QUÉT `lift@K` (nhãn bổ sung, rẻ — dùng điểm S1 có sẵn)

`lift_K = mean_t [ mean_{i∈S_K(t)} gross_i − mean_{i∈CẢ pool 32} gross_i ]` (≡ `glift` của harness, `K_LIFTS`
đã có 8/12/16 ⇒ chỉ khác là `K` do **S1** chứ không do mô hình). **Chốt trước:** `lift@32 ≡ 0` cấu trúc;
câu hỏi là **`lift` có TỤT ĐƠN ĐIỆU theo `K` không**, tức **trade-off chất lượng ↔ số lượng**.

---

## 7. RỦI RO PHẢI BÁO (chốt trước)

Với mỗi `K`: `Ē_K`, `e_max`, `e_p95` (đơn vị notional) **+ quy đổi `%equity`** theo **hai neo** ở §3;
thêm **số coin PHÂN BIỆT đang mở** (`d_t`) và **độ trùng 1-coin** (`e_t / d_t`) — vì **trần tập trung
1 coin `CONC_CAP_PERCOIN_PCT = 0.15`** (`RESULT_CONC_CAP_HIGHN` `7d85426`) là ràng buộc **theo TỈ TRỌNG của
1 coin**, và **gross 54–58 %** là mức quan sát hiện hành. ⚠️ Cảnh báo bắt buộc: nới `K` **tăng gross theo
bậc**; nếu trần gross/cap bind thì phần gross tăng **KHÔNG** vào được ⇒ `net/tick` là con số **danh nghĩa**.

---

## 8. LUẬT TRẢ LỜI (chốt trước — KHÔNG đổi sau khi đọc số)

1. **"Nới K tốt hơn NGOÀI CI"** ⟺ tồn tại `K` sao cho **`Δnet_gross_K(f) = R_K(f) − R_8(f) > 0` NGOÀI CI**
   `inflate(k = 5) = 1,7941` **ở CẢ 4 mức phí** (đặc biệt **`f = 0,008` hiện hành** và **`f = 0`** —
   `f = 0` bất biến, là bằng chứng neo). Lệch dấu giữa các mức phí ⇒ **khai**, không chọn mức có lợi.
2. **`K*` tối ưu** ⟺ trong `{8,10,12,16,32}` có `K ≠ 8` với `net_gross` **cực đại** và Δ ngoài CI. Nếu
   **đơn điệu** ⇒ **không có `K*`**, chỉ có **độ dốc**.
3. **"lift TỤT"** ⟺ `Δlift_K = lift_K − lift_8 < 0` **ngoài CI** (k = 5).
4. **KẾT LUẬN DỨT KHOÁT (chốt trước):**
   - **NÂNG K** ⟺ (1) đúng ở `f = 0,008` **VÀ** ở `f = 0` **VÀ** (3) KHÔNG xảy ra.
   - **GIỮ `K = 8`** ⟺ mọi `K`: `Δnet_gross` **trong CI** (không phân biệt được) **hoặc** ≤ 0.
   - **"ĐỔI CÓ ĐIỀU KIỆN"** chỉ được phát biểu nếu kèm **con số size mới** để giữ gross ≤ mức hiện hành
     (từ (iii) §3) — nếu không có ⇒ **KHÔNG khuyến nghị đổi**.
5. **Post-hoc:** mọi phân tích **không** có trong §1–§8 khi đọc số ⇒ **ghi rõ "POST-HOC"** trong RESULT.
   **KHÔNG** chọn `K` theo kết quả rồi trình bày như đã chốt trước.

---

## 9. RÀNG BUỘC THI HÀNH

Thuần Python offline · **KHÔNG** train · **KHÔNG** chạy Java/sim trên Oracle (shadow LIVE) · **KHÔNG** claude-run
· **KHÔNG** push git (commit local) · **DEV only**, không chạm 2026/HoldoutSeal · kiểm `free -g` trước mỗi bước ·
output tool rất nhỏ. **KHÔNG build lại nhãn (b)** (pool đã có, sha khớp) — chỉ build lại nếu **mất** và
ước tính **≤ 3 giờ** (khi đó **phải ghi rõ đã build lại**).
