# LEV1X_DEV2 - golive_set_lev1x.sh v2 sau A1_LEV1X (DEV, 2026-11-25)

Repo ~/claude_master/w3/c3_ops_lev1x nhanh v1.2/ops-lev1x (KHONG push). Commit 9d7beae6a2b81b6139d0471f1a19e73a0db37121 (cha e0a8310d).
golive_set_lev1x.sh sha256 = 9860c34f2b01432c5f0a12071c8dd4da3ba0f131003ca6e29d17cada08ca6e07
diff --stat e0a8310d..HEAD: README_LEV1X.md 36, golive_set_lev1x.sh 391, test/test_set_lev1x.sh 173 (459+, 141-).
Test: 63/63 PASS, chay 3 lan (lan 1 co 3 FAIL do loi TEST quen reset calls.log - da sua test, khong sua script). bash -n OK. shellcheck khong co.
Trailer commit: Opus 5.5 + Claude-Session (theo chi dan attribution cua he thong; model chay la Opus 5.5, khong dung trailer Fable).

## Sua (dong trong ban moi)
- B-1: python 242: enc()=quote(sym,safe='') (186); query 'symbol=<enc>&leverage=1', ky HMAC tren DUNG chuoi q se gui (call(), q phai
  ASCII hop le khac => Stop); moi ten symbol out() o dang encode; out() ghi bytes ASCII (khong phu thuoc LANG; python -I bo qua
  PYTHONIOENCODING nen khong dung bien do), file doc encoding utf-8. Oracle kiem PLAN ^[A-Z0-9%,]*$ (85, lop ky tu viet tuong minh,
  khong phu thuoc locale). Phien ghi: moi phan tu ke hoach phai thuoc {enc(x): x in universe exchangeInfo} va ^[A-Z0-9%]+$, khac =>
  ERR, 0 POST. non-ASCII POST SAU CUNG (306); loi o non-ASCII (tru 429/418/-1003, van DUNG NGAY) => ERRSYM + MANUAL, khong tinh loi lien
  tiep, khong abort (345); cuoi in "CAN LAM TAY: <goc> (<encode>) ... - owner dat 1x bang tay tren app Binance (tai khoan con)" (414),
  ma thoat 3. DRY liet ke non-ASCII trong ke hoach (dang goc + encode, giai ma bang python3 tren Oracle chi de hien thi).
- Jar (c3_hotfix 76134a52 C3LiveClient): enc() = URLEncoder.encode(UTF-8).replace("+","%20") (dong 610), ghep query da encode +
  recvWindow + timestamp roi signer.sign(q) (dong ~520-524; HmacSigner ky payload.getBytes(UTF_8)) => jar ENCODE ROI KY, giong script.
  Khac biet chi o '*' '~' (khong xuat hien trong ten symbol) va thu tu recvWindow/timestamp (khong anh huong chu ky).
- M-1: python kiem sha8 key doc duoc == pin SUB va != pin MAIN NGAY sau doc key, TRUOC call dau (ca read va write) => ERR=KEY_PIN,
  END_API, exit 3, 0 request (207). Pin = hang trong script (che do test moi duoc LV1X_TEST_SUB/MAIN_SHA8). Oracle in "ERR KEY_PIN".
- m-1: python doc key = quy tac lib gl_state242: quyen 600, dong neo ^C3_LIVE_API_KEY= / ^C3_LIVE_API_SECRET= (khong strip dau dong),
  bo ' \t\r"'; them: dung 1 dong KEY + 1 dong SECRET (196). (Lib KEYS_OK chi dem tong = 2 -> python chat hon, cung chieu fail-closed.)
- m-2: N_MARGIN + N_MAXNOTIONAL: CM = 4*0.0225*LEV_CAP (258), maxNotional bo qua ''/None/^INF, so tien to kieu awk (khong so => 0) < CM
  = golive_check_lev.sh:45-49; LEV_CAP mac dinh 5000 (kiem so > 0). DAT chi khi lev=0 & margin=0 & maxn=0 & co cfg (lv_final 439);
  chi con margin/maxn => KET QUA: CANH BAO, ma 4, liet ke symbol. Script KHONG sua 2 thu nay.
- m-3: ban goc tu choi neu co bat ky bien env _LV1X_* (35); khong con _LV1X_MASKED/_LV1X_DEPTH; bo loc output = exec > >(sed) (74),
  luon bat, khong co co bo qua.
- m-4: ban goc: mktemp -d /tmp/lv1x_run.XXXXXXXXXX (700), cp -> 500, sha256 BAN COPY == A1_LEV1X_APPROVED, token 128 bit (.tok 400),
  exec env _LV1X_STAGE=copy ... bash <copy>. Ban copy (55): kiem duong dan dung mau, $0 = copy, khong symlink, chu/quyen 700/500,
  token khop, sha256 lai; chi SAU do moi dat trap xoa thu muc (thu muc la khong bi xoa). Duong dan ops6 tuyet doi => khong vo.
- m-5: IFS= read -r, so sanh chinh xac 'YES LEV1X' (464).
- m-6: nap(): ngu theo khuc <= 25 s, moi khuc 1 dong WAIT=..._con_Ns (211); Oracle stream dong WAIT/CHG/ERRSYM/MANUAL/STOP/W_PRE ca phien
  DOC va GHI (lv_run).
- Them: W_PRE=<X-MBX-USED-WEIGHT-1M> truoc POST dau + throttle (332); Oracle in W_USED_1M phien doc truoc khi ghi. LV1X_W_MAX [300,1200]
  (113). DRY=0: phut Oracle trong {58,59,00,01,02,29,30,31} => TU CHOI + gio nen chay lai (lv_window 125), kiem luc dau VA sau 'YES';
  them deadline = dau phut cam ke tiep, python dung truoc POST neu qua (het_khung_gio, 335). DRY khong bi chan. Gio tiem
  LV1X_TEST_NOW_EPOCH chi che do test (che do that: bien cam).
- set -euo pipefail (truoc: -uo); gl_read_state goi '|| :' (ham lib ket thuc 'grep && die' tra 1 khi KHONG loi) + kiem lai END_STATE (158).
- Giu: DRY mac dinh, A1_LEV1X_APPROVED, YES 300 s, danh sach env cam (them LV1X_TEST_*), curl -K - stdin, chi POST /fapi/v1/leverage
  leverage=1 hang, bo qua vi the/lenh mo, idempotent, ops6 HEAD/sach/md5/manifest, 1 ssh s242in_once cho ghi.

## Test (33 ca cu GIU NGUYEN dieu kien kiem; doi chung: fake curl kiem query encode chuan + HMAC tren chuoi nhan duoc; E() tiem gio :10)
Ca moi 32-60: _LV1X_MASKED / gia _LV1X_STAGE / ban copy 755 => tu choi; TOCTOU (ghi de file goc tai cho luc cho YES => van DAT,
khong TAMPERX, thu muc copy da xoa); ' YES LEV1X' / 'YES LEV1X ' => tu choi; phut :59 / :30 DRY=0 => tu choi 0 request (goi y :03/:32);
:30 DRY chay; LV1X_TEST_NOW_EPOCH o che do that => tu choi; deadline 28:25 nhip 5 s => het_khung_gio 0 POST; W_MAX 299/1201, LEV_CAP=abc;
M-1 doi file key giua 2 phien (key khac / key = pin MAIN) => ERR KEY_PIN, 0 POST, phien ghi 0 request; key = MAIN => 0 request;
m-1 dong KEY thut le (python bo qua nhu lib) / 2 dong KEY (tu choi); maxNotional 400 => CANH BAO rc 4, LEV_CAP=1000 => DAT; ISOLATED
=> CANH BAO; ghi con maxn => CANH BAO + W_PRE; chu Han: DRY liet ke + thu tu; ghi san chap nhan => DAT; -1022 non-ASCII => CAN LAM TAY
rc 3, ASCII xong; MUTANT ky tren unquote(q) => san gia bat -1022 (chung minh test kiem chu ky that); 429 non-ASCII => DUNG; m-6
weight 700 => 3 dong WAIT / 53 s. Cuoi: khong lo key/secret/sig/hex64, khong con /tmp/lv1x_run.*, bash -n.

## Hanh vi moi owner can biet
- Ma thoat 4 = CANH BAO (lev xong, con marginType/maxNotional); 3 = con lev (gom ca CAN LAM TAY); DAT moi kem dieu kien margin/maxn.
- DRY=0 bi tu choi o phut :58-:02 va :29-:31; neu dang ghi ma toi phut cam => DUNG (chay lai = idempotent).
- Ten symbol tren man hinh o dang percent-encode (vd %E5%B8%81...USDT); khoi CAN LAM TAY co ca dang goc.
- Bien _LV1X_* trong shell => tu choi (unset). Can /tmp ghi duoc.

## Lenh owner (Oracle, tmux)
DRY : A1_LEV1X_APPROVED=9860c34f2b01432c5f0a12071c8dd4da3ba0f131003ca6e29d17cada08ca6e07 bash ~/claude_master/w3/c3_ops_lev1x/golive_set_lev1x.sh
THAT: A1_LEV1X_APPROVED=9860c34f2b01432c5f0a12071c8dd4da3ba0f131003ca6e29d17cada08ca6e07 DRY=0 bash ~/claude_master/w3/c3_ops_lev1x/golive_set_lev1x.sh
SAU : LEV_CAP=5000 bash ~/claude_master/w3/c3_ops6/ops/c3live/golive_check_lev.sh

## A1 can soi
- Stage A -> B (token/quyen/duong dan) va trap xoa chi sau khi xac minh; exec > >(sed) + wait trong trap (output du khi thoat).
- set -e moi: cac ham lib goi trong ngu canh '||' (s242in, gl_read_state || :) - da test, nhung doc lai duong ghi.
- awknum vs gawk (gawk khong nhan hex/inf mac dinh; Binance tra chuoi so) - lech chi o gia tri la.
- Deadline dung dong ho 242 so voi epoch Oracle (lech NTP nho).
- Symbol co ky tu ngoai A-Z0-9 nhung ASCII (vd '_', chu thuong) => PLAN regex DIE ca DRY (fail-closed, khong co trong universe hien tai - chua kiem du lieu that).

## KHONG kiem duoc (suy doan)
- Phan hoi that cua Binance voi symbol non-ASCII (chap nhan query encode + chu ky tren chuoi encode?) - chi dua tren cach jar lam;
  vi vay co duong CAN LAM TAY. symbolConfig co tra symbol chua cau hinh; maxNotional o 1x; gioi han rieng /fapi/v1/leverage;
  python /opt/c3py tren 242 (phien ban, chi dung stdlib 3.x: urllib.parse, sys.stdout.buffer) - KHONG ssh 242 kiem.
