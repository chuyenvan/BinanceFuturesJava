# ROUND4Q — jar r4q (4p + 4q) và đường đưa lên 242 (2026-11-05)

## Jar
- `~/claude_master/v12/jar/binance-java-sdk-1.2.4.jar_v12_r4q`, md5 **8c81e6b560b61e7d43ca32c4a50ec926**, build tại bc030d76 (full test
  933, 0 lỗi, 1 skip).
- Thay cho r4q trước đó (1590d606, đã A1 R4PQ). Phần thêm sau A1 R4PQ, cần A1 delta:
  - **MIN bù phí:** hết 5 lần userTrades ⇒ `[C3-LIVE] KHAN` (Telegram), và sổ ghi cờ `fee_missing` ("SYM:orderId", persist, tối đa 500).
  - **Log phục vụ hậu kiểm swap:**
    - `[UNIVERSE-A1] BAT … PREMARKET=n`;
    - `[GATE-PRE] … premarket_bo=n` (in ở tick đầu sau khởi động và mỗi khi có bỏ);
    - dòng `[LIVE_PROFILE=c3_live] BAT … LEGACY_QUEUE_LIVE_BLOCK=true|false`.
- Nội dung 4p:
  - Bug2: bù phí qua userTrades;
  - Bug3: đếm 429 riêng cho lệnh;
  - Bug4: test MERGED.
- Nội dung 4q:
  - PREMARKET (b);
  - chặn queue LEGACY khi c3_live (`LEGACY_QUEUE_LIVE_BLOCK`, mặc định chặn).

## Pin (đổi sang r4q)
| file | trước | nay |
|---|---|---|
| `golive_lib.sh` NJ_MD5 | r4n fb6711ef | r4q 8c81e6b5 |
| `deploy_v12_dry_r4.sh` NJ / NJ_MD5 | r4n | r4q |
| `restart_v12_dry_reseed.sh` NJ_MD5 | r4n | r4q (chạy reseed SAU khi swap) |
| `swap_v12_dry_jar.sh` | — | OLD = r4n fb6711ef, NEW = r4q 8c81e6b5 |

## Lệnh owner (Oracle), theo thứ tự
1. **Kiểm, không ghi gì:** `DRY=1 bash ~/claude_master/v12/c3live/ops/c3live/swap_v12_dry_jar.sh`.
   Đã chạy 11-05 13:03 trên 242 thật: DRY PASS, HAS_C11=0, LEGACY 44, latch NONE.
2. **Thay jar:** `bash ~/claude_master/v12/c3live/ops/c3live/swap_v12_dry_jar.sh`, chạy trong khung :10–:44 và gõ YES.
   - Thêm C11, không seed.
   - Hậu kiểm trượt thì tự rollback về r4n.
3. **Dry r4q smoke ≥ 24 h** trước micro, theo A1 R4PQ:
   - 0 KHẨN, latch NONE;
   - có `PREMARKET=` / `premarket_bo=`;
   - 0 lỗi tickCosts.
   - Ngày swap tính là XÁM (ADD6/ADD10).
4. Sau đó mới tới gate G-MICRO, với `jar_md5=8c81e6b560b61e7d43ca32c4a50ec926`, rồi `golive_micro_on.sh`.

## Weight REST trên IP 242 (sửa số cũ)
- Số "LEGACY ~1 300/phút" (đối chứng trước QF3, PREREG_INGEST_QUICKFIX Q5) đã **lỗi thời**.
  - Sau INGEST-QF3, collectData có ngân sách cứng ≤ 300/60 s.
  - Header `X-MBX-USED-WEIGHT-1M` là con số của **cả IP** (collectData + v_t_m dry/LEGACY).
- **Số đo** từ dòng `[REST-BUDGET]` của collectData trên 242, chỉ đọc, 31/10 12:31 → 05/11 12:52, n = 7 185 phút:

| khoảng | weight tự đếm (TB / p99 / max) | header cả IP (p50 / p99 / max) | 429 / 418 |
|---|---|---|---|
| 01–05/11 (6 500 phút) | 85 / 87 / 211 | 90 / 95 / 216 | 0 / 0 |
| 31/10 (685 phút, ngày triển khai QF3) | — | 90 / 95 / 732 | 0 / 0 |

- Theo ngày, header p99 ở mức 95 mọi ngày từ 01 đến 05/11. Đỉnh 216 rơi vào 05/11, khi restart.
- Kết luận cho A1 R4PQ MIN (sập + rớt stream):
  - Bù phí c3 tối đa ≈ 24 leg × 5 weight / 15 s ≈ 480/phút.
  - Cộng nền IP ~85–110/phút, tổng ≈ 600/phút, cách xa trần 2 400.
- Giới hạn: từ khi có QF3 chưa có đợt sập nào, nên chưa đo được weight LEGACY trong ngày sập.
