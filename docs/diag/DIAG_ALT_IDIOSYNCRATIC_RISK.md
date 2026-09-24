# DIAG_ALT_IDIOSYNCRATIC_RISK — do luong rui ro alt sap rieng le (idiosyncratic)

> **Gioi han cua tai lieu nay** (doc truoc khi dung): day la phan tich **MO TA (descriptive)**,
> chi doc du lieu da co, **KHONG pre-reg, KHONG sua `.java`, KHONG them flag, KHONG chay sim moi,
> KHONG push**. Moi so o day mo ta **co che da xay ra tren DEV** (profile `x1_gs_t170.properties`),
> khong phai bang chung de tune. Bat ky y tuong sua nao sinh ra tu day van phai **pre-reg rieng**
> va xac nhan tren holdout 2026.

Noi tiep `docs/diag/DIAG_ENTRYGATE_PRED15M_REGIME.md` (commit `c9f2433`): cua so UW dai nhat cua T170
(2024-04-10 -> 2024-07-10, 92 ngay) **khong phai do gate** ma do danh muc long-ALT khong co beta BTC,
bi mot so alt sup rieng le (CKB -41.76%, LEVER -46.39%, ATA -32.23% ...). Muc dich tai lieu nay:
**do luong chinh xac** rui ro do (phan bo lo, MAE, tap trung) va **tim dau hieu bao truoc** (descriptive).

Nguon du lieu (dung san, khong tim lai):
- `printDone.csv` + `sim.out` cua `X1_GS_T170_2021`
  (`/home/ubuntu/java/devrun/X1_GS_T170_2021/storage/`, md5 printDone `efb793e2468ca3a7318da0f0ad23d4fc`, n=1089).
  Cot `profit` = % return/leg (da dau side), `pnl` = USDT, `funding` = funding FEE USDT (da nhan),
  `symbolPred` = score selector (1 - P(win)).
- `CLOSES_1H.bin` (`/home/ubuntu/java/fsrun/`, BE `[ts>i8,sym>i2,c>f4]`), map
  `selector_pred_out/symbol_map.csv` (BTCUSDT = symId 1).

2026-09-17.

---

## 1. Phan bo PnL / leg (printDone.csv, n=1089, 100% BUY long-only)

Tat ca 1089 lenh la **BUY** (long-only). Phan bo `profit` (%):

| thong so | gia tri |
|---|---|
| p1 / p5 / p25 | **-37.09 / -18.52 / +4.00** |
| p50 / p75 / p95 / p99 | **+5.00 / +7.00 / +20.79 / +61.86** |
| min / max | **-67.69 / +207.0** |
| mean / std | +5.24 / 15.86 |

- **Ti le lo** (`profit` < 0): **11.75%** (128/1089). (131 lenh co `pnl` < 0 — 3 lenh `profit` >= 0
  nhung `pnl` am do funding fee, so nho.)
- **Do sau lo nhat**: **-67.69%** (EVAA, 2025-11-03). 21 lenh lo qua -30%, 11 lenh qua -40%.
- **Tap trung KHONG (theo leg)** — duoi lo rat mo:
  - top-5 lenh lo = **-10,365 USDT = 19.3% tong lo**;
  - top-10 = **-17,173 = 32.0%**;
  - top-20 = **-25,929 = 48.3%**.
- Tong PnL toan ky: **+76,070 USDT** (thang +129,788 / lo -53,718).
- **Diem quan trong nhat cua muc nay**: 49 lenh co `profit` <= -20% (chi **4.5%** so lenh) chiem
  **-38,686 USDT = 72.0% TONG lo lich su**. Lo cua he nay **gan nhu toan bo nam o duoi lo sau**
  (duoi fat tail), khong phai trai deu.

## 2. Tap trung theo coin (printDone.csv)

358 coin rieng / 1089 lenh. 107 coin co bat ky lenh lo nao.

- **% tong lo theo so coin** (xep theo tong lo giam dan):
  - top-5 coin = **24.9%** tong lo;
  - top-10 = **36.7%**;
  - top-20 = **51.3%**;
  - top-30 = **62.5%**.
  - 50% tong lo chi den tu **20 coin**; 80% tu **52 coin** (trong 107 coin co lo).
- **Khong phai "mot vai coin" cung khong "rai deu"** — la **fat tail**: so it coin (top-20 = 5.6%
  so coin) ganh qua nua tong lo, nhung van co duoi dai.
- Top coin gay lo (tong lo USDT, n = so lenh, net = PnL rong):
  EVAA -5,404 (n=11, net -2,062); AIA -2,384 (n=14, net +2,808); JELLYJELLY -2,255 (n=3, net -37);
  DYM -1,919 (n=2, net -1,887); IN -1,398 (n=1); CKB -1,390 (n=4, net -1,203); COAI -1,389 (n=11, net -109);
  SOON -1,219 (n=2); AVNT -1,199 (n=2); XAN -1,154 (n=2); LEVER -1,022 (n=4, net -48).
- 54 coin co **PnL rong am** (15% so coin) — gom ca nhung coin co vai lenh thang nhung bi 1 lenh
  sup xoa sach (EVAA, CKB, SOON, XAN, AVNT ...).

## 3. Max Adverse Excursion — MAE (CLOSES_1H.bin, gia dong cua 1h)

MAE = (min close 1h trong [entry, exit] - entry)/entry. **Chi tinh duoc 890/1089 lenh**; 199 lenh
(~18%) giu qua ngan (< 1h den moc close ke tiep) nen khong co close nao trong cua so — bi loai khoi
phan bo MAE (loi thuong nho vi cac lenh nay thuc te giu rat ngan).

| thong so | gia tri |
|---|---|
| p1 / p5 / p25 | **-50.48 / -33.91 / -11.72** |
| p50 / p75 / p90 | **-1.89 / +6.04 / +20.83** |
| p95 / p99 | +33.68 / +91.92 |
| min / max | -81.85 / +207.4 |
| mean | -0.98 |

- **% lenh co MAE <= nguong** (gia di nguoc sau khi vao):
  - MAE <= -20%: **14.04%** (125 lenh);
  - MAE <= -30%: **6.40%** (57);
  - MAE <= -40%: **2.58%** (23);
  - MAE <= -50%: **1.24%** (11).
- Worst MAE: FTT -81.85% (11/2022), SRM -67.65% (11/2022), JELLYJELLY -65.63% (11/2025),
  EVAA -64.54% (11/2025), FTT -61.51%.
- **Gioi han**: MAE tinh tu **close 1h**, khong phai low trong gio => **danh gia THAP** muc di nguoc
  thuc te trong 1h (low co the sau hon close). Median MAE chi -1.89% (da so lenh it bi di nguoc),
  nhung duoi fat tail (p1 -50%) trung voi duoi lo o muc 1.

## 4. Cua so UW dai nhat (2024-04-10 -> 2024-07-11, tu equity that `b+unP`)

Equity that (sim.out): peak **72,229** (2024-04-09) -> day **67,463** (2024-04-14, -6.6%) ->
lan quanh 70,000 (thang 5 + 6) -> 69,058 (2024-07-05) -> hoi ve 71,893 (07-10) va **72,236 (07-11)**
=> **92 ngay underwater**.

- **80 lenh / 60 coin** trong 92 ngay (56 gate + 24 BIG_DOWN). Tong PnL **-185.6 USDT** (gan hoa von):
  64 thang +7,818 / 16 lo -8,003.
- **8 lenh sup sau** (`profit` <= -20%) = **-6,101 USDT = 76.2% tong lo cua cua so**. Xep theo do sau:
  LEVER -46.39%, CKB -41.76%, ATA -32.23%, BB -28.00%, ORDI -25.91%, TNSR -25.37%, OM -23.10%,
  BEL -21.02%. (Kem them nhom vua: JASMY -18.14%, 1000RATS -16.11%, MEW -15.40%.)
- **Thanh 2 cum sup ro ret** (chung sup trong vong 1 tuan, thoi gian giu 168h = time-stop):
  - **Cum thang 4** (entry 04-10..04-13): CKB, ATA, TNSR, BEL, OM => **-3,632 USDT**. Trung dung
    luc equity rot -6.6% trong 4 ngay (72,229 -> 67,463).
  - **Cum thang 6** (entry 06-08..06-11): LEVER, BB, ORDI => **-2,469 USDT**. Giu equity duoi dinh
    trong thang 6/7.
- **Doi chieu "neu BO cac coin do"** (tinh tu PnL da xay ra, KHONG chay sim lai):
  - Bo 8 lenh sup => PnL cua so tro thanh **+5,916 USDT** (thay vi -186).
  - Cum thang 4 (-3,632) la **76%** cua con rot -4,766 (72,229->67,463); bo no => con rot chi con
    ~-1,134 = **~-1.6%** thay vi -6.6%.
  - => **Cua so UW gan nhu chac chan se KHONG con dai nhat** (se hoi new-high som hon rat nhieu).
  - **Gioi han**: day la tong PnL da xay ra, **KHONG phai re-run** — duong equity thuc phu thuoc
    sizing, margin, thoi diem va tuong quan cac vi the cung luc. Nhung huong la ro rang va la con so
    toi thieu (bo con sup cung giai phong margin cho cac lenh thang khac).

## 5. Idiosyncratic vs market (hoi quy return leg len return BTC 1h cung ky)

**Phuong phap (don gian nhat)**: voi moi lenh, `btc_ret` = BTC close(exit)/BTC close(entry)-1
(tu CLOSES_1H, symId=1) trong **cung cua so giu lenh**; OLS `profit% = alpha + beta * btc_ret`.
R^2 = ty le bien dong return cua leg duoc giai thich boi thi truong/BTC.

Ket qua (n=1089, du ca lenh):

| thong so | gia tri |
|---|---|
| beta | **0.634** |
| alpha (intercept) | **+6.34%** |
| **R^2** | **0.0216 (2.2%)** |
| corr (profit, btc_ret) | 0.147 |
| std profit / std residual | 15.86 / 15.68 (phan rieng ~97.8%) |

- **Ket luan**: bien dong return cua tung leg **gan nhu toan bo (97.8%) la phan rieng coin**
  (idiosyncratic), chi ~2% theo BTC. `alpha = +6.34%` = edge duong doc lap voi BTC (long-momentum).
  `beta = 0.634` = co nhay cam BTC nhung rat yeu.
- **Tac dong thi truong chi hien o duoi**: khi BTC giam manh trong luc giu lenh (btc_ret < -5%,
  n=179) => mean profit **+0.03%**, ti le lo **31.3%**; khi BTC tang (btc_ret > 0, n=313) =>
  mean profit **+6.49%**, ti le lo **11.2%**. => thi truong khong giai thich duoc lo thuong, nhung
  **BTC giam manh lam ti le lo x3**.
- **Gioi han phuong phap**: (i) cua so giu lenh rat ngan (median btc_ret chi -0.42%, p95 +2.2%) nen
  BTC it chuyen dong trong luc giu => R^2 thap mot phan la do horizon qua ngan, khong phai vi "khong
  co beta"; (ii) chi dung close 1h; (iii) khong tinh R^2 tung coin vi moi coin chi co ~1-4 lenh
  (median ~3), khong du mau de hoi quy rieng. Can do them beta o horizon dai hon (vd BTC 30d tai
  entry) neu muon phan tach beta cau truc danh muc.

## 6. Dau hieu bao truoc (descriptive) — 8 lenh sup vs 72 lenh khong sup CUNG cua so UW

So sanh tai luc entry, nhom sup (`profit` <= -20%, n=8) vs nhom doi chung (phan con lai trong cung
cua so 2024-04-10..2024-07-10, n=72). **Mau rat nho** (n=8) => day la mo ta, khong phai ket luan
thong ke.

| tin hieu (tai entry) | sup (n=8) | doi chung (n=72) | ket luan |
|---|---|---|---|
| **momentum 30d (%)** | **+57.3** | **-3.7** | **CO khac biet, BANG CHUNG MANH** (huong ro) |
| vol 30d (std return 1h, %) | 1.87 | 1.63 | co khac biet nhe, bang chung **yeu** |
| drawdown 30d tu dinh (%) | -51.7 | -49.4 | **khong** khac biet |
| so ngay niem yet (ngay) | 412 | 392 | **khong** khac biet (tron 2 nhom, xem duoi) |
| funding fee (USDT) | +0.41 | +0.08 | **khong** khac biet (gia tri tuyet doi qua nho) |
| symbolPred (1 - P(win)) | 0.176 | 0.183 | **khong** khac biet |

- **Momentum 30d la tin hieu ro nhat**: 6/8 lenh sup co momentum 30d rat cao ngay truoc khi sup:
  OM +206.7%, ORDI +66.6%, BB +60.0%, ATA +50.1%, CKB +49.1%, BEL +48.6%. Hai lenh con lai LEVER +4.2%
  va TNSR -26.6% (khong theo mau). Trong khi nhom doi chung trung binh chi -3.7%.
  => **mau "alt vua pump manh roi sup"** (mua dinh / bat dao roi), trung voi gia thuyet selector
  anti-pump (`pNoPump` long vao coin vua sut tu dinh) da neu o muc 6a cua doc truoc.
- **So ngay niem yet khong phai tin hieu don tri**: trong nhom sup co ca coin rat moi (TNSR 4 ngay,
  BB 25 ngay, OM 59 ngay) lan coin cu (BEL 1,197 ngay, ATA 955 ngay). => "coin moi niem yet" khong
  giai thich duoc ca nhom, nhung dang chu y la nhieu vu sup sau nhat (JELLYJELLY, EVAA, DYM, XAN
  ngoai cua so) deu la coin niem yet gan day (2024-2025).
- **symbolPred (score selector) KHONG phan biet duoc** coin sup trong cua so nay (0.176 vs 0.183) =>
  selector hien tai khong canh bao duoc rui ro sup rieng le.
- **Gioi han tin hieu funding**: `funding.bin` trong `/home/ubuntu/wfo_ds_x1_2021/` **KHONG phai
  funding rate** ma la **score selector (1 - P(win))** (manifest `fundingSet=funding_selector_pred_1m_v2`,
  ma hoa `(symId<<32)|floatBits(score)`, cung gia tri voi cot `symbolPred`). **Funding RATE tho
  (chuoi thoi gian/coin) KHONG co trong cac bin san co**; tin hieu funding gan nhat la cot `funding`
  (funding FEE USDT da xay ra cua tung lenh), nhung no **bi tron voi thoi gian giu** (lenh lo giu
  den time-stop 168h nen phi funding lon hon lenh thang thoat som). => chua kiem duoc "funding rate
  bat thuong truoc khi sup" tu du lieu nay.

## 7. KET LUAN

**Rui ro nay lon co nao (so):**
- Rui ro **idiosyncratic (rieng tung coin) CHI PHOI**: R^2 voi BTC chi 2.2%, 97.8% bien dong return
  la phan rieng coin. Danh muc long-ALT khong co BTC beta => moi truong BTC-giam la xau nhat.
- Duoi lo **rat tap trung**: 49 lenh sup sau (`profit` <= -20%, 4.5% so lenh) = **72% tong lo lich su**;
  8 lenh sup cua cua so UW dai nhat = **76% lo cua cua so do** va **11.4% tong lo lich su**. Mot lenh
  lo sau nhat = -67.7% (EVAA).
- MAE cho thay ~14% lenh bi gia di nguoc qua -20% sau khi vao (do tu close 1h, danh gia THAP thuc te).

**Co the giam duoc khong:** **Co, ve nguyen tac** — vi lo khong trai deu ma tap trung o mot so "alt vua
pump manh roi sup" trong pha BTC giam. Nhieu trong so do co mau nhan dien duoc (momentum 30d cuc cao),
nhung **chua co bang chung de ket luan bat ky con so nao** (mau 8 lenh qua nho, va moi so o day deu
sinh tu chinh DEV da nhin).

**Cac huong (KHONG de xuat con so):**

| huong | can gi | rui ro | bang chung can de ket luan |
|---|---|---|---|
| (1) Luat exit/SL theo coin (cap DD rieng coin) | threshold + co che | cat som => giam meanP winner | ablation phan bo MAE -> PnL tren DEV, xac nhan holdout |
| (2) Loc thanh khoan / loai coin moi niem yet + microcap | threshold thanh khoan | bo mat coin "bay" loi lon | so sanh PnL/MADE cua coin duoi/tren nguong, tren holdout |
| (3) Scaling theo vol tung coin (giam size coin vol cao) | uoc luong vol/coin + cong thuc size | giam loi cung giam lai | moi tuong quan vol30d tai entry vs PnL lenh (o day chi thay khac biet yeu n=8) |
| (4) Gioi han tuong quan / danh muc (cap % 1 coin, cap cum tuong quan) | metric tuong quan + cap | qua chat => it co hoi | phan tich tuong quan PnL giua cac leg cung coin/cung cum (chua lam) |
| (5) Gate theo regime BTC (giam long-alt khi BTC down) | pre-reg scale per regime | fit regime tren DEV | da co `PREREG_REGIME_GATE.md`; xem ket qua RG_* |
| (6) Xem lai selector anti-pump (dang long vao coin vua sut) | pre-reg rank/cutoff | doi dinh huong danh muc | rank-IC theo PnL, khong chi P(win) |

**Chua kiem duoc tu du lieu nay (can ghi ro):**
- Funding RATE tho (bin hien co chi la score selector + funding FEE da tron thoi gian giu).
- R^2/beta tung coin (mau qua nho) va tuong quan PnL giua cac lenh cung coin/cum.
- Duong equity counterfactual that (chi tinh tong PnL da xay ra, khong re-run).
- MAE dung low trong gio (chi co close 1h).

Co-Authored-By: Claude (subagent) — phan tich mo ta, khong pre-reg, khong push.
