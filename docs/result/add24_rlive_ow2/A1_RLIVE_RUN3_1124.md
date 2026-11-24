# A1 - AUDIT doc lap ket qua cham ADD24 R-LIVE luot chinh thuc #3 (E7) - 2026-11-24
Agent A1 (Opus), CHI DOC. Khong sua harness / prereg / errata / khoa / output; khong chay lai official; khong 242; khong mvn/java.
Khong in PnL / equity / mean_delta. Chenh gia thoat chi bao dang % theo TUNG cum (prereg L-X dinh nghia theo cum), khong cong don.
Ky hieu: [KIEM] = A1 tai tinh / kiem bang code tren file tho; [CODE] = doc ma nguon (file:dong); [SUY] = suy luan, chua kiem truc tiep.
Code A1 (python, doc lap voi rlive_score.py): v12/a1_rlive_run3_tmp/a1_scripts.tgz (common.py, le.py, ls.py, ls2.py, lt.py, arm.py, sl.py, ex.py, echeck.py, slx.py).
Du lieu: ban sao v12/rlive_run3_backup_1124/rlive_official_1124_203251 (live/*.csv, L0, L0-DRY, L0-FOLLOW, score_*, conclusion);
kline/mark 1m CHI cua 24 symbol live tu fx/ cua luot #3 (khong doc du lieu thi truong ngoai output luot #3).

## 0. Verdict audit (tom tat)
- Moi con so cua harness ma A1 tai tinh deu KHOP (bang muc 2). Ket luan R_LIVE = FAIL DUNG LUAT prereg s9/s10 + ERRATA3 A1.
- 100 % muc lech trong labels.csv (161 = 159 UNEXPLAINED + 2 N8) deu thuoc 16 cum DA ARM; 8 cum chua arm = 0 lech. Khong tim thay muc nao
  lẽ ra phai mang mot nhan DONG (N1..N9, N12) ma bi de UNEXPLAINED theo dung chu prereg. Co 4 diem harness chua toi uu (muc 3.3) nhung
  KHONG diem nao doi duoc ket luan.
- PHAN LOAI CO CHE (phan tich SAU khi thay ket qua, khong doi ket luan): toan bo lech thoat lenh nhat quan voi 4 co che DA BIET trong
  REVIEW_1124 (D1 MARK vs LAST, D2 lay mau 10 s vs HIGH nen, D8 gia vao = gia khop, + K6 kieu stop sau -4130); A1 KHONG tim thay bang chung
  loi LOGIC cua jar (nhom E = 0) qua 7 phep kiem bat bien tren log live (muc 4.3). Muc chac: CAO cho "khong co loi logic phat hien duoc
  o do phan giai du lieu hien co"; KHONG the loai tru loi chi lo ra o do phan giai < 1 phut (khong co chuoi gia 10 s bot da thay).
- L-S2 FAIL: do dau vao GIA (gia sizing realtime / gia khop that) lan qua U_before va C_eff cua sizing hinh hoc - khac biet DA BIET (D8 + K4/K7),
  KHONG phai loi cong thuc (L-S 24/24 PASS: budget live = cong thuc tren CHINH dau vao live).
- Blind (luot #2) vs luot #3: TRUNG noi dung (conclusion.json trung byte; score.json trung tru 1 ulp o mean_delta; labels.csv trung khi sap xep).

## 1. Toan ven (buoc 1) [KIEM]
| Kiem | Ket qua |
|---|---|
| Khoa a/OFFICIAL_ADD24_RLIVE.lock | 3 dong: 09:02 (luot #1, errata rong, head 3e6da6eb), 18:04 (luot #2, E6, a66109c1), 20:32:51 (luot #3, `errata=E7`, head=8d397ce2, a1=8d397ce2dbbd..., p1=e451154e, exinfo dcfa03c7...). Chi 1 dong E7. Khong co luot nao khac. |
| HEAD harness | w3/add24_wt HEAD = 8d397ce2dbbdf3db72da9dd7bb4399866c675911 (commit 19:56:40), git status sach. |
| ERRATA7 | vz_e1_wt fa00ccdf commit 2026-11-24 20:19:44 +07 = TRUOC khoa 20:32:51. |
| Ban sao vs manifest | sha256sum -c v12/rlive_run3_backup_1124.sha256 (173 file): 0 loi. (A1 khong doc /dev/shm theo rang buoc - so sanh nguon /dev/shm do RUN ghi.) |
| Ban harness tu luu (w3/add24/a/rlive_official_1124_203251) vs ban sao | conclusion.json, gates.json, gates.txt, score_L0*, V8/V10/v4b.json, buf_*: TRUNG (diff khong liet ke). Lane L0/L0-DRY/L0-FOLLOW/L-10K: KHAC CO CHU Y - ban harness la ban SANITIZE (run_rlive.sh:111-113 + sanitize.py: bo cot capital/eq/eq_at, khoa equity/realized trong result.json, dong equity trong run.log; khong chep fills/trace/market). Dung thiet ke ERRATA3 A10, khong phai sai lech. |
| gates.json | V1..V10a = true, ok = true (sha b526e9f3...). |
| conclusion.json | sha 03dd8cb3... (trung so RUN ghi). |

## 2. Tung tieu chi: dinh nghia, code, tai tinh [KIEM]
Dinh nghia: prereg s9.1 bang; ERRATA3 A1 (>= 1 lech KHONG GIAI THICH => FAIL bat ke mau), A6 (ghep HAI chieu), A8 (N8 chi khi REF-nhip);
ERRATA4 C2 (L-SL ghep 1-1 +-2'); s10 (FAIL > INSUFFICIENT > PASS; L-X/L-T FAIL tren lenh that khong duoc phu).
| Tieu chi | Nguong (prereg) | Code cham (rlive_score.py) | Harness (L0 / L0-DRY) | A1 tai tinh | Khop |
|---|---|---|---|---|---|
| L-E | tap (phut, sym, level, legIdx) + thu tu; 0 lech KGT; >= 20 | :155-203 | 24/24 khop, 0 KGT, thu tu 3 phut 0 lech / giong | 24 live, 24 rig, 24 khop, 0/0 thua; 3 phut (10:38 x1, 10:44 x7, 11:07 x16) thu tu trung; L0-DRY va L0-FOLLOW cung 24/24 | CO - PASS |
| L-N | phut co input: live khong SUBMIT <=> rig khong; 0 KGT | :204-207, V10b :528-539 | minutes_diff 0, V10b 0 / giong | tap phut SUBMIT live == rig (hieu doi xung rong) => 0 lech o moi phut | CO - PASS |
| L-S | bao s9.3 +-1e-5; U_before; px ngam trong [low,high] nen dts u dts+1; qty floor; legIdx | :267-333 | 24 ok / 0 fail | ls.py doc lap: 24/24 ok (legIdx, bao budget, U_before nhat quan, px ngam, qty floor stepSize) | CO - PASS |
| L-S2 | <= 5e-4 o >= 90 % VA <= 2e-3 o 100 % | :334-341 | n 24, max_rel 9,48e-4, share 0,375, n>2e-3 0 / max 8,25e-4, share 0,583 | identical: 9,4805e-4; 0,375; 0 / 8,2519e-4; 0,5833; 0 | CO - FAIL (share < 0,9) |
| L-K | rig 0 ERROR/latch/KHAN; -4130 co stop thay <= 2 nhip | :540-547 | 0/false/0; 4130 1, thay 1 | result.json errors 0, latch False, KHAN 0 (L0, L0-DRY); -4130 BLESS 12:20:19.690 -> stop qty 12:20:19.786 | CO - PASS |
| L-D | DCA bac/phut/legIdx; >= 1 | :373-405 | live 0, rig 0 | 0 leg DCA live, 0 rig (moi leg legIdx 0) | CO - INSUFFICIENT (khong phu: conclude.py khong nhan rsim S-D; khong anh huong ket luan) |
| L-T | >= 90 % cung phut; con lai <= 2' (N8); 0 thieu/thua; >= 5 | :406-431 | live 16, rig 16, same 6, n8 1, bad 13 (5 cap + 4 + 4 khong ghep) | 16/16; cung phut 6 (37,5 %); lech 1-2': 3; > 2': 7 (BLESS +4, BULLA -5, MUBARAK -3, MANTRA -24, PIEVERSE -26, EVAA -85, PONS -408). Ghep dung dung sai 5' nhu harness => 12 cap + 4/4 khong ghep, 1 N8 => bad 13 | CO - FAIL |
| L-SL | |dgia| <= 2 tick hoac 0,1 %, +-2'; 100 % cum arm co stop; kieu khac chi N7 | :432-467 | live 87, rig 58, ok 9, bad 130 (78+49+3 kieu) | slx.py doc lap: 87 / 58 / 9 cap / 78 live thua / 49 rig thua / 3 kieu (MANTRA 21:22:55, USELESS 17:50:40, 18:30:06) => 130; arm_no_stop 0 | CO - FAIL |
| L-X | ly do 100 %; >= 90 % cung phut; con lai <= 2' (N8); Delta tung cum >= -1,5 % hoac <= 2 tick; TB trong [-0,8 %; +0,2 %] | :468-525 | live 16, rig 16, reason_ok 12, same_min 3, n8 1, bad 16 | 12 cap (+-30'), 4/4 khong ghep (EVAA, MUBARAK, PIEVERSE, PONS); ly do: tat ca TRAILING_STOP 2 phia; cung phut 3 (BTW, MANTRA, PIPPIN); 9 cap lech phut (1 N8 BLESS) => 8 + 8 = 16; Delta tung cum tu -0,77 % (ARIA) den +0,41 % (BTW), khong cum nao < -1,5 %; TB trong khoang (khong cong them bad) | CO - FAIL |
| C0b | tai lap 11-05 tren stub | C0B.json (11-22 19:26, stub cf0f4792) | PASS | A1 chi doc C0B.json: moi lane ok, mism 0, max_rel_budget 0 (khong chay lai) | CO |
Gop (conclude.py:31-55): BB L-S2 FAIL (ca L0 va L0-DRY) + L-T / L-SL / L-X FAIL => R_LIVE = FAIL. Chi rieng L-S2 cung du FAIL.

## 3. Nhan (buoc 3)
### 3.1 Dem 100 % [KIEM]
labels.csv L0: 161 dong = L-SL live_only 78 + rig_only 49 + kieu 3 (UNEXPLAINED); L-T 5 cap + 4 + 4 (UNEXPLAINED) + 1 N8; L-X 8 cap + 4 + 4
(UNEXPLAINED) + 1 N8. N1..N7, N9, N12 = 0. Moi dong thuoc 16 cum da arm (ARIA 4, BLESS 12, BTW 12, BULLA 6, CYS 11, EVAA 9, HUSDT 12,
JCT 6, MANTRA 5, MUBARAK 8, NAORIS 25, PIEVERSE 11, PIPPIN 2, PONS 8, UAI 17, USELESS 13). L0-DRY 162 (khac L0 o vai cap stop/kieu).
L-S2: 15/24 leg > 5e-4 KHONG duoc liet ke trong labels.csv (chi so tong) - ngoai le duy nhat cua prereg la N4/N5: 0 leg bi tu choi, 0 nhan goc => khong ap.
### 3.2 Co diem nao le ra thuoc nhan da ghi truoc?
- Prereg KHONG co nhan nao cho "rig chi co nen 1 phut nen khong tai lap duong gia trong phut". Nguyen van cac muc lien quan:
  K8: "Trailing nhip 10-15 s trong nen (B1; ARM_CUNG_NEN 11-05: JCT som 4') | dung sai phut arm / thoat + nhan N8 khi duong gia nhip cua REF
  xac nhan | CO (N8), gioi han so luong"; N8: "B1_INTRABAR: phut arm / doi SL / thoat lech <= 2 phut va REF-nhip (noi suy nhip trong nen nhu jar)
  cho cung phut voi rig/live"; s8: "Tong N8 > 10 % cum => tieu chi tuong ung FAIL"; K9: "lech do gia cu => KHONG GIAI THICH"; ERRATA3 A8:
  "N8 ... khong gan tu dong theo lech <= 2 phut". Kich stop theo MARK (vs gia last) va lay mau dinh 10 s (vs HIGH nen): KHONG co K/N nao.
  => Theo prereg, cac diem do la UNEXPLAINED va FAIL la DUNG LUAT. Ngay ca N8 toi da: 24 cum x 10 % = 2,4 => toi da 2 N8; L-T cung phut 6/16
  va L-X cung phut 3/16 < 90 % => FAIL khong phu thuoc gan nhan.
- K6/N7 (kieu stop): N7 can "-4130 CUNG symbol truoc do". Code [CODE TrailingStopManager.java:103,285-286,344-350]: co `closePositionConflictSeen`
  la co CHUNG cua manager => sau -4130 dau tien (BLESS 12:20:19) MOI symbol dat stop xen ke qty+reduceOnly / closePosition (log: 39 qty, 48 close).
  3 muc "kieu khac" L0 (15 o L0-FOLLOW) la hanh vi THIET KE, nhung nhan N7 theo chu prereg chi phu cung symbol => UNEXPLAINED dung luat.
  Rig khong mo phong -4130 (FakeExchange1m/MockExchangeGateway chap nhan stop closePosition thu 2) => rig luon closePosition.
### 3.3 Diem harness chua toi uu (KHONG doi ket luan)
1. ref_exit (rlive_score.py:489-498) ap MUC STOP CUOI cua live cho ca cac nen TRUOC khi stop do ton tai => REF tra ve phut qua som (vd CYS REF
   15:01, NAORIS REF ...), co the tu choi N8 cho CYS (-1') va NAORIS (-1'). Neu gan: N8 = 4 > 2,4 => L-X van FAIL (tran N8), va cung phut 3/16.
2. L-SL khong bao gio gan N8 (ERRATA4 C2 cho phep khi co REF) - khong vat chat (tran N8).
3. Cap arm/thoat khong ghep bi dem 2 lan (live_only + rig_only cung cum) - quy uoc dem, khong doi trang thai.
4. labels.csv co thu tu dong KHONG tat dinh (lap qua set() symbol, hash ngau nhien) va mean_delta lech 1 ulp - xem muc 5.
5. L-D: conclude.py khong co --rsim => muc phu S-D = thieu => INSUFFICIENT (khong phu). Khong anh huong (da FAIL).

## 4. Phan loai co che (PHAN TICH SAU KHI THAY KET QUA - KHONG doi ket luan)
### 4.1 Nguon du lieu so sanh
- Live: price_realtime moi 10 s (EXIT_EVERY_MS, C3LiveRuntime.java:78, exitTick :575-585) => peak/arm/doi stop; stop tren san STOP_MARKET
  workingType MARK_PRICE (C3LiveClientConfig.java:96-119) khop MARKET.
- Rig (CrashDayRig.java:470-518): moi phut 4 moc gia tu kline LAST (O, cuc 1, cuc 2, C; nen giam O-H-L-C, nen tang O-L-H-C), mgr.step moi 10 s
  doc moc gan nhat; FakeExchange1m.tickPrice kich stop khi gia LAST <= stop. => rig luon thay dung HIGH va LOW cua nen last, live chi thay mau.
- L0 khop vao tai gia nen (sizing px); L0-FOLLOW khop vao tai GIA KHOP THAT cua live (follow.csv) => so L0-FOLLOW voi live tach rieng anh huong D8.
- Cong thuc trailing (suy tu du lieu, KHOP 2 phia): SL = entry x (1 + round((peak - 0,03)/0,005) x 0,005), arm khi rate > 0,07; 16/16 dong arm
  live va moi su kien TRAIL_SL cua rig thoa cong thuc nay [KIEM; cong thuc suy tu event rig cung jar, A1 khong doc C3TrailRate].
### 4.2 Dong thoi gian 24 cum (gio +07, ngay 11-21 neu khong ghi) [KIEM]
| Cum | arm live / L0 / FOL | stop live (so lan) vs FOL | thoat live / L0 / FOL | Delta gia thoat live vs L0 | Nhom |
|---|---|---|---|---|---|
| ARIA (11-22) | 10:56 / 10:56 / 10:56 | live ARM 4,0 % -> 5,0 % (mau), FOL ARM 5,5 % (HIGH nen) | 11:30 / 11:01 / 11:26 | -0,77 % | A -> D (stop live thap hon) |
| BLESS | 12:16 / 12:20 / 12:15 | 6 vs 3; live 6,49 % vs FOL 7,0 % luc thoat | 12:47 / 12:45 / 12:45 | -0,42 % (N8) | B (L0: D8; FOL: -1') -> D (FOL: kline cham stop, mark khong) |
| BTW | 13:42 / 13:42 / 13:41 | 8 vs 7, muc cuoi trung 8,0 % | 14:28 / 14:28 / 14:28 | +0,41 % | A (buoc trung gian) |
| BULLA | 20:38 / 20:33 / 20:36 | 2 vs 2, trung | 21:01 / 20:49 / 21:01 | -0,43 % | B (L0 do D8; FOL thoat cung phut) |
| CYS (11-23) | 15:01 / 15:01 / 15:01 | 7 vs 3, muc cuoi trung 7,98 % | 15:05 / 15:04 / 15:04 | -0,41 % | A -> D-mark (15:04 kline low cham stop live, mark khong) |
| EVAA | 15:40 / 14:15 / 14:15 | live 4 lan; FOL ARM 14:15 roi thoat | 16:30 / 14:16 / 14:16 | khong ghep | B-wick (HIGH 14:15 vuot 7 %, close vuot luc 15:43) -> D |
| HUSDT | 15:01 / 15:01 / 15:01 | 11 vs 7; FOL 10,42 % > live 9,96 % | 15:38 / 15:30 / 15:26 | -0,33 % | A -> D (+ mark: 15:31 kline cham stop live, mark khong) |
| JCT | 12:24 / 12:23 / 12:19 | 3 vs 2; FOL 7,46 % > live 6,98 % | 12:35 / 12:31 / 12:31 | -0,38 % | B (wick 12:19) -> D (+ mark 12:33) |
| MANTRA | 21:03 / 20:39 / 21:02 | 3 vs 3 trung | 11-22 02:23 / 02:23 / 04:30 | +0,06 % | B (L0 do D8) ; C: live kich MARK, stop 0,001817 < kline low 0,001818, mark low 0,001815 |
| MUBARAK (11-22) | 23:09 / 23:06 / 23:09 | 2 vs 3; FOL MOVE 4,95 % ma live khong (peak mau thap hon) | 11-23 01:08 / 23:52 / 23:27 | khong ghep | A/B -> D |
| NAORIS | 15:49 / 15:47 / 15:48 | 13 vs 10; FOL 12,0 % > live 11,48 % | 16:09 / 16:08 / 16:08 | -0,29 % | B nho -> D |
| PIEVERSE | 14:13 / 13:47 / 13:49 | 4 vs 3 | 16:17 / 15:29 / 15:29 | khong ghep | B-wick (HIGH 13:49 vuot, close 14:13) -> D (+ mark 16:16) |
| PIPPIN (11-23) | 18:11 / 18:11 / 18:11 | 1 vs 1 trung | 18:15 / 18:15 / 18:15 | +0,11 % | chi D8 (L0 lech muc do gia vao; FOL trung) |
| PONS | 20:36 / 13:48 / 13:51 | 3 vs 1 | 22:55 / 14:22 / 14:22 | khong ghep | B-wick (HIGH 13:51 vuot, close 20:36) -> D (+ mark 22:27) |
| UAI | 20:39 / 20:37 / 20:38 | 7 vs 7, muc cuoi trung | 23:03 / 22:57 / 23:03 | -0,16 % | B nho (L0 do D8; FOL cung phut) |
| USELESS | 17:17 / 17:17 / 17:17 | 11 vs 6, muc cuoi trung 9,5 % | 18:45 / 18:40 / 18:41 | -0,05 % | A -> D-mark (FOL cung muc stop; 18:41 kline low <= stop, mark low > stop) |
| 8 cum mo (MMT, ZIL, SOPH, CFG, KAVA, BREV, ICNT, IRYS) | khong arm o ca 3 phia | - | con giu tai T_cut ca 3 phia | - | khong lech (HIGH max 0,6-5,9 % < 7 %) |
(% stop = stop/entry_live - 1. Truot khop thoat live so voi stop cua chinh no: -0,58 %..+0,11 %, MARKET sau kich MARK - g_exit, khong cham o R-LIVE.)
### 4.3 Kiem bat bien tren log live (nhom E = cung thong tin ma quyet dinh khac) [KIEM, echeck.py / sl.py]
| # | Bat bien | Ket qua |
|---|---|---|
| E1 | Muc stop live khong bao gio vuot cong thuc(peak) voi peak <= HIGH kline lon nhat tu luc vao (live khong "thay" gia khong co tren san) | 87/87 dat (0 vi pham) |
| E2 | Arm: khong co phut nao O VA C deu > nguong 7 % truoc arm live (live khong bo lo vuot nguong keo dai ca phut) | 0 vi pham (16 cum) |
| E3 | Stop live chi tang (khong bao gio ha) | 16/16 cum |
| E4 | Co stop sau arm: dong stop ARM 0,18-0,29 s sau dong arm (16/16); moi stop co ALGO NEW; 71 CANCELED = 71 MOVE (huy sau khi dat moi); 16 TRIGGERED->FINISHED = 16 cum dong, ly do TRAILING_STOP | dat (1 loi dat HUSDT 15:06:56 -> thu lai 15:07:06, stop cu van hieu luc) |
| E5 | Khong bo lo kich: khong co phut tron nao (sau khi stop dat, truoc phut thoat) ma MARK low <= stop dang hieu luc | 0 |
| E6 | Phut thoat: MARK low <= stop live (kich theo mark nhat quan) | 16/16 (kline: 15/16; MANTRA chi mark cham) |
| E7 | So voi L0-FOLLOW (cung gia vao): live KHONG BAO GIO arm som hon rig, va muc stop live <= muc stop rig (+2 tick) khi rig con giu | arm 16/16 (d <= 0); stop 0 vi pham |
=> Moi lech di DUNG huong du doan cua do phan giai: rig (thay HIGH/LOW nen last) arm som hon / dat stop cao hon / bi quet boi rau last;
live (mau 10 s + kich MARK) arm muon hon / stop thap hon / giu lau hon. Khong co mot truong hop nguoc huong nao (live "biet nhieu hon" rig).
### 4.4 Dem theo nhom (cum; muc lech L0 trong labels.csv)
| Nhom | Dinh nghia | Cum | Muc lech |
|---|---|---|---|
| A | cung phut arm, muc stop / so buoc khac (live dat nhieu buoc 0,5 % theo mau; rig nhay theo HIGH) | ARIA, BTW, CYS, HUSDT, PIPPIN, USELESS = 6 | 4+12+11+12+2+13 = 54 |
| B | arm lech phut roi day chuyen stop/thoat | BLESS, BULLA, JCT, MANTRA, MUBARAK, NAORIS, UAI, EVAA, PIEVERSE, PONS = 10 (trong do 3 "wick": EVAA, PIEVERSE, PONS lech 26-408') | 107 |
| C | live thoat do stop kich trong phut theo MARK ma nen kline khong tai hien | MANTRA (stop < kline low) = 1 cum; ngoai ra 7 lan kline low cham stop live ma mark khong (JCT, PIEVERSE, HUSDT, EVAA, USELESS, PONS, CYS) => live giu tiep | (gop trong A/B) |
| D | rig thoat som hon live | 13 cum o L0 (9 cap lech phut + 4 khong ghep); ly do: (i) stop rig cao hon (peak = HIGH nen vs mau 10 s), (ii) rig kich theo LOW last, live theo MARK, (iii) rig arm tren rau roi bi quet truoc khi live arm (EVAA, PIEVERSE, PONS) | (gop trong A/B) |
| E | cung thong tin ma quyet dinh khac | 0 | 0 |
| K6 | kieu stop xen ke sau -4130 (co chung) | 2 cum (MANTRA, USELESS) | 3 |
| D8 | gia vao live = gia khop; L0 = gia nen | moi cum: L0-FOLLOW nang L-SL ok 9 -> 31, giam lech L-SL 127 -> 85 (khong ke kieu), L-T >2' 7 -> 4, L-X cung phut 3 -> 4 | ~42 muc L-SL |
Chu y: L0-FOLLOW (loai D8) VAN truot moi tieu chi thoat (L-T cung phut 6/16, L-X cung phut 4/16, L-SL 100 lech) => phan con lai la D1/D2/K6.
### 4.5 Cau tra loi then chot
KHONG co bang chung loi LOGIC cua jar (nhom E = 0). Toan bo lech thoat lenh nhat quan voi: rig thieu duong gia trong phut (D2: HIGH nen vs mau 10 s),
rig kich stop theo LAST thay vi MARK (D1), gia vao khac (D8, chi L0), va kieu stop -4130 (K6, chi L0/FOLLOW khong mo phong). Muc chac: CAO
(7 bat bien dat 100 %, moi lech dung huong du doan, ca 16 phut thoat live deu co mark low <= stop). Gioi han: A1 khong co chuoi price_realtime
10 s cua live nen KHONG chung minh duoc tung buoc dat stop live = cong thuc(peak mau that); chi chung minh duoc chan tren (E1) va huong (E7).
Mot loi lam stop live THAP hon dung (vd peak bi reset / mau cu) se KHONG bi bat boi E1/E7. [SUY] Nhung buoc nhay live 0,5 % moi 10-20 s trong
cac pha tang manh (CYS, NAORIS, USELESS) phu hop mau gia tang dan, khong co dau hieu peak bi reset.
### 4.6 L-S2: nguon lech [KIEM, ls2.py]
- Live budget = cong thuc s9.3 tren CHINH U_before/C_eff cua live (L-S 24/24) => lech L0 vs live nam o DAU VAO cong thuc.
- Tach log: rel_budget(rig-live) = phan U + phan C. 10:44 (7 leg): phan U -1,5..-3,1e-4, phan C ~ -1,8e-5. 11:07 (16 leg): phan C ~ -4,8e-4 (moi leg),
  phan U -1,4e-5..-4,7e-4 => max 9,5e-4 (ZIL, leg dau phut 11:07).
- Phan U: margin cac leg truoc tinh bang notional/qty theo gia sizing (live: price_realtime giay ~6-66; rig: gia nen) + lam tron qty; tuong quan
  rel_budget voi chenh margin tich luy cac leg truoc = 0,63 (L0), 0,68 (FOLLOW), 0,51 (DRY).
- Phan C: C_eff = min(1000, E_c3 MTM) - E_c3 phu thuoc gia khop vao cac vi the dang mo (rig khop gia nen, live khop that; L-P median 18 bps, p90 35 bps).
- Ket luan: day chuyen gia vao / gia sizing qua sizing hinh hoc (D8 trong REVIEW_1124 + K4/K7 prereg) - khac biet DA BIET ve co che, nhung
  BIEN DO (9,5e-4) lon hon can cu prereg (11-05: 1,35e-4) vi 24 leg don trong 3 phut sap voi truot vao lon. Khong co nhan cho L-S2 ngoai N4/N5
  => FAIL dung luat. Khong co dau hieu loi cong thuc. (L0-FOLLOW con lech hon, max 1,9e-3: FOLLOW chi dong bo gia khop, khong dong bo gia sizing.)

## 5. So tinh tat dinh voi blind/ (luot #2) [KIEM]
Copy bang `sudo cp -a` sang v12/a1_rlive_run3_tmp/blind_copy (ban goc giu mode 000, mtime khong doi), chown/chmod tren BAN COPY.
- conclusion.json: TRUNG BYTE (sha 03dd8cb3... = ERRATA7 muc E).
- score_L0/score.json, score_L0DRY/score.json: JSON trung moi truong tru mean_delta khac o chu so cuoi (1 ulp, thu tu cong float).
- labels.csv (L0, L0-DRY): khac byte, TRUNG khi sap xep (cung 161 / 164 dong) - thu tu dong phu thuoc thu tu lap set() (hash ngau nhien).
- score_*.txt (trang thai + dem nhan): trung.
=> Bo cham tat dinh ve noi dung; luot #2 va #3 cho cung ket qua tren cung dau vao.

## 6. 10 symbol "live giu lau hon rig" (V10_diag) [KIEM]
PONS 513', EVAA 134', PIEVERSE 48', ARIA 29', BULLA 12', HUSDT 8', USELESS 5', JCT 4', BLESS 2', NAORIS 1' = dung bang hieu phut thoat L0 vs live.
Ca 10 deu duoc cham trong L-X (PONS/EVAA/PIEVERSE: live_only + rig_only; ARIA/BULLA/HUSDT/USELESS/JCT/NAORIS: cap UNEXPLAINED; BLESS: N8) va
trong L-T (arm). Them MUBARAK (76'), UAI (6'), CYS (1') co trong L-X du khong nam trong V10_diag (V10 chi xet phut co lech ban ghi buffer).
=> Da cham du.

## 7. Y KIEN A1 (la y kien, khong phai ket qua kiem)
(a) FAIL dung luat prereg: co. L-S2 (BB, ca L0 va L0-DRY) va L-T/L-SL/L-X (FAIL tren lenh that, s10 khong cho phu) - nhan duy nhat cho lech
    trong nen (N8) bi tran 10 % cum va khong co nhan cho MARK vs LAST. Khong co duong hop le nao (trong prereg) doi FAIL thanh PASS/INSUFFICIENT.
(b) FAIL nay NOI: rig 1 phut + gia LAST + khop vao gia nen KHONG tai lap duoc quy dao thoat cua bot (thoi diem arm, so buoc va muc stop, phut
    thoat) - tuc la cac so "thoat" cua sim/rig (va HO5) khong phai mo ta chinh xac cua live; huong lech nhat quan: live arm muon hon, stop thap hon,
    giu lau hon rig. FAIL nay KHONG NOI: jar co loi logic. Phan vao lenh (tap lenh 24/24, thu tu, legIdx, ham size tren dau vao live, gate/buffer
    V10a) dat; L-S2 lech < 1e-3 do dau vao gia. Phan thoat qua 7 bat bien tren log live khong lo loi; stop luon co tren san sau arm, chi tang,
    kich dung 16/16.
(c) Lua chon cho owner:
   1. GIU DIEU KIEN (khong pilot 5.000 toi khi co bai kiem thoat dat). Rui ro: tre lich; khong lam bot an toan hon (micro 1.000 van chay).
   2. GHI DE CO PHAM VI kieu ADD5: owner chap nhan bang van ban rang lech L-T/L-SL/L-X (D1 MARK, D2 mau 10 s, D8 gia vao, K6 kieu stop) va L-S2
      (day chuyen gia vao <= 1e-3) la khac biet co che da biet. DUOC ghi de: so khop quy dao thoat live-vs-rig 1 phut, nguong L-S2. CHUA co bang
      chung: dung tung muc stop live = cong thuc(peak mau that) (chi co chan tren), hanh vi time-stop 168 h / X14 / DCA tren lenh that (0 su kien),
      sai so cua "ky vong HO5" do D1/D2 (huong lech khong the cong don thanh so loi nhuan o day). Rui ro: tien le ghi de lap lai; neu sau nay co loi
      that cung huong voi co che da biet thi kho phan biet.
   3. BAI KIEM THOAT DUNG DO PHAN GIAI (prereg moi):
      - NGAY tren log live da co, khong can rig (A1 da chay thu o muc 4.3): E1-E7 thanh tieu chi pre-register (100 % / 0 vi pham) + ADD24-M chay
        hang ngay. Lam duoc ngay; khong chung minh muc stop chinh xac.
      - Can them log: ghi moi nhip exit (10 s) price_realtime + peak + priceSL cua moi cum (1 dong / cum / nhip) => replay dung chuoi gia bot thay
        qua TrailingStopManager (khong can rig) va so tung muc stop chinh xac (dung sai 1 tick). Can doi jar (logging) => theo quy trinh doi jar.
      - Mo phong MARK: rig kich stop theo markPrice kline (da co trong fx) thay last - van chi 1 phut, chi giam lech D1, khong giai D2.
(d) A1 KHONG kiem duoc: chuoi gia 10 s live thay; /dev/shm goc (chi so manifest); C0b (chi doc C0B.json); R-SIM S-X/S-D (ngoai pham vi);
    time-stop 168 h, X14, DCA, restart JVM giua chung cum tren lenh that (0 su kien trong OW2); ma nguon C3TrailRate (cong thuc suy tu du lieu);
    V1-V10a (chi doc gates.json, khong tai tinh); hang 1 ulp / thu tu dong cua blind la do Python, A1 khong chay lai bo cham.

## Phu luc - dieu A1 da lam ngoai le
- `sudo -n cp -a` de doc thu muc blind 000 ma KHONG doi quyen ban goc (theo PHAM VI: mo trong ban COPY). Ban goc: mode 0, mtime 1795524943 truoc/sau.
- Da doc book_close/fills/result.json (co truong realized / eq) de lay thoi diem & gia; KHONG in, KHONG tinh tong, KHONG ghi ra file nao.
