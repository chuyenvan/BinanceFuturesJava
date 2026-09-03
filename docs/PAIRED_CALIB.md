# PAIRED_CALIB — hieu chuan cong cu do GHEP CAP o tang TUNG LENH

Ngay: 2026-09-03. Pham vi: **CHI DEV**. Khong cham VALIDATION (2024-07-15..2025-12-31),
khong cham HOLDOUT 2026. Khong chay java, khong backtest, khong train.

Phuong phap: **`docs/PREREG_PAIRED.md`, commit `c96ddb3`** (2026-09-03 19:41:11 +0700) — chot
**TRUOC** khi tinh bat ky hieu / CI nao o tang nay. Cong cu: `research/analysis/paired_test.py`.
Ban chay: `/home/ubuntu/paired/calib2.out`, `/home/ubuntu/paired/nc.out`,
`/home/ubuntu/paired/paired_out.json`.

Trich lai cam bay da chot o `PREREG_PAIRED.md` §9 (bat buoc): so sanh boi phai hieu chinh;
**tang tung lenh KHONG thay the rang buoc maxDD** (maxDD la tinh chat cua duong equity, khong phai
trung binh cua lenh); thang o tang lenh la **dieu kien CAN, khong phai DU**; moi so o day la
in-sample DEV.

---

## 1. DOI CHUNG AM — PASS toan bo

`PREREG_PAIRED.md` §11.1. Neu bat ky muc nao khac 0 thi cong cu SAI va moi ket qua khac vo gia tri.

| # | Cap | md5 `printDone.csv` | `d` (ca 4 dai luong, ca 3 do dai khoi) | CI95 | sd | Ket |
|---|---|---|---|---|---|---|
| NC1 | `C2b` vs `C2b` | giong (cung file) | **0.000000** | **[0, 0]** | 0 | **PASS** |
| NC2 | `K1_conc25` vs `K0_h1a_prof` | `3c9e0352...` = `3c9e0352...` | **0.000000** | **[0, 0]** | 0 | **PASS** |
| NC3 | `K1_conc25` vs `K2_conc20` | `3c9e0352...` = `3c9e0352...` | **0.000000** | **[0, 0]** | 0 | **PASS** |
| NC4 | `BR2_both` vs `BR1_margin` | `95c10404...` = `95c10404...` | **0.000000** | **[0, 0]** | 0 | **PASS** |

Tang tham chieu equity trong cung cong cu cung ra `d = 0`, `sd = 0` cho ca 4 cap.
Phan quyet cua ca 4: **VOID — NUT TRO** (dung `PREREG_PAIRED.md` §5, khac "khong phan biet duoc").

### 1.1 Dinh chinh de bai — cap "C2b vs K1" KHONG phai nut tro

De bai goi `C2b vs K1` la cap "byte-identical" va yeu cau `d = 0`. **De bai sai.**
`C2b` md5 `8f7afdfb...` (970 lenh, equity cuoi 60390); `K1_conc25` md5 `3c9e0352...`
(1603 lenh, equity cuoi 59580); khop chinh xac 333/970. Ba run **that su** trung nhau tung byte la
`K0_h1a_prof` / `K1_conc25` / `K2_conc20`. Doi chung am da chay tren cap that su trung nhau
(NC2/NC3/NC4) cong `run vs chinh no` (NC1). `C2b vs K1_conc25` van duoc do, nhung nhu **cap that**.

### 1.2 Ba kiem chung noi tai khac — deu PASS

1. **Dong nhat phan ra khop tuyet doi** o moi cap: `common + only_A - only_B` = `sum roi_A -
   sum roi_B` den 4 chu so thap phan (in ra canh nhau trong moi bang, xem §4).
2. **Cap doi selector => thanh phan EXIT phai bang 0.** `C2b vs C2_g015`, dung sai ghep 0 phut:
   thanh phan "lenh CHUNG (roi_A - roi_B)" = **-0.0000**, CI `[-0.000000, +0.000000]`. Dung: hai
   run nay dung **cung** cau hinh exit, nen mot lenh cung `(sym, side, gio vao)` phai ra **y het**
   ket qua. Tuong tu `C2b vs RND1_2dp` va `C2b vs K1_conc25`: thanh phan EXIT = 0.
3. **Cap doi tham so exit => thanh phan EXIT phai chiem gan het.** `A6_ts96 vs A6_ts336`
   (time-stop 96h vs 336h): thanh phan EXIT = **-3.4384** tren tong **-3.4695** (99.1%),
   `only_A` = -0.0311, `only_B` = 0. Dung nhu ky vong cua mot thay doi thuan exit.
4. **Tang tham chieu equity tai lap DUNG `CI_REAUDIT.md`.** Cung seed, cung phuong phap
   `PREREG_CI.md` §2:

| Cap | `CI_REAUDIT` d / CI95 block 21 | `paired_test.py` d / CI95 block 21 | Khop? |
|---|---|---|---|
| C2b vs C2_g015 | +7.33 / [-1.72, +15.61] | **+7.326 / [-1.717, +15.609]** | **KHOP** |
| C2b vs RND1_2dp | +0.32 / [-0.08, +0.81] | **+0.320 / [-0.079, +0.809]** | **KHOP** |
| (block 10 / 42 cua cap 1) | [-2.88, +16.93] / [-2.33, +16.08] | [-2.878, +16.928] / [-2.333, +16.081] | **KHOP** |
| sd(hieu CAGR) doi selector, `PREREG_GS` §11.1 = 4.45pp | — | **4.452pp** | **KHOP** |

=> Cong cu duoc coi la dung. Cac so duoi day duoc doc.

---

## 2. BANG KET QUA — 3 cap tien dang ky (§11.2) + 2 cap BO SUNG (khong pre-reg)

`d` = hieu (A - B), do o do dai khoi **chinh 72h**. "loai tru 0" = ky hieu cho **24h/72h/168h**.
Phan quyet theo `PREREG_PAIRED.md` §5 tren dai luong **CHINH `roisum`**.

Hai cap `S1`, `S2` **KHONG** co trong pre-reg; chung duoc chay **SAU** khi thay ket qua chinh, chi
de tra loi cau hoi cong suat cho gene loai **exit** (khong co cap exit-thuan nao trong §11.2).
Chung **KHONG duoc dung** de doi phan quyet nao, dung y tinh than muc "PHAN TICH BO SUNG — KHONG
PRE-REG" cua `CI_REAUDIT.md`.

| # | Cap (A vs B) | Loai thay doi | n_lenh A/B | khoi 72h (co lenh A/B) |
|---|---|---|---|---|
| P1 | `C2b` vs `C2_g015` | selector (S1 vs G015) | 970 / 1463 | 299 (89 / 89) |
| P2 | `C2b` vs `RND1_2dp` | lam tron hang so ve 2 chu so | 970 / 961 | 299 (89 / 88) |
| P3 | `C2b` vs `K1_conc25` | cau hinh khac ho (conc25 tren nen h1a_prof) | 970 / 1603 | 301 (89 / 128) |
| S1 | `R5_arm7` vs `R6_arm8` | **exit thuan**: arm 7% vs 8% | 905 / 854 | 299 (89 / 89) |
| S2 | `A6_ts96` vs `A6_ts336` | **exit thuan**: time-stop 96h vs 336h | 1717 / 1674 | 299 (89 / 89) |

### 2.1 `roisum` = `sum(pnl/margin)` theo khoi — **DAI LUONG CHINH (pre-reg)**

| # | d | CI95 72h | CI95 24h | CI95 168h | loai tru 0 | sd_boot | t | p (2 phia) | **PHAN QUYET** |
|---|---|---|---|---|---|---|---|---|---|
| P1 | +0.002208 | [-0.037336, +0.039572] | [-0.014718, +0.016790] | [-0.090442, +0.100250] | nnn | 0.018951 | 0.12 | 0.900 | **KHONG PHAN BIET DUOC** |
| P2 | +0.001411 | **[+0.000080, +0.003040]** | [+0.000026, +0.001021] | [+0.000202, +0.006756] | **YYY** | 0.000753 | 1.87 | 0.041 | **THANG** (xem §3.2 — canh bao) |
| P3 | -0.007315 | [-0.046825, +0.040987] | [-0.014447, +0.010802] | [-0.137351, +0.129359] | nnn | 0.022730 | -0.32 | 0.758 | **KHONG PHAN BIET DUOC** |
| S1 | +0.002599 | [-0.006047, +0.012344] | [-0.002142, +0.003697] | [-0.013153, +0.027979] | nnn | 0.004752 | 0.55 | 0.579 | **KHONG PHAN BIET DUOC** |
| S2 | -0.011604 | [-0.034441, +0.011519] | [-0.012081, +0.004296] | [-0.080536, +0.020164] | nnn | 0.011997 | -0.97 | 0.323 | **KHONG PHAN BIET DUOC** |

### 2.2 `pnlsum` = `sum(pnl)/35000` theo khoi — co CA sizing, **so sanh duoc voi pp CAGR**

| # | d (/khoi) | d (%/nam) | CI95 (%/nam, 72h) | loai tru 0 | sd_boot | t | p | phan loai |
|---|---|---|---|---|---|---|---|---|
| P1 | +0.001018 | **+12.390** | **[+4.274, +20.757]** | **YYY** | 0.000347 | **2.93** | 0.003 | loai tru 0 o ca 3 |
| P2 | +0.000037 | +0.450 | [-0.025, +1.016] | nnn | 0.0000217 | 1.68 | 0.062 | chua 0 |
| P3 | +0.000077 | +0.936 | [-9.448, +12.642] | nnn | 0.000461 | 0.17 | 0.851 | chua 0 |
| S1 | +0.000044 | +0.536 | [-1.665, +2.958] | nnn | 0.0000963 | 0.46 | 0.644 | chua 0 |
| S2 | -0.000020 | -0.240 | [-5.143, +4.936] | nnn | 0.000210 | -0.10 | 0.909 | chua 0 |

### 2.3 `roimean` = ROI trung binh **tung lenh** (tach khoi so lenh va sizing)

| # | d (ROI/lenh) | CI95 72h | CI95 24h | CI95 168h | loai tru 0 | sd_boot | t | p |
|---|---|---|---|---|---|---|---|---|
| P1 | +0.009773 | [+0.002247, +0.016769] | [-0.000251, +0.019340] | [+0.000672, +0.017640] | n**YY** | 0.003683 | 2.65 | 0.007 |
| P2 | +0.000180 | [-0.000178, +0.000595] | [-0.000166, +0.000601] | [-0.000163, +0.000579] | nnn | 0.000192 | 0.94 | 0.310 |
| P3 | +0.009550 | [+0.000655, +0.018704] | [+0.001439, +0.018565] | [+0.001929, +0.018268] | **YYY** | 0.004576 | 2.09 | 0.035 |
| S1 | -0.000746 | [-0.004044, +0.002554] | [-0.003996, +0.002454] | [-0.003780, +0.002155] | nnn | 0.001710 | -0.44 | 0.654 |
| S2 | -0.002372 | [-0.006005, +0.002211] | [-0.006032, +0.002185] | [-0.006037, +0.001320] | nnn | 0.002058 | -1.15 | 0.260 |

`roimean` la uoc luong ti so nen **diem uoc luong khong doi theo do dai khoi** — chi CI doi. Dung.

### 2.4 `roisum_gross` (robustness, TRUOC phi + funding)

| # | d | loai tru 0 (24/72/168) | dau so voi `roisum` |
|---|---|---|---|
| P1 | **-0.011083** | nnn | **NGUOC DAU** (`roisum` net = +0.0022) |
| P2 | +0.001616 | **YYY** | cung dau |
| P3 | -0.023569 | nnn | cung dau |
| S1 | +0.003938 | nnn | cung dau |
| S2 | -0.010555 | nnn | cung dau |

P1 doi dau khi bo phi/funding: tinh theo **loi nhuan gia thuan** thi `C2_g015` hon; chi sau khi tru
phi + funding thi `C2b` moi hon. Do la mot canh bao thuc chat: mot phan loi the do duoc cua S1
o cap nay den tu **chi phi giao dich** (it lenh hon, giu khac nhau), khong phai tu "chon coin tot
hon" theo loi nhuan gia.

---

## 3. TANG TUNG LENH CO NHAY HON TANG EQUITY KHONG — do truc tiep, cung cap, cung seed

Cong cu tinh **ca hai tang** cho cung mot cap voi cung `SEED=20260903`. So sanh
`MDE80 = 2.80158 * sd_boot` — hieu nho nhat phat hien duoc o power 80%, alpha 0.05 hai phia —
quy ve **cung don vi: % von moi nam**.

| # | equity CAGR: d (pp) / CI95 block21 / sd | **MDE80 equity** | **MDE80 tung lenh** (`pnlsum`, 72h) | ti le | tung lenh nhay hon? |
|---|---|---|---|---|---|
| P1 selector | +7.326 / [-1.717, +15.609] / 4.452 | **12.471 pp** | **11.837 %** | 0.95 | **hon 5%** |
| P2 lam tron | +0.320 / [-0.079, +0.809] / 0.224 | **0.627 pp** | **0.755 %** | 1.20 | **KHONG — te hon 20%** |
| P3 khac ho | +0.671 / [-11.976, +12.489] / 6.188 | **17.337 pp** | **15.700 %** | 0.91 | hon 10% |
| S1 exit arm | +0.247 / [-2.238, +2.736] / 1.288 | **3.607 pp** | **3.282 %** | 0.91 | hon 10% |
| S2 exit ts | -1.118 / [-5.490, +3.511] / 2.298 | **6.437 pp** | **7.158 %** | 1.11 | **KHONG — te hon 11%** |

**Ket qua trung tam: ti le nam trong khoang 0.91 - 1.20, trung vi 0.95.**
Do la **khong co cai thien dang ke**. Tang tung lenh **khong** giai duoc bai toan cong suat.

### 3.1 Nhung cho tang tung lenh THUC SU them duoc gi

Ba thu, va can ghi ro vi chung khong nam trong bang MDE:

1. **Ti so tin/nhieu (t) o cap P1 tang that.** equity CAGR `t = 1.65`; `pnlsum` `t = 2.93`;
   `roimean` `t = 2.65`. Gap **1.6 - 1.8 lan**. Va do la du de doi ket luan: `pnlsum` cua P1
   loai tru 0 o **ca ba** do dai khoi, trong khi CAGR thi khong.
   **Nhung ly do khong phai it nhieu hon** — MDE gan y nhau (§3). Ly do la **estimand khac**:
   `pnlsum` la tong loi nhuan tren von, **khong lai kep va khong nhin thu tu thoi gian**, nen diem
   uoc luong cua no lon hon (+12.39%/nam so voi +7.33pp CAGR) cho **cung** mot thay doi. Tang tung
   lenh thang bang **cau hoi de hon**, khong bang **mau tot hon**. Phai ghi dung nhu vay.
2. **Bang phan ra** — thu tang equity khong the cho: tach hieu thanh EXIT / CHON-GATE. Vi du P1
   (§4): 100% hieu den tu **chon lenh**, 0% tu exit. Vi du S2: 99.1% den tu **exit**. Day la gia
   tri chan doan that, doc lap voi chuyen co phan biet duoc hay khong.
3. **`roimean`** tach duoc "chat luong tung lenh" khoi "so lenh". P1: `+0.98pp ROI/lenh`
   (`t = 2.65`); P3: `+0.96pp ROI/lenh` (`t = 2.09`, loai tru 0 o ca ba do dai).

### 3.2 Dai luong CHINH da chot (`roisum`) hoa ra la lua chon TE — ghi thang, khong doi luat

Bang §2.1 cho ket qua **khong tu nhat quan**:

- P1 (doi selector, thay doi that lon nhat trong bo) => `roisum` `t = 0.12`, **mu tit**.
- P2 (**lam tron hang so ve 2 chu so thap phan** — thay doi gan nhu tham my) => `roisum` loai tru
  0 o **ca ba** do dai khoi, `p = 0.041` => theo luat §5 la **THANG**.

Nguyen nhan ky thuat: `roisum` cong ROI cua moi lenh voi **trong so bang nhau** bat ke size, va
cong don theo khoi ma khong chuan hoa theo so lenh => no bi **so lenh** chi phoi. P1 lech 493 lenh
(970 vs 1463) nen phuong sai no ra rat lon (sd 0.019); P2 chi lech 21 lenh nen phuong sai gan 0
(sd 0.00075) va mot chenh lech tong be xiu cung "co y nghia".

Hai dieu bat buoc:

1. **KHONG doi phan quyet.** `PREREG_PAIRED.md` §5 da chot `roisum` la dai luong quyet dinh. Vi
   vay phan quyet chinh thuc cua P2 la **THANG**, va cua P1 la **KHONG PHAN BIET DUOC**. Ghi nhu
   vay du no nguoc truc giac — do dung la muc dich cua tien dang ky.
2. **De nghi sua cho lan sau** (phai duoc tien dang ky truoc khi co ket qua wave-1, va **khong**
   duoc sua trong file nay): dai luong quyet dinh nen la **`pnlsum`** — chuan hoa theo von, cung
   don vi voi CAGR, khong bi so lenh lam nhieu phuong sai. Trong 5 cap, `pnlsum` la dai luong duy
   nhat cho ket qua **nhat quan voi truc giac va voi tang equity** (P1 loai tru 0, P2/S1/S2 khong).
   Ghi chu: `PREREG_GS.md` dang bi dong bang; day chi la **de nghi**, khong phai sua.

### 3.3 Loi cua cong thuc quy doi nam trong pre-reg §8 — ghi de khong ai doc sai

`PREREG_PAIRED.md` §8 dua mot cong thuc quy doi `MDE_nam_% = MDE * 121.67 * 100` **cho moi dai
luong**. Cong thuc do **chi dung cho `pnlsum`**. Voi `roisum` no vo nghia: `roisum` chuan hoa theo
**gia tri danh nghia tung lenh** (~600 USDT), khong theo von (35000), va nhieu lenh chay **dong
thoi** => tong ROI danh nghia khong phai ti le loi nhuan tren von. Vi vay cot "quy doi nam" cua
`roisum` trong ban chay (`+26.9%/nam`, `CI [-454, +481]` o P1) **phai bo qua**. Moi so quy doi nam
trich trong bao cao nay deu lay tu **`pnlsum`**. Diem uoc luong va CI cua `roisum` khong bi anh
huong; chi phep doi don vi la sai.

---

## 4. BANG PHAN RA — hieu den tu dau (khoi 72h, dung sai ghep 0 phut)

Don vi: tong ROI (khong chuan hoa). `KIEM` = `common + only_A - only_B` phai bang
`sum roi_A - sum roi_B`.

| # | lenh chung | chi A | chi B | EXIT (chung) | CHON: chi A (+) | CHON: chi B (-) | TONG | KIEM |
|---|---|---|---|---|---|---|---|---|
| P1 `C2b`/`C2_g015` | 317 | 653 | 1146 | **-0.0000** | +14.7220 | -14.0617 | +0.6602 | +0.6602 |
| P2 `C2b`/`RND1_2dp` | 955 | 15 | 6 | **-0.0000** | +0.5577 | -0.1358 | +0.4219 | +0.4219 |
| P3 `C2b`/`K1_conc25` | 333 | 637 | 1270 | **-0.0000** | +13.3872 | -15.5889 | -2.2017 | -2.2017 |
| S1 `R5_arm7`/`R6_arm8` | 845 | 60 | 9 | -0.2491 | +1.5369 | -0.5108 | +0.7770 | +0.7770 |
| S2 `A6_ts96`/`A6_ts336` | 1674 | 43 | 0 | **-3.4384** | -0.0311 | 0.0000 | -3.4695 | -3.4695 |

Doc bang:

- **P1, P2, P3: EXIT = 0 tuyet doi.** Toan bo hieu den tu **chon lenh nao** (`only_A` / `only_B`).
  Hop ly: ba cap nay khong doi tham so exit, va mot lenh cung `(sym, side, phut vao)` luon ra y
  het ket qua. Day la kiem chung noi tai manh nhat cua cong cu.
- **P1 la phep so CHON LENH dung nghia:** lenh chi `C2b` co dong `+14.72`, lenh chi `C2_g015` co
  dong `+14.06` (dau `-` trong bang la vi tru), rong chi `+0.66` tren 2.45 nam. CI/khoi cua
  `only_A` la `[+0.019, +0.081]` (loai tru 0) con `only_B` la `[-0.106, +0.011]` (chua 0) => **hai
  ben deu chon duoc lenh sinh loi**, hieu giua hai ben moi la thu khong do noi.
- **S2 la cap exit-thuan:** 99.1% hieu nam o thanh phan **EXIT**, `only_B` = 0 (`A6_ts336` khong co
  lenh nao ma `A6_ts96` khong co). Dung nhu ky vong.
- **Dung sai ghep 15 phut lam bang phan ra SAI o cap khac ho** (P3): no ghep 718 "lenh chung" va
  tao ra mot thanh phan EXIT `+4.66` gia tao — do la ghep **hai lenh khac nhau**. Voi cap doi
  selector, dung sai 0 phut la ban dang doc duoc; muc 15 phut chi nen doc o cap chi khac exit.
  (Ca hai muc deu duoc bao vi ca hai da tien dang ky o §3.3 cua pre-reg.)

---

## 5. CONG SUAT — hieu nho nhat phat hien duoc o tang nay

Cong thuc chot truoc (`PREREG_PAIRED.md` §8). `sd_boot` do o khoi 72h, dai luong `pnlsum`,
don vi **% von moi nam** (khong lai kep).

| # | loai thay doi | sd_boot (%/nam) | **MDE80** | MDE50 | **nguong GS N=256** (2.35 sd) |
|---|---|---|---|---|---|
| P2 | lam tron hang so | 0.270 | **0.755 %** | 0.528 % | **0.633 %** |
| S1 | exit: arm 7% -> 8% | 1.171 | **3.282 %** | 2.296 % | **2.752 %** |
| S2 | exit: time-stop 96h -> 336h | 2.555 | **7.158 %** | 5.008 % | **6.005 %** |
| P1 | doi selector | 4.225 | **11.837 %** | 8.281 % | **9.929 %** |
| P3 | khac ho cau hinh | 5.604 | **15.700 %** | 10.985 % | **13.174 %** |

Doi chieu tang equity (cung cap, cung seed, `MDE80` pp CAGR): 0.627 / 3.607 / 6.437 / 12.471 /
17.337. **Cung bac do lon.**

**`sd` khong phai hang so cua tang do — no phu thuoc HAI RUN KHAC NHAU BAO NHIEU.** Hai run gan
nhau (P2) thi phep tru ghep cap triet tieu gan het nhieu => `sd` be; hai run khac selector (P1)
thi `sd` lon gap 16 lan. Vi vay khong co mot con so "MDE cua tang tung lenh"; co mot **dai**:

- **Doi mot tham so exit** (loai gene pho bien nhat cua GS): **MDE80 ~ 3.3 - 7.2 %/nam**;
  nguong GS co hieu chinh so sanh boi **~2.8 - 6.0 %/nam**.
- **Doi selector / doi ho cau hinh**: **MDE80 ~ 11.8 - 15.7 %/nam**; nguong GS **~9.9 - 13.2 %/nam**.

So khoi can them de dat `delta = 3pp/nam` o power 80% (`n_can = n_blocks * (MDE80/3)^2`):

| # | MDE80 | so khoi can | quy doi nam DEV can |
|---|---|---|---|
| S1 (exit arm) | 3.282 | 299 * 1.20 = **358** | **2.9 nam** |
| S2 (exit ts) | 7.158 | 299 * 5.69 = **1702** | **14.0 nam** |
| P1 (selector) | 11.837 | 299 * 15.57 = **4655** | **38.3 nam** |
| P3 (khac ho) | 15.700 | 301 * 27.39 = **8244** | **67.8 nam** |

So sanh voi `PREREG_GS.md` §11.1 o tang equity (14.3 nam cho exit, 43.1 nam cho selector):
**gan y nguyen**. Ket luan co dieu kien da chot o `PREREG_PAIRED.md` §8 ("neu `MDE_nam_%` > ~1.5pp
thi phai ghi thang la tang nay cung khong du") **duoc kich hoat**: 4/5 cap co `MDE80` tu 3.3 den
15.7 %/nam, gap 1.1 den 5.2 lan nguong 3pp.

---

## 6. KET LUAN THANG

### 6.1 Tang tung lenh co du de lam tieu chi quyet dinh cho GS wave-1 khong?

**KHONG DU. Khong phai gan du.** Ba ly do, moi ly do da du:

1. **Cong suat khong tang.** `MDE80` o tang tung lenh la 0.91x - 1.20x tang equity, trung vi
   0.95x (§3, 5 cap doc lap, cung seed). Ky vong "tang tung lenh cho n hieu dung lon hon nhieu"
   **sai o du lieu nay**: `printDone.csv` chi co 854-1717 lenh tren 2.45 nam, va chung roi vao
   **89-128 khoi 72h co lenh** — chi 2-3 lan so 44 khoi cua tang equity, khong phai 100 lan.
   Bootstrap tung lenh doc lap se cho CI hep hon nhung do la **n gia**, dung loi ma
   `LEAK_L1_REPORT.md` da chi ra; pre-reg §6 da cam.
2. **Voi gene loai exit — loai chiem phan lon GS — con te hon.** `A6_ts96 vs A6_ts336` la mot
   thay doi time-stop **rat lon** (96h vs 336h, 3.5 lan) va van **khong phan biet duoc** o ca 4
   dai luong, `MDE80 = 7.16 %/nam`. `R5_arm7 vs R6_arm8` (mot buoc arm) `MDE80 = 3.28 %/nam`,
   nguong GS 2.75 %/nam. Nghia la: **khong** phat hien duoc thay doi tham so exit co tac dong
   3pp/nam, tru khi thay doi do la mot buoc rat nho tren mot tham so rat nhay.
3. **Dai luong da tien dang ky lam sai ca hai chieu.** `roisum` **mu** truoc thay doi selector
   (P1, `t = 0.12`) va **bao thang** cho mot thay doi **lam tron hang so** (P2, `p = 0.041`).
   Voi N=256 phuong an, mot tieu chi co the "thang" vi lam tron so se sinh ra ket qua duong tinh
   gia hang loat. Chi co nguong `sqrt(2 ln 256) = 2.35 sd` chan duoc P2 (`|d| = 0.001411` <
   nguong `0.001769`) — nghia la **hieu chinh so sanh boi la thu dang giu duy nhat**, khong phai
   ban than tang do.

### 6.2 Vay `PREREG_GS.md` §11.2 co con thuc hien duoc khong?

`§11.2` bat buoc finalist phai "thang o tang tung lenh/tung tick theo thong ke ghep cap, CI cua
hieu khong chua 0". Sau khi dung cong cu:

- **Voi gene loai selector / gate**: dieu kien **thuc hien duoc va co gia tri** — nhung tang co
  suc phan biet la **tang TICK** cua pool ledger (`CI_REAUDIT` #7 rank-IC `+0.0973`
  CI `[+0.0711, +0.1152]`, #8 gate `+0.0182` CI `[+0.0085, +0.0227]`), **khong phai** tang tung
  lenh. Tang tung lenh cho P1 `t` chi 2.65-2.93.
- **Voi gene loai exit / sizing / concurrency / breaker**: **khong thuc hien duoc**.
  Tang tick **khong ton tai** cho nhung gene nay (§2 cua pre-reg: khong co log quyet dinh tung
  tick cho tung run trong `sim.out`, va pool ledger khong phu thuoc cau hinh nen cho rank-IC y
  het). Tang tung lenh thi khong du cong suat (§6.1). => Voi nhung gene nay, `§11.2` **hoac** se
  loai het finalist (neu ap dung dung), **hoac** se duoc thoa man boi nhieu (neu ap dung long).
  Ca hai deu khong phai mot tieu chi quyet dinh.

### 6.3 De nghi (khong phai quyet dinh — quyet dinh la cua chu du an)

1. **Doc `§11.2` theo huong SIET, khong theo huong "co tieu chi moi".** Voi wave-1, ket qua kha
   di nhat la ket luan `(b)/(c)` da chot o `PREREG_GS.md` §11.2: **"khong the phan biet bang du
   lieu DEV hien co"**. Cong cu nay khong doi duoc dieu do; no **xac nhan** dieu do o mot tang
   thap hon, doc lap.
2. **Neu muon co mot tang thuc su nhay hon, phai them DU LIEU DAU RA, khong phai them phep tinh.**
   Cu the: cho simulator ghi **log quyet dinh tung tick cho tung run** (tick, tap ung vien, diem,
   chon/khong chon, ly do chan). Do la thu duy nhat lam cho gene exit/sizing co mot tang ghep cap
   1-1 that. Viec do can chay lai java => ngoai pham vi job nay, va phai tien dang ky rieng.
3. **Neu van dung tang tung lenh**: dung `pnlsum` lam dai luong quyet dinh (§3.2), giu nguyen
   nguong `2.35 sd`, va **giu nguyen** rang buoc `maxDD` o tang equity nhu mot rang buoc **doc
   lap** — `PREREG_PAIRED.md` §9.2: `maxDD` la tinh chat cua duong equity, tang tung lenh khong
   noi gi ve no (P1: `C2b` maxDD -13.12% vs `C2_g015` -20.82%, chenh lech **khong** xuat hien
   trong bat ky dai luong nao cua bang §2).

### 6.4 Cai bao cao nay KHONG noi

- Khong noi `C2b` tot hon hay te hon `C2_g015` / `RND1_2dp` / `K1_conc25`. Voi dai luong da tien
  dang ky, 2/3 cap la "khong phan biet duoc" va cap "thang" la cap lam tron hang so.
- Khong mo lai nhanh nao, khong doi diem uoc luong nao trong `AUDIT_APPLIED.md` /
  `CI_REAUDIT.md`.
- Khong noi gi ve VALIDATION hay HOLDOUT. Moi so la in-sample DEV.
