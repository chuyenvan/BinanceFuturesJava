# DIAG_BREADTH_REGIME — market-breadth (top-50/MA200/50%) lam regime filter — TASK B2 Buoc 5.2 (de xuat Uni) — DA CHAY XONG 2026-09-21 (executor Sonnet, 0-sim) — VERDICT **GO**

Theo `docs/PREREG_BREADTH_REGIME_DIAG.md` (commit `3536a2a`, khoa metric/cong TRUOC khi tinh so).
Commit code+ket qua: xem cuoi file. Tai dung nguyen van `trend_rank_ic.load_closes`,
`bigdown_struct.load_trades_utc/block_boot_mean/phi_for` — khong sua file goc. 0-sim tuyet doi
(khong Java, khong xgboost, khong build).

## 0. Nguon volume + cach chon top-50 (recon, khong co volume trong CLOSES_1H.bin)

Da xac nhan bang doc truc tiep: `/home/ubuntu/java/fsrun/CLOSES_1H.bin` = 144,513,404 byte;
dtype `trend_rank_ic.load_closes()` = `(ts:int64, sym:int16, close:float32)` = 14 byte/record;
144513404 / 14 = 10,322,386 record **NGUYEN** (khong du) → file **CHI co 3 cot nay, KHONG co
volume**. Nguon volume thuc (`CoinRankManager.java`: rank theo tong volume 720 nen tu
`HistoryManager` ring buffer qua Aerospike LIVE, cap nhat hang gio) doi hoi chay JVM+Aerospike —
**vi pham 0-sim**. File volume roi (`kaggle_data_hpo/ticker_YYYYMMDD.bin(.gz)`) la Java
`ObjectOutputStream` serialize `TreeMap<Long,Map<String,KlineObjectSimple>>` — khong doc duoc
bang Python thuan, va khong co artifact `ExportCoinTierStatic` nao da xuat san tren dia.

**PROXY da chon**: `symId 1..N` theo `map_kaggle.csv` (thu tu ID = thu tu Binance Futures NIEM
YET theo thoi gian — ID nho = niem yet som). Da xac nhan symId 1-50 la cac coin lon/thanh khoan
cao da biet (BTC,ETH,BNB,ADA,DOGE,LINK,AVAX,SOL,MATIC,UNI,AAVE,ATOM,NEAR,SNX,...) — face-validity
hop ly voi "top von hoa/thanh khoan som", du KHONG phai xep hang volume rolling thuc. **STATIC**
(khong rolling theo thang) — ly le: (i) tranh lookahead-selection; (ii) da xac nhan symId 1-50
(tru 2 ca) co du lieu DAY DU suot 2021-01-01→2026-01-01 nen khong can universe rolling phuc tap
cho cau hinh chinh. **Con song tai t (causal)**: symId 4 (EOSUSDT) va 35 (MATICUSDT) trong nhom
1-50 dung lai truoc 2026 (huy niem yet/doi symbol) — coin roi khoi mau so breadth tu ngay do,
KHONG backfill. Do trong SIM range: so coin "song" moi ngay min=48, median=50.0, max=50 (rat on
dinh, chi 2/50 anh huong nhe).

## 1. Dinh nghia (khoa PREREG, nhac lai)

`breadth(D) = 100 * (%coin top-50 co close[D-1] >= MA200_causal[D]) / (%coin con song)`;
`not_up(D) = breadth(D) < 50%`. Cua so SIM: `2021-07-01..2025-12-31` (trung `trend_regime.py`
Buoc 5.1 de so nam-voi-nam). Cau hinh CHINH khoa cho cong: **top50, MA200, nguong 50%**.

## 2. %not-up moi nam — breadth vs MA200-BTC (Buoc 2/4) vs trend-detector SMA7/100 (Buoc 5.1)

| Nam  | Breadth top50/MA200/50% | MA200-BTC | Trend-detector BTC |
|------|------------------------:|----------:|--------------------:|
| 2021 | **63.0%** (n=184)       | 35.3%     | 20.7%                |
| 2022 | **100.0%** (n=365)      | 100.0%    | 60.8%                |
| 2023 | **66.0%** (n=365)       | 19.7%     | 13.2%                |
| 2024 | **55.2%** (n=366)       | 19.9%     | 15.3%                |
| 2025 | **72.9%** (n=365)       | 26.6%     | 32.6%                |

**Phat hien quan trong**: breadth KHONG chi nhay hon o 2025 — no bao "not-up" NHIEU HON o **MOI**
nam (55-100%, ngay ca 2023/2024 la nam uptrend khoe nhat cua T170/core). Day la vi breadth<50%
la mot dieu kien de dat (chi can dung mot nua thi truong duoi MA200 cua chinh no, thuong xay ra
do xoay-vong/rotation giua cac coin dai). Khac han tin hieu huong-gia (MA200-BTC, SMA-crossover)
chi bao "not-up" it (13-33%) trong cac nam tang gia. Neu chuyen thanh mot gate/throttle thuc su,
day la mot thay doi **rat sau rong** (ap dung >50% thoi gian trong 4/5 nam) — can do lai bang sim
thuc truoc khi ket luan ve chi phi CAGR, KHONG suy dien tu bao phu UW mot minh.

## 3. CONG QUYET DINH — %phu not-up 2 chuoi UW (cau hinh CHINH top50/MA200/50%)

| Chuoi UW        | n ngay | %not-up (breadth) | Nguong |
|-----------------|-------:|-------------------:|-------:|
| UW-2022 (P3)    | 248    | **92.7%**           | ≥60%   |
| UW-2025 (T100)  | 227    | **70.9%**           | ≥60%   |

**GATE VERDICT: GO** — CA HAI cua so ≥60%. Day la lan DAU TIEN trong 6 round breadth (TASK B →
B2 Buoc 2 → 3 → 4 → 5.1 → **5.2 nay**) mot tin hieu regime phu duoc UW-2025 qua nguong (70.9%,
so voi MA200-BTC chi 15.9-16.1% va trend-detector SMA7/100 chi 19.8% — cach biet lon, 3.5-4.5x).
Xac nhan gia thuyet cua Uni: breadth (do rong/participation) la tin hieu KHAC LOAI voi huong-gia,
va no bat duoc dung dieu ma moi detector huong-gia da thu deu miss — giai doan UW-2025 la
"bull-run-co-song-lon" (gia BTC +33%) nhung DUOI TAN NEN, phan lon coin trong top-50 van yeu
(duoi MA200 cua chinh chung) — mot dang phan ky rong/gia (breadth divergence) co thuc.

## 4. Edge doc lap (khong qua sim) — CAN TRONG: khong ro net nhu ky vong

- **Forward BTC return theo breadth-regime** (n=1645 ngay): `up` (breadth≥50%, n=455):
  fwd1d=-0.012% (std 2.51%), fwd7d=+0.147% (std 6.55%). `notup` (breadth<50%, n=1190):
  fwd1d=+0.135% (std 2.83%), fwd7d=+0.883% (std 7.79%). **Nguoc voi ky vong don gian**: forward
  return BTC trong regime "notup" (breadth thap) cao hon (khong am) so voi regime "up". Dien
  giai hop ly: dung voi chan doan UW-2025 truoc — giai doan breadth thap thuong la luc BTC
  "gian ra" khoi altcoin (BTC-dominance tang, alt yeu) MA CHINH BTC van tiep tuc tang — khac han
  logic "not-up = gia se giam" cua MA200-BTC/trend-detector. Ca hai deu duong tren trung binh —
  khong co bang chung breadth du bao BTC giam gia sap toi.
- **ROI so T100 theo breadth-regime luc mo lenh**: `up` (n=1030): roi_mean=**3.34%**
  CI90[1.68,4.84], loss_rate=16.12%, phi_dong-thua=2.185. `notup` (n=1529): roi_mean=**1.99%**
  CI90[1.08,2.88], loss_rate=15.76%, phi_dong-thua=1.914. **`notup` VAN DUONG RO** (CI90 duoi xa
  tren 0), loss_rate GAN NHU KHONG DOI (15.76% vs 16.12%), va phi dong-thua (rui ro cluster) o
  `notup` con **THAP HON** `up` (1.91 vs 2.18) — TRAI voi huong ky vong mot regime "xau" phai co
  phi CAO hon. ⇒ Giong nhu phat hien cua trend-detector o Buoc 5.1: breadth-notup phu duoc CUA SO
  THOI GIAN cua UW nhung KHONG danh dau ro rang cac LENH XAU (khong tach duoc chat luong lenh nhu
  regime bear-multi-week thuc su o TASK B2 Buoc 1). Day la diem CAN TRONG quan trong cho MASTER:
  bao phu-thoi-gian (cong PREREG) va chat-luong-lenh (edge doc lap) la HAI cau hoi khac nhau —
  bao phu PASS nhung edge KHONG xac nhan mot co che nhan-dien-lenh-xau ro rang. Neu mo sim thuc,
  UW co the giam (vi bao phu thoi gian tot) NHUNG CAGR co the mat nhieu hon ky vong vi phan lon
  lenh bi cham/giam trong "notup" van la lenh TOT (roi_mean 1.99% >> 0).

## 5. Sweep MO TA (KHONG chon winner) — %phu UW theo tham so

| topN | MA  | Nguong | %UW-2022 | %UW-2025 |
|-----:|----:|-------:|---------:|---------:|
| 30   | 100 | 40%    | 81.5     | 50.7     |
| 30   | 100 | 50%    | 91.1     | 55.5     |
| 30   | 100 | 60%    | 94.4     | 65.2     |
| 30   | 200 | 40%    | 87.9     | 63.4     |
| 30   | 200 | 50%    | 92.3     | 70.5     |
| 30   | 200 | 60%    | 95.6     | 80.6     |
| 50   | 100 | 40%    | 84.7     | 52.9     |
| 50   | 100 | 50%    | 92.7     | 56.4     |
| 50   | 100 | 60%    | 96.0     | 67.0     |
| **50** | **200** | **50%** | **92.7** | **70.9** ← cau hinh CHINH |
| 50   | 200 | 40%    | 91.9     | 64.8     |
| 50   | 200 | 60%    | 97.6     | 81.9     |
| 100  | 100 | 40%    | 87.1     | 53.7     |
| 100  | 100 | 50%    | 91.1     | 61.7     |
| 100  | 100 | 60%    | 96.0     | 71.8     |
| 100  | 200 | 40%    | 89.9     | 72.7     |
| 100  | 200 | 50%    | 92.3     | 83.3     |
| 100  | 200 | 60%    | 92.3     | 94.3     |

**Do nhay**: MA200 luon phu UW-2025 nhieu hon MA100 cung topN/nguong (chenh ~10-13 diem%) —
robustness den chu yeu tu cua so trailing DAI (200 ngay), giong tinh than MA200-BTC goc. Voi
MA200, **MOI to hop topN×nguong (6/6) deu ≥60%** cho UW-2025 (63.4-94.3%); voi MA100, 3/9 to hop
duoi 60% (topN=30/50/100, nguong=40-50%, gan bien). Cau hinh chinh (top50/MA200/50%) nam O GIUA
vung PASS, khong phai diem cuc bien — GO khong phu thuoc vao chon dung 1 tham so may man.

## 6. Ket luan cho MASTER

- **GO cho market-breadth-regime o cap do BAO PHU**: day la tin hieu regime DAU TIEN trong 6
  round breadth doc lap phu duoc CA HAI chuoi UW (2022 va 2025) qua nguong 60% bang MOT co che,
  xac nhan gia thuyet cua Uni rang breadth (do rong) la loai tin hieu khac voi huong-gia va co
  the "nhin thay" phan ky an duoi be mat gia BTC trong giai doan bull-nhieu 2025.
- **CAN TRONG kep truoc khi mo sim**: (i) breadth bao "not-up" RAT THUONG XUYEN o moi nam (55-100%)
  — day la thay doi hanh vi rat sau rong so voi MA200-BTC/trend-detector (13-33%/nam), chi phi
  CAGR tiem an co the LON; (ii) edge doc lap KHONG xac nhan "notup" la lenh xau — ROI van duong
  ro (1.99%, CI90 duoi 1.08%), loss_rate gan nhu khong doi, phi dong-thua con THAP hon `up` —
  nghia la mot gate/throttle dua tren breadth co the cat GIAM CA LENH TOT trong "notup", giong hoan
  toan mau hinh da thay o pacing (TASK B, "cat maxDD nhung khong cat duoc UW that/khong phan biet
  chat luong"). ⇒ **KHUYEN NGHI**: neu MASTER mo round sim moi, PHAI kiem tra ca hai — (a) UW that
  co giam khi ap breadth-gate khong (khong chi la bao phu-thoi-gian danh gia); (b) CAGR mat bao
  nhieu khi cat ca lenh tot trong notup (nguy co lon nhat theo edge doc lap o day).
- Day la huong breadth DUY NHAT con lai (theo de xuat tu chan doan UW-2025) da qua duoc cong bao
  phu — nhung "qua cong bao phu" KHONG dong nghia "se thanh cong trong sim" (edge chua ro).

## 7. Dau ra

`docs/PREREG_BREADTH_REGIME_DIAG.md` (`3536a2a`) + `research/analysis/breadth_regime.py` (moi,
tai dung nguyen van `trend_rank_ic.load_closes`/`bigdown_struct.load_trades_utc,
block_boot_mean, phi_for`) + `research/analysis/out/breadth_regime.json` + doc nay (commit theo
sau). 0-sim tuyet doi, dung `logging`, cam `print()`.
