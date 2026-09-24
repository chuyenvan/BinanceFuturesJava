# PRE-REG: B FOLLOW-UP — TIME-STOP ADAPTIVE THEO RANK: TACH ADAPTIVE-vs-FIXED + SWEEP WEAK HOURS

Pre-registration CHOT truoc khi chay variant. KHONG doi sau khi thay ket qua.
Repo BinanceFuturesJava branch `module`. Sim: SimulatorMarketLevelTicker1MStopLoss.
Nen: docs/result/RESULT_SL_ADAPTIVE_SWEEP.md §6 — B (adaptive TIME-STOP theo rank) la lever DUY NHAT co
tin hieu that; follow-up chot: (1) tach adaptive-vs-fixed, (2) sweep WEAK hours (96h/120h).
Co che SL_ADAPT_TSTOP da implement commit 7e771d8 (flag default OFF byte-identical).

## 1. BASELINE (KHAC sweep cu)
BASELINE = **T170** = X1_GS_T170_2021: profile `profiles/x1_gs_t170.properties`
(gate SIM_GATE_DYN_SCALE=1.70, LOSER_TIME_STOP PHANG 168h), config `configs/sim_dev_file_2021.properties`,
env WFO_DATA_DIR=/home/ubuntu/wfo_ds_x1_2021 WFO_SMART_CACHE=1 SIM_END_DATE=20251231
EXCHANGE_INFO_PATH=/home/ubuntu/java/exchange_info_pin.json, TIME_RUN=20210701.
printDone md5 = **efb793e2**, n=**1089** (devrun X1_GS_T170_2021).
Ghi chu: sweep SL_ADAPTIVE cu dung baseline C3_FULL gate 1.0 (dc16e4da). B follow-up DOI sang T170
vi T170 la incumbent MOI da THANG readjudicate (docs/result/RESULT_DEV2021_READJUDICATE.md) va PASS hard
constraints CA 5 NAM — moc so sanh dung phai la T170, khong phai C3_FULL cu.

## 2. THIET KE
Rank split: STRONG = selRank 1-4, WEAK = selRank 5-8 (top-K=8 chia doi); selRank==null -> WEAK (bao thu).
Moi variant CUNG gate 1.70 (clone x1_gs_t170) + doi time-stop qua SL_ADAPT_TSTOP (leg CHUA arm trailing):

| variant | flag | STRONG_H (rank<=4) | WEAK_H (rank>4/null) | y nghia |
|---|---|---|---|---|
| T170 (baseline) | off | (168 phang) | (168 phang) | incumbent, LOSER_TIME_STOP 168h |
| V1 adaptive-96 | SIM_SL_ADAPT_TSTOP=1 | 168 | 96 | adaptive: WEAK cat 96h, STRONG giu 168h |
| V2 adaptive-120 | SIM_SL_ADAPT_TSTOP=1 | 168 | 120 | adaptive: WEAK cat 120h, STRONG giu 168h |
| V3 fixed-96 | SIM_SL_ADAPT_TSTOP=1 | 96 | 96 | TAT CA 96h, KHONG chia rank |

Keys profile: SIM_SL_ADAPT_TSTOP=1, SIM_SL_ADAPT_RANK_N=4, SIM_SL_ADAPT_TSTOP_STRONG_H, SIM_SL_ADAPT_TSTOP_WEAK_H.

## 3. DOC KET QUA (dinh nghia TRUOC)
- V1/V2 vs T170: adaptive time-stop co GIUP khong (vs incumbent T170 168h phang).
- V1 vs V3: phan thang den tu ADAPTIVITY (chia rank) hay CHI tu time-stop ngan hon cho TAT CA?
  V1 ~ V3 => loi ich chi la "cat ngan deu" (khong phai adaptivity). V1 > V3 => adaptivity dong gop RIENG.
- WEAK hours nao tot hon (96 vs 120): tim diem risk/return.

## 4. THAM SO CHOT (KHONG DOI / KHONG TUNE)
V1: STRONG_H=168 WEAK_H=96. V2: STRONG_H=168 WEAK_H=120. V3: STRONG_H=96 WEAK_H=96. RANK_N=4 (ca 3).
k = so variant = 3.

## 5. CONG (GATES) — CHOT
(a) PARITY: current jar + profiles/x1_gs_t170.properties (SL_ADAPT_TSTOP off) -> printDone md5 = efb793e2
    (byte-identical baseline T170, cung jar voi variant). FAIL => DUNG + bao.
(b) Jar hien tai da co SL_ADAPT_TSTOP (khong can rebuild). Neu can build: mvn -o package (bo clean).

## 6. CHAM — CHOT
- x1_rates.py moi variant vs X1_GS_T170_2021, k=3 (multiplicity sqrt(2 ln 3)=1.48 => CI_INFLATE=1.48).
- Rate chat luong: win%, TSloss%, mP|SM, mP|SL, meanP (bo n, mMargin). Huong TOT: win% cao, TSloss% thap,
  mP|SM cao, mP|SL cao (loss it nong), meanP cao.
- Quyet dinh = luat cu: >=2 rate CHAT LUONG ngoai CI CUNG huong TOT + PASS rang buoc cung tung nam
  (maxDD<=15 / UW<=120 / nam>=0 / quy>=-5). LUU Y: baseline T170 von PASS hard constraints CA 5 NAM
  (readjudicate §5) => clause hard co nghia lai: variant PHAI GIU pass ca 5 nam, khong duoc pha.

## 7. LUAT CUNG
Chi Oracle. KHONG cham 242, KHONG git push, KHONG tune (dung dung tham so muc 4), KHONG cham holdout 2026.
Parity fail -> DUNG + bao. 1 box -> khong chay 2 sim song song.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_011zpgT8SsGrmcqzxbC93PQT
