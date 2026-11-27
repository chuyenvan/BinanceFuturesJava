# A1_CMB2 - kiem toan doc lap CMB2 (2026-11-27). Code rieng (tmp, da xoa). Khong sua file nao khac.
PHAN QUYET: PASS-CO-LUU-Y (so hoc + chon cfg DUNG, tai lap khop; NHUNG dien giai "Calmar tang" bi thoi phong - xem L1-L4).

1 Chon khong nhin truoc: PASS. Viet lai rule B1 (valid n>=30, ret>0, ddw<=30%, score=min ret/ddw, plateau>=60% lang gieng 1 buoc trong HO)
  + goi select_t1.wfo: STATE 2708/2672, PART 2556/2522 - trung. chosen = TRONG HO (subset fam & gate NONE). Gate NONE dung B2.
  Hoa diem: 2708=2726, 2672=2690 (chi khac H 168/720, cung ret fold kiem) -> khong anh huong.
  LUU Y L1: neu ap rule tren TOAN luoi NONE (khong plateau), top 2025 la BRK/HEDGE voi F3 -6,8..-7,7 %. Hai ho STATE/PART duoc chon
  SAU khi thay T1 (co F3) => "khong nhin truoc" chi dung TRONG ho; chon ho co nhin truoc.
2 STATE 2025 +45,68 %: dung = F3 top-1 (top-20 trung vi +35,3 %). 87 lenh, tong +4568: top-3 lenh +2385 (52 %); bo top-3 con +21,8 %;
  top-5 lenh (5 %) +3329 (73 %); thang 9 +1961 + thang 11 +3035 > 100 %. STATE 2024 -0,33 %: top-3 = +538, bo top-3 -5,7 %.
  PART 2024 +17,97 %: top-3 76 %, bo top-3 +4,4 %. PART 2025 +2,59 %: bo top-3 -3,5 %.
3 Cach ghep: (a) DUNG cach c1_combo levz_an. (b) gross max c0s42 0,925 / 0,921, 0 gio > 1; short expo MTM max 0,67-0,68. Day la THEM
  phoi nhiem tren cung equity (gross 0,46 -> 0,92), KHONG chia lai von; B3 cho phep ("m=1 tren cung equity"). (c) Khong dem hai lan:
  daily-add == hourly-add (+-0,2 pp) ; so ve von short co dinh tu 2024 (khong lai kep): STATE CAGR 42,8 (vs 48,3), PART 38,8 (vs 41,7).
  Chia 50/50 von (khong them phoi nhiem): STATE 31,6 / PART 29,1 < LONG 35,0 (c0s42). (d) Lech gio: 5 leg (PROMPT, ZRX, BOB, ZEC, RARE)
  eq_real nhay dung gio end-7h, khong nhay o end; tong pnl ledger theo nam UTC == delta eq_real 4/4 nam.
4 Tai lap: PASS, 4 seed khop cmb2_rows <1e-4 (c0s42 LONG 35,0/21,35/1,64; STATE 48,3/21,35/2,26; PART 41,7/21,35/1,95).
  CAGR tu loi suat nam TB nhat quan (37,5 / 51,0 / 44,3).
5 maxDD: dung, dinh 2022-05-12 (c0s123 PART: 2024-11-12, 19,0 %). Cua so 2024-25 DD: LONG 10,7 / STATE 10,5 / PART 19,0 (TB).
  L2: CALMAR CUA SO 2024-25 (noi duy nhat co short), TB 4 seed: LONG 3,52; STATE 6,30; PART 2,71 => PART LAM GIAM Calmar o ca 4 seed.
  Calmar toan ky tang chu yeu vi mau so DD nam o 2022 (khong co short) - co hoc.
  Dung eq_worst short: lech <=0,1 pp. Funding leg long mo: can tren 1,6 % equity (p99 1,2 %).
6 >= 2026: PASS. CUT=2026-01-01, F3 ket 2025-12-31 23:00; long_hourly co 1 dong 2026-01-01 00:00 nhung bi loc; ledger ket 2025-11-28.
7 REPORT: khong de nghi trien khai; co ghi 2 nam, cfg doi, 4 seed chung short, chon ho sau T1. THIEU: Calmar cua so 2024-25 (PART giam),
  "them phoi nhiem gap doi" chua noi ro, tap trung top-3 lenh.
L3: Toan bo loi the STATE = 1 cfg / 2 thang 2025. L4: n = 2 diem/ho.
DUOC NOI: so ghep tai lap dung; theo cach ghep m=1 (gross x2) STATE tang CAGR ~13 pp nho 2025.
KHONG DUOC NOI: "short cai thien Calmar he long" (PART giam Calmar o cua so co short; uplift can them phoi nhiem; ho chon sau T1).
