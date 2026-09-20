# PREREG_BIGDOWN_STRUCT — bigdown co phai nhan to dong-thua? (TASK A, 0-sim)

Pre-registration. COMMIT TRUOC khi tinh bat ky so nao trong `docs/ANALYSIS_BIGDOWN_STRUCT.md`.
Theo `TASKS_2026-09-20b_bet_structure_and_closeout.md` muc 2 (redirect Uni 09-20). Khong sua
`.java`, khong chay sim, khong xgboost, khong push, khong dung HOLDOUT 2026.

## 0. Cau hoi (nguyen van muc 2.1 cua brief)
(Q1) Dong-thua cua T170 co tap trung trong bigdown khong? maxDD/UW den tu bigdown bao nhieu %?
(Q2) O gate mo (T100), thi truong sap co gay "nhoi o at" (nhieu lenh mo moi/gio, von trien khai
vot) khong, va co phai nguon dong-thua khong? (Q3) ICC/dong-thua tach theo bigdown khac gi so voi
chung? (Q4) Don vi dong printDone = lenh hay leg DCA?

## 1. Du lieu (CHI DOC)
- T170: `/home/ubuntu/java/devrun/X1_GS_T170_2021/storage/printDone.csv` (1089 dong) +
  `logs/sim.out` (1644 dong `Update`). Profile `x1_gs_t170.properties`: `SIM_GATE_DYN_SCALE=1.70`,
  `CAPITAL_START=35000`.
- T100: `/home/ubuntu/java/devrun/X1_C3_FULL_2021/storage/printDone.csv` (2559 dong) +
  `logs/sim.out`. Profile `x1_c3_full.properties`: khong dat `SIM_GATE_DYN_SCALE` (mac dinh gate
  1.0, dung nhu brief goi "T100").
- Da `ls /home/ubuntu/java/devrun/`: co rat nhieu run gate-scale trung gian tu cac vong TRUOC
  (vd `X1_C3_FULL_GD88/92/96`, `GD_GD92_2021`, `RG_A_T100/T170`, `GS055..GS140`, `NB_T170_NOBD`
  v.v., thuoc cac vong `AUDIT_GATEDYN_GD92`/`RESULT_NOBD_READJUDICATE` cu, KHONG phai vong nay).
  Theo dung §2.2 ("neu con run gate-scale trung gian -> dua vao bang lieu-dap-ung; KHONG chay run
  moi"), TASK A se dua **GS055/GS070/GS085/GS100(=T100)/GS120/GS140/T130/T170** vao MOT bang
  M2 dose-response phu (gate cang long thi burst cang lon) NEU thoi gian cho phep; bang chinh
  M1-M7 van chi tinh day du cho T170 va T100 (2 run chinh brief yeu cau).
- BTC 1h: `/home/ubuntu/java/fsrun/CLOSES_1H.bin` (dtype `[('ts','>i8'),('sym','>i2'),('c','>f4')]`,
  144.5MB, ~10.3M dong, TAT CA symbol — khong chi BTC). Loader: `trend_rank_ic.py::load_closes()`
  (loc `ts<SEAL_2026`, `ctime=ts+1h`); BTC = `sym==1` (`beta_decomp_t170.py::load_btc_series`,
  `btc_at_or_before`).
- **Universe breadth (BD2) KHA THI**: `CLOSES_1H.bin` co closes 1h cho toan bo universe (khong
  chi BTC) — dung truc tiep cho BD2, KHONG can `featv2/feat_v2.parquet` (912M). File 144.5MB tai
  het vao RAM la an toan (~250MB), da kiem `free -g` = 16G free/23G total truoc khi chay — DU
  nguong 8G yeu cau cua luat 0-sim song song shadow-c3 + 2 agent khac.
- Candidate/tick log: `ls storage/` cua ca T170 va T100 CHI co `BalanceIndex.data`,
  `OrderTestDone.data`, `printDone.csv` — **KHONG co TickDecisionLog/pos.bin doc duoc** (dung du
  doan cua brief). => dung **T100 admitted lam proxy** cho "neu gate mo thi burst co gi", ghi ro
  la proxy, khong phai candidate that truoc gate.
- Tai dung: `icc_anova()` nap qua AST tu `nbets_step3_crosssec.py` (dung ky thuat
  `load_icc_anova()` cua `hedge_overlay_a.py`); `c3_rates.py::{trades,equity,inflate}`;
  `hedge_overlay_a.py::{k_bar,sum_notional_on_grid,hourly_grid,eq_day_of}`;
  `beta_decomp_t170.py::btc_at_or_before` (import module, dung ham co san, KHONG doi).

## 1.1 Phat hien ngoai du kien (ghi lai, KHONG dung lam dinh nghia bigdown chinh cua TASK nay)
Trong luc recon phat hien repo da co mot khai niem **"BIG_DOWN"** khac o tang Java tu cac vong
TRUOC (khong thuoc vong 09-20 nay):
- `MarketBigChangeDetector.calMarketData/getMarketStatus1M`: mot co **market-wide breadth-crash**
  that (khong chi BTC) — `rateChangeDownAvg` = trung binh 1-phut-return cua ~80-100 coin te nhat,
  neu `< Configs.MS_DOWN_BIG_AVG` => `MarketLevelChange.BIG_DOWN`. Day la CAUSAL, tinh moi phut.
- `level=BIG_DOWN` trong `printDone.csv` la mot LEG TYPE rieng (khong phai DCA continuation),
  duoc chon boi `BdSelection` (mac dinh `BD_SEL_MODE=off` trong CA HAI profile T170/T100 => leg
  nay KHONG kich hoat trong 2 run muc tieu).
- `Configs.CONC_CAP_BD_RATE_ENABLED` (mac dinh **false** trong ca 2 profile) — mot cai cap-lenh
  BIG_DOWN/gio DA TON TAI trong code (cap mac dinh 75/gio) nhung **KHONG bat** cho T170/T100 =>
  xac nhan dung du doan cua A-recon "gan nhu chac la KHONG co rate-limit" cho 2 run nay.
- `MarketBigChangeDetector` con co circuit-breaker mat-do-mo-lenh (`evaluateCircuitBreakerCore`,
  BURST_BASE=40/4 phut) nhung **chi chay o duong LIVE** (`DetectEntrySignal2TradeNormal`), KHONG
  ap dung cho sim backtest — khong lien quan T170/T100 printDone.csv.
=> Ket luan cho PREREG nay: hai co san (`BD_SEL_MODE`, `CONC_CAP_BD_RATE_ENABLED`) DEU OFF trong
T170 va T100, nen KHONG anh huong so do o day; nhung day la manh moi quan trong cho A-recon (agent
khac) ve diem cam pacing an toan — se nhac lai trong bao cao MASTER.

## 2. Dinh nghia bigdown — do SONG SONG (causal), KHOA cong thuc truoc khi tinh
Tat ca deu chi dung du lieu toi thoi diem t (khong nhin tuong lai).

- **BD1a**: BTC tra ve `ret(H=24h)` tai gio t = `close(t)/close(t-24h) - 1`. Co BD1a(t)=1 neu
  `ret(24h) <= -0.05`.
- **BD1b**: nhu BD1a nhung nguong `-0.08`.
- **BD1c**: `ret(H=72h) <= -0.10`.
- **BD1q**: 1h-return cua BTC tai t `<= q05` cua PHAN PHOI 1h-return trong 60 NGAY LICH TRUOC t
  (rolling, cua so ket thuc o t-1h, cap nhat moi ngay — causal, khong dung phan vi tuong lai).
- **BD2_P** (breadth, P in {70,80,90}): tai moi ctime t trong `CLOSES_1H.bin`, tinh tap symbol co
  ca gia dong tai t va t-1h (universe "active" tai t), % trong so do co 1h-return < 0; BD2_P(t)=1
  neu % do >= P.
- **BD3** (severity, dieu kien tren BD1a=1): trong cac gio da flag BD1a, chia theo do lon cua
  `ret(24h)`: mild [-0.08,-0.05), moderate [-0.15,-0.08), severe < -0.15.
- **Bigdown episode**: chuoi gio lien tiep co cung flag =1 (dung cho "onset" o M3 va cho gan nhan
  ngay bigdown o M5 — mot NGAY duoc coi la "ngay bigdown" neu co >=1 gio trong ngay do co flag=1,
  theo lich UTC).

**Dinh nghia CHINH (headline) cho cong GO/NO-GO §5 va cho nhan lenh o M4/M5/M7: BD1a
(X=5%, H=24h)** — chon TRUOC khi tinh, ly do: la muc dau tien va "vua phai" trong danh sach Uni de
xuat (khong phai muc kheo nhat/long nhat, tranh chon-sau-khi-thay-so). Tat ca dinh nghia con lai
(BD1b/c/q, BD2_70/80/90, BD3) deu duoc tinh SONG SONG va bao cao trong bang dose-response — KHONG
tinh vao k (day la descriptive theo dung §2.3, khong phai bien the/variant so CAGR).

## 3. Don vi phan tich (M1) — khoa truoc
`row` = 1 dong `printDone.csv` (co the la leg DCA hoac leg BIG_DOWN); `episode` = nhom theo
`(sym,end)` (dung dung quy uoc cua `c3_rates.py::trades()`/`DIAG_BIGDOWN_CONCENTRATION.md`), leg
dau (`leg==0`, `start` som nhat trong nhom) dai dien episode. Moi metric burst/k_bar/n_eff bao ca
hai don vi.

Doi thoi gian: `start`/`end` trong `printDone.csv` la GIO GMT+7 NAIVE. Quy ve UTC bang
`t_utc_ms = t_naive_ms - 7h` (dung cong thuc `hedge_overlay_a.py::load_trades`, KHONG tu suy dien
lai). Equity hang ngay (`sim.out`, `Update YYYYMMDD 07:00 GMT+7` = 00:00 UTC) gan cho gio UTC bang
`eq_day_of` cua `hedge_overlay_a.py` (khong tu viet parser moi).

## 4. Metric — khoa TRUOC (M1-M7, dung nguyen muc 2.4 cua brief)
- **M1**: so dong vs so episode, ti le, cho T170 va T100.
- **M2 (nhoi o at)**: phan bo so lenh MOI mo trong cua so truot 1h va 4h, tach
  trong-bigdown/ngoai-bigdown (theo BD1a tai gio floor cua `t0_utc`), cho T170 VA T100 (+ dose-
  response tren cac run gate trung gian neu kip). Bao p50/p90/p99/max, ca hai don vi. Kem: T100
  admitted dung lam proxy "candidate/gio" (ghi ro la proxy).
- **M3 (von trien khai)**: `Sigma(notional dang mo)/equity(t)` theo gio (dung
  `sum_notional_on_grid`), tach trong/ngoai BD1a, cho T170 & T100; p50/p90/p99/max. `equity(t)`
  = snapshot ngay GAN NHAT <= t (khong co equity noi-ngay that — GIOI HAN, ghi ro). Onset event-
  study: tai gio DAU TIEN cua moi bigdown-episode (BD1a 0->1), so Sigma(notional)/equity ngay
  TRUOC onset vs +1h/+4h sau onset (median tren cac episode).
- **M4 (dong-thua)**: `icc_anova()` (AST-load, khong viet lai) tren cohort ngay/72h/tuan, 4 bien:
  (i) ROI tho, (ii) ROI winsor p1/p99, (iii) `1[ROI<0]`, (iv) `1[ROI<p10 cua run]`. Gan 2 nhan cho
  moi lenh: `enter_bd` (BD1a tai gio `t0`) va `exposed_bd` (BD1a=1 tai BAT KY gio nao trong
  `[t0,t1)`). Tinh ICC + ti le lo/lo nang RIENG cho `exposed_bd=1` vs `exposed_bd=0` (nhan chinh
  cho cau hoi dong-thua "trai qua bigdown"), va rieng theo `enter_bd`. Overdispersion
  `phi = Sum((L_j - k_j*phat)^2 / (k_j*phat*(1-phat))) / (J-1)` tren cohort ngay co `k_j>=3`,
  tinh TOAN BO / chi-`exposed_bd=1` / chi-`exposed_bd=0`, cho ca "lo" va "lo nang".
- **M5 (maxDD/UW theo bigdown)**: tu chuoi equity hang ngay, ngay bigdown = co >=1 gio BD1a=1
  trong ngay (UTC). Tren doan maxDD LON NHAT: % tong do sut (tong |return am| trong doan) roi vao
  ngay bigdown; % so ngay duoi nuoc (equity<cummax) la ngay bigdown. Top-10 ngay equity te nhat:
  co phai bigdown, so leg moi mo ngay do, % trade DONG ngay do co profit<0.
- **M6 (n_eff)**: `n_eff_total = Sum_j k_j/(1+(k_j-1)*ICC_ROI)` (cohort ngay k_j>=2, dung ICC_ROI
  toan cuc cua run) va ban NBETS `J*k_bar/(1+(k_bar-1)*ICC)`; bao ca hai + tran `1/ICC`. Tach theo
  don vi dong/episode.
- **M7 (lenh bien T100\T170)**: kiem T170 subset T100 bang khoa `(sym,start_naive)`. Bao % dong
  T170 tim thay trong T100 (ty le subset-match). Neu >=90% khop (nguong chap nhan "about subset"),
  tach tap "bien" = dong T100 KHONG co trong T170 theo khoa do; bao ROI trung binh (CI 90%,
  block-72h bootstrap, `NREP=2000, SEED=20260905`, dung `blk` co san cua `c3_rates.trades`),
  % thang, ICC, phi, va % dong bien co `enter_bd=1`.

## 5. Du bao ghi truoc (khong "giai thich xuoi" — nguyen van §2.5)
(a) `phi(lo, exposed_bd=1) >> phi(lo, exposed_bd=0)` o CA HAI run; (b) T100 co burst nhoi trong
bigdown ro hon T170 nhieu (p99 lenh moi/gio va Sigma(notional)/equity cao hon); (c) phan lon maxDD
cua ca hai den tu bigdown; (d) lenh bien T100\T170 tap trung bat can xung vao bigdown va co phi
cao hon loi, ROI trung binh duong nhung mong. Neu sai, ghi la sai trong ANALYSIS.

## 6. Cong GO/NO-GO cho TASK B — KHOA TRUOC (nguyen van §2.6, dung BD1a lam dinh nghia headline)
GO neu DONG THOI:
- (g1) `phi(lo, exposed_bd=1)/phi(lo, exposed_bd=0) >= 1.5`, tinh tren **T100** (mau lon hon,
  nhieu ngay bigdown-exposed hon T170 de uoc luong phi on dinh hon) — neu T170 khong du du lieu de
  uoc luong phi rieng (qua it lenh exposed_bd trong cohort k_j>=3), ghi ro va dung T100 lam can cu
  chinh, T170 la doi chieu.
- (g2) `>=50%` do sut maxDD (T100) xay ra trong ngay bigdown (M5).
- (g3) ROI trung binh lenh bien T100\T170 (M7) `>0` VA CI-cohort 90% khong nam hoan toan duoi
  `-0.5pp`.
- (g4) **KHONG thuoc pham vi TASK A** — phu thuoc ket qua A-recon (agent song song, tim diem cam
  admission/sizing giu OFF byte-identical). TASK A chi bao cao (g1)-(g3); GO/NO-GO **tong the**
  cho TASK B can ca (g4) tu A-recon.
NO-GO tren tung tieu chi neu vi pham; ghi ro vao bao cao gui MASTER va (neu NO-GO ro rang) vao
`power_wall.md`.

## 7. Gioi han da biet truoc khi tinh (ghi truoc, khong phai bien minh sau)
1. `equity(t)` noi-gio la xap xi tu snapshot ngay gan nhat (khong co snapshot noi-ngay that).
2. BD2 breadth dung `CLOSES_1H.bin` (hourly) — khong bat duoc bigdown-trong-vai-phut nhu
   `MarketBigChangeDetector` (1-phut); day la gioi han do gio, khong phai loi.
3. Candidate/gio dung T100-admitted lam proxy (khong co candidate-truoc-gate that).
4. `(sym,start)` co the khong khop 100% giua T100/T170 neu co lam tron/format khac nhau — se bao
   ty le subset-match truoc khi ket luan M7.
5. `icc_anova`/`phi` can `k_j>=2`/`>=3` — cohort bigdown co the it ngay hon cohort thuong, CI/uoc
   luong se rong hon, ghi ro trong bao cao thay vi lang le bo qua.
