# A1_ADD24_RSIM_DELTA - A1 duyet delta bo cham + luot chinh thuc R-SIM (DEV-B luot 7-8) - 2026-11-22 ~19:30 +07
Luat: prereg 6ee84f17 + ERRATA1-5 (29152e39, bb91e639, 050912ca, 03bb65e0, 0740e790); owner chap nhan SIM_TIER_STALE (e4c1a8e1).
Khong mo / chay OW1. Ban sao: ~/claude_master/w3/add24_audit/rsim/snap2. File doi so voi ban A1 da audit luot 3: score_rsim.py,
run_official_rsim.sh; MOI: verdict_rsim.py, test_inject.py, dev8_run.sh (cac file khac + jsrc TRUNG). Danh sach duyet:
~/claude_master/w3/add24_audit/rsim/SHA256_A1_APPROVED_RSIM.txt (25 script/MD5SUMS + jsrc + classes + DEV2W/env_used.sh; ban live TRUNG ban chup).

## PHAN QUYET: DUYET-CO-DIEU-KIEN cho luot chinh thuc R-SIM OW1 - dieu kien la THU TUC (khong sua code, khong doi sha):
P1 chay DUNG cac file trong SHA256_A1_APPROVED_RSIM.txt (sha256sum -c truoc khi chay; lech => khong chay); P2 chay 1 LAN: neu script dung giua
chung (bat ky exit != 0 sau buoc rig OW1_p1) => KHONG chay lai, trinh A1 + MASTER (errata) - vi khoa hien chi co file .done o CUOI;
P3 doc ket qua: RESULT 'PASS_CAN_OWNER' phai doc kem FLAGS - N10_CAN_OWNER=true => can owner chap nhan N10 bang van ban; BD_ORDER (EB30)
luon bat => ghi vao gate PILOT (owner da chap nhan SIM_TIER_STALE, CHUA chap nhan BD_ORDER / N10).

## 1. Bang dong / con mo
| Muc | Trang thai | Bang chung |
|---|---|---|
| R1 S-G mau + REJECT | DONG | score_rsim.py:55-57 (FAIL neu sg_bad; PASS khi >= 50 qd VA >= 10 phut); verdict_rsim.py:40-42; test_inject (a) FAIL; DEV8 97 qd / 14 phut => PASS |
| R2 S-SZ | DONG | score_rsim.py:125-127; verdict_rsim.py:59-80 (leg > 1e-3 khong N11 => FAIL; nostep => FAIL; N11 > 2 phut / n < 50 => INS); (c) FAIL |
| R3 S-X mau | DONG | verdict_rsim.py:92-93 (>= 30 / >= 1 time-stop / >= 1 trail), st3: lech => FAIL truoc mau |
| R4 S-X(a) ly do | DONG | verdict_rsim.py:106 a_reason status rieng; (d) FAIL |
| R5 moi cum co trang thai | DONG | verdict_rsim.py:84-90 SCORED / N10 / DCA_CUM / NO_EXIT_SAU_END, con lai MISSING => FAIL; (e) FAIL |
| R6 S-D | DONG | score_rsim.py:224; verdict_rsim.py:116-118 (rig_extra => FAIL; 0 su kien => INSUFFICIENT_CO_PHU); (f) FAIL |
| R7 gop ket luan | DONG | verdict_rsim.py:120-124 HUY > FAIL > INSUFFICIENT > PASS_CAN_OWNER; N10 > 5 % => FLAGS CAN_OWNER; SIM_TIER_STALE + BD_ORDER luon bat |
| m1 cong lap dat | DONG | verdict_rsim.py:27-31 (x14 / simtier rig_t <= START, khong => HUY); DEV8 rig_t = START |
| m3 L9 | DONG (ghi LAUNCHER_NOTES LUOT 8 + ERRATA5) | |

## 2. Test
- test_inject.py (DEV, chay tren ban sao DEV8 cua A1): a REJECT, b thoat +3', c size x1,01, d ly do, e mat cum, f rig DCA thua => FAIL ca 6; g = PASS_CAN_OWNER.
- A1 rieng (a1_rsim_inj2.py): X1 cua so 06-01..06-08 + 1 thoat +3' => FAIL (S-X); cua so 04-01..04-20 khong tiem => INSUFFICIENT (dung);
  X3 them 3 N10 (6,2 %) => RESULT van 'PASS_CAN_OWNER' nhung FLAGS.N10_CAN_OWNER = true (=> dieu kien P3); X2 2 leg size x1,002 => khong
  bat: lech bi lam tron qty hap thu (EB2 so SAU lam tron - dung thiet ke, khong phai loi).
- Ghi chu: S-SZ cham MOI dong ssz_jar.csv (khong loc theo cua so lo/hi) - dung cho luot chinh thuc (ssz_in xay theo cua so OW1).

## 3. EB28 / EB29 (ssz_inputs_l7.py) - DUNG theo ma nguon a8690d46
- EB28: Sim:472-480: moi moc gio (time % 1h == 0) TRU nhanh 00:00 UTC (time % DAY == 0 di nhanh updateBalance rieng) -> updateSymbolDeListed
  :907-913 dong khi order.timeUpdate < time - 2 ngay, priceTP = lastPrice. _rel() = moc gio dau tien > end + 2 ngay, bo moc 00:00 UTC => khop.
  Margin van trong marginRunning toi luc closeOrder => giu trong U dung.
- EB29: Sim:352-376 symbol2BUY = HashSet<Short>, duyet for(short id : symbol2BUY) -> createOrderBUY truoc DCA / selector. Thu tu duyet HashMap
  = bucket (hash Short = gia tri; id & (cap-1)) roi thu tu chen; resize giu thu tu tuong doi => _hs_order() dung (cap 16, nguong 0,75).
- Hop le? CO: tai lap CO CHE cua sim tu ma nguon (khong tham so tu do, khong doi nguong); phat hien tu lech DEV-2 (cua so DEV, khong phai OW1).
  Gioi han: nhan dien huy niem yet dua vao deliveryDate cua exinfo fixture 20261027 + status STOP_LOSS_DONE (heuristic, ghi chu).
- EB30 (BD_ORDER) la lech THAT production vs sim (HashSet<String>) - S-SZ khong do; co luon bat. Dung.

## 4. Mkt toan san OW1 (09-15..09-22 UTC)
- Lap luan "chi can ngay gia cham bac": rig theo vet (vao cung phut, gia vao = gia sim), gridDue chi true khi close <= first x (1+muc bac) - phu
  thuoc GIA, khong phu thuoc mkt; mkt chi can o phut gia da cham. Add24PriceDue = DcaUtils.shouldDcaGrid jar tren gia sim => tap phut co the DCA
  cua rig duoc phu day du, voi 2 dieu kien: (a) gia sim (closes, tk26) == kline Vision cua rig (DEV-B: lech 0 cho vi the mo) va (b) rig giu cum
  khong lau hon sim (S-X kiem: lech <= 1' hoac FAIL / MISSING). Thoa => khong bo sot rig_extra. OW1: ngay mkt chi phuc vu cum AIN (leg0 09-16 01:45,
  NGOAI cua so cham) => S-D OW1 ky vong 0 su kien => INSUFFICIENT_CO_PHU.
- EB24: dl_mkt_days.py:11 tu choi ngay UTC >= 09-30, :34 cat ts > 09-30 23:59:59 +07 truoc khi giu; mkt_filter.py:32 assert; dl_klines.py zip
  THANG 09 (chua 10-01 00:00-06:59 +07) doc theo dong, bo t > TS_MAX TRUOC khi giu (:58) + assert (:61) - byte nen cua 7 gio nay co qua bo nho
  (khong tranh duoc voi zip thang) - NOTE; dl_avail :46, dl_ref :21 loc tuong tu; conv_rsim / build_fx / vtier assert.

## 5. run_official_rsim.sh
- Errata bat buoc dung 5 commit (:18); md5 l6_inputs / l7_inputs / stub / pin; dia >= 15 300 MB, RAM >= 10 000 MB; NDCA OW1 = 0 (EB5); MKT_DAYS ==
  09-15..09-22 (:56); V-TIER khong FAIL_MOMENTS; lap dat L12 grep; 2 lane; ket luan = verdict_rsim lane sim; khong in PnL (result_noPnL bo
  stats.equity; score/verdict chi lech tuong doi).
- Han che (=> dieu kien thu tuc P1-P2): (i) khoa: flock -n + file .done CHI o cuoi => dung giua chung co the chay lai; (ii) sha code ghi ra
  official_code_sha256.txt nhung KHONG so voi danh sach duyet; (iii) run_pricedue.sh doc env /dev/shm/add24/b/out_dev2/DEV2W/env_used.sh (tmpfs,
  khong md5) - da dua vao SHA256_A1_APPROVED_RSIM.txt.

## 6. Tai lap DEV8 (ban sao fx_dev6 + mkt loc SLX/OPN + simtier l6_inputs, stub chi doc, bwrap, flock)
- verdict_rsim.json cua A1 == file DEV-B (dev_results/L8/DEV8_sim) MOI khoa: RESULT PASS_CAN_OWNER; S-G 97 qd / 14 phut PASS; S-G2 122/122, seen
  -1,1955e-05 PASS; S-SZ n 96 max 9,486e-05 PASS; S-X 96 SCORED + 3 N10 (90 cung phut + 6 N8, 9 time-stop / 87 trail, TB +0,068 %) PASS;
  S-D INSUFFICIENT_CO_PHU; meta: gridDue 17, due 17, sim_t3_block 17; INSTALL rig_t = START; V1-V3/V5/V6/V9 PASS; N10 3,1 %.

## 7. Phat hien con lai
MINOR: khoa 1 lan yeu (P2); sha khong tu so (P1); RESULT khong liet ke muc can owner (P3); S-SZ khong loc cua so (dung cho OW1).
NOTE: classes/ (bien dich) khong tai bien dich doc lap - DEV8 chay ra dung so voi chung; byte nen zip thang 09 qua bo nho (EB24 loc theo dong).
Rui ro ghi ket qua: SIM_TIER_STALE (owner da chap nhan), BD_ORDER, N10 (neu > 5 %), S-D INSUFFICIENT_CO_PHU (DCA chi co bang chung C0b + DEV-2).
