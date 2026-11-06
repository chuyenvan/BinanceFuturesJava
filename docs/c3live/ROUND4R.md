# ROUND 4r — guard độ đủ phút (MINUTE-GUARD), jar r4r (2026-11-06)

## Vì sao
Live phút 11-04 23:46Z: WS connection #4 của ingestor rớt, nến chốt chỉ có 627/752 symbol. v_t_m vẫn ra quyết định lúc :06 trên
dữ liệu thiếu: tính trên 504 symbol, trong khi ngày thường là 509–513. Ingestor sẽ sửa ở QF4. Guard này là lớp chặn phía v_t_m,
độc lập với QF4.

## Thay đổi (c3live `7913b1b9`)
- `MinuteCompletenessGuard` (mới) và `LiveTickerWindow.countsRange` (chỉ đọc cache).
- `DetectEntrySignal2TradeNormal.checkMarketLevelChange2Trade`: guard đặt ngay sau `tickerWindow.read`, trước UniverseA1 /
  features / quyết định.
  - `co` = số symbol có nến ở phút vừa chốt. `can` = ⌈99 % × trung vị 60 phút trước⌉. Có dưới 30 phút lịch sử thì bỏ qua.
  - `co ≥ can`: không đọc thêm, không đổi gì (giống r4q từng byte).
  - Thiếu: đọc lại mỗi 2 s, tối đa tới giây +20 sau khi chốt. Đủ thì log `[MINUTE-WAIT]`, đọc lại cửa sổ rồi quyết định bình thường.
  - Vẫn thiếu: log `[MINUTE-INCOMPLETE]` và fail-closed. `createOrderBuyRequest0` chặn mọi lệnh mới (entry, DCA, paper) trong tick đó
    và đếm `tong_chan`. Quản lý vị thế, trailing và stop giữ nguyên.
  - Khởi động có log `[MINUTE-GUARD] BAT|TAT`. Tắt bằng `LIVE_MINUTE_GUARD=0`.
- **Chỉ có ở live.** Sim, replay, E2E và harness parity không mô phỏng guard. Parity: vz_e1 `docs/prereg/PREREG_PARITY_V12_DRY_ADDENDUM14.md`.
  Phút MI bị loại khỏi K5 nhưng vẫn được đếm và báo cáo.
- Số liệu nền (log ingestor, từ QF3 11-01 → 11-06 16:56, 8 217 phút): có 6 phút sẽ kích hoạt guard, đều rơi vào 11-05/11-06. Ngày 11-01..11-04: 0 phút.

## Test
- `MinuteCompletenessGuardTest` 9/9:
  - tái hiện 23:46Z 627/752: chờ 18–20 s rồi fail-closed;
  - phút đủ: 0 lần đọc thêm, cửa sổ giống từng byte;
  - bù muộn trong hạn;
  - ngưỡng biên 744/745;
  - ngày sập có nhiều kết nối rớt: không phút nào trễ quá +20 s;
  - kiểm vị trí gắn guard.
- Full `mvn package`: 942 test, 0 fail (1 skip có sẵn).
- fake242: §33 (r4n→r4q) giữ nguyên; thêm §34 (r4q→r4r), gồm:
  - DRY;
  - env có `LIVE_MINUTE_GUARD=0` ⇒ TỪ CHỐI;
  - `[MINUTE-GUARD] TAT` ⇒ rollback;
  - XONG + `register_jar r4r`.

## Jar
`~/claude_master/v12/jar/binance-java-sdk-1.2.4.jar_v12_r4r`, md5 `bd85ca94504188c5a0dc8adac6f98a55`. Trước đó: r4q `8c81e6b5`.
Pin r4r ở các file:
- `golive_lib.sh`;
- `deploy_v12_dry_r4.sh`;
- `restart_v12_dry_reseed.sh`;
- `swap_v12_dry_jar.sh`: OLD = r4q `8c81e6b5`, NEW = r4r; tag qua `OLD_TAG` / `NEW_TAG`; `NEED_MGUARD=1`.

## Lệnh owner (trên Oracle) — CHƯA chạy
```
DRY=1 bash ~/claude_master/v12/c3live/ops/c3live/swap_v12_dry_jar.sh   # chỉ kiểm (242 CHỈ ĐỌC)
bash ~/claude_master/v12/c3live/ops/c3live/swap_v12_dry_jar.sh         # gõ YES => JOB NỀN; theo dõi: tail -f <job_log in ra>
```
Hậu kiểm gồm các mục của r4q, cộng `[MINUTE-GUARD] BAT`. Trượt ⇒ rollback tự động về r4q. Đạt ⇒ `register_jar.sh r4r …`.
Sau swap, theo dõi `grep -a 'MINUTE-INCOMPLETE\|MINUTE-WAIT' logs/full.log`.
