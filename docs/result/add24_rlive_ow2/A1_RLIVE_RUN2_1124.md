# A1 phan xu cong V truot - ADD24 R-LIVE luot chinh thuc #2 (2026-11-24 18:04:53 -> 18:15:33, EXIT 13)
A1 (Opus, doc lap), 2026-11-24 toi. CHI DOC: khong sua harness/prereg/errata/khoa/output, khong chay lane, khong cham.
Nguon: ban sao v12/rlive_run2_backup_1124/rlive_official_1124_180454 (gates.json, v4b.json, V10.json, V10_diag.json, live/{counts,tick,
tick_dts,gaps,inc_min,fin_excl*,jvm_start,gate,block}.csv, fx/sel.csv.gz cot ts, L0*/appended.csv.gz (ts, r_bits), L0/result.json chi
khoa market/buffer_*/errors/q_by_hour), pull242/2026-11-{18..23}/check.txt, pull242/2026-11-23/run/gate_ratio_live.bin.gz (ts, r bit),
dong log [GATE-RATIO] (q_t9, buffer) va 1 dong [C3-LIVE-EQ] (chi gio + ten exception), harness HEAD a66109c1, c3_hotfix 76134a52.
Script tam: v12/a1_rlive_run2_tmp/{selmin,v10a,v10b,v10c,v10d}.py.

## 0. Ket luan ngan
| Cong | Nguyen nhan goc | Loai | So luong | Bang chung chinh |
|---|---|---|---|---|
| V6 | rlive_gates.py:98 dat expect = (END-START)/60s = 7049 (do dai cua so) thay vi so phut CO INPUT (prereg s11 V6 "so phut xu ly == so phut input"; s5 dong 103 N1) | X | 275 phut N1 + 1 phut cuoi (E-A11) = 276; 0 khong giai thich | sel minutes 6774 = 7049 - 275; rig chi decide b khi co sel (CrashDayRig:717-726, marketRows chi them khi rows != rong) va b < END-1' (vong :472-482) => 6773 = 6774 - 1 |
| V10a | (a) 554 phut: trang thai GIU khac nhau (live giu, rig khong) - mien V10a gom moi phut vi menh de "HOAC truoc lech L-E dau tien" (ERRATA4 C3, v10_buffer.py:94) ma first_L_E_dev = END; (b) 1 phut: 11-24 06:59 (bien cua so, rig khong decide nen cuoi) | (a) X o dinh nghia cong; nguyen nhan sau cua khac trang thai giu = cau hoi cua buoc CHAM (L-X/L-T), A1 KHONG phan loai duoc Z/khong-Z o day; (b) X | 554 + 1 = 555 phut; 735 = 755 - 20 ban ghi | 554/554 phut: multiset r live la TAP CON bit-exact cua rig; so ban ghi thua = so symbol live-giu-rig-khong-giu o 553/554 phut (1 phut bien 11-21 16:29); 6167 phut con lai trung bit tuyet doi; q_t: cung day 9 gia tri voi live |
| V4b | Parser live_log_parse.py THIEU quy tac cho dong that C3MainEquity.java:218 "[C3-LIVE-EQ] doc income FUNDING_FEE loi"; "C9" la do shape() thay so -> 9 (live_log_parse.py:4,100-105), tag that = C3-LIVE-EQ | X | 1 dong (23/11/2026 04:07, GatewayException) | grep ma nguon; dong log that 1 lan (trung lap 2 file log, parser dedup) |
Tra loi thang: KHONG co bang chung "cung dau vao + cung trang thai ma jar tinh r khac" (Z cua gate). Phan con mo: 554 phut khac trang thai GIU
(rig khong giu 10 symbol trong khi live con giu) la dau hieu khac biet o duong THOAT/giu vi the - thuoc pham vi cham L-X/L-T/L-SL/V10b, chua
phan loai duoc trong pham vi doc cho phep.

## 1. V6
(i) Dinh nghia: prereg s11 "V6 rig: so phut xu ly == so phut input; 0 exception nuot"; s5: "pull 2026-11-19 INCOMPLETE (feat/sel 1165/1440) =>
phut khong co sel_dump = NO_INPUT (N1)"; s9.2: "Phut co input = phut co sel_dump va JVM live chay (khong N1/N3)"; ERRATA1 E-A11: "so phut rig
xu ly = N hoac N-1 (phut cuoi khong co nen sau)". Code: rlive_gates.py:98 `'expect': (E - S) // 60000` (= 7049), :100 chap nhan expect/expect-1.
(ii) So lieu: L0 / L0-FOLLOW / L0-DRY minutes 6773, errors 0. fx/sel.csv.gz: 6774 phut, first 11-19 09:31, last 11-24 06:59; thieu 275 phut.
(iii) Nguyen nhan: rig dem phut = marketRows.size() (CrashDayRig.java:1179); marketRows chi them trong decide(b) SAU `if (rows.isEmpty()) return;`
(:717-726) => phut khong co sel khong dem. Vong :472: tm < END, b = tm - 1' => nen cuoi 06:59 khong bao gio duoc decide => 6774 - 1 = 6773.
275 phut thieu = 22 khoang 12-13 phut, TAT CA trong ngay UTC 2026-11-19 (11-19 09:36 -> 11-20 05:43 +07). Kiem them: moi khoang bat dau ngay
sau dong tick cuoi (hh:mm:06) va ket thuc ngay truoc mot dong khoi dong JVM BinanceOrderTradingManager (jvm_start.csv: 24 dong; 22 khop 22
khoang; 2 con lai = 11-19 09:31:12 va 11-20 06:17:35 swap jar). check.txt 11-19: feat_minutes 1165, log_marker_minutes_GATE 1165, MainClass 24.
=> 275 phut la luc JVM live KHONG chay (vong khoi dong lai ~22 lan), KHONG phai pull thieu file: du lieu da keo ve day du cho nhung gi bot ghi.
Nhan van la N1 (dinh nghia N1 = phut khong co sel_dump trong pull) - cau "pull INCOMPLETE" trong prereg mo ta sai nguyen nhan nhung khong doi nhan.
Live buffer: 0 ban ghi trong 275 phut nay; rig: 0 (kiem bang v10c.py). K5 (4 phut guard ca phut) = 11-20 21:44, 21:45, 23:36, 23:38 (block.csv
"*|*"), KHONG lien tiep nhu "4 phut dem 20/11" goi y; ca 4 co sel => rig VAN dem (decide chay toi marketRows roi moi return o :731) - khong anh
huong V6. gaps.csv rong; fin_excl rong.
(iv) Phan loai: 276 = 275 (N1, X: expect cua cong khong tru N1 trai prereg s11+s5) + 1 (phut cuoi, X: da duoc E-A11 cho phep, code da cho
expect-1 nhung expect sai goc) + 0 khong giai thich.
(v) Prereg DA quy dinh (s5 N1, s9.2, s11 V6, E-A11). Code lech prereg.
(vi) Sua (an toan, "cong dem sai so voi prereg"): rlive_gates.py:98 expect = so ts phan biet trong fx/sel.csv.gz thuoc [S, E) (6774);
giu quy tac expect/expect-1 o :100. Tuy chon chat hon: them assert tap phut thieu sel == tap N1 (ghi ra gates.json). Tinh lai: 6773 in
{6774, 6773} => V6 ok cho ca 3 lane.

## 2. V10a
(i) Dinh nghia: ERRATA3 A4 (tap (ts, r) rig nap == buffer live, r lech <= 1e-6); ERRATA4 C3: "V10a (HUY neu truot): chi xet cac phut ma rig va
live co CUNG tap dang giu va cung trang thai so day (hoac cac phut truoc lech L-E dau tien): multiset r phai trung bit"; V10b: lech ngoai mien
-> cum lech co nhan, con lai = L-N KHONG GIAI THICH. ERRATA5 B(ii)(3): "cung dau vao + cung trang thai ma jar nap r khac => LECH LOGIC gate =>
R-LIVE = FAIL". Code v10_buffer.py: :37-40 rig appended.csv.gz ts in [S,E); :50 live ts in [S,E); :86-103 moi phut: `if t < first_dev or same`
=> so multiset bit (float32). Buffer chi co (ts, r) - KHONG co coin; coin chi suy duoc qua held_* trong V10_diag.
(ii) So lieu: live 136866, rig 137601 (+735), domain 6770, mismatch 555, outside 0, bad_frames 0, first_L_E_dev = 1795478400000 (= END).
(iii) Phan ra (v10a/b/d.py):
- Theo ngay/gio: 11-21 525 phut (12:31 -> 22:54), 11-22 29 phut (11:01 -> 11:29), 11-24 1 phut (06:59). 0 phut tren 11-19 (khong dinh toi lo
  N1), 0 quanh restart 20/11 06:17, 0 quanh 4 phut K5.
- Theo kieu: 554 phut rig > live (+1: 410, +2: 96, +3: 39, +4: 9), 1 phut rig = 0 / live = 20 (06:59). Khong phut nao cung khoa khac gia tri:
  o 554/554 phut, multiset bit cua live la TAP CON cua rig (khong co |dr| nao, ke ca 1e-6) => moi ban ghi live co ban sao bit-exact o rig.
- Theo coin: o 553/554 phut, so ban ghi rig thua == so symbol (live giu - rig giu) (V10_diag held_live \ held_rig), rig giu luon la tap con live
  giu; tong 755 ban ghi thua vs 756 symbol-phut; ngoai le 11-21 16:29 (thua 1, 2 symbol EVAAUSDT+PONSUSDT - phut bien khi mot cum live dong:
  V10 dung moc tg = t + 60 s cho trang thai live, gate that chay o ~t + 66 s; SUY DOAN, chua kiem vi can thoi diem dong cum).
  Symbol-phut: PONSUSDT 513 (11-21 14:22-22:54), EVAAUSDT 134 (14:16-16:29), PIEVERSEUSDT 48, ARIAUSDT 29 (11-22 11:01-11:29), BULLAUSDT 12,
  HUSDT 8, USELESSUSDT 5, JCTUSDT 4, BLESSUSDT 2, NAORISUSDT 1. Khong symbol nao trong 5 symbol non-ASCII / TradFi.
- 735 = 755 (thua o 554 phut) - 20 (phut 06:59 live co, rig khong).
- Gia thuyet "live ghi buffer trong phut NO_INPUT 11-19 => lech day chuyen": BAC - live 0 ban ghi trong 275 phut N1 (JVM tat), 0 trong 4 phut K5,
  0 trong 48 phut 11-21 11:08-11:55 (live khong co dong [GATE], rig cung 0). Gia thuyet "live thieu ban ghi do restart 06:17 / phut INCOMPLETE":
  BAC (0 phut lech quanh do). Day chuyen qua q_t: q_by_hour rig vs [GATE-RATIO] live: cung DAY 9 gia tri q_t9 (bit chuoi) sau START (live co
  them gia tri truoc START 0.00925871823); 98/109 gio trung khoa; 11 gio lech la do moc doi gia tri: 9 gio rig[h] == live dong h+1:01, 2 gio
  (11-22 07, 11-23 02) tre 2 gio. => ban ghi thua cua rig KHONG lam doi gia tri q nao; moc gio ghi q cua rig vs dong log live CHUA giai thich
  bang ma nguon (ghi lai, khong thuoc V10a).
- 6167 phut con lai co ban ghi: trung bit tuyet doi.
(iv) Phan loai:
- 1 phut (06:59): X - bien cua so (cung co che E-A11 cua V6: rig khong decide nen END-1'); v10_buffer.py:50 lay live ts < E.
- 554 phut: X o tang DINH NGHIA cong: menh de "hoac phut truoc lech L-E dau tien" gia dinh trang thai giu chi tach nhau khi tap SUBMIT tach
  nhau; o day tap SUBMIT khong tach (first_L_E_dev = END) nhung trang thai giu tach (rig khong giu 10 symbol trong cac khoang tren trong khi live
  con giu) => cong ep so multiset o phut KHAC trang thai. Theo dung chu ERRATA5 B(ii)(3), FAIL gate chi khi "cung dau vao + cung trang thai";
  554 phut nay KHONG cung trang thai => KHONG phai Z cua gate. Bang chung r tinh trung: moi r live co ban sao bit-exact o rig.
- Nguyen nhan cua viec rig khong giu (rig dong vi the som hon / khong giu nhu live): NGOAI pham vi doc cho phep (can exit/fill/close). Day la
  ung vien lech o duong THOAT (L-X / L-T / L-SL) hoac co che da biet (K8 nhip trong nen, K9 gia cu, FakeExchange1m) - phan loai X/Y/Z PHAI lam o
  buoc cham (V10b + L-X), khong duoc ket luan o day. Ghi chu: L0-FOLLOW cung thua 701 ban ghi, L0-DRY 718 (chi dem) => FOLLOW (dong bo fill
  vao) khong khu khac biet nay.
- Y (dau vao thieu): 0 phut.
(v) Prereg/errata: ERRATA4 C3 dinh nghia mien (co menh de gay loi); ERRATA5 B(ii) thu tuc khi V10a truot (A1 phan xu, loi harness/dau vao =>
errata + chay lai, toi da 1 lan truoc khi trinh owner); ERRATA6 D/M2: may kiem chi-V10a; o day tap truot = {V10a, V4b, V6} => "thu tuc cong V
(errata dau vao)".
(vi) De xuat:
- V10-1 (an toan, cung co che E-A11): v10_buffer.py:39 va :50 doi `t < E` / `ts < E` thanh `< E - MIN` (bo nen cuoi ca hai phia). Tinh lai: -1 phut.
- V10-2 (CAN MASTER/owner - doi dinh nghia ERRATA4 C3): mien V10a = CHI phut `same` (bo `t < first_dev or`), phut khac trang thai -> V10b (cham).
  Tinh lai tren output hien co: 554 phut ra khoi mien => V10a mismatch 0 => V10a ok; outside_domain = 554 phut -> V10b/L-N o buoc cham.
  Phuong an CHAT hon (de A1 uu tien): giu 554 phut trong V10a nhung doi phep so o phut khac trang thai: multiset r live phai la tap con bit-exact
  cua rig (hoac nguoc lai theo phia giu nhieu hon) VA |hieu| == |held_live xor held_rig|; tinh lai: 553/554 dat, 16:29 truot tru khi sua moc tg
  (t + 60 s -> thoi diem gate that). Danh gia: V10-2 KHONG noi tieu chi cham tong the (lech chuyen sang V10b -> L-N KHONG GIAI THICH neu khong
  thuoc cum co nhan) nhung bien mot cong HUY thanh muc CHAM => la thay doi dinh nghia, phai la errata MASTER + A1 duyet, khong phai "sua dem".

## 3. V4b
(i) ERRATA3 A5: "moi dong co tag [C3-LIVE*] KHONG khop quy tac nao phai duoc dem theo tag + A1 xem xet. Truot => khong cham." v4b.sh:29
ok &= unmatched == 0.
(ii) unmatched 1, bad_rules [], shape "[C9-LIVE-EQ] doc income FUNDING_FEE loi".
(iii) "C9" KHONG phai loi go: shape() (live_log_parse.py:100-105, mo ta :4 "so -> 9") thay chu so => C3 -> C9. Dong that: C3MainEquity.java:218
(c3_hotfix 76134a52) `LOG.warn("[C3-LIVE-EQ] doc income FUNDING_FEE loi {} => thu lai sau {} s", ...)` trong pollFunding(): loi doc income
=> return -1, KHONG cap nhat incomeLastMs => lan poll sau (FUNDING_POLL_MS = 600 s, :54) doc lai tu moc cu (from = max(startMs, incomeLastMs))
=> funding KHONG mat, chi tre <= 10 phut. Thoi diem: 23/11/2026 04:07:11 (1 lan; xuat hien o 2 file log chong lan, parser dedup), exception
GatewayException. api.onApiResult("income", false) -> KillSwitchEngine.onApiResult: c3Consec + 1, reset khi call ok ke tiep (KS:595-601).
Parser co quy tac EQ_UNAVAIL / EQ_NOEQ / EQ_ACCOUNT / EQ_KYQUY / FUNDING (live_log_parse.py:73-77) nhung khong co "doc income ... loi" va
khong nam trong danh sach info (:83-87).
Anh huong toi cham: N9 dinh nghia theo "positions() loi" (E-A8) - khong lien quan; bao size E_c3 dung funding cong don theo dong FUNDING
(E-A12, bien +-|funding|) - mot lan poll tre 10 phut nam trong bien do (SUY LUAN tu code, khong kiem tren lenh). Khong co duong nao tu dong nay
toi quyet dinh vao lenh/size ngoai KS C3 (1 loi don, duoi nguong lien tiep - SUY LUAN tu code, chua doc C3_CONSEC).
(iv) Loai X (quy tac parser thieu cho mot dong log production co that), 1 dong. Khong Y, khong Z.
(v) ERRATA3 A5 quy dinh: phai dem + A1 xem; truot => khong cham. Khong co dieu khoan cho phep A1 "chap nhan" thay cho sua parser.
(vi) Sua (an toan, chi them phan loai, khong doi tieu chi): them quy tac vao RULES live_log_parse.py (canh :73-77), vd
`('EQ_INCOME_ERR', ('[C3-LIVE-EQ] doc income FUNDING_FEE loi',), r'\[C3-LIVE-EQ\] doc income FUNDING_FEE loi', '', 'C3MainEquity:218'),`
(dem, khong dung cho cham). KHONG nen dua vao danh sach info (:87) vi do la "bo qua". Tinh lai: v4b quy tac moi grep 1 == tag_lines 1 ==
parsed 1, unmatched 0 => V4b ok. Luu y: grep cac dong [C3-LIVE*] khac trong ma nguon de bat dong hiem tuong tu (vd "funding ... khong on dinh",
C3MainEquity:235) truoc luot sau - de xuat A1 lam khi duyet errata.

## 4. Tong hop
(a) Loai Z: KHONG co bang chung jar tinh r khac live cung dau vao + cung trang thai. Mo: khac biet trang thai giu o 10 symbol (554 phut) - can
cham L-X/L-T/V10b de biet Z hay co che da biet.
(b) Thay doi toi thieu (ERRATA7 + A1 duyet delta truoc luot sau):
 1. rlive_gates.py:98 expect = so phut sel trong [S,E) - AN TOAN (cong dem sai so voi prereg s11/s5).
 2. live_log_parse.py RULES + quy tac C3MainEquity:218 - AN TOAN (them phan loai).
 3. v10_buffer.py:39,:50 bo nen END-1' - AN TOAN (E-A11).
 4. v10_buffer.py:94 mien V10a (bo "hoac truoc lech L-E dau tien" hoac phep so tap-con) - KHONG thuan tuy an toan: doi dinh nghia ERRATA4 C3,
    can MASTER (va bao owner); nen chon phuong an tap-con (chat hon) + sua moc tg.
 Uoc tinh sau 1-4 tren output hien co: V4b ok, V6 ok, V10a ok (hoac 553/554 voi phuong an tap-con chua sua tg). Lane rig tat dinh nen luot sau
 tren cung dau vao du kien cho cung so.
(c) Dieu khoan chay lai (trich):
 - prereg s11: "Cong kiem chung TRUOC khi cham (truot => khong cham, sua dau vao, khong doi tieu chi)"; "Chay chinh thuc 1 LAN (khoa ...).
   Lot ket qua roi moi phat hien loi harness => errata + chay lai, bao CA HAI."
 - ERRATA5 B(ii): "(2) loi harness / dau vao => errata + chay lai, bao CA HAI luot; ... (4) toi da 1 lan chay lai truoc khi trinh owner."
 - ERRATA6 D: "Moi loi SAU khi dong "errata=E6" da ghi (exit 9 build, 11, 12, 13 do loi ky thuat - vd lane khong chay vi flock het han / java
   crash / traceback, 17) = luot #2 HONG KY THUAT => DUNG; MASTER trinh owner TRUOC moi luot tiep."; M2: "Exit 13 voi cong khac truot =>
   thu tuc cong V (errata dau vao)."
 - run_rlive.sh: khoa da co dong errata=E6 => luot moi CHI voi E2E_ERRATA moi (vd E7).
 Doc cua A1: luot #1 (exit 11, truoc khi doc du lieu) = khong cham, da bao cao (ERRATA6 A). Luot #2 (exit 13, da doc du lieu OW2, lane da chay,
 CHUA cham) = luot hong do loi BO KIEM (X), khong phai loi ky thuat kieu crash; tuy nhien chu ERRATA6 D gom "13 do loi ky thuat" va ERRATA5
 B(ii)(4) gioi han 1 lan chay lai. De nghi bao thu: MASTER trinh owner ngan (3 cong X, 0 Z, thay doi 1-3 an toan + 4 can duyet) TRUOC luot #3;
 luot #3 = lan chay lai DUY NHAT (E2E_ERRATA=E7, cung OW2/T_cut/EXINFO/jar, A1 duyet delta); luot #3 truot bat ky cong V => DUNG,
 R-LIVE = INSUFFICIENT (khong phu) theo s10, trinh owner.
(d) Lam ban: luot #2 khong co score/conclusion => chua ai thay ket qua cham. A1 da thay (de MASTER can nhac): first_L_E_dev = END trong V10.json
 (ngam chi tap khoa SUBMIT live va rig L0 khong tach trong OW2 - mot phan ket qua L-E); V10_diag: 10 symbol + khoang thoi gian rig khong giu ma
 live giu (ngam chi khac biet thoat/giu); q_t live/rig; 1 dong log EQ. A1 KHONG doc submit/exec/fill/order/trail/close/cum/eq/legs/size, khong
 tinh PnL. Nhung dieu tren khong cho phep chinh nguong (nguong da chot), nhung MASTER nen ghi vao bao cao luot #3 rang A1 da biet L-E "khong
 tach khoa" va co khac biet giu o 10 symbol.
(e) Neu khong duoc chay lai: R-LIVE = INSUFFICIENT khong phu (cong V chua dat) => ADD24 INSUFFICIENT => khong pilot tu dong; MASTER trinh owner
 danh sach (V4b/V6/V10a = X, 554 phut khac trang thai giu chua cham) + lua chon: (1) cho phep luot #3 voi ERRATA7; (2) chap nhan van ban.

## 5. KHONG kiem duoc / gioi han
- Vi sao rig khong giu 10 symbol trong cac khoang (thoat som hon? khac fill?) - can doc exit/fill (cam).
- Phut bien 11-21 16:29 (moc tg) - can thoi diem dong cum live (cam).
- Moc gio q_by_hour cua rig vs dong [GATE-RATIO] live (lech 1-2 gio, cung gia tri) - chua doc ma nguon LiveGateRollingRatio/CrashDayRig phan q.
- 48 phut 11-21 11:08-11:55 khong co dong [GATE] va 0 ban ghi ca hai phia - nhat quan, khong dao nguyen nhan.
- Vong khoi dong lai JVM ~22 lan 11-19 09:36 -> 11-20 05:44 (moi lan ~12-13 phut khong chay) - van hanh, ngoai ADD24; MASTER nen biet.
- C3_CONSEC (nguong KS C3) chua doc.
