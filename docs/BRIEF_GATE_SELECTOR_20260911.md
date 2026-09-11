# BRIEF_GATE_SELECTOR_20260911 — ban do GATE + SELECTOR, cai gi da dong, du lieu nao con dung duoc

Muc dich: tra loi cho master truoc khi thiet ke 1 thi nghiem MOI ve gate thi truong
(`SIM_MIN_MOMENTUM_15M=0.008`) + cach gate ket hop SELECTOR (S1 + net015 build_map). Doc-only,
khong sua code, khong chay sim. Repo `/home/ubuntu/src/BinanceFuturesJava` branch `module`,
HEAD luc viet = `f10f6ca`.

---

## A. BANG "DA DONG" — nhanh | nen | verdict | commit/doc

| nhanh | nen | verdict nguyen van (rut gon) | nguon |
|---|---|---|---|
| B4 rolling-percentile gate (RG95/RG97/RG95w180, W=90/180) | C2b DEV 911 ngay | **KHONG PHAN BIET DUOC**: ca 3 hieu CAGR nam trong CI (`sd_boot` 2.7-3.8pp), maxDD ca 3 khong te hon C2b | `PREREG_B4.md`+`B4_RESULT.md` (a0c7ad6) |
| GD92/GATEDYN — rolling gate mo lai tren C3_FULL 48 thang (pct=0.92,W=90) | C3_FULL (X1) | Audit doc lap: **KHONG PHAN BIET DUOC** o CAGR (`d=+4.98pp CI[-4.47,+16.09]`, nguong hieu chinh boi k=9 la 10.90pp); UW=116 (nguong 120) la so quan sat KHONG CI, sat bien; nam 2022 GD92 **kem hon** gate cung co CI loai tru 0 | `AUDIT_GATEDYN_GD92.md` (272d8f1/1c1ecca/41d5d76) |
| GATEDYN2 — grid 6 bien the quanh GD92 (doi pct/window) | C3_FULL | **VI PHAM thu tuc**: grid tren dung khong gian ma `B4_RESULT` dong 179-180 cam ("noi cua so, doi phan vi"); "6/6 FAIL" la dau hieu **dinh nhieu**, khong phai vung on dinh (3 metric dat dinh o 3 diem khac nhau) | `AUDIT_GATEDYN_GD92.md` muc A4 |
| mom15 sweep TASK-135 (engine CU, truoc fix funding/breaker) | W13 series (khong phai C2b) | Superseded — dung engine khac han hien tai, khuyen nghi mo range **da khong duoc ap dung** tren engine moi | `archive/_cleanup_20260829/.../mom15_sweep_135.md` |
| Q3 — noi lai 0.006 tren engine DA SUA (C3_mom006) | C3 | **5/5 rate CI dat nhung FAIL 3/4 rang buoc cung** => 0.008 khong loc qua chat. Dong huong | `QUEUE.md` dong 296 |
| F4 — doi bien gate tang timing (br_lag3/p15_ma24h/mkt_vol7/mkt_dd7) + model to hop 5 bien | tick 86,971 (30 thang) | **NULL KHONG CO POWER**: MDE80 hieu `\|rank-IC\|` ~0.128 > chinh IC cua p15 (0.100); model to hop **THUA** bien don (`-0.043` OOS) | `F4_TIMING.md`/`PREREG_F4.md` (0c649e0/1fa042d) |
| G1 — doi nhan gate sang `maxFav_72h>=0.07` | 30 thang, 15.44M dong OOS | NULL **nguoc huong**: model moi te hon **ngay tren outcome no duoc train** (AUC `-0.0299` CI`[-0.0459,-0.0145]`, 3/3 nam) | `QUEUE.md` muc G1 (f931265/6519c22) |
| GATEFEAT — giam 33 -> 27 feature cua model gate | X1_C3_FULL 48 thang | IC OOS tot hon **that** (+0.0159, P=1.000) nhung **sim KHONG cai thien** (2024 TSloss% xau `+1.26pp` CI ngoai 0); giu 33f, de xuat rieng con 30f (chua chay sim) | `PREREG_GATEFEAT.md`/`RESULT_GATEFEAT.md` (8fc7d90) |
| 5m grid (S1+net015 predict tren luoi 5 phut thay 15 phut) | X1_C3_FULL 48 thang | NULL **sai huong toan dien**: 0/5 nam PASS het rang buoc cung, 2025 la nam AM | `RESULT_5MGRID.md`/`PREREG_5MGRID.md` |
| K12 (SELECTOR_RANK_TOPK 8->12) | C3_FULL 48 thang | NULL sai huong, DCA loang von (`mMargin -18%`) | `K12_RESULT.md` (bc9d066) |
| W1 truc D+E (ti so MIN_MOMENTUM_15M/PREDICT_SYMBOL_RATE_MAX) | C2b | Don dieu that nhung **FAIL rang buoc cung** underwater (93->172->223 ngay) | `QUEUE.md` muc W1 |

---

## B. GATE AP DUNG HOM NAY TRONG CODE — phat hien quan trong nhat cua brief nay

**Cong thuc `checkSignalDynamic`** (`AIRejectFilter.java:70-92`):
```
dyn_thr = thres15M(t) * max(AI_DYNAMIC_MIN, symbolPred/PREDICT_SYMBOL_RATE_MAX_THRESHOLD * AI_DYNAMIC_MULTIPLIER)
```
`AI_DYNAMIC_MIN=0.26787`, `AI_DYNAMIC_MULTIPLIER=1.28760` (`Configs.java:340-341`). Comment dong
87-88 xac nhan `AI_DYNAMIC_MAX` **KHONG con la tran clamp o day** (vai tro cu da doi, xem
`C2B_SPEC.md` muc 0) — PHASE1_DECISION_SURFACE mo ta cong thuc co "clamp hai dau" la **CU, sai
voi code hien tai**.

### LECH SIM <-> LIVE trong rank-mode (SELECTOR_RANK_TOPK>0) — CHUA duoc do rieng o dau khac

- **SIM** (`SimulatorMarketLevelTicker1MStopLoss.java` ~955-961, ham `createOrder`): LUON goi
  `checkSignalDynamic` cho leg `PREDICT_SYMBOL_TRADE`, **khong dieu kien theo `SELECTOR_RANK_TOPK`**.
  `git log -S checkSignalDynamic` tren file nay chi ra **1 commit duy nhat** (`8fa930b`, tao dong
  nay) — chua bao gio sua. => moi con so equity DEV/VAL (C2b, X1_C3_FULL...) **CO** ap dung
  scale-theo-score.
- **LIVE** (`DetectEntrySignal2TradeNormal.java` dong 653-661 va dong ~646-661 trong
  `createOrderBuyRequest`): **BYPASS co y** `checkSignalDynamic` khi `SELECTOR_RANK_TOPK>0`
  (comment "[PARITY] rank-mode... KHONG goi checkSignalDynamic, de roi xuong checkSignal
  (market-only)"), tu commit `311bb29` (`fix(live): K5 selector parity voi backtest RANK-TOPK`).
  Ly do ghi trong `docs/archive/_cleanup_20260829/docs/project-memory/live_k5_parity_fix_deploy_2026-08-21.md`:
  so sanh voi **buoc CHON candidate** cua sim (`selectorRankPool` bo qua nguong tuyet doi `maxThres`),
  **KHONG phai** buoc entry-filter (`createOrder` cua sim van goi `checkSignalDynamic` nguyen ven).
- **He qua**: production live (K=5 theo runbook, hoac K=8 neu doi theo profile) **KHONG con ap
  dung scale-theo-score cua gate**, chi con gate thi truong bang phang (hang so 0.008 hoac rolling
  neu bat). Nhung KET QUA DEV/VAL dung de ra quyet dinh (C2b 60390, X1_C3_FULL 111428...) **DEU
  phan anh gate CO scale**. Day la mot dang venh sim<->live **chua nam trong 9 diem** cua
  `L4_LIVE_BUILDMAP.md` muc 7 (diem gan nhat la #2 "thu tu selector — DA DONG"). **Can ghi bo
  sung**, khong phai loi cua brief nay sua.

**Rolling gate** (`GateRollingThreshold.java`): OFF mac dinh (khong khai `SIM_GATE_ROLLING_PCT`
trong profile dang chay). Khi ON no **CHI thay `thres15M` (nguong CO SO)**; phan scale-theo-score
o tren KHONG doi (`GateRollingThreshold.java` dong 32-33, tu-comment). Luoi cua rolling gate la
**15 phut hardcode** (`GRID = 15*60_000L`, dong 42) — B4/GATEDYN deu o luoi nay, chua ai thu <15m.

**`riskDrawdown4H`/`predRisk4H`**: van con trong `AiPredictionData`/log/export nhung **KHONG con
dung de loc** — bo hoan toan 2026-08-08 (`AIRejectFilter.java:103-104`: "predRisk4H khong con
model dung sau, dung lam la chan live la rui ro gia"). Chi con doc boi tool validate/legacy
(`Task128ModelQuality`, `ValidateOldPredict3Targets`, `ValidateBrakeDynamic` — code cu).

---

## C. LUOI DU DOAN MARKET + MODEL — tra loi "GF27/gate 33f la gi"

- `claudedata/wfo_gate_pred.csv`: **2,500,260 dong, luoi 1 PHUT** (2 dong dau cach nhau 60,000ms),
  2021-03-31 -> 2025-12-31 (2026 da xoa theo `HoldoutSeal`). => **Gate 1m/5m KHONG can retrain
  model market** — `p15` da co san moi phut; `PREREG_5MGRID.md` muc 0 da xac nhan dieu nay rieng
  cho gate ("Gate p15: GIU NGUYEN... da o luoi 1 PHUT san").
- Model market ("gate 33f"): `XGBRegressor`, **33 feature "V3FULL"** (`WFO_DATAFLOW.md:27`),
  nhan `label_oldbasket`, export `Model_Regressor_Return15M.onnx` per-fold.
- **GF27 = nhanh GATEFEAT** (khong lien quan GATEDYN/rolling gate): devrun `X1_C3_FULL_GF27` dung
  **cung profile** `x1_c3_full.properties` (`PROFILE_HASH=135750e04d67c263`, giong het
  `X1_C3_FULL_PARITY`) nhung doi **nguon dataset gate** sang model 27-feature (bo 3 calendar +
  `rsi14`/`monthOfYear`/`fundingRateRaw`). Ket qua: IC OOS tot hon that (+0.0159) nhung sim
  `X1_C3_FULL_GF27` xau hon parity o 2024 (`TSloss% +1.26pp` CI ngoai 0), equity thap hon 3.9%.
  **KHONG duoc ap dung**; de xuat con lai (chua chay sim) la ban 30-feature (bo 3, giu calendar).
  `AUDIT_GATEDYN_GD92.md` muc A2 da xac nhan doc lap: GF27 **KHONG phai** doi chung cua GATEDYN.

---

## D. DU LIEU CHO CALIBRATION MUC TICK — kiem ton tai/dinh dang/khoang thoi gian (khong chay)

| artifact | kich thuoc | pham vi | cot chinh |
|---|---|---|---|
| `claudedata/wfo_gate_pred.csv` | 2,500,260 dong | 2021-03-31..2025-12-31, luoi **1 phut** | ts,predReturn15M,predRisk4H |
| `ledger/f4_ticks.parquet` | 4.9MB, **86,971 dong** | 2022-01-01..2024-06-30 (ts 1640970000000-1719765900000), luoi **15m MO RONG khong loc** | ts,ncoin,npass,**Y**(=mean g1lite top8),Y2,Y3,p15,p15_ma24h,br_lag3,br_lag4,mkt_vol7,mkt_dd7 |
| `ledger/cand_dev_x1.parquet` | 209.5MB, 7,020,129 dong, **21,396 tick unique** | 2021-04..2025-12 nhung **100% dong da loc `p15>=0.008`** (xac nhan bang code) | ts,maxFav_72h,maxAdv_72h,retEnd_72h,nBars_72h,sym,p15,p_g015,g1lite,score_g015,dyn_thr,gate_dyn_ok (103,840/7.02M dong `gate_dyn_ok=True`) |
| `predwf_map_s1a2_x1/predict_wf_*.bin` | 16 fold, ~900MB | 2022-01-01..2025-12-31 | p0=symbolPred SAU `build_map` (dao dau tu P(win) net015) |
| `label_15m/funding_label_*.pb` | 24 file, ~2GB | 2021Q1..2026Q3 | maxFav/maxAdv/retEnd nhieu horizon |
| `java/fsrun/CLOSES_1H.bin` | 144.5MB | luoi GIO | nguon `feat_v2` (9 feature KEEP S1) |

**Doc dung**: `f4_ticks.parquet` la luoi TICK-15M-MO-RONG **da tinh san outcome top-8** — dung
DUOC NGAY de sweep nguong `p15` (F4_TIMING muc 9 huong mo #1, chi phi ~0). `cand_dev_x1.parquet`
**KHONG dung duoc cho cau hoi "ngoai gate co gi"** vi da bi loc truoc; muon do outcome ngoai gate
phai dung lai nguon goc (bins + label pb) nhu `f4_timing.py`/`f3_supply.py` da lam.

**Khoang thoi gian CHUNG** cua toan bo nguon (neu build lai theo X1 48 thang): 2022-01-01 ->
2025-12-31. `f4_ticks.parquet` hien co CHI toi 2024-06-30 (30 thang) — muon dung ban 48-thang phai
build lai (chi phi thap, cung cong thuc `f4_timing.py`, KHONG can train lai gi).

**Lo hong phai ghi**: (a) `predwf_G015x26` (nguon `p_g015`) khong tai lap byte-exact toan phan,
thieu bin 2021 (`G3_X26_RECOVERY.md`); (b) 2025H2 la mep du lieu — het han o 2025-12-31, KHONG co
2026 (`HoldoutSeal`, `PREREG_X1.md` muc 1.1); (c) leak `f0..f39` (feature Tool1 cua ca model gate
lan net015/S1) **VAN CON MO**, chua co bang chung nhan-qua (`PHASE1_DECISION_SURFACE.md` muc A1) —
moi so tren day ke thua nghi van nay, khong phai loi hong moi.

---

## E. CAU HOI CHUA DONG (2), do duoc bang tick, KHONG can sim

**Q1 — Duong cong danh doi precision/coverage cua nguong `p15`** (tren `f4_ticks.parquet`,
sweep threshold lien tuc, **cong thuc tradeoff phai viet TRUOC khi nhin duong cong** — day la
mo ta 1-bien, khong phai kiem dinh chon-ung-vien, nen it bi tuong power hon Q2/F4).
*Power caveat*: neu ai muon bien no thanh "tim nguong toi uu" (nhieu diem), se roi vao dung
tuong ma F4 da do: `n=86,971` tick nhung `n_eff ~ 900` khoi 72h (`sd_boot`=0.033), MDE80 cua
hieu `|rank-IC|` ~ **0.13**, lon hon chinh IC cua `p15` (0.100) — xem `F4_TIMING.md` muc 2, 8.

**Q2 — Gate scale-theo-score (`dyn_thr`) co doi outcome top-8 so voi gate market-only (khong
scale)** — do TRUC TIEP tren `cand_dev_x1.gate_dyn_ok` (da co san, khong can tinh lai), noi rong
cua so tu 30 len 48 thang de tang khoi 72h.
*Power caveat*: `CI_REAUDIT.md` NHOM B #9 da lam dung phep so nay tren 30 thang
(gate MO top8 - gate DONG top8 = `+0.0238`, CI `[-0.0053,+0.0442]`, **n_eff=52 khoi 72h** =>
KHONG PHAN BIET DUOC). Noi cua so len 48 thang uoc `n_eff` ~80-90 khoi (x1.5-1.7) — **chua chac
du** de vuot MDE, phai bao ca hai kha nang truoc khi chay.

**Bat buoc chung cho ca 2**: viet cong thuc/tieu chi TRUOC khi nhin so (bai hoc F4: "chot nguong
ma gan nhu khong ung vien nao vuot noi" — `F4_TIMING.md` muc 2 doan cuoi).

---

## F. XAC NHAN CAC NHANH USER DA NGHI LA DONG

- **5m S1**: DA DONG, NULL sai huong toan dien — `RESULT_5MGRID.md` muc 3 (0/5 nam PASS rang
  buoc cung, 2025 la nam AM).
- **Rolling gate (5m/1m)**: pham vi rolling gate da tung thu (B4/GATEDYN) **CHI o luoi 15 phut**
  (`GateRollingThreshold.java:42` hardcode). Chua ai thu luoi <15m, nhung F4 da chi ro lam min
  luoi **KHONG tao them power**: "lam min luoi len 1 phut se cho n=1.3M va **CUNG n_eff~900**"
  (`F4_TIMING.md` muc 8 diem 4) — nen huong nay coi nhu **dong ve mat ly thuyet**, du chua ai
  chay thuc nghiem.
- **Sweep `MIN_MOMENTUM_15M`**: dong **2 lan doc lap** — TASK-135 (engine CU, truoc fix
  funding/breaker, KL "mo rong range" **chua tung ap dung tren engine moi**) va Q3 (engine C3 da
  sua, noi lai 0.006, KL giu 0.008). **CANH BAO**: nhanh SIET (`M010`/`M012`, nguong 0.010/0.012)
  duoc khai bao trong `QUEUE.md` dong 304 nhung **KHONG tim thay ket qua/DONE rieng** cho 2 tag
  nay — dong-huong cua Q3 dua tren doc LAI thi nghiem NOI (0.006), khong phai SIET. Neu master
  quan tam huong SIET, day **chua thuc su la mot cau hoi da dong bang du lieu** — nhung no can
  chay sim (ngoai pham vi "do bang tick" cua brief nay).

---

## Nguon chinh da doc
`PREREG_B4.md`, `B4_RESULT.md`, `AUDIT_GATEDYN_GD92.md`, `RESULT_5MGRID.md`, `PREREG_5MGRID.md`,
`F4_TIMING.md`, `PREREG_F4.md`, `PHASE1_DECISION_SURFACE.md`, `SELECTOR_LADDER.md`,
`K12_RESULT.md`, `archive/_cleanup_20260829/docs/reports/mom15_sweep_135.md`,
`archive/H1_GATE_SPEC.md`, `G4_RECIPE_C4.md`, `L4_LIVE_BUILDMAP.md`, `PREREG_X1.md`,
`CI_REAUDIT.md`, `index.md`, `QUEUE.md`, `PREREG_GATEFEAT.md`, `RESULT_GATEFEAT.md`,
`archive/_cleanup_20260829/docs/project-memory/live_k5_parity_fix_deploy_2026-08-21.md`;
code: `AIRejectFilter.java`, `GateRollingThreshold.java`, `DetectEntrySignal2TradeNormal.java`,
`SimulatorMarketLevelTicker1MStopLoss.java`, `Configs.java`, `WfoDataset.java`,
`LoadWfoGatePredTool.java`, `WFOGateRunner.java`.
