# RESULT_BOOK_COST — phí THẬT/vòng cho book L/S (Track B): có ≤ 0,414 %/vòng không?

Ngày đo: **2026-09-28**. Pre-reg: `docs/prereg/PREREG_BOOK_COST.md` (**commit `0b482b4`**, chốt **TRƯỚC**
khi đo; sau đó **không sửa thiết kế**). Script: `research/analysis/book_cost_real.py`.
JSON: `docs/result/book_cost_real.json`. Trung gian `/tmp/book_cost/` (**dọn sau commit**).

**Tuân thủ:** thuần Python · **0 train / 0 sim** · **không chạy nặng** (đọc Aerospike local, ~16 s) ·
**không** chạm production/`242`/ONNX/LIVE · **không push file dữ liệu** · **DEV ≤ 2025-12-31** (không chạm 2026)
· không ghi gì vào Aerospike (read-only).

---

## 0. KẾT LUẬN (một dòng)

> **KHÔNG ≤ 0,414 %/vòng ở mốc trung tâm ĐO ĐƯỢC ⇒ Track B vẫn NULL — nhưng NULL vì CHI PHÍ, không phải vì
> tín hiệu.** Con số "phí thật ~0,05 %/chân ⇒ 0,1–0,2 %/vòng" trong đề bài **chỉ là PHÍ SÀN của sàn**, thiếu
> **spread + impact**: đo trên **991 chân khớp THẬT** cho **0,757 %/vòng (median) / 1,530 % (mean)**.
> Dải đo được: **0,17 %/vòng** (fee + spread ĐO) … **1,53 %/vòng** (stress) — **hoà vốn 0,414 % nằm TRONG dải**,
> và **impact tại 00:00 UTC cho size của book là số DUY NHẤT còn thiếu** để chốt.

---

## 1. NGUỒN + PHƯƠNG PHÁP (đúng pre-reg §1/§2)

| Thành phần | Nguồn | Loại |
|---|---|---|
| Phí sàn taker/maker | `/fapi/v1/commissionRate` live = `0,0500` / `0,0200` %/chân | ĐO (API) |
| **Phí THỰC đã trả** | 991 chân thật: `8,9061 / 18 135,48` = **0,0491 %/chân** | **ĐO (fill thật)** |
| **Mix maker/taker** | **991/991 chân TAKER**; **388/388 lệnh MARKET**; fill-rate 100 % | **ĐO (fill thật)** |
| **Slip THẬT** | 976 chân khớp nến 1m (§5) | **ĐO (fill thật)** |
| **Spread** | **KHÔNG có bid/ask trong DEV** ⇒ tự đo **proxy** trên `test.kline_1m_opt` (chỉ OHLC+totalUsdt), nến 1m quanh **00:00 UTC** (=07:00 GMT+7), ngày-15 mỗi tháng 2021-01…2025-12 | ĐO (proxy) |
| Hoà vốn maker `p*` | `RESULT_EXECUTION_MAKER.md` §5 = `0,92–0,99` | ĐO (counterfactual) |

Nguồn fill thật = `RESULT_LIVE_FILLS_AUDIT.md` (đo trên live `242` ngày 2026-09-23 — **audit CÓ SẴN trong repo**;
đây là tài liệu cũ, **không** phải lượt đo mới trên 2026).

**Top-200 (DEV)**: xếp hạng theo `Σ totalUsdt` tại **đúng nến 00:00 UTC** trên 60 ngày mẫu (≥12 ngày mẫu).
Kết quả: 610 symbol có mẫu, 354 đủ điều kiện, lấy **200** (BTC/ETH/SOL/XRP/DOGE/BNB/ADA/LINK/DOT/LTC…).
Mốc rebalance **00:00 UTC** (GMT+7 07:00) — đúng mốc của `build_panel.py`/`run_trackb.py`.

**Công thức (khai rõ):** `cost_rt = 2·fee_1chân + spread_rt + 2·impact` ≡ `2·fee_1chân + 2·|slip_1chân|`
(vì `|slip|` đã gồm nửa-spread + impact). Mỗi vòng = 2 chân.

---

## 2. PHÍ SÀN (đo được — đây là điểm "rẻ" nhất)

| | %/chân | %/vòng (×2) |
|---|---|---|
| taker (hợp đồng) | 0,0500 | 0,1000 |
| **taker THỰC đã trả** | **0,0491** | **0,0982** |
| maker (hợp đồng) | 0,0200 | 0,0400 |
| maker THỰC đã dùng | **0,0000** (0/991 chân) | — |

⇒ **Chỉ riêng phí sàn (0,098 %/vòng) ≤ 0,414 % ✅** — đây là gốc của giả định "~0,1–0,2 %/vòng" trong đề bài.
**Nhưng phí sàn KHÔNG phải tổng chi phí của một lệnh MARKET.**

---

## 3. MIX MAKER/TAKER THỰC TẾ (đo được)

| | Số chân | % |
|---|---|---|
| maker | **0** | **0,00 %** |
| taker | **991** | **100,00 %** |

- **388/388 lệnh là MARKET** ⇒ **fill-rate 100 %**, 0 lệnh treo ⇒ **không có rủi ro không khớp** trong live.
- ⇒ **Mix thực tế = 100 % TAKER** ⇒ kịch bản (iii) **=** (i). Nếu book chạy cùng executor, nó cũng **đi market**.
- Kịch bản maker **chỉ tồn tại trên giả định**: `RESULT_EXECUTION_MAKER.md` §5 ⇒ hoà vốn đòi khớp
  **`p* = 0,92–0,99`** (2 mốc slip thực tế), **≈1,00** nếu có adverse selection ⇒ **không khả thi**.

---

## 4. SPREAD tại 00:00 UTC (DEV, top-200) — **ĐO PROXY + NÓI RÕ THIẾU**

| Chỉ số (median) | top-200 (n=8 544 ô) | majors (n=296 ô) |
|---|---|---|
| biên độ 1 phút `(h−l)/c` | **0,2393 %** | 0,1429 % |
| Corwin–Schultz (khung 1h) | 0,3612 % | 0,1860 % |
| **Roll (1m)** — proxy spread tốt nhất | **0,0751 %** (63,4 % ô hợp lệ) | 0,0450 % (56,8 %) |

- **`(h−l)/c` và CS là BIẾN ĐỘNG, KHÔNG phải spread** ⇒ chỉ dùng làm **biên trên**, KHÔNG đưa vào cost.
- **Roll(1m) = 0,0751 %/vòng (≈7,5 bps effective spread)** cho top-200 ⇒ nửa-spread ~3,8 bps/chân.
  Đây là **ước lượng spread ĐẦU TIÊN bằng số cho top-200 tại 00:00 UTC** trong repo (trước đây repo ghi
  *"CHƯA CÓ"* — `PROPOSAL_MICROSTRUCTURE_DATA.md` §1). **Hạn chế:** Roll ở 1m bị **thiên lên**, 37 % ô
  `cov ≥ 0` (không ước được).
- **Vẫn THIẾU spread TRÍCH DẪN (bid/ask)**: `test.kline_1m_opt` chỉ có OHLC ⇒ **không** thể xác nhận số Roll.

**⇒ SAN CHI PHÍ = `2·fee + spread_Roll = 0,098 + 0,075 =` 0,173 %/vòng** (chưa cộng impact).

---

## 5. SLIP THẬT (đo trên 976 chân khớp nến 1m — `RESULT_LIVE_FILLS_AUDIT` §7)

| | mean | median |
|---|---|---|
| `\|slip\|` vs **close** phút | 0,71600 % | **0,32952 %** |
| `\|slip\|` vs **open** phút | 0,33202 % | 0,23308 % |
| slip **có dấu** vs close phút | **−0,01957 %** | +0,02150 % |

- **Điểm mấu chốt (phải nói rõ):** `|slip|` = **ĐỘ LỚN** (0,33 %) **không phải** chi phí có hướng — slip
  **có dấu** vs giá close **≈ 0** (mean −0,02 %). Nghĩa là **một phần lớn của "0,33 %" là nhiễu/biến động
  trong phút**, không phải chi phí khớp lệnh. **Chi phí có hướng nằm giữa 0 và 0,33 %/chân** tuỳ giá tham chiếu.
- Slip thật đo trên **chiến lược SẢN XUẤT KHÁC** (size median **11,27 USDT**, 54 alt, lệnh **momentum**, 2026)
  ⇒ **không chuyển thẳng** sang book (top-200, size ~700–5 000 USDT, rebalance **hẹn giờ**).

---

## 6. BẢNG CHI PHÍ 3 KỊCH BẢN (%/vòng; hoà vốn **0,414**)

| kịch bản | fee | spread | slip | **TỔNG** | ≤ 0,414 ? |
|---|---|---|---|---|---|
| (i) taker — **sàn đo được** (fee + spread Roll) | 0,098 | 0,075 | *(impact chưa đo)* | **0,173** | **✅** |
| (i) taker — **tổng trên CHÂN THẬT** (fee + 2·`\|slip\|`close, median) | 0,098 | gộp | 0,659 | **0,757** | ❌ |
| (i) biến thể giá tham chiếu = **open** phút (median) | 0,098 | gộp | 0,466 | **0,564** | ❌ |
| (i) stress **mean** (fee + 2·`\|slip\|`close, mean) | 0,098 | gộp | 1,432 | **1,530** | ❌ |
| (i) biên **lạc quan nhất** (slip **có dấu** mean) | 0,098 | gộp | −0,039 | **0,059** | ✅ |
| (i) chỉ phí sàn taker | 0,098 | — | — | **0,098** | ✅ |
| **(ii) maker hết** | **0,040** | 0 | adverse selection | **0,040** *(+ cần p\*=0,92–1,00)* | ⚠️ trên giấy, **bất khả** |
| **(iii) MIX THỰC TẾ = 100 % taker** | = (i) | | | **0,757** | ❌ |

**Trung tâm (pre-reg §3.1) = (iii) median = 0,757 %/vòng > 0,414 % ⇒ FAIL.**

---

## 7. TRẢ LỜI 4 CÂU (bắt buộc)

**(1) Phí thật/vòng = bao nhiêu? (3 kịch bản + nguồn)**
- **taker** (mix thực tế): **0,757 %/vòng** median / **1,530 %** mean — *tổng ĐO trên 991 chân khớp thật*
  (fee 0,098 + slip 0,66/1,43). Sàn chỉ-fee = 0,098 %; sàn fee+spread đo = 0,173 %.
- **maker**: **0,040 %/vòng** *trên giấy* — nhưng **0/991 chân thật là maker**, và hoà vốn cần **`p* = 0,92–0,99`**.
- **mix thực tế**: **100 % taker** ⇒ **0,757 %/vòng** (= taker).

**(2) Có ≤ 0,414 %/vòng không? ⇒ KHÔNG (ở mốc trung tâm đo được). ⇒ Track B KHÔNG được lật.**
Lý do: "0,1–0,2 %/vòng" là **phí sàn**, thiếu spread+impact. ⇒ **KHÔNG nên chạy lại bước 1** với con số đó.
**Đề xuất bước tiếp:** (a) nếu chỉ tin **sàn đo được** (0,173 %) thì chạy lại bước 1 ở **fee 0,17 %/vòng** là
**hợp lệ về kỹ thuật** — nhưng phải ghi rõ **impact = 0 là GIẢ ĐỊNH**; (b) **cách sạch hơn**: đo **impact thật
tại 00:00 UTC cho size của book** (mục (4)), rồi mới chạy lại.

**(3) Nếu không ⇒ Track B NULL vì CHI PHÍ. Đề xuất giảm:**
- **Giảm turnover**: `band ≥ 5` (giữ ≥ 5,2 ngày/leg ⇒ `TO/d ≤ 0,19`) — nhưng ngay `band=3` cũng chỉ
  `−0,091 %/ngày` ⇒ **giảm turnover một mình KHÔNG đủ** (từ `RESULT_TRACKB_STEP1` §4).
- **Maker-first**: **bác** — `p* = 0,92–0,99` và 0/991 chân thật là maker.
- **Universe thanh khoản hơn**: majors spread 0,045 %/vòng vs top-200 0,075 % ⇒ **chỉ tiết kiệm ~0,03 %/vòng**,
  không đủ để bắc cầu 0,757 → 0,414.
- ⇒ Không cách nào trong 3 cách trên đưa 0,757 xuống ≤ 0,414 mà **không cần dữ liệu mới**.

**(4) Nếu phải đo mà KHÔNG CÓ DỮ LIỆU ⇒ nói rõ THIẾU gì + cách thu:**
- **THIẾU (a) spread TRÍCH DẪN (bid/ask)** tại 00:00 UTC — DEV **chỉ có kline OHLC** (`PROPOSAL_MICROSTRUCTURE_DATA.md` §1);
  chỉ có **proxy** (Roll 0,075 %). **THIẾU (b) impact/fill THẬT của BOOK** (size 700–5 000 USDT trên top-200) —
  fill thật duy nhất có là của **chiến lược khác**. **THIẾU (c) fill-rate limit maker** (không có L2).
- **Cách thu:** (1) ghi `orderId` + `commission` + `executedQty` + **top-of-book lúc đặt** vào log của chính
  book (paper/shadow) ⇒ có spread + impact THẬT của book; (2) **Binance Vision MIỄN PHÍ** có `aggTrades`
  (có cờ `is_buyer_maker`) + `bookTicker` theo ngày ⇒ dựng lại spread/impact lịch sử **≤ 2025** mà **không mua
  data**; (3) A/B maker-first trên shadow để đo `p` thật.

---

## 8. MỤC NÀO BỎ + LÝ DO

| mục | quyết định | lý do (số đo) |
|---|---|---|
| Giả định **"phí thật 0,1–0,2 %/vòng"** | **BỎ** | đó là **chỉ phí sàn**; tổng trên chân thật = **0,757 %/vòng** |
| **Corwin–Schultz (0,36 %)** làm spread | **BỎ** làm cost | ở 1h nó đo **biến động**, không đo spread ⇒ chỉ để làm biên trên |
| `(h−l)/c` 1 phút (0,24 %) làm spread | **BỎ** làm cost | là **biến động**; giữ làm biên trên |
| **Maker-first** làm ứng viên deploy | **BỎ** | 0/991 chân thật là maker; `p* = 0,92–0,99` ⇒ bất khả thi |
| **Roll(1m) 0,075 %** làm proxy spread | **GIỮ** | ước lượng spread **đầu tiên** cho top-200 @00:00 UTC; biết rõ hạn chế |
| Cờ **"THIẾU impact"** | **GIỮ** | đây là số **duy nhất** còn thiếu để chốt dứt điểm |

---

## 9. SẢN PHẨM + TÁI LẬP

| File | Nội dung |
|---|---|
| `docs/prereg/PREREG_BOOK_COST.md` | pre-reg, commit **`0b482b4`** |
| `research/analysis/book_cost_real.py` | đo (Aerospike read-only + stack chi phí), chạy **~16 s** |
| `docs/result/RESULT_BOOK_COST.md` | file này |
| `docs/result/book_cost_real.json` | mọi số + nguồn |
| `/tmp/book_cost/` | trung gian **đã dọn** sau commit |

```bash
PYTHONPATH=/home/ubuntu/.local/lib/python3.10/site-packages \
  python3 research/analysis/book_cost_real.py     # -> /tmp/book_cost/book_cost_real.json
```

**Hạn chế (ghi trước, đúng pre-reg §4):** top-200 theo **mẫu ngày-15** (selection theo mẫu); slip thật từ
**chiến lược sản xuất khác** (size nhỏ, 2026); Roll(1m) **thiên lên**; mọi kết luận là **mô tả quá khứ DEV**.
