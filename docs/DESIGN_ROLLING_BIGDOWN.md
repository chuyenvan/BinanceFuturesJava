# DESIGN_ROLLING_BIGDOWN — hướng "rolling" cho BIG_DOWN (scale + bắt chuẩn hơn)

> **Tai lieu THIET KE/DESCRIPTIVE — KHONG chay sim, KHONG sua code, KHONG chot tham so.** Moi de
> xuat duoi day phai qua pre-reg rieng + duyet cua master truoc khi chay. Doc cung:
> `DIAG_BIGDOWN_TRIGGER_MECHANISM.md`, `DIAG_BIGDOWN_ADAPTIVE_SANITYCHECK.md`,
> `AUDIT_BIGDOWN_DECOMPOSE_READJUDICATE.md`, `DIAG_BIGDOWN_CONCENTRATION.md`,
> `DIAG_DCA_CONCURRENCY.md`, `DIAG_UW_WINDOW_202503_202510.md`.
> 2026-09-16. Yeu cau: *"tim huong rolling cho bigdown de scale va bat chuan hon"*.

---

## 0. Tom tat cho nguoi doc nhanh

- **KHONG nen** lam nguong rolling kieu `mean_N - k*std_N` tren `rateDownAvg`: da do, 9/9 to hop
  FAIL (166x-495x so trigger hien tai) vi phan phoi **skew -14.9 / excess-kurtosis +2401**; nguong
  co dinh `-0.03157` tuong duong **-22.4 sigma**. Dang `mean±k*std` gia dinh gan-chuan => sai.
- **KHONG the** tai lap do hiem hien tai (124 phut / 2.3 trieu phut = **5.4e-5**) bang quantile
  rolling truc tiep: cua so 30 ngay chi co ~43k mau, quantile p5.4e-5 ~ **2 mau** => khong uoc
  luong duoc. Do hiem phai den tu **HOI TU (conjunction)** cac marginal uoc luong duoc, khong phai
  tu mot quantile cuc doan cua mot bien fat-tail.
- **3 truc dong duoc**, xep theo rui ro tang dan (va theo bang chung):
  1. **SIZING (scale)** — giu nguyen trigger, dat size leg BIG_DOWN theo do sau (rolling-normalized).
     Chi cham duong budget; khong cham trigger/live/isDcaAlt/HPO gene.
  2. **SELECTION (bat chuan hon)** — giu nguyen trigger, doi **coin nao** duoc chon (hien tai chon
     theo pNoPump tang dan, KHONG theo do giam). Rolling-normalize theo tung coin de "bat dung con
     rớt sau nhat". Khong cham trigger.
  3. **TRIGGER (rolling co hoi tu)** — thiet ke lai dieu kien kich hoat thanh hoi tu cua >=2
     marginal uoc luong duoc (depth quantile vua phai + xac nhan nhieu phut). Rui ro cao nhat vi
     cham ca sim+live + gene HPO.
- **Rang buoc bat buoc** (tu DIAG muc 5): (5.1) `MS_DOWN_BIG_AVG` dung CHUNG cho `isDcaAlt` (DCA
  nhay hon 43x) — phai TACH 2 duong, va tach la doi hanh vi can parity gate; (5.2) `getMarketStatus1M`
  dung chung sim+LIVE, thuan + khong tham so thoi gian; (5.3) cam dong `calMarketData` (duong
  feature model); (5.5) `MS_DOWN_BIG_AVG` la gene HPO o 3 noi; (5.7) mau su kien mong (56 ngay).

---

## 1. Vi sao "rolling nguong" kieu cu KHONG duoc (chot lai, khong mo lai)

| bang chung | so lieu |
|---|---|
| Nguong hien tai `rateDownAvg < -0.03157` | **124 phut / 56 ngay / 248 leg** tren 4.5 nam |
| Hinh dang `rateDownAvg` | skew **-14.87**, excess-kurtosis **+2401** (chuan = 0/0) |
| Nguong co dinh quy ra sigma | **-22.4 sigma** (do ca span) — khong phai 2-3 sigma |
| `mean_N-k*std_N` (9 to hop N=90..180, k=2..3) | **20,536-61,397 phut = 166x-495x**; 87-98% so ngay; 0/1645 ngay co `thr>=0`; `thr` trong [-0.00807,-0.00195] |
| `k` de tai lap mat do hien tai | phai **~23-25**, va **dao -13.5..-41.5** (3.1x) theo giai doan => khong on dinh |
| Quantile trailing-30d cua `rateDownAvg` | p0.01 median **-0.01634**; nguong co dinh sau hon p0.01 o **83.9%** so ngay |

=> Van de khong phai "chon N/k khac", ma la **dai luong bi so (rateDownAvg) co duoi qua nang so voi
than phan phoi**; moi thong ke rolling kieu mean/std/quantile re (p>=0.1%) deu nong hon su kien
that 4x-16x. Ket luan: **doi cach tiep can, khong doi tham so.**

---

## 2. Truc SIZING (khuyen nghi so 1 — "scale")

### 2.1 Bang chung ung ho
`AUDIT_BIGDOWN_DECOMPOSE_READJUDICATE` muc 1+3: leg BIG_DOWN **bypass hoan toan gate** (symbolPred
= null) nhung `pnl/leg` tang don dieu theo do chat gate: **46.6 -> 53.3 -> 65.5 USD/leg** (T100 ->
T170), **+41%** tu **cung 248 leg / 124 tick / 54 ngay**. Co che: gate chat => it lenh dong thoi =>
`throttle = 1 - u/U_MAX` cao => **moi leg duoc cap budget lon hon**. Tuc **loi ich cua BIG_DOWN o
T170 la qua SIZING**, khong phai qua chon entry. T170 hien **chua bao gio** cham bac 3 (0/1069 cum;
tap trung toi da 1 coin = **8.71% equity**).

### 2.2 Thiet ke de xuat (S1) — size theo do sau, causal
```
severity(D,t) = vi tri cua rateDownAvg(t) trong phan duoi rolling N-ngay cua chinh no,
                normalize ve [0,1] bang quantile rolling (p0.5 .. p0.01) — CAUSAL [D-N, D)
sizeMult(t)   = clamp(1 + a * (severity - 0.5), lo, hi)      # a, lo, hi chot TRUOC
margin(leg BD) = base * sizeMult(t)                          # chi nhanh BIG_DOWN
```
- Khac biet co ban voi "nguong rolling": **khong doi DIEU KIEN kich hoat** (248 leg giu nguyen,
  parity de giu) — chi doi **kich thuoc** tung leg.
- **Chieu scale phai chot TRUOC va co ly do**: (i) scale LEN khi sau (an theo pnl/leg cao cua
  BIG_DOWN), hay (ii) scale XUONG khi cuc sau (an theo `DIAG_BIGDOWN_CONCENTRATION`: 13 cum bac 3
  => **-27,857 USD**, 6 thang/7 thua; T130/AIA -12,400 = -11.8% equity 1 coin). **De xuat (ii) —
  tran/ giam size khi severity cuc doan** la huong an toan hon va truc tiep giam rui ro tap trung.
- Uoc luong duoc: severity dung quantile **p0.5..p0.01** (uoc luong duoc voi 43k mau/cua so), khong
  dung duoi cuc doan.

### 2.3 Chi phi/rui ro
- Chi cham `managerBudget` cho rieng nhanh BIG_DOWN => **khong cham live trigger**, khong cham
  `isDcaAlt`, khong cham gene HPO, khong cham feature model.
- Can flag moi default OFF + cong parity byte-identical (T170 md5 `efb793e2…`).
- Khong sua `NUMBER_ENTRY_EACH_SIGNAL` (2 coin/tick giu nguyen).

---

## 3. Truc SELECTION (khuyen nghi so 2 — "bat chuan hon")

### 3.1 Bang chung
`DIAG_BIGDOWN_TRIGGER_MECHANISM` muc 1.5: BIG_DOWN chon coin theo **score selector pNoPump TANG
dan** (`getTopSymbolArray` lay cone pNoPump THAP nhat = "de pump nhat"), **KHONG theo do giam sau
nhat**. Do la mot diem bat hop ly: khi thi truong sup, thu tu "de pump" khong lien quan den "con
nao dang bi ban manh nhat". `AUDIT` muc 3 cung cho thay **coin chon khac nhau** (161/166/161 coin)
giua cac gate nhung so leg y het => co **khong gian doi SELECTION ma khong doi so luong**.

### 3.2 Thiet ke de xuat (SEL1) — doi tieu chi chon coin trong 2 leg BIG_DOWN
```
candidate = coin co  (rateChangeCoin(t) / rollingScaleCoin(D))  am nhat  (causal, [D-N,D))
```
hoac ban an toan hon: **giu pNoPump lam primary, dung rolling-drop lam tie-break** khi nhieu coin
cung score. Phai causal theo tung coin; nguon gia tung coin trong sim: ticker 1m (co san o duong
sim), live cung co.
- Loi ich ky vong: "bat dung con rớt sau nhat" => leg BIG_DOWN chat luong hon (pnl/leg, TSloss)
  ma **khong tang so leg, khong doi trigger, khong doi gate**.
- So luong giu **2 coin/tick** (khong doi) => khong pha `symbolLocked`/concurrency.

### 3.3 Rui ro
- Chon theo "rớt sau nhat" co the trung **coin delist/thanh khoan mong** (loc `diedSymbol` da co,
  nhung can kiem them thanh khoan). Phai co cong kiem: khong duoc chon coin ngoai universe trade.

---

## 4. Truc TRIGGER (khuyen nghi so 3 — rui ro cao, chi lam sau)

### 4.1 Thiet ke "hoi tu" (conjunction) — de xuat (R1)
Do hiem den tu **giao cua >=2 marginal uoc luong duoc**, khong tu mot quantile cuc doan:
```
D1: rateDownAvg(t)  <=  q_p1(N)          # p1 in {0.1%, 0.5%} -> ~-0.0088 / -0.0056
D2: rateDown15MAvg(t) <= q_p2(N)         # bien 15-phut (co trong market.bin + live tinh duoc)
D3: xac nhan k phut lien tiep / khong hoi phuc ngay
trigger = D1 AND D2 (AND D3)
```
- Moi marginal uoc luong duoc (p1>=0.1% => >=43 mau/cua so 30 ngay). Do hiem den tu **giao**.
- `rateDown15MAvg` dang co san: p0.1 = -0.040281, p1 = -0.021841; nguong -0.03157 cham o **0.231%**
  so phut (43x `rateDownAvg`) => la bien "bot hiem" phu hop lam D2.

### 4.2 Canh bao (tu DIAG muc 5 — phai xu ly truoc khi code)
1. **Tach `MS_DOWN_BIG_AVG`**: hien dung chung cho ca `getMarketStatus1M` (BIG_DOWN) va `isDcaAlt`
   (DCA, nhay 43x). Lam rolling ma khong tach => **doi luon tan suat DCA**. Tach = doi hanh vi =>
   parity gate rieng.
2. **Sim + LIVE dung chung ham**: `getMarketStatus1M` la static/thuan/khong tham so thoi gian.
   Rolling => phai them `time` hoac state => **cham duong LIVE**. Sim doc `market.bin`, live tu tinh
   tu ticker => phai dam bao **cung ket qua** (loai loi da tung xay ra: `AUDIT_GATE_DYN_PARITY`).
3. **Uu tien "schedule" nhu `RegimeSchedule`**: tinh rolling stat **offline theo ngay (causal)** ->
   CSV -> doc bang `floorEntry`, yhet tien le `GATE_REGIME_ADAPTIVE` (da kiem causal, da co pre-reg).
   Cach nay **khong cham cong thuc tinh ticker tren live**, chi them 1 reader + 1 flag default OFF.
4. **Gene HPO**: `MS_DOWN_BIG_AVG` la gene o `WFORunner:67`, `StrategyWfoTask:74`,
   `SensitivityTool:69` — neu no thanh dai luong dan xuat thi 3 cho kia set field chet (loi im lang).
5. **Mau su kien mong**: 56 ngay co su kien / 4.5 nam => moi tham so moi rat de overfit; ca 3 gate
   T100/T130/T170 cho **cung 248 leg** nen **khong the dung gate lam bien doi chung doc lap**.

---

## 5. Thu tu de xuat (de nghi master chon)

| # | Huong | Cham gi | Rui ro | Gia tri ky vong |
|---|---|---|---|---|
| 1 | **SIZING S1** (size theo severity, tran khi cuc doan) | budget nhanh BIG_DOWN | thap | giam tap trung 1-coin (bac3), giu/ tang pnl/leg |
| 2 | **SELECTION SEL1** (doi/bo sung tieu chi chon coin) | chon coin 2 leg BD | thap-vua | "bat chuan hon", khong tang so leg |
| 3 | TRIGGER R1 (hoi tu 2 marginal + xac nhan) | trigger sim+live + gene HPO | cao | thay doi ban chat BIG_DOWN |

**De nghi bat dau bang (1) SIZING** vi: (a) bang chung manh nhat (audit da chung minh gia tri
BIG_DOWN den tu sizing), (b) blast radius nho nhat (chi budget), (c) truc tiep giam rui ro tap trung
da do (-27,857 USD o 13 cum bac 3). Neu (1) khong sinh loi -> sang (2). (3) chi lam khi (1)/(2) da
chay xong va co ly do ro.

---

## 6. Tieu chi danh gia de xuat (cho pre-reg sau nay)
- **Chat luong leg BIG_DOWN**: `pnl/leg`, `meanP` rieng nhanh BIG_DOWN (khong lan voi entry).
- **Tap trung**: max % equity vao 1 coin; so cum cham bac >=2 / bac 3; PnL cum bac 3.
- **Rui ro tong**: maxDD / UW toan cua so (nho: hard-constraint tren duong TONG HOP khong dung duoc
  — `AUDIT` muc 5.2; phai lay tu `sim.out` equity THAT).
- **So leg BIG_DOWN**: phai **khong doi** o truc SIZING/SELECTION (248) — do la cong chan drift.
- **CI block 72h x1.21**; multiplicity: ghi ro so bien the da chay truoc khi ket luan.
- **Khong cham holdout 2026**; moi so tren DEV 2022-2025 => chi la ung vien, xac nhan that o holdout.

## 7. Gioi han cua memo nay
- Khong de xuat con so cu the (a, lo, hi, p1, N, k) — do la quyet dinh pre-reg cua master.
- Moi de xuat dua tren bang chung DEV da nhin => **mang rui ro overfit y het moi vong truoc**.
- Chua kiem tra duong live cua bat ky thiet ke nao (chua co harness).
