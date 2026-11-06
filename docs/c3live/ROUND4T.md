# ROUND 4t — A1 MAJ-S: ngưỡng theo exchangeInfo khi delist hàng loạt, jar r4t (2026-11-06)

r4r (`bd85ca94`) và r4s (`30469710`) **không** lên 242. Swap một lần r4q → r4t. Nền tảng xem `ROUND4R.md` và `ROUND4S.md`.

## Thay đổi
- `MinuteCompletenessGuard`:
  - **Số kỳ vọng = min(trung vị 60 phút ĐỦ, |symbol đã thấy ở phút ĐỦ ∩ TRADING theo exchangeInfo hiện hành|)**.
    - Delist thật làm symbol rời TRADING, nên kỳ vọng giảm theo và guard không kẹt fail-closed. Guard chỉ trễ tới lần làm mới
      exchangeInfo kế tiếp (cron :03/:18/:41/:48): trong khoảng đó các phút là MI và có KHẨN.
    - WS rớt thì symbol vẫn TRADING, nên vẫn bị bắt.
    - Universe tăng không ảnh hưởng, vì lấy min.
  - Tập symbol đã thấy được giữ cố định: mầm từ cache 60′, sau đó chỉ thêm từ phút ĐỦ.
  - Không có exchangeInfo, hoặc kỳ vọng nhỏ hơn nửa trung vị (nguồn nghi sai) ⇒ bỏ qua exchangeInfo, chỉ dùng trung vị, có WARN.
  - Log thêm trường `ky_vong_ex=`.
- `UniverseA1Filter.tradingSymbols()`: lấy tập status=TRADING từ snapshot A1 hiện hành (có reload theo mtime). `LiveTickerWindow.symbolsIn`.
- Phút đủ ⇒ quyết định y nguyên r4q.

## Test
- `MinuteCompletenessGuardTest` 17/17. Thêm vào:
  - delist 8, 20 và 60 symbol một lần: 0 MI, `need` = ceil(99 % × (752 − k));
  - delist 20 khi exchangeInfo trễ 15′: 15 MI + KHẨN, rồi hết ngay khi làm mới;
  - sự cố 627/752 khi exchangeInfo đủ: vẫn bắt;
  - delist 20 đúng phút WS rớt (607 < 725): bắt;
  - universe tăng: không ảnh hưởng;
  - exchangeInfo vô lý: bỏ qua.
- Full `mvn package`: 950 test, 0 fail. fake242: §34 chuyển sang r4q → r4t.
- exchangeInfo trên 242 (20:18): 804 TRADING, 137 SETTLING, 1 PENDING_TRADING.

## Jar
`~/claude_master/v12/jar/binance-java-sdk-1.2.4.jar_v12_r4t`, md5 `694b29b2e5be32b537ca6c38557e64db`. Đã pin r4t ở `swap_v12_dry_jar.sh` (OLD = r4q `8c81e6b5`),
`golive_lib.sh`, `deploy_v12_dry_r4.sh` và `restart_v12_dry_reseed.sh`.

## Lệnh owner (trên Oracle) — CHƯA chạy
```
DRY=1 bash ~/claude_master/v12/c3live/ops/c3live/swap_v12_dry_jar.sh   # chỉ kiểm (242 CHỈ ĐỌC)
bash ~/claude_master/v12/c3live/ops/c3live/swap_v12_dry_jar.sh         # gõ YES => JOB NỀN; theo dõi: tail -f <job_log in ra>
```
