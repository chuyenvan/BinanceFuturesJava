# ADDENDUM24_PILOTFID - ERRATA1 (MASTER, 2026-11-22 ~10:55 +07) - commit TRUOC moi luot chinh thuc
Goc: PREREG_PARITY_V12_DRY_ADDENDUM24_PILOTFID.md (6ee84f17). Nguon de xuat: ~/claude_master/w3/add24/ERRATA_PROPOSED_A.md (DEV-A, E-A1..15),
ERRATA_PROPOSED_B.md (DEV-B, EB1..12). Can cu: CHI fixture da co (fx1105), banner khoi dong live 2026-11-20 06:17, DEM dong log OW2, va cua so
DEV cua R-SIM (lenh sim start 2026-04-01..06-15). CHUA ai chay / mo / cham R-LIVE tren OW2 hay R-SIM tren OW1. Trang thai cong: C0 PASS,
C0b PASS (0 dong lech, 78 leg) - stub md5 cf0f479241265de68836716ee66a1866.
Kiem ten bien tren 242 (MASTER, chi ten, 2026-11-22 10:50): so ten bien SIM_U_MAX / U_MAX / LIVE_U_MAX trong conf/env.sh = 0.

## A. R-LIVE
- E-A1 (s9.3): cong thuc bao size DUNG = b = min(sizeCap x C_eff ; C_eff x F_BASE x (1 - U/U_MAX) / sum(w) x ratio(legIdx)), ratio(leg) =
  w[leg] x SCALE; hang so tu banner live: F_BASE 0,015; SCALE 6; weights [1,1,1,1]; sizeCap 4,5 %  => leg0 = 0,0225 x C_eff x (1 - U/U_MAX).
- E-A2: U_MAX khong co trong banner va KHONG co bien nao dat no tren 242 (dem = 0) => jar dung mac dinh trong code (Configs.U_MAX): DEV-A
  trich dong code + gia tri vao bao cao, A1 kiem; gia tri do la U_MAX cua bao size.
- E-A3 / E-A4: override khai truoc cua rig R-LIVE: SHADOW_NO_PUSH=false, LIVE_ENTRY_ENABLED=true, LIVE_TS_MKT_EXT=0 (X14 khong the kich trong
  OW2), LIVE_ADAPTER=dry, C3_CAPITAL=1000, LIVE_IS_SHADOW_HOST=true, duong dan du lieu. Truong banner duoc phep khac o V8: duong dan file,
  PUSH / killSwitch exists luc 06:17 (file KILL_SWITCH cua script swap), sha256 / serverTime exchangeInfo, LIVE_TS_MKT_EXT.
- E-A5 (L-S): khoang gia ngam = HOP [low, high] cua nen dts va nen dts+1 (quyet dinh chay o giay ~6 cua phut sau nen dts - K4).
- E-A6 (N3): phut JVM_DOWN = phut khong co dong log nao HOP {phut co dong khoi dong MainClass BinanceOrderTradingManager, phut ke tiep}.
- E-A7: exchangeInfo cho R-LIVE = file run/c3live_exchangeInfo.json cua 242 do MASTER chep ve (chi doc) SAU khi owner duyet P1; ghi sha256;
  khac sha banner 06:17 la truong khai truoc (file duoc lam moi 4 lan / gio).
- E-A8: THEM nhan dong **N9 EQ_UNAVAIL**: live co dong "[C3-LIVE-EQ] positions() loi" trong [dts, dts+1'] va rig SUBMIT ma live khong.
  Gioi han: N9 > 2 phut-SUBMIT => MASTER bao owner (loi doc equity dang chan lenh that).
- E-A9: chap nhan L0-FOLLOW-lite (dong bo gia khop vao lenh). Lech day chuyen do TAP lenh khac ma FOLLOW-lite khong chung minh duoc => KHONG
  duoc gan N5 => KHONG GIAI THICH (bao thu).
- E-A10: cach anh xa "phut=" cua dong MINUTE-INCOMPLETE / MINUTE-FIN-EXCL sang nen quyet dinh PHAI xac minh tu MA NGUON jar (76134a52), trich
  dong code vao bao cao; A1 kiem TRUOC luot chinh thuc. Chua xac minh => khong chay chinh thuc.
- E-A11 (V6): so phut rig xu ly = N hoac N-1 (phut cuoi khong co nen sau).
- E-A12 (E_c3 trong bao size): phi moi khop trong [0 ; 0,0005 x notional]; funding trong +-|funding c3 cong don theo log|; cong thuc E_c3 lay
  tu C3MainEquity (trich code).
- E-A13: L-SL ghep moi lan dat / doi stop live voi lan cua rig cung symbol gan nhat ve gia trong +-2 phut (khong co => lech); L-X ghep theo
  thu tu thoat trong tung symbol.
- E-A14: markPrice 1m = Vision markPriceKlines (tai CHI sau P1). E-A15: BO L-SIMQ; L-10K chi bao cao.

## B. R-SIM
- EB1: von size sim E_sim = MTM chup tai moc gio gan nhat truoc t (BudgetManagerSimple.equityNow); U_sim nhu ERRATA_PROPOSED_B. Da kiem 16/16
  phut DEV (<= 1,2e-5).
- EB2 (S-SZ): so SAU cung phep lam tron: qty_jar = floor(f_jar / entry, stepSize); chi so = |qty_jar x entry - margin_sim| / margin_sim;
  NGUONG GIU NGUYEN (<= 1e-3 o >= 90 %, <= 5e-3 o 100 %); bao cao kem chi so goc. Cum DCA (khong tach duoc margin leg 0) loai khoi S-SZ, dem.
- EB3 (S-G): sel = DAY DU top-24 ung vien cua sim MOI phut; "theo vet" = tap LEGACY dong (symbol khong phai lenh sim o phut do va khong
  dang giu => van qua gate + nap r, khong vao lenh). S-G = jar PASS tai moi (phut, symbol) PREDICT cua sim. Them cong **V9**: so ban ghi
  warm-up buffer tai lap / so sim log theo quy trong 1 +- 1e-4.
- EB4: override rig R-SIM: LIVE_TS_MKT_EXT=1 + co TS_EXT cua sim nap vao TsMktExt cua jar; khong loc A1 (K11); C3_CAPITAL=10000;
  LIVE_ADAPTER=dry; LIVE_APPLY_GRID_RATIO=true; LIVE_DCA_GRID_ENABLED=true; C3_EXCLUDE_LEGACY_HELD=false. OW1 KHONG co ngay TS_EXT => dieu
  kien mau X14 cua S-X khong ap cho OW1; logic X14 chi co bang chung o cua so DEV (bao cao kem, KHONG tinh la chinh thuc) - ghi vao gioi han.
- EB5 / EB6 (S-D): DEV-B thu dung duong DCA tren cua so **DEV-2** (cum sim co DCA, start < 2026-04-01, du lieu <= 2026-06-30) trong toi da
  3 gio cong. Dung duoc => OW1 tai mkt toan thi truong Q3 vao tmpfs va cham S-D. Khong dung duoc (printDone khong co thoi diem leg dau)
  => S-D = INSUFFICIENT-co-phu (C0b S-DCA PASS), cum DCA cua OW1 loai khoi S-X va S-SZ, DEM + ghi vao gioi han cua gate PILOT.
- EB7: R-SIM dung --patch-settling (status SETTLING -> TRADING tren BAN SAO fixture exchangeInfo 20261027); ghi danh sach symbol da patch.
- EB8: THEM nhan dong **N10 PROD_GUARD**: sim vao lenh nhung jar chan bang guard production co dong log ly do (NOT_BUYABLE DELIVERY_SOON ...)
  dung phut + symbol. Lenh N10: S-G van cham (gate phai PASS), loai khoi S-X / S-SZ, DEM. N10 > 5 % so lenh PREDICT sim cua OW1 => ADD24
  KHONG duoc PASS neu khong co chap nhan bang van ban cua owner (jar bo nhieu lenh ma sim co).
- EB9 / EB10 / EB12: sua harness (nen BTCUSDT cho KillSwitch C1; defer time-stop = TsMktExt::deferTimeStop cua jar; nap warm-up bang
  GateRatioBuffer.bulkAdd sau init) - khong doi tieu chi; A1 phai soi launcher reflection cua DEV-B (khong duoc lam jar chay khac duong
  production ngoai cac diem khai o day).
- EB11 (S-X) - BUOC 1 (chot): "theo vet" gom ca GIA VAO: FakeExchange khop leg 0 tai gia vao cua sim (close nen sim) - ly do: S-X do LOGIC
  THOAT voi cung vi the; lech gia vao (S-E, chi bao cao) khong duoc lam lech nguong arm. NGUONG S-X GIU NGUYEN. DEV-B chay lai cua so DEV
  (DEV4), phan loai phan lech con lai (nhip trong nen K8 / mo hinh khop stop nen gap) kem REF-nhip.
  BUOC 2 (CHUA chot): neu sau DEV4 van con lech co he thong do quy uoc (khong do logic jar), MASTER ra ERRATA2 TRUOC khi mo OW1; khong co
  ERRATA2 => OW1 cham theo nguong goc.

## C. Thu tu
DEV-A / DEV-B ap errata nay vao harness -> DEV-B DEV4 + DEV-2 -> (ERRATA2 neu can) -> A1 duyet harness + launcher + REF + script nhan ->
luot chinh thuc R-SIM OW1 (khong can P1) va R-LIVE OW2 (CAN owner duyet P1; T_cut 2026-11-24 07:00 +07) -> A1 kiem ket qua -> MASTER ket luan.
