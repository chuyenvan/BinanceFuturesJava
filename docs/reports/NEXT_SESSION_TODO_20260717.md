# HANDOFF 2026-07-17 — chuyen session moi. Doc file nay + docs/rules/ce-buttons.md la du ngu canh.

## SO DA CHOT (verified, 2 code-path doc lap)
- **EV2 2-model n=6 (classifier P(HIT+6%) + regressor E(ret4h|miss); gating P>=0.7): +1.74%/keo,
  hit 70.4%, 78 keo/quy** (selector cu duoi ke toan SL-cung: −1.30%/keo). 12h: +1.46%/keo, 1152 keo/quy.
  AUC 0.743. Top-k rank van <1 → DUNG THRESHOLD, khong top-k. Chua tru phi (~0.2%), la median/fold.
- Vong-1 label 1-regression: FAIL ca 4 n (LIFT@32 0.67–0.96 <1). KHONG phai data thieu edge —
  la 1-regression bi ve phat nuot ve thuong (EV2 cung data chung minh edge co that). CDC n=3 do DUNG.
- A/B V4.1 vs V4.2 (fitness, maxfav3): y het 43.8%/WFE~1.0 → doi objective khong du; giu V4.2.
- maxfav3 > ret2 (43.8% vs 37.5%). Chot maxfav3.

## 2 TRACK DOC LAP (dung nham)
- Track A (Oracle WFO): **XONG 2026-07-17, pipeline DONE 7/7, gate da tra loi.** KET QUA:
  DCA-ON 43.8%/WFE0.999/maxDD32.4% vs DCA-OFF+A 43.8%/WFE0.999/maxDD38.5% (per-window khac nhau
  that su — flag ap dung dung) vs DCA-OFF+C placebo 0.0%/WFE0.000/maxDD60.7%.
  → DCA dong gop ~0 edge (chi giam nhe DD); edge model THAT (A>>C); CHOT bo DCA di huong SL-cung.
  Ca A van FAIL pass-criteria (43.8%<70%) → bo DCA la dieu kien can, chua du.
- Track B (Kaggle sl4h): label/selector cho he TUONG LAI SL-cung. EV2 da PASS so bo.

## HUONG DI "BO DCA + SL-CUNG" (uu tien tu tren xuong; moi buoc = 1 phep do co so)
1. **[CHINH] Sim SL-cung + WFO that**: sim Java moi don gian (entry khi P(HIT6%)>=0.7 tu model EV2;
   TP +6% intrabar; khong hit → dong cung tai 4h; KHONG DCA) → WFO 16 window → so pass-criteria
   (70%/WFE0.5/DD50). Can: export pred EV2 per-minute (nhu predict_wf cu) + sim class moi (~300 dong).
2. Bien the horizon: 12h (1152 keo/quy — tan suat giai TOO_FEW!) song song 4h; chon theo WFO.
3. Exit lai "cut-loss-by-time, let-winner-run": thay TP cung +6% bang arm-trailing khi cham +3%
   (tai dung 3-state maxfav3); van dong cung 4h/12h neu chua cham. Ky vong WFE cao hon TP cung.
4. Partial exit: dong 50% tai moc time-stop neu am, 50% con lai trailing (CDC math: chi can go 18% do am).
5. Calibration P (isotonic) + per-fold tail check (quy am?) + tru phi 0.2% vao eval EV2.
6. Classifier-thuan cho n=3/9/15 (nhu model A) — dong ho so vong-1 + chon n toi uu.
7. Placebo test cho EV2 (A-vs-C tren label moi) — chong overfit label.
8. SL-gia (-2/-3% intrabar) vs SL-thoi-gian 4h — do cai nao it bi noise-stop hon.
9. Feature bo sung classifier: momentum ngan/vol/liquidity (tool1 hien thien funding/OI).
10. Ensemble P(hit3/6/9) lam meta-gating + sizing theo EV (sau khi sim pass).

## DANG CHAY / DON DEP
- ~~chain_dca_edge_1784234477~~ DONE 7/7, gate da tra loi (2026-07-17).
- ~~Don watch_v42 + sl4h_watch/_n3~~ DA pipe_stop (2026-07-17). Con RUNNING: exitlab_watch_1784237668
  + wave3b_watch_1784244674 (khong thuoc danh sach don — giu).
- CHUA COMMIT: jar 6ff3f562 (V4.2+retry-EOF+WFO_DISABLE_DCA), mcp_tools fix ns=test + wfo_fanout/kaggle_*/pipe_*,
  profiles, kernels_sl4h/ (5), pipelines, insights docs, file nay. → gop 1 commit + push sau khi edge_C xong.

## LUAT TOKEN — DA GHI VAO docs/rules/ce-buttons.md §"VE SINH CACHE" (doc truoc tien!)
PHAT HIEN LON (do 6 turn thuc): turn cache-SONG=1% vs cache-VO=12-26% cung so infer.
MCP disconnect GIUA turn → tool list doi → vo prompt-cache → moi inference sau tra GIA DAY history (x10-20).
→ 8 luat trong ce-buttons: gom call lien mach; agent=hanh dong CUOI turn; ToolSearch 1 lan dau turn;
che viec lon thanh nhieu turn ngan; output <=10 dong; kiem marker reconnect khi turn dat; <=3-5 infer/turn;
cam SSH inline quote phuc tap. Con lai: nut --brief + pipe_doctor (chua lam); Kaggle env → bake vao kernel gen.

## HA TANG VERIFIED
CE 5 tang OK (bg_selftest 6/6; fix _wfo_coord_cmd LUON gan WFO_STATE_* — bug ns=test da vá).
226 = ticker central 2.9M rec. Jar 6ff3f562 deploy Oracle + Kaggle java-run-lc. Push gan nhat: 0bd65a1.

## DANG CHAY KAGGLE (push 2026-07-17, doc khi quay lai) — 3 kernel, 5/5 slot ban dau
Doc ket qua khi COMPLETE:
  ce kaggle_status chuyendinh/<kernel>            # cho COMPLETE
  ce kaggle_output chuyendinh/<kernel> /home/ubuntu/claudedata/.run/mcp_ce/kout/<kernel>
  ssh ... "grep -hE '<MARKER>' kout/<kernel>/*.log"
- **sl4h-ev2-n3** + **sl4h-ev2-n15**: dong ho so CHON-N dung kien truc EV2 (n6 da +1.74/keo).
  Marker `SL4H_EV2_RESULT`. Doc: pnl_per_trade / best_threshold / auc_med. So voi n6(+1.74) + n9(+1.19)
  → chon n theo pnl-per-keo * tan suat. Ky vong: n3 tan suat cao base_rate cao; n15 hiem/AUC cao.
- **exit-lab-4h v2**: RERUN co FIX PLACEBO (top-N_real thay p>=0.7 → khong con null). Marker
  `PLACEBO_RESULT` + `EXITLAB_RESULT`. Doc: placebo.pnl vs placebo.random — neu ~= nhau => gate E4
  KHONG overfit label (xac nhan +8.8/keo dang tin); neu placebo >> random => tin hieu ao, DUNG nhanh E4.
- Con lai (mục 1 Java sim SL-cung + WFO): CHUA lam — chan cho design khi Uni ve (entry tre 1 nen vi
  edge = f36 ret15m + f10 rsi1H = momentum ngan, nhay slippage).
