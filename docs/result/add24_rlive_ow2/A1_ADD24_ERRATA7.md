# A1 duyet DELTA ERRATA7 (harness a66109c1 -> 8d397ce2) - 2026-11-24 ~20:10-20:40 +07
A1 doc lap (Opus). CHI DOC; khong chay official/go, khong sua, khong mo sandbox/blind, khong doc noi dung quyet dinh/size/gia/PnL, khong 242,
khong lay oracle_heavy.lock. Script tam: v12/a1_rlive_run2_tmp/e7_v10.py, e7_parse/ (counts.json, mode format), e7_diff_*.txt.

## VERDICT
- Harness HEAD 8d397ce2dbbdf3db72da9dd7bb4399866c675911: DUYET.
- ERRATA7_PROPOSED.md sha256 689d8f9b7d5a6180d0b117c9b2b682e98a3befc01527ebd663644e3b4f913878: CHUA DUYET - 1 loi so lieu + 3 bo sung (muc 5);
  DEV sua roi A1 duyet lai sha.
- run_rlive_e7.sh: DAT (= run_rlive_e6.sh chi doi ten E6->E7, log run3, file errata; preflight giu nguyen; khong duong nao toi official khi
  FAIL=1; khong boc flock).

## 1. Diff a66109c1..8d397ce2
5 file: live_log_parse.py (+2: quy tac EQ_INCOME_ERR), rlive_gates.py (V6 v6_lane + chep khoa V10a), v10_buffer.py (dieu kien dat V10a +
E1 = END-1'), tests/run_tests.sh (+test_errata7), tests/test_errata7.py (moi). KHONG cham rlive_score / conclude / ref_size / nguong / nhan /
lane / run_rlive.sh / fixture / buf_check / v8_check / OW2 / T_cut / EXINFO / stub. Worktree sach (porcelain 0). Mien V10a (`t < first_dev or
same`) GIU NGUYEN; khoa outside_domain_mismatch_minutes (rlive_score doc) giu nghia. Diff trong errata (dong 40-377) == git diff TUNG BYTE
(sha256 fedf4cbe...cf5 ca hai).

## 2. V10a
(a) Dung quyet dinh MASTER (phuong an chat): minute_rule() (1) sorted(L)==sorted(R); (2) assert multiset r_bits trace_dec(held=0) == appended
(khac => truot), L tap con multiset R, ton tai cach gan X = symbol(R\L) voi X == S_m ('subset') hoac X\flex == S_m\flex ('subset_trans');
nhieu symbol cung bit => xet moi to hop (tran 4096 => truot). TONG QUAT: khong co ts / symbol viet cung; flex tinh tu du lieu (flex_at,
cua so -1'/0/+1'). Khong dieu kien rieng cho 16:29.
(b) Phut chuyen trang thai: live = floor phut moc SUBMIT leg dau / book_close cum (cung nguon cl cua held_live); rig = phut co trace ma tap
held khac phut trace truoc (sau lo N1 gan vao phut dau sau lo). Hop ly (do phan giai 1' + gate chay o ~m+66 s trong khi held_live dung
moc m+60 s). Do rong: rig 187 phut / 250 su kien symbol; live <= ~40 su kien (24 SUBMIT, 16 dong cum) => tran ly thuyet ~870 symbol-phut
duoc "linh hoat", nhung flex CHI xet khi (1) va 'subset' chinh xac deu truot: tren OW2 dung 1 phut (11-21 16:29: S_m {EVAAUSDT, PONSUSDT},
X {PONSUSDT}). Thu hep ve +-0: 1 phut truot (16:29; EVAA dong cum live o phut 16:30 theo held_live). Phuong an chat hon ma van dat: cua so
{m, m+1} (mot phia) hoac dung moc log [GATE] that (gate.csv log_ms) thay m+60 s - de xuat cho sau, KHONG chan.
Kha nang che khac biet THAT: chi khi jar khac o (i) thoi diem doi trang thai giu trong +-1' cua mot moc mo/dong, voi symbol co moc do
(khong anh huong r: L van phai tap con bit-exact); (ii) rig KHONG giu symbol ma live giu (S_m) - day la khac biet giu vi the, khong phai
gate; no bi bat o L-X/L-T (xem e). Kich ban con lot: jar dat co held=0 SAI cho mot symbol rig van giu (loi trong GatePreFilter.heldPredicate
C3_LIVE_BOOK) va gate khong PASS => khong lo o L-E; nhung heldPredicate la ma production chung cho rig va live (CrashDayRig:786-795,
886-895), live chay cung ma => khong phai khac biet jar-vs-live. Luat KHONG cho phia nguoc (rig giu, live khong; R tap con L) => fail-closed.
(c) Nguon: symbol ban ghi rig = trace_dec cot symbol/held/r_bits (muc gate/buffer); trang thai live = submit.csv/book_close.csv qua code
v10_buffer (symbol + moc thoi gian, nhu truoc E7). DEV khai khong doc noi dung khac; A1 khong doc cac file do.
(d) A1 tu tinh (e7_v10.py, doc buffer live pull 11-23, appended + trace_dec L0, held_live/held_rig tu V10_diag luot #2): live 136846, rig
137601; 6769 phut; multiset trace(held=0) == appended o 6769/6769; dat (1) 6215; khong bit-exact 554, trong do 'subset' chinh xac 553,
16:29 can flex (EVAA co moc dong o m+1 theo held_live/diag) => 554 dat (2); 0 khong dat. KHOP keep/V10.json (sha ed10d944...a416).
(e) DONG Y voi MASTER (chap nhan): khac biet giu vi the la doi tuong cua tieu chi thoat. Phu: prereg s9.1 L-X ("ly do 100 %; phut >= 90 %
cung phut, con lai <= 2' (N8)"), L-T, L-SL; ERRATA3 A6 "ghep CA HAI chieu ... cum rig da thoat ma live con giu tai T_cut (hoac nguoc lai)
la lech L-X"; ERRATA3 A1 ">= 1 lech KHONG GIAI THICH => FAIL bat ke co mau"; ERRATA4 C1 ke thua chi tu N1-N4/N6/N9. Code: rlive_score.py
:486-518 two_way L-X cua so 30', "L-X rig_only (live con giu)" => bad. Khoang PONS (live giu toi 22:54, rig khong giu tu 14:22) se lo o
L-X neu la thoat lech. Dieu kien: A1 vong cham PHAI kiem 10 symbol nay xuat hien trong L-X/L-T (doi chieu V10_diag e7_S_m) - ghi vao
A1_ADD24_RESULT.

## 3. V6, V4b (A1 tu kiem bang code HEAD)
- V6: n_sel (fx/sel.csv.gz, [S,E)) = 6774, window 7049, rig 6773 in {6774, 6773} => ok (3 lane). keep/gates.json cung ket qua.
- V4b: live_log_parse.py HEAD --mode format (out tmp A1): unmatched 0, EQ_INCOME_ERR tag_lines 1 parsed 1; grep -F doc lap (sort -u, 5 ngay)
  = 1 => ok. (Khong chay v4b.sh vi no tao tmp trong /dev/shm/add24.) keep/v4b: ok, bad [], unmatched 0.

## 4. Kiem mu
- blind.sh: 3 lenh rlive_score/conclude, stdout+stderr -> blind/; rc -> tmp/blind_rc.txt (chi so). gate_trial.log / progress / bao cao DEV:
  khong co noi dung cham. blind/ d--------- (A1 khong mo; ls tu choi). sandbox out/ va tmp/ da don (chi con keep/, blind/). rlive_score ghi
  CHI vao --out (json.dump :572; labels trong out). => mu ve thu tuc. Gioi han: chmod 000 do chinh user ubuntu dat, dao duoc - niem phong la
  quy uoc, khong phai ky thuat.
- Vi pham? Prereg s11 "Chay chinh thuc 1 LAN (khoa ...)" va s15 P12 "chinh thuc 1 lan co khoa; ket qua qua A1 roi MASTER moi ket luan": chay
  bo cham tren du lieu OW2 NGOAI luot co khoa khong bi cam bang chu, nhung tao ra mot ket qua cham ngoai so sach (tat dinh => gan chac bang
  ket qua luot #3). Khong vi pham neu: (i) cong khai (E da ghi), (ii) NIEM PHONG: khong mo truoc khi luot #3 cham xong va A1 kiem; (iii) KHONG
  BAO GIO dung thay ket qua neu luot #3 hong (van INSUFFICIENT); (iv) sau luot #3 chi dung de so tat dinh. (ii)-(iv) CHUA co trong errata.
- So tat dinh an toan sau luot #3: labels.csv so byte; score.json / conclusion.json: nap JSON, thay moi chuoi bat dau bang duong dan out
  (sandbox/blind, /dev/shm/add24/rlive_official_*) bang "<OUT>", dump sort_keys, sha256 hai ben. Chi lam SAU khi ket qua #3 da chot.

## 5. ERRATA7_PROPOSED.md - doi chieu
Dung: gio / exit 13 / HEAD / P1 / dong khoa + sha 9e1cd897 / log sha dcc07f47 / 165 file / sha danh sach c9713177 / gates 562e6792 /
v4b bab16969...107f / gates luot #2 / so lieu E / diff tung byte. Can sua:
 1. Dong 22: "V10.json 45cb089c...b0dd" SAI -> "V10.json 45cb089c...afb4" (that: 45cb089c0d92bb23171dcca03c479a891c2183f21c5aa3d911fc0eefee1cafb4).
 2. Muc H them: "Output sandbox/blind (chay thu bo cham tren du lieu luot #2) NIEM PHONG: khong mo truoc khi luot #3 cham xong va A1 kiem;
    KHONG dung thay ket qua neu luot #3 hong (van INSUFFICIENT); sau luot #3 chi dung de so tinh tat dinh (chuan hoa duong dan out)."
 3. Muc F them (A1 vong ERRATA7 da thay): keep/ (gates.json, V10.json, V10_diag.json moi: e7_S_m / X / flex tung phut), blind.sha256 +
    blind_rc (ma thoat 0), live_cmp.txt (ten file SAME/DIFF), bao cao + progress DEV; A1 tu tinh lai V10a (cung so 6215/553/1/0), dem
    chuyen trang thai held cua rig (187 phut / 250 su kien), counts.json parse mode format (so dong theo quy tac, khong gia tri).
 4. Muc H dieu kien tien quyet them: khong job nao khac giu / tranh oracle_heavy.lock trong luc chay (tam dung s2_chain_v2.sh); ghi
    manifest sha256 /dev/shm/add24/vision ra dia truoc khi xoa.
Khong cau nao noi nguong cham. Quy tac luot #3 (E7, lan cuoi, cong V truot / loi ky thuat sau khoa => INSUFFICIENT khong phu, khong #4,
bao ca ba luot) DAT.

## 6. run_rlive_e7.sh + dieu kien chay
- Script dat (muc VERDICT). Preflight hien TRUOT: errata chua commit; /dev/shm/add24/vision ton tai (127 MB, 18:12); dia (DEV do 13008 MB,
  A1 do 20:2x 21909 MB - dao dong do s2_chain ghi ~4,4 GB/dot).
- Xoa /dev/shm/add24/vision: KHONG van de neu truoc do ghi manifest (ten, kich thuoc, sha256 tung zip) ra v12/. Bang chung luot #2 da co:
  fx/ (klines/mark/mkt da trich) + manifest_ow2.json sha trong ban sao; zip Vision la nguon cong khai tai lai duoc. Luot #3 tai lai =>
  so sha fx/*.csv.gz + manifest_ow2 voi luot #2 (V1) de bat thay doi nguon.
- s2_chain_v2.sh (pid 3360754 dang song) + watcher parity (pid 936196): lane cho lock <= 3600 s; flock khong cong bang, dot s2 ~20' =>
  rui ro cho qua han thap nhung khac 0; rui ro lon hon: s2 ghi ~4,4 GB/dot len / trong luc chay (run_rlive chi kiem dia luc dau, :11).
  KHUYEN NGHI: tam dung chuoi s2 (de dot hien tai xong, khong khoi dong dot moi) tu truoc preflight toi khi co EXIT_CODE luot #3; chay
  truoc khi pull242/2026-11-24/COMPLETE (watcher se cham 11-23 va giu lock). A1 khong kiem duoc co che "tu nghi khi thay run_rlive" cua s2.
- Uoc luong luot #3 hong: cong V ~3 % (rig tat dinh, cung dau vao; rui ro: Vision tai lai khac, V10a cuc doan neu lane khong tat dinh);
  ky thuat ~5 % neu s2 van chay (lock/dia), ~2 % neu tam dung.

## 7. KHONG kiem duoc
- Co che s2_chain_v2 tu nghi; khong chay test java (guard_gate, full_tier3); khong kiem dev1105 cua E7; tinh tat dinh lane chua kiem bang
  chay lai; tg/moc dong that 16:29 (can book_close); khong mo blind/ nen khong xac nhan noi dung chua duong dan.

## DUYET LAI ERRATA (2026-11-24 ~20:50)
- DUYET ERRATA7_PROPOSED.md sha256 bbaa31f0d15390524961f0cb42d976fc58decf9af85869de72f5d33a9be1d137 (485 dong). HEAD add24_wt van 8d397ce2dbbdf3db72da9dd7bb4399866c675911, porcelain 0.
- diff vs .bak (689d8f9b): CHI 3 hunk - dong 22 sha V10.json du 64 ky tu == file sao luu (45cb089c...cafb4); muc F them A1 vong delta + MASTER (ke ca MASTER da doc 24 dong SUBMIT 21/11 truoc luot #2); muc H them NIEM PHONG blind/ + dieu kien van hanh (tam dung s2_chain, manifest vision truoc khi xoa, chay truoc pull 11-24 COMPLETE).
- Khoi diff code (dong 40-377) == git diff a66109c1 8d397ce2 tung byte. Khong cau moi nao noi nguong / doi pham vi.
