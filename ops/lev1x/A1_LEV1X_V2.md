# A1_LEV1X_V2 - audit doc lap golive_set_lev1x.sh v2 (A1, Opus, 2026-11-25)

Doi tuong: commit 9d7beae6a2b81b6139d0471f1a19e73a0db37121 (cha e0a8310d), 3 file; golive_set_lev1x.sh sha256
9860c34f2b01432c5f0a12071c8dd4da3ba0f131003ca6e29d17cada08ca6e07 (khop), 483 dong - doc TOAN BO tung dong (ca python 242).

## VERDICT: PASS-WITH-MINOR - DUOC dua owner chay ban 9860c34f (kem dieu kien cuoi file).
Khong con BLOCKER/MAJOR. B-1, M-1, m-1..m-6 da sua va duoc test that su bat (6/6 mutant bi DEV test giet).

## Kiem B-1 / M-1
- B-1: enc()=quote(sym,safe='') (186), q tu enc (338), chan q khong ASCII (230 => Stop), ky HMAC tren DUNG q gui (231). Jar
  C3LiveClient.java:515-524 ghep enc(key)=enc(value) roi signer.sign(q) (HmacSigner:23 UTF-8), enc = URLEncoder UTF-8 '+'->%20 (610)
  => jar ENCODE ROI KY, giong script [doc code]. PLAN regex lop tuong minh (85, 451); phien ghi: allow phai thuoc enc(universe) va
  ^[A-Z0-9%]+$ (325-327); non-ASCII sau cung (306); loi non-ASCII => MANUAL, khong abort (345); 429/418/-1003 van Stop (249).
  Fake curl DEV kiem HMAC tren q nhan + query encode chuan. Mutant: m1 ky unquote(q) => 60/63 (3 FAIL); m2 gui symbol tho => 59/63.
- M-1: pin kiem trong python NGAY sau doc key, truoc moi call, ca read/write (203-207), fin(3) 0 request. Pin = hang Oracle (81-82),
  truyen argv (174). Ghi de pin CHI trong nhanh LV1X_TEST=1 (93-96); che do that: LV1X_TEST phai rong/0 (102) va LV1X_TEST_* bi
  cam (103-106). Che do test khong the ky key that: FAPI .invalid + proxy, KEYS_FILE ngoai /root, CURL242 co dau fake, SSH_242
  cam *ssh*. Mutant m3 (bo kiem pin) => 61/63.
- m-4: stage A tu choi moi _LV1X_* (35); stage B: regex thu muc ^/tmp/lv1x_run\.[A-Za-z0-9]{10}$ (59) truoc trap rm (70) => khong the
  rm -rf rong / '/' / '..' (B6-B10). Token gia mao DUOC (cung user tu tao thu muc 700/500 + .tok) NHUNG ban copy van phai = sha da
  duyet (72) => chi chay dung noi dung da duyet (B5) - chap nhan. Duong dan ops6 tuyet doi (78).
- Mutant khac: m4 leverage=2 => 52/63; m5 bo MANUAL-continue => 61/63; m6 bo deadline => 62/63.

## LOI MOI (MINOR, khong chan)
n-1 (136 vs 335): deadline tinh bang dong ho Oracle, so voi time.time() 242. Lech gio => dung som hon (242 nhanh) hoac POST lan vao
  phut cam vai giay (242 cham). Khung gio la chinh sach giam tai, khong phai an toan => chap nhan. Sua (tuy chon): truyen so giay con lai.
n-2 (111): LEV_CAP doc tu env shell owner; khac 5000 => N_MAXNOTIONAL/DAT cua script lech voi lenh check_lev LEV_CAP=5000. Dong 155/435
  in LEV_CAP. Dieu kien: owner khong dat LEV_CAP (hoac =5000).
n-3: log gl_init (tee) nam TRUOC bo loc sed => log khong loc (nhu v1; python khong in secret; test 0 lo).
n-4 (380, 394): lv_has = printf|grep -q duoi pipefail: neu LVO > 64 KB co the SIGPIPE => '! lv_has ^ERR=' am tinh gia. Uoc LVO ghi that
  ~35-45 KB; khi co ERR= output ngan => khong xay ra. Ghi nhan.
Diem DEV nho soi: `gl_read_state || :` dung (ham tra 1 khi KHONG loi; die van exit; 159 kiem lai END_STATE). awknum = awk voi chuoi so
  thuong; la (hex/nan/inf thuong) ca 2 ra 0 => nhat quan. Symbol ASCII co '_'/chu thuong: universe that 0/522 (doc LEV_CHECK) => fail-closed
  (B13). Ma thoat 0/3/4/1 dung (B1-B4, B11-B14). exec > >(sed) + wait trong trap: dong cuoi co mat, rc giu (B12). read tu stdin (tty
  tmux), stdin dong => TU CHOI (B11).

## MUC 6 - DU LIEU THAT (LEV_CHECK_SUB_20261125_094730, key 43820b5b, W_USED_1M=162)
(a) universe 522, co cfg 522 (thieu 0) => symbolConfig CO tra symbol chua cau hinh. 20x: 496, gom CA 5 symbol chu Han. Mo phong script
  v2 tren du lieu that (exchangeInfo 522 + cfg tu file): N_LEV 496, KE HOACH 496 (bo qua = symbol co vi the/lenh co lev!=1; 7 cum mo
  nhieu kha nang nam trong 26 symbol 1x - suy doan), 5 non-ASCII POST cuoi, N_MAXNOTIONAL 86, DRY rc 3 (B1). Ghi: ~496 POST + ~195
  weight doc, ~3,5-4,5 phut that (uoc).
(b) maxNotional = truong maxNotionalValue cua GET /fapi/v1/symbolConfig (lib 1081-1093 in LEVSYM sym:leverage:marginType:maxNotionalValue;
  check_lev:49 so < 4x0,0225xCAP). Gia tri '0' la SAN TRA THAT: thieu truong => python in 'None' va bi bo qua, khong ra 0. Ca 86 deu
  leverage 20x, maxNotional dung 0; 0/26 symbol 1x bi (26 symbol 1x co maxNotional 2M-60M); symbol 20x khac 5k-2M. Dien giai (SUY DOAN,
  theo hieu biet Binance): maxNotionalValue = tran notional o leverage HIEN TAI; cac symbol nay co bac leverage toi da < 20x => o 20x tran = 0.
  Danh sach 86: ACT ACU AGT AIA AIN AKE ALCH ALPINE ARK ASR AVAAI AVA AWE BAS BEAT BEL BICO BLUAI BROCCOLIF3B BSB BTR CAP CHILLGUY CLO
  COAI COOKIE DOLO DYM ESPORTS FHE FLOW GTC GUA GUN HAEDAL HANA HEI HMSTR KITE KOMA LAB LIGHT LUMIA LYN MAVIA MAV MOVE M MYX NOM O PLAY
  PORTAL PREDICT RARE RAVE RESOLV SANTOS SCR SHELL SIREN SKYAI SONIC SPORTFUN STAR SYN TAC TAKE TA THE TLM TOWNS TRADOOR TREE TRUST TURTLE
  TUT US VELVET XNY ZEREBRO ZEST (moi ten + USDT) + 4 chu Han: ???USDT ????USDT ??USDT ??USDT (?????USDT 20x maxN 5000 - khong bi).
(c) Theo CODE: ca 86 nam trong ke hoach (lev 20 != 1) => script POST 1x, roi doc lai symbolConfig va tinh N_MAXN_AFTER (355, 360);
  DAT CHI KHI lev=0 & margin=0 & maxN=0 (440). Viec maxNotional het 0 sau 1x la HANH VI SAN (suy doan, du lieu ung ho manh: 26/26 symbol 1x
  co maxN >= 2M). Neu dung => DAT rc 0 va check_lev se DAT (cung nguon, cung cong thuc). Neu san van tra 0 => script in
  "KET QUA: CANH BAO (leverage xong; ... maxNotional < 450.00: n [...])" rc 4 (B3) => check_lev CANH_BAO => cong pilot KHONG tao duoc.
  Neu 5 chu Han bi san tu choi (chu ky non-ASCII chua kiem voi san that) => rc 3 + "CAN LAM TAY: <ten goc> (<encode>)" (B4) => owner dat
  1x tren app cho dung cac symbol do roi chay check_lev.

## TEST
DEV 63/63 (1m45). Mutant 6/6 bi giet. Ca pha A1 v2 14/14 (B1-B4 du lieu that 522/496/86/5; B5-B10 stage B/rm; B11 stdin dong; B12 output
qua file; B13 symbol ASCII la; B14 ssh rc != 0). Ca che do that chay voi PATH ssh gia - khong goi 242/san.

## DIEU KIEN KHI OWNER CHAY
1 Shell sach: khong co LEV_CAP (hoac =5000), khong co bien _LV1X_*, LV1X_*, KEYS_FILE..., trong tmux. 2 DRY truoc; ky vong: key_sha8=43820b5b,
universe 522, thieu_cfg 0, leverage!=1 496, margin 0, maxNotional 86, ke hoach ~496 (5 non-ASCII), rc 3. Lech => dung, gui MASTER.
3 Ghi o phut :03-:27 hoac :32-:56 gio Oracle, HOM NAY 25/11 (LEV_EV han 48 h). 4 rc 0 => LEV_CAP=5000 golive_check_lev.sh ngay; rc 3 co
CAN LAM TAY => dat tay tren app roi check_lev; rc 4 => DUNG, gui MASTER (khong lach phep kiem); rc 1 => chay lai DRY, gui MASTER.

## KHONG KIEM DUOC
San that chap nhan query percent-encode + chu ky tren chuoi encode; maxNotional sau 1x; gioi han rieng /fapi/v1/leverage; python /opt/c3py
tren 242 (phien ban, urllib.parse/sys.stdout.buffer); lech dong ho 242-Oracle; vi the/lenh mo hien tai (BUSY).
