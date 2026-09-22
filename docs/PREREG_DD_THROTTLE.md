# PREREG_DD_THROTTLE — TASK B2 Buoc 3: drawdown-throttle (phep thu dut khoat cho breadth) (2026-09-21)

Theo thiet ke MASTER `TASK_B2_step3_drawdown_throttle.md`. Khoa TRUOC khi build/chay bat ky bien
the nao. Khong sua nguong/cong thuc sau khi thay so — moi lech (neu co) duoc ghi ro la "phat hien
luc chay", khong hoi to PREREG nay.

## 0. LUAT — nhu B2 (khong noi)

An toan: KHONG HOLDOUT 2026 (`SIM_END_DATE<=20251231`, khong dung seal); KHONG ssh 242; KHONG
`git push`; khong xoa thu muc bao ve; `.git/index.lock` doi 30s retry. **1 job nang/lan**
(`free -g`>=12G, `pgrep java` rong truoc moi sim) — `sudo systemctl stop shadow-c3` TRUOC chuoi
sim, `sudo systemctl start shadow-c3` NGAY SAU, verify active + log sach (khong -2014; -2015
IP-whitelist goi phu la binh thuong), ghi moc dung/bat. Cong tai lap T170 md5
`efb793e2468ca3a7318da0f0ad23d4fc` bat buoc TRUOC khi chay bien the moi. Cong OFF byte-identical
bat buoc cho flag moi (`SIZE_PACING_MODE=DT`) — OFF khong cho md5 nay => DUNG, bao MASTER, khong
chay bien the. Khau vi hien hanh: `x1_rates.py --appetite current --k <k>`.

## 1. GIA THUYET + DU BAO GHI TRUOC CUA MASTER (khong doi sau khi thay so)

H: Tren nen gate 1.0 (breadth), mot **drawdown-throttle** — giam phoi nhiem MOI khi equity dang
duoi dinh cu (rolling max), causal, KHONG can biet loai giai doan xau — keo UW <= 200 ma giu
n_eff >= 1.5x T170. Vi ca bear-2022 lan bull-nhieu-2025 deu bieu hien la "he duoi nuoc", mot co
che theo dd noi tai nham duoc CA HAI cung luc ma chi 1 tham so (it overfit hon nhieu-detector).

**DU BAO CUA MASTER (ghi TRUOC khi chay)**: nhieu kha nang **NULL** — drawdown-throttle gan nhu
chac chan giam maxDD (giam size khi duoi nuoc), NHUNG co nguy co **keo dai UW** vi giam phoi
nhiem luc duoi nuoc = it von de phuc hoi = hoi cham hon = thoi gian duoi nuoc khong giam hoac
tang. Day dung co che da lam TASK B (pacing-size) NULL: UW quyet boi *nhip phuc hoi*, khong phai
*bien do lo*. Neu du bao dung => bang chung manh UW la NOI TAI cua breadth long-only (khong co
che phoi-nhiem nao giai duoc) => dong huong breadth dut khoat. Neu SAI (UW ve <=200 ma n_eff giu)
=> giai tron ven, tin tot lon.

H0 (NULL): UW khong ve <=200; HOAC doi chung giam-deu (R0) dat ngang DT (phong thu theo-dd khong
hon giam-chung).

Agent (nguoi thuc thi) se KHONG dieu chinh D/floor sau khi thay so. Neu quan sat thay dang "giam
size" keo dai UW dung nhu du bao, duoc phep them 1 bien the dang ADMISSION (dung mo lenh MOI khi
dd sau, giu lenh dang mo) — khai bao la bien the thu 2 (k tang len 3), xem muc 3.3.

## 2. CO CHE (khoa truoc khi chay, toi thieu tham so, causal)

`dd(t) = equity(t) / rollingMaxEquity(<=t) - 1` (<=0), equity NOI TAI cua chinh he backtest
(khong phai gia BTC/thi truong ngoai), causal tuyet doi (chi dung <= t).

`mult(t) = clip( 1 - |dd(t)| / D , floor , 1 )` — phoi nhiem MOI (nhan vao budget truoc DCA-grid,
giong VolTargetSizing/PacingSizing) co tuyen tinh theo do sau drawdown, cham `floor` khi
`|dd(t)| >= D`.

### Chon D (khoa TRUOC)
`D = 0.15` (15%) = nua nguong maxDD khau vi hien hanh (30%). Ly le: bat dau phong thu MANH (tien
ve floor) khi he da mat nua "ngan sach" rui ro cho phep — con nua con lai (15-30%) van co the
phuc hoi ma khong pha khau vi, nhung tu diem giua tro di can co dong luc phong thu manh hon tuyen
tinh don thuan tu 0.

### Chon floor (khoa TRUOC, tinh tu du lieu)
`floor = 0.2146` — tai su dung nguyen ven `PacingSizing.P0_MULT` (da tinh trong TASK B:
`median(margin/equity|bigdown,T170) / median(margin/equity|bigdown,T100) = 0.057965.../0.270101...`).
Ly do dung lai (khong tinh moi): TASK B2 chan doan UW-2025 (`DIAG_UW2025_SOURCE.md`, Q3) da tinh
DOC LAP mot ty le tuong duong nhung KHONG dieu kien bigdown — Sigma(notional)/equity T170/T100
"MOI LUC" trong toan cua so 2021-07-01..2025-12-31 = 0.058/0.270 = 0.2148. Hai phuong phap doc
lap (bigdown-conditional tu TASK B, va moi-luc tu chan doan UW-2025), tren hai tap du lieu con
khac nhau (bigdown BD1a vs toan cua so), hoi tu ve cung mot con so ~0.215 — day la bang chung day
la mot TY LE CAU TRUC on dinh cua he thong (T170 luon chay it phoi nhiem hon gate-1.0 ~4.5-5 lan
MOI LUC, khong rieng luc bigdown), khong phai trung hop 1 lan do. Chot `floor = P0_MULT = 0.2146`
dung y nhu yeu cau thiet ke "tinh tu du lieu, chot truoc" — khong chay them script tinh moi vi so
da co san va da duoc kiem chung cheo.

Luu y ve dinh nghia `equity(t)`: dung `BudgetManagerSimple.equityNow()` (= balanceCurrent +
unProfit — CUNG dinh nghia lam goc SIZING cho toan bo budget trong Simulator, xem comment B3
2026-09-05 trong `BudgetManagerSimple.java`), KHONG dung nhanh mtm pessimistic (bar.low,
`equityPeakMtm`/`maxDDMtm` — day la kenh REPORT-ONLY rieng cho maxDD chinh thuc, khong dung de
quyet dinh sizing). Chon `equityNow()` vi day la dinh nghia equity DUY NHAT da dung xuyen suot de
tinh budget lenh moi (nhat quan noi bo) — he qua: dd(t) do boi throttle co the NONG hon (it am
hon) so voi maxDD chinh thuc bao cao trong RESULT (vi maxDD chinh thuc dung bar.low pessimistic),
nen throttle co the kich hoat FLOOR o muc dd nong hon 15% thuc te bar-low — day la lua chon thiet
ke chu dong (nhat quan sizing), se doi chieu thuc nghiem trong RESULT.

### Cai cam (diem cam sizing, PacingSizing-style, byte-identical OFF)
Mo rong `PacingSizing` (khong tao class moi) bang mode thu 3 `DT` cho
`Configs.SIZE_PACING_MODE` (hien co OFF|P0|P3). `PacingSizing.ACTIVE` van chi false khi
MODE=="OFF" — them nhanh DT KHONG dong den duong OFF => cong OFF byte-identical duoc bao toan
trivial (khong sua gi tren duong OFF).

Rolling-max equity (`dtPeakEquity`, static float, sentinel -1) duoc cap nhat NGAY TRUOC khi tinh
dd, o dau moi loi goi `ddThrottleMultiplier()` — ham nay duoc goi tai chinh diem cam da co cua
`PacingSizing.multiplier(tsMs)` trong `SimulatorMarketLevelTicker1MStopLoss.java` (dong ~1318,
SAU `VolTargetSizing`, TRUOC ty trong DCA-grid — diem cam sizing da duoc TASK B recon GO). Vi
Simulator xu ly 1 luong tuan tu theo thoi gian (khong da luong trong quy trinh backtest nay),
`dtPeakEquity` tai moi thoi diem goi chi phan anh cac gia tri equity <= t da tung duoc quan sat
=> KHONG lookahead. Khong can hook them vao Simulator/BudgetManagerSimple — tu chua het logic
trong `PacingSizing`, giam dien sua doi.

`DT_MODE` fallback ve `multiplier=1.0f` khi thieu du lieu equity (eq null/<=0) — giong quy uoc
P0/P3, KHONG BAO GIO tra null/NaN/<=0.

## 3. BIEN THE (k trong PREREG)

Baseline (khong tinh k): **T170** (`X1_GS_T170_2021`, dung lai neu md5 re-verify khop
`efb793e2468ca3a7318da0f0ad23d4fc`), **gate-1.0/T100** (`X1_C3_FULL_2021`, dung lai nguyen ven,
KHONG chay lai — n=2559, n_eff_total=1103.86, maxDD=-16.13%, UW=248, CAGR=31.94% theo
`docs/RESULT_PACING_BIGDOWN.md`/`docs/RESULT_REGIME_GATE.md`).

### 3.1 DT (CHINH)
`profiles/x1_c3_full_dt.properties` = `x1_c3_full.properties` + `SIZE_PACING_MODE=DT`. Tag chay
`X1_C3_FULL_2021_DT`.

### 3.2 R0 (doi chung, tach phong-thu-theo-dd khoi giam-chung)
Gate CO DINH DEU `SIM_GATE_DYN_SCALE=g0`, `g0` chon de tong so lenh toan ky (`n_rows` trong
`printDone.csv`) cua R0 xap xi cua DT. **Phuong phap chon g0 (khoa TRUOC, chi tinh SO sau khi co
ket qua DT)**: tai su dung CHINH XAC cong thuc noi suy log-tuyen tinh da khoa o TASK B2 Buoc 2
(`docs/PREREG_REGIME_GATE.md` muc 3) tu 2 diem neo trong DUNG cua so 2021-07-01..2025-12-31:
`gate=1.00 -> n=2559` (gate-1.0/T100), `gate=1.70 -> n=1089` (T170). Giai `ln(n) = a + b*gate` voi
`b = (ln(1089)-ln(2559))/(1.70-1.00) = -1.22166`, `a = ln(2559) - b*1.00 = 9.06946`. Sau khi co
`n_total(DT)` tu sim DT, tinh `g0 = (a - ln(n_total(DT))) / (-b)`, lam tron 2 chu so thap phan,
kep trong `[0.50, 2.00]`. Day la NOI SUY THEO SO LENH, khong tinh chinh theo huong co loi cho DT —
cong thuc co dinh truoc, chi thay so `n_total(DT)` vao sau.

Bien the R0 gate=1.18 da co tu Buoc 2 (`X1_C3_FULL_2021_REGIME_R0`, n=1908) CHI duoc tai su dung
NEU `n_total(DT)` ra xap xi 1908 (chenh lech <5%, tuc n_total(DT) trong [1813, 2003]) — kiem tra
va ghi ro trong RESULT truoc khi quyet dinh dung lai hay chay R0 moi. Neu chay moi:
`profiles/x1_c3_full_dt_r0.properties` = `x1_c3_full.properties` + `SIM_GATE_DYN_SCALE=g0` (tinh
nhu tren). Tag chay `X1_C3_FULL_2021_DT_R0`.

### 3.3 (co dieu kien) ADMISSION — CHI mo neu quan sat u4 xac nhan du bao MASTER
Neu, sau khi chay DT, quan sat thay UW(DT) >= UW(gate-1.0) (dung dang du bao — "giam size" khong
giam duoc UW, thap chi con keo dai/khong doi), agent duoc phep them **1** bien the ADMISSION:
dung MO LENH MOI khi `|dd(t)| >= D` (nhi phan, cung `dd(t)`/`D` da khoa o muc 2 — KHONG them
tham so moi), GIU nguyen cac lenh dang chay (khong dong som). Day la bien the THU HAI, k TANG len
3 (T170 khong tinh, DT + R0 + ADMISSION = 3 ung vien). Se khai bao ro trong RESULT neu duoc
kich hoat, cung ly do cu the (so UW quan sat) va xac nhan day KHONG phai hoi to nguong — nguong
kich hoat ("UW(DT) >= UW(gate-1.0)") da khoa TRUOC o day, chi so duoc dien sau.

## 4. TIEU CHI (khoa truoc; UW la chinh)

- **u1 breadth**: `n_eff_total(DT) >= 1.5 * n_eff_total(T170)` = `1.5 * 606.26 = 909.39`.
- **u2 khau vi**: PASS `x1_rates.py --appetite current --k <k>` hien hanh (maxDD<=30%, UW<=200/nam,
  nam khong am, quy>=-15%) TOAN KY VA MOI NAM (2021-2025), DAC BIET UW<=200 (day la tieu chi
  quyet dinh cua vong nay); VA `CAGR(DT) >= can duoi CI95-72h(k) cua T170` (`cagr_ci_t170.py
  --k <k> X1_GS_T170_2021`, k = so ung vien trong round nay — mac dinh 2 (DT+R0), thanh 3 neu mo
  them ADMISSION o muc 3.3).
- **u3 vs incumbent (T170)**: `maxDD(DT) >= -14.8%` VA `UW(DT) <= 115` (ngat 25% tren maxDD/UW
  cua T170, cung cong thuc da dung o TASK B2 Buoc 2).
- **u4 theo-dd dung co che (quyet dinh dung/sai du bao MASTER)**: `UW(DT) < UW(R0)` VA
  `UW(DT) < UW(gate-1.0 khong throttle, =248)` — bang chung throttle theo-dd THUC SU giam (khong
  chi khong tang) UW so voi ca doi chung giam-deu LAN so voi nen khong throttle. Neu
  `UW(DT) >= UW(gate-1.0)` => XAC NHAN du bao MASTER (throttle keo dai UW).

**Phan quyet**: THANG = DT dat DONG THOI u1-u4. NULL = u2 vo (UW>200 bat ky nam/toan ky nao) HOAC
DT khong hon R0/gate-1.0 o UW (u4 fail). HON HOP = con lai (vd dat u1-u3 nhung u4 khong ro rang,
hoac ADMISSION cai thien mot phan).

## 5. DO — metric tong hop/phan phoi (KHONG khoa sym,start). Cung cua so 2021-07-01..2025-12-31,
Oracle ARM64. Bao per-year. Tai su dung NGUYEN VAN `bigdown_struct.py`/`c3_rates.py`/`x1_rates.py`
(KHONG sua) qua 1 script moi `research/analysis/dd_throttle_metrics.py` (theo dung mau
`pacing_taskb_metrics.py`/`regime_gate_metrics.py` cua 2 vong truoc) tinh u1/u3/u4; u2 tinh rieng
bang `x1_rates.py --appetite current --k <k> X1_GS_T170_2021 X1_C3_FULL_2021_DT` (va lai voi R0)
+ `cagr_ci_t170.py --k <k> X1_GS_T170_2021`.

## 6. QUY TRINH

`docs/PREREG_DD_THROTTLE.md` (file nay, muc 2 co che + D/floor + bien the + u1-u4 + du bao muc 1
+ phan quyet) commit TRUOC (rieng, khong kem code) -> code (`PacingSizing.java` mode DT, cai vao
diem cam sizing co san, giu OFF byte-identical) -> build -> cong OFF T170 md5
`efb793e2468ca3a7318da0f0ad23d4fc` -> dung shadow-c3 -> sim TUAN TU (T170 verify, DT, R0 neu can
chay moi, ADMISSION neu dieu kien muc 3.3 kich hoat) -> bat lai shadow-c3, verify active + log
sach -> tinh u1-u4 (`dd_throttle_metrics.py` + `x1_rates.py` + `cagr_ci_t170.py`) per-year ->
`docs/RESULT_DD_THROTTLE.md` verdict + doi chieu du bao muc 1 -> commit code+doc branch `module`
(KHONG push) -> don `wfo_ds` tam, giu `printDone.csv`/`sim.out`.

OFF khong byte-identical => DUNG, bao MASTER, khong chay bien the.

## 7. Y NGHIA (diem quyet dinh lon)

- THANG => breadth giai duoc bang phong thu universal => shadow paper song song >=1 thang truoc
  khi ban doi incumbent.
- **NULL => DONG HUONG BREADTH LONG-ONLY dut khoat**: ghi `power_wall.md` ket luan day du — UW la
  noi tai cua breadth (da thu size-pacing/TASK B, regime-per-type/B2 Buoc 2,
  universal-dd-throttle/B2 Buoc 3; khong co che phoi-nhiem nao giai duoc vi giam phoi nhiem = phuc
  hoi cham = UW khong doi). Chuyen TASK D (alpha moi: tang so cuoc bang trigger khong tuong quan
  MOM15) nhu duong power con lai.

## 8. Sau khi xong
Cap nhat project memory (`round_2026-09-20_beta_decomp_and_data_survey.md` + `MEMORY.md`), bao
MASTER: bang T170/gate-1.0/DT/R0 (n_eff_total, ICC, maxDD, UW, CAGR+CI, per-year 2021-2025),
u1-u4 PASS/FAIL, verdict, doi chieu DU BAO muc 1 (throttle giam hay KEO DAI UW — so cu the), cong
OFF PASS, moc dung/bat shadow-c3, diff Java.
