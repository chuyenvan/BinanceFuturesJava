# c3_ops_lev1x - dat leverage 1x universe c3 tren tai khoan CON (SUB)

Repo rieng (nhanh v1.2/ops-lev1x), KHONG sua ops6. Script `golive_set_lev1x.sh` chay tren ORACLE boi OWNER, sau A1.

Muc dich: `golive_check_lev.sh` (ops6 082c10f5) ra `KET QUA: DAT` that -> `golive_make_gate_pilot.sh` nhan LEV_EV.
Tk con: symbol chua tung giao dich o leverage mac dinh 20x (jar AccountModeGuard.java:218-222 chi dat 1x truoc leg dau).

## Lenh owner (Oracle, tmux), <SHA> = sha256 MASTER/A1 cap
    A1_LEV1X_APPROVED=<SHA> bash ~/claude_master/w3/c3_ops_lev1x/golive_set_lev1x.sh
    A1_LEV1X_APPROVED=<SHA> DRY=0 bash ~/claude_master/w3/c3_ops_lev1x/golive_set_lev1x.sh
    LEV_CAP=5000 bash ~/claude_master/w3/c3_ops6/ops/c3live/golive_check_lev.sh

DRY mac dinh (chi DRY=0 moi ghi, phai go CHINH XAC `YES LEV1X` trong 300 s). DRY=0 bi TU CHOI o phut :58-:02 va :29-:31 (gio Oracle).
Ma thoat 0 DAT | 3 con symbol != 1x | 4 CANH BAO (leverage xong, con marginType != CROSSED / maxNotional < 4 x 0,0225 x LEV_CAP) | 1 TU CHOI/DUNG.
Ket qua: `~/claude_master/deploy/lev1x/LEV1X_SUB_<TS>.txt`; log `~/claude_master/deploy/golive_set_lev1x_<TS>.log`.

## Chot chan
- `A1_LEV1X_APPROVED` = sha256 file script. Script copy chinh no vao `mktemp -d /tmp/lv1x_run.*` (700, file 500), kiem sha256 BAN COPY
  roi `exec` ban copy (sua file goc trong luc chay khong anh huong); thu muc copy bi xoa khi thoat.
- Bien noi bo `_LV1X_*` dat san tu env -> tu choi. Bo loc output (token/signature/APIKEY/hex64) luon bat.
- Che do that: cam ghi de qua env SSH_242 SCP_242 APP_DIR PROC_PAT ING_PAT KEYS_FILE PY242 CURL242 SUB_KEY_SHA8 MAIN_KEY_SHA8 LOGDIR GL_TEST
  GL_SSH_* WD_PAUSE LV1X_TEST_*; C3_ACCOUNT chi SUB. LV1X_W_MAX trong [300, 1200].
- ops6 ghim: HEAD 082c10f5, ops/c3live sach, md5 golive_lib.sh = 5d0febd2..., gl_manifest_check -> source lib (chi dung ham).
- Tai khoan: file key bot dang dung = /root/.config/c3live/keys_sub.env; sha8 key file = 43820b5b (SUB), != 3ef771e0 (MAIN).
  Python tren 242 kiem LAI sha8 key doc duoc == pin SUB va != pin MAIN TRUOC call dau tien (ca phien doc lan ghi) -> sai: ERR KEY_PIN, 0 request.
  Python doc key cung quy tac lib bash (dong neo ^C3_LIVE_API_KEY=, dung 1 dong KEY + 1 dong SECRET, quyen 600).

## Hanh vi
- Doc (95 weight): v3/account, v1/symbolConfig, v3/positionRisk, v1/openOrders, v1/openAlgoOrders. Universe = run/c3live_exchangeInfo.json
  (TRADING/USDT/PERPETUAL) nhu check_lev. Bao N_LEV, N_MARGIN, N_MAXNOTIONAL (cung cong thuc check_lev, LEV_CAP mac dinh 5000).
- Ten symbol non-ASCII (chu Han): query = urllib.parse.quote(symbol, safe='') UTF-8, ky HMAC tren DUNG chuoi da encode se gui (giong jar
  C3LiveClient: URLEncoder UTF-8 roi ky). Moi ten symbol in / truyen Oracle<->242 o dang percent-encode.
- Ghi: POST /fapi/v1/leverage leverage=1 (weight 1) cho symbol universe lev != 1, KHONG vi the, KHONG lenh mo, nam trong ke hoach owner
  da xac nhan. Symbol ASCII truoc, non-ASCII SAU CUNG. KHONG dong marginType / maxNotional (chi bao), vi the, lenh, symbol ngoai universe.
  Idempotent. In W_PRE (X-MBX-USED-WEIGHT-1M) truoc POST dau.
- Nhip >= 0.25 s/goi (LV1X_PACE_S, >= 0.2). X-MBX-USED-WEIGHT-1M >= 600 (LV1X_W_MAX) -> ngu toi phut sau (in trang thai moi <= 25 s),
  tong <= 240 s (LV1X_WAIT_MAX_S) roi DUNG. POST dung khi toi phut cam ke tiep. 429/418/-1003 -> DUNG NGAY (moi symbol).
  Symbol ASCII: -2014/-2015/-1022 hoac 5 loi lien tiep -> DUNG; loi khac -> ghi, tiep. Symbol non-ASCII: loi (tru 429/418/-1003) -> KHONG
  dung, ghi, cuoi in khoi `CAN LAM TAY: <goc> (<encode>) - owner dat 1x bang tay tren app Binance (tai khoan con)`.
- Cuoi: doc lai symbolConfig -> DAT chi khi N_LEV = N_MARGIN = N_MAXNOTIONAL = 0; chi con 2 loai sau -> CANH BAO; con lev -> CON.
- Key khong roi 242: python /opt/c3py tren 242 doc keys_sub.env, ky HMAC, goi curl -K - (stdin) tai cho; Oracle chi nhan dong KEY=VAL.

## Test
    bash test/test_set_lev1x.sh      # 63 ca (~3 phut), sandbox /tmp, 242 gia (bash -c), san gia (fake curl kiem HMAC tren query encode),
                                     # FAPI .invalid + proxy 127.0.0.1:9; gio gia LV1X_TEST_NOW_EPOCH (CHI hieu luc khi LV1X_TEST=1)
