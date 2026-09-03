# PREREG_PAIRED — tien dang ky phep do GHEP CAP o tang TUNG LENH

Chot luc: 2026-09-03, **TRUOC khi tinh bat ky hieu / CI nao o tang nay**. Commit cua file nay
phai co TRUOC commit cua ket qua (`docs/PAIRED_CALIB.md` + `research/analysis/paired_test.py`
chay ra so). Neu thu tu nguoc lai => toan bo ket qua tang nay bi coi la VOID.

Ly do ton tai:

- `docs/CI_REAUDIT.md` (commit `a396797`): 14/18 verdict cu la **khong phan biet duoc**. Ca 3 tru
  cot cua "S1 +7.35pp CAGR" chet (`d = +7.33pp`, CI95 `[-1.72, +15.61]`).
- `docs/PREREG_GS.md` §11.1: sd cua HIEU CAGR tren DEV la 2.57pp (doi tham so exit) den 6.34pp
  (noi gate) => can **14.3 den 87.4 nam** du lieu de thay 3pp o power 80%. Tang equity/CAGR
  **vo dung lam tieu chi quyet dinh**.
- `docs/PREREG_GS.md` §11.2 da bat buoc: finalist chi duoc tuyen bo thang neu **thang o tang tung
  lenh / tung tick theo thong ke ghep cap, CI cua hieu khong chua 0**. Cong cu do CHUA TON TAI.
  File nay chot phuong phap cho cong cu do.

Pham vi: **CHI DEV**. Khong cham VALIDATION (2024-07-15..2025-12-31), khong cham HOLDOUT 2026.
Khong chay java, khong backtest, khong train. Chi doc `printDone.csv` + `sim.out` co san.
Khong sua `docs/PREREG_GS.md`, `docs/PREREG_CI.md`, `research/kaggle/gsearch/*`.
Khong cham `/home/ubuntu/gs/`, `/home/ubuntu/oiprobe/`, `/home/ubuntu/leakprobe/`, `/home/ubuntu/ci/`.

---

## 0. KIEM TON TAI DU LIEU — da lam TRUOC khi chot file nay

Day chi la **kiem cau truc / dem**, khong phai tinh estimand (dung y tinh than `PREREG_CI.md` §1).
Khong mot con so ve HIEU nao duoc tinh truoc commit cua file nay.

| Kiem | Ket qua |
|---|---|
| `printDone.csv` co ton tai cho moi run DEV | CO, tai `/home/ubuntu/java/devrun/<TAG>/storage/printDone.csv` |
| Cot co san | `sym,side,entry,tp,profit,status,start,time_start_format,end,level,maxmin15m,lastentry,volume,quantity,margin,pnl,time_order,funding,dow,up,dow15m,pred15m,risk4h,symbolPred` |
| Phu het DEV? | CO. `start` tu `2022-01-06 03:07` den `2024-06-18 08:41` (C2b) |
| So lenh | C2b 970, C2_g015 1463, RND1_2dp 961, K0/K1/K2 1603 (sau loc `level==PREDICT_SYMBOL_TRADE` va `margin>0`) |
| `level` khac? | KHONG — 100% la `PREDICT_SYMBOL_TRADE` |
| `status` | `STOP_MARKET_DONE` 823 / `STOP_LOSS_DONE` 147 (C2b) |
| md5 `printDone.csv` | `K0_h1a_prof` == `K1_conc25` == `K2_conc20` (GIONG NHAU TUNG BYTE); `BR1_margin` == `BR2_both` |
| md5 C2b vs K1_conc25 | **KHAC NHAU** — xem §11 |
| Co log quyet dinh TUNG TICK cho tung run? | **KHONG** — xem §2 |

---

## 1. DON VI QUAN SAT — CHOT: **LENH DA DONG**, gop len **KHOI THOI GIAN**

Chot: don vi quan sat co ban la **mot lenh da dong** doc tu `printDone.csv`, gan vao **khoi thoi
gian** theo **thoi diem VAO lenh**; don vi thong ke (va don vi bootstrap) la **khoi**, khong phai
lenh.

Vi sao gan theo thoi diem VAO chu khong phai thoi diem RA: thoi diem ra la **noi sinh** voi chinh
tham so dang bi kiem (doi `SIM_LOSER_TIME_STOP_HOURS`, doi trailing => doi gio ra). Neu chia khoi
theo gio ra thi ban than **cach chia khoi** phu thuoc cau hinh => khong con ghep cap duoc. Thoi
diem vao lenh la thoi diem QUYET DINH, va voi hai cau hinh chi khac exit thi phan lon thoi diem
vao la **giong nhau**, nen chia theo gio vao giu duoc tinh chat "cung khoi la cung doan thi truong".

---

## 2. VI SAO KHONG DO O TANG TUNG TICK — chot va giai thich

De bai de nghi can nhac ky huong TICK vi "tick la chung cho ca hai, ghep 1-1 that". Da kiem. Ket
luan: **khong lam duoc voi du lieu hien co**, va ly do la ky thuat, khong phai lua chon tham my.

1. **Khong co log tick cho tung run.** `/home/ubuntu/java/devrun/<TAG>/logs/sim.out` chi co
   **911 dong `Update ...`** (moi ngay mot dong: `b:` + `unP:`) cong voi log khoi dong.
   `full.log` la ban cung noi dung, khac dinh dang ngay. **Khong co** dong nao ghi diem so cua
   tung ung vien tai tung tick, khong co dong nao ghi "tick nay xet N coin, chon coin X, bo coin Y".
   => Muon co chuoi tick cho MOT cau hinh cu the thi phai **chay lai java** — bi cam.
2. **Pool tick `/home/ubuntu/ledger/*.parquet` KHONG phu thuoc cau hinh.** Do la pool du doan cua
   model (`cand_dev`, `pred_s1a2`, `path_labels`). Do la thu ma `CI_REAUDIT` #7/#8 do duoc, va no
   tra loi dung MOT loai cau hoi: **selector nao xep hang tot hon** (rank-IC), **gate co chon dung
   tick hon random khong**. No **khong** phan biet duoc hai cau hinh khac nhau o **exit / sizing /
   concurrency / breaker**, vi nhung tham so do **khong doi diem so ung vien**, chi doi ket qua
   sau khi da vao lenh. Hai cau hinh khac nhau o exit se cho **y het** mot rank-IC.
3. **He qua bat buoc phai ghi:** tang tick chi bao phu duoc gene loai **selector / gate / xep
   hang**. Voi moi gene loai **exit, sizing, time-stop, trailing, giveback, concurrency, breaker**,
   tang tung lenh la **tang duy nhat** con lai duoi tang equity. Neu tang tung lenh cung khong
   phan biet duoc thi nhung gene do **khong co tang nao** kiem duoc bang du lieu DEV hien co —
   va do la ket luan phai bao, khong duoc lap lieu bang mot tieu chi khac.

---

## 3. VAN DE GHEP CAP — hai cau hinh sinh TAP LENH KHAC NHAU

Da do (chi dem, khong tinh estimand), khop chinh xac theo `(sym, start)`:

| Cap | khop chinh xac | chi A | chi B |
|---|---|---|---|
| C2b vs C2_g015 | 317 | 653 | 1146 |
| C2b vs RND1_2dp | 955 | 15 | 6 |
| K1_conc25 vs K0_h1a_prof | 1603 | 0 | 0 |
| C2b vs K1_conc25 | 333 | 637 | 1270 |

=> Voi cap doi selector (C2b vs C2_g015) chi **33%** lenh cua A co ban sao o B. **Khong the** coi
day la phep do "ghep 1-1 tung lenh". Ghep 1-1 tung lenh la **sai** o day.

### 3.1 Cach ghep DUOC CHOT: ghep o tang KHOI, khong ghep o tang lenh

Don vi ghep cap la **khoi thoi gian** — khoi la chung cho ca hai run theo dinh nghia (cung lich,
cung doan thi truong). Voi moi khoi `b` va moi run `X`, dinh nghia mot thong ke khoi `S_b(X)` tinh
tu **tat ca** lenh cua `X` vao trong khoi `b` (co the la 0 lenh). Hieu la

```
d = mean_b[ S_b(A) ] - mean_b[ S_b(B) ]
```

va bootstrap resample **danh sach khoi**, dung **MOT** danh sach chi so cho ca hai run (§6).

Cach nay xu ly triet van de tap lenh khac nhau: khong can lenh nao khop lenh nao. "A vao 3 lenh o
khoi nay, B vao 1 lenh" la **du lieu**, khong phai tro ngai.

### 3.2 Khoi RONG (khong co lenh) — CHOT: GIU, tinh `S_b = 0`

Ly do: "khong vao lenh nao trong 72h nay" la mot ket qua **that va co thong tin**. Bo khoi rong se
**thien vi** cau hinh vao lenh it (chi con nhung khoi no chon vao, tu dong lam sach mau).
Da do: tren span 901.8 ngay = **301 khoi 72h**, so khoi CO lenh la C2b 89, C2_g015 89,
RND1_2dp 88, K0/K1/K2 128. Mau khoi = 301; thong tin thuc te ~89-128 khoi. **Day la con so quan
trong**: tang tung lenh KHONG cho hang nghin quan sat doc lap, no cho **~89-128** khoi — chi khoang
**2-3 lan** tang equity (44 khoi), khong phai 100 lan.

### 3.3 Ghep 1-1 tung lenh — chi dung cho BANG PHAN RA, khong dung cho phan quyet

Bang phan ra (§7) can biet lenh nao la "chung". Khoa ghep: `(sym, side, ts_in)` chinh xac; sau do
ghep tham lam theo `sym+side` voi **dung sai +-15 phut** (do luoi mau la 15m). Bao ca hai muc
`tol=0` va `tol=15m`. **Khong** chon dung sai sau khi xem ket qua. Bang phan ra la **mo ta**;
phan quyet chi theo §5.

---

## 4. DAI LUONG SO — chot 3 dai luong, moi cai tra loi mot cau hoi khac

Doc cot y het `research/analysis/sim_truth.py:16-21`: loc `level == "PREDICT_SYMBOL_TRADE"`,
`margin > 0`, `roi = pnl / margin`. Da xac minh `margin == quantity * entry` (gia tri danh nghia),
`profit == (tp/entry - 1) * 100 * dau(side)` (loi nhuan GIA, chua tru phi), `pnl` la USDT **rong**
(da tru phi + funding).

| Ten | Dinh nghia `S_b(X)` | Tra loi cau hoi | Bi nhieu boi sizing? |
|---|---|---|---|
| **CHINH: `roisum`** | `sum( pnl/margin )` tren cac lenh vao trong khoi `b` | "moi 72h, cau hinh nay tao ra bao nhieu loi nhuan tren mot don vi von da trien khai" | **KHONG** (chuan hoa theo von danh nghia tung lenh) |
| **PHU 1: `roimean`** | uoc luong ti so: `sum(pnl/margin) / count` gop tren cac khoi duoc resample | "chat luong TUNG LENH, tach khoi so lenh" | KHONG |
| **PHU 2: `pnlsum`** | `sum(pnl) / 35000` | "ke ca sizing thi sao" | **CO** — co y, de do ca sizing |

Robustness (bat buoc bao, khong duoc dung de doi phan quyet): `roisum_gross` dung
`profit/100` thay `pnl/margin` — bo phi/funding, de biet ket luan co phu thuoc mo hinh phi khong.

`roisum` la dai luong CHINH vi: (a) khong bi nhieu boi sizing / leverage, (b) cong tinh nen khoi
rong = 0 co nghia, (c) `mean_b(roisum) * 121.67` la "ROI cong don khong lai kep mot nam tren von
trien khai" — doc duoc, so sanh duoc voi pp CAGR o cung bac do lon (121.67 = 365*24/72 khoi/nam).

**`roimean` KHONG duoc dung mot minh de tuyen bo thang.** Mot cau hinh vao it lenh hon nhung moi
lenh tot hon co the co `roimean` cao hon ma tong loi nhuan thap hon. `roisum` la dai luong quyet
dinh; `roimean` chi de **giai thich** hieu den tu chat luong hay tu so luong.

---

## 5. DIEU KIEN "THANG" — chot cung, khong doi sau

Cho moi cap (A, B) va dai luong CHINH `roisum`:

| Phan loai | Dieu kien |
|---|---|
| **THANG** | CI95 percentile cua `d` **khong chua 0** o **CA BA** do dai khoi (24h, 72h, 168h), **VA** dau cua `d` giong nhau o ca ba |
| **KHONG PHAN BIET DUOC** | CI95 chua 0 o do dai chinh (72h), **hoac** khong chua 0 o 72h nhung chua 0 o mot trong hai do dai kiem tra |
| **VOID — nut tro** | `printDone.csv` cua hai run **giong nhau tung byte** => `d = 0` theo **dinh nghia**. KHONG bootstrap. VOID **khac** "khong phan biet duoc" |

Do dai khoi: **chinh = 72h** (khop `PREREG_CI.md` §3.1), kiem do ben o **24h** va **168h**.

Ghi thang mot diem yeu da biet, chot truoc: mot lenh song toi da `SIM_LOSER_TIME_STOP_HOURS=168`
(7 ngay) voi lenh lo, dai hon voi lenh lai chay trailing. Vi vay ket qua cua mot lenh vao o khoi
`b` co the tran sang khoi `b+1`, `b+2` => khoi 72h **khong hoan toan doc lap**. Lap luan vong doi
lenh thuc ra **uu tien 168h** lam do dai chinh. Ta van chot 72h lam chinh de khop `PREREG_CI.md`,
va bu lai bang cach **bat buoc CI phai loai 0 o CA BA do dai** — nen khong the lay do dai khoi de
lai ket qua theo huong mong muon.

### 5.1 Hieu chinh SO SANH BOI — bat buoc khi dung cho GS

Khi cong cu duoc dung de xet **N** phuong an (GS wave-1: N=256), dieu kien THANG o tren la
**chua du**. Them, khop `PREREG_GS.md` §11.2:

```
|d| > sqrt(2 * ln N) * sd_boot(d)        # N=256 => he so 2.35
```

`sd_boot(d)` = do lech chuan bootstrap cua `d` o khoi 72h. Bao cao **song song** ket qua kiem soat
FDR Benjamini-Hochberg `q = 0.10` tren p-value bootstrap 2 phia
`p = 2 * min( P(d_boot <= 0), P(d_boot >= 0) )`, de thay hai cach hieu chinh co cung ket luan hay
khong. Neu hai cach khac nhau => bao ca hai, **khong chon cai de hon**.

Voi cac cap HIEU CHUAN trong `docs/PAIRED_CALIB.md` thi `N = 1` (cap da chot truoc trong file
nay, §11), he so `sqrt(2 ln 1) = 0` => chi ap dieu kien CI. Do la ly do phai liet ke cap hieu
chuan **trong file pre-reg nay**, khong duoc them cap sau khi thay ket qua.

---

## 6. BOOTSTRAP — don vi, so lan, seed

- Don vi resample: **KHOI**, khong phai lenh. Resample `n_blocks` khoi **co hoan lai, i.i.d.** tu
  danh sach `0..n_blocks-1` (giong `PREREG_CI.md` §3.2/3.3 cho nhom B).
- **Vi sao khong bootstrap tung lenh doc lap:** cac lenh vao trong cung mot cua so gio chia nhau
  **cung mot cu dong thi truong** — cung mot con bear day tat ca altcoin xuong cung luc. Bootstrap
  tung lenh coi 970 lenh nhu 970 quan sat doc lap => CI hep gia, dung y loi ma
  `docs/LEAK_L1_REPORT.md` da chi ra (n gia). Them nua, sizing lam cac lenh mo dong thoi phu thuoc
  nhau qua von kha dung. Khoi thoi gian la don vi doc lap gan dung duy nhat co san.
- **GHEP CAP bat buoc:** moi rep sinh **MOT** danh sach chi so khoi; danh sach do dung **Y NGUYEN**
  cho ca A va B; tinh `S(A)`, `S(B)` tren cung danh sach; lay `d`. **CAM** so hai CI rieng roi xem
  co chong nhau — hai run o day chay tren cung thi truong, tuong quan rat cao; bootstrap doc lap
  se pha tuong quan do va lam CI cua hieu **rong gia** => bao thu qua muc.
- `N_REP = 2000`, `SEED = 20260903`, `numpy.random.default_rng(SEED)`, reseed lai cho **tung**
  (cap, do dai khoi, dai luong) de ket qua khong phu thuoc thu tu chay.
- CI95 = **phan vi 2.5% / 97.5%** cua phan bo bootstrap cua `d` (percentile, khong BCa).
- Bao them: `sd(d)`, `P(d > 0)`, `n_blocks`, `n_blocks_occupied` cho ca hai run.
- Voi `roimean` (uoc luong ti so): neu mot rep co `count == 0` o **bat ky** ben nao thi **bo rep
  do** va **dem** so rep bi bo; neu bo qua 1% thi ghi canh bao.

---

## 7. BANG PHAN RA — hieu den tu dau

Dong nhat **chinh xac** (khong phai xap xi), tren dai luong `roisum` chua chuan hoa:

```
sum_A(roi) - sum_B(roi)
  = SUM_{cap chung} ( roi_A - roi_B )      # cung lenh, ket qua khac  -> tac dong cua EXIT
  + SUM_{chi co o A} roi_A                 # A vao ma B khong vao     -> tac dong cua CHON/GATE
  - SUM_{chi co o B} roi_B                 # B vao ma A khong vao     -> tac dong cua CHON/GATE
```

Bao 3 thanh phan nay: gia tri diem, so lenh moi nhom, **va** CI95 bootstrap cua tung thanh phan
tinh tren **cung danh sach chi so khoi** (nen 3 CI cong lai nhat quan voi CI cua tong). Bang nay
la **mo ta / chan doan**, khong tao ra phan quyet moi.

---

## 8. CONG SUAT (power) — cong thuc chot TRUOC, so dien sau

Voi kiem dinh 2 phia `alpha = 0.05`, power `1-beta`, hieu nho nhat phat hien duoc:

```
MDE(80%) = (z_0.975 + z_0.80)  * sd_boot(d) = 2.80158 * sd_boot(d)
MDE(50%) =  z_0.975            * sd_boot(d) = 1.95996 * sd_boot(d)
MDE_GS   = sqrt(2 ln 256)      * sd_boot(d) = 2.35    * sd_boot(d)   # nguong tuyen bo, N=256
```

`sd_boot(d)` do o khoi 72h. Doi don vi de so voi tang equity (bao thu, khong lai kep):

```
MDE_nam_% = MDE * 121.67 * 100      # 121.67 = 365*24/72 khoi 72h moi nam
```

So khoi can co de dat mot muc `delta` mong muon (sd ti le `1/sqrt(n_blocks)`):

```
n_can = n_blocks * ( MDE(80%) / delta )^2 ;   nam_can = n_can * 72 / (365*24)
```

**Chot truoc mot ket luan co dieu kien** (de khong the "giai thich lai" sau khi thay so): tang
tung lenh chi co ~89-128 khoi co du lieu so voi 44 khoi o tang equity (§3.2). Ti le sd ky vong
chi khoang `sqrt(44/89) = 0.70` den `sqrt(44/128) = 0.59`. **Neu** `MDE_nam_%` o tang tung lenh
lon hon ~1.5pp thi ket luan bat buoc phai ghi la: **tang tung lenh cung KHONG du de lam tieu chi
quyet dinh cho GS wave-1**, va do la thong tin phai bao, khong duoc thay bang mot tieu chi de hon.
So do se duoc dien vao `docs/PAIRED_CALIB.md`.

---

## 9. CAM BAY — ghi truoc, bat buoc trich lai trong bao cao ket qua

1. **So sanh boi.** Do N phuong an thi ky vong cua `max|d|` thuan nhieu la `sd * sqrt(2 ln N)`.
   Bat buoc dung §5.1. Khong duoc bao "CI khong chua 0" cho phuong an tot nhat trong 256 ma coi
   nhu bang chung.
2. **Tang tung lenh KHONG thay the rang buoc maxDD.** `maxDD` la tinh chat cua **duong** equity
   (thu tu thoi gian), khong phai trung binh cua lenh. Trung binh lenh bang nhau van co the cho
   maxDD -13% hay -51% tuy lenh tap trung the nao. `PREREG_CI.md` §2.5 da cam bootstrap maxDD.
   => Rang buoc maxDD van la **quan sat mot lan**, van la **rang buoc cung rieng**, phai kiem
   truoc/song song, khong duoc suy ra tu phep do nay.
3. **Thang o tang lenh la DIEU KIEN CAN, khong phai DIEU KIEN DU.** Mot cau hinh co the thang o
   `roisum` ma thua o equity (vao nhieu lenh tuong quan cung luc => DD sau => lai kep te hon).
   Phan quyet cuoi cung van phai qua rang buoc equity/maxDD cua `PREREG_GS.md`.
4. **Kiem duyet (censoring).** `printDone.csv` chi co lenh **DA DONG**. Lenh con mo cuoi DEV bi
   thieu, va hai cau hinh khac tham so exit co muc kiem duyet khac nhau. Bat buoc bao `unP` cuoi
   ky cua ca hai run tu `sim.out`; neu `|unP|` lon so voi `|d| * 35000` thi ghi canh bao.
5. **Khong duoc chon** do dai khoi, dung sai ghep, hay dai luong sau khi xem ket qua. Ba do dai
   khoi va ba dai luong deu bao **het**, moi lan.
6. **`roisum` khong phai CAGR.** Khong duoc phat bieu "tuong duong +X pp CAGR" ma khong ghi ro do
   la phep doi don vi khong lai kep o §8, va rang phep doi do bo qua thu tu thoi gian.
7. **DEV la DEV.** Moi so o day la in-sample DEV. Khong duoc dung de tuyen bo bat ky dieu gi ve
   VALIDATION hay HOLDOUT.

---

## 10. CONG CU — `research/analysis/paired_test.py`

Yeu cau chot: Python 3, dung module `logging`, **CAM `print`**. Doc `printDone.csv` va `sim.out`
bang **dung** logic da co (`sim_truth.py` cho printDone, regex cua `qret.py:7` cho sim.out), khong
viet lai khac. Dau vao: 2 tag run duoi `/home/ubuntu/java/devrun/`. Dau ra: `n_blocks`,
`n_blocks_occupied`, `d`, `CI95`, `sd_boot`, `P(d>0)`, `MDE`, phan quyet theo §5, o **3 do dai
khoi** x **3 dai luong**, cong bang phan ra §7.

---

## 11. DOI CHUNG AM va CAC CAP HIEU CHUAN — chot danh sach TRUOC

### 11.1 Doi chung am (bat buoc PASS truoc khi tin bat ky so nao khac)

| # | Cap | Yeu cau |
|---|---|---|
| NC1 | `C2b` vs `C2b` (chinh no) | `d` **dung 0**, CI95 = `[0, 0]`, sd = 0, o ca 3 do dai va ca 3 dai luong |
| NC2 | `K1_conc25` vs `K0_h1a_prof` | md5 `printDone.csv` giong nhau => `d` **dung 0**, CI `[0,0]` |
| NC3 | `K1_conc25` vs `K2_conc20` | y nhu NC2 |
| NC4 | `BR2_both` vs `BR1_margin` | y nhu NC2 |

Neu bat ky NC nao ra khac 0 => **cong cu SAI**, DUNG moi ket luan khac, sua cong cu truoc.

**Dinh chinh de bai — ghi de kiem duoc:** de bai goi "C2b vs K1" la cap "byte-identical".
**KHONG dung.** Da kiem md5: cap giong nhau tung byte la `K1_conc25` / `K2_conc20` /
`K0_h1a_prof` (cung `3c9e0352...`); `C2b` la `8f7afdfb...`, khac. `C2b` co 970 lenh, `K1_conc25`
co 1603 lenh, khop chinh xac 333. Vi vay doi chung am duoc chay tren cap **that su** giong nhau
(NC2/NC3/NC4) cong voi cap **run vs chinh no** (NC1). Cap `C2b vs K1_conc25` van duoc chay nhung
duoc phan loai la **cap that**, khong phai nut tro.

### 11.2 Cap hieu chuan — `N = 1` moi cap, chot truoc

| # | Cap | Ket luan tang equity da co (`CI_REAUDIT`) | Cau hoi |
|---|---|---|---|
| P1 | `C2b` vs `C2_g015` (doi selector) | `d = +7.33pp` CI `[-1.72, +15.61]` — KHONG PHAN BIET DUOC | tang tung lenh co phan biet duoc? |
| P2 | `C2b` vs `RND1_2dp` (lam tron hang so) | `d = +0.32pp` CI `[-0.08, +0.81]` — KHONG PHAN BIET DUOC | y nhu tren |
| P3 | `C2b` vs `K1_conc25` | (khong co trong `CI_REAUDIT`; `K1` la nut tro so voi `K0`) | do them, cap that |

---

## 12. THU TU THUC HIEN — bat buoc, se bi kiem bang timestamp commit

1. Commit **file nay**. Ghi lai commit hash.
2. Chi sau do moi viet/chay `research/analysis/paired_test.py`.
3. Chay **doi chung am truoc** (§11.1). Neu FAIL => sua cong cu, khong bao ket qua nao khac.
4. Chay 3 cap hieu chuan (§11.2), bao **het** 3 do dai khoi x 3 dai luong, khong loc.
5. Viet ket qua vao `docs/PAIRED_CALIB.md` theo dung phan loai §5, kem so power §8 va
   ket luan co dieu kien da chot o §8.

## 13. FILE NAY KHONG LAM GI

- Khong sua diem uoc luong nao da co. Khong mo lai nhanh nao.
- Khong tuyen bo cau hinh nao thang. Khong doi `PREREG_GS.md`.
- Khong tra loi cau hoi ve VALIDATION / HOLDOUT.
