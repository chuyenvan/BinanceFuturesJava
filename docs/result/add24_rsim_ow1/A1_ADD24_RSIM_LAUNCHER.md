# A1_ADD24_RSIM_LAUNCHER - A1 audit launcher + bo cham R-SIM (DEV-B) TRUOC luot chinh thuc OW1 - 2026-11-22 ~19:10 +07
Luat: prereg 6ee84f17 + ERRATA1-4 (muc B R-SIM). KHONG chay / mo OW1. Ban sao da audit: ~/claude_master/w3/add24_audit/rsim/snap
(sha256 tung file: rsim/SHA256_A1_AUDITED.txt; bo l6_inputs / l7_inputs / bak_*). DEV-B dang lam tiep - file them SAU 18:05 chua audit.
Ma nguon doi chieu: jar 76134a52 (c3_hotfix), sim a8690d46, harness DEV-A dff0354d.

## PHAN QUYET: KHONG DUYET luot chinh thuc R-SIM OW1 o ban hien tai.
Launcher (L1-L13) CHAP NHAN (2 dieu kien nho). BO CHAM co loi cung loai B1 (INSUFFICIENT che FAIL) + sai dinh nghia mau S-G (ERRATA2) +
thieu kiem mau / ly do S-X => phai sua (uoc 2-3 h) roi A1 duyet delta (~1 h). Phan size BIG_DOWN va mkt toan san (DEV-B dang lam) chua xem.

## 1. Bang L1-L13 (diem can thiep vao jar / harness)
| # | Ket luan | Ghi chu |
|---|---|---|
| L1 FollowSet (tap LEGACY dong) | CHAP NHAN | contains = !(lenh sim (s,b) hoac rig dang giu s); duong production LEGACY (gate + nap r, khong vao) = EB3. NOTE: iterator rong / size 0 - neu code nao duyet / isEmpty tap legacy thi thay "rong" (A1 khong thay cho nao trong duong quyet dinh, chua kiem het). |
| L2 bulkAdd warm-up | CHAP NHAN | ham jar loadPersistedAndSeed; V9 so voi log sim theo quy (V9 chi co cho quy du warm-up) |
| L3 defer = TsMktExt::deferTimeStop | CHAP NHAN | = mac dinh production; V6 kiem 'swapped' nhung KHONG kiem thoi diem lap (rig_t) - them (m1) |
| L4 TsMktExt co ngay | CHAP NHAN | du lieu co; OW1 khong co ngay TS_EXT |
| L5 followPx gia vao sim | CHAP NHAN | EB11 buoc 1 |
| L6 a1=false | CHAP NHAN | K11 |
| L7 fixture (SETTLING, BTCUSDT, sel top-24) | CHAP NHAN | du lieu |
| L8 doi chuoi Bar.s[1]/s[2] | CHAP NHAN | A1 doc: applyPrices giam O,s1,s2,C / tang O,s2,s1,C => lane sim moi nen O->L->H->C; float h/l giu cho KillSwitch |
| L9 khop stop min(SL,open) o SCORER | CHAP NHAN co ghi chu | score_rsim.py:155-162 them quy tac "SL dat TRONG nen khop => SL" (ngoai chu ERRATA2 2a - hop ly voi O->L->H->C, can ghi errata). Rig van giu gia khop tho => equity rig lech quy uoc => chi anh huong C_eff khi E_rig < C3_CAPITAL (NOTE) |
| L10 pin bo loc san | CHAP NHAN | du lieu |
| L11 S-G2 ca quy | CHAP NHAN | |
| L12 tier luoi qua Proxy gridDue + boc reconAllows | CHAP NHAN co dieu kien | C3LiveEntry.decide (76134a52): reconAllows :227 -> legacy -> nhanh DCA: DCA_OFF / NOT_HOLDING / PENDING -> gridDue.due :238 -> legIdx -> tier3 :243. Tra false o gridDue = cung "khong vao leg DCA", khac duy nhat ten outcome (DCA_NOT_DUE thay TIER3_DCA); gridDue chi dung o decide (C3LiveRuntime:420 tao). Trang thai tier: A1 kiem simtier_code.csv: FIGHT/SPACE khong co hang o moc 01-19 07:00 (UNKNOWN->T3), T1 o moc 02-06 04:00; SLX/OPN khong co hang ca 2 moc. DIEU KIEN (m1): lap dat Proxy bang THREAD rieng (doi r.entry) => phai co cong assert "simtier installed rig_t <= START" (meta co ghi nhung chua co cong). |
| L13 N10 = xoa nen | CHAP NHAN | MarketReplay doc d.mkt (khong phai klines) => xoa nen khong doi dieu kien thi truong; KillSwitch van doc d.bars (anh huong nho, NOTE) |
| (moi, khong co trong danh sach) nguon bookFull gate | NOTE | env 242 GATE_QUOTA_SKIP_WHEN_FULL=true; rig tinh bookFull tren so c3 rig (C3_CAPITAL 10000) - sim tinh tren so sim (von lai kep). Ham size cung ti le => U tuong duong; S-G2 THO la phep kiem truc tiep (Q2 122/122). Ghi vao danh sach diem khac. |

## 2. Bo cham - PHAT HIEN
BLOCKER
- R1 S-G sai mau + che FAIL: score_rsim.py:55 status = INSUFFICIENT neu len(sim_min) < 50 (PHUT) TRUOC khi xet fail. ERRATA2 s1 sua mau =
  >= 50 quyet dinh (phut, symbol) VA >= 10 phut. Hau qua: OW1 (67 leg / 16 phut) => S-G LUON INSUFFICIENT (ADD24 khong the PASS) VA mot lenh
  sim bi jar REJECT van ra INSUFFICIENT. A1 tiem (pass->0 cho 1 lenh PREDICT): S-G fail=1, status INSUFFICIENT - KHONG BAT (S-G2 bat gian tiep).
MAJOR
- R2 S-SZ: :122 INSUFFICIENT khi n < 50 truoc khi xet lech (cung loai B1). verdict_e3.py:70 B4 'PASS_N11' co the de len INSUFFICIENT cua S-SZ.
- R3 S-X thieu kiem mau: prereg s9 (>= 30 cum thoat, >= 1 time-stop, >= 1 trail) KHONG co o verdict_e3 / summarize => mau nho van PASS.
- R4 S-X(a) "ly do 100 %" khong co status (summarize chi in reason_eq_share; verdict B1 khong xet ly do) => lech ly do khong lam FAIL.
- R5 Cum sim KHONG duoc cham bi loai im lang: verdict_e3:17 / score_rsim:172 chi lay rig SUBMITTED + co thoat; cum rig NO_LEG / outcome khac
  (tru N10, V-TIER, DCA) hoac NO_EXIT khi sim da thoat trong cua so KHONG thanh FAIL (DEV7: 0 truong hop, nhung khong co luat).
- R6 S-D: :219 in 'PASS_ZERO (sim 0 = rig 0)' - prereg: 0 su kien => INSUFFICIENT (co phu C0b S-DCA); "KHONG XAY RA" khong bao gio PASS.
  (rig_extra = FAIL: dung.)
- R7 Khong co script gop ket luan R-SIM (summarize_official.py chi gom so, khong verdict; N10 > 5 % chua thanh trang thai; V-TIER / co
  SIM_TIER_STALE chua noi vao ket luan) => MASTER gop tay - rui ro lap lai loi B1.
MINOR
- m1 Cong V: them assert lap dat L12 (simtier installed, rig_t <= START) va L3 (rig_t <= START), khong chi 'swapped'.
- m2 B4: leg co stepSize <= 0 bi bo qua im lang (verdict_e3:59).
- m3 Ghi errata cho quy tac khop stop mo rong (L9).
NOTE
- REF S-X (classify_sx.py) doc lap Java (chi printDone + klines fixture); REF-sim tai lap phut / gia sim (kiem tren cum trail); K8 chi khi
  REF-nhip == phut rig VA REF-sim == phut sim; lech > 1' => FAIL (verdict gt1). Tran N8 10 %: co.
- EB24: assert ts <= 2026-09-30 23:59 o conv_rsim (:65,:78,:96), build_fx (:14,:65,:72), vtier (:23,:38,:54); gates V3 kiem klines + dau vao
  conv. Khong in PnL: dat (score/verdict chi lech tuong doi).
- So DEV-B bao "S-X (b) 92 cung phut + 6 N8 / 98" la cua DEV6; DEV7 (file cua DEV-B va ban tai lap A1) = 90 + 6 / 96 (+3 N10 loai), TB gia
  thoat +0,068 % (khong phai +0,078 %). Ti le van 100 %.

## 3. Tai lap (ban sao fixture fx_dev6 + simtier l6 vao /dev/shm/add24_a1; stub chi doc; bwrap --unshare-net; flock)
- DEV7 lane chinh: score.json TRUNG file DEV-B (dev_results/DEV7_sim): S-G 97/97 pass (status INSUFFICIENT - R1); S-G2 THO 122/122, seen
  -1,1955e-05 PASS; S-SZ n 96 max 9,486e-05 PASS; S-X 96 cum: 90 cung phut, 6 +-1' (6 K8 REF), ly do 96/96; B1 PASS; B2 TB +0,068 % PASS;
  B4 PASS. meta: simtier installed rig_t = START, gridDue goi 0 (Q2 khong co mkt toan san), x14 swapped.
- Tiem lech vao ban sao output: (1) 1 khop SELL +3' => B1 FAIL (LABUSDT, OTHER) - BAT; (2) f_jar 1 leg x1,01 => S-SZ FAIL, B4 FAIL - BAT;
  (3) gate: 1 lenh PREDICT sim pass->0 => S-G fail=1 nhung status INSUFFICIENT - KHONG BAT (R1).

## 4. TIER_IMPACT (tai tinh doc lap mot muc)
- FIGHT bi chan 02-01 -> 02-06: (a) code sim Sim:1431-1436 + CoinRankManager:91-97, 129-139; (b) printDone: khong lenh :00 nao giua
  01-19 07:00 va 02-06 04:00; (c) simtier_code.csv (code a8690d46): FIGHTUSDT moc 01-19 ranked=0 => T3, moc 02-06 TIER_1 => DCA 02-06 04:01
  dung 1' sau moc. => khop TIER_IMPACT (c) Q1. A1 KHONG tai lap dieu kien DCA 02-01 00:10 (thi truong / gia / gate) va KHONG chay
  repro_tier_impact.sh (script ghi vao /dev/shm/add24/b/l5 - vung cam ghi cua A1).
- SLX / OPN: simtier_code.csv ranked=0 o ca 2 moc => T3 suot Q2 (khop "sim khong bao gio DCA"); tier theo gio T1/T2 cua production chua
  tai lap.

## 5. Dieu kien truoc luot chinh thuc OW1
1. Sua R1 (mau S-G theo ERRATA2: >= 50 quyet dinh VA >= 10 phut; FAIL neu co lenh sim bi jar REJECT bat ke mau).
2. Sua R2-R6: moi chi so: >= 1 lech khong giai thich => FAIL; INSUFFICIENT chi khi 0 lech va duoi mau; S-X kiem mau (30 / 1 / 1) + ly do
   100 %; moi cum sim trong cua so phai co trang thai (cham / N10 / V-TIER / DCA-loai) - con lai FAIL; S-D 0 su kien = INSUFFICIENT.
3. R7: script gop ket luan R-SIM (BB, BB co phu, N10 > 5 %, V-TIER, co SIM_TIER_STALE) - kem test tong hop nhu R-LIVE (lech mau nho, cum bi
   bo, tiem gate / size / thoat).
4. m1 cong lap dat L3 / L12.
5. A1 duyet delta + phan size BIG_DOWN + mkt toan san (F1) truoc khi mo OW1. Owner: co SIM_TIER_STALE (ERRATA4 1c).
