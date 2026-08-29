# WFO WORST-N — CHẨN ĐOÁN & LEVER EXIT (2026-07-23)

Tổng hợp research arc từ roadmap notebooklm → WFO thực. Nguồn số: `wfo_report_long_invsel_*` trên Oracle.

## 1. Kết quả WFO (LONG, dataset oiz2022_75, 16 window, 30 samples, Oracle-only)

| Run | Selector | ABLATION | %OOS-dương | WFE median | worst maxDD | ZERO_TRADES | Ghi chú |
|---|---|---|---|---|---|---|---|
| N5 (A) | Worst-5 | A (filter ON) | 12.5% (2/16) | 4.641 | 9.1% | 8 | AIRejectFilter reject chính coin worst → đói lệnh |
| N5B | Worst-5 | B (filter OFF) | 18.8% (3/16) | 0.248 | 16.6% | 0 | Hết đói lệnh; nhưng 7 BURN + edge dồn 1 window |
| N3B | Worst-3 | B | *(đang chạy)* | | | | |
| N8B | Worst-8 | B | *(chờ)* | | | | |

**Kết luận cốt lõi (N5B, mode B — phép thử đúng của thesis Worst-N):**
- Entry worst-N vào lệnh bình thường (hàng trăm lệnh/window) — gate KHÔNG còn là nút thắt.
- **Edge KHÔNG robust:** tổng OOS pnl thô ~+4106 nhưng **+5045 đến từ DUY NHẤT win15 (2025 Q4)**; bỏ ra còn **~−939** (7 window BURN, catch-falling-knife trong downtrend). "+712% proxy" nhiều khả năng cùng bản chất: 1–2 window bull may mắn.
- win13/14/15 `reject=30/30` → bestGenome là "ít tệ nhất" → OOS ở đó gần như **noise**, chưa tối ưu thật.

## 2. Vì sao fitness V4 gạt oan (xác nhận nghi ngờ của Uni)
- `minTrades = max(5, windowDays×0.33)` → TRAIN 12 tháng cần **≥120 lệnh**; gate chặt → không đạt → `REJECT_BASE −100000` → HPO không chọn được genome tốt.
- `BURN_ACCOUNT` (pnl≤0) và `TOO_MUCH_CAPITAL_LOCK` (held>7d) reject cứng → **win15 lãi +5045 bị vứt** vì capital-lock. Fitness đang tối ưu về phía ít-lệnh/an-toàn, ngược với play mean-reversion.

## 3. Cơ chế BURN / capital-lock (đọc OrderTargetInfoTest)
- Position **chưa arm trailing**: chỉ TIME_STOP_HOURS cứu. Mua oversold không nảy → thoát lỗ sau 24h → nhiều lệnh lỗ nhỏ = BURN (rõ nhất bear-2022 win1: 359 lệnh, −105).
- Position **đã arm trailing** (nảy nhẹ): TIME_STOP KHÔNG còn áp → bleed ngang >7d chưa chạm SL → **capital-lock** (win15).
- **Hard-SL mặc định TẮT** trong run → thiếu vế "chặn lỗ" của thesis "SL chặn lỗ khi có lãi & nuôi lãi".

## 4. Lever EXIT sweep được (cho phase sau — phần lớn KHÔNG cần code)
| Lever | Cơ chế | Wire | Hiện tại |
|---|---|---|---|
| `SIM_HARD_SL_PCT` | blanket hard-SL trên giá entry đầu cụm | env ✓ | 0 (OFF) — **lever cắt lỗ chính** |
| `TIME_STOP_HOURS` | thoát nếu chưa arm trailing quá N giờ | env ✓ | 24 (chỉ pre-arm; cần bản post-arm) |
| `TRAIL_PEAK_MODE` | đỉnh arm/ratchet: high vs close (chống wick) | env ✓ | high |
| `TS_PROFIT_MULTIPLIER` | ngưỡng arm trailing | genome [4,8] | HPO tune |
| `HARD_STOP_LOSS_RATE` | SL riêng cho PREDICT_SYMBOL_TRADE theo độ sâu lỗ | **chỉ properties, CHƯA env** | 0 (OFF) — muốn sweep phải wire env |

## 5. Hướng đề xuất (chờ Uni chốt sau khi đủ N3B/N5B/N8B)
- **A. Exit-sweep** trên nền Worst-5 mode B: bật `SIM_HARD_SL_PCT` (vài mức 0.06/0.10/0.15) + thử `TIME_STOP_HOURS` ngắn hơn → cắt 7 window BURN, xem net-pnl. Test trực tiếp "SL chặn lỗ".
- **B. Regime filter:** chỉ vào worst-N khi BTC/breadth không downtrend mạnh → tránh falling-knife (nguồn BURN chính).
- **C. Nới fitness rồi WFO lại:** hoãn reject BURN/CAPITAL_LOCK/minTrades để HPO thấy vùng lãi-nhưng-kẹt, tune exit về net-pnl thật. Rủi ro overfit — cần định nghĩa mục tiêu mới cẩn thận.

## 6. GHOST PRE-LISTING (điều tra timezone/data 2026-07-23)

- **Timezone chỉ sai HIỂN THỊ, KHÔNG sai data.** Epoch lưu raw UTC (KlineObjectSimple.startTime = Binance openTime; bin WfoDataset ghi/đọc đối xứng, md5-verified; ticker bin = Java ObjectInputStream). `sdfFileHour` pin GMT+7 chỉ để format log. forward-fill funding dùng `floorEntry` = không look-ahead.
- **NHƯNG ghost pre-listing CÓ THẬT:** AINUSDT niêm yết Binance Futures **2025-07-11 07:15 UTC** (web-verified). Log sim vào lệnh lúc 06:09 UTC = **trước listing 66 phút**, giá thật (O=0.1571..). Lọt qua `isTickerAvailable` (giá≠0).
- **`SymbolLifecycleManager.isAlive` KHÔNG cứu được:** `SymbolLifecycleBuilder:134` tính `firstSeen = phút-data-đầu-tiên` → quét chính data có ghost → firstSeen inherit ghost → guard vô hiệu cho đúng cửa sổ ghost. Chặn thật cần **onboardDate authoritative từ fapi exchangeInfo**, không phải data-scan.
- **Reframe quan trọng:** ghost làm KẾT QUẢ TỐT HƠN thực tế (vào sớm giá pre-listing). worst-N vốn ĐÃ FAIL (3-4/16) kể cả khi được ghost thổi. Dọn ghost sẽ làm worst-N **tệ hơn, KHÔNG cứu được**. → Ghost-cleanup KHÔNG phải để cứu worst-N (đã chết), mà là **hạ tầng data-integrity cho MỌI backtest tương lai**.

> Nhận định: edge nằm ở **exit + regime**, KHÔNG ở breadth N. N3B/N8B nhiều khả năng chỉ đổi độ đậm kết luận (N nhỏ = tập trung, N lớn = pha loãng), không tạo edge mới. Hard-fix gate/nới fitness không tạo ra edge không tồn tại — nhưng sửa exit để cắt BURN + giữ win kiểu win15 thì phân phối có thể đảo.
