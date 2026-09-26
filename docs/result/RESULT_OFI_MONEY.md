# RESULT_OFI_MONEY — OFI candidate có **TẠO RA GIÁ TRỊ TIỀN** không (trần gross 70 % CỨNG + phí 0,6 %/vòng)?

**Ngày:** 2026-09-26 · **Nhánh:** `module` · **Trạng thái:** ĐO XONG · **KHÔNG push**
**Pre-reg:** `docs/prereg/PREREG_OFI_MONEY.md` (commit `4948795`) — chốt **TRƯỚC** khi chấm.
**Code:** `research/analysis/ofi_money_score.py` (đường RE, pool `P32`) · `research/analysis/ofi_money_ext.py`
(đường **B2**, pool mở rộng) · `research/kaggle/ofi_money/make_ofi_ext_kernel.py` (sinh kernel Kaggle).
Dùng **NGUYÊN** `model_ruler.ci_mean` → `stage2_score.block_boot_mean` + `c3_rates`
(`BLOCK_H=72`, `NREP=2000`, `SEED=20260905`), `inflate(k)=sqrt(2 ln k)` (`k=5` CHÍNH = 1,7941; báo thêm `k=2`, `k=10`).
**Số thô:** `docs/result/ofi_money.json` (487 KB) · `docs/result/ofi_money_ext.json` (480 KB) ·
nhãn B2 + gate chi phí: `/home/ubuntu/ofi_v3/ofimoney/label_b_pnl_ext.parquet` (sha `c93b0b2a8e7c5f94…`,
6,0 MB — **ngoài repo**) · `docs/result/cost_report_ext.json`.
**Đối tượng:** `candidate` (`KEEP9`+`ofi_1h`+`aggr_buy_ratio_1h`) vs `baseline_fresh` (CÙNG seed, **KHÔNG** có 2 cột OFI)
vs `noise_ofi_check` (OFI thay bằng nhiễu) — điểm **ensemble 3 seed MỚI 43/44/45**, lấy từ kernel
`chuyendinh/ofi-v3-ms-s{42,43,44,45}` (COMPLETE). **KHÔNG** train lại, **KHÔNG** chạy Java/sim.

---

## 0. TRẢ LỜI NGẮN (3 câu bắt buộc)

### (1) `candidate` có `Δnet` **ngoài CI** vs `baseline_fresh` **VÀ** vs `noise_ofi_check` ở `f = 0,006`, dưới trần 70 % không? → **KHÔNG — ở CẢ HAI đường đo**

| đường đo | chỉ số quyết định `Δnet_gr1dv(cand−base)` [CI5] | `Δnet_gr1dv(cand−noise)` [CI5] | ngoài CI? |
|---|---|---|---|
| **RE (`P32`)** | **−3,0e−06** [−3,726e−05, +2,980e−05] | **+3,59e−06** [−2,324e−05, +3,196e−05] | **KHÔNG** (cả 2) |
| **B2 (pool mở rộng)** | **−7,29e−06** [−2,757e−05, +1,258e−05] | **+2,3e−07** [−1,791e−05, +1,941e−05] | **KHÔNG** (cả 2) |

Không ô nào ngoài CI ở **`k = 2`, `k = 5` hay `k = 10`**; không ô nào ngoài CI **raw**.
Đường RE còn **vô hiệu về mặt cấu trúc** (§2: **100 %** top-K của **cả 3** đối tượng nằm **ngoài `P32`**) nên
**B2 mới là đường trả lời**; cả 2 đường đều cho **cùng một kết luận**.

### (2) Kết luận dứt khoát → **OFI là tín hiệu TĂNG SELECTOR nhưng KHÔNG QUY RA TIỀN — lần thứ 3**

- Ở tầng **selector**: 2 cột OFI **có** tác dụng (`RESULT_S1_FREE_OFI_V3_MULTISEED`, pooled Δedge5 **+1,76 pp**`*`,
  noise NULL 4/4 seed, seed 42 tái lập 0,0 tuyệt đối).
- Ở tầng **tiền**: `Δnet` so **cả 2** đối chứng **trong CI** ở **mọi `K`**, **mọi mức phí**, **cả 3 cách áp trần 70 %**,
  trên **cả 2** pool — và **lần này đã đo trên chính những coin candidate chọn** (B2), không còn là đo hộ.
- **Đây là lần thứ 3** (đếm theo thứ tự thời gian): (1) `RESULT_PNL_RULER` (`acb88bd`) — 0 chỉ số kinh tế dương
  ngoài CI; (2) `RESULT_MONEY_RANKER` (`4a94c36`) — mạnh hơn ở tầng thống kê, kinh tế = 0; (3) **vòng này** — OFI
  candidate: **0** ở tầng tiền, kể cả khi đo trên pool mở rộng.

### (3) Khuyến nghị tích hợp → **KHÔNG đưa vào lộ trình ở thời điểm này**

Lý do: (i) **không có bằng chứng tiền** (Δ trong CI ở mọi cấu hình đã chốt trước); (ii) về mặt kỹ thuật, thêm 2 feature
= **47 cột** ⇒ **đụng ONNX/LIVE**, phải **owner duyệt riêng** — không nên tiêu vào một ứng viên mà tầng tiền = 0;
(iii) nếu vẫn muốn theo, việc đúng thứ tự là **đóng trục này** và chuyển sang đòn bẩy **MỨC** (kiểm chứng giả định nhãn
+ luật thoát) như `RESULT_PNL_RULER` §9-(3) đã đề xuất.

---

## 1. CÁCH ĐO (đúng pre-reg §2–§5, KHÔNG đổi luật sau khi thấy số)

- **Thước tiền:** `y = gross` của **luật thoát** (arm +7 %/ratchet/`cap=0,03` WEAK/TS 168 h, 1 leg, không funding)
  từ **exit engine Python** (`research/exitfit/exit_engine.py`, đã PARITY PASS).
- **Đường RE:** pool `P32` = `/home/ubuntu/mr_kaggle/ds_mr_labels/label_b_pnl.parquet` (309.024 = 9.657 tick × 32,
  `sha 1d42b7f6…`) — **dùng lại, KHÔNG build lại**.
- **Đường B2 (pre-reg §6):** pool mở rộng = `P32` ∪ **tập coin MỚI** = (candidate top-8 ∪ baseline_fresh top-8 ∪
  noise top-8, **hợp 3 seed 43/44/45**) \ `P32` = **166.080** cặp `(tick, coin)`, **560** symbol ⇒ build **nhãn luật thoát
  MỚI** bằng **chính** `research/pipeline/mr_label_build.py` + exit engine trên **Kaggle CPU**
  (kernel `chuyendinh/ofi-ext-labelb-cpu`) — **KHÔNG** chạy Java/sim trên Oracle. Pool cuối: **475.104 dòng**
  = 309.024 (P32) + 166.080 (mới) · 9.657 tick · **49,2 coin/tick** (tối đa 75).
- **Đặt điểm lên pool:** mỗi tick, xếp hạng **các coin của pool** theo điểm từng đối tượng → lấy **`top-K`**
  (`K ∈ {8,10,12,16,32}`; **`K = 8` là `K` vận hành**). Phủ điểm **100 %** cặp của pool (kiểm ở tầng cấu trúc).
- **Phí:** `f ∈ {0 · 0,004 · **0,006** · 0,008}` (phân số/vòng) — `0,6 %` là **mức quyết định** (owner 26/09).
- **Chỉ số:** `net_coin` (net/coin/vòng) · `net_tick` · **`net_gr1dv` = `Σi(gross_i−f)/Σt e_t` = CHỈ SỐ QUYẾT ĐỊNH**
  (net trên 1 đơn vị gross-exposure, **bất biến size**); `e_t` = số **vị thế** đang mở tại `t`.
- **Trần 70 % — ĐÚNG 3 cách** (neo POST-HOC `100·0,02·d_t`, `d_t` = số coin PHÂN BIỆT đang mở): **(A)** `s = 70/gross_TB`
  · **(B95)** `s = 70/gross_p95` · **(Bmax)** `s = 70/gross_max` (**mọi tick ≤ 70 %** — kiểm: `gross_post` max = **70,00** ở
  **mọi** `K` và **mọi** cách, cả 2 pool). `net/tick SAU size = 100·0,02·s·net_tick` (%equity/tick).
- **CI:** block 72 h, `NREP=2000`, `SEED=20260905`, **một** `BI` dùng chung ⇒ **paired**; `k = 5` chính.
- **KIỂM HỢP LỆ (bắt buộc) — PASS ở cả 2 pool:** (a) `Δnet_coin(f)` **≡ `Δgross` độc lập `f`** trên cả 4 mức phí
  (lệch **0,00e+00** — §3.3 / §4.3); (b) `K=32` ⇒ **cả 3 đối tượng trùng khít** (Δ = `0,000000` tuyệt đối) ⇒
  máy xếp hạng/tính chỉ số đúng; (c) `noise − candidate` **KHÔNG** dương ngoài CI (RE: −3,59e−06; B2: −2,3e−07)
  ⇒ **không HARNESS_NGHI_NGỜ**.
- **LỖI ĐÃ BẮT + SỬA (ghi để tái lập):** bản đầu dùng mask `order < K` (**chỉ số cột gốc**) cho mảng phẳng dựng `e_t`/`d_t`
  ⇒ `e_t`, `d_t`, hệ số áp trần và `net_gr1dv` **sai** (dù `net_coin`/`net_tick` vẫn đúng vì lấy theo `argsort`).
  Đã sửa thành **mask theo VỊ TRÍ top-K** (`np.put_along_axis`) và **chạy lại TOÀN BỘ** cả 2 đường; mọi số dưới đây là
  số **sau sửa**. Kiểm chứng bắt được lỗi: `net_coin` **bất biến theo `f`** khớp tuyệt đối giữa 2 bản, còn `e_t(K=8)`
  nhảy 505 → 628 khi sửa (dấu hiệu mask cũ chọn sai vị thế).

## 2. ⚠️ B1 — KHAI THIÊN LỆCH: **100 % top-K nằm NGOÀI `P32`** (pre-reg §6, ngưỡng 10 % ⇒ **VƯỢT RẤT XA**)

| đối tượng | `K=8` | `K=10` | `K=12` | `K=16` | `K=32` |
|---|---|---|---|---|---|
| **`candidate`** | **100,0 %** (0/77.256) | 100,0 % | 100,0 % | 100,0 % | 100,0 % (1/309.024) |
| `baseline_fresh` | **100,0 %** (0/77.256) | 100,0 % | 100,0 % | 100,0 % | 100,0 % |
| `noise_ofi_check` | **100,0 %** (0/77.256) | 100,0 % | 100,0 % | 100,0 % | 100,0 % |

- Đo bằng **global top-K trên toàn universe 621 symbol** rồi đếm số nằm ngoài `P32`. Kiểm độc lập (hợp **3 seed**
  thay vì 1 seed 43): candidate **16**/116.916 (`0,014 %`), baseline **0**/115.288, noise **15**/118.606 ⇒ **cùng kết luận**.
- **Nguyên nhân (đo được):** `P32` do **S1** định nghĩa, và **S1 KHÔNG chọn major** (BTCUSDT/ETHUSDT: **0** lần trong
  309.024 dòng; S1 chọn `PEOPLEUSDT, CRVUSDT, AVAIIUSDT, MASKUSDT, RSRUSDT…`), trong khi **top-8 của candidate là major**:
  `BNBUSDT, 1000SHIBUSDT, XTZUSDT, DOTUSDT, SFPUSDT, XRPUSDT, 1INCHUSDT, ADAUSDT…` ⇒ **2 vũ trụ lựa chọn GẦN NHƯ RỜI NHAU**
  (Spearman TB theo tick *trong nội bộ* `P32` vẫn **+0,90**, nhưng top toàn cục thì không giao nhau).
- ⇒ **HỆ QUẢ BẮT BUỘC (pre-reg §6):** mọi con số trên `P32` phải gắn cờ **"KHÔNG ĐO ĐƯỢC hết"**; chúng chỉ nói
  *"xếp hạng lại **trong** rổ S1 không thêm gì"*, KHÔNG được đọc là "candidate dở". ⇒ **B2 là đường trả lời** (§4).

## 3. ĐƯỜNG RE (`P32`) — đo được nhưng **KHÔNG đại diện** (dùng làm đối chiếu)

### 3.1 MỨC @ `K = 8`, dưới trần 70 % (`*` = ngoài CI; **KHÔNG ô nào có `*`**)

| đối tượng | `net_coin` @0,000 / 0,004 / **0,006** / 0,008 (%/vòng) | **`net_gr1dv`** @0,006 (×10⁻³) |
|---|---|---|
| **candidate** | +1,2416 / +0,8416 / **+0,6416** / +0,4416 | **+0,10171** |
| `baseline_fresh` | +1,2561 / +0,8561 / **+0,6561** / +0,4561 | +0,10471 |
| `noise_ofi_check` | +1,2157 / +0,8157 / **+0,6157** / +0,4157 | +0,09812 |
| *cả 3 (trùng khít)* — `K=32` | +1,2678 / +0,8678 / **+0,6678** / +0,4678 | +0,11654 |

`BE_coin` = **1,2416 %** (candidate) · 1,2561 % (baseline) · 1,2157 % (noise) · 1,2678 % (`K=32`).
Trần 70 % ở đây **bind mạnh**: `gross_TB ≈ 98 %`, `gross_MAX = 168–170 %` ⇒ **(Bmax) size ≈ 0,41–0,42×**
(≈ 0,83 % equity/lệnh). `net/tick SAU size` @0,006 (Bmax): candidate **+4,2775** · baseline **+4,3223** ·
noise **+4,1046** (%equity/tick) — chênh lệch **trong CI**.

### 3.2 Δ ghép cặp theo tick @ `f = 0,006`, `K = 8` — **TRONG CI**

| Δ | n | `Δnet_coin` [CI5] | **`Δnet_gr1dv`** [CI5] | `Δnet/tick` sau (Bmax) [CI5] | ngoài CI? |
|---|---|---|---|---|---|
| `candidate − baseline_fresh` | 9.657 | −0,000144 [−0,002153, +0,001878] | **−3,0e−06** [−3,726e−05, +2,980e−05] | −0,00045 [−0,01383, +0,01309] | **KHÔNG** |
| `candidate − noise_ofi_check` | 9.657 | +0,000259 [−0,001434, +0,001991] | **+3,59e−06** [−2,324e−05, +3,196e−05] | +0,00173 [−0,00956, +0,01328] | **KHÔNG** |
| `noise_ofi_check − candidate` (KIỂM) | 9.657 | −0,000259 | −3,59e−06 | — | không dương ⇒ **PASS** |

**Ở cả 5 `K`** (10/12/16/32): mọi `Δ` **TRONG CI** (`K=32` ⇒ Δ = 0 tuyệt đối). **Ở cả 3 cách áp trần** và **cả 4 mức phí**
(vì `Δnet_coin ≡ Δgross` độc lập `f` — §3.3) ⇒ **không có `K*`**, **phí/cách áp trần không cứu được `Δ = 0`**.
*Phụ:* xếp theo **thứ tự S1** cho `gross` top-8 = **1,2006 %**, còn **candidate** và **baseline** cho **1,2416 / 1,2561 %**
⇒ cả 2 *nhích hơn* thứ tự S1 nhưng **chênh lệch giữa chúng = 0 ngoài CI**.

### 3.3 Kiểm bất biến theo phí — **ĐẠT**

`Δnet_coin(f)` của `candidate − baseline_fresh` (`K=8`): **−0,000144421096** ở **cả 4** mức `f`
(lệch `0,00e+00`) ⇒ **mô hình phí ĐÚNG**; phí chỉ đổi **MỨC**.

## 4. B2 — POOL MỞ RỘNG: **đường ĐO ĐƯỢC** cho chính những coin candidate chọn

### 4.1 Cổng chi phí (pre-reg §6) — **QUA CỔNG, không phải DỪNG**

| chỉ số (kernel `ofi-ext-labelb-cpu`) | giá trị |
|---|---|
| **Khoảng-fold ĐẦU** (`i00_20220401`) | **3,6 phút** (ngưỡng cổng **120 phút**) ⇒ **PASS** |
| Tổng 15 khoảng | **144,6 phút** (1 phiên Kaggle CPU, hạn 12 h) |
| Khoảng dài nhất | 24,6 phút (`i14_20251001`); dải 3,6 → 24,6 phút/khoảng |
| Mô phỏng | **166.080/166.080** cặp, `noentry = 0`, `OPEN_AT_END = 8` (0,005 %) |
| RAM đỉnh | **8,93 GB** |
| Cấu hình | **giữ nguyên** `KMAX=64`, `CHUNK_DAYS=90`, `TS_MAX_MS=1758992400000`, engine **NGUYÊN** (WEAK `cap=0,03`) |

### 4.2 MỨC @ `K = 8`, dưới trần 70 % (`*` = ngoài CI; **KHÔNG ô nào có `*`**)

| đối tượng | `net_coin` @0,000 / 0,004 / **0,006** / 0,008 (%/vòng) | **`net_gr1dv`** @0,006 (×10⁻³) | `BE_coin` | `gross_TB` | `gross_MAX` | `s_A` | `s_Bmax` | `net/tick` sau (Bmax) @0,006 |
|---|---|---|---|---|---|---|---|---|
| **candidate** | +1,1704 / +0,7704 / **+0,5704** / +0,3704 | **+0,07272** | 1,1704 % | 165,7 % | **302,0 %** | 0,422 | 0,232 | **+2,1154** |
| `baseline_fresh` | +1,2269 / +0,8269 / **+0,6269** / +0,4269 | +0,08001 | 1,2269 % | 163,2 % | 316,0 % | 0,429 | 0,222 | +2,2220 |
| `noise_ofi_check` | +1,1650 / +0,7650 / **+0,5650** / +0,3650 | +0,07249 | 1,1650 % | 168,1 % | 318,0 % | 0,416 | 0,220 | +1,9899 |
| *cả 3* — `K=32` | +1,2480…+1,2529 / **+0,6480…+0,6529** / … | +0,0909…+0,0917 | 1,248–1,253 % | 258 % | 452–458 % | 0,271 | 0,155 | +6,38…+6,44 |

- **Đọc đúng:** `MỨC` `net_coin` **dương** ở mọi mức phí (BE ≈ 1,17–1,23 %/vòng) — nhưng đó là **MỨC của RỔ**
  (nhãn luật thoát), **KHÔNG** phải kỹ năng xếp hạng; và `net_coin` của candidate **thấp hơn** baseline (Δ **trong CI**).
- Trần 70 % ở pool này **bind CỰC mạnh** (`gross_MAX = 302 %`) ⇒ size chỉ còn **0,232×** (≈ 0,46 % equity/lệnh)
  — vì vòng quay coin lớn (`d_mean = 82,8`, `d_max = 151`). `net/tick` sau size vẫn **dương** cho cả 3 (≈ +2,0…2,2 %equity/tick).
- **KHÔNG** được đọc bảng này là "candidate có tiền": cả 3 đối tượng **gần như trùng nhau**; phần chênh là **nhiễu**.

### 4.3 Δ ghép cặp theo tick @ `f = 0,006`, `K = 8` — **TRONG CI** (kết quả QUYẾT ĐỊNH)

| Δ | n | `Δnet_coin` [CI5] | **`Δnet_gr1dv`** [CI5] | `Δnet/tick` sau (Bmax) [CI5] | ngoài CI? |
|---|---|---|---|---|---|
| `candidate − baseline_fresh` | 9.657 | −0,000565 [−0,002152, +0,000961] | **−7,29e−06** [−2,757e−05, +1,258e−05] | −0,00106 [−0,00734, +0,00505] | **KHÔNG** |
| `candidate − noise_ofi_check` | 9.657 | +0,000054 [−0,001387, +0,001524] | **+2,3e−07** [−1,791e−05, +1,941e−05] | +0,00126 [−0,00440, +0,00642] | **KHÔNG** |
| `noise_ofi_check − candidate` (KIỂM) | 9.657 | −0,000054 | −2,3e−07 | — | không dương ⇒ **PASS** |

- Ở **cả 5 `K`**: `Δnet_gr1dv` = −7,3e−06 … +2,3e−07, **TRONG CI** mọi ô ⇒ **không có `K*`**.
- **Per-seed** (điểm phụ): `cand−base` = −1e−06 / +3e−06 / −5e−06 (s43/44/45) và `cand−noise` = +1e−06 / −5e−06 / +8e−06
  ⇒ **đổi dấu theo seed**, tất cả **TRONG CI** ⇒ **nhiễu**, không phải tín hiệu.
- **`Δnet_coin(f)` bất biến theo `f`**: **−0,000565073134** ở cả 4 mức ⇒ **ĐẠT**.
- ⚠️ **Đọc kèm:** `Δnet_coin` của candidate so baseline **ÂM** (−0,056 pp/vòng) dù trong CI; tức ở pool mở rộng
  candidate **không nhích hơn** baseline — nếu có gì thì **hơi kém hơn**, và **không phân biệt được với nhiễu** (noise).

## 5. KHAI BÁO TRUNG THỰC — **KHÔNG** ĐƯỢC NÓI GÌ

1. **KHÔNG** được nói "OFI có giá trị tiền": ở `f = 0,006`, `K = 8`, dưới trần 70 %, `Δnet_gr1dv` so **cả 2** đối chứng
   **nằm trong CI** ở **cả 2** pool; không ô nào ngoài CI ở `k = 2/5/10`.
2. **KHÔNG** được đọc các số `P32` (§3) là đánh giá candidate: **100 %** lựa chọn của nó nằm ngoài pool đó (§2).
3. **KHÔNG** được nói "MỨC dương ⇒ ranker kiếm được tiền": `net_coin > 0` là **MỨC của RỔ/luật thoát**, không phải xếp hạng.
4. **KHÔNG** được nói "thêm 2 feature là vô hại": thêm 2 cột = **47 cột** ⇒ **đụng đường ONNX/LIVE** ⇒ cần owner duyệt riêng.
5. **GIỚI HẠN PHẢI ĐỌC KÈM:** (a) nhãn (b) là **bản bảo thủ** (WEAK `cap=0,03`, 1 leg, không funding, bỏ ~6,9 % cặp);
   (b) `gross` là **đo trên luật thoát + quy đổi POST-HOC `2,0 %/lệnh` trên coin PHÂN BIỆT** — **KHÔNG** phải equity LIVE
   (không de-dup live, không DCA nhiều chân, không trần size/notional, không funding, không margin-call);
   (c) `net/tick` sau size là **MÔ HÌNH**; (d) **B2 chỉ phủ `K = 8`** (K vận hành) và **hợp 3 seed** cho tập coin mới —
   `K ∈ {10…32}` của candidate **không** được build nhãn mới (xem §6); (e) B2 **không** thay thế việc quét thời gian OOS mới:
   vẫn là **1 cửa sổ dữ liệu DEV**.
6. **KHÔNG** chạm ONNX/LIVE/`2026`/`HoldoutSeal`; **KHÔNG** push git.

## 6. VIỆC BỎ + LÝ DO

| # | việc | trạng thái | lý do |
|---|---|---|---|
| 1 | Chấm candidate trên `P32` (RE) | ✅ XONG (~1,3 phút) | đường rẻ, chạy trước; **bị vô hiệu bởi B1** |
| 2 | Đo tỷ lệ trùng nhau B1 | ✅ XONG | bắt buộc; kết quả **100 % ngoài** ⇒ gắn cờ "không đo được" cho đường RE |
| 3 | Cổng chi phí B2 (1 fold) | ✅ XONG — **3,6 phút < 120 phút** ⇒ QUA | bắt buộc trước khi mở rộng pool |
| 4 | B2 — build nhãn 166.080 cặp coin MỚI + chấm lại | ✅ XONG (144,6 phút Kaggle CPU) | **đường duy nhất trả lời được** câu hỏi |
| 5 | `K ∈ {10,12,16}` trên pool mở rộng **với nhãn MỚI** | ⛔ BỎ (một phần) | hợp 3 seed × 3 mức K cho cả 3 đối tượng ⇒ **~2–3× thời gian Kaggle**; chạy `K>8` **trên pool hiện có** đã cho mọi Δ **trong CI** ⇒ không đổi kết luận |
| 6 | Sweep hyperparameter / train lại / đổi luật thoát / funding / DCA / de-dup live | ⛔ BỎ | ngoài phạm vi pre-reg; **2 vòng tiền trước đã đóng trục này** |
| 7 | Chạy Java/sim, `claude-run`, chạm LIVE/`HoldoutSeal` | ⛔ BỎ | ràng buộc đề bài (shadow-c3 đang LIVE) |
| 8 | Tải `pred_*.parquet` về lâu dài trên Oracle | ⛔ BỎ | đĩa `/` 93 %; chỉ để tạm, **xoá ngay sau khi chấm** |

## 7. KẾT LUẬN (1 dòng)

**OFI candidate là tín hiệu TĂNG SELECTOR nhưng KHÔNG quy ra TIỀN — lần thứ 3**: ở `f = 0,6 %/vòng`, dưới trần
gross **70 % CỨNG**, `Δnet` (chỉ số quyết định `net/1đv-gross`) so **cả** `baseline_fresh` **và** `noise_ofi_check`
**nằm TRONG CI** ở **mọi `K`**, **mọi mức phí**, **cả 3 cách áp trần** và trên **cả 2 pool** — kể cả pool mở rộng
đã build nhãn luật thoát cho **chính 166.080 cặp coin mà candidate chọn** (đường RE trên `P32` **không đo được**:
100 % top-K nằm ngoài `P32`); khuyến nghị **KHÔNG** tích hợp (2 feature = 47 cột ⇒ đụng ONNX/LIVE, cần owner duyệt riêng).
