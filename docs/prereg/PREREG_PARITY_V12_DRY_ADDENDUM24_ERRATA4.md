# ADDENDUM24_PILOTFID - ERRATA4 (MASTER, 2026-11-22 ~18:00 +07) - commit TRUOC khi mo OW1 / OW2
Goc: prereg 6ee84f17 + ERRATA1 29152e39 + ERRATA2 bb91e639 + ERRATA3 050912ca. Can cu: v12/ADD24_DEV_B.md (LUOT 4, 5),
w3/add24/b/dev_results/TIER_IMPACT.md, v12/A1_ADD24_TIER.md, v12/A1_ADD24_HARNESS_R2.md, v12/ADD24_DEV_A.md (LUOT 3).
CHUA ai chay / mo / cham rig tren OW1 hay OW2.

## 0. Su co pham vi du lieu (ghi nhan, bao owner)
DEV-B (luot 5) khi tinh tier theo gio da nap file ticker cua sim theo ngay UTC "ticker_20260930", file nay chua ca 2026-10-01 00:00..06:59 +07
(7 gio thuoc vung niem phong >= 2026-10-01). Du lieu chi nam trong bo nho; 4 669 dong dau ra > 09-30 23:59 +07 da bi cat truoc khi phan
tich; khong so nao >= 10-01 duoc dung hay in; file tho da xoa. Luat bo sung (EB24): khong nap tron file ngay UTC cuoi cung cua cua so;
moi bo doc phai assert ts <= 2026-09-30 23:59:59 +07 TRUOC khi dua vao bo nho xu ly.

## 1. Phat hien: backtest (sim) cap nhat TIER "luoi" - jar production cap nhat theo gio (A1 xac nhan: loi cua SIM, jar dung y do)
- Co che (A1 doc ma nguon hai ben): sim a8690d46 chi cap nhat bang xep hang tier khi getCoinTier duoc goi dung phut :00, ma chi createOrder
  goi no (Sim:1431) => tier cua sim cu toi ~230 ngay (2026: chi 2 moc cap nhat 01-19 07:00 va 02-06 04:00). Coin chua co hang = UNKNOWN =>
  TIER_3 => sim CHAN DCA. Jar production 76134a52 cap nhat xep hang moi gio (LiveFeaturePipeline:201-207) va chan DCA khi tier3
  (C3LiveEntry:236-243). Tier KHONG anh huong vao lenh / size / thoat (TIER_FLAT=1 hai phia).
- Do lon (DEV-B, HO5 Lane L s123, 2026-01-01..09-30, mo hinh tai tao dung 6/6 leg DCA cua sim; A1 chua tai tinh): production se DCA THEM so
  voi sim o 3 cum / 3 leg (Q1: FIGHT ~0,7 % von, som hon 124 gio; Q2: SLX, OPN ~3,8 % von uoc luong; Q3: 0); chieu nguoc lai: 0.
  OW1: 0 su kien lech tier (cum GUA khong bi anh huong).
- Day la loai KHONG co trong ERRATA3 B5 (chuan so sai, jar dung). KHONG duoc tu quy ve PASS. Xu ly:
  1a. Rig R-SIM "theo vet" ca TRANG THAI TIER cua sim: tier3 dua vao jar = tier luoi cua sim (tai tao bang code CoinRankManager a8690d46
      tai dung cac moc cap nhat cua sim). Voi trang thai do, DEV-2 phai cho S-D 2/2 (FIGHT + SPACE dung phut). Khong dat => LECH LOGIC DCA
      that => ADD24 = FAIL.
  1b. Cong MOI **V-TIER** tren OW1: dem su kien TIER_DIV = (cum, phut) thoa moi dieu kien DCA khac ma tier luoi va tier theo gio cho quyet
      dinh chan khac nhau. TIER_DIV > 0 => cac cum lien quan loai khoi S-X / S-SZ / S-D, DEM + bao cao. TIER_DIV = 0 => cham theo nguong.
  1c. KET LUAN ADD24 luon mang co **SIM_TIER_STALE**: so HO5 (~23 %/nam) KHONG phan anh dung nhanh DCA cua jar voi coin moi niem yet / doi
      hang. ADD24 chi duoc ghi "PASS" khi (i) moi chi so BB dat VA (ii) owner chap nhan co nay BANG VAN BAN (commit OWNER_DECISION_*), hoac
      sim duoc sua (tier theo gio) va HO5 chay lai theo prereg rieng. Khong co (ii) => ADD24 = INSUFFICIENT khong phu (DCA).
  1d. Kiem them truoc OW1 (bao cao): symbol id >= 1000 trong sim (MAX_COINS); tap symbol nuoi HistoryManager o sim so voi live.

## 2. R-LIVE (dieu kien C1-C4 cua A1 + bo sung)
- C1 (nhan ke thua): mot muc lech duoc mang nhan cua cum goc CHI KHI: (a) thuoc DUNG cum co leg 0 lech: cung symbol, thoi diem trong
  [ts leg 0 ; ts thoat cua chinh cum do + 2'], cum chua thoat thi toi T_cut; (b) o DUNG phia cum ton tai (rig_only cho cum rig thua,
  live_only cho cum live thua); (c) nhan goc chi thuoc {N1, N2, N3, N4, N6, N9}; KHONG ke thua N5, N7, N8, KHONG GIAI THICH; (d) ghi
  "ke_thua" + khoa cum goc, dem rieng; tran N6 / N9 tinh theo cum goc; (e) cum co leg 0 khop thi khong bao gio ke thua.
- C2 (L-SL): ghep 1-1 moi lan dat / doi stop (live <-> rig) trong +-2 phut va dung sai gia; lan dat khong ghep duoc o BAT KY phia nao = lech
  (N8 chi khi co REF-nhip).
- C3 (V10 tach doi): V10a (HUY neu truot): chi xet cac phut ma rig va live co CUNG tap dang giu va cung trang thai so day (hoac cac phut
  truoc lech L-E dau tien): multiset r phai trung bit, lech dem = 0. V10b (bao cao, khong huy): lech dem ngoai V10a phai nam trong thoi gian
  ton tai cua mot cum lech da co nhan; phan con lai tinh la lech L-N KHONG GIAI THICH.
- C4: tuy chon --log-files KHONG duoc bo qua kiem P1 khi file nam duoi pull242.
- TIER3 trong rig R-LIVE: rig phai dung tier theo gio nhu production (tinh tu du lieu fixture bang CHINH code jar) neu lam duoc; neu khong,
  DEV-A neu ro ly do va lech DCA do tier3 chi duoc gan nhan **N12 TIER3_DCA** khi log live co dong ly do chan tier3 dung phut + symbol
  (DEV-A trich dinh dang dong log tu ma nguon). Khong co bang chung => KHONG GIAI THICH.
- L-D bo sung REF theo gia (bat buoc neu OW2 co DCA live): voi moi leg DCA live bac k: close nen dts <= gia khop leg 0 x (1 + muc bac k
  theo banner).
- Pham vi P1 (de owner duyet): V3 cho phep doc du lieu van hanh tu 2026-11-18 (START - 1 ngay) den T_cut.
- K7 (avail + margin): chap nhan la rui ro ghi trong ket qua (neu rang buoc xay ra thi L-S FAIL - huong bao thu).

## 3. Thu tu
DEV-B: 1a (tier luoi vao rig) -> DEV-2 lai -> V-TIER + 1d -> A1 duyet launcher R-SIM -> chinh thuc R-SIM OW1.
DEV-A: C1-C4 + tier3 / N12 + L-D REF -> A1 duyet delta -> (owner duyet P1) -> chinh thuc R-LIVE OW2.
Owner: P1; chap nhan hay khong co SIM_TIER_STALE (1c).
