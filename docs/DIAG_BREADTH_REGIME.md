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

## 8. Bước 5.3 (2026-09-21, giao bởi MASTER) — bổ sung định nghĩa B (BTC+ETH MA200 AND/OR) và C
(BTC-đơn MA200), tính TRONG CÙNG script/cửa sổ với A để so cạnh công bằng

Định nghĩa khoá TRƯỚC khi tính tại `docs/PREREG_BREADTH_REGIME_DIAG.md` §6. Chạy lại
`research/analysis/breadth_regime.py` (đã bổ sung phần "BUOC 5.3"), ghi đè
`research/analysis/out/breadth_regime.json` (thêm khoá `def_b_c`, `summary_a_b_c`; các khoá A cũ
giữ nguyên số — đã xác nhận `gate_verdict` (A) vẫn `92.74%/70.93%/GO=True` như §3, không đổi).

### 8.1 %ngày "yếu" mỗi năm — A vs B_AND vs B_OR vs C (BTC-đơn)

| Năm  | A (breadth top50) | B_AND (BTC∧ETH<MA200) | B_OR (BTC∨ETH<MA200) | C (BTC-đơn<MA200) |
|------|-------------------:|-----------------------:|-----------------------:|--------------------:|
| 2021 | 63.0%              | 6.5%                    | 35.3%                   | 35.3%                |
| 2022 | 100.0%             | 97.5%                   | 100.0%                  | 100.0%               |
| 2023 | 66.0%              | 19.2%                   | 22.5%                   | 19.5%                |
| 2024 | 55.2%              | 19.7%                   | 30.1%                   | 19.9%                |
| 2025 | 72.9%              | 24.1%                   | 57.5%                   | 26.8%                |

(ETH-đơn, chỉ mô tả — không dùng cho cổng: %yếu/năm 2021=6.5, 2022=97.5, 2023=22.2, 2024=29.8,
2025=54.8 — ETH "yếu" nhiều hơn BTC ở 2024/2025 nhưng vẫn không đủ để B_OR/B_AND qua cổng UW2025,
xem 8.2.)

### 8.2 CỔNG QUYẾT ĐỊNH — %phủ not-up 2 chuỗi UW, từng định nghĩa (ngưỡng ≥60% CẢ HAI)

| Định nghĩa | UW-2022 (248 ngày) | UW-2025 (227 ngày) | GATE (≥60% cả hai) |
|---|---:|---:|:---:|
| **A** — breadth top50/MA200/50% | **92.74%** | **70.93%** | **ĐẠT** |
| **B_AND** — BTC∧ETH < MA200 | 77.82% | **15.86%** | KHÔNG ĐẠT |
| **B_OR** — BTC∨ETH < MA200 | 84.27% | **52.42%** | KHÔNG ĐẠT (gần nhất trong nhóm B, vẫn dưới 60%) |
| **C** — BTC-đơn < MA200 | 84.27% | **15.86%** | KHÔNG ĐẠT |

**Nhận xét mấu chốt**: B_AND và C cho ra CÙNG %phủ UW-2025 (15.86%) — vì trong đúng cửa sổ
UW-2025 (2025-03-04→2025-10-16), BTC gần như luôn ở trên MA200 của chính nó (đúng như bối cảnh:
BTC +33% năm 2025), nên `not_up_BTC` gần như luôn False trong cửa sổ này ⇒ B_AND (cần CẢ HAI)
bị chặn bởi chính BTC, không "nhìn thấy" gì thêm từ ETH. B_OR nới điều kiện (chỉ cần MỘT trong
hai yếu) nên tăng lên 52.42% — ETH có yếu hơn trong giai đoạn này — nhưng NHÀNH VẪN chưa qua
ngưỡng 60%. Kết hợp BTC+ETH bằng MA200 hướng-giá (dù AND hay OR) **KHÔNG giải quyết được** đúng
điểm mù mà Bước 5.1 (SMA7/100-crossover BTC/ETH-OR, UW2025=32.6% not-up — xem PREREG_TREND_REGIME
_DIAG) đã gặp: mọi tổ hợp hướng-giá BTC+ETH (MA200 lẫn SMA-crossover) đều KHÔNG đủ 60% ở UW-2025.
Chỉ breadth (đo TRÊN 50 coin, không riêng BTC/ETH) làm được.

### 8.3 Edge độc lập (forward-return BTC, ROI T100) — B_AND / B_OR, để kiểm tín hiệu có nghĩa

- **Forward BTC return theo B_AND** (not_up n=598, up n=1047): fwd1d up=+0.159% notup=-0.020%;
  fwd7d up=+0.888% notup=+0.311%. Theo B_OR (not_up n=832, up n=813): fwd1d up=+0.108%
  notup=+0.081%; fwd7d up=+0.604% notup=+0.753%. Không như A (nơi "not-up" có forward-return CAO
  hơn "up", một phát hiện nghịch-hướng ở §4), ở B_AND forward-return "notup" THẤP hơn "up" (đúng
  hướng kỳ vọng của một detector hướng-giá thường), nhưng B_OR lại gần bằng/nghịch hướng nhẹ ở
  fwd7d — không đủ mạnh, và dù sao cả hai đều KHÔNG qua được cổng bao phủ ở 8.2.
- **ROI T100 theo B_AND** (n=706 "notup"): roi_mean=1.39% CI90[-0.16,2.80] (CHẠM 0, không dương
  rõ như A), loss_rate=17.56% (CAO hơn "up" 15.27%), phi_dong-thua=2.14 (cao hơn "up" 1.95) — B_AND
  là định nghĩa DUY NHẤT trong A/B/C có tín hiệu "notup = lệnh xấu hơn" ĐÚNG HƯỚNG (loss_rate và
  phi đều cao hơn "up"), NHƯNG lại là định nghĩa có %phủ UW-2025 THẤP NHẤT (15.86%, cùng C) — một
  sự đánh đổi: B_AND "chọn đúng lệnh xấu" nhưng "không phủ được thời gian" của UW-2025.
- **ROI T100 theo B_OR** (n=1105 "notup"): roi_mean=1.49% CI90[0.32,2.58] (dương rõ, không giống
  B_AND), loss_rate=16.38% (~bằng "up" 15.54%), phi=1.99 (~bằng "up" 2.04) — GIỐNG mẫu hình của A
  (không tách được lệnh xấu), và vẫn KHÔNG qua cổng UW-2025 (52.42% < 60%).

### 8.4 KẾT LUẬN A/B/C cho MASTER (cập nhật §6 cũ với B mới)

| Định nghĩa | UW2022 | UW2025 | GATE | Có nhận ra CẢ 2022 và 2025? |
|---|---:|---:|:---:|---|
| A — breadth top50/MA200/50% | 92.7% | 70.9% | **ĐẠT** | **CÓ** — duy nhất trong A/B/C |
| B_AND — BTC∧ETH<MA200 | 77.8% | 15.9% | KHÔNG | Không (mù 2025 như BTC-đơn) |
| B_OR — BTC∨ETH<MA200 | 84.3% | 52.4% | KHÔNG | Không (gần nhất, vẫn thiếu ~8 điểm%) |
| C — BTC-đơn<MA200 | 84.3% | 15.9% | KHÔNG | Không (như dự kiến, đây là baseline đã biết mù 2025) |

**Kết hợp BTC+ETH bằng hướng-giá (định nghĩa B, dù AND hay OR, dù MA200 "nguyên văn" ở đây hay
SMA7/100-crossover ở Bước 5.1) KHÔNG đủ để nhận ra giai đoạn giằng-co-2025** — ý (b) của Uni
("altcoin đi theo ETH ngược BTC") không tự nó giải quyết được vấn đề khi đo qua đúng 1 coin thứ
hai (ETH); phải mở rộng ra ĐỘ RỘNG toàn thị trường (ý (a), định nghĩa A, top-50 coin) mới bắt
được đúng phân kỳ "giá BTC/ETH vẫn tăng nhưng đa số altcoin vẫn yếu". Xác nhận lại kết luận §6 cũ:
**A là định nghĩa DUY NHẤT trong 3 (và duy nhất trong toàn bộ 7 round regime đã thử: MA200-BTC,
SMA-crossover BTC/ETH-OR, B_AND, B_OR, breadth) phủ được CẢ HAI chuỗi UW qua ngưỡng 60%.**
Các cảnh báo về edge độc lập ở §4/§8.3 (breadth "notup" không đánh dấu lệnh xấu rõ, chi phí CAGR
tiềm ẩn khi gate thật) vẫn giữ nguyên — bao phủ-thời-gian PASS không đồng nghĩa sẽ thành công
trong sim thật.

### 8.5 Đầu ra bổ sung

`research/analysis/breadth_regime.py` (đã sửa, thêm phần "BUOC 5.3" ở cuối `main()`, KHÔNG đụng
code A cũ) + `research/analysis/out/breadth_regime.json` (ghi đè, thêm khoá `def_b_c`/
`summary_a_b_c`) + `docs/PREREG_BREADTH_REGIME_DIAG.md` §6 (khoá định nghĩa B/C trước khi tính,
theo brief MASTER) + mục này. 0-sim tuyệt đối (không Java, không xgboost, không build).
