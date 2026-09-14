# PREREG_REGIME_GATE — gate scale doi theo regime BTC 30d (uptrend 1.00, con lai 1.70)

Chot: 2026-09-14, commit TRUOC khi cai code / build / chay. Agent thuc thi (Opus). RULE CO DINH, KHONG fit.
Co so: docs/ANALYSIS_T170_VS_T100.md (commit 8878a96) muc 4b/4c — lenh marginal DOI DAU theo xu the BTC 30 ngay
(uptrend +65.7/lenh, chop -35.6/lenh). Y tuong: uptrend NOI gate (bat marginal tot), chop/down SIET gate (cat marginal doc).

## 0. Neo baseline (da co, KHONG chay lai de lam baseline)
- Dataset `wfo_ds_x1_2021`, config `configs/sim_dev_file_2021.properties` (TIME_RUN=20210701), SIM_END_DATE=20251231,
  TICKER_SOURCE=file, harness `/home/ubuntu/k_runarm.sh TAG PROFILE` -> `/home/ubuntu/java/devrun/TAG/storage/printDone.csv`.
- **T170** = `X1_GS_T170_2021`, profile `profiles/x1_gs_t170.properties` (SIM_GATE_DYN_SCALE=1.70),
  printDone.csv n=1089 (1090 dong), md5 `efb793e2468ca3a7318da0f0ad23d4fc`.
- **T100** = `X1_C3_FULL_2021`, profile `profiles/x1_c3_full.properties` (khong khai scale => 1.0),
  printDone.csv n=2559 (2560 dong), md5 `dc16e4da6ff6cb7b8d41c592bc3d9c45`.
- KHONG cham HOLDOUT 2026 (SIM_END_DATE=20251231 giu nguyen). KHONG cham 242. KHONG git push. KHONG tune.

## 1. RULE regime — CO DINH, KHONG fit, KHONG quet nguong
- **Tin hieu**: BTC 30-day return tu BTC daily close (dung CHINH gia BTC symId=1 trong tick-data ma sim giao dich,
  `kaggle_data_hpo`, field `priceClose`) — KHONG dung proxy featv2, de nhat quan voi gia sim + audit duoc.
- **Daily close** C[d] = gia dong cua BTC o UTC-day d = bar co startTime lon nhat trong ngay UTC d (bucket theo
  `startTime // 86400000`, doc lap timezone).
- **Regime cho UTC-day D** (ap cho MOI tick trong ngay D), CAUSAL — chi dung close <= het ngay D-1:
  `ret30(D) = C[D-1] / C[D-1-30] - 1`. **UP** neu `ret30(D) > 0`; nguoc lai **NOT-UP**. Nguong = 0 (bien tu nhien, KHONG do).
  Khong co look-ahead: quyet dinh trong ngay D chi dung du lieu tu cac ngay da dong truoc D.
- **GATE_DYN_SCALE(t)** = **1.00** neu UP, **1.70** neu NOT-UP. Hai so nay CO DINH tu pre-reg (= T100 va T170), KHONG fit.
- Precompute chuoi regime daily (causal) ghi ra file, nap vao sim (audit duoc); sim tra cuu scale theo UTC-day cua tick.

## 2. Cai dat — 1 config REGIME_ADAPTIVE, sau flag, default OFF = byte-identical
- `EntryGate`: them `boolean GATE_REGIME_ADAPTIVE=false`, hang so `REGIME_SCALE_UP=1.00f`, `REGIME_SCALE_NOTUP=1.70f`,
  bien theo-tick `CURRENT_REGIME_SCALE`. `threshold()`: `gateScale = GATE_REGIME_ADAPTIVE ? CURRENT_REGIME_SCALE : GATE_DYN_SCALE;`
  roi `return thrBase * max(DYN_MIN, scale) * gateScale;`. Flag OFF => bieu thuc Y HET ban goc => byte-identical
  (x * GATE_DYN_SCALE, IEEE-exact). Chi ap nhanh dyn (symbolPred != null); nhanh co so (BIG_DOWN/DCA/leg market) KHONG bi scale.
- `Configs` static block doc 3 key: `SIM_GATE_REGIME_ADAPTIVE` (1/true -> flag ON), `SIM_REGIME_FILE` (duong dan file regime),
  `SIM_REGIME_FORCE` (UP|NOTUP -> ep hang so, chi cho gate 2-cuc). Khong khai => giu default => byte-identical.
- `RegimeSchedule` (tradecore): nap file regime -> TreeMap<utcDay, scale>; `scaleForTime(ms)` = scale cua `ms/86400000`
  (thieu -> floorEntry, causal). FORCE=UP/NOTUP -> tra hang so 1.00/1.70.
- `SimulatorMarketLevelTicker1MStopLoss`: truoc vong lap, neu flag ON nap RegimeSchedule (hoac dat FORCE). Trong vong lap tick,
  ngay sau `Long time = entry.getKey();` dat `EntryGate.CURRENT_REGIME_SCALE = RegimeSchedule.scaleForTime(time)` (1 lan/tick,
  truoc moi createOrder; vong lap tick DON LUONG). Live path KHONG doi (flag OFF).
- `DumpBtcDaily` (research): dung `KaggleDataLoader.loadDailyTickersShort`, bucket BTC(symId=1) theo UTC-day, xuat CSV daily close.

## 3. CONG BAT BUOC (fail -> DUNG + bao master, KHONG chay tiep, KHONG sua ngưỡng)
- **(a) Parity hang so, flag OFF -> byte-identical** (chung minh khong pha code cu):
  - jar moi + `x1_gs_t170.properties` (scale 1.70, flag OFF) => md5 printDone = `efb793e2...` (= T170).
  - jar moi + `x1_c3_full.properties` (scale 1.0, flag OFF) => md5 printDone = `dc16e4da...` (= T100).
- **(b) 2 cuc, flag ON + FORCE (chung minh wiring dung)**:
  - flag ON, `SIM_REGIME_FORCE=NOTUP` (scale 1.70 hang so) => md5 = `efb793e2...` (= T170).
  - flag ON, `SIM_REGIME_FORCE=UP` (scale 1.00 hang so) => md5 = `dc16e4da...` (= T100).
- Ca (a) va (b) PASS => moi chay REGIME_ADAPTIVE. Bat ky md5 lech => DUNG.

## 4. Cham + quy tac
- `research/analysis/x1_rates.py X1_C3_FULL_2021 <REGIME_TAG>` va `... X1_GS_T170_2021 <REGIME_TAG>` (5 rate + CI khoi-72h,
  bang nam, rang buoc cung HARD_DD 15 / UW 120 / nam>=0 / quy>=-5). Cham chinh = REGIME vs **T170** (k=1, 1 config duy nhat).
- **MUC TIEU (ky vong ghi truoc)**: "best of both" = CAGR REGIME CAO hon T170 (thu lai loi uptrend) trong khi maxDD & UW
  KHONG xau hon T170 dang ke (≈ hoac tot hon); DONG THOI rui ro (maxDD/UW) THAP hon T100 ro. Neu khong dat -> NULL, GIU T170.
- Bao cao ghi: %tick (va %ngay) o regime UP vs NOT-UP, bang T100/T170/REGIME (n, win/TSloss/meanP, maxDD, UW, CAGR + CI vs T170), verdict.

## 5. CANH BAO KY LUAT (bang chung YEU)
Rule regime sinh tu HAU KIEM tren CHINH cua so DEV nay (analysis 8878a96). Vi tham so (nguong 0, scale 1.00/1.70) DA CO DINH
truoc khi chay va KHONG fit theo ket qua, DEV la mot test HOP LE cua rule da khoa — NHUNG bang chung YEU (winner's-curse residual:
viec CHON dung tin hieu BTC-30d la hau kiem). Xac nhan THAT = forward / holdout 2026 sau nay. TUYET DOI KHONG tune scale/nguong
theo ket qua DEV; neu thua ro tren DEV van chi la "dang thu forward", khong doi production.

## 6. Thu tu bat buoc
1. Commit file nay (TRUOC). 2. Cai code (EntryGate/Configs/RegimeSchedule/DumpBtcDaily/sim), build `mvn -o package` (test PASS).
3. Dump BTC daily close + precompute file regime (causal). 4. Cong (a) parity const. 5. Cong (b) 2 cuc. 6. Sim REGIME_ADAPTIVE.
7. Cham vs T170 (+ tham chieu T100). 8. `docs/RESULT_REGIME_GATE.md`, commit SAU. KHONG push, KHONG 242, KHONG holdout 2026.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_011zpgT8SsGrmcqzxbC93PQT
