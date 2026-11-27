# REPORT_CMB2 - ghep LONG DEV voi SHORT chon KHONG nhin truoc (PREREG_X3_1127 phan B) - MO TA, khong phai de nghi trien khai
2026-11-27. Code `code/cmb2.py`; out `out/cmb2_rows.json`, `out/cmb2_check.json`, `out/cmb2_worst_months.csv`; log `logs/`.
Du lieu < 2026-01-01 UTC. CHUA AUDIT DOC LAP.

## Cach lam
- Long: chuoi MTM GIO cua A1 (`levz_an/a1/out/long_hourly.parquet`, ledger -7 h, close1m). Tinh lai CAGR / maxDD gio va assert khop
  `long_metrics.json` (sai so < 0,2 pp).
- Short: cau hinh = `report_t1.json` fam.{STATE,PART}|NONE .wfo.<Y>.chosen (WFO top-1, chon tren fold < Y; khong gate). Chay lai B1
  `port.run` tren fold kiem (2024 = F2, 2025 = F3, moi fold tu 10 000), noi chuoi (2025 nhan he so equity cuoi 2024). 2022-23 khong short.
- Ghep: DUNG cach xap xi cua levz_an A1 (`c1_combo.py`): r_ghep = r_long + m x r_short theo duong tuong doi trong ngay, can bang lai
  hang ngay (= short size theo equity chung dau ngay), m = 1, phoi nhiem short 0,60/K tren equity rieng cua sleeve. KHONG chay port voi
  equity ghep that (khong co tuong tac size / slot). maxDD = MTM GIO. CAGR theo ngay 2022-01-01 -> 2025-12-31 23:00.
- Doi chieu IN-SAMPLE (INS): cfg DEV_ret cao nhat cua ho (gate NONE), DEV lien mach 2022-2025 - CHI de doi chieu.

## Cau hinh short + kiem tra
| | cfg | z | K | bo thoat | ret fold kiem (chay lai / report_t1) |
|---|---|---|---|---|---|
| STATE 2024 (chon tren F1) | 2708 | 3,0 | 5 | zo 1,0 SL 15 % H168 | -0,33 % / -0,33 % (180 lenh) |
| STATE 2025 (chon tren F1+F2) | 2672 | 3,0 | 5 | zo 0,0 SL 30 % H168 | +45,68 % / +45,68 % (87) |
| PART 2024 | 2556 | 2,5 | 3 | s 12 % H72 | +17,97 % / +17,97 % (131) |
| PART 2025 | 2522 | 2,5 | 5 | s 8 % H72 | +2,59 % / +2,59 % (157) |
| INS STATE | 2670 | | | (DEV +107,7 %) | |
| INS PART | 2556 | | | (DEV +105,3 %) | |
Khop chinh xac (|d| < 1e-9) voi report_t1 top-1 va grid_t1. Long: CAGR 35,0-39,8 %, maxDD gio 18,2-21,4 % - KHOP A1.
Chua kiem: tinh lai luat select_b1.rule (lay `chosen` tu json, chi doi chieu ret).

## Bang chinh (2022-2025, m = 1)
| seed | LONG CAGR / DDgio / Calmar | +CMB-STATE | +CMB-PART | INS-STATE | INS-PART |
|---|---|---|---|---|---|
| c0s42 | 35,0 / 21,4 / 1,64 | 48,3 / 21,4 / 2,26 | 41,7 / 21,4 / 1,95 | 62,2 / 22,3 / 2,79 | 61,9 / 21,5 / 2,88 |
| c0s7 | 36,4 / 21,0 / 1,73 | 49,7 / 21,0 / 2,37 | 43,1 / 21,0 / 2,06 | 63,8 / 21,9 / 2,91 | 63,4 / 21,1 / 3,01 |
| c0s123 | 39,8 / 18,2 / 2,19 | 53,6 / 18,2 / 2,95 | 46,7 / 19,0 / 2,46 | 68,0 / 18,2 / 3,74 | 67,6 / 19,0 / 3,56 |
| c0s13 | 38,7 / 20,6 / 1,88 | 52,4 / 20,6 / 2,54 | 45,5 / 20,6 / 2,21 | 66,6 / 21,5 / 3,09 | 66,2 / 20,7 / 3,20 |
| TB 4 | 37,5 / 20,3 / 1,86 | 51,0 / 20,3 / 2,53 | 44,3 / 20,5 / 2,17 | 65,1 / 21,0 / 3,13 | 64,8 / 20,6 / 3,16 |
maxDD gio rieng cua cua so 2024-2025 (TB 4 seed): LONG 10,7 %; CMB-STATE 10,5 %; CMB-PART 19,0 % (ca 4 seed 18,99 % - do short); INS-STATE 15,0; INS-PART 19,0.
maxDD toan ky cua LONG va CMB nam o May 2022 (khi chua co short) => Calmar toan ky thay doi gan nhu chi do CAGR.

## Loi suat tung nam (TB 4 seed; %), dong gop short = ghep - long (pp)
| | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|
| LONG | 8,9 | 73,3 | 41,9 | 33,5 |
| CMB-STATE | 8,9 | 73,3 | 41,6 (-0,3) | 94,6 (+61,1) |
| CMB-PART | 8,9 | 73,3 | 67,5 (+25,6) | 37,1 (+3,7) |
| INS-STATE | 13,8 | 75,0 | 56,2 | 139,2 |
| INS-PART | 16,0 | 120,9 | 67,1 | 72,3 |

## Trung lap / van hanh (moi seed; short chung cho 4 seed)
| | gio short co vi the | gio CA HAI co vi the | gross dinh (long+short) | gio gross > 1 | lenh short | trung coin dang long luc vao / chong thoi gian |
|---|---|---|---|---|---|---|
| CMB-STATE | 2 240 | 838-923 | 0,92-0,93 | 0 | 267 | 3-5 / 12-14 |
| CMB-PART | 7 294 | 2 442-2 531 | 0,92 | 0 | 288 | 0-1 / 11-13 |
| INS-STATE | 3 512 | 1 309-1 471 | 0,96-1,01 | 0-1 | 255 | |
| INS-PART | 11 145 | 4 172-4 396 | 0,93-0,97 | 0 | 352 | |
Long rieng gross dinh 0,45-0,46.

## 3 thang short lo nhat (sleeve, %) va long cung thang (khoang 4 seed)
- CMB-STATE: 2025-10 short -9,7 / long +11,2..+14,1 / ghep +0,5..+3,0; 2024-12 -4,7 / +9,9..+11,1 / +4,9..+6,1; 2025-02 -3,7 / +7,8..+9,4.
- CMB-PART: 2024-11 -8,2 / long +2,7..+4,0 / ghep -5,8..-4,6; 2024-02 -7,9 / +6,4..+7,0 / -1,8..-1,3; 2025-10 -5,6 / +11,2..+14,1.

## Ket luan (khuon B4 - mo ta, khong phai ky vong, khong de nghi trien khai)
1. Ghep khong-nhin-truoc CMB-STATE lam Calmar tang +0,62..+0,76 o tung seed (1,64-2,19 -> 2,26-2,95), CAGR +13,3..+13,8 pp; maxDD gio toan ky KHONG doi (dinh May 2022, truoc khi co short).
2. CMB-PART: Calmar +0,27..+0,33 (-> 1,95-2,46), CAGR +6,7..+6,9 pp; maxDD gio toan ky doi 0 o 3 seed, +0,8 pp o c0s123; trong 2024-2025 maxDD gio tang 10,3-11,0 -> 19,0 % o ca 4 seed.
3. Toan bo phan tang cua CMB-STATE den tu MOT nam / MOT cau hinh: 2025 (cfg 2672, +45,7 % rieng) dong gop +59..+63 pp; 2024 -0,3 pp. CMB-PART: chu yeu 2024 (+25 pp), 2025 +3,7 pp. Hai ho cho thu tu nam nguoc nhau.
4. Khac voi lan WFO cua B1 (levz_an A1: ghep lam Calmar giam 1,6-2,2 -> 0,85-1,08), lan nay ca hai ho T1 khong lam giam Calmar o seed nao - nhung n = 2 nam kiem, 1 cau hinh/nam, 2 ho duoc chon tu T1 vi "co cai thien" (chon ho la sau khi thay T1).
5. In-sample (chi doi chieu): Calmar 2,79-3,74; khoang cach in-sample - WFO = 0,6 (STATE) / 1,0 (PART) Calmar => phan lon ket qua in-sample khong tai hien khi chon khong nhin truoc.
6. Gross dinh ghep 0,92-0,93 (< 1), long rieng 0,46; xung dot cung coin it (0-5 lenh luc vao, 11-14 lenh chong thoi gian / 267-288).
Gioi han: chi 2 nam co short (2022-23 = long rieng); cau hinh short doi theo nam; ghep bang xap xi can bang ngay (khong mo phong slot/margin/one-way chung);
MTM short chi close 1m; MTM long bo phi/funding leg mo; 4 seed dung CHUNG mot chuoi short nen khong doc lap ve phia short.
