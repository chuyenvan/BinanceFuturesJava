# PREREG_FS — tien dang ky: tim FEATURE MOI cho selector S1

Chot luc: 2026-09-03, **TRUOC khi build hay do bat ky ung vien nao**. Commit cua file nay phai
co truoc moi commit ket qua (`docs/FS_RESULT.md`). Neu thu tu commit nguoc lai => toan bo ket qua
bi coi la VOID.

Ly do ton tai: `/home/ubuntu/feataudit/SELECTOR_FEATURES.md` (2026-09-03) do duoc rang buoc sau:
S1 bat **17.8%** tran oracle (edge5 +6.80% vs +38.34%) nhung mot feature don `vol_7d` tho bat
**19.8%**. Nghia la khoang trong 80% con lai **khong** phai du dia cua model tren bo feature nay
=> muon tien them phai co **thong tin MOI**. Job nay tra loi mot cau hoi duy nhat:

> **Co feature nao suy tu du lieu gia / khoi luong / funding ma bo 7 feature hien tai chua
> chua thong tin cua no, va do duoc?**

Cau tra loi "KHONG" la ket qua hop le va quan trong: no dong lai gia thuyet "bottleneck nam o
feature suy tu du lieu gia" va chuyen bottleneck sang lop du lieu khac.

Pham vi: **CHI DEV**. Duoc doc du lieu gia 2020-12..2024-06 de build feature; moi phep CHAM
chi tren tick OOS trong DEV (2022-01-01 .. 2024-06-30). **KHONG cham VALIDATION**
(2024-07-15..2025-12-31), **KHONG cham HOLDOUT 2026**. Khong chay java, khong backtest.
Duoc train lai S1 (python/GPU). Khong ghi de `ledger/pred_s1a2.parquet`, `predwf_map_s1a2/`,
`featv2/feat_v2.parquet`.

---

## 0. NEO NHAN QUA — do truoc khi chot pre-reg (chi la kiem du lieu, khong phai ket qua)

Nguon du lieu moi: `data.binance.vision`, `data/futures/um/monthly/klines/<SYM>/1h/`.
Cot: `open_time, open, high, low, close, volume, close_time, quote_volume, count,
taker_buy_volume, taker_buy_quote_volume, ignore`.

**Da do (khong doan):** `CLOSES_1H.bin[ts]` **bang close cua kline co `open_time = ts - 1h`**.
- BTCUSDT 2022-03: n=743, sai so tuong doi max **4.14e-08**, trung binh 2.20e-08.
- ETHUSDT 2023-08: n=743, max **3.59e-08**, trung binh 1.67e-08.
- Doi chieu voi gia thuyet nguoc (`open_time = ts`): sai so max **4.6e-02** / **5.8e-02** => sai.

=> **Luat nhan qua cua moi ung vien:** tai gio `t`, chi duoc dung cac bar co
`open_time <= t - 1h`. Bar `B_k` := kline co `open_time = t - k*1h`, `k = 1..K`; `B_1` dong dung
tai `t`. Cua so "7 ngay" = `B_1..B_168`. Feature tinh tai moc gio roi ffill sang tick 15m qua
`ts_h = floor(ts/3600000)*3600000` — **y het** cach `s1_rank.py:26,28` join feature hien tai
(feature co the cu toi 45 phut so voi thoi diem quyet dinh; lech theo huong **bao thu**).

Universe: **294 symbol** co mat trong `CLOSES_1H.bin` trong 2021-01..2024-07 (`symId` tu
`/home/ubuntu/selector_pred_out/symbol_map.csv`). Thang tai: 2020-12..2024-06 (2020-12 de du
lookback 720h truoc 2021-01).

**Unit test bat buoc truoc khi do:** lay 200 mau `(sym, t)` ngau nhien, **cat chuoi kline tai
`t - 1h`**, tinh lai 3 ung vien tu chuoi da cat, doi chieu voi bang => phai khop tuyet doi
(y phuong phap `feat_v2_build.py` muc V3(b) da dung cho 9 feature hien tai). FAIL => dung.

---

## 1. BO NEN (BASE) — chot cung

`BASE7 = ["vol_7d", "dd_7d", "rk_dd_7d", "hrs_since_high_7d", "ret_3d", "rk_ret_3d", "ret_14d"]`

Tuc **9 feature `KEEP` cua production tru 2 feature OI** (`ls_global`, `rk_oi_delta24h`).
Day dung la model `no_oi` cua feataudit muc C.6.

Ly do chon BASE7 chu khong phai BASE9 (chot truoc):
1. feataudit C.6 do duoc `no_oi` (7 feat) **khong phan biet duoc** voi bo 9 feature tren **ca 4
   chi tieu** (rank-IC/edge5 x g1lite/g1_replay), diem uoc luong edge5 con **cao hon 0.69pp**.
2. Hai feature OI dung tren du lieu **da chung minh ro ri 5 phut** voi moi `ts >= 2024-03-04`
   (`docs/OI_SCOPE_REPORT.md`) — 19.0% tick OOS bi nhiem. Dat ung vien canh mot base bi nhiem
   la tron hai nguon sai lech.
3. Toan bo thi nghiem tro thanh **khong can metrics** => bat ky ung vien thang cung mo duong lui
   DEV ve 2020-01 (`docs/DATA_EXTENT_SURVEY.md` muc 2: metrics chan cung o 2021-12-01,
   kline + funding co tu 2020-01).

Bao cao phu (khong dung trong luat quyet dinh): voi ung vien nao PASS, do lai
`Delta rankIC` khi them vao **BASE9** (du 9 feature production) de kiem tinh ben.

Moi thu khac giu **y nguyen** `research/pipeline/s1_rank.py`: `XGBRanker(objective="rank:ndcg",
n_estimators=300, max_depth=4, learning_rate=0.05, subsample=0.8, colsample_bytree=0.8,
min_child_weight=50, tree_method="hist", random_state=42, lambdarank_pair_method="topk",
lambdarank_num_pair_per_sample=8)`; 10 cutoff (`20220101, 20220401, ..., 20240401`, TZ +7h);
purge 72h; nhan `rel5` = ngu phan vi trong tick cua `g1lite - median(tick)`; pool =
`ledger/cand_dev.parquet` loc `g1lite.notna()`. `device="cuda"` chi doi backend tinh, khong doi
cau hinh; **phai** kiem tai lap truoc (muc 5).

---

## 2. DANH SACH UNG VIEN — DONG BANG, N = 16

Ky hieu: `c,o,h,l` = close/open/high/low cua bar; `v` = volume co so; `qv` = quote volume (USDT);
`n` = so lenh khop; `tbqv` = taker buy quote volume; `eps = 1e-12`. Moi trung binh/tong lay tren
`B_1..B_K` (lui, khong center). "Nguon" ghi ro co can `metrics` hay khong.

### Nhom A — THANH KHOAN / DOLLAR-VOLUME (lo trong duy nhat duoc ghi ten trong `SPEC_FEAT_V2.md`)

| # | Ten | Cong thuc | Cua so | Nguon | Gia thuyet kinh te: tai sao 7 feature hien tai KHONG chua thong tin nay |
|---|---|---|---|---|---|
| 1 | `fs_dvol_7d` | `log10(1 + mean(qv, B_1..B_168))` | 168h | kline 1h | Muc thanh khoan tuyet doi. Ca 7 feature hien tai den tu **gia**; `vol_7d` la **do lech chuan loi suat**, khong phai vong quay tien. Hai coin cung `vol_7d` nhung khac 100x turnover la hai the gioi khac nhau: coin mong bat 6% bang mot cu day nho roi khong co ai mua tiep, con exit trailing cua G1 can **theo duoi duoc** => thanh khoan quyet dinh cu bat 6% la cau hay la nhu cau that. Khong ham nao cua gia sinh ra duoc `qv`. |
| 2 | `fs_dvol_ratio` | `mean(qv, B_1..B_24) / max(eps, mean(qv, B_1..B_168))` | 168h | kline 1h | Su chu y / dong tien moi. Khoi lai kien thuc manh nhat dang co la `dd_7d` (sut gia 7 ngay): no biet coin **da roi bao sau** nhung **khong** biet **co ai dang mua day khong**. Ti so turnover 1 ngay tren 7 ngay la do luong truc tiep viec von moi dang chay vao, va vi la ti so cua hai khoi luong nen **truc giao voi gia theo cau truc** (khong mot bien doi nao cua chuoi close sinh ra duoc no). |
| 3 | `fs_amihud_7d` | `mean(abs(c/o - 1) / log10(1 + qv), B_1..B_168)` | 168h | kline 1h | Illiquidity Amihud (2002) = **tac dong gia tren moi don vi dong tien**. Coin co tac dong cao di xa voi it tien: bien do thuan loi lon hon **va** dao chieu nhanh hon — dung hai mat ma nhan `g1_replay` (arm 6% + trailing giveback) phan biet. Day la **ti so** gia/khoi luong: `vol_7d` co tu so, khong co mau so; `fs_dvol_7d` co mau so, khong co tu so. |
| 4 | `fs_trdsize_7d` | `log10(1 + mean(qv, B_1..B_168) / max(1, mean(n, B_1..B_168)))` | 168h | kline 1h | Co lenh trung binh tach **von lon** khoi **churn ban le**. Cung turnover nhung co ticket khac nhau 10 lan => nguoi giu khac nhau, nen su tiep dien sau cu bat dau khac nhau. `n` (so lenh khop) **khong** suy ra duoc tu gia lan tu khoi luong. |

### Nhom B — CARRY TU FUNDING (khong can metrics)

| # | Ten | Cong thuc | Cua so | Nguon | Gia thuyet kinh te |
|---|---|---|---|---|---|
| 5 | `fs_fund_sum_7d` | tong cac ky settle funding co `settle_ts` trong `(t-168h, t]` | 168h | Aerospike `funding_data` | Carry tich luy ma **long da tra** = do chen chuc cua vi the long don bay. Long chen chuc la nhien lieu cho chuoi thanh ly: hinh dang duong gia thanh "bat manh roi quay dau" — dung cai ma exit trailing bi phat. **S1 hien tai khong dung mot feature funding nao**: ca 5 feature funding trong `feat_v2.parquet` bi cat o buoc 40->9 va **ly do bi cat khong con tai lieu** (`PROCESS_LOG.md` khong ton tai — feataudit B.1). |
| 6 | `fs_fund_slope` | `mean(funding, (t-72h, t]) - mean(funding, (t-168h, t-72h])` | 168h | Aerospike `funding_data` | Gia toc cua carry: vi the **dang duoc dung len bay gio** so voi **dang tan ra**. Coin co funding chuyen tu am sang duong dang bi chen vao moi; **muc** funding khong phan biet duoc dieu do voi mot trang thai duong on dinh da lau. |
| 7 | `fs_fund_persist` | `sign(f_last) * min(21, so ky settle lien tiep cung dau voi ky moi nhat, quet lui)` | expanding, chan 21 ky (~7 ngay) | Aerospike `funding_data` | Do **ben** cua carry mot chieu = coin dang o che do dinh huong on dinh. Do lon va do ben la hai su that khac nhau: mot cu +0.05% khong giong hai muoi ky +0.005%. **Rui ro da khai bao:** o dau doi mot coin day co the la proxy cho tuoi; chan o 21 de gioi han (doi chieu `f23 fundingPersistence` cua G015 la ham tang theo lich — feataudit D.3.3). |

### Nhom C — MICROSTRUCTURE SUY TU KLINE (khong can metrics)

| # | Ten | Cong thuc | Cua so | Nguon | Gia thuyet kinh te |
|---|---|---|---|---|---|
| 8 | `fs_wick_up_7d` | `mean((h - max(o,c)) / max(h - l, eps), B_1..B_168)` | 168h | kline 1h | Ti le rau tren = **nguon cung hap thu cac cu bat**: nguoi ban danh vao bid khi gia manh. Day la dau vet **trong nen** cua hien tuong "bat len roi that bai", tuc dung coin arm duoc 6% trailing roi tra lai. S1 chi thay `close` nen **mu ve cau truc bac bo trong nen** — day khong phai "them mot bien the momentum", day la mot chieu du lieu chua he co. |
| 9 | `fs_body_ratio_7d` | `mean(abs(c - o) / max(h - l, eps), B_1..B_168)` | 168h | kline 1h | Ti le than nen = **hieu suat dinh huong** (xu the vs lang xang) o thang do gio. Hieu suat cao thi trailing stop da arm song sot; thap thi bi rung ra. Feature close-only thay **do dich chuyen rong** nhung khong thay **ma sat** da sinh ra no: hai coin cung `ret_3d` co the mot di thang, mot zigzag — `g1_replay` phan biet hai truong hop nay, `ret_3d` thi khong. |
| 10 | `fs_close_vwap_7d` | `c(t) / VWAP_168 - 1`, `VWAP_168 = sum(qv, B_1..B_168) / max(eps, sum(v, B_1..B_168))` | 168h | kline 1h | Khoang cach tu **gia von binh quan theo khoi luong** cua tuan qua = nguoi giu trung binh dang lai hay lo. Duoi VWAP la nguon cung bi ket phia tren, no chan cac cu bat; tren VWAP la khong khi trong. Day la ban **co trong so khoi luong** cua `dd_7d`, va **khong** lay duoc tu chuoi close khong trong so: dinh 7 ngay la mot diem, VWAP la ca phan bo giao dich. |
| 11 | `fs_taker_buy_7d` | `sum(tbqv, B_1..B_168) / max(eps, sum(qv, B_1..B_168))` | 168h | kline 1h | Ti le taker buy = **mat can bang dong lenh**: ai dang **chu dong** vao, khong chi gia ket thuc o dau. Mua chu dong ma chua day gia la tich luy; cung duong gia do voi ban chu dong la phan phoi. **Diem quan trong:** cot nay den tu **file kline**, nen khac feature `taker_buy` cua G015 (tu metrics), no **khong can metrics** va co tu 2020-01. |
| 12 | `fs_up_streak` | `min(24, so bar lien tiep co c > o, tinh lui tu B_1) / 24` | 24h | kline 1h | Do dai chuoi la mot **thong ke hinh dang**, khong phai do lon: k gio tang lien tiep bao mot chieu ap luc va su can suc ngan han theo cach ma `ret_3d` (dich chuyen rong) khong bieu dien duoc ma khong can rat nhieu lat cat cua cay. |

### Nhom D — CAU TRUC CUA CHINH DRAWDOWN (khoi manh nhat dang co)

| # | Ten | Cong thuc | Cua so | Nguon | Gia thuyet kinh te |
|---|---|---|---|---|---|
| 13 | `fs_dd_speed` | `dd7 / max(1, k*)` voi `dd7 = c(t)/max(c, B_1..B_168) - 1` (<=0) va `k*` = so gio ke tu bar dat max do (`1..168`) | 168h | kline 1h (close) | **Do sau tren moi gio** = van toc suy giam. Sup do nhanh (ban cuong buc) hoi lai; mai mon cham la phan phoi va tiep tuc. Do sau (`dd_7d`) va do dai (`hrs_since_high_7d`) **da co rieng le**, nhung **TI SO** cua chung la mot hinh dang khac han ma cay phai xap xi bang rat nhieu lat cat song song truc — va feataudit C.1 do duoc `hrs_since_high_7d` don le co `Delta rankIC = -0.0002` (khong phan biet duoc), tuc thong tin do dai **hien khong duoc dung**. |
| 14 | `fs_pos_7d` | `(c(t) - min(c, B_1..B_168)) / max(eps, max(c, B_1..B_168) - min(c, B_1..B_168))` | 168h | kline 1h (close) | Vi tri trong bien do 7 ngay = **bao nhieu phan cua drawdown DA duoc mua lai**. `dd_7d` khong phan biet duoc "con dang roi, sat day" voi "da bat 60% khoi day": truong hop sau **da chung minh** co nhu cau that. Ghi chu trung thuc: `pos_30d` co trong bo 40 tien-dang-ky va bi cat; `pos_7d` **chua tung ton tai**. |
| 15 | `fs_dd_term` | `dd30 - dd7`, `ddX = c(t)/max(c, B_1..B_{24X}) - 1` | 720h | kline 1h (close) | Cau truc ky han cua drawdown: tach **cu dip tuoi trong xu the thang thang** (`dd30 ~ dd7`) khoi **bear dai** (buc tranh 7 ngay trong yen binh nhung coin dang o rat xa dinh thang). Mot mot minh `dd_7d` khong mang duoc su phan biet nay; `ret_14d` mang mot phan **loi suat** nhung khong mang **khoang cach tot dinh**. |

### Nhom F — DOI CHUNG AM (bat buoc)

| # | Ten | Cong thuc | Cua so | Nguon | Vai tro |
|---|---|---|---|---|---|
| 16 | `fs_noise` | `U(0,1)` doc lap cho tung `(gio, symbol)`, `numpy.random.default_rng(20260903)` | — | — | **PHAI** ra "khong phan biet duoc". Cung phan phoi (deu [0,1], nhu moi feature `rk_*`), cung cau truc theo tick (mot gia tri cho moi cap gio-symbol). Neu no vuot nguong => **pipeline do SAI**: dung lai, sua, **khong bao cao ket qua nao khac**. |

**N = 16** (dem ca `fs_noise`, vi no cung la mot phep do).
`sqrt(2 * ln 16) = sqrt(5.545177) = **2.354820**`.

### 2b. HAI DOI CHUNG SAN DO (khong phai ung vien, khong duoc "thang")

- `ctrl_seed1`, `ctrl_seed7`: train lai **dung BASE7** voi `random_state = 1` va `7`, roi do
  `Delta rankIC` so voi BASE7 seed 42 y het cach do ung vien. Hai so nay them **ZERO** thong tin
  => chung do **san nhieu huan luyen** cua thuoc do.
- **Luat chot truoc:** neu `abs(Delta)` cua **mot trong hai** doi chung seed vuot nguong o muc 3,
  thi san do **cao hon** kich thuoc hieu ung can tim => bao cao **"khong do duoc"** cho toan bo
  bang ung vien, **khong** tuyen bo ung vien nao thang. Day la mot ket qua hop le.

### 2c. LOAI TRU CO CHU DICH — ghi de khong bi mo lai thanh "them ung vien sau khi xem so"

1. **Moi ung vien cross-sectional dang "gia tri cua coin tru trung vi/trung binh pool cung tick"
   deu bi LOAI, bang LY LE chu khong bang phep do.** S1 la ranker **trong tick**. Tru hoac chia
   cho mot hang so cua tick la bien doi **don dieu trong tick** => **dong nhat hang** => ranker
   khong nhin thay mot bit nao. Day dung la dong nhat toan hoc da lam `dd_7d == rk_dd_7d`
   (tuong quan hang trong tick = 1.000, feataudit C.2). Lop duy nhat co the them thong tin la
   mang **gia tri cap thi truong** vao nhu mot **muc** — va lop do **da do va that bai**:
   feataudit E6 / `AUDIT_APPLIED` B6 (14 dai luong gop cap thi truong => OOS **-0.1467**).
2. **Moi ung vien can `metrics` (OI / LS / taker tu metrics) bi LOAI khoi job nay.** Hai ly do:
   (i) 6 cot metrics **da chung minh** chua 5 phut tuong lai voi `ts >= 2024-03-04`
   (`OI_SCOPE_REPORT.md`) va **dang duoc mot agent khac sua** — do bay gio la do tren du lieu
   sap doi; (ii) uu tien thiet ke la ung vien **khong can metrics**, vi metrics chan DEV o
   2021-12-01 con kline+funding co tu 2020-01 (`DATA_EXTENT_SURVEY.md` muc 2).
   **He qua phai noi ro:** job nay **khong** tra loi duoc cau "OI co thong tin moi khong";
   cau do hoan lai sau khi sua OI.
3. **Khong them ung vien nao sau khi file nay duoc commit.** Voi N ung vien,
   `E[max nhieu] = sd * sqrt(2 ln N)`; them ung vien sau khi xem so la leak L2.

---

## 3. THUOC DO VA NGUONG — chot cung

### 3.1 Thuoc do chinh

`Delta rankIC(cand) = rankIC(BASE7 + cand) - rankIC(BASE7)`

— tuc **THEM** ung vien vao bo nen, **khong** phai rankIC don le cua ung vien. Ly do: cau hoi la
"co thong tin MOI khong", khong phai "feature nay co tuong quan voi nhan khong". Mot feature co
rankIC don le cao nhung trung voi `dd_7d` thi `Delta = 0` va dung la vo dung o day.

`rankIC` = trung binh **theo tick** cua `spearman(-score, outcome)` tren cac tick co **>= 10 dong**
(nguong 10 va huong `-score` — score THAP = TOT — lay y nguyen `PREREG_CI` muc 3.2 /
`gate_vs_rank3.py:18-19`).

### 3.2 Outcome: `g1_replay` la CHINH, `g1lite` la PHU

Day la **khuyen nghi #1 cua feataudit (muc E1)** va ly do phai ghi ro:

- `g1lite` va `maxFav_72h` **thuong cho bien do** => cham feature bang chung se chon ra
  "feature nao giong bien dong nhat". Da xay ra that: the he V2/V4/V5 (nhan `maxFav_72h >= 0.06`)
  bi `vol_3d`/`vol_7d`/`vol_30d`/`range_7d` chi phoi (feataudit B.1 dong 17:11).
- Bang chung dinh luong: xep coin **chi bang `vol_7d` tho** **thang** model 9 feature tren
  `g1lite` (`d = -0.0210`, CI72 `[-0.0374, -0.0045]`, loai 0 o ca 3 do dai block) va tren
  `maxFav_72h` (`-0.0502`, loai 0) — nhung **ngang nhau** tren `g1_replay` va **thua** tren
  `retEnd_72h` (feataudit C.4).
- Tren `g1_replay` (mo phong dung luat exit G1: arm 6%, trailing giveback), dong gop cua
  `vol_7d` **tan** (`+0.0009`, CI `[-0.0064, +0.0079]`, chua 0) va cap momentum 3 ngay tro thanh
  **co hai** (`-0.0050`, CI `[-0.0096, -0.0006]`, loai 0) — hai ket luan **chi hien ra** khi doi
  thuoc (feataudit C.5).
- **Nhan TRAIN khong doi**: van la `rel5` tu `g1lite`, vi A11 (`AUDIT_APPLIED:70`) da do tuong
  quan voi ROI that: `g1lite 0.584 > maxFav 0.574 > g1_replay 0.507`. Doi thuoc **danh gia**,
  khong doi nhan **train**.

Nguon `g1_replay`: `/home/ubuntu/ledger/path_labels.parquet`, inner-join `ts+sym`,
`dropna(g1_replay)` — y het `research/analysis/gate_vs_rank3.py:7-13`.

### 3.3 CI

Block-bootstrap theo `docs/PREREG_CI.md` muc 3:
- `block_id = floor((ts - ts_min) / L)`; **L chinh = 72h**, kiem do ben o **24h** va **168h**.
- `N_REP = 2000`, `SEED = 20260903`, `numpy.random.default_rng(SEED)`, resample lai tu seed do
  cho tung (ung vien, do dai block).
- CI95 = **phan vi 2.5 / 97.5** cua phan bo bootstrap **cua HIEU** `Delta`, **khong** BCa.
- **Ghep cap bat buoc**: mot lan resample sinh MOT danh sach block, dung **y nguyen** cho ca hai
  nhanh (BASE7 va BASE7+cand); CI la CI cua `Delta`. Cam so hai CI rieng roi xem co chong nhau.
- Tinh truoc thong ke **theo tick** (`ic_base`, `ic_cand`, `n_rows`, `block_id`) roi resample
  block — cho ket qua giong bootstrap tho tren dong ma khong tinh lai spearman 2000 lan
  (`PREREG_CI` 3.2).
- Bao cao them: `sd(Delta)`, `P(Delta > 0)`, `n_eff` = so block.

### 3.4 Nguong CHAP NHAN — hieu chinh so sanh boi

Voi `N = 16`: `sqrt(2 ln N) = **2.354820**`.

Ung vien duoc goi **PASS** khi thoa **CA BA**:

- **(T1)** `Delta rankIC > 0` tren **`g1_replay`**, tren cua so **SELECT** (muc 4).
- **(T2)** `abs(Delta) >= 2.354820 * sd_boot(Delta, block 72h, SELECT)`.
- **(T3)** CI95 cua `Delta` **khong chua 0** o **ca ba** do dai block (72h, 24h, 168h) tren SELECT
  — dung chuan **"SONG"** cua `PREREG_CI` muc 4.

Ghi chu doc so: (T2) nghiem ngat hon CI95 thuong (2.3548 so voi 1.95996, tuc rong hon **1.20 lan**);
do la gia phai tra cho viec thu 16 ung vien. (T3) doc lap voi (T2) va cam viec chon do dai block
cho ra ket luan mong muon.

`g1lite` duoc bao cao day du **song song** nhung **khong** vao luat quyet dinh. Muc dich: mot ung
vien PASS tren `g1lite` ma FAIL tren `g1_replay` chinh la dau van tay cua vol-confound, va do la
mot thong tin can bao cao chu khong phai can an.

---

## 4. XAC NHAN TACH ROI — chot truoc

`s1_rank.py` co 10 fold; fold `i` co OOS = `[cut_i, cut_i + 3 thang)`.

| Cua so | Fold | Khoang thoi gian | Vai tro |
|---|---|---|---|
| **SELECT** | 0..7 | 2022-01-01 .. 2023-12-31 | chon ung vien, ap nguong muc 3.4 |
| **CONFIRM** | 8..9 | 2024-01-01 .. 2024-06-30 | xac nhan, **khong** duoc xem truoc khi SELECT xong |

Ca hai nam **trong DEV**. **KHONG dung VALIDATION** cho bat ky muc dich nao trong job nay.
Mot lan train moi nhanh sinh du doan cho ca 10 fold; SELECT/CONFIRM chi la hai tap tick khac nhau
cua cung du doan do => khong co train them, khong co bac tu do them.

**CONFIRMED** khi: ung vien **PASS** o SELECT (muc 3.4) **va** tren CONFIRM co
(i) `Delta` **cung dau** voi SELECT, **va** (ii) CI95 cua `Delta` o block **72h** **khong chua 0**.

CONFIRM co khoang **60 block 72h** (182 ngay) nen cong suat thap hon SELECT; vi vay o CONFIRM
**khong** ap thua so `sqrt(2 ln N)` (chi con vai ung vien song, va day la buoc xac nhan chu khong
phai buoc chon). Dieu nay duoc chot **truoc** khi thay so.

Ung vien PASS o SELECT ma **FAIL** o CONFIRM duoc ghi la **PASS-KHONG-XAC-NHAN** va **khong**
duoc de xuat ap dung.

---

## 5. TAI LAP TRUOC KHI DO — dieu kien tien quyet

Truoc bat ky phep do nao: train lai S1 bang **dung 9 feature `KEEP`** va dung `s1_rank.py`, roi
doi chieu voi artifact dang chay `ledger/pred_s1a2.parquet`:

- Yeu cau: `spearman(pred_moi, -score_cua_pred_s1a2) >= 0.999` tren toan bo dong chung
  (feataudit dat **1.0000** tren 774,270 dong), va `edge5 g1lite` khop `+6.80%` trong `+-0.05pp`.
- Neu chay GPU (`device="cuda"`): phai **kiem them** rang ban CPU va ban GPU cho
  `spearman >= 0.999` voi nhau. Neu khong dat => **do bang CPU**, khong doi tieu chi cho khop.
- FAIL => **dung**, ghi "khong tai lap duoc", khong bao cao so so sanh nao.

---

## 6. CACH DOC KET QUA — chot truoc, gom ca truong hop "khong ai thang"

| Truong hop | Dieu kien | Ket luan phai viet |
|---|---|---|
| **(a) CO THONG TIN MOI** | >= 1 ung vien **CONFIRMED** | Bo 7 feature hien tai **khong** vet can thong tin suy tu gia/khoi luong/funding. Bao cao ro: ung vien nao, `Delta` bao nhieu, **co can metrics khong** (neu khong can => mo duong lui DEV ve 2020-01: `T_dev` 2.50 -> 4.50 nam, `MDE80` selector 12.46pp -> 9.28pp). **Khong** tu dong ap dung: viec ap dung can mot pre-reg rieng, vi tang quyet dinh cuoi (`maxDD <= 15%`) chi do duoc bang equity va tang do **can 43 nam** (`CI_REAUDIT` iii). |
| **(b) CHI THANG TREN `g1lite`** | >= 1 ung vien vuot nguong tren `g1lite` nhung **khong** ung vien nao PASS tren `g1_replay` | Day la **dau van tay vol-confound**, khong phai thong tin moi. Phai viet thang: ung vien do chi giup **doan dung nhan**, chua chung minh giup **kiem tien**. **KHONG de xuat ap dung.** Dong thoi la bang chung xac nhan khuyen nghi E1 cua feataudit (doi thuoc cham) la dung. |
| **(c) KHONG AI THANG** | Khong ung vien nao PASS tren ca `g1_replay` lan `g1lite` | **Ket qua hop le va quan trong.** No noi: khoang trong 80% toi tran oracle **khong** nam o feature suy tu du lieu **gia / khoi luong / funding** o thang gio. Bottleneck phai nam o (i) **lop du lieu khac** (order book, trade-by-trade, cross-exchange, on-chain) — chinh la ket luan cua B6; hoac (ii) **cach dat bai toan** (khong phai "chon coin nao" ma "vao luc nao / thoat the nao"); hoac (iii) tran oracle 38.34% ban chat **khong dat toi duoc** vi phan lon no la nhieu khong du bao duoc. De xuat tiep theo phai ra khoi tang feature-tu-gia. |
| **(d) KHONG DO DUOC** | Mot trong hai doi chung seed (`ctrl_seed1`/`ctrl_seed7`) vuot nguong muc 3.4 | San nhieu huan luyen cao hon kich thuoc hieu ung can tim. Bao cao **"khong do duoc"** cho ca bang; khong tuyen bo ai thang. Ghi ro san do la bao nhieu de lan sau biet can bao nhieu du lieu / bao nhieu seed averaging. |
| **(e) PIPELINE SAI** | `fs_noise` vuot nguong muc 3.4 | **DUNG NGAY.** Khong bao cao ket qua nao khac. Sua pipeline, do lai tu dau. |

Thu tu doc: (e) truoc, roi (d), roi (a)/(b)/(c).

---

## 7. THU TU THUC HIEN — bat buoc

1. Commit file nay. Ghi lai commit hash.
2. Tai du lieu kline 1h (chi thang can), build `/home/ubuntu/fs/feat_fs.parquet`, chay unit test
   nhan qua muc 0. FAIL => dung.
3. Tai lap S1 theo muc 5. FAIL => dung.
4. Do doi chung am `fs_noise` va hai doi chung seed. Theo luat (e)/(d).
5. Do 16 ung vien, moi diem ket qua ghi **1 dong jsonl + `fsync` ngay** (Kaggle kill 12h —
   `docs/KAGGLE_RULES.md` muc 2).
6. Viet `docs/FS_RESULT.md` theo dung 5 truong hop muc 6.

## 8. NHUNG GI PRE-REG NAY KHONG LAM

- Khong ap dung feature nao vao production. Ket qua toi da la "de nghi pre-reg mot lan ap dung".
- Khong tra loi cau OI (loai tru co chu dich, muc 2c.2).
- Khong cham `docs/PREREG_GS.md`, `/home/ubuntu/gs/`, `/home/ubuntu/g015/`, `/home/ubuntu/tick/`,
  `/home/ubuntu/feataudit/`, `/home/ubuntu/java/devrun/`.
- Khong sua `docs/PREREG_*.md` cua nguoi khac.
- Khong train G015, khong chay java, khong backtest, khong `git push`.
