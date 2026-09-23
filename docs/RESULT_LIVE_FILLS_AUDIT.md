# RESULT_LIVE_FILLS_AUDIT — KHỚP LỆNH THẬT (Binance USDⓈ-M, tài khoản live 242)

Ngày: 2026-09-23. Đây **không phải** một vòng nghiên cứu mới mà là **audit dữ liệu khớp lệnh THẬT**
theo yêu cầu chủ (không pre-reg; không đổi code chiến lược).
Script: `research/live_fills_audit/fetch_live_fills_242.sh` (chạy **trên 242**),
`analyze_fills.py`, `slip_vs_kline1m.py`. Dữ liệu dẫn xuất: `research/live_fills_audit/data/`
(**không commit**: `*.csv` bị chặn bởi `.gitignore` gốc của repo — tái tạo bằng script, ~40 s).

**Ràng buộc đã tuân thủ:**
- **CHỈ GET** (`/fapi/v1/userTrades`, `/fapi/v1/allOrders`, `/fapi/v1/order`, `/fapi/v1/commissionRate`,
  `/fapi/v2/positionRisk`, `/fapi/v1/klines`). **Không** đặt/huỷ/sửa lệnh, không `batchOrders`,
  không `allOpenOrders` (DELETE), không `leverage`/`marginType`/`positionMargin`.
- **Key ở lại 242**: key/secret đọc tại chỗ từ jar đang chạy, chỉ nằm trong biến shell của script
  trên 242 — **không** in, **không** ghi log, **không** copy sang Oracle. Chỉ **JSON thô (không có key)**
  được copy về Oracle để phân tích.
- 242: **chỉ đọc** file cấu hình; không sửa file, không restart/kill tiến trình.

## 0. KẾT LUẬN (một dòng)

> **FEE THẬT = 0,05 %/chân (taker 100 %, maker 0 %)** ⇒ round-trip **0,098 %**, **thấp hơn 8,2×** giả định
> **0,8 %/round-trip** của sim (và **đúng bằng** giả định taker 0,05 %/chân; giả định maker 0,02 %/chân
> **chưa từng được dùng** trong 991 chân thật). **FILL-RATE THẬT = 100 %** (388/388 lệnh FILLED, **100 %
> MARKET**, 0 lệnh treo ⇒ không có rủi ro khớp một phần/không khớp). **SLIP THẬT ≈ 0,33 %/chân (median) /
> 0,72 % (mean|.|)** ⇒ **0,45–0,64× proxy `0,5×(h−l)/c`** của sim ⇒ proxy **bảo thủ ~1,6–2,2×**.
> Tổng chi phí thật **≈ 0,76 %/round-trip (median)** ≈ đúng giả định 0,8 % của sim (1,05×).

## 1. Cách tiếp cận + công cụ

| Bước | Thực hiện |
|---|---|
| Key ở đâu | **KHÔNG** có trong `conf/env.sh` (42 tên biến: cấu hình chiến lược, không có biến key) và **KHÔNG** có trong `/proc/<pid>/environ` của tiến trình live (`BinanceOrderTradingManager`, pid đọc được). Key là **hằng số Java `API_KEY`/`SECRET_KEY`** nhúng trong `com/binance/chuyennd/config/PrivateConfig.class` **bên trong jar đang chạy** trên 242 ⇒ **có tìm thấy**, ở lại 242. |
| python3 trên 242 | **KHÔNG có** (`command -v python3` → none). Có `python2` (dùng để unzip class + parse JSON) ⇒ lệnh API ký bằng **`curl` + `openssl dgst -sha256 -hmac`** (đúng phương án dự phòng trong yêu cầu). |
| Ký request | `openssl dgst -sha256 -hmac <secret>`, header `X-MBX-APIKEY`; `recvWindow=10000`. |
| Giới hạn cửa sổ API (đo được) | `/fapi/v1/userTrades`: cửa sổ **tối đa 7 ngày** (`-4165`), **lịch sử ~91 ngày**. `/fapi/v1/allOrders`: **tối đa 7 ngày/cửa sổ** và **chỉ trong 90 ngày gần nhất** (`-4166`); lệnh cũ hơn chỉ đọc được lẻ bằng `/fapi/v1/order?orderId=`. |

## 2. Xác định symbol đã giao dịch

| Nguồn | Kết quả |
|---|---|
| `run/legacy_symbols.csv` (242) | **54** symbol legacy (có comment `#`, đã lọc) |
| `storage/data/order/**` (242) | **83 ngày** (2026-04-24 → 2026-09-12), **317** symbol phân biệt |
| `/fapi/v2/positionRisk` (GET) | **54** vị thế đang mở (khớp đúng tập legacy) |
| Danh sách ứng viên gộp | **317** symbol → quét đầy đủ **61** (=54 legacy ∪ 7 symbol có phát sinh trong 7 ngày cuối) |
| Kết quả | **50 symbol** có khớp lệnh thật trong cửa sổ lấy được |

## 3. Dữ liệu THẬT lấy được

| Chỉ tiêu | Giá trị |
|---|---|
| Số chân khớp (legs, đã dedupe theo `id`) | **991** |
| Khoảng thời gian | **2026-06-24 13:31 → 2026-09-20 14:18 UTC** (88,0 ngày) |
| Ghi chú retention | Live bắt đầu 2026-04-24 ⇒ **~35 ngày đầu đã bị Binance xoá** (không lấy được, **không bịa**) |
| Notional/chân | mean 18,30 USDT · median 11,27 · max 79,19 |
| `realizedPnl` tổng (cửa sổ) | **+187,21 USDT** |
| Commission tổng | 8,9061 USDT trên 18.135,48 USDT notional (blended **0,0491 %**) |

## 4. MAKER / TAKER (%)

| | Số chân | % |
|---|---|---|
| maker | **0** | **0,00 %** |
| taker | **991** | **100,00 %** |

⇒ Executor live **chỉ đi market**, không bao giờ nằm sổ ⇒ mọi giả định maker (0,02 %/chân, ưu tiên khớp
maker, adverse selection của maker) **không có cơ sở dữ liệu thật** để kiểm chứng trong giai đoạn này.

## 5. FEE THẬT / chân

| | mean | median |
|---|---|---|
| fee/chân | **0,04897 %** | **0,05000 %** |
| fee/round-trip (2 chân) | 0,09794 % | **0,10000 %** |

- Hợp đồng phí đo được (`/fapi/v1/commissionRate`): **taker 0,000500**, **maker 0,000200** — khớp đúng
  0,05 % / 0,02 %.
- Phân bố: **888** chân @0,0500 %, **102** chân @0,0400 % (6 symbol: APP, GEV, SHAZ, SOXS, TZA, XBI), 1 chân @0,0497 %.
- `commissionAsset` = **USDT** 100 %.

**So với sim:**

| Giả định sim | Thực tế | Kết luận |
|---|---|---|
| taker **0,05 %/chân** | 0,049 %/chân | ✔ **khớp** |
| maker **0,02 %/chân** | không dùng | — (0 % maker) |
| **0,8 %/round-trip** | **0,098 %** (mean) / **0,100 %** (median) | ⚠️ **sim đắt hơn thực tế 8,2×** (mean) / **8,0×** (median) ở khoản phí |

## 6. TỈ LỆ KHỚP (từ `/fapi/v1/allOrders`)

| Chỉ tiêu | Giá trị |
|---|---|
| Lệnh đọc được (cửa sổ 89 ngày) | **388** (dedupe `orderId`) |
| Trạng thái | **FILLED 388 / 388 = 100,00 %** (NEW 0 · CANCELED 0 · EXPIRED 0) |
| Loại lệnh | **MARKET 388/388** (không có LIMIT/STOP chờ sổ) |
| reduceOnly/closePosition | 164 (đóng vị thế) · 224 (mở/DCA) |
| Khớp nối với trades | 388/388 `orderId` xuất hiện trong `userTrades`; **2,20 chân khớp/lệnh** (market quét nhiều mức giá) |

⇒ **Fill-rate thật = 100 %** vì **không có lệnh nào nằm sổ**. Rủi ro "lệnh không khớp" trong live
giai đoạn này = **0**; mô hình sim nếu giả định limit-order với xác suất khớp **không được dữ liệu live xác nhận**.

## 7. SLIP THẬT / chân (so với proxy của sim)

Đối chiếu `price` khớp với nến **1m công khai của Binance** (`/fapi/v1/klines`) tại **đúng phút**
(biến thể **cùng symbol + cùng phút**, 1.250 dòng nến, 423 request):

| Chỉ tiêu (976/991 chân khớp được nến) | mean | median |
|---|---|---|
| slip vs **close** phút (`(fill−c)/c` cho BUY, `(c−fill)/c` cho SELL) | **−0,01957 %** | +0,02150 % |
| slip vs **open** phút | +0,33202 % | +0,23308 % |
| **\|slip\| vs close** | **0,71600 %** | **0,32952 %** |
| **proxy sim `0,5×(h−l)/c`** | **1,11965 %** | **0,72850 %** |

Phân vị `|slip|`: p75 0,897 % · p90 1,629 % · p95 2,487 % · p99 **6,014 %** (đuôi dày).

**So với proxy:**

| Cách so | Tỉ lệ thực/proxy |
|---|---|
| mean(\|slip\|) / mean(proxy) | **0,639** |
| median(\|slip\|) / median(proxy) | **0,452** |

⇒ Slip THẬT **nhỏ hơn** proxy `0,5×(h−l)/c` của sim **~1,6–2,2×** (sim **bảo thủ**).
Bias có dấu gần bằng 0 (−0,02 % vs close) ⇒ **không** có dấu hiệu "mua đuổi/bán đuổi" hệ thống.

## 8. STACK CHI PHÍ THẬT/round-trip

| | Fee | Slip | Tổng/round-trip |
|---|---|---|---|
| **median** | 0,100 % | 0,659 % | **0,759 %** |
| **mean** | 0,098 % | 1,432 % | **1,532 %** |

- So với **0,8 %/round-trip** của sim: **median ≈ 0,95× (sim nhỉnh hơn 1,05×)**;
  **mean ≈ 1,9× sim** (do đuôi `|slip|` p90–p99).
- So với **0,05/0,02 %/chân**: **taker đúng**, maker **không dùng**; sim **không** mô hình hoá phí maker
  mà thực tế cũng **không** sinh maker.

## 9. Hạn chế / điều KHÔNG đo được

1. **~35 ngày đầu live (2026-04-24 → 2026-06-23) bị Binance xoá** — vĩnh viễn không lấy được qua API.
2. `allOrders` chỉ 90 ngày & tối đa 7 ngày/cửa sổ ⇒ tỉ lệ khớp chỉ đo trên 388 lệnh (không phải toàn bộ 991 chân).
3. **15 chân** không khớp được nến 1m (niêm yết/huỷ niêm yết giữa phút) ⇒ slip tính trên 976 chân.
4. Quét đầy đủ 13 cửa sổ cho **61 symbol** (54 legacy + 7 có phát sinh); 256 symbol còn lại chỉ **probe 7 ngày**
   (không thấy phát sinh) ⇒ nếu có symbol ngoài legacy khớp lệnh **>7 ngày trước**, audit này **không thấy**.
5. Phí 0,04 % ở 6 symbol là **tier/ưu đãi riêng**, có thể đổi; 0,05 % mới là mức phổ quát.

## 10. Việc cần làm (đề xuất, không tự làm)

- **Xoay (rotate) API key**: (a) key nhúng **hardcode trong jar** trên 242 là rủi ro vận hành (mọi bản backup
  jar/backup dir đều mang key); (b) trong lúc thu thập, một lệnh `pgrep -af curl` trên 242 đã **in nguyên
  command line của curl (có key)** vào phiên làm việc ⇒ **key đã lộ vào transcript** (chỉ tới chủ sở hữu key,
  nhưng vẫn nên rotate). Ghi nhận trung thực, không giấu.
- Nếu muốn sim sát thực tế hơn: **bỏ** giả định maker, giữ taker 0,05 %/chân, và dùng slip
  **0,45–0,64×** proxy `0,5×(h−l)/c` (hoặc giữ nguyên proxy nếu muốn bảo thủ).

## 11. Tái lập

```bash
# Trên 242 (READ-ONLY, GET-only):
find /home/chuyennd/java/v_t_m/storage/data/order -mindepth 2 -maxdepth 2 -type f \
     -printf '%f\n' | sed 's/-[0-9]*$//' | sort -u > /tmp/fills_audit/order_symbols.txt
bash research/live_fills_audit/fetch_live_fills_242.sh      # raw -> /tmp/fills_audit/raw{2,3,4}

# Trên Oracle (không có key, chỉ JSON thô + dữ liệu dẫn xuất):
FILLS_RAW2=/tmp/fills_audit_oracle/raw2 FILLS_RAW4=/tmp/fills_audit_oracle/raw4 python3 analyze_fills.py
FILLS_RAW3=/tmp/fills_audit_oracle/raw3                            python3 slip_vs_kline1m.py
```

Ghi chú: `data/*.csv` + `data/slips.json` là **sản phẩm dẫn xuất, không commit** (`*.csv` bị `.gitignore`
gốc chặn); chạy 2 script trên là tái tạo đủ mọi số trong tài liệu này. JSON thô (`raw2/raw3/raw4`) nằm
trong `/tmp/fills_audit/` trên **242** và bản copy không chứa key ở `/tmp/fills_audit_oracle/` trên Oracle.
