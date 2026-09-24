# PREREG_L1 — run doi chung "symbolPred = HANG SO" (2 arm, 48 thang)

Viet TRUOC khi chay (AGENT_RUNBOOK muc 0.2). Khong sua sau khi thay ket qua.

## 1. Cau hoi

Shadow C3 chay live **khong the** dung gia tri `symbolPred` cua `predwf_G015x26` (artifact
dong bang, khong tai lap, khong co ban 2026 — `docs/plan/H1_HOLDOUT_PREP.md` muc 5). Neu dung
shadow, gia tri do phai bi thay bang mot nguon KHAC (model 45-feature live, hoac hang so).
`symbolPred` di vao DUNG MOT cho trong engine khi `SELECTOR_RANK_TOPK>0`:
`OrderTargetInfoTest.trailRate()` — ban le TUYET DOI `pnp <= TS_PNOPUMP_WEAK_THR (0.29)`
-> cap STRONG 0.08, nguoc lai WEAK 0.03. (Gate tang 2 `checkSignalDynamic` BI BO QUA khi
TOPK>0 — `DetectEntrySignal2TradeNormal:512`.)

=> **Do nhay cua C3 voi GIA TRI symbolPred = do nhay voi ban le do.** Thay `symbolPred`
bang mot hang so tuong duong dat `TS_PNOPUMP_WEAK_THR` ra ngoai dai gia tri: 1.0 (moi lenh
STRONG) hoac 0.0 (moi lenh WEAK). Hai arm nay **chan tren va chan duoi** moi hang so co the.

## 2. Thiet ke — KHONG rebuild bins, KHONG rebuild dataset

- Nen: `X1_C3` (48 thang, `docs/experiment/X1_EXTEND.md`): 2,058 lenh, win 85.33%, TSloss 14.87%,
  `mean(profit|SL)` -21.85, equity 98,523, CAGR 29.58%, maxDD -13.31%, UW 302,
  md5 printDone `d39da2940dfd815f60772f70517750bf`.
- Dataset dung lai `/home/ubuntu/wfo_ds_x1` (da co, binsSha256 `b8776231...`, 16 fold).
  **Khong build lai** => khong ton dia (con 6.9G, duoi nguong 8G cua `run_x1_sim.sh`).
- Profile: `profiles/l1_pnp_strong.properties` va `profiles/l1_pnp_weak.properties`
  = `profiles/x1_c3.properties` + **DUNG MOT dong** `SIM_TS_PNOPUMP_WEAK_THR=1.0 / 0.0`.
- `SIM_END_DATE=20251231`. **KHONG mo holdout 2026.** `TICKER_SOURCE=file` (neo 60395).
- Chay TUAN TU, 1 slot JVM.

## 3. Tieu chi (rate, khong phai equity)

So `L1_PNP_STRONG` va `L1_PNP_WEAK` voi `X1_C3` tren: `n`, `win%`, `TSloss%`,
`mean(profit|SM)`, `mean(profit|SL)`, `meanP`, `mean(margin)`.
`n` PHAI khong doi (2,058) o ca hai arm — ban le chi tac dong SAU khi arm, khong doi tap
lenh vao. **`n` doi = co gi do sai, dung doc tiep.**
Equity/CAGR bao cao rieng, dan nhan "khong phai tieu chi" (`sd(dCAGR)` = 2.57pp).

## 4. DU DOAN GHI TRUOC

1. `n` = 2,058 giong het o ca hai arm (ban le sau-arm).
2. `X1_C3` da la **83.8% STRONG** (`AGENT_RUNBOOK` muc 3) => `L1_PNP_STRONG` chi doi
   **16.2%** so lenh; du doan **khong rate nao ngoai CI**, equity lech < 2.57pp.
3. `L1_PNP_WEAK` doi 83.8% so lenh => du doan doi HINH DANG phan bo winner theo dung
   co hoc muc 4 `docs/experiment/C3_BASELINE.md` (than LEN ~1pp, duoi phai TUT ~1pp), nhung
   `win%`/`TSloss%` van trong CI.
4. Bien do lech tong the (|equity - 98,523|) du doan **< 5%** o ca hai arm.
   Neu SAI (lech > 5%) => gia tri `symbolPred` la load-bearing va shadow C3 KHONG duoc
   thay no bang hang so; phai cam model 45-feature live vao.

## 5. Rang buoc

Khong holdout (`SIM_END_DATE=20251231`). Khong sua profile goc `x1_c3`. Khong push.
