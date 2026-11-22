# ADDENDUM24_PILOTFID - ERRATA5 (MASTER, 2026-11-22 ~18:40 +07) - commit TRUOC khi mo OW1 / OW2
Goc: prereg 6ee84f17 + ERRATA1-4 (29152e39, bb91e639, 050912ca, 03bb65e0). Can cu: v12/A1_ADD24_HARNESS_R3.md (R-LIVE dff0354d:
DUYET-CO-DIEU-KIEN), v12/A1_ADD24_RSIM_LAUNCHER.md (R-SIM: launcher L1-L13 chap nhan; bo cham KHONG DUYET - R1..R7), v12/ADD24_DEV_B.md
(LUOT 6, 7), v12/ADD24_DEV_A.md (LUOT 4). CHUA ai chay / mo / cham rig tren OW1 hay OW2. Khong noi nguong nao.

## A. R-SIM - bo cham (loi code so voi errata da chot; KHONG doi luat)
- R1: mau S-G theo ERRATA2 (>= 50 quyet dinh (phut, symbol) VA >= 10 phut); moi lenh PREDICT cua sim bi jar REJECT (khong phai N10)
  => S-G FAIL bat ke co mau.
- R2-R5: moi chi so: >= 1 lech KHONG GIAI THICH => FAIL bat ke co mau; INSUFFICIENT khong bi de boi PASS_N11; S-X kiem mau toi thieu
  (>= 30 cum thoat, >= 1 time-stop, >= 1 trailing) va (a) ly do thoat 100 % la mot TRANG THAI rieng; MOI cum sim trong cua so phai co
  trang thai - cum rig khong vao / khong thoat ma khong co nhan (N10 / TIER_DIV) => FAIL.
- R6 (S-D): voi du lieu thi truong toan san da nap (rig CO nhanh DCA): leg DCA cua rig ma sim khong co (khong phai TIER_DIV) => FAIL;
  0 su kien o ca hai phia => INSUFFICIENT-co-phu (phu boi C0b S-DCA PASS; DEV-2 S-D 2/2 la bao cao kem), KHONG ghi "PASS".
- R7: gop ket luan R-SIM bang SCRIPT (S-G, S-G2, S-SZ, S-X, S-D, N8, N10 > 5 %, N11, V-TIER, cac cong V, co SIM_TIER_STALE) + test tong hop
  (tiem: 1 lenh sim bi REJECT; 1 phut thoat; 1 size; 1 ly do thoat; 1 cum mat) - tat ca phai ra FAIL.
- Cong lap dat: L3 (defer time-stop) va L12 (Proxy tier luoi) phai assert "da lap TRUOC phut START cua rig"; khong dat => HUY luot.
- L9 (ghi nhan quy tac da dung o scorer): khi SL duoc DAT ngay trong nen khop thi gia khop = SL (khong ap min(SL, open)).
- EB28 / EB29 (sua dau vao bo cham, khong doi tieu chi): margin cua vi the bi huy niem yet van nam trong U cua sim toi khi sim dong no
  (moc gio dau tien sau timeUpdate + 2 ngay); thu tu cac leg BIG_DOWN cung tick theo thu tu duyet cua sim (HashSet theo id).
  Sau khi sua: DEV-2 S-SZ max 7,7e-5 (truoc: FAIL), 0 leg khong giai thich, 0 N11.
- EB30 (lech THAT, nho - ghi vao gioi han + bao owner): khi co >= 2 leg BIG_DOWN cung tick, production duyet theo thu tu khac sim (bam chuoi
  vs bam id) => size TUNG leg lech khoang +-4 %, tong margin cua tick gan nhu khong doi. S-SZ (goi ham jar voi E, U cua sim) khong do duoc
  diem nay. Ket luan ADD24 mang them co **BD_ORDER**.
- Du lieu thi truong toan san cho OW1: chi cac ngay UTC can cho dieu kien DCA (DEV-B: 09-15..09-22), EB24 (khong nap ngay UTC >= 09-30).

## B. R-LIVE
- D1 (MAJOR cua A1): "so day" cua gate trong production tinh tren SO GIAY (ShadowBookC3), khong phai so c3. Rig va V10a lay trang thai
  "so day" THEO VET live: dong "[GATE] ... n_skipfull=" cung phut (n_skipfull > 0 = day). Parser them quy tac [GATE] + V4b. Bang chung N6 =
  n_skipfull > 0 (khong phai chuoi 'skipFull'). Test: so c3 cua rig day ma live n_skipfull = 0 => rig van nap r, V10a khong lech.
- (i) TIER3 o R-LIVE (thay cach gan nhan N12 sau su kien): THEO VET tier cua live bang log - moi dong "[C3-LIVE] skip SYM DCA_* TIER3_DCA"
  tai dts => tiem (dts, SYM, level) vao block.csv (co che E2E_LIVE_BLOCK_FILE). Rig DCA ma live khong co dong TIER3 cung phut = lech KHONG
  GIAI THICH. Dem so cum bi tiem; > 3 cum => L-D = INSUFFICIENT khong phu.
- (ii) V10a la cong KHONG CHAM (exit, khong ket luan). Thu tuc khi truot: (1) A1 phan xu nguyen nhan tu tap (ts, r); (2) loi harness /
  dau vao => errata + chay lai, bao CA HAI luot; (3) cung dau vao + cung trang thai ma jar nap r khac => LECH LOGIC gate => R-LIVE = FAIL;
  (4) toi da 1 lan chay lai truoc khi trinh owner.
- Pham vi P1 trinh owner: du lieu van hanh bot + kline / markPrice cua symbol lien quan tu 2026-11-18 09:31 +07 den T_cut (2026-11-24 07:00).

## C. Thu tu
DEV-B: A (R1-R7, cong lap dat, mkt OW1) -> A1 duyet delta -> chinh thuc R-SIM OW1 (1 lan, co khoa). DEV-A: B (D1, tiem tier3) -> A1 duyet
delta -> [owner duyet P1; EXINFO; pull 11-23 COMPLETE] -> chinh thuc R-LIVE OW2.
