# A1_LEV1X - audit doc lap golive_set_lev1x.sh (A1, Opus, 2026-11-25)

Doi tuong: repo w3/c3_ops_lev1x nhanh v1.2/ops-lev1x commit e0a8310d871b0b776d6add1b2a4a175c6989d1f4 (git show --stat: dung 3 file),
golive_set_lev1x.sh sha256 111c17678a336fa372d270904f9bd0fa105fbd7230eccf170a7f1b59cbb8cf41 (khop). ops6 HEAD 082c10f5 sach, md5 lib 5d0febd2 khop.

## VERDICT: FAIL - CHUA dua owner chay ban 111c1767. Can DEV sua B-1 + M-1 (+ khuyen nghi m-*), A1 duyet delta.
(Khong co duong nao dung tai khoan MAIN o che do that / khong gui gi ngoai leverage=1 - phan an toan TOT; FAIL vi B-1 lam script
khong dat muc dich va M-1 la lo chot chan tren tien that.)

## LOI
B-1 BLOCKER (chuc nang, fail-safe) dong 288 + python 167-168/210/221: universe co 5 symbol ten chu Han (xac nhan tren exchangeInfo
  fixture 10-27 va mm_markout: 522-523 symbol, 5 non-ASCII). Neu symbolConfig tra cac symbol nay o 20x (kha nang cao: chua tung giao
  dich) thi PLAN chua ten non-ASCII => dong 288 `die "danh sach ke hoach co ky tu la"` NGAY CA O DRY => script KHONG BAO GIO ra DAT,
  va check_lev (lib 1077-1093, golive_check_lev.sh:47) van dem 5 symbol do => cong pilot van chan. Tai lap: ca pha A11.
  Sua: trong python dung urllib.parse.quote(sy, safe='') cho qs (ky HMAC tren chuoi DA encode, gui dung chuoi do); in PLAN dang
  percent-encode; Oracle kiem `^[A-Z0-9%,]*$`; ben ghi so sanh quote(x) in allow; CHG/ERRSYM in dang encode. Test them symbol chu Han
  (fake curl kiem chu ky tren qs encode). [Hieu biet, CHUA kiem: Binance yeu cau ky tren payload percent-encoded UTF-8 cho symbol
  non-ASCII.] Neu khong sua duoc: MASTER quyet loai 5 symbol khoi phep kiem = sua ops6 (trai ghim) - khong khuyen nghi.
M-1 MAJOR dong 105-123 + 213-221 (+309): phien GHI doc lai file key tren 242 va POST NGAY, KHONG kiem KEY_SHA8 == SUB pin truoc POST;
  kiem chi o dong 309 SAU khi da POST. TOCTOU giua phien doc (dong 252) va phien ghi (<= 300 s cho YES + ~95 weight doc lai).
  Tai lap A10: doi file key giua 2 phien => 2 POST da ky bang key khac roi moi rc 1. Xac suat thap (phai co nguoi sua keys_sub.env)
  nhung la chot chan duy nhat chong ky nham tren tien that. Sua: truyen LV_SUB_SHA8_PIN + LV_MAIN_SHA8_PIN vao python (argv);
  ngay sau tinh KEY_SHA8: neu != SUB hoac == MAIN => out ERR=key_pin, END_API, exit 0 TRUOC moi call (ca read va write).
m-1 MINOR python 115-118: doc key "strip roi startswith, dong CUOI thang" khac lib bash (^ neo, dong DAU) - dong thut le chen key thu 2
  qua duoc KEYS_OK (A9: bi chan nho kiem sha8 dong 252 => fail-safe). Sua: khong strip dau dong, tu choi neu > 1 dong KEY/SECRET.
m-2 MINOR: script KHONG bao maxNotionalValue < 4 x 0,0225 x 5000 = 450 (dieu kien thu 3 cua check_lev:49). KET QUA: DAT cua script
  CHUA dam bao check_lev DAT. Sua: in N_NOTIONAL (cap 5000) o DRY va sau ghi (chi bao).
m-3 MINOR dong 69/66: _LV1X_MASKED dat san = PID shell owner => bo qua bo loc output (python khong in secret nen khong lo; ghi nhan).
m-4 MINOR dong 26-30: sha256 kiem luc dau, bash doc file dan dan + re-exec doc lai file => file sua trong luc chay khong bi bat
  (can quyen ghi repo Oracle). Sua (tuy chon): cp script vao mktemp, kiem sha ban copy, exec ban copy.
m-5 MINOR dong 299: read cat khoang trang => '  YES LEV1X  ' duoc chap nhan (vo hai).
m-6 INFO: cho weight o phien DOC im lang (WAIT chi stream o phien ghi) - toi da 240 s khong in gi.

## TRA LOI
(i) MAIN / ghi sai: Khong co duong (o che do that) ky bang key MAIN neu keys_sub.env khong bi sua: KEYS_FILE bi cam ghi de (51-53, A1-A6),
  sau source lib phai = /root/.config/c3live/keys_sub.env (83), file key bot dung phai = file do (91-96), sha8 file = 43820b5b != 3ef771e0
  (98-99), sha8 key ky = SUB (252-253). Lo duy nhat: M-1 (TOCTOU phien ghi). Danh sach cam ghi de du so voi bien lib doc anh huong ket noi/
  tai khoan (SSH_242 SCP_242 APP_DIR PROC_PAT KEYS_FILE PY242 CURL242 SUB/MAIN_KEY_SHA8 LOGDIR GL_*; A bi lib dat lai; C3_ACCOUNT chi SUB).
  Key khong roi 242: curl -K - qua stdin, argv chi co duong dan file; Oracle chi nhan KEY=VAL; test 32 xac nhan khong lo.
  Ghi: duy nhat POST /fapi/v1/leverage voi 'symbol=%s&leverage=1' hang (221); khong co call marginType/order/position. Tap symbol =
  universe(exchangeInfo 242) & lev!=1 & khong vi the & khong lenh thuong/algo (snapshot dau phien ghi) & trong PLAN owner xac nhan (215).
  Injection qua ten symbol: bi chan o dong 288 (A12: khong thuc thi), phia python dung argv/khong shell.
(ii) Rate-limit: script <= 4 req/s (<= 240 weight/phut cua minh), doc header THAT X-MBX-USED-WEIGHT-1M sau moi call, IP >= 600 => ngu toi
  phut sau. Jar c3 nhan call thuong khi IP+cost <= 1800 (ProductionRatePolicy.java:11-12,33) => script khong the tu day IP len 1800/2400;
  429/418/-1003 => DUNG ngay. Rui ro bot dinh 429/418: THAP. Rui ro la script DUNG giua chung neu nen IP >= 600 lien tuc (chay lai =
  idempotent). Khuyen nghi: chay toi nay 25/11 (khong phai sang 26/11), tranh phut :58-:02 va :29-:31; xem W_USED_1M o DRY: neu 600-1000
  co the them LV1X_W_MAX=1200 (van < 1800 cua jar). Gioi han rieng endpoint leverage: theo hieu biet chi weight 1, khong tinh order-count
  - CHUA kiem. ~500 su kien ACCOUNT_CONFIG_UPDATE: C3StreamScope.java:140-145 bo symbol khong lien quan; UserStreamEvents khong parse =>
  vo hai (doc code). AccountModeGuard: cache chi giu symbol OK (prefetch 84-119, checkSymbol 196-218) => doi 20x->1x tu ngoai khong chan
  nham/cho qua nham, khong can restart. Race bot vao lenh: jar tu dat 1x, POST 1x trung gia tri.
(iii) check_lev: cung nguon symbolConfig, cung dinh nghia universe (script 167-168 = lib 1077-1078), symbol thieu cfg bo qua o CA HAI =>
  nhat quan. Sau khi sua B-1, script DAT => N_LEV check_lev = 0, tru symbol moi list/doi giua 2 lan chay hoac symbol bi bo qua do vi the
  (vi the c3 da 1x). Con 2 dieu kien script khong sua: marginType != CROSSED (script bao N_MARGIN) va maxNotional < 450 (script KHONG bao -
  m-2; theo hieu biet o 1x maxNotional = bac cao nhat, gan nhu chac >= 450 - CHUA kiem). Neu DRY bao N_MARGIN > 0 => cong van chan.
(iv) Test: DEV 33/33 tai lap. Ca pha A1 16/16 chay dung ky vong (trong do A10 va A11 XAC NHAN loi M-1, B-1). Che do test khong the goi
  san that: FAPI .invalid + proxy 127.0.0.1:9 + CURL242 phai co dau LV1X_FAKE_CURL + SSH_242 cam *ssh*/242 + KEYS_FILE ngoai /root;
  ca che do that trong ca pha chay voi PATH shim ssh/curl gia - 0 lan goi ssh.

## 7 diem DEV
1 race bot: CHAP NHAN. 2 gioi han rieng leverage: CHAP NHAN (dung o 429/-1003; chua kiem). 3 symbolConfig co tra moi symbol: CHAP NHAN
(nhat quan 2 script) NHUNG ket hop B-1 => PHAI SUA. 4 cho weight im lang o DRY: CHAP NHAN (m-6). 5 khong ap gl_time: CHAP NHAN + khuyen
nghi gio o (ii). 6 loc output PPID/log truoc loc: CHAP NHAN (m-3). 7 ssh dut => DUNG, chay lai idempotent: CHAP NHAN (A14/A15).

## DIEU KIEN KHI OWNER CHAY (sau ban sua)
DRY truoc; gui MASTER: KEY_SHA8, universe, thieu_cfg, N_LEV, N_MARGIN, BO QUA, W_USED_1M. Ghi trong 1 tmux, khong Ctrl-C tru khan; sau do
LEV_CAP=5000 golive_check_lev.sh ngay. Khong chay cung luc pilot_on/golive_* khac.

## KHONG KIEM DUOC
Phan hoi that cua san: symbolConfig co tra symbol chua cau hinh; cach ky symbol non-ASCII; gioi han rieng /fapi/v1/leverage; maxNotional
o 1x; nen weight IP thuc te 242; locale python 242 khi in ten chu Han.
