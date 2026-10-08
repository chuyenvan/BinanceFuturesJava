# DEPLOY_SHADOW2_K24_20261008 — shadow #2 (K24 + GATE_QUOTA_SKIP_WHEN_FULL, paper, Oracle)

- **Ngày:** 2026-10-08. **Người làm:** agent dựng shadow #2 (MASTER giao, owner duyệt 10-05 "shadow #2 = K24 + skipFull", 10-08 "chủ động triển khai shadow").
- **Plan:** `docs/runbooks/SHADOW2_K24_SKIPFULL_PLAN.md` §2 T3–T10, §3, §4 (G2 rút gọn — MASTER chốt: CHỈ dữ liệu sạch ≥ 2026-10-01 13:00 +07), §5.
- **Phạm vi chạm:** tạo `~/shadow_c3b`, unit `shadow-c3b` + `shadow-c3b-redis` (Oracle). 242: CHỈ ĐỌC (tar predictionSymbol/prediction 20261001..08, grep env). Shadow #1 (`~/shadow_c3`, `shadow-c3*`): chỉ đọc (copy bin/conf/env.sh/config/redis.config/logback, symlink `storage/ai_ml_data`). Không sửa .java, không build, không sim.
- **Script/đầu ra:** `~/claude_master/1008_s2/` (`s2_pull.sh`, `s2_build.sh`, `s2_setup.sh`, `s2_redis.sh`, `s2_check.sh`, `*.out`, `build_k24.json`, `buffer_k24.bin(.report.json)`, `buffer_k16.bin(.report.json)`).

## 1. Jar
- `~/shadow_c3b/app/target/binance-java-sdk-1.2.4.jar` = `~/claude_master/1005/shadow2/jar/…` sha256 **20d412e83dba15ff9320b02c011f37d36a99c66b9f8487ff32a73adc12e7b238** (khớp §7; KHÔNG dùng jar module mới có NSEL).

## 2. env.sh (§3)
- Copy `~/shadow_c3/app/conf/env.sh` (đã bật `LIVE_GATE_ROLLING_MODE=ratio / PCT=0.999950829 / DAYS=90` từ 10-08 14:26) rồi sửa. `diff <(grep '^export' #1|sort) <(grep '^export' #2|sort)` = **đúng 3 dòng**:
  `GATE_QUOTA_SKIP_WHEN_FULL=true` (thêm), `SELECTOR_RANK_TOPK=16→24`, `SHADOW_C3_DIR=/home/ubuntu/shadow_c3→/home/ubuntu/shadow_c3b`.
- Giữ: `LIVE_PROFILE=c3_shadow`, `SHADOW_NO_PUSH=true`, `LIVE_IS_SHADOW_HOST=true`, heap 3g, không `TRADING_PROFILE`. `grep shadow_c3[^b]|7301` trong `app/bin app/conf app/redis.config` = 0 dòng. `run/KILL_SWITCH` đã touch (dây lưng).
- Redis 7302 (`~/shadow_c3b/redis/redis-shadow.conf` = bản 7301 thay port/đường dẫn, maxmemory 512mb), 1-node cluster addslots 0..16383 ⇒ `cluster_state:ok`.

## 3. Buffer gate K24 (§4, G2 rút gọn)
- Nguồn: 242 `storage/data/{predictionSymbol,prediction}/20261001..20261008` (tar chỉ đọc, 1,1G, 14:31–14:32). Model net015 Oracle `/home/ubuntu/g3x26/g015x26_f15_cut20251231.onnx` md5 e65e683b = file 242.
- Tick/ngày: 1 440 (10-01: 1 439), **10-07 chỉ 875 tick** (242 không có tick 10-07 00:45→10:11 — cùng lỗ có trong buffer K16 thật của 242), 10-08 tới 14:30.
- `build_gate_buffer_k24.py extract` → `build --k 24` (now 14:47) → `trim_gate_buffer.py --cutoff "2026-10-01 13:00" --tz +07:00`.
- **K24:** n = **230 544**, firstTs **2026-10-01 13:00**, lastTs 2026-10-08 14:30 (7,06 ngày), armed (arm 10-08 13:00), q(h=15:00) = **0,0062053**; 57 chunk ≤4096, đọc lại bản ghi OK (CRC). sha256 `a0c27cadeee4dacfd33e2b54b58e7c7a7059cbd0f84a7cf6e1507f67b9a4c2fc` = `~/shadow_c3b/app/run/gate_ratio_live.bin`.
- **Đối chứng K16** (cùng khoảng, vs `~/claude_master/trim242_20261008/trim_final.bin` = buffer 242 đã trim, sha dbe12d63): 9 330 tick 242, missing 0, giải thích được (top-16 bỏ 0–3 hạng LEGACY, sai số < 1e-6) **9 312 = 99,81%** (unexplained 18); q(0,99995) cùng tick: 242 = tái tạo K16 = **0,006307358853518963 (trùng bit)**. Buffer K16 tái tạo đã trim: n 153 696, q(15:00) = 0,0063074 (= 242 trim). ⇒ ĐẠT (≥ 99%).
- q K24/K16 cùng cửa sổ (3 mốc 6h, sau arm): 0,984–0,986. Lệch còn lại như §4 (coin LEGACY: K24 tái tạo lấy hạng 1–24, live bỏ LEGACY rồi lấy tiếp).
- Khoảng trống 14:30 (cuối dữ liệu kéo) → 14:49 (start) không có r; live nạp tiếp từ start.

## 4. Start
- `shadow-c3b-redis` start 14:33 (PONG, `cluster_state:ok`, 1,53M). `shadow-c3b` start **2026-10-08 14:49:10 +07** (MainPID 2797258). Trước start: `date` 14:49 > firstTs+7d (10-08 13:00); RAM available 15G, đĩa trống 22G.
- `enable` cả 2 unit lúc 15:49 sau khi qua kiểm 60'.

## 5. Kiểm (10' lúc 14:51, 60' lúc 15:49) — `~/claude_master/1008_s2/check_2min.out`, `check_60min.out`
| Mục | Kết quả |
| --- | --- |
| Banner skipFull | `*** [GATE-QUOTA] LIVE SKIP_WHEN_FULL=ON` |
| Gate ratio | `*** [GATE-RATIO] LIVE BAT: mode=ratio pct=0.99995083 window=90d file=run/gate_ratio_live.bin`; `LIVE nạp buffer: size=230544 firstTs=20261001 13:00 (warm-up=armed)`; **0** dòng "seed lịch sử"/"khong nap duoc persist"/"TRƯỚC khi đủ 7 ngày" |
| q_t 15:01 | #2 **0,006205** (buffer 230 808 = 230 544 + 11 tick×24) vs #1 0,006307 (buffer 149 856) — khớp build (K24 0,0062053, K16 0,0063074) |
| Profile/push | `[LIVE_PROFILE=c3_shadow] BAT … SHADOW_NO_PUSH=true (hardcode)` |
| 242 | `[NO-WRITE-242] GHI Aerospike 242 BI TAT (LIVE_IS_SHADOW_HOST=true …)` |
| [GATE] | 60 dòng/60 phút, tất cả `topk=24`, `n_cand` max 24, tất cả có `n_skipfull= u=`; n_skipfull>0: 0 tick; u = 0,0000 (chưa có vị thế); vi phạm (skip>0 & u<0,6) = 0. #1 vẫn `topk=16` |
| Restart | NRestarts #2 = 0, #1 = 0 |
| Exception (journal) | #2: 62 × `BinanceClientException -2015` (key/IP không hợp lệ cho host paper, gọi positionRisk/account mỗi phút) + 1 × NPE `BudgetManager.updateBudget` lúc khởi động. #1 cùng cửa sổ: 64 × -2015 + 3 × NPE ⇒ **cùng mẫu với #1 (đã chấp nhận), không phải lỗi mới**. `full.log` Exception/OOM = 0. Tiêu chí "=0" của §5 viết theo nghĩa đen là không đạt với cả #1 ⇒ MASTER sửa tiêu chí thành "không có loại exception ngoài -2015/NPE khởi động". |
| Sổ | `~/shadow_c3b/ledger.csv` tạo 14:49; `lsof -p <#2>` mở file `~/shadow_c3/` = 0; process cwd `/home/ubuntu/shadow_c3b/app`; `/proc/<#2>/environ`: TOPK=24, SKIPFULL=true, SHADOW_C3_DIR=/home/ubuntu/shadow_c3b, LIVE_PROFILE=c3_shadow, SHADOW_NO_PUSH=true, LIVE_IS_SHADOW_HOST=true, LIVE_GATE_ROLLING_* như #1 |
| Tài nguyên | RSS #2 3 666 MB (≤ 4,3G), #1 3 828 MB; `free` available 11G (≥ 6G); redis 7302 1,53M (≤ 512mb); đĩa trống 22G |
| #1 | active, NRestarts 0, full.log cập nhật mỗi phút, ledger.csv không đổi (75 dòng) |

**Parity** (`SHADOW_DIR=/home/ubuntu/shadow_c3b PARITY_WORK=~/claude_master/1008_s2/parity live_vs_sim_check.py --fetch --probe`, 15:27, 242 chỉ đọc; `s2_parity.json`): overall FAIL như #1. Phân loại phía shadow:
- **A1** Configs khác B0 — 2 trường "chưa giải thích" = đúng `GATE_QUOTA_SKIP_WHEN_FULL` (sh=true) và `SELECTOR_RANK_TOPK` (sh=24); 6 trường còn lại giống 242. A1b (shadow vs 242) = 2 trường; A1c TOPK 16|24|16. ⇒ đúng 2 khác biệt được phép.
- **A2** FAIL là **lỗi script**: `live_vs_sim_check.py:1128` lấy MainPID cứng của `shadow-c3` (#1) ⇒ so environ #1 với env.sh #2 ⇒ lệch đúng TOPK/SHADOW_C3_DIR. Kiểm tay environ #2 = env.sh #2 (bảng trên). H3 cũng đọc PID #1.
- **C4** n_cand=24 (theo thiết kế K24). B5/B8/D1/D2/F7/F8/G1 `known=True` hoặc 242 cũng FAIL (cấu trúc, giống #1). B7 MISSING (script chỉ đọc buffer 242/#1). E5/E6 MISSING: chưa có lệnh/ledger.

## 6. Rủi ro / việc treo
1. Tiêu chí exception §5 cần viết lại (xem bảng). Parity script cần tham số hoá unit/PID (`SHADOW_UNIT`) để dùng cho #2 — chưa sửa (ngoài phạm vi).
2. Buffer K24 chỉ 7,06 ngày (G2 rút gọn) ⇒ q dao động theo cửa sổ ngắn cho tới khi tích luỹ; lệch LEGACY (§4) còn nguyên; lỗ 10-07 00:45→10:11 có ở cả buffer 242/#1.
3. RAM: available 11G sau #2 ⇒ chỉ đủ 1 job agent ≤ 8G (lock `oracle_heavy.lock`), không 2 job nặng song song. Đĩa trống 22G (ngưỡng dừng #2 < 10G). Dữ liệu kéo `~/claude_master/1008_s2/d242` 1,1G (cache tự tạo — có thể xoá).
4. Theo dõi tuần đầu: dòng `[GATE]` có `n_skipfull>0` phải kèm `u ≥ 0,6000` (prereg (iv)); timeout `AEROSPIKE_BATCH_*` ở cả hai shadow.
5. Rollback: `sudo systemctl stop shadow-c3b shadow-c3b-redis && sudo systemctl disable shadow-c3b shadow-c3b-redis` (giữ thư mục).
