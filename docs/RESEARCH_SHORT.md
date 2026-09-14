# RESEARCH_SHORT — Feasibility + Edge cua chien luoc SHORT (nguoc top-8 BUY)

Ngay: 2026-09-14. Che do: RECON (doc code) + PROBE (python offline).
KHONG build short infra, KHONG cham port 242, KHONG sua code logic, KHONG push.
Chi commit: doc nay + `research/analysis/probe_short_edge.py`.
Holdout 2026 nguyen ven (featv2 chi den 2024-07; probe = dev 2021-12..2024-07).

## 0. TL;DR / VERDICT
**KHONG dang build short duoi dang "mirror" cua top-8 BUY.**
Edge long la BAT DOI XUNG (pump-lottery: mean>median, thang nho duoi phai),
KHONG the soi guong thanh short edge. Coin diem cao nhat (dump-candidate) van
DRIFT LEN trung binh => short leg gross ~0%, sau cost 0.8%/lenh la LO chac o
moi horizon. Funding tailwind (+1 bp/ngay) qua nho de bu. Tail risk pump lon
(2.4% lenh end-ret > +20%; intra-path maxFav toi +243%) => 1x lev bi quet margin
khi gia +100%. Chi dang xem xet lai NEU muc tieu la market-neutral hedge (giam
beta) chu khong phai alpha short doc lap — va do la scope khac han.

## 1. RECON (doc code, khong doan)

### 1.1 Sim co short duoc khong?
- `OrderTargetInfoTest`: CON GIU field `side` (OrderSide) va `calTp()` DA CO nhanh
  SHORT: `if(side==SELL) tp = qty*(priceEntry - priceTP) - fee`. => Toan PnL short
  ton tai san.
- `SimulatorMarketLevelTicker1MStopLoss`: `createOrder(side,...)` DA parameter-hoa
  theo side (comment: "goi OrderSide.BUY -> byte-identical"). NHUNG tat ca CALL SITE
  chi goi `createOrderBUY(...)`. Nhanh ENTRY short (`createOrderSELL`) da bi GO
  2026-09-03 (comment L279: "co ENABLE_SHORT da go ... long-only"). Git history cho
  thay short tung duoc draft day du (df542c5 wire ENTRY short createOrderSELL,
  8d93f93 order-side SHORT flag-gated, short-export/WFO, "short alpha AUC 0.85")
  roi bi xoa loat (e43e213 "bo sell", 50a "delete all sell", 95c "delete sell").
- **Ket luan:** engine PnL da san sang 2 chieu; can build lai (i) wiring ENTRY short
  o selector (chon high-score thay vi low-score) + (ii) SL doi xung + (iii) funding sign.

### 1.2 Funding co duoc mo hinh khong?
- CO, nhung MAC DINH TAT: `Configs.APPLY_FUNDING_FEE=false` (chi bat qua
  SIM_APPLY_FUNDING=true; baseline runs KHONG tinh funding).
- `computeFundingOnClose()`: fee = Sum(rate(settle) x notional), notional=qty*avgEntry,
  quet settlement THAT trong (firstLegTime, close], KHONG look-ahead.
- Dau hien tai: rate>0 => long TRA => fee DUONG => calTp TRU. Co ban notional-mark
  (FUNDING_MARK_NOTIONAL) tich luy streaming moi tick.
- **SHORT funding = DRAFT PESSIMISTIC (BUG can sua neu build):** khoi "SHORT funding
  (DRAFT 2026-07-18)" trong `computeFundingOnClose` co REVIEW-POINT ghi ro: cong thuc
  `feeTotal=rate*notional` dung chung ca 2 side, va calTp(SELL) VAN TRU fee =>
  **short bi TRU khi funding duong** (mo hinh nhu chi phi). THUC TE Binance: short
  NHAN khi funding duong. => Neu build product phai DAO DAU feeTotal cho side==SELL.

### 1.3 Stop-loss hien tai (long) + can gi cho short
- `PreArmSlUtils`: hard SL pre-arm cham nguong bang `barLow <= entry*(1+preArmSl)`
  (preArmSl<0) => CHI DUNG cho LONG (theo bar.minPrice). Comment L30 xac nhan
  "doi xung cong arm dung maxPrice". Short can HAM GUONG: cham khi
  `barHigh >= entry*(1+|preArmSl|)`.
- `PRE_ARM_SL=0` mac dinh (tat); LOSER_TIME_STOP_HOURS=0 mac dinh. Ca hai bat qua env.
- Lev = 1x (`LEVERAGE_ORDER=1`) => short KHONG lo vo han ve mat ke toan (mat toi da
  100% notional khi gia x2), nhung +100% pump = quet sach margin. => short BAT BUOC
  can hard SL + mandatory cap (long chay duoc khong SL vi day la -X% co san; short
  KHONG the vi duoi phai vo han).

## 2. PROBE EDGE (offline, khong sim)
Nguon: `featv2/feat_v2.parquet` (hourly, 288 sym, 2021-02..2024-07) + S1 score
`ledger/pred_s1a2x1.parquet` (15-min, snap gio de join fwd) + tail-path
`ledger/path_labels.parquet` (maxFav 72h) + `cand_dev.parquet` (validate).
Forward return = trailing-ret dich ts (fwd_Xh(t)=trailing_ret(t+Xh)); VALIDATE:
corr 0.991 vs cand_dev.retEnd_72h. Mau: 774,148 obs / 4,595 decision-ts.
S1 score: DIEM CAO = dump-candidate (he BUY chon K coin score THAP nhat).

### 2.1 Bucket forward return (per-ts; SHORT pnl = -fwd)
| bucket (per-ts) | n | f24 | f72 | f168 | med72 |
|---|---|---|---|---|---|
| LONG top8 (low score) | 36,760 | +0.44% | +0.79% | +5.13% | -0.90% |
| MID | 700,628 | +0.57% | +1.06% | +3.96% | +0.59% |
| SHORT bot8 (high score) | 36,760 | +0.09% | -0.03% | +1.56% | +0.47% |
| ALL | 774,148 | +0.54% | +1.00% | +3.90% | +0.52% |

- LONG top8: mean f72 +0.79% >> median -0.90% => edge la RIGHT-TAIL (pump lottery).
- SHORT bot8: **fwd van gan 0 / DUONG** (median +0.47%). Coin diem cao nhat KHONG
  giam trung binh — chung van drift len theo thi truong.

### 2.2 Decile theo score (0=low..9=high), fwd ret
| qd | f24 | f72 | f168 |
|---|---|---|---|
|0(low)|+0.67%|+1.56%|+5.36%|
|5|+0.60%|+1.28%|+4.28%|
|8|+0.34%|+0.48%|+2.84%|
|9(high)|+0.22%|+0.32%|+2.37%|
- Don dieu giam nhung **TAT CA DUONG**: khong co vung fwd ret AM tuyet doi.
  Shorting decile te nhat = short cai van len +0.32%/72h.

### 2.3 IC / AUC (co du bao forward-DOWN khong?)
- Rank-IC (per-ts spearman score vs fwd): f24 +0.019, f72 +0.019, f168 -0.012.
  |IC| ~ 0.02 = gan NHIEU; dau khong on dinh theo horizon => KHONG phai predictor
  short dung doc lap.
- AUC score->P(f72<0) = 0.535; P(f72<-0.05)=0.523; P(f72<-0.20)=0.533. Deu ~0.5
  => rat yeu. (Doi chieu: long edge cung khong "manh" theo AUC — no song nho magnitude.)
- Long-short spread lowK-highK f72 = +0.83%/72h, t=6.47 (co y nghia thong ke) NHUNG
  win-frac chi 51.9% (nhinh hon tung dong xu) => spread song nho DO LON (right-tail
  long leg), KHONG phai hit-rate. **SHORT leg RIENG = +0.03% gross (~0).**

### 2.4 Short net edge sau cost (bot8, cost 0.8% round-trip)
| horizon | gross(=-fwd) | net(-0.8%) |
|---|---|---|
| 24h | -0.09% | **-0.89%** |
| 72h | +0.03% | **-0.77%** |
| 168h | -1.56% | **-2.36%** |
=> LO chac o moi horizon. Cost an het (va hon) gross ~0.

### 2.5 Funding tailwind (short NHAN khi funding>0)
- bot8 fund_sum_3d mean = +0.00031 => **+1.03 bps/ngay** short NHAN (neu sua dau dung).
- fund_last>0 chi 60.6% thoi diem; fund_sum_3d>0 chi 56.0% => **~44% ky short PHAI TRA**
  (funding flip am). ALL-universe fund_sum_3d +0.00063 (short-candidate co funding
  THAP hon trung binh — khong phai vung funding cao).
- +1 bp/ngay x ~3 ngay = +3 bps: qua nho so voi thieu hut 77-236 bps/lenh. Funding
  KHONG cuu duoc short.

### 2.6 Tail risk (pump nguoc short) — ly do BAT BUOC hard SL
- End-ret f72 > +20%: 2.43% lenh; > +50%: 0.06%; > +100%: 0.00%.
- Intra-path maxFav_h (72h): mean +6.75%, p95 +19.5%, p99 +34.2%, **max +243.6%**;
  > +20%: 4.58% lenh; > +50%: 0.15%; > +100%: 0.006%.
- Tai 1x lev: gia +100% = mat 100% margin (liquidation). Cac case p99 +34% da la
  -34% margin trong 1 lenh. Duoi phai vo han la ban chat rui ro short.

## 3. THIET KE SL de xuat (neu van build — KHONG code o day)
Vi duoi phai vo han + du lieu tail:
- **Parametric SL (guong PreArmSl):** dong khi `barHigh >= entry*(1+sl_pct)` voi
  sl_pct doi xung theo selRank (SL_ADAPT). De xuat sl_pct = +8%..+12% (rank manh chat
  hon). Con so tu tail: p95 maxFav +19.5% => SL +10% cat truoc phan lon pump vua.
- **MANDATORY hard cap:** dong BAT BUOC khi lo dat -100% margin, tuc tai 1x la
  gia = entry*2 (+100%). Nhung vi 0.006% case len > +100% va gap-risk, dat cap
  CUNG o **+50% gia** (= -50% margin) lam tran tuyet doi khong bao gio vuot, doc lap
  parametric SL. Time-stop guong (LOSER_TIME_STOP) cho cum chua arm.
- **Sizing:** vi tail nang, short size <= 1/2 long size, va cap concurrency rieng.
- **Funding sign FIX bat buoc** (muc 1.2) truoc moi backtest short co that.

## 4. VERDICT & scope build
**KHONG dang build short mirror bay gio.** Ly do (so lieu):
1. Short leg gross ~0% (h72 +0.03%), sau cost 0.8% => -0.77%..-2.36%/lenh: LO chac.
2. Khong co vung fwd-ret am (decile te nhat van +0.32%/72h): crypto drift len + pump
   lottery lam edge BAT DOI XUNG, khong mirror duoc.
3. IC ~0.02, AUC 0.535: tin hieu short gan nhu ngau nhien khi dung doc lap.
4. Funding tailwind +1 bp/ngay, 44% ky flip am: khong bu noi.
5. Tail pump nang (maxFav max +243%, 1x wipe tai +100%): rui ro cao doi lay EV am.

**Chi cannh xem xet neu doi muc tieu** sang MARKET-NEUTRAL / beta-hedge (short leg de
GIAM beta khi long chay), khong phai alpha short. Do la de tai khac (danh gia theo
drawdown/Sharpe ca danh muc, khong theo EV short leg) — can master quyet dinh truoc.

Neu VAN quyet build (scope toi thieu, moi cai deu can lam):
- ENTRY: wiring selector chon high-score (mirror TOPK) + createOrderSELL call-site.
- SL: parametric guong (barHigh) + mandatory cap +50% + time-stop guong (muc 3).
- FUNDING: dao dau feeTotal cho side==SELL + bat APPLY_FUNDING_FEE (short THUC nhan).
- SIZING/RISK: short size <= 1/2, concurrency cap rieng.
- BACKTEST tren dev x1 + parity-gate truoc; KHONG dung ket qua nay lam bang chung
  live (probe la dev-only, chua qua sim/gate/holdout).

## 5. Blocker / lech
- CLOSES_1H.bin format serialized (khong decode nhanh) => horizon 4h/12h KHONG do
  truc tiep; da dung 24h/72h/168h tu featv2 (validated) + maxFav 72h tu path_labels.
  4h/12h can decode closes neu master muon — chua lam (khong bia).
- Probe = DEV 2021-12..2024-07 (featv2 cap), CHUA cham holdout 2026, CHUA qua sim.
- Prior work da tung claim "short alpha AUC 0.85" (git a0e8cdb) — probe nay tren S1
  score hien tai KHONG tai lap duoc (AUC 0.535); claim cu co the tren feature/label
  khac (horizon 12h, proxy label) => neu master muon theo huong do can recon rieng
  cac short-kernel cu, ngoai scope lan nay.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_011zpgT8SsGrmcqzxbC93PQT
