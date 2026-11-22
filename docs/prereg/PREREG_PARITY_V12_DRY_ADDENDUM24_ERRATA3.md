# ADDENDUM24_PILOTFID - ERRATA3 (MASTER, 2026-11-22 ~15:30 +07) - commit TRUOC khi mo OW1 / OW2
Goc: prereg 6ee84f17 + ERRATA1 29152e39 + ERRATA2 bb91e639. Can cu: A1 duyet harness R-LIVE (v12/A1_ADD24_HARNESS.md: stub + C0 / C0b DUYET;
harness R-LIVE HEAD d1922e4c KHONG DUYET - 1 BLOCKER, 8 MAJOR); DEV-B luot 3 (v12/ADD24_DEV_B.md, cua so DEV / DEV-2, du lieu <= 2026-06-30).
CHUA ai chay / mo / cham rig tren OW1 hay OW2. Khong noi nguong nao tru cho ghi "NOI".

## A. R-LIVE (sua harness + dinh nghia; A1 duyet lai HEAD moi truoc luot chinh thuc)
- A1 (BLOCKER B1 - loi code, KHONG doi prereg): moi chi so co >= 1 lech KHONG GIAI THICH => FAIL bat ke co mau; INSUFFICIENT chi khi 0 lech
  khong giai thich VA mau < toi thieu. Gop ket luan s10 lam bang SCRIPT.
- A2 (N3 dinh nghia MOI, thay E-A6): JVM_DOWN = phut dts CO sel_dump nhung live KHONG co dong tick quyet dinh cho dts (dong "Btc ticker size
  ... -> dts" hoac dong tuong duong do A1 xac nhan tu ma nguon). N3 KHONG ap cho lech "live co, rig khong" (live da SUBMIT thi JVM dang chay).
- A3 (N4 pham vi): EXCH_REJECT chi giai thich lech "rig co leg / cum, live khong co vi the" khi CHINH lenh live cung (phut, symbol, legIdx)
  co bang chung tu choi / het han theo cid. KHONG ap cho lech "live co, rig khong". Symbol lay theo cid, khong lay symbol dau tien sau tu khoa.
- A4 (cong MOI V10 - buffer gate): phut bi guard ca phut chan thi rig KHONG duoc goi gate (production return truoc gate). Tap (ts, r) rig nap
  vao buffer trong OW2 phai trung tap ban ghi cua buffer live (lay tu file gate_ratio_live cua lan pull SAU OW2) cho cac phut OW2: so ban ghi
  lech <= 1e-4 tuong doi va r lech <= 1e-6. Truot => sua dau vao / harness, KHONG cham.
- A5 (cong MOI V4b): voi MOI loai dong parser dung (SUBMIT, FILL stream, FILL REST, "KHONG khop", "KHONG vao lenh" / skip, TRAIL arm / place /
  move, exitFill, thoat MARKET / -2021 / FLATTEN / thanh ly, -4130, MINUTE-*, khoi dong JVM, C3-LIVE-EQ loi): so dong parser doc == grep -c
  doc lap; va moi dong co tag [C3-LIVE*] KHONG khop quy tac nao phai duoc dem theo tag + A1 xem xet. Truot => khong cham.
- A6 (ghep hai chieu): L-T / L-SL / L-X ghep CA HAI chieu - arm / stop / thoat THUA cua rig la lech; cum rig da thoat ma live con giu tai
  T_cut (hoac nguoc lai) la lech L-X.
- A7 (U_before): kiem U_before theo margin PENDING tai thoi diem SUBMIT nhu Java (khong dung gia khop den SAU SUBMIT); leg chua co gia khop
  khong duoc dat avg = 0.
- A8 (N8 cho L-X / L-T): chi gan khi co REF-nhip xac nhan cung phut (nhu S-X); khong gan tu dong theo "lech <= 2 phut".
- A9 (V8 danh sach khai truoc - CHOT, thay danh sach rong cua DEV): duoc phep khac CHI cac cap: moi truong la DUONG DAN file / thu muc;
  [C3-LIVE] PUSH / killSwitch exists; [UNIVERSE-A1] sha256, serverTime (va so symbol neu snapshot khac - phai liet ke); [TS-EXT]
  LIVE_TS_MKT_EXT va cac truong suy tu no (X14, file, days_loaded); adapter; ten host. MOI tag banner live in luc khoi dong deu phai so
  (ke ca GATE-PRE, MINUTE-GUARD); khoa chi-co-o-live la LECH tru khi nam trong danh sach nay.
- A10 (nho, bat buoc lam): N9 = [dts, dts + 120 s) (ERRATA2); cua so mark gom nen dts+1; phi vao cua cum da dong tru vao E_lo; SUBMIT
  thieu nen (no_px) => leg do INSUFFICIENT (khong tinh OK); V3 phu MOI dau vao; luot chinh thuc build lai test-classes tu HEAD va kiem
  worktree sach; L-D kiem bac; L-SL kiem "co stop sau arm"; N5 doi rang buoc nhan qua (lech goc co nhan N1-N4 / N6 / N9 xay ra TRUOC va
  cung symbol hoac lam doi U); result cua rig ghi ra ban KHONG co truong equity / PnL.
- A11 (rui ro phai ghi vao ket qua): trang thai sau restart JVM khong tai hien trong rig; bang chung N9 thua (log throttle 10 phut);
  K7 (avail + margin) khong kiem; mau nho (1 ngay vao lenh).

## B. R-SIM
- B1 (S-X (b) - lam ro cach doc): ti le ">= 95 %" tinh tren (so cum cung phut + so cum N8 co REF-nhip xac nhan) / tong; N8 van <= 10 % tong;
  moi cum khac phai <= +-1'. Cum lech KHONG co co che => FAIL. [NOI: ban goc doc theo chu la >= 95 % cung phut truoc khi gan N8. Ly do: voi
  duong gia O->L->H->C van con truong hop H nang SL roi C cham SL trong cung nen; sim thoat o nen sau - lech so sach 1 phut, co REF.]
- B2 (S-X (c)): sau khi mo hinh khop stop da trung sim (ERRATA2 2a), TB Delta(rig - sim) / sim phai trong [-0,2 % ; +0,2 %] (ban goc
  [-0,8 % ; 0]: can duoi CHAT hon, can tren NOI 0,2 diem %); tung cum |Delta| <= 1,5 % hoac <= 2 tick, tru N8.
- B3 (S-G2 voi N10): khi jar chan mot lenh sim bang guard production (N10), rig coi symbol do la "dang giu" trong dung khoang sim giu
  (de tap ung vien va buffer gate cua rig trung trang thai sim). Sau do S-G2 cham THO (bang nhau tuyet doi, khong loai tru gi).
- B4 (S-SZ, bo sung 3c): leg lech qua nguong chi duoc gan nhan **N11 E_SIM_SRC** khi phut do co >= 3 leg sim va E suy nguoc tu cac leg
  trung nhau <= 1e-4 (ham size cua jar tai lap dung ti le giua cac leg voi mot E chung). N11 > 2 phut trong OW1 => S-SZ = INSUFFICIENT
  khong phu (can ticker cua sim de phan xu). Leg lech khong du dieu kien N11 => FAIL.
- B5 (3b FIGHT - van CHAN): ket qua DEV-2: voi CHINH du lieu thi truong cua sim, ham jar cho DCA FIGHT luc 02-01 00:10; sim DCA 02-06 04:01
  => khong phai do nguon thi truong. Truoc khi mo OW1 phai phan xu bang MA NGUON + log sim: liet ke MOI dieu kien DCA cua sim (a8690d46:
  tier, U / budget null, nhip DCA, so, gate, thu tu trong tick ...) va cua duong production jar (C3LiveHook, C3LiveEntry - ke ca tier3 ma
  harness dang truyen false), danh gia tung dieu kien cho FIGHT tai 02-01 00:10. Ket luan mot trong ba:
  (1) HARNESS thieu mot dieu kien ma production jar CO (vd tier3) => dua dieu kien that vao harness, chay lai DEV-2, S-D DEV-2 phai 2/2;
  (2) jar production THIEU / KHAC dieu kien cua sim => LECH LOGIC DCA that => ADD24 = FAIL (khong mo OW1); MASTER bao owner;
  (3) khong phan xu duoc trong thoi gian => ADD24 = INSUFFICIENT khong phu (DCA), trinh owner.
- B6 (bao cao bat buoc cho owner, khong cham): lane do nhay cua so DEV (O->H->L->C): 41 / 98 cum doi phut thoat; Delta gia thoat so voi
  lane chinh TB -0,91 %, trung vi 0, p05 -9,1 %. OW1 bao cung dinh dang.

## C. Thu tu
DEV-A sua A1-A10 -> chay lai C0b, dev1105, cac test A1 yeu cau (lech o mau nho => FAIL; rig thua => FAIL; fill sau submit => U nhat quan;
tiem "*|*" => 0 lan goi gate) -> A1 duyet lai. DEV-B: B1-B4 + phan xu B5 -> A1 duyet R-SIM. Sau do moi chay chinh thuc (R-LIVE con can
owner duyet P1).
