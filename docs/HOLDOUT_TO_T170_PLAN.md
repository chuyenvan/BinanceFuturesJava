# KE HOACH TICH HOP HOLDOUT-TREND SANG T170 (RANKING + STOP LOGIC)

**Ngay:** 2026-09-17
**Trang thai:** DOC-ONLY (khong sua `.java`, khong chay sim T170)
**Nguon:** branch `holdout-archive` / commit `1b93fe9`, thu muc `_wfotmp/holdout/`

---

## 0. TOM TAT NGHIEN CUU HOLDOUT (da tai lap)

- Holout chay tren **40 tai san truyen thong, bar NGAY** (equity / commodity / fx / bond),
  long-only, khong short, khong don bay. Bo hoi quy `ensemble trend + vol targeting`
  (SMA 50/100/200 -> sig, vol 30d -> size = min(0.40/rv, 1), band 0.20, exec_lag 1 ngay).
- **Ket qua (da chay lai, khong lech):**
  - `sharpe_strat = 0.2279`, `sharpe_hold = 0.3003`, `p_value = 0.069`, `z = 1.638`
  - `dd_improve = 0.2470`, `classes_pass = 2/4`
  - **verdict = CHET (p >= 0.05).** => huy bo "trend following lam loi" cho tradfi.

### Ket qua ABLATION (descriptive, KHONG phai kiem dinh xac nhan)

Tach 2 thanh phan, CUNG data + CUNG null (1000 rotation, seed `20260830`):

| Bien the | Sharpe strat | Sharpe hold | p_value | z | dd_improve | verdict (descriptive) |
|---|---|---|---|---|---|---|
| trend-only (size=1) | 0.2192 | 0.3003 | 0.109 | +1.31 | 22.7% | KHONG edge |
| vol-only (sig=1) | 0.3097 | 0.3003 | 0.000 | +4.85 | 5.4% | edge manh (canh bao duoi) |
| full (goc) | 0.2279 | 0.3003 | 0.069 | +1.64 | 24.7% | KHONG edge |

**Doc y nghia:**
- **Thanh phan trend (SMA crossover) KHONG mang tin hieu** tren tradfi daily, long-only.
  No keo Sharpe cua ca bo xuong (full 0.228 < vol-only 0.310). Day la dieu nguoc lai
  so voi ke vong "trend following la san nha tradfi".
- **Thanh phan vol-targeting (giam size khi vol cao) moi la cho mang chut tin hieu.**
  Nhung canh bao: null hoan vi cho bien the vol-only **rat chat** (position gan nhu hang
  so, roll no khong doi gi) -> p=0.000 la do `sd` null rat nho, khong phai edge lon.
  Muc cai thien Sharpe so voi mua-giu thuc te chi **+0.009** (0.3097 vs 0.3003), va
  `dd_improve` chi 5.4%. Day ban chat la **de-risking (vol-managed portfolio)** chu
  khong phai "alpha trend-following".

=> **Ket luan cho T170:** dung mang y tuong "trend" sang crypto 1-phut. Neu muon dung
gi do tu holout nay, chi con (a) y tuong **vol-targeting de-risking** (yeu, chua chac
chuyen domain) va (b) **cau truc xep hang + stop logic** (thuoc T170, khong phai holout).

---

## 1. KHAC BIET DOMAIN (vi sao khong "mang nguyen xien" duoc)

| | Holdout | T170 |
|---|---|---|
| Tai san | 40 tradfi (equity/commodity/fx/bond) | crypto perpetual futures |
| Bar | NGAY | 1 PHUT |
| Huong | long-only, khong don bay | long + short, co don bay |
| Tin hieu | SMA 50/100/200 + vol 30d | S1 selector 9 feature (bar 1h) |
| Exit | khong stop, khong TP | arm 0.07 + giveback min(peak*0.5,cap), time-stop 168h |
| Null | rotation 1000, seed co dinh | (rieng cua T170) |

- Tham so `50/100/200 ngay`, `vol 30 ngay`, `target 0.40`, `band 0.20` deu la cua khung
  NGAY + tradfi. Tren crypto 1-phut chung **vo nghia** (thanh phan trend da FAIL o daily).
- Domain shift (tradfi -> crypto) + resampling (ngay -> phut) + che do (long-only ->
  long/short) => bat ky "mang nguyen xien" nao deu la overfit tuong minh.

---

## 2. DE XUAT: DUNG Y TUONG LAM RANKING (KIEU S1/SELECTOR) + STOP LOGIC CUA T170

Khong port bo hoi quy. Chi muon lai **y tuong "tap dac trung trend/vol -> tin hieu xep
hang coin"** va **giu nguyen co che exit cua T170**.

### 2.1 Tin hieu xep hang coin (thay the / bo sung S1)

- Xay mot tap dac trung trend/vol (khong tune truoc) cho moi coin, vi du:
  - trend: dac trung SMA/EMA da khung (50/100/200 nhung tinh tren bar 1h hoac 4h),
    MACD, don gian la ty le SMA da tan so vuot/duoi.
  - vol: realized vol (nhieu khung), vol percentile, `vol-targeting` da dang
    (dung de **de-risk** / giam size, khong phai de xep hang).
- Dung tap dac trung nay lam **dau vao ranker** (kieu `S1RankerLive`), cho ra score xep
  hang cac coin -> chon top-K de vao lenh.
- **Khong dung** ket qua tradfi de chon tham so. Tat ca la gia thuyet MOI.

### 2.2 Exit: GIU NGUYEN logic stop cua T170

- Khong mang "khong stop / khong TP" tu holout (holout la backtest don gian, khong co
  co che quan tri rui ro). T170 da co exit da kiem:
  - arm = 0.07 (C3) / 0.05 (live), giveback = `min(peak * 0.5, cap)`,
  - time-stop = 168h (STRONG) / 72h (WEAK).
- Muc dich xep hang chi la **chon coin nao vao lenh + co the scale size**; viec thoat
  van do stop logic T170 quyet dinh.

---

## 3. THU TU BAT BUOC TRUOC KHI TICH HOP

> Quy tac cung: **khong duoc tune tren DEV**, moi lan nhin DEV phai ghi nhan. Holout goc
> da FAIL (p=0.069) => day la **gia thuyet MOI**, khong phai "verify lai". Phai co
> **pre-reg rieng** truoc khi chay sim.

### Stage 1 — STANDALONE (khong dung T170, khong sua Java)

**Cau hoi:** tin hieu xep hang (tap trend/vol) co **du doan duoc forward return** cua
crypto khong?

- **Lam gi:** tinh dac trung trend/vol cho moi coin, moi bar; tinh **IC / rank-IC**
  giua score xep hang tai t va forward return (t+1 .. t+H) tren du lieu crypto.
- **Kiem dinh:** IC mean != 0 (t-test / bootstrap), kiem tra tinh on dinh qua thoi gian,
  kiem tra co phu thuoc phan phoi (rank-IC thay vi IC don).
- **Nguong PASS (ghi truoc):** rank-IC mean duong voi p < 0.01, va khong do mot vai coin
  / mot khoang thoi gian duy nhat tao nen.
- **Neu PASS** -> sang Stage 2.
- **Neu FAIL** -> DUNG, ghi `NULL` (khong co tin hieu), khong tiep tuc.

### Stage 2 — PRE-REG + CODE + SIM TONG THE T170

- **Pre-reg (ghi truoc khi chay, khong sua sau khi thay ket qua):**
  - tap dac trung cu the + cong thuc tinh,
  - cach xep hang (top-K, ngat the nao),
  - che do vao lenh (chi long / long-short),
  - exit = stop logic T170 (arm 0.07 + giveback min(peak*0.5,cap), time-stop 168h),
  - metrics chinh (Sharpe, maxDD, so lenh, IC), ngung quyet dinh song/chet.
- **Code:** them ranker / feature moi (Java, hoac Python pipeline roi export), chay
  **sim tong the T170** voi stop logic hien tai, so sanh voi baseline T170 hien tai.
- **Neu co edge that** -> danh gia tiep (robustness, domain, capacity).
- **Neu khong** -> DUNG, ghi NULL, khong tune de cuu.

---

## 4. CAN GI CHO TUNG BUOC

### Stage 1 (STANDALONE)
- **Du lieu:** crypto perp OHLCV (1h va 4h de tinh trend/vol), cung nguon data voi T170
  hien tai; forward return theo khung cua ranker.
- **Feature:** trend (SMA/EMA da khung, MACD, slope), vol (realized vol nhieu khung,
  percentile, vol-managed de-risk).
- **Code:** script Python doc lap (khong dung vao `src/`), tinh IC/rank-IC + kiem dinh.

### Stage 2 (PRE-REG + SIM)
- **Du lieu:** cung tren + du lieu OI/funding neu muon bo sung (giu dong bo voi S1).
- **Feature:** ban dong cua Stage 1 (da pre-reg).
- **Code:** ranker moi (kieu S1) + hook vao sim tong the T170; dung lai exit hien tai.

---

## 5. RUI RO

- **Overfit:** 40 tai san tradfi + 1 lan nhin ket qua => bat ky "dieu chinh" nao sau khi
  thay ket qua crypto deu la overfit. Buoc pre-reg Stage 2 la bat buoc.
- **Domain shift:** tradfi daily -> crypto perp 1-phut; vol-targeting va trend deu co the
  doi dau khi sang crypto (crypto vol cao, khong co "bull 40 nam").
- **Leak:** khi tinh feature phai dung duy nhat thong tin toi t (khong nhin tuong lai),
  can than rank cross-section va warm-up.
- **Null chat (bai hoc tu ablation):** null hoan vi cho position gan hang so cho sd rat
  nho -> p "dep" gia tao. Kiem dinh IC/rank-IC o Stage 1 phai dung null dung nghia
  (shuffle thoi gian / bootstrap block), khong dung lai null position-rotation cua holout.
- **Stop logic tuong tac:** ranking moi co the doi so lenh vao/ra -> ket qua tang/giem co
  the den tu exit (stop T170) chu khong phai ranker. Phai so sanh cung exit baseline.
