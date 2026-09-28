# PREREG_COST_TRUTH — CHI PHÍ THẬT: giá khớp của SIM + slip CÓ DẤU theo LOẠI LEG ⇒ chốt 3 mức base/stress/legacy

Ngày chốt: **2026-09-28**, viết **TRƯỚC** khi đo bất kỳ số nào của vòng này. Sau khi thấy số **KHÔNG sửa thiết kế**
(mọi thay đổi ⇒ AMENDMENT có lý do, ghi ở cuối file).

Ràng buộc (cứng): **offline Python · 0 sim / 0 train** · giữ box Oracle **NHẸ** (shadow đang chạy) ·
**KHÔNG chạm production / `242` / ONNX / LIVE** · **KHÔNG push file dữ liệu** (chỉ code/doc) ·
**DEV ≤ 2025-12-31** (không chạm 2026) · `df -h /` 93 % ⇒ file nhỏ, dọn temp · **output tool nhỏ** ·
commit sớm + `git push` được phép.

Nguồn bối cảnh (đọc trước, KHÔNG tính lại): `Claude outputs/PLAN_OPENCLAW_ADDENDUM_20260928.md` (§A + §D1) ·
`docs/result/RESULT_BOOK_COST.md` · `RESULT_BOOK_COST2.md` · `RESULT_LIVE_FILLS_AUDIT.md`.

## 0. CÂU HỎI QUYẾT ĐỊNH (3 việc)

- **(i)** **SIM giả định giá vào/ra ở ĐÂU** (close phút · open nền sau · giá tick)? Nếu sim vào ở **close phút**
  thì chi phí sim ĐÚNG = `fee + spread(±impact)`, **KHÔNG** phải slip ⇒ nói rõ.
- **(ii)** **Slip CÓ DẤU tách theo LOẠI LEG** trên **991 chân THẬT**: vào `PREDICT` · vào `BIG_DOWN` (lúc sập) ·
  `DCA` · thoát `STOP_MARKET` (trailing) · `STOP_LOSS`. Với từng loại: **mean/median + CI block-72h + n**.
  Nếu leg **lúc sập** có slip có dấu **DƯƠNG đáng kể** ⇒ **đó mới là chi phí cần dùng**, báo số riêng.
- **(iii)** Chốt **3 mức**: `base` (đo được) · `stress` (p90) · `legacy = 0,8 %/vòng` (chỉ đối chiếu). Báo **chi phí
  /vòng** ở cả 3 mức để D2 áp lại. Nếu khác `0,11 %/vòng` của `RESULT_BOOK_COST2` ⇒ giải thích.

**Tiên nghiệm (đã biết từ tiền đề, ghi để không tự lừa):** 991 chân thật, fee `0,0491 %/chân` (taker 100 %);
slip có dấu vs close phút ≈ `−0,02 %` (≈0); `|slip|` vô hướng `0,33 %`/chân = **NHIỄU**;
chi phí có hướng đo (bookTicker+aggTrades) `0,112 %/vòng`; sim trừ **phẳng `0,8 %/vòng`**.

## 1. NGUỒN DỮ LIỆU (chốt trước · chỉ số ĐO ĐƯỢC, không sinh mới)

| Thành phần | Nguồn | Loại |
|---|---|---|
| 991 chân khớp THẬT (đã dedupe theo `id`) | `research/live_fills_audit/data/trades.csv` (từ `raw2/` — `RESULT_LIVE_FILLS_AUDIT`, **tái dùng, không fetch lại**) | ĐO |
| Vai trò lệnh (mở/đóng) | `research/live_fills_audit/data/orders.csv` (từ `raw4/`) | ĐO |
| Nến 1m tại đúng phút khớp (976/991 chân) | `research/live_fills_audit/data/slips.json` (từ `raw3/kline_*`) | ĐO |
| Phí/chân | `0,0491 %/chân` = `8,9061 / 18 135,48` (991 chân) — `RESULT_LIVE_FILLS_AUDIT` §3/§5 | ĐO |
| Spread + impact (L1 + effective spread) | `RESULT_BOOK_COST2` §2/§3: `2·h(2000)` median `0,0134 %/vòng`, p90 `0,0518 %/vòng` (`C p90 0,1500 − fee 0,0982`) | ĐO |
| Hằng số chi phí sim | `tradecore/Configs.java:103,117,125` (`RATE_FEE` 0,002 · `SLIPPAGE_RATE` 0,003 · `APPLY_SLIPPAGE` true) + `research/OrderTargetInfoTest.java:286-288` (`slip = qty·priceEntry·SLIPPAGE_RATE·2`) | ĐO (code) |

**KHÔNG** dùng tính năng mạng; **KHÔNG** chạm 242 (xem §8 hạn chế). Tất cả đầu vào là file đã có trong repo.

## 2. VIỆC 1 — SIM VÀO Ở GIÁ NÀO? (chốt tiêu chí đọc code, TRƯỚC khi kết luận)

Đọc các điểm chốt (file:line) và trả lời theo **đúng** các dòng code:

- **GIÁ VÀO (entry)**: `research/SimulatorMarketLevelTicker1MStopLoss.java:1372` — `Float entry = ticker.priceClose;`
  (`ticker` = nến **1 phút** tại tick quyết định). Ứng viên bị loại: `priceOpen` nền sau, giá `tick`
  (sim **không** có đường tick cho entry), `hlc3`.
- **GIÁ RA (exit)**: `credit` = `order.lastPrice` với `lastPrice = ticker.priceClose`
  (`research/OrderTargetInfoTest.java:134`), gán `order.priceTP = order.lastPrice` tại
  `Simulator…:551,892`; các nhánh SL/stop trong nến thì `priceTP = min(ticker.priceOpen, ticker.priceClose)`
  (`:1025,1042`) và `PreArmSlUtils.exitPriceVal` (`:1000`). ⇒ **KHÔNG bao giờ dùng high/low hay giá tick**.
- **LUẬT (i)**: nếu entry = **close nến 1 phút** ⇒ chi phí sim ĐÚNG = `2·fee + 2·h` (**fee + spread±impact**),
  **KHÔNG** phải slip. Ghi rõ `SLIPPAGE_RATE` phẳng `0,60 %/vòng` là khoản **cộng thêm trên giá đã ở close**
  ⇒ mâu thuẫn nội tại (double-count) **trừ khi** mục đích là phạt look-ahead (xem (ii)).

## 3. VIỆC 2 — PHÂN LOẠI LEG (chốt trước · tất định · chỉ dùng dữ liệu đã có)

**Đơn vị phân loại = LỆNH (`orderId`)**; mỗi chân (fill) thừa hưởng loại của lệnh.

**Bước A — vai trò lệnh** (`orders.csv`): `reduceOnly=True` hoặc `closePosition=True` ⇒ **CLOSE**;
`reduceOnly=False` & `closePosition=False` ⇒ **OPEN**; **không có** trong `orders.csv` ⇒ **UNKNOWN**
(đưa ra bảng riêng; **KHÔNG** gán loại).

**Bước B — trạng thái vị thế** theo `symbol`, xếp theo thời gian, dùng **qty CÓ DẤU toàn bộ chân**
(`BUY=+qty`, `SELL=−qty`, mọi lệnh kể cả UNKNOWN để dò vị thế):
- **OPEN** & tại thời điểm xét **vị thế đang mở** (cùng dấu với chiều lệnh) ⇒ **`DCA`**;
- **OPEN** & vị thế **≈ 0** (|pos| < 1e-9) ⇒ **`ENTRY`** (vị thế mới);
- **CLOSE** ⇒ **`EXIT`**, tách bằng **tổng `realizedPnl` của lệnh** (`orders.csv` không có; dùng tổng
  `realizedPnl` các chân cùng `orderId`): `Σpnl ≥ 0` ⇒ **`STOP_MARKET` (trailing/arm, thoát có lãi)**;
  `Σpnl < 0` ⇒ **`STOP_LOSS` (SL cứng/time-stop lỗ)**.

**Bước C — tách `ENTRY` thành `PREDICT` vs `BIG_DOWN`** bằng **PROXY giá** (khai rõ, vì KHÔNG có log intent — §8):
`r_leg = (c − o)/o` của **nến 1m tại đúng phút khớp** (từ `slips.json`).
- `r_leg ≤ −1,0 %` ⇒ **`ENTRY_BIG_DOWN`** (proxy "vào lúc sập").
- `r_leg > −1,0 %` ⇒ **`ENTRY_PREDICT`**.
- **Độ nhạy** (báo kèm, KHÔNG dùng làm chính): ngưỡng live `−3,157 %` (`MS_DOWN_BIG_AVG`) và `r_leg < 0` (mọi nền đỏ).
- Chân `ENTRY` **không khớp được nến** ⇒ loại khỏi bảng chia (báo n).

**Dấu slip (chốt):** `s_close = (fill−c)/c` (BUY) · `(c−fill)/c` (SELL) ⇒ **dương = BẤT LỢI = chi phí**
(khớp `RESULT_LIVE_FILLS_AUDIT` §7). Dùng `s_close` (so close phút) làm thước đo chính; `s_open` chỉ tham chiếu.

## 4. THỐNG KÊ (chốt trước)

- **Block-72h bootstrap**: `blk = floor((t − t0)/72h)`, `t0 = 2026-06-24 13:31 UTC` (đầu cửa sổ); resample **block**
  có hoàn lại; **2000 rep**; **seed `20260905`** (`c3_rates.SEED`).
- **CI** = phân vị `[2,5 %, 97,5 %]`, rộng ra quanh điểm theo **`inflate(k)`** = `sqrt(2 ln k)` (`c3_rates.inflate`).
  **`k = 5`** (5 loại leg được soi trong cùng round) ⇒ **`inflate(5) = 1,7941`** (mức CHÍNH);
  báo thêm **`inflate(1) = 1,0`** (CI gốc) để minh bạch.
- Báo **n · mean · median** cho từng loại leg; **KHÔNG** dùng `|slip|` vô hướng làm chi phí (§5).

## 5. VIỆC 3 — CHỐT 3 MỨC CHI PHÍ /VÒNG (chốt TRƯỚC khi tính)

```
base   = 2·fee + 2·h(median, S=2000)     fee = 0,0491 %/chân (ĐO) ;  2·h = 0,0134 %/vòng (ĐO, BOOK_COST2)
       ⇒ kỳ vọng ≈ 0,1116 %/vòng  ("đo được, có dấu")
stress = 2·fee + 2·h(p90, S=2000)        = C(2000) p90 = 0,1500 %/vòng (ĐO, BOOK_COST2)   [báo kèm p90 @5000 = 0,1833]
legacy = RATE_FEE×1 + SLIPPAGE_RATE×2    = 0,20 % + 0,60 % = 0,800 %/vòng (sim đang trừ, FLAT)
```
- **Chi phí DÙNG cho sim** = **`base`** (mức đo được), **`stress`** để kiểm bền; **BỎ `legacy 0,8 %`** làm chi phí.
- Nếu số vòng này **khác `0,112 %`** của `RESULT_BOOK_COST2` ⇒ **giải thích nguyên nhân** (nguồn/cửa sổ/size).
- Nếu `ENTRY_BIG_DOWN` có slip dương đáng kể ⇒ báo **số riêng** + **chi phí bổ sung /vòng** (tỷ lệ chân sập × slip),
  KHÔNG trộn vào `base` (vì `base` là chi phí ĐO của một vòng "bình thường").

## 6. LUẬT KẾT LUẬN (chốt trước · KHÔNG đổi sau khi thấy số)

1. **(i)** Trả lời dứt khoát sim vào ở `priceClose` nến 1 phút (nếu code đúng §2) ⇒ **chi phí sim đúng = fee + spread,
   KHÔNG phải slip**; `SLIPPAGE_RATE` 0,6 %/vòng là cộng thêm ⇒ **bỏ** (hoặc giữ như biên trên look-ahead).
2. **(ii)** Với **mỗi** loại leg: nêu `mean/median/CI(inflate 5)`. **"Slip dương đáng kể"** ⇔ **mean > 0 VÀ CI
   (inflate 5) không chứa 0**. Nếu **có** loại (đặc biệt `ENTRY_BIG_DOWN`) ⇒ **đó là chi phí hướng cần dùng**, báo riêng.
   Nếu **không loại nào** ⇒ ghi rõ: **không có slip hướng nào ngoài fee+spread** ⇒ `base` đứng vững.
3. **(iii)** Chốt số 3 mức (%/vòng) + **mục nào BỎ** (kèm lý do). `base` là số DÙNG cho sim.
4. **Chống dredging:** một phân loại duy nhất, một ngưỡng proxy duy nhất (`−1,0 %`) đã khai; các biến thể chỉ là
   **độ nhạy**, không chọn hậu nghiệm. Không mở thêm biến thể sau khi thấy số.

## 7. SẢN PHẨM

`docs/prereg/PREREG_COST_TRUTH.md` (file này) + `docs/result/RESULT_COST_TRUTH.md` + `docs/result/cost_truth.json`
+ script `research/analysis/cost_truth.py`. Commit + push (code/doc; **không** file dữ liệu).

## 8. HẠN CHẾ (khai trước)

1. **KHÔNG có log intent (level) của 242** ⇒ `BIG_DOWN` là **PROXY theo nền giá**, `DCA`/`STOP_*` là **suy luận**
   từ vị thế + dấu PnL. Loại leg **chính xác** cần đọc file `storage/data/order/<YYYYMMDD>/<SYM>-<ts>` trên 242
   (Java-serialized `OrderTargetInfo` có trường `level`) — **ngoài phạm vi** vì ràng buộc "KHÔNG chạm 242".
2. Cửa sổ 88 ngày (2026-06-24 → 09-20); **~35 ngày đầu live đã bị Binance xoá**; vị thế mở trước cửa sổ bị cắt.
3. **136 chân UNKNOWN** (lệnh ngoài cửa sổ `allOrders` 90 ngày) — báo riêng, không gán loại.
4. `STOP_LOSS` có thể **rất ít mẫu** (sim chỉ ~1 leg SL) ⇒ nếu n nhỏ thì **chỉ mô tả**, không kết luận.
5. Proxy `−1,0 %` dùng **nền của chính coin**, không phải breadth toàn thị trường (`BIG_DOWN` live là sự kiện
   market-wide) ⇒ có thể **bỏ sót** `BIG_DOWN` và/hoặc **lẫn** dump riêng lẻ.
