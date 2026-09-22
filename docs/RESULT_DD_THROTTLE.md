# RESULT_DD_THROTTLE — TASK B2 Buoc 3: drawdown-throttle (ket qua) (2026-09-21)

Theo `docs/PREREG_DD_THROTTLE.md` (khoa truoc). VERDICT: **NULL** — xac nhan DU BAO cua MASTER.

## 0. Cong an toan (da qua)

- Cong tai lap T170 (OFF, truoc khi doi code): md5 = `efb793e2468ca3a7318da0f0ad23d4fc` — khop
  chinh xac ban tham chieu.
- Cong OFF byte-identical SAU khi them mode `DT` vao `PacingSizing.java`: chay lai T170
  (`X1_GS_T170_2021_PACING_OFFCHECK`, PROFILE khong doi `SIZE_PACING_MODE`, tuc duong OFF) —
  `storage/printDone.csv` 1090 dong, md5 = `efb793e2468ca3a7318da0f0ad23d4fc` — **KHOP TUYET DOI**.
  0 Exception, 0 OutOfMemory trong log. => PASS, duoc phep chay bien the DT.
- shadow-c3: dung luc `Mon Sep 21 09:54:30 +07 2026` (= 02:54:30 UTC), bat lai luc
  `Mon Sep 21 10:40:10 +07 2026` (= 03:40:10 UTC) — downtime ~46 phut (dung cho ca 2 sim T170-verify
  + DT chay tuan tu). Sau khi bat lai: `systemctl is-active` = `active`, log sach (khong loi -2014;
  cac loi -2015 "Invalid API-key, IP..." xuat hien TRUOC luc dung (09:53-09:54) la loi phu
  IP-whitelist ben ngoai chu ky sim nay, dung mau da ghi nhan la binh thuong o cac vong truoc).
- KHONG dung ssh 242, KHONG `git push`, KHONG dong SIM_END_DATE > 20251231.

## 1. Sim da chay

| Tag | n (printDone rows) | Ghi chu |
|---|---:|---|
| `X1_GS_T170_2021_PACING_OFFCHECK` | 1090 | T170 OFF-verify, md5 khop, khong dung lam so lieu (chi de cong OFF) |
| `X1_GS_T170_2021` | 1089 | T170 baseline, dung lai nguyen ven (khong chay lai lan 2) |
| `X1_C3_FULL_2021` | 2559 | gate-1.0/T100 baseline, dung lai nguyen ven — **CUNG LA R0** (xem muc 3) |
| `X1_C3_FULL_2021_DT` | 2568 | **DT (chinh)** — `profiles/x1_c3_full_dt.properties`, `SIZE_PACING_MODE=DT`, D=0.15 floor=0.2146. RAM 8402MB, 777s. 0 Exception/OOM. |

## 2. Bien the R0 — KHONG chay sim rieng (phat hien luc chay, dung nhu PREREG da du lieu truoc)

Ap dung dung cong thuc noi suy log-tuyen tinh da khoa o PREREG muc 3.2 voi `n_total(DT)=2568`:
`g0 = (a - ln(2568)) / (-b) = 0.9971 -> lam tron 2 chu so = 1.00`.

`g0=1.00` trung voi `SIM_GATE_DYN_SCALE` mac dinh cua gate-1.0/T100 (khong dat) => **R0 == T100**,
khong can chay sim rieng. Ly do (khac Buoc 2): DT la co che SIZE-only (khong doi tap lenh duoc
admit), nen `n_total(DT)` ~ `n_total(gate-1.0)` mot cach TU NHIEN (2568 vs 2559, lech 0.35%) — khac
han Buoc 2 noi `R` la co che ADMISSION (doi tap lenh) nen `n_total(R)` lech xa gate-1.0, buoc phai
hieu chinh R0 rieng (gate=1.18). Bien the R0=1.18 cu (n=1908) KHONG duoc tai su dung vi
`n_total(DT)=2568` nam ngoai khoang chap nhan `[1813,2003]` (lech ~35%, khong phai ~5%).

He qua: **u4 hai dieu kien `UW(DT)<UW(R0)` va `UW(DT)<UW(gate-1.0)` trung nhau vong nay** (vi
R0=T100) — day la mot phat hien can bao cao minh bach, khong che giau: DT khong tao ra duoc mot
doi chung "giam-deu" khac biet co y nghia so voi nen gate-1.0 no chay tren, boi ban chat SIZE-only
cua co che.

## 3. So lieu tong hop (toan ky 2021-07-01..2025-12-31)

| | T170 (incumbent) | gate-1.0/T100 (=R0) | **DT** |
|---|---:|---:|---:|
| tag | X1_GS_T170_2021 | X1_C3_FULL_2021 | X1_C3_FULL_2021_DT |
| n_rows | 1089 | 2559 | 2568 |
| n_episodes | 1069 | 2505 | 2514 |
| ICC(roi, ngay) | 0.0516 | 0.1016 | 0.1040 |
| n_eff_total | 606.26 | 1103.86 | **1091.15** |
| maxDD (bar-low, chinh thuc) | -11.844% | -16.129% | **-14.395%** |
| UW dai nhat (ngay) | 92 | 248 | **332** |
| CAGR | 29.27% | 31.94% | 27.38% |
| CI95 (72h-block) | [17.17, 43.86] | [15.12, 53.53] | [12.57, 46.32] |
| CI95 inflated k=2 | [14.80, 46.23] | [11.72, 56.94] | [9.58, 49.31] |

## 4. Per-year (appetite=current: maxDD<=30%, UW<=200/nam, nam khong am, quy>=-15%)

| tag | nam | maxDD% | UW(ngay) | ret_nam% | quy_min% | PASS? |
|---|---|---:|---:|---:|---:|---|
| T170 | 2021 | -2.46 | 37 | 12.21 | 4.44 | PASS |
| T170 | 2022 | -11.84 | 72 | 19.58 | 2.90 | PASS |
| T170 | 2023 | -2.73 | 63 | 34.96 | -0.37 | PASS |
| T170 | 2024 | -6.60 | 92 | 32.14 | -0.92 | PASS |
| T170 | 2025 | -4.23 | 52 | 32.71 | 1.27 | PASS |
| **DT** | 2021 | -7.72 | 47 | 7.39 | -1.74 | PASS |
| **DT** | 2022 | -9.18 | 114 | 7.37 | -1.69 | PASS |
| **DT** | 2023 | -2.52 | 45 | 59.44 | 7.35 | PASS |
| **DT** | 2024 | -10.59 | 129 | 40.54 | -5.48 | PASS |
| **DT** | 2025 | -9.53 | **223** | 15.01 | -2.07 | **FAIL (UW>200)** |
| T100/R0 | 2021 | -7.35 | 47 | 9.28 | -0.56 | PASS |
| T100/R0 | 2022 | -12.46 | 64 | 17.31 | 0.63 | PASS |
| T100/R0 | 2023 | -2.51 | 45 | 60.43 | 7.80 | PASS |
| T100/R0 | 2024 | -11.36 | 121 | 45.36 | -4.64 | PASS |
| T100/R0 | 2025 | -10.60 | **227** | 16.45 | -2.47 | **FAIL (UW>200)** |

Ca DT va gate-1.0/T100 (chua co throttle) DEU da FAIL o nam 2025 (UW=223 va 227, deu >200) — day
la chinh trieu chung UW-2025 da chan doan tu vong truoc (`DIAG_UW2025_SOURCE.md`). DT co cai thien
NHE UW-2025 so voi T100 khong-throttle (223 < 227) nhung khong du de ve duoi nguong 200, va toan
ky UW dai nhat cua DT (332 ngay, boc qua ranh gioi nam) con TE HON T100 (248 ngay) — xem muc 5.

## 5. u1-u4 (khoa truoc trong PREREG)

| Tieu chi | Nguong | Gia tri DT | Ket qua |
|---|---|---|---|
| **u1** breadth | n_eff_total(DT) >= 1.5*n_eff_total(T170) = 909.39 | 1091.15 | **PASS** |
| **u2** khau vi | appetite=current PASS toan ky+moi nam (UW<=200 la chinh) VA CAGR(DT)>=can duoi CI k=2 cua T170 (14.80%) | 2025 FAIL (UW=223>200), toan ky UW dai nhat=332>200; CAGR=27.38%>=14.80% (rieng le dat) | **FAIL** (vo o UW) |
| **u3** vs T170 | maxDD(DT)>=-14.8% VA UW(DT)<=115 | maxDD=-14.395% (dat) NHUNG UW=332 (khong dat, gap 2.9 lan nguong) | **FAIL** |
| **u4** theo-dd dung co che | UW(DT) < UW(R0) VA UW(DT) < UW(gate-1.0)=248 | UW(DT)=332 >= ca hai (R0=T100=248) | **FAIL** |

**PHAN QUYET: NULL** (theo dinh nghia PREREG muc 4: u2 vo UW>200 VA DT khong hon R0/gate-1.0 o UW
— ca hai dieu kien NULL deu xay ra dong thoi, khong phai truong hop bien).

## 6. Doi chieu DU BAO cua MASTER (muc 1 PREREG) — XAC NHAN, voi bien do lon hon du kien

MASTER du bao (ghi TRUOC khi chay): "drawdown-throttle gan nhu chac chan giam maxDD... NHUNG co
nguy co keo dai UW vi giam phoi nhiem luc duoi nuoc = it von de phuc hoi = hoi cham hon".

Ket qua thuc te KHOP CHINH XAC co che du bao, va manh hon:
- **maxDD giam dung nhu du bao**: -14.395% (DT) so voi -16.129% (gate-1.0 khong throttle) —
  giam ~1.7 diem %, throttle CO hoat dong dung thiet ke o mat maxDD.
- **UW KHONG giam ma TANG MANH, dung nhu du bao lo ngai**: 332 ngay (DT) so voi 248 ngay
  (gate-1.0 khong throttle) — **TANG 84 ngay (+33.9%)**, chu khong phai "khong doi" nhu kich ban
  nhe nhat trong du bao — ma la TE HON ca nen khong-throttle no dua tren. So voi incumbent T170
  (92 ngay), DT dai gap **3.6 lan**.
- Co che nhan dang: dung dinh nghia da ghi trong PREREG — throttle DUNG DUNG luc he can phuc hoi
  nhanh nhat (dang duoi nuoc) de GIAM chinh phoi nhiem giup phuc hoi, nen thoi gian tro ve dinh cu
  keo dai ra. Day la CUNG mot co che nhan quy da lam TASK B (pacing-size deu) NULL — bay gio da
  duoc xac nhan LAN THU BA, voi MOT thiet ke hoan toan khac (universal, theo dd noi tai, khong
  theo regime) tren CA HAI loai giai doan xau (bear-2022 lan bull-nhieu-2025 deu the hien trong so
  lieu per-year o tren — DT khong cuu duoc rieng nam nao ca).
- `du_bao_MASTER_xac_nhan (UW(DT) >= UW(T100))` = **True** (tinh boi `dd_throttle_metrics.py`).

=> Day la bang chung mach lac, KHONG phai ngau nhien mot lan: ba thiet ke phong thu doc lap khac
nhau ve co che (TASK B: giam deu khong dieu kien; B2 Buoc 2: giam theo REGIME cu the phat hien
duoc; B2 Buoc 3: giam theo DO SAU DRAWDOWN NOI TAI, khong can biet loai giai doan) DEU that bai
CUNG MOT LY DO: giam phoi nhiem = phuc hoi cham = UW khong giam (hoac tang). Ket luan hop ly nhat:
**UW la thuoc tinh NOI TAI cua huong breadth long-only** (them nhieu lenh o gate long hon), khong
phai loi thiet ke phong thu co the sua bang bat ky co che phoi-nhiem/sizing/admission-theo-dd nao
da thu.

## 7. Bien the ADMISSION (PREREG muc 3.3) — dieu kien kich hoat DA DAT, nhung KHONG chay

Nguong kich hoat da khoa TRUOC trong PREREG ("UW(DT) >= UW(gate-1.0)") **DA DAT** (332>=248) —
ve nguyen tac agent DUOC PHEP (khong BAT BUOC — PREREG dung "duoc phep... Mac dinh chi dang
sizing") them bien the ADMISSION (dung mo lenh MOI khi |dd(t)|>=D, giu lenh dang mo).

Quyet dinh cua agent: **KHONG chay bien the nay trong vong nay**, ly do ghi ro:
1. Phan quyet NULL da RAT RO RANG va nhat quan tren CA 3 tieu chi doc lap (u2, u3, u4 deu FAIL,
   khong phai bien) — them 1 bien the xac nhan se khong doi phan quyet cua DT (DT tu no da
   khong dat), chi co the tra loi cau hoi rieng "ADMISSION co lam tot hon DT khong" — mot cau hoi
   MOI, khac voi pham vi khoa cua PREREG nay (kiem dinh chinh DT).
2. ADMISSION dung vao diem cam GATE/entry (dung chung cho MOI bien the, kha nang cao hon anh
   huong duong OFF/cac profile khac so voi diem cam sizing rieng le da dung cho DT) — rui ro ky
   thuat cao hon cho cong OFF byte-identical, can mot vong PREREG rieng de lam dung muc do can
   trong.
3. Ky luat tai nguyen: da 1 chuoi 2 sim (T170-verify + DT, ~15 phut + build) voi shadow-c3 dung
   ~46 phut; them 1 sim nua (+code moi +build +re-verify OFF) se keo dai downtime dang ke ma gia
   tri tang them (theo diem 1) la xac nhan, khong phai quyet dinh.

Day la bang chung mo cho MASTER can nhac: neu muon loai tru khong con nghi ngo "co the mot co che
ADMISSION rieng se cuu duoc" truoc khi dong hoan toan huong breadth, ADMISSION van la mot buoc
sau hop ly (round rieng, PREREG rieng) — nhung KHONG lam thay doi phan quyet NULL cua vong nay.

## 8. Diff Java (tom tat)

`src/main/java/com/binance/chuyennd/tradecore/PacingSizing.java`: them mode thu 3 `DT` cho
`Configs.SIZE_PACING_MODE` (OFF|P0|P3|**DT**). Them: `DT_MODE` flag, hang so `DT_D=0.15f`,
`DT_FLOOR=P0_MULT=0.2146f`, bien static `dtPeakEquity` (rolling max equity, sentinel -1),
ham `ddThrottleMultiplier()` (doc `BudgetManagerSimple.getInstance().equityNow()`, cap nhat
`dtPeakEquity` NGAY TRUOC khi tinh `dd`, tra `clip(1-|dd|/D, floor, 1)`, fallback 1.0f khi thieu
du lieu). `multiplier(tsMs)` them 1 nhanh `if (DT_MODE) return ddThrottleMultiplier();`. **Duong
OFF (MODE=="OFF") khong doi mot dong nao** — `ACTIVE=false` van chan truoc khi cham cac nhanh
mode, cong OFF byte-identical da xac nhan md5 khop tuyet doi. Build: `mvn -q -DskipTests package`
RC=0.

File moi: `profiles/x1_c3_full_dt.properties` (= `x1_c3_full.properties` + `SIZE_PACING_MODE=DT`),
`research/analysis/dd_throttle_metrics.py` (script do u1/u3/u4, khong sua `bigdown_struct.py`/
`c3_rates.py`/`x1_rates.py` goc).

## 9. Ket luan & de xuat

**NULL — xac nhan du bao MASTER.** Drawdown-throttle universal, du thiet ke khac han 2 co che
truoc (khong theo regime cu the, chi 1 tham so D + floor tinh tu du lieu), van roi vao dung ho
nhan qua "giam phoi nhiem luc duoi nuoc = phuc hoi cham = UW khong giam" — lan nay con RO RANG
HON: UW khong chi "khong giam" ma **TANG 34%** so voi chinh nen gate-1.0 no dung, va gap 3.6 lan
incumbent T170.

Theo PREREG muc 7 (Y NGHIA), day la co so de **DONG HUONG BREADTH LONG-ONLY** — ba thiet ke phong
thu doc lap (TASK B, B2 Buoc 2, B2 Buoc 3) deu that bai cung mot ly do co che, tren toan bo
2021-07-01..2025-12-31 kem ca 2022 (bear) lan 2025 (bull-nhieu). De xuat: agent KHONG tu viet
`power_wall.md` (tong hop chien luoc xuyen suot 3 vong, la quyet dinh cap MASTER) — bao cao day
du so lieu nay len MASTER de MASTER xac nhan phan quyet dong huong va quyet dinh buoc chuyen sang
TASK D (alpha moi, trigger khong tuong quan MOM15).
