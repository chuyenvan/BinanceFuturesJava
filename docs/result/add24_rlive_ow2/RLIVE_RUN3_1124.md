# ADD24 R-LIVE luot chinh thuc #3 (ERRATA7, LAN CHAY LAI CUOI) - bao cao RUN (agent Opus), 2026-11-24
CHI GHI NHAN (chep tu output harness). KHONG dien giai, KHONG ket luan thay MASTER. Khong chep so lai lo / equity (cac truong lien quan gia /
mean_delta bi luoc). blind/ KHONG mo.

## B0 - tam dung S2
- 20:20:57 kill -STOP 3360754 (cmdline xac nhan "bash code/s2_chain_v2.sh"; chi dieu phoi). Heavy con s2_heavy_v2.sh c0s7 tu chay xong
  (cooldown 180 s), thoat; 20:31:17 pgrep s2_heavy rong + oracle_heavy.lock ranh.
## B1 - preflight run_rlive_e7.sh 8d397ce2dbbdf3db72da9dd7bb4399866c675911
- 20:32:02 PREFLIGHT_OK lan dau: DAT 18 / TRUOT 0; Vision 5170 request non200=0. CANH BAO watcher parity pid 936196 song (watcher chi cham
  11-23 khi co pull242/2026-11-24/COMPLETE - chua co luc go).
## B2 - chay
- 20:32:50 `bash ~/claude_master/w3/add24/run_rlive_e7.sh 8d397ce2dbbdf3db72da9dd7bb4399866c675911 go` (preflight lai OK, nohup pid 3370341).
- START 2026-11-24T20:32:50+07:00 ; EXIT_CODE=0 END 2026-11-24T20:43:14+07:00.
- Dong khoa moi: 2026-11-24T20:32:51+07:00 head=8d397ce2 a1=8d397ce2dbbdf3db72da9dd7bb4399866c675911 p1=e451154e errata=E7
  exinfo_sha256=dcfa03c72c38a658e7de7df812e876bbca903f9e0dfd81ab02b1aeb61f3a1684 out=/dev/shm/add24/rlive_official_1124_203251
  (lock file sha256 sau: d1bccc4aa79c4f22fc81c0a61bf2340a3d5c2b27d401948cf153bdacd9022b96)
- Log v12/rlive_1124_run3.log (24 dong) sha256 5d4b1d61261ffb78081a258514dcb379fa37c41a74f481cf2d2dae92120fdaba.
- Dong log: build RC=0; parse files=7 unique_lines=324125; fixture miss_k=0 miss_m=0; buf_check pre ok (5 check true); 4 lane RC=0;
  buf_check post ok (4 lane true); "R-LIVE official xong head=8d397ce2 out=/dev/shm/add24/rlive_official_1124_203251
  keep=/home/ubuntu/claude_master/w3/add24/a/rlive_official_1124_203251 gates_rc=0".

## Cong V (gates.json)
{"V1": true, "V2": true, "V3": true, "V4": true, "V4b": true, "V5": true, "V6": true, "V7": true, "V8": true, "V10a": true, "ok": true}
- V4b: ok=true unmatched=0 bad_rules=[]
- V6: L0 / L0-FOLLOW / L0-DRY moi lane: minutes 6773, expect 6774, expect_window 7049, n_N1 275, n_last 1, errors 0, ok true
- V10a: domain_minutes 6769, mismatch 0, V10a_pass_eq 6215, V10a_pass_subset 553, V10a_pass_subset_trans 1, V10a_not_bitexact_minutes 554,
  V10a_fail [] (n 0). Rule: "ERRATA7: (1) L==R bit; hoac (2) L tap con bit cua R va symbol(R\L) == S_m (symbol chuyen trang thai m+-1 tu do)"

## Ket luan harness (conclusion.json, nguyen van tru truong gia)
{"gates_ok": true, "items": {"L0 L-E": "PASS", "L0 L-N": "PASS", "L0 L-S": "PASS", "L0 L-S2": "FAIL", "L0 L-K": "PASS", "L0-DRY L-E": "PASS",
"L0-DRY L-N": "PASS", "L0-DRY L-S": "PASS", "L0-DRY L-S2": "FAIL", "L-D": "INSUFFICIENT", "L-T": "FAIL", "L-SL": "FAIL", "L-X": "FAIL"},
"cover": {"C0b": "PASS"}, "R_LIVE": "FAIL", "warn": [], "rui_ro_A11": [6 muc: restart JVM khong tai hien (A11); N9 throttle 10 phut;
K7 khong kiem phia live; mau nho ~1 ngay vao lenh; U_MAX 0,60 (Configs.java:177); nguon so day/K3 qua [GATE] n_skipfull (ERRATA5)]}

## score (L0 | L0-DRY)
- L-E PASS: live 24, rig 24, matched 24, unexplained 0, order_minutes 3, order_mismatch 0 | giong
- L-N PASS: minutes_diff 0, unexplained 0 | giong
- L-S PASS: n 24 ok 24 fail 0 ins_no_px 0 (mark) | giong
- L-S2 FAIL: n 24, max_rel 0.000948, share_le_5e-4 0.375, n_gt_2e-3 0 | max_rel 0.000825, share_le_5e-4 0.583, n_gt_2e-3 0
- L-P (khong co trong items): n 24, median_bps 17.99, p90_bps 34.78, bao_owner_g_exec false | giong
- L-D INSUFFICIENT: live 0 rig 0 pairs 0 bad 0 | giong
- L-T FAIL: n_live 16 n_rig 16 same 6 n8 1 bad 13 live_only 4 rig_only 4 | giong
- L-SL FAIL: n_live 87 n_rig 58 ok 9 bad 130 mode_N7 0 live_only 78 rig_only 49 | n_rig 60 ok 7 bad 134 live_only 80 rig_only 53
- L-X FAIL: n_live 16 n_rig 16 reason_ok 12 same_min 3 n8 1 bad 16 deltas 12 live_only 4 rig_only 4 | same_min 4 bad 15
- L-K PASS: rig_errors 0, rig_latch false, rig_khan 0, live_4130 1, live_4130_replaced_le_2nhip 1 | giong
- labels: N1-N7 0, N8 2, N9 0, N12 0, UNEXPLAINED 159 | UNEXPLAINED 162
- V10b: checked true minutes 0 unexplained 0 | checked false; N9_phut 0; warn []; inherit_n ke_thua 0; u_max 0.6; cap 1000; apply_ratio on

## manifest_ow2.json
excluded_not_live_ingest = 5 symbol non-ASCII (nhu ERRATA6); missing / missing_unexplained rong; symbols_klines 517, symbols_mark 27.

## Output + sao luu
- /dev/shm/add24/rlive_official_1124_203251 (140 MB); keep harness: w3/add24/a/rlive_official_1124_203251 (conclusion/gates trung sha).
- Sao luu: v12/rlive_run3_backup_1124/rlive_official_1124_203251 (cp -a), v12/rlive_run3_backup_1124.sha256 (173 file; trung byte voi nguon)
  sha256 cua file .sha256 = 8a08140ba6284ca88466638d2599b8120acebc4790e18dde3d8eeb3085c763f1
- sha256: gates.json b526e9f3...980a; conclusion.json 03dd8cb3...efb7; score_L0/score.json d9f26d21...787b; score_L0DRY/score.json
  79fcf365...7619; V10.json ed10d944...a416; V10_diag.json ba666f3e...09b7; fx/manifest_ow2.json 6294ac76...eae3

## WARNING / ERROR
Log chinh: 0. run.log lane WARN 9/10/9/9 (banner khoi dong), ERROR/Exception 0.

## B4
20:43:36 kill -CONT 3360754 OK (stat Ss); s2_chain.log co dong moi 20:43:47 / 20:43:58 ("[c0s7] a3 dataset create").

## Diem KHONG chac
- Agent da luoc cac truong ten chua gia / ref_gia va L-X mean_delta (co the lien quan loi nhuan) - MASTER xem file goc neu can.
- Thoi gian STOP S2 ~23 phut (20:20:57 -> 20:43:36).
