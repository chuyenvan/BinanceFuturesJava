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
