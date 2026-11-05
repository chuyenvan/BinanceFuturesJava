# v1.2/c3-live — Round 4o: C11 env + script re-seed dry (chỉ ops)

- **C11:** `LIVE_SEED_EXCLUDE_DECISION_MIN=1` (`LiveFeaturePipeline:41-44` ghi "c3_live dat 1"; deploy 11-03 thiếu ⇒ log
  `[FEAT-PIPE] … =0 => race seed/tick dau sau restart (C11) VAN CON`). Thêm vào `ENV_ADD` của `deploy_v12_dry_r4.sh` + CHK env.
  Dry đang chạy: áp qua `restart_v12_dry_reseed.sh` (gộp với lần re-seed ADD6, 1 lần dừng LEGACY).
- **`ops/c3live/restart_v12_dry_reseed.sh`** (owner, Oracle): `SEED=<file> SEED_MD5=<md5>` hoặc `SEED=none` (chỉ C11); `DRY=1`.
  Kiểm seed md5 Oracle + 242; PRE chỉ đọc (1 process, jar r4n, env dry, env.sh chưa có GATE_BUFFER_SEED, `.seeded` chưa có,
  không PAUSE/canary/soak, RAM ≥ 1000 MB, LEGACY N, latch NONE, ADD6: 0 gate PASS / BIG_DOWN trong ~7 h); khung :10–:44; YES;
  env.sh backup + thêm dòng (seed = đường dẫn tuyệt đối `run/gate_seed_v12_<md5>.bin`); PAUSE token + tự gỡ; stop; backup
  `gate_ratio_live.bin` + md5; start; hậu kiểm (`[GATE-SEED] nap seed … md5`, không KHAN/BO QUA, `.seeded` md5, env process có
  C11 + seed, 0 cảnh báo race, latch NONE, 0 KHAN, `[GATE]` tick; LEGACY khác trước restart = WARN, không rollback); trượt ⇒
  ROLLBACK TỰ ĐỘNG (env.sh + gate_ratio md5, `.seeded` đổi tên, start lại dry như trước). Exit 0/1/2.
- fake242 §31 + toàn bộ: TEST PASS 271/271. DRY=1 trên 242 thật: SEED=none DRY PASS; SEED (file giả, chỉ chạy bước kiểm) DRY PASS.
- Mapper 242 (chỉ đọc, `client.get` từ Oracle, guard bật): n=951 gen=1314 maxId=967 **idTrung=0**, BTC=1 ETH=2 BNB=3, XUSDT không còn.

## 4o-B — gói GO-LIVE OPS tài khoản CHÍNH (GOLIVE_SCENARIO ADDENDUM 1, research/vz-e1 `90cd2e77`, viết TRƯỚC script)
Chỉ ops/test/docs; jar r4n `fb6711ef` không đổi. Thư viện chung `ops/c3live/golive_lib.sh` (đọc trạng thái 242, restart có PAUSE token
+ backup env + đổi tên sổ/trạng thái, rollback, hậu kiểm chung, gọi API chỉ đọc bằng key c3 qua `/opt/c3py` + `curl -K -`: key/secret
không vào argv, không in; chỉ in sha256(key)[:8]).
| Script | Làm gì | Chặn / tự rollback |
|---|---|---|
| `golive_check_key.sh` | GET `/sapi/v1/account/apiRestrictions` ký từ 242 | ĐẠT ⇔ HTTP 200 + enableWithdrawals=false + ipRestrict=true + enableFutures=true; ghi `gates/KEY_CHECK_<TS>.txt` |
| `golive_micro_on.sh` | dry → live, `C3_CAPITAL=1000`, push mở, key, C11=1; sổ/trạng thái dry (sổ, equity c3, đỉnh + latch nhãn dry) đổi tên `.dry_TS` ⇒ live bắt đầu sạch | gate `GOLIVE_GATE_MICRO.ok` có `jar_md5=` jar đang chạy; latch NONE; không `run/KILL_SWITCH`; key file; LEGACY mới. Hậu kiểm trượt: c3 chưa có lệnh ⇒ về dry; ĐÃ có lệnh ⇒ KHÔNG về dry, đặt `run/KILL_SWITCH` + KHẨN (exit 2) |
| `golive_pilot_on.sh` | `C3_CAPITAL` → `size` của gate | gate `GOLIVE_GATE_PILOT.ok` (`jar_md5=`, `size=`), `LEGACY_CUT_VERIFIED.ok` ≤ 24 h, LEGACY managed 0, owner gõ `YES DA CAT LEGACY`; trượt ⇒ về C3_CAPITAL cũ (adapter live, sổ giữ) |
| `golive_legacy_verify.sh` | chỉ đọc: vị thế ngoài sổ c3, lệnh/algo cid không `c3` trên sàn = 0 + log `[LEGACY] managed 0` ≤ 10′ | ĐẠT ⇒ ghi `gates/LEGACY_CUT_VERIFIED.ok` |
| `golive_monitor.sh` | 1 lệnh: env/push/KILL_SWITCH, latch + đỉnh, equity/HOURLY/recon, sổ c3, lệnh c3 1 h, LEGACY, stream, 429/418/ban, KHẨN/ERROR 1 h, exinfo, RAM | chỉ đọc |
| `golive_live_off.sh` | `MODE=drain` (đặt `run/KILL_SWITCH`, không restart) / `undrain` / `dry` (env về dry, sổ live `.live_TS`) | `dry` từ chối khi chưa drain, sổ c3 còn cụm, sàn còn lệnh/algo c3; trượt ⇒ về live (vẫn drain) |
- fake242 §32 (32 mục) + toàn bộ: **TEST PASS 301/301**. 242 thật DRY: check_key DRY PASS; micro_on DRY từ chối (chưa gate); với gate giả
  (thư mục tạm) mọi bước kiểm OK → DRY PASS; pilot_on từ chối (chưa gate); live_off từ chối (không chạy live); monitor chạy.
