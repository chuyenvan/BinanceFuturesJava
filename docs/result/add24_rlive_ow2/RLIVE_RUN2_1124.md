# ADD24 R-LIVE luot chinh thuc #2 (ERRATA6) - bao cao RUN (agent Opus), 2026-11-24
CHI GHI NHAN, KHONG dien giai / KHONG ket luan dat-truot (MASTER quyet).

## Preflight (run_rlive_e6.sh a66109c12220de59ed8d5b065d33d0eb8875d5bf, khong 'go')
- 17:28, 17:31, 17:34, 17:37, 17:40, 17:44, 17:48, 18:03: DAT 17 / TRUOT 1 (Vision) - THIEU 3: klines 1m 2026-11-23 XPLUSDT, ZESTUSDT, ZORAUSDT (404).
- Giua cac lan: vong HTTP HEAD chi 3 file tren moi 60 s (ghi progress), 404 toi 17:59.
- 18:04:07 PREFLIGHT_OK: DAT 18 / TRUOT 0; VISION requests=5170 non200=0.
- Moi lan deu co CANH BAO watcher parity watch_daily_v12.sh pid=936196 song. Kiem: d/2026-11-22/DONE co; watcher chi cham 11-23 khi co
  pull242/2026-11-24/COMPLETE (chua co) => khong tranh oracle_heavy.lock trong luot nay. (Dieu kien A1 "chay sau khi watcher cham xong 11-23"
  hieu theo muc dich m5 = tranh trung lock; theo nghia den thi chua dap ung - xem Diem khong chac.)

## Lenh + thoi gian
- 18:04:53 `bash ~/claude_master/w3/add24/run_rlive_e6.sh a66109c12220de59ed8d5b065d33d0eb8875d5bf go` (preflight lai OK 18:04:53, script tu nohup, pid 3314818).
- START 2026-11-24T18:04:53+07:00 ; EXIT_CODE=13 END 2026-11-24T18:15:33+07:00.
- Dong khoa moi (a/OFFICIAL_ADD24_RLIVE.lock, sha256 sau ghi 9e1cd8973c4b659347df05109710ab392e7a81c9f58f68ce155c5a49d7aca0dd):
  2026-11-24T18:04:54+07:00 head=a66109c1 a1=a66109c12220de59ed8d5b065d33d0eb8875d5bf p1=e451154e errata=E6 exinfo_sha256=dcfa03c72c38a658e7de7df812e876bbca903f9e0dfd81ab02b1aeb61f3a1684 out=/dev/shm/add24/rlive_official_1124_180454
- Log: v12/rlive_1124_run2.log (21 dong) sha256 dcc07f473e95c260e0076058cd358337d24e874ca5b19c89d693886edb1ff6a3.

## Dien bien (theo log)
build_wt RC=0; live_log_parse files=7 unique_lines=324125; fixture OW2 xong tcut=2026-11-24 07:00 miss_k=0 miss_m=0;
buf_check pre ok=true (same_n_pre, same_sha_pre, no_bad_chunk, monotone, no_wallclock_trim = true);
lane L0, L0-FOLLOW, L0-DRY, L-10K: RC=0; buf_check post ok=true (4 lane true);
gates: {"V1": true, "V2": true, "V3": true, "V4": true, "V4b": false, "V5": true, "V6": false, "V7": true, "V8": true, "V10a": false, "ok": false}
"CONG V truot => KHONG cham (sua dau vao bang errata)" => exit 13. KHONG co score / conclusion (dung truoc buoc cham);
KHONG co thu muc keep a/rlive_official_* (cp nam sau exit 13). Moi output CHI o /dev/shm (de mat khi reboot).

## Cong V (chep tu gates.json / v4b.txt / v10.txt / V10.json)
- V1 ok=true n=64 (sha256 dau vao; fx/exinfo.json = dcfa03c7...1684)
- V2 ok=true missing_n=0
- V3 ok=true violations=[] lookback_allowed_ms=86400000 lookback_from 2026-11-18 09:31 +07
- V4 ok=true parsed=24 grep=24
- V4b ok=false unmatched=1 bad_rules=[] ; v4b.json unmatched_by_shape {"[C9-LIVE-EQ] doc income FUNDING_FEE loi": 1}; rules 46
- V5 ok=true (moi lane: banners du, net_lines 0, jar_md5 cf0f4792...1866, errors 0, violations 0)
- V6 ok=false: L0 minutes 6773 expect 7049 errors 0; L0-FOLLOW 6773/7049/0; L0-DRY 6773/7049/0
- V7 ok=true files_with_java_hint=[]
- V8 ok=true (V8.json)
- V10a ok=false: domain_minutes 6770, V10a_mismatch_minutes 555, live_records 136866, rig_records 137601, outside_n 0,
  live_buffer_bad_frames 0, V10a_first[0]=1795239060000 (20 phan tu dau trong V10.json)

## Quy tac may kiem ERRATA6 muc D (M2)
Lenh dung nhu errata tren $OUT/gates.json => rc=1. Tap cong ok=false = ['V10a', 'V4b', 'V6'] (KHONG phai chi V10a)
=> theo errata: "Exit 13 voi cong khac truot => thu tuc cong V (errata dau vao)". Khong ap ERRATA5 B(ii). MASTER/A1 phan xu.

## manifest_ow2.json
excluded_not_live_ingest: 5 symbol ???USDT, ????USDT, ?????USDT, ??USDT, ??USDT
missing klines/mark = [] ; missing_unexplained = [] ; symbols_klines 517 ; symbols_mark 27 ; udays 2026-11-19..2026-11-23

## Output /dev/shm/add24/rlive_official_1124_180454 (sha256)
gates.json 562e6792e1f7155f586840fdae31d9da5c5d144ca7138127b2e4c47e274b57c8
gates.txt 6533b4d9a00cbd50fcc43cb49637c54dff73a3d5629e20d635c309e7e5d73715
V8.json 115e80d68f34a69e4e10958d8546d259f0cef3bc7adbaaa6a83b9e1918a5d92b
V10.json 45cb089c0d92bb23171dcca03c479a891c2183f21c5aa3d911fc0eefee1cafb4
V10_diag.json 15f618b0c964cc4cedd78f68abf72f16be84f7d487846e9bb6ca196bf0b05ffc
buf_pre.json 0ba10065c49828d49e9dbb196386ffa452048d90599147f8bf924d45d706e197
buf_post.txt 44aa518347a1e16a8b9357fa0169e0f8d92eb2b1120df167ccf8d99f40d4563d
fx/manifest_ow2.json d5d8910749c96ca1a306438de9146bf49c079c6ca7676004db348d71719735ef
fx/manifest.json bc217f040cd9912e9d217706c22539423ba9c7df325566a4077ff73f39a2e452
Khac: L0, L0-FOLLOW, L0-DRY, L-10K (result.json, run.log, ...), fx/, live/, v4b.json, v4b.txt, v10.txt, run_all.txt, fx_exinfo.json.gz.

## WARNING / ERROR
Log chinh: 0 dong warn/error/exception/traceback. run.log lane: WARN 9/10/9/9 dong (banner khoi dong: GATE-RATIO, MINUTE-FIN, E2E_V12,
C3-LIVE-SCOPE, TS-EXT...), ERROR/Exception 0.

## Diem KHONG chac / can MASTER xu ly
1. Khoa da ghi errata=E6 => KHONG chay lai (agent da dung).
2. Output chi o /dev/shm, chua sao ve a/ (agent khong duoc ghi). Nen sao luu truoc moi viec / reboot.
3. Dieu kien A1 ve watcher: watcher song nhung khong the cham 11-23 hom nay (can pull242/2026-11-24/COMPLETE); agent coi la khong xung dot lock.
4. Agent khong mo noi dung lane (fills/legs/result) ngoai cac truong buffer + dem dong WARN; khong tinh PnL.
