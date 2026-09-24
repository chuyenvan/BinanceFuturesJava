# PREREG_PUMPDUMP_OHLCV — chot thiet ke do "pump xong chuan bi dump" bang OHLCV 1m + OI (descriptive)

> **MO TA (descriptive) — KHONG chay sim, KHONG sua `.java`, KHONG push.**
> Chot TRUOC khi do de khong p-hack. Day la **lan dau** dung thu "mat nguoi nhin" (than/bong nen + volume)
> thay cho close-only cua `docs/result/RESULT_PUMPDUMP_DETECT.md` (`edbbf91`).
> Script: `research/analysis/pumpdump_ohlcv.py`. Tool doc du lieu: `.../research/PumpDumpOhlcvExtract.java`
> (doc-only, them moi, khong sua logic trading). 2026-09-17.

## 0. BOI CANH

`RESULT_PUMPDUMP_DETECT` (commit `edbbf91`): 4 detector close-based (ret_24h/ret_72h, ext_ma7/ext_ma30,
ddmag_72h, accel_24h) tren toan bo 1089 lenh T170 deu **NULL**. Ly do goc: he vao lenh coin momentum
(mean profit +5.24%) nen "pump sap dump" va "pump sap con bay" KHONG tach duoc bang close tai entry.

User mo ta pattern bang "nhin bieu do": **than/bong nen + volume** ("nen xanh dai roi xuong", blow-off
volume, upper wick) + **OI phan ky**. Du lieu da co san (recon muc 8 cua result truoc):
- **`ticker_*.bin.gz`** (`/home/ubuntu/kaggle_data_hpo/`, 2008 file ngay): OHLCV 1 phut,
  Java-serialized `TreeMap<Long, Map<String, KlineObjectSimple>>`. `KlineObjectSimple{startTime(Long),
  priceOpen, maxPrice=high, minPrice=low, priceClose, totalUsdt=volume(quote)}`. 1440 bar/ngay,
  636 symbol, 2021-01-01 .. 2026-07-01. **Da verify parse** (Java parser: BTCUSDT 2026-06-30 bar dau
  O/H/L/C/V = 60224.7/60224.7/60164.3/60188.0/7.14M).
- **OI** `oi_percoin_full.bin` (`/home/ubuntu/claudedata/oi/`, 4.2GB, 5m, raw binary BE
  `long ts + short symId + 5x float` = 30B/record, 140,924,110 record, 863 symbol). 5 float =
  `oiDelta24h (OI(t)/OI(t-24h)-1), z(expanding), lsGlobal, lsToptrader, takerBuy`. **KHONG co raw OI**
  trong file — chi oiDelta24h + z. 2021-01-01 .. 2026-08.

**Quyet dinh**: do truc tiep tu `ticker_*.bin.gz` (OHLCV 1m) + `oi_percoin_full.bin` (OI). Khong dung
`CLOSES_1H.bin` o lan nay.

## 1. NGUON DOC DU LIEU (Buoc 1 — cong kha thi)

Repo **CO san** loader Java `KaggleDataLoader.loadObject()` doc `ticker_YYYYMMDD.bin.gz` (ObjectInputStream
+ GZIPInputStream → `TreeMap<Long, Map<String, KlineObjectSimple>>`). Tool moi
`PumpDumpOhlcvExtract.java` dung cung cach (doc truc tiep file .gz, KHONG qua Aerospike), va stream OI
file (DataInputStream, 30B/record). Convert **chi cac ngay/quanh moc vao lenh** (KHONG convert 2008 file).

- Tap = 49 lenh SUP + **200 DOI_CHUNG** (lay ngau nhien tu 1040 lenh con lai, **seed `20260917`**, ko lap).
  → 249 lenh. Voi moi lenh chi doc **30h OHLCV 1m truoc moc vao** (1800 bar) + **30h OI truoc moc vao**.
- Output (chi trong `/tmp`, KHONG commit): `ohlcv_1m.csv.gz` + `oi_5m.csv` (cot `tid, ts_ms, ...`).

## 2. Nhom (GIU NGUYEN nhu 2 bai truoc)

| nhom | dinh nghia | n |
|---|---|---|
| `SUP` | `profit <= -20` | **49** |
| `DOI_CHUNG` (DC) | lay 200 ngau nhien tu phan con lai (seed `20260917`) | **200** |

## 3. DETECTOR (chot TRUOC, k=4, mot feature moi detector)

Cua so causal = cac bar 1m **da dong** truoc moc vao: `startTime < entry_ts_ms`, trong
`[entry-30h, entry)`. `entry_ts_ms` = epoch ms UTC cua `start` (goc Asia/Ho_Chi_Minh), giong bai truoc.

Ky hieu: `c(t)` = close bar 1m cuoi cung co `startTime <= t`. `ret_K = c(t)/c(t-K) - 1` (fraction).

| ID | ten | feature (tai entry, causal) | gia thuyet (huong) |
|---|---|---|---|
| D1 | rejection / upper-wick 60m | `wick60 = max` over 60 bar cuoi cua `upper_wick_ratio = (high - max(open,close)) / (high-low)` (0 khi high==low) | cang cao → cang de SUP (nen "phun" o dinh) |
| D2 | volume blow-off | `volblow = max(vol5)` over 60 bar cuoi / `median(vol5)` over 24h truoc do; `vol5(i)=sum(totalUsdt)` 5 bar [i-4..i] | cang cao → cang de SUP (dinh volume roi tat) |
| D3 | OI vs gia phan ky 24h | `oi_px_div = oiDelta24h(entry) - (c(t)/c(t-24h) - 1)` (oiDelta24h tu OI file, fraction) | cang cao → cang de SUP (OI tang ma gia khong tang) |
| D4 | parabolic-then-stall | `stall = ret_6h - ret_15m` (ret_6h = 6h, ret_15m = 15m) | cang cao → cang de SUP (chay manh roi mat da) |

- Tat ca deu "cang cao → cang de SUP" (mot huong). 4 detector = 4 feature.
- **D3 ghi ro han che**: OI file chi chua `oiDelta24h` (OI thay doi **24h**), KHONG chua OI thay doi 1h/4h
  (z la z-score expanding, khong phai raw OI). ⇒ D3 dung horizon 24h thay vi 1h/4h nhu user mo ta.

### Nguong NaN (chot truoc)

| feature | can | NaN neu |
|---|---|---|
| D1 wick60 | >= 60 bar | N < 60 bar |
| D2 volblow | >= 60 bar gan nhat + 1440 bar baseline | N < 1500 bar hoac median baseline <= 0 |
| D3 oi_px_div | close(t), close(t-24h), oiDelta24h finite | thieu bat ky thanh phan nao |
| D4 stall | close(t), close(t-6h), close(t-15m) | N < 361 bar |

## 4. TIEU CHI KET LUAN (chot TRUOC — GIONG bai truoc de so sanh)

Mot detector **DANG_THEO** neu **CA 3**:
- **(a) monotone**: ti le SUP theo decile (10 bucket rank-based) tang theo huong: Spearman
  rho(bucket, ti le SUP) **>= +0.7** VA ti le SUP decile-10 > decile-1.
- **(b) CI hieu mean (SUP - DC) KHONG chua 0**: bootstrap block-72h, 2000 rep, seed `20260905`,
  inflate **x1.21** quanh tam; CI percentile 2.5/97.5 sau inflate khong chua 0.
- **(c) PnL rong >= 0** o **it nhat 1 nguong** (p75/p90/p95 cua feature; what-if KHONG re-run):
  `PnL rong = -(tong pnl lenh bi loc)` = (lo SUP tranh) - (lai mat) >= 0.

Khong dat ca 3 => **NULL**. Neu dat: **KHONG tu ap dung**; chi de xuat pre-reg test trong sim,
noi ro nguong chon post-hoc + can holdout 2026.

## 5. BAO CAO (moi detector, dung 4 thu nhu bai truoc)

- (a) bang decile 10 bucket: ti le SUP + Spearman rho + monotone T/F.
- (b) mean/median SUP vs DC + CI bootstrap block-72h x1.21 (raw + inflated) + sd_boot.
- (c) bang danh doi what-if p75/p90/p95: n loc, n SUP (lo tranh $), n LAI (lai mat $), n lo-nhe, **PnL rong (USD)**.
- (d) so lenh NaN/khong do duoc.

## 6. KY LUAT (da nhin ket qua truoc khi do — POST-HOC)

- **Multiplicity**: day la lan screen thu **2**; tong so detector da thu tich luy =
  **10** (6 close-based bai truoc + 4 OHLCV/OI bai nay). 4 feature o day chot truoc, khong them sau.
- Neu co detector dat: chi la **de xuat** pre-reg test trong sim + can **holdout 2026**; KHONG tu ap dung.
- **n_SUP = 49 nho** → power thap, CI rong; decile ~5 SUP/decile.

## 7. GIOI HAN (phai ghi)

- n_SUP=49 nho; DC = 200 ngau nhien (seed 20260917), khong phai toan bo 1040.
- **KHONG co funding rate lich su** (chi live `derivs_store/` tu 2026-09-12).
- What-if (c) KHONG re-run, KHONG tinh tuong quan vi the / margin / giai phong margin.
- CI chi cho (b) hieu mean, khong cho bang danh doi (c).
- D3 dung OI delta 24h (file khong chua OI 1h/4h / raw OI).
- OI 5m; moc "oiDelta24h tai entry" = snapshot 5m gan nhat `<= entry`.

Co-Authored-By: Claude (subagent) — pre-reg truoc, khong push.
