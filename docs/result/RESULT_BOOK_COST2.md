# RESULT_BOOK_COST2 — spread TRÍCH DẪN + impact (Binance Vision MIỄN PHÍ) ⇒ chấm lại Track B

Ngày đo: **2026-09-28**. Pre-reg: `docs/prereg/PREREG_BOOK_COST2.md` (**commit `b8bcca9`**, chốt **TRƯỚC**;
sau đó **không sửa thiết kế**). Code: `research/analysis/vision_micro.py` (đo) +
`research/trackb/cost2_trackb.py` (chấm lại Track B).
JSON: `docs/result/book_cost2.json` + `docs/result/book_cost2_trackb.json`.

**Tuân thủ:** thuần Python **offline** · **0 train / 0 sim** · **không** chạm production/`242`/ONNX/LIVE ·
**không push file dữ liệu** · **DEV ≤ 2025-12-31** (không chạm 2026) · tải **có chặn dung lượng** (HTTP
Range + raw-inflate streaming, **dừng khi qua cửa sổ**, **không ghi zip/csv ra đĩa**) · không dùng API key.

---

## 0. KẾT LUẬN (một dòng)

> **Track B KHÔNG NULL vì chi phí ⇒ MỞ LẠI.** Chi phí **CÓ HƯỚNG** đo trên dữ liệu thật
> (`bookTicker` + `aggTrades`) = **0,112 %/vòng** (`size 2 000 USDT`, median) — **thấp hơn hoà vốn
> `0,414 %` tới ~3,7×**. Ở chi phí đó `BOOK_EW` net **+0,106 %/ngày**, **CI95 `[+0,062 %, +0,150 %]`
> (ngoài 0 về phía DƯƠNG)**, MDE80 `0,032 %` ⇒ **đủ power**. Con số **0,757 %/vòng** cũ là
> **`|slip|` vô hướng = NHIỄU**, không phải chi phí. **NHƯNG** Rào (a)/(b′) **vẫn FAIL** ⇒
> **được lên bước 2, KHÔNG được deploy**.

---

## 1. NGUỒN DỮ LIỆU (đúng pre-reg §1)

| Thành phần | Nguồn | Loại |
|---|---|---|
| **Spread TRÍCH DẪN (bid/ask)** | Binance Vision `futures/um/daily/bookTicker` (L1 thật: `best_bid_price/qty, best_ask_price/qty`) | **ĐO** |
| **Trade + bên taker** | Binance Vision `futures/um/daily/aggTrades` (`price, quantity, is_buyer_maker`) | **ĐO** |
| **Phí mỗi chân** | `0,0491 %/chân` = `8,9061 / 18 135,48` (991 chân thật) — `RESULT_LIVE_FILLS_AUDIT.md` | **ĐO** |
| Hạng thanh khoản | `dv_med` (panel `build_panel.py`) — **đúng cách `RESULT_TRACKB_STEP1`** | ĐO |

**Tải kiểu BOUNDED:** `Range` ≤ **8 MB nén/file** + `zlib` raw-inflate **streaming**, **dừng ngay** khi
`transaction_time >` cửa sổ. (BTC `bookTicker` 1 ngày = **1,13 GB giải nén / 128 MB nén** ⇒ bắt buộc chặn.)

⚠️ **LỆCH SO VỚI PRE-REG (khai rõ):** pre-reg chốt 4 ngày **2025**; kiểm tra **trước khi đo** thấy
`bookTicker` daily **chỉ được publish trong cửa sổ ~2023-05-16 … 2024-03-30** (mọi ngày 2025 ⇒ **404**).
Theo **đúng luật pre-reg §2 "(404 ⇒ bỏ ngày đó, ghi lại)"**, chọn lại **4 ngày cùng vị trí trong cửa sổ có dữ
liệu**: **2023-06-14 · 2023-09-13 · 2023-12-13 · 2024-03-13**.

**Cửa sổ đo:** `[00:00:00, 00:30:00) UTC` (quanh **mốc rebalance 00:00 UTC**). **Mẫu:** 6 symbol/nhóm
(theo quy tắc tất định pre-reg §2) → **14/18 symbol** có dữ liệu, **50 symbol-ngày** đo được
(**22/72** symbol-ngày thiếu: FARTCOIN/LUNA/PENGU/ZRO/TURBO chưa niêm yết ở các ngày đó) ·
**363 725 trade** phân tích.

---

## 2. SPREAD TRÍCH DẪN + EFFECTIVE SPREAD (số ĐO)

`qs` = `(ask−bid)/mid × 100` (%/vòng) · `e` = `sign × (p_trade − mid)/mid × 100` (%/chân),
`sign = +1` nếu taker BUY. `h_g(S)` = phân vị của `e` trên trade có notional ∈ `[S/√2, S·√2)`.

| nhóm | symbol (mẫu) | n trade | **`qs` median** | **`qs` p90** | L1 notional (med) | % trade > L1 |
|---|---|---|---|---|---|---|
| **G1** (hạng 1–20) | ETH, 1000PEPE, SUI, LINK | 164 095 | **0,0012 %** | 0,0153 % | 2 411 USDT | 22,6 % |
| **G2** (21–100) | ARB, ATOM, BCH, FIL, ORDI | 149 332 | **0,0085 %** | 0,0214 % | 2 056 USDT | 22,8 % |
| **G3** (101–200) | AR, NEO, OCEAN, SNX | 50 298 | **0,0197 %** | 0,0409 % | 533 USDT | 23,1 % |

**`h_g(S)` (%/chân, median / p90) — "impact" hiệu dụng cho size thật:**

| nhóm | `h(700)` | `h(2 000)` | `h(5 000)` |
|---|---|---|---|
| G1 | 0,0024 / 0,0129 | **0,0016** / 0,0151 | 0,0006 / 0,0214 |
| G2 | 0,0036 / 0,0155 | **0,0040** / 0,0212 | 0,0043 / 0,0324 |
| G3 | 0,0079 / 0,0240 | **0,0098** / 0,0318 | 0,0118 / 0,0549 |

- **`h` ở median ≈ NỬA spread trích dẫn** (khớp lệnh **tại giá tốt nhất**, ví dụ ETH: buy khớp **đúng
  ask**, `|p−ask| = 0`) ⇒ **impact vượt nửa-spread ≈ 0** ở median; chỉ **p90** mới thấy impact.
- **`imp = h − qs/2`** ⇒ median **~0** (G1 2 000: `+0,0010`; G2 `−0,0002`; G3 `−0,0000`); p90 mới dương
  (G3 5 000: `+0,023 %`). Một số ô **âm nhẹ** = trade khớp **trong** spread (mid nhích) — báo nguyên trạng.

---

## 3. CHI PHÍ CÓ HƯỚNG /VÒNG (công thức pre-reg §3)

`C_g(S) = 2·fee + 2·h_g(S)`, `fee = 0,0491 %/chân`; `C(S) = Σ_g w_g·C_g(S)`, `w = (0,10 · 0,40 · 0,50)`.

| `C_g(2 000)` median | G1 | G2 | G3 |
|---|---|---|---|
| %/vòng | **0,1013** | **0,1063** | **0,1179** |

| `S` (USDT) | `C` median | `C` p90 (stress) |
|---|---|---|
| 700 | **0,1095** | 0,1371 |
| **2 000 (trung tâm)** | **0,1116** | 0,1500 |
| 5 000 | **0,1135** | 0,1833 |

- **`C(2 000)` = `0,112 %/vòng` ≪ hoà vốn `0,414 %`** (và **cả `C` stress p90 @5 000 = `0,183 %`** cũng ≪ 0,414).
- **Phí sàn `2×0,0491 = 0,098 %` chiếm ~88 %** chi phí có hướng; **spread+impact chỉ ~0,014 %/vòng**.
- **So với số cũ:** `2×h(2 000)` ≈ `0,01–0,02 %/vòng` so với **Roll(1m) = `0,075 %/vòng`** ⇒ **Roll bị
  thiên lên ~4–7×**, đúng cảnh báo `RESULT_BOOK_COST` §4.

---

## 4. CHẤM LẠI TRACK B (VIỆC 2 — cùng harness `RESULT_TRACKB_STEP1`)

`net_new[t] = gross[t] + fund[t] − Σ_g TO_g[t]·C_g(S)`; `TO_g` = `½Σ_{i∈g}|Δw_i|`.
**Kiểm chứng harness:** chạy lại ở `0,757 %` cho **net `−0,1200 %/ngày`** và **hoà vốn `0,4137 %`**
⇒ **khớp `RESULT_TRACKB_STEP1`** (`−0,1211 %`, `0,414 %`) ⇒ tái lập **đúng**.

**`BOOK_EW` (4 tín hiệu, `band=2`, 1 460 ngày):**

| chi phí | fee/ngày | **net/ngày** | CI95 raw | MDE80 | Rào (a)/(b′) |
|---|---|---|---|---|---|
| **`C` CÓ HƯỚNG `0,112 %`** | 0,0392 % | **+0,1059 %** | **[+0,0615 %, +0,1502 %]** | 0,0316 % | **FAIL / FAIL** |
| stress `0,183 %` (p90, 5 000) | 0,0648 % | +0,0803 % | [+0,0361 %, +0,1245 %] | 0,0304 % | FAIL / FAIL |
| flat `0,173 %` (sàn cũ) | 0,0606 % | +0,0845 % | [+0,0402 %, +0,1288 %] | 0,0303 % | FAIL / FAIL |
| flat `0,414 %` (hoà vốn) | 0,1450 % | +0,0001 % | [−0,0440 %, +0,0442 %] | 0,0294 % | FAIL / FAIL |
| flat `0,757 %` (kết luận cũ) | 0,2651 % | −0,1200 % | [−0,1637 %, −0,0763 %] | 0,0311 % | FAIL / FAIL |

**Book con ở chi phí có hướng `0,112 %`** — **CẢ 4 đều DƯƠNG**:

| book con | net/ngày | TO/ngày | CI95 raw | net @`0,414 %` | (a)/(b′) |
|---|---|---|---|---|---|
| `funding` | +0,1347 % | 0,333 | [+0,081 %, +0,188 %] | +0,0341 % | FAIL/FAIL |
| `dOI` | +0,0974 % | 0,752 | [+0,031 %, +0,164 %] | −0,1297 % | FAIL/FAIL |
| **`vol`** | +0,1124 % | **0,071** | [+0,045 %, +0,180 %] | **+0,0909 %** | FAIL/FAIL |
| `reversal` | +0,0790 % | 0,247 | [+0,005 %, +0,153 %] | +0,0043 % | FAIL/FAIL |

- **CI ngoài 0 phía DƯƠNG** cho `BOOK_EW` và **cả 4 book con** ⇒ **khác hẳn kết luận NULL cũ**.
- **Nhưng Rào (a) `share top-1 % ≤ 15 %` và (b′) `TF(25 %) > 0` vẫn FAIL cho MỌI object** ⇒ lợi nhuận vẫn
  **tập trung ở vài leg tốt nhất**, không phải edge phân tán.

**Đối chứng coin ngẫu nhiên** (giữ nguyên số cũ, chỉ đổi phí): control `gross +0,0642 %`, `TO 0,872`
⇒ net **−0,0331 %/ngày**; `BOOK_EW` **+0,1006 %/ngày**. **Chênh GROSS chỉ `+0,0755 %/ngày`**
⇒ **~85 % "lợi thế" vẫn đến từ TURNOVER THẤP, KHÔNG phải từ tín hiệu** (kết luận cũ giữ nguyên).

---

## 5. TRẢ LỜI 4 CÂU (bắt buộc)

**(1) Chi phí CÓ HƯỚNG /vòng = bao nhiêu?**
→ **0,112 %/vòng** (`size 2 000 USDT`, median) — **nguồn: `bookTicker` (spread trích dẫn) + `aggTrades`
(effective spread/impact), Binance Vision miễn phí**. Theo nhóm: **G1 `0,101` · G2 `0,106` · G3 `0,118`**
(%/vòng). Theo size: **700 → `0,109`** · **2 000 → `0,112`** · **5 000 → `0,114`**; stress p90:
**0,137 / 0,150 / 0,183**. **Phí sàn = 0,098 %/vòng chiếm ~88 %.**

**(2) Dưới chi phí đó, Track B có NET DƯƠNG không?**
→ **CÓ.** `BOOK_EW` **+0,1059 %/ngày**, **CI95 raw `[+0,0615 %, +0,1502 %]`** (ngoài 0 **phía dương**),
`MDE80 = 0,0316 %` (**đủ power**). **Hoà vốn phí = `0,4137 %/vòng`** (khớp bước 1). So sánh:
net tại **`0,112 %` → `+0,106 %`** · tại **`0,173 %` → `+0,085 %`** · tại **`0,414 %` → `+0,000 %`** ·
tại **`0,757 %` → `−0,120 %`**. **Rào (a)/(b′) = FAIL/FAIL** (mọi object).

**(3) Kết luận dứt khoát: NULL hay MỞ LẠI?**
→ **MỞ LẠI (lên bước 2) — KHÔNG phải NULL vì chi phí.** Theo **đúng luật pre-reg §4.2**:
`C(2 000) = 0,112 % ≤ 0,414 %` ⇒ **phải chạy lại bước 1 với phí thật**; **kết luận NULL cũ bị BÁC** vì dựa
trên `0,757 %` — mà `0,757 %` = **`|slip|` vô hướng (0,33 %)** trong khi **slip có dấu ≈ 0** ⇒ **nhiễu**.
**Điều kiện kèm:** bước 2 **vẫn phải vượt Rào (a)/(b′) và đối chứng ngẫu nhiên** — hiện **đều FAIL** ⇒
**MỞ LẠI để nghiên cứu, KHÔNG deploy.**

**(4) Dữ liệu thiếu gì?**
→ **Không thiếu lần này** (tải được cả `bookTicker` lẫn `aggTrades`). **Cần nói rõ 3 hạn chế:**
**(i)** `bookTicker` chỉ **L1** ⇒ impact cho size **> qty L1** (≈23 % số trade) có thể **bị ĐÁNH GIÁ THẤP**;
**(ii)** `bookTicker` daily **chỉ tồn tại ~2023-05-16 … 2024-03-30** ⇒ **không** đo được 2025 trực tiếp
(cách thu khác: **ghép `bookTicker` tháng** hoặc **shadow-log top-of-book** của chính book);
**(iii)** mẫu **14 symbol × 4 ngày**. **Cách thu bổ sung:** log `orderId + commission + executedQty +
top-of-book lúc đặt` vào chính book (paper/shadow), **hoặc** A/B maker-first trên shadow để đo `p` thật.

---

## 6. MỤC NÀO BỎ + LÝ DO

| mục | quyết định | lý do (số đo) |
|---|---|---|
| **"Phí thật `0,757 %/vòng`" của `RESULT_BOOK_COST`** | **BỎ làm chi phí (giữ làm BIÊN TRÊN)** | dựa trên `|slip|` **vô hướng** (nhiễu); **slip có dấu ≈ 0**; chi phí có hướng **ĐO = 0,112 %** |
| **Roll(1m) `0,075 %/vòng`** | **BỎ** | **thiên lên ~4–7×** so với effective spread đo trực tiếp (`0,01–0,02 %`) |
| **4 ngày mẫu 2025 ở pre-reg** | **BỎ (đổi ngày)** | `bookTicker` daily **404** sau `2024-03-30`; theo luật pre-reg chọn lại ngày trong cửa sổ có dữ liệu |
| **`|slip|`/`|p−mid|` median làm cost** | **BỎ** | effective spread dùng **CÓ DẤU** (`sign` từ `is_buyer_maker`); median của `e` mới là chi phí |
| **Kết luận "Track B NULL vì CHI PHÍ"** | **BỎ** | `C ≤ hoà vốn`; net **+0,106 %/ngày**, CI **ngoài 0 phía dương** |
| **Maker-first** | **GIỮ BỎ** (như cũ) | `0/991` chân thật là maker; `p* = 0,92–0,99` |
| `bookTicker` + `aggTrades` (Vision, miễn phí) | **GIỮ làm nguồn chuẩn** | giải quyết đúng "THIẾU spread trích dẫn + impact" (`RESULT_BOOK_COST` §7.4) |
| **Rào (a)/(b′)** | **GIỮ** | vẫn **FAIL** ⇒ **chặn deploy** dù net dương |

---

## 7. SẢN PHẨM + TÁI LẬP

| File | Nội dung |
|---|---|
| `docs/prereg/PREREG_BOOK_COST2.md` | pre-reg, commit **`b8bcca9`** |
| `research/analysis/vision_micro.py` | đo spread + impact (Range-streaming, **~59 s**, **0 byte ghi đĩa**) |
| `research/trackb/cost2_trackb.py` | chấm lại Track B (**~8 s**, tái dùng `run_trackb.py`) |
| `docs/result/book_cost2.json` · `book_cost2_trackb.json` | mọi số + nguồn |
| `/tmp/trackb/panel.npz` (45,8 MB) | trung gian, **dọn sau commit** |

```bash
PYTHONPATH=/home/ubuntu/.local/lib/python3.10/site-packages python3 research/analysis/vision_micro.py
PYTHONPATH=/home/ubuntu/.local/lib/python3.10/site-packages python3 research/trackb/cost2_trackb.py
```

**Hạn chế (ghi trước, đúng pre-reg §6):** mẫu nhỏ (14 symbol × 4 ngày); `bookTicker` **L1-only**;
cửa sổ **00:00–00:30 UTC** (có thể **biến động cao hơn** trung bình); mọi kết luận là **mô tả quá khứ DEV**.
