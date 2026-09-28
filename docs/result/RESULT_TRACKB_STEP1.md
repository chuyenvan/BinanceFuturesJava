# RESULT_TRACKB_STEP1 — harness Python cho SLEEVE market-neutral cross-section (KHÔNG sim)

Ngày đo: **2026-09-28**. Pre-reg: `docs/prereg/PREREG_TRACKB_CROSSSECTION.md` (**commit `642afbd`**,
chốt **TRƯỚC** khi đo bất kỳ số nào; sau đó **không sửa thiết kế**).
Code: `research/trackb/build_panel.py` (dựng panel), `research/trackb/run_trackb.py` (đo).
JSON: `docs/result/trackb_step1.json`.
**Thuần Python offline**, **0 train / 0 sim**, **không** job nặng trên Oracle, **không** chạm
production/`242`/ONNX/LIVE, **không** push file dữ liệu, **DEV only** (mọi cửa sổ `< 2026-01-01`).

---

## 0. KẾT LUẬN (một dòng)

> **NULL ở cấu hình pre-reg (phí `0,76 %/vòng`).** `BOOK_EW` (4 tín hiệu) **net −0,121 %/ngày**
> (`TO 0,351/ngày` ⇒ **10,5 vòng/tháng**; phí `0,266 %/ngày` ăn hết gross `+0,140 %/ngày`),
> CI block **ngoài 0 về phía ÂM** (không phải thiếu power: `MDE80 = 0,031 %/ngày < |net| 0,121 %`),
> **Rào (a)/(b′) FAIL** cả hai. **Phí hoà vốn = `0,414 %/vòng`** — thấp hơn `0,76 %` tới **45 %**.
> Chỉ **1/4 book con** net dương: **`vol` +0,067 %/ngày** (`TO 0,071/ngày`) — nhưng **CI chứa 0** và
> **Rào FAIL** (`share top-1 % = 484 %`, `TF25 = −26,0`) ⇒ **không deploy**. **`ΔOI` là tín hiệu
> TỆ NHẤT** (net `−0,389 %/ngày`, `TO 0,752/ngày`) ⇒ **bỏ khỏi book ngày**.
> **Câu (1): `t = 6,47` của `spread S1 L/S` KHÔNG còn dùng được** — tái lập **đúng** `+0,8267 %/72h`
> và **đúng `t_iid = 6,47`**, nhưng **CI block-72h `[−0,481 %, +2,135 %]`, `t_block = 1,24`**
> (cửa sổ 15′ chồng lấn làm **phồng t ≈ 5,2×**).

---

## 1. UNIVERSE + 4 TÍN HIỆU (đã chốt ở pre-reg §1/§3)

- **Universe**: **top-200** trong 627 USDT-perp theo **`dv_med`** (trung vị USD-volume/ngày trên **60 ngày
  mẫu** ngày-15 mỗi tháng 2021-01…2025-12; cần `≥ 12` mẫu). **CÓ major** (BTC/ETH trong top-200).
  Điều kiện động/ngày: có giá `t` & `t−24h`, `≥ 30` ngày lịch sử, có cả OI và funding.
  **`n_elig`/ngày: median 137 (min 51, max 183).** Số ngày giao dịch: **1 460**
  (2022-01-01 … 2025-12-30, hold kết thúc 2025-12-31).
- **Nhịp**: **ngày**, 00:00 UTC; hold **24h**; decile `n_dec = round(0,10·N_elig)`;
  **hysteresis `band = 2`**: vào khi `u < 0,10` / ở lại khi `u < 0,30` (short đối xứng);
  equal-weight, chân long **+0,5** / chân short **−0,5**. Trung vị **34,8 vị thế/ngày**.
- **Phí**: `fee_rt = 0,76 %/vòng` (taker 0,05 %×2 + trượt giá 0,33 %×2) × `TO_t = ½Σ|Δw|`;
  **funding tính vào net** (`P_fund = −Σ w_i·f_i`, short coin funding dương ⇒ THU).
  **Trần squeeze**: `|w_i| ≤ 2×|w_nominal|`; **stop 24h tại −10 %** (+0,5 % trượt giá khi khớp stop).

| # | tín hiệu | định nghĩa (1 dòng) |
|---|---|---|
| f1 | `funding` | `Σ` funding rate trong `(t−24h, t]` — **cao = SHORT** (crowded-long trả phí) |
| f2 | `dOI` | `oi_delta24h` (cột 0 OI bin) tại `t` — **cao = SHORT** (Q9 ΔOI cao nhất là nhóm tệ nhất) |
| f3 | `vol` | `std` log-return **1h** trên **168h** gần nhất — **cao = SHORT** (vol IC −0,09) |
| f4 | `reversal` | `close[t]/close[t−168h] − 1` — **cao = SHORT** (loser long) |

**IC trung bình (rank vs `fwd24h`), đo được:** `funding +0,0061` · `dOI −0,0237` ·
**`vol −0,0819`** (≈ −0,09 đã công bố ✔) · `reversal −0,0446`.
⇒ **cả 4 tín hiệu đều có dấu ĐÚNG** (high ⇒ return thấp), `vol` mạnh nhất.

---

## 2. BẢNG CHÍNH — tín hiệu × book (`band=2`, phí `0,76 %/vòng`, 1 460 ngày)

| object | gross/ngày | fund/ngày | **fee/ngày** | **net/ngày** | TO/ngày | **TO/tháng** | Sharpe | maxDD | winrate ngày |
|---|---|---|---|---|---|---|---|---|---|
| `funding` | +0,0985 % | +0,0734 % | 0,2529 % | **−0,0809 %** | 0,333 | 9,99 | −1,49 | −138,0 % | 0,402 |
| `dOI` | +0,1971 % | −0,0155 % | 0,5703 % | **−0,3887 %** | 0,752 | **22,55** | −6,21 | −569,5 % | 0,312 |
| **`vol`** | +0,1431 % | −0,0229 % | 0,0538 % | **+0,0665 %** | **0,071** | **2,12** | **+0,82** | −40,4 % | 0,497 |
| `reversal` | +0,1202 % | −0,0137 % | 0,1878 % | **−0,0812 %** | 0,247 | 7,41 | −1,11 | −134,0 % | 0,441 |
| **`BOOK_EW`** | **+0,1398 %** | +0,0053 % | **0,2662 %** | **−0,1211 %** | 0,351 | 10,52 | −2,92 | −184,4 % | 0,375 |
| `BOOK_RANK` (phụ) | +0,1630 % | +0,0096 % | 0,3590 % | −0,1864 % | 0,472 | 14,17 | −3,07 | −280,9 % | 0,393 |

| object | **Rào (a)** `share top-1 % ≤ 15 %` | **Rào (b′)** `TF(25 %) > 0` | `q*` | `asym` | `pnl_vol_norm` |
|---|---|---|---|---|---|
| `funding` | FAIL (N/A: Σ<0) | **FAIL** (−31,20) | 0,5 % | 0,33 | −0,00020 |
| `dOI` | FAIL (N/A: Σ<0) | **FAIL** (−39,83) | 0,5 % | 0,30 | −0,00087 |
| `vol` | **FAIL (484,3 %)** | **FAIL** (−26,01) | 0,5 % | 0,39 | **+0,00012** |
| `reversal` | FAIL (N/A: Σ<0) | **FAIL** (−33,46) | 0,5 % | 0,34 | −0,00021 |
| **`BOOK_EW`** | **FAIL (N/A: Σ<0)** | **FAIL** (−32,67) | 0,5 % | 0,34 | −0,00008 |
| `BOOK_RANK` | FAIL (N/A: Σ<0) | **FAIL** (−32,88) | 0,5 % | 0,30 | −0,00041 |

- **`q* = 0,5 %` cho MỌI object** = bước nhỏ nhất đã làm `TF ≤ 0` ⇒ **không có đuôi bền**:
  bỏ top 0,5 % leg là tổng đã âm.
- `share top-1 %` **vô nghĩa khi Σ < 0** ⇒ ghi **FAIL/N/A** (không được đọc thành PASS).
- **`vol`** là object duy nhất Σ > 0, và **cũng FAIL (a) nặng (484 %)** ⇒ lợi nhuận **tập trung ở
  ~1 % leg tốt nhất**, không phải edge phân tán.

---

## 3. ĐỐI CHỨNG COIN NGẪU NHIÊN (`n = 200`, seed `20260928`)

| | net/ngày | gross/ngày | TO/ngày |
|---|---|---|---|
| control (mean) | **−0,5985 %** | **+0,0642 %** | 0,872 |
| control p5 / p95 | −0,6286 % / −0,5689 % | — | — |
| **`BOOK_EW`** | **−0,1211 %** | **+0,1398 %** | **0,351** |
| **chênh (book − control)** | **+0,4774 %** | **+0,0755 %** | −0,521 |

- **`BOOK_EW` > p95(control)** ⇒ **có kém control** — nhưng **chênh GROSS chỉ +0,076 %/ngày**.
  ⇒ **~85 % "lợi thế" của book đến từ TURNOVER THẤP, KHÔNG phải từ tín hiệu.**
- Cả book và control đều **net ÂM** ở phí `0,76 %`.

---

## 4. PHÍ + HYSTERESIS (chỗ quyết định — đúng cảnh báo kỹ thuật)

**Độ nhạy phí** (`BOOK_EW`, TO/d `0,351`):

| `fee_rt` | 0,30 % | 0,50 % | **0,76 %** | 1,00 % |
|---|---|---|---|---|
| net/ngày | **+0,0399 %** | −0,0302 % | **−0,1214 %** | −0,2056 % |

- **PHÍ HOÀ VỐN = `0,414 %/vòng`** (cần thấp hơn `0,76 %` **45 %**).
- **Turnover trần để hoà vốn: `TO/ngày ≤ 0,191`** (⇒ **giữ trung bình ≥ 5,2 ngày/leg**);
  cấu hình hiện tại `TO/d = 0,351` (giữ ~2,9 ngày) ⇒ **cần giảm turnover ~46 %** nữa.

**Độ nhạy hysteresis:**

| `band` | net/ngày | TO/ngày | TO/tháng | Sharpe | vị thế tb/ngày |
|---|---|---|---|---|---|
| 1 (không) | −0,1760 % | 0,433 | 12,99 | −3,96 | 27,5 |
| **2 (chính)** | **−0,1211 %** | 0,351 | 10,52 | −2,92 | 34,4 |
| 3 | **−0,0912 %** | 0,302 | 9,06 | −2,29 | 40,1 |

⇒ Hysteresis **giúp thật** (band 1→3: `+0,085 %/ngày`) và **giảm turnover 30 %**, nhưng **vẫn không đủ**:
ngay cả `band = 3` cũng chỉ đưa net lên `−0,091 %/ngày`; **cần `band ≳ 5` (giữ ≥ 5,2 ngày)** mới hoà vốn.

**Biến thể khác:** **tắt stop −10 % ⇒ tệ hơn hẳn** (`−0,2545 %` vs `−0,1211 %`) ⇒ **trần squeeze có giá
trị thật** (+0,133 %/ngày). Dùng `fsum` realized (`t+1`) thay trailing: `−0,1225 %` ≈ như cũ
⇒ ước lượng funding causal **không phải** nguồn sai.

---

## 5. CI + MDE (block bootstrap khối 10 ngày, NREP 2000, seed `20260905`)

| object | net/ngày | CI raw95 | CI `inflate(8)=2,0393` | p(>0) | **MDE80** | 2,8×SD(null) |
|---|---|---|---|---|---|---|
| `vol` | +0,0665 % | **[−0,0007 %, +0,1337 %]** | [−0,0706 %, +0,2035 %] | 0,972 | 0,0433 % | 0,0977 % |
| **`BOOK_EW`** | −0,1211 % | [−0,1648 %, −0,0774 %] | [−0,2102 %, −0,0320 %] | 0,000 | **0,0312 %** | 0,0728 % |

- **`BOOK_EW`: CI ngoài 0 về phía ÂM** và `|net| (0,121 %) > MDE80 (0,031 %)` ⇒ **ĐỦ power**, kết luận
  **ÂM là thật**, **không** phải "thiếu power".
- **`vol`: CI raw95 chứa 0 sát biên** (`−0,0007 %`), CI nới cũng chứa 0 ⇒ **KHÔNG kết luận được dương**;
  `MDE80 (0,043 %) < net (0,067 %)` ⇒ **đủ power để thấy cỡ này**, nhưng **không đủ để vượt CI**
  ⇒ **dấu dương nhưng chưa đạt ngưỡng**.

---

## 6. CÂU (1) — `spread S1 L/S` TÍNH LẠI BẰNG CI BLOCK

Cùng công thức `RESEARCH_SHORT` §2.3 (long **8 điểm thấp nhất** vs short **8 điểm cao nhất** mỗi
`decision-ts` nhịp 15′, `f72 = close[t+72h]/close[t] − 1`), pool = giao `pred_s1a2x1 ∩ cand_dev`:

| mẫu | n obs | tick | lo8 | hi8 | **spread** | `t_iid` | **CI block-72h** | **`t_block`** | p(>0) |
|---|---|---|---|---|---|---|---|---|---|
| **`pool_canddev`** (tái lập) | **774 148** | **4 595** | +0,7939 % | −0,0328 % | **+0,8267 %/72h** | **6,47** | **[−0,481 %, +2,135 %]** | **1,24** | 0,901 |
| `pool_allparq` (mở rộng tới 2025-12) | 6 484 722 | 17 042 | −0,3748 % | −0,0676 % | **−0,3071 %/72h** | −2,64 | [−2,449 %, +1,835 %] | −0,28 | 0,367 |

- **TÁI LẬP ĐÚNG**: `n = 774 148` · `4 595` tick · `lo8 = +0,7939 %` · `hi8 = −0,0328 %` ·
  **`spread = +0,8267 %/72h`** · **`t_iid = 6,47`** — khớp từng chữ số với `RESEARCH_SHORT` §2.3
  ("+0,83 %/72h, t=6,47").
- **NHƯNG với block bootstrap khối 72h** (303 khối, 2 000 rep, seed `20260905`):
  **CI95 = `[−0,481 %, +2,135 %]` (chứa 0)**, **`t_block = 1,24`**, `p(>0) = 0,901`.
  Khối 10 ngày còn rộng hơn: CI `[−0,783 %, +2,437 %]`, `t_block = 1,01`.
- ⇒ **`t = 6,47` bị PHỒNG ≈ 5,2×** do cửa sổ 72h **chồng lấn** ở nhịp 15′ (≈ 288 tick/72h).
  **Con số `6,47` KHÔNG còn dùng được làm bằng chứng ý nghĩa thống kê.**
- **Bằng chứng phụ (dấu không ổn định)**: mở rộng pool tới 2025-12 ⇒ spread **đổi dấu**
  (`−0,307 %/72h`) và `t_block = −0,28`.
- Xu hướng decile vẫn **giảm đơn điệu** (`q0 = +1,024 % → q9 = −0,024 %`) ⇒ **hướng tín hiệu là thật,
  nhưng độ lớn không đủ để tách khỏi 0 khi tính đúng cửa sổ chồng lấn.**

---

## 7. TRẢ LỜI 6 CÂU (bắt buộc)

1. **`spread S1 L/S` bằng CI block = bao nhiêu, `t = 6,47` còn đúng không?**
   → **`+0,8267 %/72h` tái lập đúng** (t_iid **6,47**), nhưng **CI block-72h = `[−0,481 %, +2,135 %]`,
   `t_block = 1,24`**. ⇒ **KHÔNG còn đúng** — `t` cũ **phồng ≈ 5,2×**; mở rộng mẫu còn **đổi dấu**.
2. **Book ghép có NET dương sau phí `0,76 %` không?**
   → **KHÔNG.** `BOOK_EW` **−0,1211 %/ngày** (`TO 0,351/ngày`, **10,5 vòng/tháng**).
   **Phí hoà vốn `0,414 %/vòng`**; **trần turnover `TO/d ≤ 0,191`** (giữ **≥ 5,2 ngày/leg**).
3. **Rào (a)/(b′).** → **FAIL cả hai, cho cả 6 object.** `BOOK_EW`: (a) N/A (Σ<0), (b′) `TF25 = −32,67`.
   Ngay **`vol`** (Σ>0) cũng **(a) FAIL `484 %`**, **(b′) FAIL `−26,01`**. `q* = 0,5 %` mọi object
   ⇒ **không có đuôi bền**.
4. **Kém đối chứng ngẫu nhiên không?** → **CÓ kém hơn về NET** (`−0,121 %` vs `−0,599 %`, > p95)
   **nhưng lợi thế gần như toàn bộ nhờ turnover thấp**: chênh **GROSS chỉ `+0,076 %/ngày`**
   (book `+0,140 %` vs random `+0,064 %`) ⇒ **giá trị tín hiệu rất nhỏ**; cả hai đều net âm.
5. **MDE của thiết kế ⇒ có đủ power không?**
   → **CÓ.** `MDE80(BOOK_EW) = 0,031 %/ngày` (`2,8·SD(null) = 0,073 %`), **nhỏ hơn** `|net| = 0,121 %`
   ⇒ kết luận **ÂM là thật**, **không** phải thiếu power. `MDE80(vol) = 0,043 %` cũng đủ power,
   nhưng dương **chưa vượt CI** ⇒ **chưa kết luận**.
6. **Kết luận: có đáng lên bước 2 không?** → **KHÔNG (NULL)** ở cấu hình pre-reg.
   Điều kiện để **đáng** (phải đo lại, không suy diễn): **phí thật ≤ 0,41 %/vòng**
   **HOẶC** kéo `TO/d ≤ 0,19` (giữ **≥ 5,2 ngày** — cần `band ≳ 5`), **VÀ** book phải vượt Rào (a)/(b′).
   Hiện **không đạt mục nào**.

---

## 8. MỤC NÀO BỎ + LÝ DO

| mục | quyết định | lý do (số đo) |
|---|---|---|
| **`ΔOI` ở nhịp NGÀY** | **BỎ** | net `−0,389 %/ngày` (tệ nhất), `TO/d 0,752` (**2,1×** book), IC `−0,024`, Sharpe `−6,21` ⇒ ΔOI quá nhiễu ở nhịp ngày |
| `funding` (L/S thuần) | **BỎ** ở nhịp ngày | net `−0,081 %/ngày`; `fund/d +0,073 %` (**thu funding THẬT**, đúng cơ chế) nhưng **fee/d 0,253 %** ⇒ **cost/gross 257 %**; `TO/d 0,333` |
| `reversal` 7 ngày | **BỎ** ở nhịp ngày | net `−0,081 %/ngày`; `TO/d 0,247`; IC `−0,045` quá nhỏ so với phí |
| **`vol` 168h** | **GIỮ làm hướng DUY NHẤT còn lại — nhưng KHÔNG deploy** | net `+0,067 %/ngày`, `TO/d 0,071` (**2,1 vòng/tháng**), Sharpe `+0,82`; nhưng **CI chứa 0** và **Rào (a)/(b′) FAIL** |
| `BOOK_EW` / `BOOK_RANK` | **BỎ** | net âm, CI ngoài 0 phía âm, Rào FAIL, thắng control chỉ nhờ turnover |
| trần squeeze / stop −10 % | **GIỮ** (có giá trị) | tắt stop ⇒ net `−0,2545 %` vs `−0,1211 %` (xấu đi **0,133 %/ngày**) |
| hysteresis | **GIỮ**, cần mạnh hơn | band 1→3: net `−0,176 → −0,091 %/ngày`, `TO 0,433 → 0,302` |
| ngưỡng "dislocation" (chỉ vào khi lệch ≥ ngưỡng) | **CHƯA đo** | ngoài phạm vi lần này; đề xuất cho bước sau **nếu** có đường phí ≤ 0,41 % |

**Harness đã để lại (tái dùng được, không sim):** `research/trackb/build_panel.py` +
`research/trackb/run_trackb.py` (panel ngày từ 4 nguồn; book L/S equal-weight; hysteresis; trần squeeze;
Rao (a)/(b′)/`q*`/`asym`/`pnl_vol_norm`; CI block; MDE; đối chứng ngẫu nhiên; độ nhạy phí/hysteresis;
tái lập `spread S1`). Chạy lại **~76 s**, panel trung gian **45,8 MB** ở `/tmp/trackb/` (**đã dọn**).
