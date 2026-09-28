# PREREG_BOOK_COST — đo PHÍ THẬT/vòng cho book L/S (Track B) và luật kết luận

Ngày chốt: **2026-09-28**, viết **TRƯỚC** khi đo bất kỳ số nào. Sau khi đo **không sửa thiết kế**.

Ràng buộc: **offline**, **0 train / 0 sim**, **không chạy nặng trên Oracle** (shadow đang chạy), **không chạm
production/242/ONNX/LIVE**, **không push file dữ liệu**, **DEV ≤ 2025-12-31** (không chạm 2026), file **nhỏ**,
output tool **nhỏ**. `git push` **được phép**.

## 0. Câu hỏi quyết định

`docs/result/RESULT_TRACKB_STEP1.md` (commit `29b1f6e`) kết luận **NULL** cho book L/S ở **phí `0,76 %/vòng`**
(`net −0,121 %/ngày`; **phí hoà vốn `0,414 %/vòng`**; ở `0,30 %/vòng` thì net **+0,040 %/ngày**).
⇒ **Toàn bộ kết luận Track B phụ thuộc MỘT con số: phí THẬT mỗi vòng.**
Câu hỏi: **phí thật/vòng có ≤ `0,414 %` không?**

## 1. NGUỒN DỮ LIỆU (chốt trước · chỉ số ĐO ĐƯỢC, không giả định)

| Thành phần | Nguồn (đã có trong repo) | Loại |
|---|---|---|
| **Phí sàn taker/maker** | hợp đồng đo được qua `/fapi/v1/commissionRate` trên live 242: `taker 0,000500`, `maker 0,000200` — `RESULT_LIVE_FILLS_AUDIT.md` §5 | **ĐO** (API) |
| **Phí THỰC đã trả** | 991 chân thật (`/fapi/v1/userTrades`): `commission 8,9061 / notional 18 135,48` = **0,0491 %/chân** — `RESULT_LIVE_FILLS_AUDIT.md` §3+§5 | **ĐO** (fill thật) |
| **Mix maker/taker THỰC** | 991/991 chân **taker**; 388/388 lệnh **MARKET**, 0 LIMIT ⇒ fill-rate 100 % — `RESULT_LIVE_FILLS_AUDIT.md` §4+§6 | **ĐO** (fill thật) |
| **Slip THỰC** | 976 chân khớp nến 1m: `\|slip\|` vs **close** phút median **0,32952 %** / mean **0,71600 %**; vs **open** phút median **0,23308 %** / mean **0,33202 %**; slip **có dấu** vs close mean **−0,01957 %**, median **+0,02150 %** — `RESULT_LIVE_FILLS_AUDIT.md` §7 | **ĐO** (fill thật) |
| **Spread trích dẫn (bid/ask)** | **KHÔNG CÓ** — DEV không lưu L2/top-of-book (`PROPOSAL_MICROSTRUCTURE_DATA.md` §1: *"CHƯA CÓ — không có bid/ask lịch sử"*; `test.kline_1m_opt` chỉ có OHLC+totalUsdt) | **THIẾU** |
| **Spread PROXY (DEV)** | tự đo: Aerospike local `test.kline_1m_opt` (Snappy protobuf, đã dùng ở `build_panel.py`): nến 1m quanh **00:00 UTC** (=07:00 GMT+7), 15/mỗi tháng 2021-01…2025-12 | **ĐO** (proxy) |
| **Hoà vốn maker `p*`** | `RESULT_EXECUTION_MAKER.md` §5: `p*_B = 0,92–0,99` (2 mốc slip thực tế), `≈1,00` nếu adverse selection | **ĐO** (counterfactual) |
| Hằng số sim | `Configs.java:103` `RATE_FEE=0,002`, `:117` `SLIPPAGE_RATE=0,003` (×2 chân) ⇒ 0,80 %/RT — `RESULT_COST_LIQUIDITY.md` §4.1 | đọc CODE |

**Top-200 (DEV)**: xếp hạng theo `Σ totalUsdt` tại **đúng nến 00:00 UTC** trên **60 ngày mẫu** (ngày 15 mỗi
tháng, 2021-01…2025-12); yêu cầu **≥ 12 ngày mẫu**; lấy **200 symbol** thanh khoản nhất. (Khác `build_panel.py`
— ở đó top-200 theo `dv_med` cả ngày; ở đây theo **thanh khoản TẠI mốc rebalance**, đúng câu hỏi hơn.)

## 2. CÔNG THỨC (khai rõ)

```
cost_rt = 2·fee_1chan + spread_rt + 2·impact_1chan        (mỗi vòng = 2 chân; spread_rt = 2·(nửa spread))
```
Vì `2·|slip_1chan|` **đã bao gồm** `nửa spread + impact`, ta trình bày 2 dạng **tương đương**:
- dạng **fill thật**: `cost_rt = 2·fee_1chan + 2·|slip_1chan|`
- dạng **phân rã**: `cost_rt = 2·fee_1chan + spread_rt + 2·impact`

**3 kịch bản** (chốt trước):
- **(i) TAKER HẾT** — `fee = 0,0491 %/chân` (thực) ; `slip` = số ĐO (§1). Vòng = 2 chân khớp.
- **(ii) MAKER HẾT** — `fee = 0,0200 %/chân` (hợp đồng) ; né nửa spread (kỳ vọng) ; **cộng adverse selection**
  theo `p*` (`RESULT_EXECUTION_MAKER.md`: hoà vốn đòi khớp `p ≥ 0,92–0,99`).
- **(iii) MIX THỰC TẾ** — mix ĐO ĐƯỢC = **100 % taker** ⇒ **= (i)**. (Không bịa tỉ lệ khác.)

**Mốc báo cáo**: median (central) + mean (stress). Báo **cả** slip-vs-close (**|.|**, mốc của audit) **và**
slip-vs-open, **và** slip có dấu, để lộ rõ độ phụ thuộc giá tham chiếu.

## 3. LUẬT KẾT LUẬN (chốt trước)

1. **`cost_rt(trung tâm)` = kịch bản (iii) mix thực tế, mốc `median`, dùng `|slip|` vs close** (mốc audit).
2. Nếu **`cost_rt ≤ 0,414 %`** ⇒ **Track B KHÔNG NULL vì chi phí** ⇒ phải **chạy lại bước 1** với phí thật
   (đề xuất bước tiếp cụ thể).
3. Nếu **`cost_rt > 0,414 %`** ⇒ **Track B NULL vì CHI PHÍ** (không phải vì tín hiệu) ⇒ đề xuất cách **giảm
   chi phí** (maker-first / giảm turnover / universe thanh khoản hơn).
4. **Báo cáo luôn cả 2 đầu**: (a) **sàn phí** (anchor chỉ-fee = 0,098 %/vòng) và (b) **trần proxy spread**
   (upper bound) — để thấy dải, không trình 1 số duy nhất.
5. **Nếu spread trích dẫn / slip không đo được** ⇒ ghi **THIẾU** + **đề xuất cách thu** (ghi top-of-book tại
   00:00 UTC / mua-quét Binance Vision `bookTicker` / Roll từ aggTrades free) — **không** suy diễn thành số.

## 4. GHI TRƯỚC HẠN CHẾ

- Slip thật đo trên **chiến lược SẢN XUẤT khác** (T170/T170-legacy, lệnh **momentum** trên 54 alt, size
  ~11–18 USDT, **2026-06→09**) — **KHÔNG** phải book L/S (top-200, rebalance **hẹn giờ 00:00 UTC**, size lớn
  hơn). ⇒ số có thể **không chuyển thẳng**; phải nói rõ khi trích.
- Spread proxy từ OHLC là **biến động**, **KHÔNG** phải spread trích dẫn ⇒ chỉ dùng làm **biên**, không làm cost.
- "Top-200" theo mẫu ngày-15 ⇒ **selection theo mẫu**, không phải universe cả ngày.
- Mọi kết luận là **mô tả quá khứ DEV**, không phải forward.

## 5. SẢN PHẨM

`docs/prereg/PREREG_BOOK_COST.md` (file này) + `docs/result/RESULT_BOOK_COST.md` + `docs/result/book_cost_real.json`
+ `research/analysis/book_cost_real.py`. Commit + **push**.
