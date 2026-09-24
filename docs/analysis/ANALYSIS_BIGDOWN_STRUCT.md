# ANALYSIS_BIGDOWN_STRUCT — bigdown co phai nhan to dong-thua? (TASK A, 0-sim)

Ket qua tinh theo dung cong thuc da khoa trong `docs/prereg/PREREG_BIGDOWN_STRUCT.md` (commit `22c0815`).
Script: `research/analysis/bigdown_struct.py`. Output tho: `research/analysis/out/bigdown_struct.json`.
0-sim tuyet doi: khong chay java sim, khong xgboost, khong sua `.java`; chi doc
`printDone.csv`/`sim.out` cua T170 (`X1_GS_T170_2021`) va T100 (`X1_C3_FULL_2021`) + `CLOSES_1H.bin`.

Sanity check truoc khi tin so: `n_rows/n_episodes` = 1089/1069 (T170) va 2559/2505 (T100) — KHOP
CHINH XAC voi `docs/diag/DIAG_BIGDOWN_CONCENTRATION.md` cua vong truoc => du lieu nap dung.

## 0. Dinh nghia headline dang dung: BD1a (BTC ret 24h <= -5%)
`flag_frac` (ti le gio trong 39480 gio grid, 2021-2025 truoc HOLDOUT) cua tat ca dinh nghia da khoa
song song:

| Dinh nghia | % gio bi flag |
|---|---|
| BD1a (5%/24h) — headline | 3.37% |
| BD1b (8%/24h) | 0.83% |
| BD1c (10%/72h) | 1.95% |
| BD1q (rolling p05, 60 ngay) | 5.08% |
| BD2_70 (breadth >=70% do do) | 33.93% |
| BD2_80 | 25.13% |
| BD2_90 | 13.47% |

## 1. Tra loi 4 cau hoi (Q1-Q4, muc 2.1 PREREG)

**Q1 — Dong-thua cua T170 co tap trung trong bigdown khong?** CO, ro rang.
- `phi(lo | exposed_bd=1)` = **2.68** vs `phi(lo | exposed_bd=0)` = **1.37** => ty le **1.96x**
  (M4, T170). ICC(loss, cohort ngay) cung tang manh: 0.204 (exposed=1) vs 0.046 (exposed=0).
- M5: maxDD cua T170 (-11.84%, dinh 2022-10-17 -> day 2022-11-10) co **100%** do sut xay ra trong
  ngay bigdown (BD1a). Nhung chi 11.86% tong so ngay-duoi-nuoc la ngay bigdown => rui ro tap trung
  o mot so it ngay hiem nhung rat nang, dung mo hinh "duoi beo" (fat-tail) hon la rui ro dan trai.

**Q2 — Gate mo (T100) co gay "nhoi o at" va la nguon dong-thua khong?** CO, co bang chung cau truc
ro rang tren ca hai truc (so lenh moi + von trien khai), va manh hon T170 o CA HAI:
- Burst (M2, lenh moi/gio, T100): trung binh trong-bigdown 0.355 vs ngoai-bigdown 0.055 (~6.4x);
  cua so 4h: 2.277 vs 0.189 (~12x); p99/4h = 19 lenh trong bigdown vs 8 ngoai. T170 cung co burst
  ratio tuong tu ve TY LE (0.216 vs 0.021, ~10x) nhung mean tuyet doi thap hon nhieu (gate chan bot
  so luong).
- Von trien khai (M3, Sigma(notional)/equity): T100 median trong-bigdown = **0.270** (~4.7x T170's
  0.058). Su kien-onset (235 episode): T100 DA o muc ~0.207 TRUOC khi bigdown bat dau va gan nhu
  KHONG doi sau 1h/4h (0.211/0.205) — nghia la T100 gan nhu luon chay o muc tai gan-bang du truoc
  khi crash toi, khong con "chan doc" de giam tai. T170 nguoc lai: ti le = 0 truoc onset, van con 0
  sau 1h, chi len 0.026 sau 4h — gate 1.70 THUC SU giu duoc mot phan tai trong luc bigdown moi bat
  dau, dung nhu thiet ke.

**Q3 — ICC/dong-thua tach theo bigdown khac gi so voi chung (T100)?**
- g1 chinh thuc (T100, exposed_bd): `phi_ratio = 2.082` (PASS nguong 1.5).
- ICC(roi, cohort ngay, all) cua T100 = **0.1016** — GAP DOI so voi ICC cua T170 (0.0516, khop voi
  so lieu vong truoc). Dieu nay cung co gia thuyet cua MASTER o vong truoc: ICC thap cua T170 mot
  phan la HE QUA cua gate chat (loc bot dong-thua tuong quan), khong phai T170 "vo can" voi bigdown.
- M6 n_eff: T100 co n_eff_total (dong, cohort ngay) = 1104/2521 lenh (ICC keo n_eff xuong ~44%
  so N); T170 = 606/1084 (~56%) — T170 giu duoc ty le n_eff/N cao hon (it tuong quan hon), cung
  chieu voi ICC thap hon.

**Q4 — Don vi dong printDone = lenh hay leg DCA?** = leg (co the la `PREDICT_SYMBOL_TRADE` hoac
`DCA_LEVEL1`); `episode` = nhom `(sym,end)`. Ty le row/episode ~1.02 o CA HAI run (T170: 1.019,
T100: 1.022) => phan lon la leg don, DCA continuation la thieu so (~2%). `level=BIG_DOWN` KHONG
xuat hien o ca hai run (`BD_SEL_MODE=off`, xac nhan lai o PREREG muc 1.1).

## 2. M7 — lenh "bien" T100\T170 va MOT CANH BAO PREREG QUAN TRONG

**Sai lech so voi PREREG (ghi truoc/sau day):** PREREG muc 4 (M7) dat nguong chap nhan "T170 la
tap con cua T100" o **>=90% khop** theo khoa `(sym, start_naive)` truoc khi coi tap "bien" la mot
uoc luong sach cho "hieu ung rieng cua gate". Ket qua do duoc: **match_rate = 32.6%** — THAP HON
NHIEU nguong 90%. Day la mot PHAT HIEN, khong phai loi tinh: da `diff` hai file profile va xac nhan
**CHI KHAC DUY NHAT** o dong `SIM_GATE_DYN_SCALE=1.70` (T170) — tat ca tham so con lai (capital,
DCA grid, v.v.) giong het T100. Vi vay gia thuyet hop ly nhat la: gate dong (dyn threshold) khong
chi loc SO LUONG lenh ma con **doi GIO vao lenh** cua chinh nhung co hoi duoc ca hai run cung "thay"
(vi nguong dong thay doi theo gio, mot candidate co the truot tu gio t sang gio t' o run kia) — nen
khoa dung `(sym, start_naive)` chinh xac tung phut se bo lo nhieu cap trung khop that. **Ket luan:**
so lieu M7 duoi day CHI nen doc nhu uoc luong xap xi/dinh huong cho "lenh duoc them vao khi mo gate
long hon", KHONG phai mot phep tru tap chinh xac (T100 - T170). Khong the nang cap do chinh xac nay
trong pham vi 0-sim (can candidate/tick log that, xem muc "khong tinh duoc" ben duoi).

Voi canh bao do, so lieu tinh duoc tren tap "bien" (n=2204 dong, la dong T100 khong tim thay khoa
khop trong T170):
- ROI trung binh = **+1.907%**, CI90% (block-72h bootstrap, NREP=2000) = **[+1.169%, +2.621%]** —
  hoan toan duong, khong cham -0.5pp.
- Win rate = 83.76%. ICC(roi, cohort ngay) = 0.100. phi(lo) = 2.042 (J=201 ngay).
- % dong bien co `enter_bd=1` (mo NGAY trong gio bigdown) = **17.97%**; % co `exposed_bd=1` (trai
  qua bigdown bat ky luc nao trong doi lenh) = **48.87%**.
=> Tap lenh duoc "them vao" khi mo gate KHONG co ROI trung binh am, nhung gan mot nua so lenh nay
trai qua bigdown va co do tuong quan lo (phi/ICC) cao hon muc trung binh cua ca run — tuc la day la
mot nguon rui ro DUOI (tail) hon la mot nguon EV am ro rang.

## 3. Bang tong hop M1-M6 (T170 vs T100)

| Metric | T170 (gate 1.70) | T100 (gate 1.0) |
|---|---|---|
| M1 n_rows / n_episodes | 1089 / 1069 | 2559 / 2505 |
| M2 rows/1h mean: bigdown vs non | 0.216 vs 0.021 (10.3x) | 0.355 vs 0.055 (6.5x) |
| M2 rows/4h p99: bigdown vs non | 17.7 vs 0.0 | 19.0 vs 8.0 |
| M3 Sigma(notional)/equity, median: bigdown vs non | 0.058 vs 0.000 | 0.270 vs 0.000 |
| M3 onset: pre / +1h / +4h (median) | 0.000 / 0.000 / 0.026 | 0.207 / 0.211 / 0.205 |
| M4 phi(lo): exposed1 vs exposed0 | 2.68 vs 1.37 (1.96x) | 3.49 vs 1.68 (2.08x, = g1) |
| M4 ICC(roi, ngay, all) | 0.0516 | 0.1016 |
| M5 maxDD % (peak->trough) | -11.84% (2022-10-17 -> 11-10) | -16.13% (2021-11-15 -> 2022-05-12) |
| M5 % do sut maxDD trong ngay bigdown | 100.0% | 74.8% (= g2) |
| M5 % ngay-duoi-nuoc la bigdown | 11.86% | 11.35% |
| M6 n_eff_total (dong, cohort ngay) / N | 606 / 1084 | 1104 / 2521 |

## 4. Bang do-dap-ung (sensitivity) g1/g2 tren T100 qua tat ca dinh nghia bigdown

| Dinh nghia | flag% | g1 (phi ratio) | g2 (% maxDD trong bigdown) |
|---|---|---|---|
| BD1a (headline) | 3.37% | 2.08 | 74.8% |
| BD1b (8%/24h, chat hon) | 0.83% | 1.93 | 53.4% |
| BD1c (10%/72h) | 1.95% | 2.55 | 71.0% |
| BD1q (p05 60 ngay) | 5.08% | 3.60 | 98.9% |
| BD2_70 (breadth) | 33.93% | null (thoai hoa, xem ghi chu) | 100.0% |
| BD2_80 (breadth) | 25.13% | 1.57 | 100.0% |
| BD2_90 (breadth) | 13.47% | 2.20 | 99.9% |

Ghi chu BD2_70: `phi_exposed0` khong tinh duoc (mau `exposed_bd=0` con lai qua it/qua dong nhat de
uoc luong on dinh khi 33.9% thoi gian da bi flag) — ghi ro la KHONG tinh duoc, khong suy dien.
**Ket luan do-dap-ung: g1>=1.5 va g2>=50% giu vung tren MOI dinh nghia tinh duoc** (6/7; 1/7 khong
tinh duoc do thoai hoa mau) — ket luan Q1-Q3 KHONG phu thuoc vao viec chon dinh nghia bigdown nao.

## 5. Du bao ghi truoc (PREREG muc 5) — doi chieu

(a) `phi(exposed1) >> phi(exposed0)` o ca hai run: **DUNG** (1.96x T170, 2.08x T100).
(b) T100 nhoi manh hon T170 ro ret ca ve burst va Sigma(notional)/equity: **DUNG**.
(c) Phan lon maxDD ca hai den tu bigdown: **DUNG** (100% T170, 74.8% T100).
(d) Lenh bien T100\T170 tap trung bat can xung vao bigdown, phi cao hon trung binh, ROI duong
nhung mong: **DUNG mot phan** — ROI duong (+1.91%) khong "mong" nhu du doan (CI90 hoan toan tren
0, khong sat -0.5pp), nhung phi/ICC cua tap bien (2.04/0.10) DUNG la cao hon (ICC bien 0.100 >
ICC toan T170 0.0516). Diem sai voi du doan: PREREG doi ROI "mong" nhung so do la khong-mong o
muc bootstrap CI90 nay — ghi nhan la sai lech so voi du doan, KHONG dieu chinh nguong sau khi thay
so.

## 6. Cong GO/NO-GO cho TASK B (PREREG muc 6, nguyen cong thuc)

| Gate | Gia tri | Nguong | Ket qua |
|---|---|---|---|
| g1 phi ratio (T100) | 2.082 | >= 1.5 | **PASS** |
| g2 % maxDD trong bigdown (T100) | 74.85% | >= 50% | **PASS** |
| g3 ROI bien + CI90 | mean +1.907%, CI90 [+1.17%, +2.62%] | mean>0 VA CI90 khong hoan toan duoi -0.5pp | **PASS** |
| g4 diem cam admission/sizing OFF byte-identical | — | — | **NGOAI PHAM VI TASK A** — can A-recon |

**Ket luan TASK A: g1-g3 (thuoc pham vi 0-sim cua TASK A) DEU PASS.** GO/NO-GO **tong the** cho
TASK B con phu thuoc g4 (ket qua tu agent A-recon song song) — chua ket luan duoc o day.

## 7. Nhung gi KHONG tinh duoc / gioi han (PREREG muc 7, xac nhan lai sau khi chay)

1. Khong co candidate/tick log truoc gate (chi co `printDone.csv` da qua gate) => M2 burst dung
   T100-admitted lam PROXY cho "candidate/gio", KHONG phai luong lenh thuc te truoc khi bi loc.
   Nghia la con so nhoi-o-at o day co the con la UOC LUONG THAP hon thuc te (vi cac lenh bi tu choi
   boi risk-check khac khong xuat hien trong printDone.csv).
2. `equity(t)` noi-gio la xap xi tu snapshot ngay gan nhat qua `eq_day_of`/`asof_leq`, khong co
   snapshot noi-ngay that => ty so Sigma(notional)/equity co the sai lech nho trong ngay bien dong
   manh (chinh la ngay bigdown — luc equity thay doi nhanh nhat trong ngay).
3. BD2 breadth dung `CLOSES_1H.bin` (do gio) — khong bat duoc bigdown-trong-vai-phut nhu
   `MarketBigChangeDetector` (Java, 1-phut, causal). Day la gioi han do granularity, khong phai loi.
4. M7: xem canh bao rieng o muc 2 — match_rate 32.6% << 90% nguong PREREG => tap "bien" la uoc
   luong xap xi, khong phai phep tru chinh xac; ly do co the la gate lam LECH GIO vao lenh (khong
   chi loc so luong) chu khong phai do hai profile khac tham so nhau (da `diff` xac nhan CHI khac
   `SIM_GATE_DYN_SCALE`).
5. Khong chay them dose-response tren cac run gate trung gian (GS055/070/085/120/140) du PREREG co
   du kien "neu kip" — uu tien hoan tat day du M1-M7 cho T170/T100 (2 run brief yeu cau) truoc, va
   het pham vi 0-sim/thoi gian danh cho TASK A; day la lua chon PHAM VI, ghi ro chu khong an di.
6. `g4` (diem cam admission/sizing OFF byte-identical) ngoai pham vi thiet ke cua TASK A tu dau
   (PREREG muc 6) — can doi ket qua A-recon.
