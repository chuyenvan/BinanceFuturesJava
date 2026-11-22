# ADDENDUM24_PILOTFID - ERRATA2 (MASTER, 2026-11-22 ~13:10 +07) - commit TRUOC khi mo OW1 / OW2
Goc: prereg 6ee84f17 + ERRATA1 29152e39. Can cu: CHI cua so DEV / DEV-2 cua R-SIM (du lieu <= 2026-06-30), so DEM tu printDone HO5 da cong
bo (khong chay rig tren OW1), ma nguon jar 76134a52. CHUA ai chay / mo / cham rig tren OW1 hay OW2. Bao cao nguon: v12/ADD24_DEV_B.md (LUOT 2),
ERRATA_PROPOSED_B.md (EB13-EB16), v12/ADD24_DEV_A.md (LUOT 2).
Moi thay doi duoi day la ve QUY UOC CUA RIG (harness) hoac dinh nghia mau; khong noi nguong nao. Cho nao lam tieu chi DE hon ban goc deu ghi ro "NOI".

## 1. S-G (gate) - sua dinh nghia mau + THEM phep thu hai chieu (CHAT hon)
- Su that tu printDone (da cong bo): OW1 co 67 leg PREDICT trong 16 phut (chien luoc vao lenh theo dot) => "mau toi thieu >= 50 PHUT" cua ban
  goc la LOI THIET KE (khong the dat o bat ky quy nao). Sua: mau toi thieu S-G = >= 50 quyet dinh (phut, symbol) PREDICT cua sim trong OW1
  VA >= 10 phut khac nhau. [NOI ve don vi mau]
- THEM S-G2 (BAT BUOC, hai chieu): rig chay gate tren TOAN BO ung vien top-24 moi phut cua 2026Q3 (07-01 00:00 -> 09-30 23:59 +07, chi gate;
  lenh van chi cham trong OW1). So (phut, symbol) jar cho PASS trong quy == so "pass" cua sim trong dong log [GATE-RATIO] 2026Q3 cua HO5 Lane L
  (BANG NHAU TUYET DOI), va "seen" lech <= 1e-4 tuong doi. Neu rig khong the chay gate het quy (thieu sel sau 09-16) => S-G2 = INSUFFICIENT
  khong phu. Tren DEV phai thay truoc: PASS jar ca quy 2026Q2 == so pass sim log 2026Q2 (DEV-B bao so; lech => sua harness truoc, khong mo OW1).
- S-G (mot chieu, giu): jar PASS tai 100 % (phut, symbol) PREDICT cua sim.

## 2. S-X (thoat) - quy uoc duong gia trong nen va mo hinh khop stop cua RIG R-SIM
Phat hien tren DEV4 (98 cum, sau khi khop gia vao theo sim): ly do thoat trung 98/98; lech con lai co co che may doc duoc:
 (i) 10 cum: rig gia dinh duong gia trong nen O->H->L->C nen nang SL tai H roi cham L CUNG nen; sim chi ap SL moi tu nen sau;
 (ii) 4 cum: rig khop stop tai moc L cua nen (thap hon SL 2-13 %) du open > SL - artefact noi suy 4 moc; sim chot min(SL, open);
 (iii) 1 cum: tick size cua snapshot exchangeInfo 20261027 khac tick sim dung.
Quyet dinh (thu tu trong nen la GIA DINH cua mo phong, khong phai logic jar; S-X do LOGIC jar duoi CUNG gia dinh voi sim):
- 2a. Lane CHINH cua R-SIM: duong gia trong nen theo quy uoc SIM = O->L->H->C; khop stop = SL neu open cua nen kich > SL, nguoc lai = open
  (dung quy tac sim min(SL, open)). NGUONG S-X GIU NGUYEN ((a) 100 %; (b) >= 95 % cung phut, con lai <= +-1' hoac N8; (c) TB trong
  [-0,8 %; 0], tung cum >= -1,5 % hoac <= 2 tick). N8 van can REF-nhip xac nhan tung cum va van bi tran 10 %.
- 2b. Lane DO NHAY (BAT BUOC chay, CHI BAO CAO, khong cham): duong gia O->H->L->C + khop stop nhu 2a. Bao cao: so cum doi phut thoat, phan
  bo Delta gia thoat (%) so voi lane chinh. Day la uoc luong "do lac quan do thu tu trong nen" cua sim HO5 - MASTER phai bao owner con so nay
  (bai hoc da ghi o FINDINGS_GRID: gia dinh thu tu trong nen thuan loi lam dep ket qua). Khong in PnL.
- 2c. Bo loc san (tickSize / stepSize / minQty) cua rig R-SIM = bo loc ma sim da dung (pin cua sim) khi khac snapshot 20261027; ghi danh
  sach symbol khac.
- 2d. Truoc khi mo OW1: chay lai cua so DEV voi 2a-2c (DEV5) va bao S-X. Neu DEV5 VAN co cum lech khong co co che => do la ung vien LECH
  LOGIC THAT: bao MASTER, KHONG mo OW1.

## 3. DCA (S-D) va S-SZ voi cum DCA
- EB13 (dinh chinh): printDone co 1 dong moi LEG => leg 0 cua cum DCA tach duoc. S-SZ cham leg 0 cua MOI cum (ke ca cum DCA) co leg 0 trong
  cua so. OW1 theo printDone: 0 su kien DCA co leg 0 trong cua so (1 cum co leg 0 ngay 06-25: loai, dem) => S-D OW1 = INSUFFICIENT-co-phu
  (C0b S-DCA PASS) NEU muc 3b duoi day khong ra lech logic.
- 3b. THEM dieu kien CHAN (CHAT hon ban goc) tu DEV-2: cum FIGHT (leg 0 2026-01-30): rig DCA som 5 ngay so voi sim khi dung dieu kien thi
  truong tu tai lap Vision. DEV-B phai phan xu bang cach nap CHINH du lieu thi truong cua sim (market.bin HO5, <= 2026-02-06): (1) rig DCA
  cung phut voi sim => lech do NGUON du lieu thi truong cua rig (harness), logic jar = sim; ghi vao gioi han + MASTER kiem rieng nguon
  dieu kien thi truong cua bot LIVE so voi sim (ngoai ADD24, truoc pilot); (2) van lech => LECH LOGIC DCA jar vs sim => ADD24 = FAIL-ung-vien,
  A1 phan xu, KHONG mo OW1 cho toi khi ro.
- 3c. Lech S-SZ -2,7..-8,8 % o 25 leg ngay 2026-02-01 00:11-01:43 cua DEV-2 (REF numpy trung jar => nghi cong thuc E_sim tai lap sai trong
  doan co DCA / nhieu cum mo): DEV-B phai tim nguyen nhan TRUOC khi mo OW1; khong tim ra => S-SZ OW1 van cham theo nguong, moi leg lech
  phai co giai thich may doc duoc, khong thi FAIL.

## 4. R-LIVE
- N9 EQ_UNAVAIL: cua so bang chung = [dts, dts + 120 s) (quyet dinh chay o giay ~6 cua phut sau nen dts; cache equity 60 s). CHUA co phep so
  nao tren OW2 khi quyet dinh nay duoc ghi.
- E-A2 chot: U_MAX = 0,60 (Configs.java:177; khong co bien SIM_U_MAX tren 242; TRADING_PROFILE: so ten bien trong conf/env.sh = 0 - A1 kiem
  them duong profile trong code khi TRADING_PROFILE khong dat).
- E-A10 chot: "phut=" = dts (+07) cho ca dong theo leg va dong ca phut; guard ca phut chan CA DCA (createOrderBuyRequest0) - rig da theo.

## 5. Thu tu
DEV-B: ap muc 1-3 -> DEV5 (+ S-G2 tren Q2) -> phan xu FIGHT (3b) -> 3c -> bao MASTER. A1 duyet harness R-LIVE (HEAD d1922e4c + thay doi N9)
song song; A1 duyet R-SIM sau khi DEV-B xong. Chi khi A1 duyet va khong con muc "KHONG mo OW1" moi chay chinh thuc.
