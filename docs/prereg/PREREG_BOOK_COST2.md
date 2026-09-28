# PREREG_BOOK_COST2 — spread TRÍCH DẪN + impact (Binance Vision, MIỄN PHÍ) ⇒ chấm lại Track B

Ngày chốt: **2026-09-28**, viết **TRƯỚC** khi đo bất kỳ số nào. Sau khi thấy số **không sửa thiết kế**.

Ràng buộc (cứng): **offline Python** · **0 train / 0 sim** · **không chạm production/`242`/ONNX/LIVE** ·
**không push file dữ liệu** (chỉ code/doc) · **DEV ≤ 2025-12-31** (không chạm 2026) · **output tool nhỏ** ·
tải dữ liệu **có chặn dung lượng, dọn ngay** (`df -h /` ≈ 93 %) · `git push` **được phép**.

## 0. Câu hỏi quyết định

`docs/result/RESULT_BOOK_COST.md` (**`90f36bc`**) đo **phí THẬT/vòng = 0,757 %/vòng (median)** trên 991 chân
khớp thật ⇒ tuyên Track B **NULL vì CHI PHÍ**. **NHƯNG** chính file đó ghi rõ một **mâu thuẫn chưa gỡ**:

- `|slip|` vs close phút: **median 0,3295 %/chân** (lớn);
- slip **CÓ DẤU** vs close: **mean −0,0196 %** (≈ 0).

⇒ Phần lớn "0,33 %" là **nhiễu biến động trong phút**, **KHÔNG phải chi phí có hướng**. Nếu tính **chi phí CÓ
HƯỚNG** = `fee + nửa-spread + impact` thì có thể chỉ **~0,12–0,25 %/vòng**, **dưới hoà vốn `0,414 %/vòng`**
của `RESULT_TRACKB_STEP1` ⇒ **có thể LẬT kết luận NULL**.

Số **DUY NHẤT** còn thiếu để chốt (đúng `RESULT_BOOK_COST` §7.4): **spread TRÍCH DẪN (bid/ask) + impact tại
00:00 UTC**. Lần này lấy bằng **Binance Vision MIỄN PHÍ**.

## 1. NGUỒN DỮ LIỆU (chốt trước · chỉ số ĐO ĐƯỢC)

| Thành phần | Nguồn | Loại |
|---|---|---|
| **Spread TRÍCH DẪN (bid/ask)** | `https://data.binance.vision/data/futures/um/daily/bookTicker/<SYM>/<SYM>-bookTicker-YYYY-MM-DD.zip` — cột `update_id,best_bid_price,best_bid_qty,best_ask_price,best_ask_qty,transaction_time,event_time` | **ĐO** (L1 thật) |
| **Trade + bên taker** | `.../daily/aggTrades/<SYM>/<SYM>-aggTrades-YYYY-MM-DD.zip` — cột `agg_trade_id,price,quantity,first_trade_id,last_trade_id,transact_time,is_buyer_maker` | **ĐO** (trade thật) |
| **Phí mỗi chân** | `0,0491 %/chân` = `8,9061 / 18 135,48` (991 chân thật) — `RESULT_LIVE_FILLS_AUDIT.md` §3/§5 | **ĐO** |
| Hạng thanh khoản | `dv_med` (USD-volume/ngày, panel `build_panel.py`) — đúng cách `RESULT_TRACKB_STEP1` | ĐO (panel) |

**Tải BOUNDED (không lưu file lớn)**: gọi HTTP **Range** lấy **tối đa ~6 MB nén/file**, giải nén **raw-inflate
streaming** (`zlib`, `wbits=-15`) và **dừng đọc ngay khi timestamp vượt cửa sổ**. Không ghi zip/csv ra đĩa
(BTC `bookTicker` 1 ngày = 1,13 GB giải nén / 128 MB nén ⇒ **bắt buộc** chặn). Không dùng API cần key.

## 2. UNIVERSE · NHÓM · MẪU · CỬA SỔ (chốt trước)

- **Universe**: **top-200** theo **`dv_med`** (đúng `RESULT_TRACKB_STEP1`; cần `≥ 12` mẫu ngày-15, 2021-01…2025-12).
- **Nhóm thanh khoản** (theo **hạng `dv_med`**): **G1 = hạng 1–20**, **G2 = 21–100**, **G3 = 101–200**.
- **Mẫu symbol** (18 symbol): trong **mỗi** nhóm, sắp **giảm dần theo `dv_med`**, lấy **chỉ số 0-based
  {1, 4, 7, 10, 13, 16}** ⇒ **6 symbol/nhóm**. (Quy tắc tất định, chốt TRƯỚC.)
- **Ngày mẫu** (DEV, ≤ 2025-12-31): **2025-02-12 · 2025-05-14 · 2025-08-13 · 2025-11-12**.
- **Cửa sổ đo**: **`[00:00:00, 00:30:00)` UTC** mỗi ngày — quanh **mốc rebalance 00:00 UTC**.
- **File 404** hoặc symbol chưa niêm yết ⇒ **bỏ ngày đó**, ghi lại số bỏ (không nội suy).

## 3. CÔNG THỨC CHI PHÍ CÓ HƯỚNG (khai rõ)

```
qs_i            = (ask_i − bid_i)/mid_i × 100                  (%/vòng, mid=(bid+ask)/2)   [quoted spread]
e             = sign × (p_trade − mid(t))/mid(t) × 100        (%/chân)   sign = +1 nếu taker BUY
                                                                          (is_buyer_maker = false)
                                                                          sign = −1 nếu taker SELL
h_g(S)        = quantile_k( { e : notional ∈ [S/√2, S·√2) } ) trong nhóm g     (k = 0,5 hoặc 0,9)
imp_g(S)      = h_g(S) − qs_g/2                              (impact VƯỢT nửa-spread trích dẫn)

Chi phí CÓ HƯỚNG /vòng (size S, nhóm g):
C_g(S) = 2·fee + 2·h_g(S) = 2·fee + qs_g + 2·imp_g(S)        fee = 0,0491 %/chân; mỗi vòng = 2 chân

Chi phí tổng hợp (book equal-weight ⇒ trọng số theo SỐ TÊN):
C(S) = Σ_g w_g · C_g(S),   w = (20, 80, 100)/200 = (0,10 · 0,40 · 0,50)
```

- **`k`** = hệ số phân vị của `h`: **`k = 0,5` (median — mốc TRUNG TÂM)** và **`k = 0,9` (p90 — STRESS)**.
- **Size đo được**: **`S ∈ {700, 2 000, 5 000}` USDT** (size một chân của book).
- **KHÔNG** dùng `|slip|` vô hướng (0,33 %) làm chi phí — đó là **nhiễu** (slip có dấu ≈ 0, `RESULT_BOOK_COST` §5).
- **`qs` và `h` là số ĐO**; `imp` là **số dẫn xuất** từ hai số đo.

## 4. LUẬT KẾT LUẬN (chốt trước)

1. **Mốc trung tâm**: **`C(2 000 USDT)`, `k = 0,5`** (median), trọng số nhóm `(0,10 · 0,40 · 0,50)`.
2. Nếu **`C(2 000) ≤ 0,414 %/vòng`** ⇒ Track B **KHÔNG NULL vì chi phí** ⇒ **MỞ LẠI** (được lên bước 2) và
   **phải chạy lại bước 1** với phí đó (không được giữ kết luận NULL cũ).
3. Nếu **`C(2 000) > 0,414 %/vòng`** ⇒ Track B **NULL vì CHI PHÍ** (giữ nguyên).
4. **Luôn báo cả 3 size** (`700/2 000/5 000`) **và cả `k = 0,9`** (stress) ⇒ thấy **dải**, không trình 1 số.
5. Nếu **tải không được** `bookTicker`/`aggTrades` ⇒ ghi rõ **THIẾU gì** + **cách thu khác**, **không** suy diễn.

## 5. CHẤM LẠI TRACK B Ở CHI PHÍ ĐÚNG (VIỆC 2)

- **Book**: `BOOK_EW` (4 tín hiệu, equal-weight) + 4 book con, `band = 2`, **đúng harness**
  `research/trackb/run_trackb.py` (`RESULT_TRACKB_STEP1`).
- **Turnover theo nhóm**: `TO_g[t] = ½·Σ_{i ∈ g} |W[t,i] − W[t−1,i]|`.
- **net mới**: `net_new[t] = gross[t] + fund[t] − Σ_g TO_g[t]·C_g(S)`.
- **Báo**: `net/ngày`, **CI block bootstrap** (khối 10 ngày, 2 000 rep, seed `20260905`, inflate `k=8`),
  **MDE80**, **Rào (a) `share top-1 %` / (b′) `TF(25 %)`**, `q*`.
- **So sánh**: net tại **`C = 0,173 %`** (sàn fee+spread cũ) vs **`0,414 %`** (hoà vốn) vs **`0,757 %`** (kết
  luận cũ) — cùng một book.
- **Đối chứng ngẫu nhiên**: giữ nguyên thiết kế cũ; ghi lại `chênh GROSS ≈ +0,076 %/ngày`
  (kết luận cũ: lợi thế gần như toàn bộ đến từ **turnover thấp**, KHÔNG phải tín hiệu).

## 6. GHI TRƯỚC HẠN CHẾ

- Mẫu **18 symbol × 4 ngày** (`2025`) — **không** phải toàn universe/toàn kỳ ⇒ mọi số là **mô tả MẪU**.
- `bookTicker` chỉ **L1** ⇒ impact đo qua **effective spread của trade THẬT** (không phải walk-the-book);
  nếu size > qty L1, impact **có thể bị ĐÁNH GIÁ THẤP** ⇒ báo thêm **tỉ lệ trade có notional > qty L1**.
- Cửa sổ **00:00–00:30 UTC** có thể **biến động cao hơn** trung bình (mốc rebalance funding) ⇒ `qs` có thể
  **cao hơn** mức thường ⇒ nghiêng về **thận trọng** (chi phí cao hơn), ghi rõ khi trích.
- Roll(1m)/CS/(h−l) **không** dùng làm cost ở đây (đã bàn ở `RESULT_BOOK_COST`).
- Mọi kết luận là **mô tả quá khứ DEV**, không phải forward.

## 7. SẢN PHẨM

`docs/prereg/PREREG_BOOK_COST2.md` (file này) + `docs/result/RESULT_BOOK_COST2.md` +
`docs/result/book_cost2.json` + `research/analysis/vision_micro.py` (đo) + `research/trackb/cost2_trackb.py`
(chấm lại Track B). Commit + **push**.
