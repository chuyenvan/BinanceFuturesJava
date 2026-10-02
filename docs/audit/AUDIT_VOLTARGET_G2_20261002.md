# AUDIT doi khang — RESULT_VOLTARGET_G2 (commit b452d8b3)

Doi tuong: `docs/result/RESULT_VOLTARGET_G2.md` + `voltarget_g2.json`, pre-reg `PREREG_VOLTARGET_G2.md` (md5 24369f25) + `AMEND1` (commit ecae6ef, TRUOC result), driver `research/analysis/voltarget_g2_driver.py`, Kaggle out `~/kaggle_sim/out/vt-g2-{b0,coin}` + baseline `de-p1`.
0-sim, chi doc artifact da co. Script: `research/analysis/voltarget_g2_audit.py` -> `docs/audit/AUDIT_VOLTARGET_G2_20261002.json`. DEV <= 2025-12-30, khong cham 242/shadow/2026.

## 0. Ket luan (rui ro truoc)

1. **Verdict NULL ("VT ≈ B0") DUNG VUNG** duoi moi thuoc thu: CI cua thuoc chinh thuc (±50 Calmar) VO LUC, nhung ca 3 thuoc thay the (ghep cap theo lenh co leverage-match, bootstrap return ngay ghep cap, hoi quy alpha/beta) deu cho CI chua 0. Khong co arm nao duoc nang/ha cap.
2. **Dien giai "chi cat don bay" DUNG ve phia LOI NHUAN, SAI NHE ve phia RUI RO.** Bang chung so: beta ngay 0.728, R² 0.972, alpha +1.03%/nam CI [-0.39, +2.69]; Spearman(multiplier VT, profit% lenh) = +0.026; multiplier TB 0.78, 83% lenh m<1 (G2 chon coin vol cao hon SIGMA_REF = trung vi universe => COIN mode CO CAU TRUC la de-lever). NHUNG lap luan so trong RESULT ("~1.8pp CAGR / 1pp maxDD = dung ti le Calmar B0 1.94 => tuong duong cat leverage") dung moc so sai: cat leverage THUAN tren B0 (co compound) lam Calmar GIAM (1.94 -> ~1.87-1.88 MTM, 3.43 -> 3.30-3.33 ngay), nen COIN 1.99 la **+6..7% (MTM) / +17% (ngay) tren B0 cung exposure** — diem uoc luong co loi ich rui ro (DD thap hon ~10-17% o cung CAGR/exposure), KHONG co y nghia (P(dCalmar>0) ~0.89-0.91, CI chua 0).
3. **Thuoc ΔCalmar block-72h trong driver vo luc VA lech thong ke**: bootstrap tinh Calmar tren ledger CLOSED-PnL cong don khong compound (CAP0 35k co dinh, maxDD closed) trong khi diem quan sat la Calmar MTM-phut compound => CI [-48.5, +74.7] cho mot dai luong ~2; inflate quanh TAM CI chu khong quanh obs. Ket luan NULL khong doi vi CI raw da chua 0, nhung con so CI khong dung de bao "khong co loi ich".
4. **Thuoc ghep cap theo lenh cua AUDIT_LONG_LEVERS (size-neutral) MU voi lever sizing BAN CHAT**: dPnL_size_neutral = (p_a − p_b)·N_b chi do tac dung phu len exit/tap lenh (2.8% lenh khop doi profit, 49 lenh doi cho). Khong dung de cham VT. Ban khong size-neutral = do luong size cat (-35k, co y nghia, vo nghia ve kinh te). Thuoc dung = leverage-matched (muc 2).
5. **Tuan thu pre-reg: PASS.** jar sha 7368be46 ca 3 run; profile_hash B0 = de-p1 = c47b73f3; COIN chi them dung 1 key `SIZE_VOL_TARGET_MODE=COIN` (diff prof_run.properties); md5 printDone B0 = de-p1 = g2flat3-val = 650c386f; COIN 137c886a; hang so COIN (SIGMA_REF 0.010657, clamp [0.5,2], 168h/minp 84) khop PREREG_VOL_TARGET. Causal COIN kiem: CLOSES_1H ts = CLOSE time (closes1h_build.py:10-12), lookup tai floor(t/1h) => nen da dong, KHONG leak.
6. **VT_PORT "blocked" = that, nhung la rang buoc NHIEM VU, khong phai ky thuat**: `VolTargetSizing.java:66` `public static final float PORTFOLIO_TARGET_ANNUAL_VOL = 0.25f;` (dung o :185), khong qua Cfg => doi = sua 1 dong + build jar + parity B0. Rui ro chua duoc neu du: ngay ca khi doi target, cong thuc sigma_equity_20d tren chien luoc "bursty" (rolling-20d p10≈0) day multiplier len clamp 2.0 sau cac cua so phang => thiet ke PORTFOLIO co loi cau truc, khong chi hang so.
7. Nho/bao cao hoi qua loi: "n khong doi => cach ly sach" — n bang nhau nhung 49/2517 lenh (1.9%) KHAC (sym/start/level), 69 lenh khop doi profit%. Tac dung phu do duoc = -1.0k USDT CI [-4.7k, +1.9k] => khong dang ke, nhung khong phai "sach" tuyet doi.

## 1. Equity/MTM (b+unP NGAY tu logs/sim.out, 1644 ngay; maxDD phut tu cache MTM cua driver)

| arm | CAGR % | maxDD ngay % | Calmar ngay | maxDD MTM-phut % | Calmar_MTM | UW max (ngay) | Sharpe | Sortino | vol nam % | exposure TB (gross/equity) |
|---|---|---|---|---|---|---|---|---|---|---|
| B0 | 34.31 | -10.02 | 3.43 | -17.68 | 1.940 | 86 | 2.292 | 1.827 | 13.25 | 3.57% |
| VT_COIN | 25.45 | -6.55 | 3.89 | -12.77 | 1.993 | 82 | 2.365 | 1.930 | 9.79 | 2.80% |

Ti le exposure COIN/B0: 0.786 (gross ngay) / 0.746 (theo lenh, N/E) ; vol 0.739 ; beta 0.728.

### B0 scale tuyen tinh (r'_t = c·r_t, compound) — "cat don bay thuan"

| c (cach chon) | c | CAGR | maxDD ngay | Calmar ngay | maxDD phut ~ | Calmar_MTM ~ | dCalmar ngay COIN− | dCalmar_MTM COIN− |
|---|---|---|---|---|---|---|---|---|
| exposure ngay | 0.786 | 26.28 | -7.90 | 3.33 | -13.94 | 1.885 | +0.56 | +0.108 |
| exposure lenh | 0.746 | 24.83 | -7.50 | 3.31 | -13.24 | 1.875 | +0.58 | +0.118 |
| vol | 0.739 | 24.56 | -7.43 | 3.31 | -13.11 | 1.873 | +0.58 | +0.120 |
| beta | 0.728 | 24.17 | -7.32 | 3.30 | -12.93 | 1.870 | +0.58 | +0.123 |
| khop CAGR | 0.764 | 25.45 | -7.67 | 3.32 | -13.55 | 1.879 | +0.57 | +0.114 |
| khop maxDD ngay | 0.651 | 21.39 | -6.55 | 3.27 | -11.56 | 1.850 | +0.62 | +0.143 |

(maxDD phut cua B0×c xap xi = -17.68 × ddNgay(B0×c)/ddNgay(B0) — tuyen tinh theo c; KHONG bootstrap duoc o muc phut vi khong co duong MTM phut cua B0×c.)
Luu y: ti so DD phut/ngay cua COIN (1.95) > B0 (1.77) => loi the cua COIN co lai o muc phut (+17% ngay -> +6% MTM): VT khong giam duoc swing trong ngay tuong xung.

### Paired circular block-bootstrap return NGAY (block 10 ngay, NREP 2000, seed 20260905, KHONG inflate)

| so voi | c | dCalmar ngay obs | CI95 | P(>0) | dCAGR obs [CI] | dMaxDD obs [CI] | d mean-ret nam [CI] |
|---|---|---|---|---|---|---|---|
| B0 tho | 1.000 | +0.46 | [-0.96, +0.97] | 0.85 | -8.86 [-14.25, -4.27] | +3.46 [+0.95, +6.21] | -7.22 [-10.64, -3.97] |
| B0×exposure | 0.786 | +0.56 | [-0.71, +1.11] | 0.89 | -0.83 [-2.92, +1.38] | +1.35 [-0.20, +3.00] | -0.72 [-2.35, +1.03] |
| B0×beta | 0.728 | +0.58 | [-0.65, +1.17] | 0.90 | +1.28 [-0.49, +3.35] | +0.77 [-0.54, +2.09] | +1.03 [-0.39, +2.69] |
| B0×khop CAGR | 0.764 | +0.57 | [-0.69, +1.14] | 0.90 | -0.01 [-1.92, +2.09] | +1.12 [-0.33, +2.65] | -0.04 [-1.56, +1.65] |
| B0×khop DD | 0.651 | +0.62 | [-0.56, +1.23] | 0.91 | +4.06 [+2.09, +6.64]* | 0.00 [-1.10, +0.98] | +3.39 [+1.83, +5.29]* |

\* khop-DD: c chon tu 1 diem maxDD thuc hien (nhieu) va c < beta => ΔCAGR duong la co hoc (COIN mang beta 0.728 > 0.651), KHONG phai bang chung alpha. Thuoc cong bang = beta/khop-CAGR: moi CI chua 0.
=> Ngay ca thuoc ngay (hep hon thuoc chinh thuc ~50 lan) van NULL; voi inflate k=3 (1.48) con rong hon.

## 2. Thuoc ghep cap theo lenh (khop sym|start|level; block-72h theo gio vao, K=125, NREP 2000, seed 20260905)

Khop: 2468 chung, 49 chi-B0, 49 chi-COIN; 2.8% lenh chung doi profit%.

| thuoc | dai luong | obs | CI95 | chua 0 |
|---|---|---|---|---|
| P1 size-neutral (dung cong thuc long_levers_paired_ruler) | USDT | -1 034 | [-4 685, +1 892] | CO |
| P2 KHONG size-neutral (profit%·notional moi phia) | USDT | -35 244 | [-52 171, -20 041] | KHONG (= size cat) |
| P3 leverage-matched, chuan hoa equity: Σ(g_a − c·g_b), c = exposure lenh 0.746 | %equity | +2.42 | [-3.53, +8.65] | CO |
| P3, c = multiplier TB 0.780 | %equity | -2.16 | [-8.67, +4.56] | CO |
| P3, c = OLS qua goc 0.662 (fit tren ket qua — KHONG hop le, chi de thay do nhay) | %equity | +13.78 | [+7.56, +20.59] | KHONG |

g = pnl / equity ngay truoc khi vao (bo troi compound). Σg B0 135.5%, COIN 103.5%. P3 nhay manh voi c (±0.03 c ≈ ±4%eq) => thuoc ghep cap theo lenh KHONG phai thuoc tot cho lever size; thuoc equity-level (muc 1) moi la thuoc dung. Ca hai NULL.

### Multiplier VT uoc luong theo lenh (m = (N_coin/N_b0)/(E_coin/E_b0))
m TB 0.780; phan vi p1/p5/p25/p50/p75/p95/p99 = 0.50/0.51/0.60/0.72/0.89/1.25/1.64; 7.3% kep 0.5, 0.2% kep 2.0, 83% < 1.

| quintile m | m TB | profit% TB (B0) | median | ty le SL | Σg B0 |
|---|---|---|---|---|---|
| Q1 (coin vol cao) | 0.53 | 3.86 | 5.50 | 12.1% | 0.356 |
| Q2 | 0.62 | 3.22 | 5.50 | 14.2% | 0.224 |
| Q3 | 0.72 | 4.36 | 5.50 | 11.5% | 0.255 |
| Q4 | 0.85 | 5.92 | 5.50 | 15.6% | 0.262 |
| Q5 (coin vol thap) | 1.17 | 5.04 | 5.97 | 17.4% | 0.239 |

Spearman(m, profit%) = +0.026 => VT khong chon duoc lenh tot hon; phan bo lai size giua lenh khong tao loi nhuan. Loi ich (neu co) chi o phia rui ro MTM (coin vol cao dong gop swing lon hon).

## 3. §9 T1–T4

- Pre-reg chi khai T1 + (Calmar_MTM > B0) + CI ΔCalmar khong chua 0. Driver ap dung dung nhu vay; T1 cua driver BO tieu chi `gross <= 70` co trong `reset_rule_score.tier1` — pre-reg cung khong liet ke gross, va gia tri PASS (gross_max 51.2 / 48.5).
- T2 (khong khai, bo sung): q* 26.4 / 29.5 (>=15), top1% 15.0 / 13.9 (<=25), bo top-3 episode >0 (70.6k / 47.1k) => ca 2 PASS.
- T3 (khong khai): win 85.86 -> 85.94, TSloss 14.30 -> 13.83 => khong kem.
- T4 (n >= 1.3x) KHONG ap dung cho lever sizing (thiet ke cho lever tang so lenh) — loai dung.
- Ap dung luat: T1 PASS, Calmar_MTM 1.993 > 1.940, CI chua 0 => "VT ≈ B0". DUNG.

## 4. Pre-reg / toan ven

- prof_run.properties: B0 == de-p1 (0 dong khac); COIN = B0 + `SIZE_VOL_TARGET_MODE=COIN`. jar_sha256 7368be46... ca 3. java_rc=1 ca 3 (giong nhau, hanh vi ket thuc chuan cua sim).
- md5 printDone: de-p1 = g2flat3-val = vt-g2-b0 = 650c386f; vt-g2-coin 137c886a. n 2517 ca 2.
- AMEND1 commit ecae6ef TRUOC b452d8b; so do vol tu nhien chi tren B0 (g2flat3-val) — khong nhin so arm VT => amendment hop le.
- Dataset phu sim-vt-data (CLOSES_1H.bin + symbol_map.csv) — sha ghi trong RESULT; log `[VOL_TARGET] loaded 10322386 rows -> 627 symbol arrays`. Khong kiem lai sha tren Kaggle (ngoai tam).

## 5. VT_PORT

- Hard-code: `src/main/java/com/binance/chuyennd/tradecore/VolTargetSizing.java:66` `public static final float PORTFOLIO_TARGET_ANNUAL_VOL = 0.25f;`, dung tai `:185`; MODE doc key `Configs.java:736` nhung target/clamp/lookback deu `static final`.
- "Blocked" = do lenh "KHONG build" cua task; ve ky thuat chi can them `Cfg.getOr("SIZE_VOL_TARGET_ANNUAL_VOL", 0.25f)` + build + parity B0 650c386f.
- Nhung KHONG nen chay chi bang doi hang so: sigma_equity_20d tren G2 (bursty, p10 rolling-20d ≈ 0) => multiplier ket 2.0 sau moi cua so phang (ke ca target 6%: TB 1.16) — lever-up dung luc it thong tin nhat. Neu muon test PORTFOLIO, can pre-reg lai cong thuc sigma (san sigma, hoac dung vol ex-ante cua cac vi the mo), khong chi target.

## 6. Khuyen nghi
- Giu NULL. Khong nang VT_COIN thanh mac dinh. Neu owner muon giam DD: VT_COIN ≈ giam F_BASE ~0.75x voi diem uoc luong DD tot hon 10-17% o cung CAGR (khong co y nghia) — quyet dinh la risk-preference, khong phai edge.
- Cho cac lever SIZE sau nay: thuoc chinh nen la paired block-bootstrap return NGAY (MTM) so voi B0×c (c = beta hoac khop CAGR, c chot truoc), khong dung ΔCalmar ledger closed (vo luc) va khong dung ghep cap size-neutral (mu voi size).
