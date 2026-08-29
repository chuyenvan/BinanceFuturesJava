# basis_verify.md — VERIFY basis 1m (premiumIndex / mark / index) — TASK-022 BƯỚC 1

- **Owner:** CCD-basis · **Ngày:** 2026-06-14 · **Trạng thái:** VERIFY xong → chờ Desktop/user chốt dùng + schema (mới sang BƯỚC 2 backfill).
- **Nguồn:** `data.binance.vision/data/futures/um/{daily,monthly}/{premiumIndexKlines,markPriceKlines,indexPriceKlines}/<SYM>/1m/`
- **Mẫu tải:** BTCUSDT (2024-06-01 daily + monthly 2020-01/2020-06/2021-01 probe) · ENAUSDT (alt list muộn 2024-04) · funding BTCUSDT 2024-06 để đối chiếu.
- **Phạm vi:** CHỈ tải + đọc + dump (đọc-only, không Aerospike, không live). ✅ tuân an toàn.

---

## 1. Granularity + schema 3 loại

Cả **3 loại đều dùng đúng format kline chuẩn 12 cột** (giống ticker kline), granularity **1m thật**:
`open_time, open, high, low, close, volume, close_time, quote_volume, count, taker_buy_volume, taker_buy_quote_volume, ignore`

- **1m xác nhận:** file daily BTC 2024-06-01 = **1440 bar** (1440 phút/ngày), step `open_time` = đúng 60000 ms, **0 gap**, **1440 ts unique** (không trùng).
- **Timezone:** `open_time` = epoch **ms UTC**. `1717200000000` = 2024-06-01 00:00:00 **UTC**. (⚠️ hệ ta chuẩn GMT+7 — khi backfill phải convert/align key như funding, xem [[timezone-gmt7-standard]].)
- **Cột có nghĩa chỉ là OHLC `close_time`**; `volume/quote_volume/taker_*` = **0** (kline tổng hợp từ chỉ số, không có khối lượng). `count` = số mẫu trong phút: **premiumIndex=12** (5s/mẫu), **mark/index=60** (1s/mẫu). `ignore`=0.

| Loại | `close` là gì | Đơn vị | Ví dụ (BTC 2024-06-01 00:00) |
|------|---------------|--------|------------------------------|
| `premiumIndexKlines` | **premium rate** (tỷ lệ perp vượt index) | tỷ lệ (unitless, ~1e-4) | 0.00059992 (≈ 0.060%) |
| `markPriceKlines` | **mark price** | giá USDT | 67602.75 |
| `indexPriceKlines` | **index price** (giá spot tham chiếu) | giá USDT | 67571.57 |

→ **premiumIndex KHÔNG phải giá** — nó đã là *premium rate sẵn*, đúng dạng "basis" cần dùng.

## 2. Coverage per-coin

- **BTCUSDT:** premiumIndex/mark/index có từ **2020-01** (2019-12 = HTTP 404). ⚠️ **đính chính TASK-014** (ghi "từ 2019-12"): thực tế 3 loại basis bắt đầu **2020-01**, không phải 2019-12 (2019-12 chỉ có ticker/kline spot-perp, chưa có premium/mark/index kline). Range: 2020-01 → nay.
- **Alt list muộn (ENAUSDT, list 2024-04):** cả 3 loại bắt đầu **đúng tháng list 2024-04** (2024-03 = 404), **3 nguồn đồng bộ firstSeen**. → mỗi coin chỉ có basis từ ngày list (giống mọi metric per-coin).
- **Gap:** mẫu daily BTC 0 gap; mẫu monthly 200 liên tục. (Backfill thật vẫn nên chạy gap-check như funding/OI.)
- **Dedup:** ts unique trong mẫu, không trùng.

## 3. Định nghĩa basis + ĐẠI DIỆN chọn (quan trọng)

3 cách biểu diễn basis:
- `premiumIndexKlines.close` — **premium index trực tiếp** (rate sẵn), mean 2024-06-01 = **0.000569** (0.057%), range 0.000128–0.001020.
- Tự tính `(mark − index)/index` — mean 0.000545, range −0.000173…0.000963.
- Hai cái **tương quan corr = 0.895** nhưng **KHÔNG trùng** (diff mean 2.4e-5, std 4.9e-5): premiumIndex là chỉ số impact-price riêng của sàn (mượt, dùng cho funding), còn `(mark−index)` là chênh tức thời (mark đã là index + MA-giảm-chấn của premium nên lệch).

### → CHỌN **`premiumIndexKlines.close`** làm 1 đại diện basis. Lý do:
1. **Đã là rate** — không cần chia, không phụ thuộc đơn vị giá, **so sánh được giữa các coin** (BTC vs alt giá nhỏ).
2. **Chính là input funding** (xem mục 4) — đúng tín hiệu "perp đắt/rẻ hơn spot".
3. **1 cột thay vì 2** (mark+index) → tránh nhồi 3 cột trùng (luật chống trùng schema).
4. Mark/index riêng lẻ **không cần lưu** cho mục đích basis (nếu sau cần mark cho mục đích khác — vd SL/định giá — mở task riêng; backtest đã có ticker close).

## 4. Quan hệ basis ↔ funding (định lượng, không chỉ định tính)

Funding BTC 2024-06: interval **8h**, rate **0.0001** (0.01%, **kẹp sàn**). Tái tạo funding từ premiumIndex bằng công thức sàn `funding = avg(P) + clamp(interest − avg(P), ±0.05%)` (interest=0.01%/8h):

| Block 8h (UTC) | avg premiumIndex (n=480) | funding dự đoán | funding thực |
|---|---|---|---|
| 00:00 | 0.000583 | **0.000100** | **0.0001** ✓ |
| 08:00 | 0.000622 | 0.000122 | 0.0001025 ✓ (xấp xỉ) |
| 16:00 | 0.000503 | 0.000100 | (sang ngày sau) |

→ **premiumIndex 1m là input trực tiếp dựng nên funding 8h** ("dẫn" funding theo định nghĩa). Vì funding chỉ cập nhật **8h/lần và thường bị kẹp sàn 0.01%** (3 mốc đều 0.0001), trong khi premium 1m **dao động 0.013%–0.102%** ngay trong ngày → **basis 1m mang nhiều thông tin hơn hẳn funding thô**, và sớm hơn 8h. **Giá trị bổ trợ funding = CAO, xác nhận đánh giá TASK-014.**

## 5. Dedup + gap
- Mẫu sạch: 1440 ts/ngày, unique, 0 gap, step 60000ms đều. Backfill thật vẫn cần gap/dedup-check chuẩn (như funding/OI pipeline).

---

## Kết luận cho Desktop/user (cần chốt trước BƯỚC 2)
1. **Dùng basis?** Khuyến nghị **CÓ** — bổ trợ funding rõ rệt (1m vs 8h-kẹp-sàn), là tín hiệu crowdedness perp.
2. **Đại diện:** **`premiumIndexKlines.close`** (1 cột rate), KHÔNG lưu mark/index cho mục đích basis.
3. **Granularity backfill:** nguồn là 1m. Chốt lưu 1m hay aggregate (vd 5m/15m như gate khác) — tuỳ tầng dùng (gate 15m/4h hay selector). **Cần user chốt.**
4. **Schema 226(+242 qua 226):** thống nhất với pipeline funding/OI; key align GMT+7; gap/dedup-check. Spec chi tiết ở BƯỚC 2 sau khi chốt.
5. **Coverage:** basis chỉ từ 2020-01 (BTC) / ngày-list (alt) — khớp ràng buộc survivorship/lifecycle hiện có.
