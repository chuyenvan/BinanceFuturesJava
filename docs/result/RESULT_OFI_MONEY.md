# RESULT_OFI_MONEY — OFI candidate có **TẠO RA GIÁ TRỊ TIỀN** không (trần gross 70 % CỨNG + phí 0,6 %/vòng)?

**Ngày:** 2026-09-26 · **Nhánh:** `module` · **Trạng thái:** ĐO XONG · **KHÔNG push**
**Pre-reg:** `docs/prereg/PREREG_OFI_MONEY.md` (commit `4948795`) — chốt **TRƯỚC** khi chấm.
**Code:** `research/analysis/ofi_money_score.py` (đường RE, pool `P32`) · `research/analysis/ofi_money_ext.py`
(đường **B2**, pool mở rộng) · `research/kaggle/ofi_money/make_ofi_ext_kernel.py` (sinh kernel Kaggle).
Dùng **NGUYÊN** `model_ruler.ci_mean` → `stage2_score.block_boot_mean` + `c3_rates`
(`BLOCK_H=72`, `NREP=2000`, `SEED=20260905`), `inflate(k)=sqrt(2 ln k)` (`k=5` CHÍNH = 1,7941; báo thêm `k=2`, `k=10`).
**Số thô:** `docs/result/ofi_money.json` (487 KB) · `docs/result/ofi_money_ext.json`.
**Đối tượng:** `candidate` (`KEEP9`+`ofi_1h`+`aggr_buy_ratio_1h`) vs `baseline_fresh` (CÙNG seed, **KHÔNG** có 2 cột OFI)
vs `noise_ofi_check` (OFI thay bằng nhiễu) — điểm **ensemble 3 seed MỚI 43/44/45**, lấy từ kernel
`chuyendinh/ofi-v3-ms-s{42,43,44,45}` (đã COMPLETE). **KHÔNG** train lại, **KHÔNG** chạy Java/sim.

---

## 0. TRẢ LỜI NGẮN (3 câu bắt buộc)

### (1) `candidate` có `Δnet` **ngoài CI** vs `baseline_fresh` **VÀ** vs `noise_ofi_check` ở `f = 0,006`, dưới trần 70 % không? → **KHÔNG** — ở **CẢ HAI** đường đo

| đường đo | `Δnet_gr1dv(cand−base)` [CI5] | `Δnet_gr1dv(cand−noise)` [CI5] | ngoài CI? |
|---|---|---|---|
| **RE (`P32`)** | −0,0000023 **[−0,0000359, +0,0000303]** | +0,0000043 **[−0,0000232, +0,0000327]** | **KHÔNG** (cả 2) |
| **B2 (pool mở rộng)** | «B2_DGR_BASE» | «B2_DGR_NOISE» | **«B2_OUT»** |

**Và đường RE còn bị VÔ HIỆU về mặt cấu trúc (§2):** **100 %** top-K của **cả 3** đối tượng nằm **NGOÀI `P32`**
⇒ đường RE **KHÔNG đo được** giá trị tiền của cụm này; con số Δ ≈ 0 của nó chỉ nói **"xếp hạng lại *trong* rổ S1
không thêm gì"**, KHÔNG được đọc là "candidate dở".

### (2) Kết luận dứt khoát → **«VERDICT2»**

### (3) Khuyến nghị tích hợp → **«VERDICT3»**

---

## 1. CÁCH ĐO (đúng pre-reg §2–§5, KHÔNG đổi sau khi thấy số)

- **Thước tiền:** `y = gross` của **luật thoát** (arm +7 %/ratchet/`cap=0,03` WEAK/TS 168 h, 1 leg, không funding)
  từ **exit engine Python** (`research/exitfit/exit_engine.py`, đã PARITY PASS).
- **Đường RE:** pool `P32` = `/home/ubuntu/mr_kaggle/ds_mr_labels/label_b_pnl.parquet` (309.024 = 9.657 tick × 32,
  `sha 1d42b7f6…`) — **dùng lại, KHÔNG build lại**. Mỗi tick: xếp hạng 32 coin trong pool theo điểm từng đối tượng → `top-K`.
- **Đường B2 (§6 pre-reg):** pool mở rộng = `P32` ∪ **tap coin MỚI** = (candidate top-8 ∪ baseline_fresh top-8 ∪
  noise top-8, hợp 3 seed) \ `P32` = **166.080** cặp `(tick, coin)` trên **560** symbol ⇒ build **nhãn luật thoát MỚI**
  bằng **chính** `research/pipeline/mr_label_build.py` + exit engine trên **Kaggle CPU** (kernel `chuyendinh/ofi-ext-labelb-cpu`),
  **KHÔNG** chạy Java/sim trên Oracle.
- **`K ∈ {8,10,12,16,32}`** · **phí `f ∈ {0 · 0,004 · 0,006 · 0,008}`** (`f = 0,006` là mức **quyết định**).
- **Chỉ số:** `net_coin` (net/coin/vòng) · `net_tick` · **`net_gr1dv` = `Σi(gross_i−f)/Σt e_t` = CHỈ SỐ QUYẾT ĐỊNH**
  (net trên 1 đơn vị gross-exposure, **bất biến size**).
- **Trần 70 % — ĐÚNG 3 cách** (neo POST-HOC `100·0,02·d_t`, `d_t` = số coin PHÂN BIỆT đang mở):
  **(A)** `s=70/gross_TB` · **(B95)** `s=70/gross_p95` · **(Bmax)** `s=70/gross_max` (mọi tick ≤ 70 %).
- **CI:** block 72 h, `NREP=2000`, `SEED=20260905`, cùng **một** `BI` cho mọi đối tượng ⇒ **paired**; `k=5` chính.
- **KIỂM HỢP LỆ (bắt buộc, đã PASS):** (a) `Δnet_coin(f)` **≡ `Δgross` độc lập `f`** trên cả 4 mức phí
  (lệch **0,00e+00**, xem §3.3); (b) `K=32` = cả pool ⇒ **cả 3 đối tượng trùng khít** (Δ = `0,000000` tuyệt đối) ⇒
  máy xếp hạng/tính chỉ số đúng; (c) `noise − candidate` **KHÔNG** dương ngoài CI (mean −4,3e−06) ⇒ **không HARNESS_NGHI_NGỜ**.

## 2. ⚠️ B1 — KHAI THIÊN LỆCH: **100 % top-K nằm NGOÀI `P32`** (pre-reg §6, ngưỡng 10 % ⇒ **VƯỢT RẤT XA**)

| đối tượng | `K=8` | `K=10` | `K=12` | `K=16` | `K=32` |
|---|---|---|---|---|---|
| **`candidate`** | **100,0 %** (0/77.256) | 100,0 % | 100,0 % | 100,0 % | 100,0 % (1/309.024) |
| `baseline_fresh` | **100,0 %** (0/77.256) | 100,0 % | 100,0 % | 100,0 % | 100,0 % |
| `noise_ofi_check` | **100,0 %** (0/77.256) | 100,0 % | 100,0 % | 100,0 % | 100,0 % |

- Đo bằng **global top-K trên toàn universe 621 symbol** (không phải top-K trong pool) rồi đếm số nằm ngoài `P32`.
  Kiểm độc lập (hợp **3 seed** thay vì 1): candidate **16**/116.916 (`0,014 %`), baseline **0**/115.288,
  noise **15**/118.606 ⇒ **cùng kết luận**.
- **Nguyên nhân (đo được):** `P32` do **S1** định nghĩa, và **S1 KHÔNG chọn major** (BTCUSDT/ETHUSDT: **0** lần;
  S1 chọn `PEOPLEUSDT, CRVUSDT, AVAIIUSDT, MASKUSDT, RSRUSDT…`), trong khi **top-8 của candidate là major**:
  `BNBUSDT, 1000SHIBUSDT, XTZUSDT, DOTUSDT, SFPUSDT, XRPUSDT, 1INCHUSDT, ADAUSDT…` ⇒ **2 vũ trụ lựa chọn GẦN NHƯ RỜI NHAU**.
  (Trong *nội bộ* `P32` thì thứ hạng của candidate lại khớp S1 mạnh: Spearman TB theo tick **+0,90**.)
- ⇒ **HỆ QUẢ BẮT BUỘC (pre-reg §6):** mọi con số trên `P32` phải gắn cờ **"KHÔNG ĐO ĐƯỢC hết"**; chúng là **cầu nối
  bị thiên lệch**, không được dùng để kết luận về giá trị tiền của candidate. ⇒ **kích hoạt B2** (§4).

## 3. ĐƯỜNG RE (`P32`) — đo được nhưng **KHÔNG đại diện**

### 3.1 MỨC @ `f = 0,006` (%/vòng) + hệ số áp trần 70 %

| đối tượng | `K` | `net_coin` @0,004 / **@0,006** / @0,008 | **`net_gr1dv` @0,006** | `BE_coin` | `gross_TB` | `gross_MAX` | `s_A` | `s_Bmax` |
|---|---|---|---|---|---|---|---|---|
| **candidate** | 8 | +0,8416 / **+0,6416** / +0,4416 | **+0,01019** | 1,2416 % | 103,3 % | **172,0 %** | 0,678 | **0,407** |
| `baseline_fresh` | 8 | +0,8561 / **+0,6561** / +0,4561 | +0,01043 | 1,2561 % | 101,5 % | 170,0 % | 0,689 | **0,412** |
| `noise_ofi_check` | 8 | +0,8157 / **+0,6157** / +0,4157 | +0,00977 | 1,2157 % | 101,9 % | 170,0 % | 0,687 | **0,412** |
| *cả 3 (trùng khít)* | 32 | +0,8678 / **+0,6678** / +0,4678 | +0,01165 | 1,2678 % | 144,1 % | 206,0 % | 0,486 | 0,340 |

- **MỨC của rổ DƯƠNG rõ** ở `f = 0,006` (BE ≈ 1,22–1,26 %/vòng ⇒ biên ≈ 0,6 pp/vòng) **nhưng** đây là **MỨC của RỔ**
  (nhãn luật thoát), **KHÔNG** phải kỹ năng xếp hạng — đúng di sản `RESULT_PNL_RULER` §6.2.
- **Trần 70 % ở đây là ràng buộc BUỘC CO RẤT MẠNH:** `gross_MAX ≈ 170–172 %` ⇒ theo **(Bmax)** size phải còn **≈ 0,41×**
  (≈ **0,82 %** equity/lệnh thay vì 2,0 %). (Đây là hệ quả của việc top-8 *trong pool* đổi coin liên tục ⇒ `d_mean ≈ 51`
  coin đang mở, so với `d_mean = 24,4` khi xếp theo chính thứ tự S1.)

### 3.2 Δ ghép cặp theo tick @ `f = 0,006`, `K = 8` — **TRONG CI** (không `*`)

| Δ | n | `Δnet_coin` [CI5] | `Δnet_gr1dv` [CI5] | `Δnet/tick` sau (Bmax) [CI5] | ngoài CI? |
|---|---|---|---|---|---|
| `candidate − baseline_fresh` | 9.657 | **−0,000144** [−0,002153, +0,001878] | **−0,0000023** [−0,0000359, +0,0000303] | −0,0014 [−0,0146, +0,0119] | **KHÔNG** |
| `candidate − noise_ofi_check` | 9.657 | **+0,000259** [−0,001434, +0,001991] | **+0,0000043** [−0,0000232, +0,0000327] | +0,0012 [−0,0097, +0,0130] | **KHÔNG** |
| `noise_ofi_check − candidate` (KIỂM) | 9.657 | −0,000259 | −0,0000043 | — | không dương ⇒ **PASS** |

- **Δ ≈ 0 ở CẢ 4 mức phí và CẢ 3 cách áp trần** (chi tiết trong JSON) ⇒ **thay mức phí/cách áp trần KHÔNG cứu được `Δ = 0`**.
- Ở **cả 5 `K`**: mọi Δ (`net_coin`, `net_gr1dv`, `net/tick` sau size) **TRONG CI** ⇒ không có `K*` đo được.
- **Phụ:** trong nội bộ `P32`, xếp theo **thứ tự S1** cho `gross` top-8 = **1,2006 %**, còn **candidate** (và baseline)
  cho **1,2416 / 1,2561 %** ⇒ cả 2 đều *nhích hơn* thứ tự S1 nhưng **chênh lệch giữa chúng = 0 ngoài CI**.

### 3.3 Kiểm bất biến theo phí (bắt buộc) — **ĐẠT**

`Δnet_coin(f)` của `candidate − baseline_fresh` (`K=8`) ở `f = 0,000 / 0,004 / 0,006 / 0,008`
= **−0,000144421096** — **giống hệt tới 12 chữ số** (lệch `0,00e+00`) ⇒ **mô hình phí ĐÚNG**, phí chỉ đổi MỨC.

## 4. B2 — POOL MỞ RỘNG (đường ĐO ĐƯỢC): nhãn luật thoát cho 166.080 cặp coin MỚI

«B2_SECTION»

## 5. KHAI BÁO TRUNG THỰC — **KHÔNG** ĐƯỢC NÓI GÌ

1. **KHÔNG** được nói "OFI có giá trị tiền": «B2_CLAIM»
2. **KHÔNG** được đọc các số `P32` (§3) là đánh giá candidate: **100 %** lựa chọn của nó nằm ngoài pool đó (§2).
3. **KHÔNG** được nói "MỨC dương ⇒ ranker kiếm được tiền": `net_coin > 0` là **MỨC của RỔ/luật thoát**, không phải xếp hạng.
4. **KHÔNG** được nói "candidate thắng vì `net_coin` cao hơn": mọi Δ giữa 3 đối tượng **trong CI**.
5. **GIỚI HẠN PHẢI ĐỌC KÈM:** (a) nhãn (b) là **bản bảo thủ** (WEAK `cap=0,03`, 1 leg, không funding, bỏ ~6,9 % cặp);
   (b) `gross` là **quy đổi/đo trên luật thoát**, KHÔNG phải equity LIVE (không de-dup live, không DCA, không trần
   size/notional, không funding); (c) `net/tick` sau size là **MÔ HÌNH**; (d) **`P32` không đo được** phần ngoài rổ S1
   — nên **B2** mới là đường trả lời; (e) B2 chỉ phủ **top-8** (K quyết định) và **hợp 3 seed**, không phủ `K ∈ {10…32}`
   của candidate (xem §6).
6. **KHÔNG** chạm ONNX/LIVE/`2026`/`HoldoutSeal`; **KHÔNG** push git.

## 6. VIỆC BỎ + LÝ DO

| # | việc | trạng thái | lý do |
|---|---|---|---|
| 1 | Chấm candidate trên `P32` (RE) | ✅ XONG (~1,3 phút) | đường rẻ, chạy trước; **bị vô hiệu bởi B1** |
| 2 | Đo tỷ lệ trùng nhau B1 | ✅ XONG | bắt buộc; kết quả **100 % ngoài** ⇒ cờ "không đo được" |
| 3 | Cổng chi phí B2 | «B2_GATE» | bắt buộc trước khi mở rộng pool |
| 4 | B2 — build nhãn cho coin MỚI + chấm lại | «B2_STATUS» | đường duy nhất trả lời được câu hỏi |
| 5 | `K ∈ {10,…,32}` trên pool mở rộng | ⛔ BỎ (một phần) | cổng chi phí: build thêm 3 tập coin ⇒ **tăng thẳng thời gian Kaggle**; `K=8` là `K` vận hành (đã chốt ở `RESULT_CAP70_FEE06`) |
| 6 | Sweep hyperparameter / train lại / đổi luật thoát / funding / DCA / de-dup live | ⛔ BỎ | ngoài phạm vi pre-reg; 2 vòng tiền trước đã đóng trục này |
| 7 | Chạy Java/sim, `claude-run`, chạm LIVE | ⛔ BỎ | ràng buộc đề bài (shadow-c3 đang LIVE) |

## 7. KẾT LUẬN (1 dòng)

«CONCLUSION»
