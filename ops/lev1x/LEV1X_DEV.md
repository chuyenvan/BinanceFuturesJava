# LEV1X_DEV - golive_set_lev1x.sh (DEV, 2026-11-25)

Repo: ~/claude_master/w3/c3_ops_lev1x (nhanh v1.2/ops-lev1x), commit e0a8310d871b0b776d6add1b2a4a175c6989d1f4 (chua push).
Files: golive_set_lev1x.sh, test/test_set_lev1x.sh, README_LEV1X.md.
sha256 golive_set_lev1x.sh = 111c17678a336fa372d270904f9bd0fa105fbd7230eccf170a7f1b59cbb8cf41
Test: 33/33 PASS (bash test/test_set_lev1x.sh). bash -n OK. shellcheck KHONG co tren Oracle (khong chay duoc).

## Thu tu script
1 sha256 file == A1_LEV1X_APPROVED; 2 che do that cam ghi de env ket noi/tk (SSH_242 APP_DIR KEYS_FILE PY242 CURL242 SUB_KEY_SHA8 ... ),
C3_ACCOUNT chi SUB; tham so nhip/nguong co gioi han; 3 loc output (re-exec qua sed: token TG, signature=, X-MBX-APIKEY, hex64);
4 ops6 ghim: HEAD 082c10f5, ops/c3live sach, md5 golive_lib.sh 5d0febd23158acc52e2fe116c2f60ba8, gl_manifest_check(check_lev) -> source lib;
5 gl_init log + flock deploy/lev1x/.lock; 6 gl_read_state (chi doc 242): LIVE_C3_KEYS_FILE cua bot (env process; bot dung -> env.sh)
== /root/.config/c3live/keys_sub.env, KEYS_OK, sha8 key file == 43820b5b != 3ef771e0; 7 doc san (95 weight) + sha8 key ky == SUB;
in universe/phan bo/lev!=1 (ds)/margin!=CROSSED (ds, chi bao)/vi the/lenh mo/bo qua/ke hoach/uoc weight-thoi gian;
8 DRY -> thoat (0 neu 0 symbol != 1x, 3 neu con); DRY=0 -> 'YES LEV1X' 300 s; 9 1 ssh (s242in_once): doc lai, POST leverage=1
cho (ke hoach moi) giao (ke hoach da xac nhan); 10 doc lai symbolConfig -> KET QUA DAT(0)/CON n(3)/DUNG(1); file deploy/lev1x/LEV1X_SUB_<TS>.txt.

## Tai dung ops6 (SOURCE, khong chep): golive_lib.sh gl_init 173-180, say 181, die 258, s242in 297-308, s242in_once 309,
gl_state242 472-517, gl_read_state/sv 519-524, gl_manifest_check 67-81. Python ky/goi API = CHEP + mo rong tu gl_api242 885-922
(doc key, call() HMAC + curl -K - + x-mbx-used-weight-1m), universe 1065-1072 (them POST, throttle, Stop 429/418/-1003).

## Lenh owner (Oracle, tmux)
DRY : A1_LEV1X_APPROVED=111c17678a336fa372d270904f9bd0fa105fbd7230eccf170a7f1b59cbb8cf41 bash ~/claude_master/w3/c3_ops_lev1x/golive_set_lev1x.sh
THAT: A1_LEV1X_APPROVED=111c17678a336fa372d270904f9bd0fa105fbd7230eccf170a7f1b59cbb8cf41 DRY=0 bash ~/claude_master/w3/c3_ops_lev1x/golive_set_lev1x.sh
SAU : LEV_CAP=5000 bash ~/claude_master/w3/c3_ops6/ops/c3live/golive_check_lev.sh

## Uoc (universe 242 = 522 symbol TRADING/USDT/PERPETUAL, dem 25/11; ~24 da 1x theo PILOT_DAY_1126 => ~498 POST)
DRY: 95 weight, vai giay. THAT: 95 (DRY trong lan chay) + 95 (doc lai) + ~498 (POST x1) + 5 = ~690 weight trong ~2,5-4 phut
(0,25 s/goi + do tre curl); toc do script <= 4 req/s ~ <= 240 weight/phut; nguong dung 600/phut tinh CA bot (IP chung).

## Jar (c3_hotfix 76134a52, AccountModeGuard): cache CHI giu symbol OK (prefetchedOk, nap lai moi gio; clearedSymbols);
symbol 20x KHONG bi cache la "sai" -> leg dau goi REST symbolConfig, thay 1x -> OK, khong setLeverage. Doi 20x->1x tu ngoai KHONG lam
jar hieu sai, KHONG can restart. Jar cung POST leverage qua query string, body rong (C3LiveClient:444,527-529), W_SET=1 - khop script.

## Rui ro / A1 soi
- Race: bot vao symbol trong luc chay -> jar tu dat 1x truoc leg dau; POST 1x cua script trung gia tri (vo hai). Script khong kiem lai
  vi the tung symbol truoc POST (chi theo anh doc dau phien ghi).
- Chua chac: POST /fapi/v1/leverage co gioi han rieng ngoai weight 1 hay khong (vd dem vao order-rate) - toi khong xac minh duoc.
- Chua chac: symbolConfig co tra moi symbol hay chi symbol da cau hinh; symbol thieu cfg -> script KHONG dong (check_lev cung khong tinh).
- Cho weight luc DOC (DRY) im lang toi 240 s (dong WAIT chi hien o phien ghi).
- Khong ap khung gio gl_time (doi leverage khong dong bot); A1 quyet co can.
- Re-exec loc output dung PPID; log gl_init ghi TRUOC bo loc (nhu check_lev) - python khong in key/sig.
- Ssh dut giua phien ghi -> KET QUA DUNG (chua ro), chay lai = idempotent.
