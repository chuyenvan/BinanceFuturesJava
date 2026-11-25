# A1_PILOT_M_TOOL_V2 - audit lai pilot_m_daily.py sha256 8bc4da418d25... (prereg 2a21fe35 + ERRATA1 c0f35f3c + ERRATA2 efc4f9c1) - 2026-11-25
Chi doc; sandbox /dev/shm/a1tool2.* (da xoa). Khong doc du lieu >= 2026-11-24 07:00; khong --official; khong ghi v12/pilot_m/.

VERDICT: PASS-WITH-MINOR - dung cho lan cham chinh thuc D=2026-11-24 duoc; dieu kien muc "Dieu kien".

## Ket qua
- Test DEV 351/351 PASS (11,9 s). Mutant DEV 20/20 GIET.
- Ca pha: 15/18 bat (5 ca cu B1 B2 B10 B11 B12 deu bat). Lot: N2 cum DANG arm (khong RST) bi TIME-STOP => M-T KCSK, I8/I10 DAT (lo prereg: E7 chi neu "cum co pha arm hieu luc khong time-stop" nhung khong co luat cham); N6 1 luot ssh hong toan bo (latch rong) => K2 VI_PHAM (VANG) - cach doc ERRATA1 E2(b) "(khi truong khong rong)" (README lua chon 10 ap ca latch rong); N12 2 cum cung symbol dong cach nhau < 600 s => I10 VI_PHAM DO gia (chk_I10 :1178/:1185 ghep BOOK<->CLOS theo symbol, khong theo cum).
- Mutant A1 moi: 12/14 GIET. SONG: X01 bo han 600 s cua E6 (ca N1 cua A1 bat, bo test DEV khong); X04 dung sai 0,1 % cho moi ho (khong co test ho cham dong > 1000 dong voi 1 dong khong parse).
- Chay thu 21/22/23 (--max-ts): VANG/VANG/XANH; M-S 21 DAT 24/24; K2 21-22 KCD (dong truoc 22/11 17:24 thieu deadman=), 23 DAT; khop bao cao DEV.
- Ro du lieu: quet md+json 21-23: 0 truong tien / so du / SIG / TOKEN, 0 so thap phan >= 3 chu so. san() moi loc dung dong thu LECH EQUITY + BFUSD_WALLET + so_du + availableBalance + "eq = C3_CAPITAL + (..)".
- ERRATA1 E1-E13 + ERRATA2 F1-F3: cai dung chu (doc chk_MS S1/S1b/S2/S3/TIER/AVAIL/EQ_DUOI, chk_K2 dong hop le / (b) / (c) / (d) dau-cuoi ngay / .log.1 / end_t = min(hi, max-ts, cham_luc), official_time_ok 07:10, I4(d) TRIGGERING|TRIGGERED +-61 s, E4 --delist-noted ca I8/I10, E6, E7 unarmed_at, E8, E9 PFX + 0 dung sai tru 4 ho mo ta, E10-E12, E13 chi M-T).
- OTHER_TPL (127 mau): chi duoc thu khi KHONG ho cham nao khop tien to => khong nuot duoc dong ho cham bi hong; 12 mau ngan (vd '[KILLSW] {} code={} mode=') khong trung tien to ho cham ([KILLSW] HOURLY / C2_WARN / LATCH duoc xet truoc). Khong thay sot.
- Du lieu truoc moc: moi dong TOM TAT sau 22/11 17:24 deu co deadman=; latch rong 0/3524 dong (19/11-24/11 07:00); adapter rong 13 dong.

## Minor (ERRATA3 / sua truoc 2026-11-28)
m1 (prereg + tool) them vao M-T: "dong TIME-STOP (hoac CLOS TIME_STOP_168H) cua cum dang co pha arm hieu luc (ARM cuoi khong co RST sau no) => VI_PHAM M-T". Sua chk_MT :1406-1416. Can truoc due 28/11.
m2 (ERRATA3 cau chu) E2(b): "(khi truong khong rong)" ap cho ca latch, khan, jar; tool chk_K2 :1946 doi thanh `if kv.get('latch') and kv.get('latch') != 'NONE'`.
m3 chk_I10 :1176-1197: ghep BOOK/CLOS/SFIL trong CUNG cum (cl.clos, cl.books) + su kien mo coi (cl None), khong theo symbol.
m4 test: them ca giet X01, X04.
m5 README lua chon 10 doi theo m2.

## Dieu kien commit cong cu + cham chinh thuc
1. Commit dung sha 8bc4da418d25 (hoac ban sua m1-m4, chay lai 351+ test + 20 mutant DEV + X01-X14). 2. D=2026-11-24: `pilot_m_daily.sh 2026-11-24 --official` khong can tham so them, tru --external-noted / --delist-noted neu MASTER co ghi chep. 26/11 BAT BUOC --pilot-on-start; drain co ghi chep => --drain-window. 3. MASTER doc json truoc khi bao owner (kiem_cheo 3 so, muc 9); neu I10 DO co 2 cum cung symbol trong 10 phut => xem m3 truoc khi bao. 4. m1 phai xong truoc lan cham D=2026-11-28.

## Khong kiem duoc
Hanh vi tren log that cua duong DCA, TIME-STOP, defer [C3LIVE-OPS], PX_CORRECTED, lop B, LATCH (0 dong truoc moc); gia tri env.
