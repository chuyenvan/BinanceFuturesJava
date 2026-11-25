# A1_PILOT_M_TOOL - audit cong cu cham chi-log PILOT-M (pilot_m_daily.py sha256 024b5330b1dd..., chua commit) - 2026-11-25
Prereg 2a21fe35 (+ ADD7 c1a752c1). Chi doc; sandbox /dev/shm/a1tool.* (da xoa). Khong doc pull242/2026-11-24+, cron >= 24/11 07:00; khong --official; khong PnL.

## VERDICT: FAIL - can T1-T12 + ERRATA1 truoc khi dung ket qua chinh thuc.

## Tai lap
- Test DEV: 128/128 PASS (tai lap). Chay thu 21/22/23/11 (--max-ts 2026-11-24 07:00): trang thai khop bao cao DEV tung muc (21: DO do M-S 8 leg; 22,23: VANG do K2).
- Kiem tay tu log goc 21/11: I3 mau 63 = so MOVE trong cua so (75 STOP - 12 ARM); I9 mau 75 = 63 + 12 ARM; F(peak) float32 BLESS/JCT khop SL log; C_ngam BLESS = 1000,000 (budget 22,5, U=0) -> r_cap = 1, r = 1,00033 (eq_lo < C_eff) = hien tuong E1 that; I10 mau 12 = 12 CLOS 21/11; K3 25 = 1 dem + 24 streak lien tuc; JCT 12:35:54: TRIGGERING .094 -> SFIL .100 -> BOOK .191 -> CLOS .298 -> TRIGGERED/FINISHED .299 (E3 that); BLESS TRIGGERING 12:47:31.096, CLOS 12:47:41.176 (10 s).

## Ca pha (log tong hop, dua tren kich ban clean() cua DEV): 10/15 bat
LOT (DAT gia): B1 cum dong khong co dong CLOS (chi SFIL+BOOK) -> I10/I12/I4 DAT; B2 dong CLOS bi cat giua dong -> I10 DAT (dong mat chuoi ' DA DONG tren san' nen khong vao ho nao, khong tinh 'khong parse'); B10 monitor chet tu 15:00 -> K2 DAT; B11 cron xoay (nua dau ngay o .log.1) -> K2 DAT; B12 SFIL du qty + khong CLOS -> I12 DAT.
BAT: B3 hai cum cung symbol noi tiep (DAT dung); B4 cid lap; B5 MOVE ha stop; B6 gz hong giua file (KCD); B7 flag ON chi defer so giay; B8 symbol non-ASCII; B9 26/11 thieu --pilot-on-start (K1/K2 KCD); B13 MOVE dinh dang la (KCD); B14 RST; B15 KHAN o dong noi tiep.

## Mutant (25 mutant, bo test DEV): GIET 8 / SONG 17
SONG: I4(a) bo; I4(b) bo han 61 s; I4(c) luon DAT; I4(d) bo; I8 bo SFIL truoc ARM; I10 bo so ly do BOOK=CLOS; I11(b) bo leo thang; I12(d) bo tong SFIL; M-T bo yeu cau CLOS; M-T bo "som hon due"; D1(a) bo level; M-S bo (6); M-E0 bo (c); K2 bo khoang trong 10'; K3 bo streak; K4 bo "chua co co ngay"; K5 bo log_minutes.
GIET: I3 1,001; fam_bad; san(); I9(c); K3 bac DO; I11(a) n; D1(e); K6 LATCH A40 bac DO.

## Ro du lieu
san() (pilot_m_daily.py:56-78) KHONG loc: BFUSD_WALLET= (\b truoc 'wallet' khong khop vi '_W'), so_du=, equity_so=, upl_so=, chot=, moc=, chuyen=, dinh=. Duong ra hien tai: dong log su kien + 3 dong vi du ERROR/KHAN/LATCH (K6) + TOM TAT. Dong ERROR "[C3-LIVE-RECON] LECH EQUITY ... equity_so= chot= upl_so=" (Reconciler :766-770) se lot gia tri tien vao json/md. TOM TAT hien khong chua BFUSD (chi cac dong '== BFUSD' khac, cong cu khong doc) => chua ro thuc te, nhung phai sua. Ket qua chay thu 21-23/11: khong co so tien nao (chi C3_CAPITAL 1000.0).

## Sua BAT BUOC cong cu
T1 pilot_m_daily.py:247-267 (classify) + :383-387: dong bat dau bang tien to cua bat ky ho nao ('[C3-LIVE] cum ', '[C3-LIVE] SUBMIT ', '[C3-LIVE-TRAIL] ', '[C3-LIVE-FILL] ', '[C3-LIVE-BOOK] ', '[C3-LIVE-EXEC] ', '[C3-LIVE-RECON] ', '[TS-EXT] ', '[KILLSW] ') ma khong khop regex nao => 'khong parse' cua ho co tien to dai nhat (khong doi chuoi cont). (B2)
T2 chk_I10/chk_I12/chk_I4 (:976-1095, :888-914): them su kien 'dong cum' tu BOOK va tu tong SFIL >= qty cum; BOOK khong co CLOS trong +-600 s / SFIL du qty khong CLOS trong 600 s => VI_PHAM I10 (theo ERRATA1 E6). (B1, B12)
T3 chk_K2 (:1626-1712): doc ca golive_monitor_cron.log.1; xet khoang trong dau ngay (tu D 07:00 neu khong co dong truoc) va cuoi ngay (dong hop le cuoi -> min(D+1 07:00, horizon cron)); theo ERRATA1 E2 (dong hop le). (B10, B11)
T4 chk_I4(d) (:883-895): cua so [t_CLOS-61 s; t_CLOS+61 s], X in {TRIGGERING, TRIGGERED} (E3).
T5 chk_MS (:1288-1352): S1-S9 theo E1/E5; bac_of M-S: DO chi khi co S1/S2/S4-S9; S3 = VANG EQ_DUOI.
T6 chk_I8/chk_I10: DELIST_SETTLE DAT chi khi --delist-noted (E4).
T7 chk_MT: 'chua arm tai due' theo E7 (ARM cuoi truoc due bi RST sau no => cham nhu chua arm).
T8 chk_D1: leg DCA ket thuc khong khop => bo (a) cho leg do, khong KCD (E8).
T9 M-T flag=NA => OFF (TsMktExt.flagFor :221-232 tra OFF cho NA), khong KCD.
T10 fam_bad (:417-426): 0 dung sai cho moi ho dung cham M-I/M-T/D1/M-S/K (E9); 0,1 % chi cho MKT/AIPASS/SKIPORD/DCAGRID (mo ta / D1(e) fail-closed tu nhien).
T11 san(): them (?i)\b[A-Z0-9_]*(WALLET|BALANCE)[A-Z0-9_]*=\S*, \b(so_du|equity_so|upl_so|chot|moc|chuyen|dinh|tmb\w*|eq\w*)=[^\s,;)\]]*, va bo noi dung trong ngoac sau 'eq = C3_CAPITAL + (' ; test voi 3 dong tren.
T12 test: them >= 1 ca tiem cho MOI dieu kien con (17 mutant song phai bi giet) + 5 ca B1/B2/B10/B11/B12; chay lai mutant.

## 15 'lua chon cai dat' = DOI LUAT (phai vao ERRATA1): 1 (I4(d) -> E3), 3 (level leg 0 khac -> VI_PHAM: E10), 5 (U >= 0,6 -> VI_PHAM: E5 S9), 6 (I12(b) dung 'leg nho nhat' thay stepSize: E11), 7 (E4), 10 (flag NA -> KCD: sai code, sua T9), 12 (K1 khung 60': E12), 15 (0,1 %: E9). Con lai (2, 4, 8, 9, 11, 13, 14) la chi tiet cai dat hop le.

## VAN BAN ERRATA1 DE XUAT (ASCII, de MASTER commit TRUOC lan cham chinh thuc dau tien)
ERRATA1 PREREG_PILOT_M (2a21fe35). Nguon: A1_PILOT_M_TOOL (2026-11-25), hien tuong tai lap tren log TRUOC 2026-11-24 07:00. Moi sua la sua DINH NGHIA theo co che code/ha tang; khong nguong nao suy tu so quan sat. Ap cho moi ngay cham tu 2026-11-24.
E1 (muc 5 MUC CANH BAO CUNG, thay (1)): co che: C_eff = min(C3_CAPITAL, c3Equity MTM, availableBalance + margin c3) tai luc SUBMIT (C3MainEquity :122-170); eq= cua [KILLSW] HOURLY la cung ham nhung lay mau moi gio => equity luc SUBMIT co the nam ngoai khoang 2 dong bao quanh.
 (S1) r_cap = C_ngam / C3_CAPITAL > 1 + 1e-6 => VI_PHAM (code: C_eff <= C3_CAPITAL).
 (S2) r_hi = C_ngam / min(C3_CAPITAL, eq_hi) > 1,02 => VI_PHAM; eq_hi = max eq= cac dong [KILLSW] HOURLY CUNG JVM bao quanh SUBMIT (toi da 1 dong truoc, 1 dong sau).
 (S3) r_lo = C_ngam / min(C3_CAPITAL, eq_lo) < 0,98 => VANG "EQ_DUOI" (khong DO); eq_lo = min eq= cung cap dong do. Ly do: huong size NHO hon (an toan); equity c3 MTM trong gio giam > 2 % la co che binh thuong khi dang giu vi the luc thi truong sap (chinh luc he vao lenh).
 Ngoai le: |r - 1,2| <= 0,02 hoac |r - 0,5| <= 0,02 (r = r_hi o S2, r_lo o S3) => VANG "TIER"; S3 co "[C3-LIVE-EQ] CANH BAO ky quy" trong 24 h truoc => VANG "AVAIL". Khong co dong HOURLY cung JVM => chi xet S1; S2/S3 = KHONG_CHAM_DUOC cho leg do.
E5 (muc 5, danh so lai): (S1)(S2)(S3) nhu E1; (S4) notional > b x (1 + 1e-9); (S5) b - notional > marketStepSize x (n/q) + 1e-9; (S6) q khong la boi so marketStepSize; (S7) b > 0,045 x C3_CAPITAL x 1,2 hoac b < 5 x 0,5; (S8) legIdx sai (leg 0 khi dang giu / DCA k != legCount); (S9) U_before >= 0,6 ma van SUBMIT (TradeUtils.managerBudget :140 chan). (S5)(S6) = KCD_CAU_TRUC (R3). Moi tham chieu "M-S (1)/(2)" trong prereg (dong 30, muc 10) doc la "M-S (S1)-(S9)"; muc 10: M-S VI_PHAM tru VANG "TIER"/"AVAIL"/"EQ_DUOI" => DO.
E2 (muc 8 K2, thay noi dung): co che (golive_monitor.sh pinned d60882c1): cron */2 phut, flock -n, timeout 100 s; adapter / C3_CAPITAL / push lay tu doc trang thai 242 qua ssh (sv ENV_*), doc hong => truong rong va push tinh ra OFF (dong 119) = LUOT DOC HONG, khong phai trang thai bot; deadman canh monitor o MON_DM_MAX_S = 600 s; monitor tu KHAN sau 5 luot loi lien tiep.
 Dong TOM TAT HOP LE = adapter va C3_CAPITAL khong rong. Dong khong hop le: chi dem (mo ta so_luot_doc_hong). VI_PHAM khi: (a) dong hop le co adapter != live, C3_CAPITAL sai von, push != ON, deadman != OK; (b) dong bat ky co latch != NONE, khan=KHAN, hoac jar khac 01cfbb43 (khi truong khong rong); (c) khan_canh_bao != 0 hoac khan != 0 o >= 2 dong hop le lien tiep cung noi dung; (d) khoang cach giua 2 dong HOP LE lien tiep > 10 phut (= MON_DM_MAX_S), tinh ca doan dau ngay (tu dong hop le cuoi truoc D 07:00, khong co thi tu D 07:00) va doan cuoi ngay (toi min(D+1 07:00, thoi diem cuoi cua cron log da doc)). Nguon: golive_monitor_cron.log va golive_monitor_cron.log.1 (monitor xoay khi > 20 MB). Ngoai le R4 (26/11) va drain co ghi chep giu nguyen.
E3 (muc 2.1 I4(d), thay): moi CLOS ly do TRAILING_STOP co ALGO_UPDATE cua cid stop dang hieu luc (cid cua dong STOP cuoi truoc CLOS) voi X in {TRIGGERING, TRIGGERED} trong [t_CLOS - 61 s ; t_CLOS + 61 s]. Co che: ALGO_UPDATE (FillAccounting :294) va CLOS (:421) in tren cung thread user stream theo thu tu su kien san: TRIGGERING truoc khop, TRIGGERED / FINISHED sau khi vi the dong; 61 s = C3StopProtector.DEADLINE_MS. Het du lieu truoc t_CLOS + 61 s => KHONG_CHAM_DUOC.
E4 (I8 + I10): DELIST_SETTLE (cid settlement_autoclose, FillAccounting :458, san tu dong vi the khi huy niem yet) DAT o I8 va I10 CHI KHI MASTER co ghi chep thong bao huy niem yet cua san cho symbol (truoc hoac cung ngay CLOS), nhu EXTERNAL-co-ghi-chep; khong ghi chep => VI_PHAM.
E6 (I10, them): "cum dong" con duoc xac dinh boi dong BOOK "[C3-LIVE-BOOK] dong cum" (LiveBookC3 :737, in cung luong closedOnExchange voi CLOS) hoac tong qty SFIL >= qty cum. Moi BOOK phai co dung 1 CLOS cung symbol trong [t_BOOK - 600 s ; t_BOOK + 600 s] va nguoc lai; SFIL du qty ma khong co CLOS trong 600 s => VI_PHAM I10. Het du lieu => KHONG_CHAM_DUOC.
E7 (muc 3 M-T, thay "Cum da arm KHONG bao gio time-stop"): cum co pha arm hieu luc khong time-stop; DCA khop reset arm (dong RST, priceSL ve NaN - TrailingStopManager :207-244) => cum lai thuoc time-stop. "Chua arm tai due" = khong co dong ARM nao, hoac dong ARM cuoi truoc due co dong RST sau no truoc due.
E8 (D1(a)): leg DCA ket thuc khong khop (dong "ket thuc ... khong khop => huy giu cho" / "... => huy giu cho") => (a) khong ap dung cho leg do (khong co ref); (b)-(e) van cham; khong sinh KHONG_CHAM_DUOC vi ly do nay.
E9 (muc 12, fail-closed): dong co tien to cua mot ho mau ma khong khop mau day du = dong khong parse. Ho dung cho M-E0 / M-I / M-T / D1 / M-S / K (SUBMIT, FILL, ket thuc leg, ARM, STOP, ALGO, SFIL, CLOS, BOOK, TIME-STOP, RST, RECON, lop B, TS-EXT, KILLSW, banner): >= 1 dong khong parse trong cua so => muc dung ho do = KHONG_CHAM_DUOC. Ho chi mo ta (Market level, AI PASS, SKIP ORDER, LIVE-DCA-GRID): dung sai 0,1 %.
E10 (M-E0(b)): leg 0 level khac PREDICT_SYMBOL_TRADE / BIG_DOWN => VI_PHAM (code c3: leg mo cum chi qua selector hoac BIG_DOWN).
E11 (I12(b)): khi chua co stepSize (R3): exitQty > qty + qty leg nho nhat cua cum => VI_PHAM; qty < exitQty <= qty + leg nho nhat => KHONG_CHAM_DUOC.
E12 (K1, 26/11): "khung owner" = [gio bat dau pilot_on ; + 60 phut] (cung 60' cua R4).
E13 (M-T): dong "[TS-EXT] flag day=.. flag=NA(->OFF)" = OFF (TsMktExt.flagFor :221-232).

## Khong kiem duoc
Duong DCA / TIME-STOP / defer [C3LIVE-OPS] / PX_CORRECTED / lop B / LATCH / restart trong ngay tren log THAT (0 dong truoc moc; chi test tong hop + chuoi code). Gia tri env. Hanh vi cong cu khi pull co nhieu file log xen ke (dedup theo dong nguyen van). Hieu nang > 14 ngay (DEV uoc ~25 s).
