# v1 live deploy — entry cadence 15m grid (2026-08-17)

Thuộc Track 1 / Gate 1 (reconcile live↔backtest). KHÔNG phải "tối ưu gate" (đó là Track 2).

## Vấn đề
Live `DetectEntrySignal2TradeNormal.isTimeProcessData()` chạy cadence **1 phút** (fire ở second 6–10 mỗi phút) trong khi WFO canonical = **G015 = grid 15m**. ⇒ live đánh giá entry ~15× nhiều điểm hơn backtest; selector còn ăn feature ở timestamp off-grid chưa validate.

## Sửa (commit `3ba86f6`, branch `module`)
- Thêm điều kiện `curMin % ENTRY_GRID_MIN == 0` → entry chỉ tại :00/:15/:30/:45 UTC.
- `ENTRY_GRID_MIN` đọc env `LIVE_ENTRY_GRID_MIN` (default 15; `=1` revert cadence 1m không cần rebuild).
- Chỉ throttle vòng **entry + DCA-check**. Exit/SL nằm ở `BinanceOrderTradingManager` (`ThreadManagerOrder`) → KHÔNG bị ảnh hưởng.

## Deploy (242 = 3stech.vn, root:2222, /home/chuyennd/java/v_t_m)
- Build fat jar: IntelliJ bundled Maven + JDK Corretto 17, pom `<target>11</target>` → bytecode v55 chạy trên java-11 của 242. Jar `binance-java-sdk-1.2.4.jar` = 99,628,333 B.
- Verify: class `DetectEntrySignal2TradeNormal` trong jar chứa literal `LIVE_ENTRY_GRID_MIN`.
- Backup: `target/binance-java-sdk-1.2.4.jar.bak_15m_20260817` (jar cũ 99,602,908 = bản selector 08:19).
- scp `.new15m` → `mv` đè → `bin/daemon.sh stop` → `start`. Bot pid 17337 (12:49), init sạch: AI + Funding model loaded, các thread lên, KHÔNG exception/fail-fast.
- **Rollback**: `mv .bak_15m_20260817 → binance-java-sdk-1.2.4.jar` + restart.

## Verify gate 15m
- 12:50:55: entry-loop log **rỗng** kể từ start 12:49 (bản 1m đã phải tick ở 12:50) → 1m firing bị chặn đúng.
- Còn chờ: tick dương ở 13:00 + im tới 13:15 (bằng chứng dứt điểm).

## Config live (env.sh, đã có sẵn) — gate threshold khớp backtest
`SELECTOR_RANK_TOPK=5`, `SIM_MIN_MOMENTUM_15M=0.008` (áp qua `static{}` block Configs → live thật dùng 0.008, không chỉ backtest).

## Còn hở (chưa làm)
Feature live vẫn tính trên cửa sổ 1m rolling (`readDataForSymbols(...,1500)`), CHƯA align về nến-15m-đóng như `ExportFeaturesForPythonTool`. ⇒ mới khớp *tần suất* lưới, chưa khớp *giá trị* feature (rủi ro parity #2 trong `wfo_train_data_recipe`). Việc tiếp theo nếu muốn parity thật.

## Ghi chú hạ tầng (quan trọng cho phiên sau)
SSH từ bridge desktop: **System32 `ssh.exe` bị chặn stdio** (ssh -V rỗng, exit 255) — KHÔNG phải mạng/target. Dùng **git-bash ssh** `C:\Program Files\Git\usr\bin\ssh.exe` + key `~/.ssh/id_rsa_chuyennd` (KHÔNG phải `_openssh`). scp tương ứng `C:\Program Files\Git\usr\bin\scp.exe`. Build local >60s nên phải chạy background (bridge cap tool call 60s).
