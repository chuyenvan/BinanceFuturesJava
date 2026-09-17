# PREREG_PUMPDUMP_DETECT — chot thiet ke do tin hieu "pump xong chuan bi dump" (descriptive)

> **MO TA (descriptive) — KHONG chay sim, KHONG sua `.java`, KHONG push.**
> Chot TRUOC khi do de khong p-hack. Script `research/analysis/pumpdump_detect.py`.
> Thuc hien DUNG tai lieu nay. 2026-09-17.

## 0. BOI CANH

User: *"co huong nao detect duoc pump xong chuan bi dump khong, nhin bieu do thi thay de ma.
di kieu exit/SL/DCA chi la va vet thuong, xu ly goc hieu qua hon"*.

Truoc do:
- `docs/RESULT_POSTPUMP_MEASURE.md` (`058ecb5`): `mom30d` (momentum 30 ngay tai entry) **NULL** —
  CI chua 0, bucket khong don dieu, loc lam PnL rong XAU DI o ca 3 nguong.
- `docs/DIAG_ALT_IDIOSYNCRATIC_RISK.md` (`d02c7aa`): 49 lenh SUP (`profit <= -20%`) = 72% tong lo;
  R^2 voi BTC chi 2.2%. (Mau n=8 trong cua so UW dai nhat thay momentum 30d cao, nhung khong lap
  lai tren toan bo.)

Cau hoi o day hep hon mom30d: khong phai "momentum 30 ngay" ma la **extension NGAN (24h/72h)** +
**rollover tu dinh gan** + **gia toc** — nhung dau hieu "pump xong roi quay dau" gan voi thoi diem
vao lenh hon.

## 1. RECON DU LIEU (ket qua khao sat, xem chi tiet muc 8)

**CO OHLCV + volume khong? → CO.** Nguon:
- **`ticker_*.bin.gz`** (`/home/ubuntu/kaggle_data_hpo/`, 2008 file ngay): **OHLCV 1 phut**,
  Java-serialized `TreeMap<Long, HashMap<String, KlineObjectSimple>>`. `KlineObjectSimple` =
  `startTime(Long), priceOpen(F), maxPrice(F)=high, minPrice(F)=low, priceClose(F)=close,
  totalUsdt(F)=volume(quote)`. 1440 bar/ngay, **636 symbol**, **2021-01-01 .. 2026-07-01**.
  Da verify bang Java parser (BTCUSDT 2026-06-30: o/h/l/c/v = 60224.7/60224.7/60164.3/60188.0/7.14M).
- `CLOSES_1H.bin` (fsrun): close 1h, `[ts>i8, sym>i2, c>f4]` BE, 10,322,386 dong, 627 symbol,
  2021-01-01 08:00 .. 2026-01-01 07:00. (Dung boi cac bai truoc.)
- OI: `oi_percoin_full.bin` (`claudedata/oi/`, 4.2GB, 5m, `[ts>i8, sym>i2, oiDelta/z/lg/lt/takerBuy>f4]`,
  863 symbol). Funding rate **that**: KHONG co lich su (`funding.bin` la score selector 1-P(win));
  chi co **live** tu `derivs_store/` (funding.csv + oi.csv + lsr_*.csv, 5m, tu 2026-09-12).

**Quyet dinh do luong**: 4 detector D1-D4 (muc 2) **deu la close-based** → do tu **`CLOSES_1H.bin`**
(cung nguon voi postpump truoc, de so sanh truc tiep). OHLCV 1m (ticker) **khong dung trong lan nay**
vi detector da chot la close-based; no la nguon cho **follow-up** (body/wick/volume pattern) neu
4 detector nay NULL (xem muc 7).

## 2. CAC DETECTOR GIA THUYET (chot TRUOC, k=4, khong them sau)

Nhom (GIU NGUYEN nhu postpump): `SUP` = `profit <= -20` (n=49); `DOI_CHUNG` = con lai (n=1040).

| ID | ten | feature (tai entry, tu close 1h) | gia thuyet (huong) |
|---|---|---|---|
| D1 | extension-ngan | `ret_24h = c(t)/c(t-24h) - 1`; `ret_72h = c(t)/c(t-72h) - 1` | cang cao -> cang de SUP (mua dinh sau pump) |
| D2 | extension-vs-MA | `ext_ma7 = c(t)/MA7 - 1`; `ext_ma30 = c(t)/MA30 - 1` (MA_k = mean k close 1h gan nhat) | cang xa tren MA -> cang de SUP |
| D3 | rollover | `ddmag_72h = 1 - c(t)/max(close 72h)` (do sau tu dinh 72h, >= 0) | cang sau -> cang de SUP (quay dau tu dinh) |
| D4 | acceleration | `accel_24h = ret_24h - ret_24h_truoc` = `c(t)/c(t-24h) - c(t-24h)/c(t-48h)` | cang tang toc -> cang de SUP (blow-off) |

Tat ca deu "cang cao -> cang de SUP" (mot huong). 6 cot feature, 4 detector.

## 3. TIEU CHI KET LUAN (chot TRUOC)

Mot detector **DANG_THEO** neu **CA 3** dieu sau DUNG (tren cot feature chinh):
- **(a) monotone**: ti le SUP theo decile (10 bucket, rank-based) tang theo huong gia thuyet:
  Spearman rho(bucket, ti le SUP) **>= +0.7** VA ti le SUP decile-10 > decile-1.
- **(b) CI hieu mean (SUP - DOI_CHUNG) KHONG chua 0**: bootstrap block-72h, 2000 rep,
  seed `20260905`, **inflate x1.21** (như postpump). CI percentile 2.5/97.5 sau inflate.
- **(c) PnL rong >= 0** o **it nhat 1 nguong** trong bang danh doi (what-if, KHONG re-run):
  nguong p75/p90/p95 cua feature; `PnL rong = -(tong pnl cac lenh bi loc)` =
  `(lo SUP tranh duoc) - (lai bi mat)` >= 0.

**Khong dat ca 3 => NULL.** Neu dat: **KHONG tu ap dung**; chi de xuat pre-reg test trong sim,
noi ro nguong chon post-hoc + can holdout 2026.

## 4. BAO CAO (moi detector, dung 4 thu)

- (a) bang decile: ti le SUP, mean PnL, tong PnL theo bucket + Spearman rho + monotone T/F.
- (b) mean/median SUP vs DOI_CHUNG + CI bootstrap block-72h x1.21 (raw + inflated) + sd_boot.
- (c) bang danh doi what-if (p75/p90/p95): n lenh loc, n SUP (lo tranh USD), n LAI (lai mat USD),
  n lo-nhe, **PnL rong thay doi (USD)**.
- (d) so lenh NaN/khong do duoc (coin niem yet < lookback).

## 5. DU LIEU + PP (dung nhu postpump, khong doi)

- `printDone.csv` T170 (`/home/ubuntu/java/devrun/X1_GS_T170_2021/storage/`, n=1089).
- `CLOSES_1H.bin` + `/home/ubuntu/selector_pred_out/symbol_map.csv` (BTCUSDT=symId 1).
- Lookback bang gio: 24h=24 close, 72h=72 close, 7d=168, MA_k = mean k close.
- Bootstrap: block 72h; `t0 = min(ts)`; moi rep chon lai cac block; seed `20260905`; 2000 rep.
- CI inflate x1.21 quanh tam (percentile): `lo_i = c - (c-lo)*1.21; hi_i = c + (hi-c)*1.21`.

## 6. KET QUA MONG DOI (de biet minh co dang p-hack khong)

Tu postpump (mom30d NULL) va DIAG (mau n=8 khong lap lai), tien nghiem: **ca 4 deu NULL**.
Neu ca 4 NULL => ket luan "khong detect duoc bang close hien co", va **can data gi** (muc 7).

## 7. NEU NULL — CAN DU LIEU GI (ghi truoc, khong chon post-hoc)

- Pattern body/wick/volume ("nen xanh dai roi xuong", blow-off volume) can **OHLCV 1m** —
  **da co** (`ticker_*.bin.gz`). Neu can, follow-up se do truc tiep tu nguon nay (da verify parse).
- Funding rate **that** lich su: can tai tu `data.binance.vision` `monthly/fundingRate/<S>/`
  (2020-01..); hien chi co live `derivs_store/`.
- OI: da co (`oi_percoin_full.bin` 5m) — co the lam feature "OI surge truoc dump" o follow-up.

## 8. GIOI HAN (phai ghi)

- Close-only (detector close-based, do tu CLOSES_1H); khong dung high/low/volume trong lan nay.
- Lenh conditional (chi lenh he THUC SU vao), n_SUP=49 nho; decile ~5 SUP/decile.
- What-if (c) khong re-run, khong tinh tuong quan vi the/margin.
- CI chi cho (b), khong cho bang danh doi (c).

Co-Authored-By: Claude (subagent) — pre-reg truoc, khong push.
