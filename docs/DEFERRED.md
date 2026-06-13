# DEFERRED — hoãn tới khi có CI/CD

> Lý do hoãn: LIVE hiện **chưa có CI/CD**, vận hành thủ công + kiểm soát rất chặt, nên các vấn đề liên quan config/an-toàn-deploy chưa ưu tiên. Ghi lại để KHÔNG trôi; khi dựng CI/CD thì xử lý.

## 1. Fix parser `Configs.java:38` — `split("=", 2)`
- Hiện: `line.split("=")[1]` ném AIOOBE với value rỗng → app `System.exit(0)` (ảnh hưởng cả LIVE). Cũng sai nếu value chứa `=`.
- Đã vá tạm bằng sửa FILE config (bỏ value rỗng) — bug code vẫn còn.
- Fix tận gốc 1 dòng: `split("=", 2)` + chấp nhận value rỗng. Không đổi giá trị → không bump CONFIG_VERSION.

## 2. Tách `DIED_SYMBOLS` theo môi trường SIM vs LIVE
- Hiện `Constants.diedSymbol` dùng CHUNG (SIM + LIVE). Đã xóa còn `BTCDOMUSDT` để SIM thấy coin chết (cho survivorship).
- Hệ quả LIVE: live có thể thử entry coin đã delist. Cần: LIVE giữ loại coin delist (an toàn), SIM bỏ loại (để đo) — một cờ riêng theo môi trường.
- Hoãn vì live thủ công + chặt; khi có CI/CD thì tách.

## 3. (KHÔNG hoãn hẳn — liếc khi chốt baseline) coin DIED_SYMBOLS cũ có-data giờ vào backtest
- Bỏ DIED_SYMBOLS làm backtest có thể trade coin trước bị loại mà dataset đã có data (vd `USDCUSDT` stablecoin). Ảnh hưởng tính đúng của baseline/fingerprint.
- Nên soi 1 lần khi chốt baseline FAST: có coin không-nên-trade nào lọt vào trades không; nếu có → thêm lọc (không phải qua DIED_SYMBOLS).

## 4. Thống nhất nguồn `DIED_SYMBOLS` (3 bản đang vênh) — TASK-008 nêu
- Sau 008: tồn tại 3 giá trị — **repo `config.properties`** (~30) / **prod 226** (129, đã apply phương án A) / **SIM-survivorship** (BTCDOMUSDT-only). Nguồn vênh tiềm ẩn → backtest/sim có thể dùng DIED khác live.
- ⚠️ **Căng thẳng thật:** LIVE cần DIED RỘNG (skip coin chết/không-trade); SIM sau khi backfill 30 core cần DIED HẸP (để coin chết VÀO backtest mà đo survivorship — nếu sim cũng loại 129 thì backfill vô nghĩa).
- **Hướng giải (qua TASK-010 lifecycle, KHÔNG cần tách 2 list):** SIM/feature/backtest dùng `SymbolLifecycleManager.isAlive(symbol,t)` thay việc đọc DIED → coin chết vẫn vào backtest trong giai đoạn sống, tự loại sau delist (survivorship đúng). LIVE giữ `DIED_SYMBOLS` (config ingest/trade). Lifecycle là DATA chung → KHÔNG vi phạm 'một bộ não' (khác với tách 2 list logic mà user đã từ chối ở 008).
- Khi lifecycle xong: rà call-site đọc `diedSymbol` ở nhánh SIM/feature/export (`MarketBigChangeDetector:63`, `MarketDataInlineGenerator`, `ExportMarketData2File`) → chuyển sang lifecycle; đồng bộ repo config với prod. Bump CONFIG_VERSION nếu đụng nhánh sim.
