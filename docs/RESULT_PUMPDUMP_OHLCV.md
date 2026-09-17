# RESULT_PUMPDUMP_OHLCV — do 4 detector "pump xong chuan bi dump" bang OHLCV 1m + OI (descriptive)

> **MO TA (descriptive) — KHONG chay sim, KHONG sua `.java`, KHONG push.**
> Thuc hien dung `docs/PREREG_PUMPDUMP_OHLCV.md` (commit `df60077`). Lan dau do truc tiep
> **body/wick/volume (OHLCV 1m)** + **OI** thay cho close-only cua `RESULT_PUMPDUMP_DETECT.md`
> (`edbbf91`). Script `research/analysis/pumpdump_ohlcv.py` + tool doc-only
> `src/main/java/com/binance/chuyennd/research/PumpDumpOhlcvExtract.java`. 2026-09-17.

## 0. TOM TAT (doc nhanh)

**Ca 4 detector deu NULL.** Khong detector nao dat ca 3 tieu chi chot truoc (monotone rho>=0.7
VA CI hieu mean khong chua 0 VA PnL rong >= 0). Nhung khac voi bai close-only:

- **D1 (wick60) va D2 (volblow) dao dau** (rho AM -0.32 / -0.21): upper-wick dai va volume blow-off
  la tin hieu cua **lenh LAI** (momentum continuation), KHONG phai "sap dump".
- **D3 (OI phan ky 24h) va D4 (stall) dung huong nhung YEU**: rho +0.578 / +0.557 (duoi nguong 0.7),
  decile D1→D10 = 9.1→27.3% / 12→24%, va **PnL rong DUONG** o ca 3 nguong (lan dau tien, khong cat
  vao loi). Nhung CI hieu mean van **chua 0** (n_SUP=49 qua nho → power thap).

**Ket luan**: "pump xong chuan bi dump" **khong tach duoc** bang OHLCV 1m + OI tai entry, voi n=49 SUP.
Pattern candle "mat nguoi nhin" (nen phun, volume dinh) thuc ra la dac diem cua **lenh dang LAI**
(he momentum). Hai dau hieu duy nhat dung huong (OI phan ky, mat da) con qua yeu de dat nguong.

## 1. Nhom + doc du lieu

| nhom | dinh nghia | n |
|---|---|---|
| `SUP` | `profit <= -20` | **49** |
| `DOI_CHUNG` (DC) | 200 ngau nhien tu con lai (seed `20260917`) | **200** |

- **OHLCV 1m**: `ticker_*.bin.gz` → `PumpDumpOhlcvExtract.java` (doc-only) doc cac ngay quanh entry,
  chi convert **445,150 bar** (249 lenh x ~1800 bar, 30h truoc entry). KHONG convert het 2008 file.
- **OI 5m**: `oi_percoin_full.bin` (4.2GB) → stream 1 lan, loc 79,707 dong cho 249 lenh.
- Verify parse: BTCUSDT 2026-06-30 bar dau O/H/L/C/V = 60224.7/60224.7/60164.3/60188.0/7.14M (khop).

## 2. Bang ket qua 4 detector

| detector | feature | n NaN | rho decile | monotone | D1→D10 SUP% | CI infl (x1.21) hieu mean | excl0 | PnL rong >=0 (p75/p90/p95) | **ket luan** |
|---|---|---|---|---|---|---|---|---|---|
| D1 rejection | `wick60` | 0 | **-0.317** | ✗ | 20.0→12.0 | [-0.054, +0.021] | ✗ | ✓/✗/✗ | **NULL** |
| D2 blow-off | `volblow` | 3 | **-0.213** | ✗ | 32.0→12.0 | [-7.223, +3.036] | ✗ | ✗/✗/✗ | **NULL** |
| D3 OI divergence | `oi_px_div` | 29 | **+0.578** | ✗ | 9.1→27.3 | [-0.118, +0.690] | ✗ | ✓/✓/✓ | **NULL** |
| D4 stall | `stall` | 0 | **+0.557** | ✗ | 12.0→24.0 | [-0.012, +0.126] | ✗ | ✓/✓/✓ | **NULL** |

- `CI infl` = bootstrap block-72h (2000 rep, seed `20260905`) hieu mean (SUP - DC), inflate x1.21.
- `PnL rong >=0` = `-(tong pnl lenh bi loc)` tai nguong p75/p90/p95 (what-if, KHONG re-run).

## 3. (a) Ti le SUP theo decile (rank-based, 10 bucket)

| feature | D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | D9 | D10 | rho |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `wick60` | 20.0 | 28.0 | 20.0 | 20.0 | 8.0 | 16.7 | 28.0 | 28.0 | 16.0 | 12.0 | **-0.317** |
| `volblow` | 32.0 | 4.0 | 20.8 | 20.0 | 16.7 | 24.0 | 33.3 | 20.0 | 16.7 | 12.0 | **-0.213** |
| `oi_px_div` | 9.1 | 22.7 | 18.2 | 13.6 | 13.6 | 27.3 | 45.5 | 13.6 | 27.3 | 27.3 | **+0.578** |
| `stall` | 12.0 | 16.0 | 20.0 | 8.0 | 24.0 | 29.2 | 16.0 | 28.0 | 20.0 | 24.0 | **+0.557** |

- **D1/D2 dao dau**: SUP% giam khi upper-wick/volume-blowoff tang (D1 20→12%, D2 32→12%).
  Candle "phun" + volume dinh la tin hieu **continuation** (lenh LAI), KHONG phai dump.
- **D3/D4 dung huong nhung khong don dieu**: D1→D10 tang (9→27%, 12→24%) nhung decile lung tung o giua,
  rho chi ~0.56-0.58 (nguong chot 0.7).

## 4. (b) Hieu mean SUP - DC + CI bootstrap

| feature | SUP mean / median (n) | DC mean / median (n) | hieu mean | CI raw | **CI infl x1.21** | excl0 |
|---|---|---|---|---|---|---|
| `wick60` | 0.8294 / 0.8448 (49) | 0.8405 / 0.8420 (200) | -0.0112 | [-0.048, +0.015] | **[-0.054, +0.021]** | ✗ |
| `volblow` | 16.02 / 8.14 (49) | 18.19 / 6.79 (197) | -2.171 | [-6.33, +2.15] | **[-7.22, +3.04]** | ✗ |
| `oi_px_div` | 0.3582 / 0.0169 (48) | 0.1144 / -0.0204 (172) | +0.244 | [-0.048, +0.620] | **[-0.118, +0.690]** | ✗ |
| `stall` | -0.0306 / -0.0409 (49) | -0.0902 / -0.0584 (200) | +0.060 | [-0.000, +0.114] | **[-0.012, +0.126]** | ✗ |

- Hieu mean SUP - DC deu nho (sd_boot 0.016-2.08); n_SUP=49 qua nho → moi CI deu chua 0.
- D1/D2 hieu mean AM (SUP thap hon DC), xac nhan dao dau.

## 5. (c) Bang danh doi (what-if, KHONG re-run)

Loc bo lenh co `feature > nguong`. "PnL rong" = `-(tong pnl lenh bi loc)` = (lo SUP tranh) - (lai mat).

| feature | nguong | gia tri | lenh loc | SUP loc (lo tranh $) | LAI loc (lai mat $) | lo-nhe | **PnL rong (USD)** |
|---|---|---|---|---|---|---|---|
| `wick60` | p75 | 0.9006 | 62 | 9 (+6,039) | 47 (-5,243) | 6 | **+2,193** |
| | p90 | 0.9454 | 25 | 3 (+1,470) | 20 (-2,610) | 2 | **-815** |
| | p95 | 1.0000 | 0 | 0 (0) | 0 (0) | 0 | **0** |
| `volblow` | p75 | 16.04 | 62 | 7 (+3,826) | 53 (-7,406) | 2 | **-3,429** |
| | p90 | 44.13 | 25 | 3 (+1,239) | 20 (-2,393) | 2 | **-1,003** |
| | p95 | 56.44 | 13 | 2 (+788) | 10 (-991) | 1 | **-170** |
| `oi_px_div` | p75 | 0.0803 | 55 | 15 (+14,645) | 36 (-4,781) | 4 | **+10,782** |
| | p90 | 0.4267 | 22 | 6 (+5,988) | 15 (-2,942) | 1 | **+3,381** |
| | p95 | 0.7369 | 11 | 6 (+5,988) | 5 (-848) | 0 | **+5,140** |
| `stall` | p75 | -0.0056 | 62 | 15 (+16,869) | 42 (-5,471) | 5 | **+12,420** |
| | p90 | 0.0698 | 25 | 6 (+5,333) | 18 (-1,617) | 1 | **+4,031** |
| | p95 | 0.1363 | 13 | 5 (+4,561) | 8 (-619) | 0 | **+3,943** |

- **D1/D2**: loc cat vao **nhieu lenh LAI** hon lenh SUP → PnL rong am hoac gan 0 (xac nhan dao dau).
- **D3/D4**: lan dau tien PnL rong **duong** o ca 3 nguong (lo SUP tranh > lai mat). D4 p75 net
  +$12,420 (15 SUP tranh $16,869 vs 42 LAI mat $5,471). Nhung day **KHONG du** de dat tieu chi vi
  (a) khong don dieu va (b) CI chua 0.

## 6. (d) So lenh NaN/khong do duoc

| feature | n NaN | % | ghi chu |
|---|---|---|---|
| `wick60` | **0** | 0% | 60 bar 1m luon du |
| `volblow` | 3 | 1.2% | < 1500 bar (30h) hoac baseline volume = 0 |
| `oi_px_div` | **29** | 11.6% | oiDelta24h NaN (coin moi/khong du 24h OI) hoac thieu close 24h |
| `stall` | 0 | 0% | 6h+15m du |

## 7. KET LUAN

- **Ca 4 detector deu NULL** theo tieu chi chot truoc. Khong co bang chung "detect duoc pump sap dump"
  bang OHLCV 1m + OI tai entry, tren 49 lenh SUP.
- **Vi sao**: he vao lenh coin momentum, nen (i) upper-wick dai + volume blow-off la tin hieu **lenh LAI**
  (continuation), va (ii) hai dau hieu "phan ky" dung huong nhat (OI phan ky 24h, mat da 15m sau run-up)
  con qua yeu: rho 0.56-0.58 < 0.7 va CI chua 0 vi **n_SUP=49 nho → power thap**.
- **Diem moi so close-only**: D3/D4 la lan dau PnL rong what-if **duong** (loc khong cat vao loi nhu
  truoc), nhung chua du 3 tieu chi. => khong de xuat ap dung, khong chay sim.

## 8. Con thieu gi / huong tiep (NEU can, chi neu huong — khong chot con so)

- **n qua nho**: 49 lenh SUP khong du power. Can them lenh SUP (them nam 2026 holdout, hoac mo rong
  dinh nghia SUP/`profit <= -10`).
- **Funding rate lich su**: KHONG co (chi live tu 2026-09-12). "Dump truoc funding settlement" la
  mot goc kha thi nhung can tai `data.binance.vision` monthly fundingRate.
- **OI raw 1h/4h**: file `oi_percoin_full.bin` chi chua `oiDelta24h` + z (KHONG raw OI). Muon do
  "OI surge 1h/4h" can export lai OI raw tu Aerospike 226 hoac Vision.
- **Tach theo che do**: co the SUP chi tach duoc trong 1 regime (vd alt rieng le, xem
  `DIAG_ALT_IDIOSYNCRATIC_RISK.md`) — mau n=8 trc do khong lap lai, nhung chua thu tren OHLCV.

## 9. Gioi han (phai ghi)

- **POST-HOC / multiplicity**: day la screen thu 2; tong detector da thu tich luy = **10**
  (6 close-based + 4 OHLCV/OI). Neu co cai dat thi chi la de xuat pre-reg test trong sim + holdout 2026,
  KHONG tu ap dung.
- n_SUP=49 nho → power thap, CI rong; DC = 200 ngau nhien (khong phai toan bo 1040).
- KHONG co funding rate lich su. What-if (c) KHONG re-run, KHONG tinh tuong quan vi the / margin.
- CI chi cho (b) hieu mean, khong cho bang danh doi (c).
- D3 dung OI delta **24h** (file khong chua OI 1h/4h / raw OI); OI 5m.

Co-Authored-By: Claude (subagent) — phan tich mo ta, pre-reg truoc, khong push.
