# PREREG_FAMILY2B - LONG: vao lenh co SL / TP theo ti le R, KHONG DCA, tren nen r1-a3 (BAN CUOI, MASTER commit truoc khi chay)
Chi doi CAU HINH sim (khong sua Java, khong build jar). Can mo rong DRIVER Python (muc 8). DEV <= 2025-12-31. Khong doi luat sau khi thay so.

## 0. Boi canh
- Owner 26/11 (nguyen van bo dau): "nghien cuu kieu ko phai long only ma kieu vao co SL/TP theo ti le ay nho ap dung cac filter ... cach
  nay chac ko dca nhung nghien cuu xem co p/a giai phap nao nhe"; "xem ngoai sl/tp con phuong an retail trade nao khac nua ko".
- Da do (CHI THAM KHAO, nen cu KHONG dung lai): PREREG_FAMILY2_TP_SL.md (2026-09-27 + AMENDMENT) -> RESULT_FAMILY2_TP_SL.md; key TP commit
  04f4039; jar sim-jar-tpsl; bundle sim-x1-2021-bundle; profile x1_gs_t170 + DCA_GRID_WEIGHTS=1,1,1,1, DCA_GRID_SCALE=6.0, SIM_ENTRY_SAMPLE_MIN=15
  (nen N0 cd-sel15: n 744, CAGR +17,29 %). N1 TP 0,02 / SL -0,01; N2 0,01 / -0,01; N3 0,03 / -0,015; N4 = N1 + time-stop 24h; tat DCA bang
  WFO_DISABLE_DCA=1; khong dat SIM_TAKE_PROFIT_ONLY. Tieu chi cu: (a) %top-1 <= 15 % VA (b') TF50 > 0 (+ asym, rao appetite, 5 rate + CI).
  Ket qua 0/4: CAGR -20,5..-22,9 %, maxDD -64..-68 %; ly do: TP sat chi phi ~0,6-0,8 %, SL -1 % an lo that, mat duoi thang. Vung SL 5-20 % CHUA do.

## 1. Nen = r1-a3 (cau hinh sat ban dang chay)
- Profile r4_kg0_k16_f015_g155 + OV_R1A3 = {SIM_GATE_ROLLING_MODE=ratio, SIM_GATE_ROLLING_DAYS=90, SIM_GATE_ROLLING_PCT=0.999950829,
  TS_GIVEBACK_RATIO=1.0, SIM_TS_MAX_GAP=0.03, SIM_TS_MAX_GAP_WEAK=0.03, SELECTOR_RANK_TOPK=24, GATE_QUOTA_SKIP_WHEN_FULL=true,
  SIM_LOSER_TS_EXT_HOURS=336, SIM_LOSER_TS_EXT_DAYS=<flags.json "ranges">} (nguon: r1_a3_driver.py OV; gate_ablation_driver.py:396-400;
  gate_skipfull_driver.py:41; /home/ubuntu/claude_master/tsx/flags.json). Profile da co SIM_LOSER_TIME_STOP_HOURS=168, SIM_RATE_PROFIT_STOP_MARKET=0.07,
  SIM_F_BASE=0.015, DCA_GRID_ENABLED=true, DCA_GRID_WEIGHTS=1,1,1,1, DCA_GRID_SCALE=6.0, CONC_CAP_PERCOIN 0,15, SIM_FIX_B2/B3=true.
- Bundle sim-x1-2021-bundle (GA.BUNDLE, gate_ablation_driver.py:396); jar dataset sim-jar-tsx (sha256 cc0f9d11...), code ghi trong
  /home/ubuntu/claude_master/tsx/code_sha.txt = a8690d46 (2026-10-19, feat TS_MKT_EXT); bins S1 A3 (dataset r1-a3-bins + s3-moc-2021bins, sha kiem
  trong kernel); cua so 2021-07-01..2025-12-30 (sim_end_date 20251231, ticker_min_days 1826).
- Seed: danh sach 8 seed = A1, S7, S13, S21, S99, S123, S777, S2024 (gate_skipfull_driver.py:37). 42 KHONG co trong danh sach => theo luat MASTER
  lay 2 seed DAU = **A1 va S7** (trung voi "7"). Seed = bo pred gate p15 khac nhau (G.pred_of; A1 dung template goc, S7 patch pred_ds).
- Moc tham chieu: r1-a3-a1 md5 printDone 8986d332..., n 3 622, eq 145 391, 2 381 s; r1-a3-s7 md5 083e3de0..., n 3 548, eq 138 042, 2 193 s.

## 2. Co che sim (jar a8690d46; SimulatorMarketLevelTicker1MStopLoss)
- Moi nen 1 PHUT, cum dang giu: PRE_ARM_SL -> LOSER_TIME_STOP (+ hoan X14 neu ngay co co) -> COND_EXIT -> TP -> arm/trailing.
- SL: bar.low <= firstEntry x (1 + SIM_PRE_ARM_SL) => thoat min(stop, open, close); chi cum CHUA arm. TP: bar.close >= firstEntry x (1 + TP) =>
  thoat DUNG muc TP. Cung nen SL va TP => SL thang. Time-stop: min(open, close). Log "PREARM_SL sym=" / "TAKEPROFIT sym=".
- Key trong Configs @a8690d46: TAKE_PROFIT_RATE :188 (parse :947), TAKE_PROFIT_ONLY :190 (:948), PRE_ARM_SL :512 (:946), LOSER_TIME_STOP_HOURS :499
  (:943), LOSER_TS_EXT_HOURS :166 mac dinh 0 (:922-923), WFO_DISABLE_DCA :359 (env INFRA, qua extra_env), F_BASE :155 (:914).

## 3. Sizing + tat DCA (ca hai nhanh cho moi o)
- managerBudget = equity x F_BASE x clamp(1 - U/0,60) / tong trong so; sim nhan gridLegWeightRatio = w x DCA_GRID_SCALE khi FIX_B2 (DcaUtils @a8690d46).
- S1: giu profile (1,1,1,1 ; SCALE 6 ; F_BASE 0,015) + extra_env WFO_DISABLE_DCA=1 => leg 2,25 % x throttle.
- S2: overrides DCA_GRID_WEIGHTS=1,0,0,0 + SIM_F_BASE=0.0075 (+ extra_env WFO_DISABLE_DCA=1, de nghi them cho dong nhat; MASTER co the bo) =>
  leg = equity x 0,0075 x 6 x throttle = 4,5 % x throttle. CAM DCA_GRID_ENABLED=false (bay: leg 0,375 %, mat SCALE).
- Da kiem (doc code): WFO_DISABLE_DCA chan CA leg grid: DcaProcessor.getDCA tra rong tai :28-30 truoc nhanh grid :40-41, va moi leg DCA trong sim
  di qua getDCA (sim @a8690d46 :367 leg theo level, :398 DCA lo lon). Sim KHONG co tran 4,5 % rieng (khong co hang 0.045; tran 4,5 % chi o
  LiveProfileC3 duong live); CONC_CAP_PERCOIN 15 % ap moi leg => leg 4,5 % KHONG bi cat (1 coin 1 vi the).

## 4. Luoi (24 cau hinh moi + 1 nen), moi cau hinh x 2 seed
Nhanh A (SL + TP, khong arm, TAT X14): them SIM_PRE_ARM_SL, SIM_TAKE_PROFIT_RATE, SIM_TAKE_PROFIT_ONLY=true; BO hai key SIM_LOSER_TS_EXT_HOURS va
SIM_LOSER_TS_EXT_DAYS khoi overrides (mac dinh 0 = tat X14); time-stop 168h (profile).
Nhanh B (SL + trailing arm 0,07 / gap 0,03, khong TP, GIU X14): them SIM_PRE_ARM_SL; khong khai TP; giu nguyen OV_R1A3.
| ten | SIM_PRE_ARM_SL | SIM_TAKE_PROFIT_RATE | SIM_TAKE_PROFIT_ONLY | X14 | sizing |
|---|---|---|---|---|---|
| A05R05-S1/S2 | -0.05 | 0.025 | true | bo | S1 / S2 |
| A05R1-S1/S2 | -0.05 | 0.05 | true | bo | S1 / S2 |
| A05R2-S1/S2 | -0.05 | 0.10 | true | bo | S1 / S2 |
| A10R05-S1/S2 | -0.10 | 0.05 | true | bo | S1 / S2 |
| A10R1-S1/S2 | -0.10 | 0.10 | true | bo | S1 / S2 |
| A10R2-S1/S2 | -0.10 | 0.20 | true | bo | S1 / S2 |
| A20R05-S1/S2 | -0.20 | 0.10 | true | bo | S1 / S2 |
| A20R1-S1/S2 | -0.20 | 0.20 | true | bo | S1 / S2 |
| A20R2-S1/S2 | -0.20 | 0.40 | true | bo | S1 / S2 |
| B05-S1/S2 | -0.05 | (khong) | (khong) | giu | S1 / S2 |
| B10-S1/S2 | -0.10 | (khong) | (khong) | giu | S1 / S2 |
| B20-S1/S2 | -0.20 | (khong) | (khong) | giu | S1 / S2 |
| NEN | (khong) | (khong) | (khong) | giu | profile, khong WFO_DISABLE_DCA |
S1 = extra_env {WFO_DISABLE_DCA: "1"}; S2 = them overrides DCA_GRID_WEIGHTS="1,0,0,0", SIM_F_BASE=0.0075 + extra_env {WFO_DISABLE_DCA: "1"}.
Tag: f2b-<ten>-<seed> (vd f2b-A10R1-S2-a1). So kernel: 24 x 2 = 48 + parity nen 2 + smoke 1 = **51**.

## 5. Tieu chi (chot truoc)
- Mot o "DAT" <=> o CA 2 seed (A1, S7): Calmar > nen cung seed VA maxDD (chuoi equity MTM cuoi ngay) <= maxDD nen (khong sau hon) VA
  CAGR >= 0,5 x CAGR nen; VA >= 3/4 nam 2022-2025 co PnL duong o CA 2 seed.
- Bao kem (mo ta, khong quyet dinh): bo cham FAMILY2 cu ((a) %top-1, (b') TF50, asym, 5 rate + CI inflate theo k = 24), so lenh, win%, PnL/lenh,
  phan phoi ly do thoat (TP / SL / time-stop / trailing / X14), U trung binh / toi da, conc 1 coin, so coin "chet", equity (khong phai tieu chi).
- Khong o nao dat => bao owner so thuc. Khong them o / doi luoi / doi seed sau khi thay so. Loi ky thuat => ERRATA, khong sua tieu chi.

## 6. Rui ro / gioi han
- Lech live: live kich stop theo MARK, lay mau ~10 s; sim dung LOW / CLOSE nen 1m (MASTER_CONCLUSION_RLIVE_1124 D1/D2/D8). SL chat => lech lon.
- Duong live c3 chua co SL truoc arm / TP (c3live/exit: arm + trailing + time-stop + X14) => len live phai sua jar live (ngoai pham vi).
- TP khop dung muc khi close vuot (bo rau nen). Size co dinh theo von (khong theo rui ro) => o SL khac nhau co rui ro/lenh khac nhau.
- Doi kieu thoat doi U => doi skipFull => doi phan phoi buffer gate rolling => doi so lenh: bao rieng so lenh, khong quy het cho "thoat".
- Chi so Kaggle voi Kaggle (AGENT_RUNBOOK ?0.3); Oracle khong chay sim; DEV <= 2025-12-31, khong doc 2026 (HoldoutSeal; >= 2026-10-01 niem phong).
- Luat nguoi chay: prereg commit truoc (AGENT_RUNBOOK ?0.2, rules/backtest: khong chay working-tree ban); dung tools/kaggle_sim.py + driver da
  duyet, CAM bash driver ad-hoc (CLAUDE.md, ce-buttons); dem slot truoc khi push, FREE = 0 thi dung, 5 slot dung chung (KAGGLE_RULES ?1);
  1 kernel truoc fleet (?6); 12h kill (?2); kernel internet + mapper >= 800 (KAGGLE_SIM ?0.2); khong push git (?0.6); khong sua Java.

## 7. CAN KIEM - trang thai
- (ii) seed + bundle: DA GIAI (muc 1). (iii) WFO_DISABLE_DCA chan grid: DA GIAI (muc 3). (iv) tran 4,5 % / 15 % sim: DA GIAI (muc 3).
- (v) end_date / ticker_min: DA GIAI - ks.submit(..., sim_end_date="20251231", ticker_min_days=1826) (tools/kaggle_sim.py:417-443); driver
  r1-a3 dat san trong cfg (sim_end_date, ticker_min_days = ks.TICKER_MIN_DAYS).
- (vi) jar: code a8690d46 (theo tsx/code_sha.txt) CO ca 3 key (Configs @a8690d46 :946-948) va 04f4039 la to tien cua a8690d46 (git merge-base).
  Viec jar cc0f9d11 that su build tu a8690d46: tai lieu ghi, KHONG kiem duoc bang doc => CAN KIEM BANG SMOKE (muc 9).
- (i) driver: xem muc 8.

## 8. Thay doi driver toi thieu (agent DEV, Python; A1 audit)
research/r1_s1/r1_a3_driver.py hien: OV co dinh (dong ~33), build(seed, arm) dung dict(OV) va extra_env={} (dong 166-195), tag co dinh
"r1-a3-<seed>"; check() so overrides voi tsx-x14-<seed> va push() assert bang nhau (197-215); CLI 4 lenh (218-223). Can (khuyen file moi
research/r1_s1/f2b_driver.py import r1_a3_driver, KHONG sua ban cu):
1. CELLS = dict ten -> (add_ov, drop_keys, extra_env) dung bang muc 4 (sinh tu 1 cho, khong go tay 24 lan).
2. build_f2b(seed, cell): goi build(seed) roi thay cfg["overrides"] = OV + add_ov - drop_keys, cfg["extra_env"], cfg["tag"], folder, ref = f2b-...
   (hoac them tham so tuy chon vao build, mac dinh giu nguyen hanh vi).
3. check_f2b: (a) phan OV_R1A3 (tru drop_keys) phai trung tsx-x14-<seed>; (b) key them chi thuoc whitelist {SIM_PRE_ARM_SL, SIM_TAKE_PROFIT_RATE,
   SIM_TAKE_PROFIT_ONLY, DCA_GRID_WEIGHTS, SIM_F_BASE}; (c) extra_env chi {WFO_DISABLE_DCA}; (d) jar_ds = sim-jar-tsx.
4. Lenh: parity <seed> (cell NEN, tag f2b-nen-<seed>) -> fetch va so md5 printDone voi r1-a3-<seed> (8986d332 / 083e3de0); lech => DUNG.
   push <cell> <seed> chi cho phep khi parity seed do DAT; free_slots() truoc moi push.
5. Test don vi (khong mang): overrides sinh ra cua 25 cau hinh dung bang muc 4; NEN == OV r1-a3 tung byte; kernel-metadata giong r1-a3 tru tag.

## 9. Thu tu thuc hien
1. DEV mo rong driver (muc 8) + test -> 2. A1 audit driver -> 3. SMOKE 1 kernel A10R1-S1 seed A1: DAT khi log JAR_SHA256 = cc0f9d11..., mapper >= 800,
   co dong "TAKEPROFIT sym=" va "PREARM_SL sym=" > 0, printDone co TAKE_PROFIT_DONE voi profit = +10,000 % (+-1e-4), khong leg DCA_LEVEL1, khong
   dong log X14 defer (tsxDeferTicks = 0) -> 4. Parity NEN 2 seed (md5 trung r1-a3) -> 5. Luoi 48 kernel (5 slot, ~37-40 phut/kernel, ~10 dot,
   ~7-8 h neu slot trong) -> 6. A1 audit ket qua -> 7. Bao owner.

## 10. Lenh mau (CHI VIET; driver f2b chua ton tai)
cd ~/src/BinanceFuturesJava && python3 research/r1_s1/f2b_driver.py smoke A10R1-S1 A1
cd ~/src/BinanceFuturesJava && python3 research/r1_s1/f2b_driver.py parity A1 && python3 research/r1_s1/f2b_driver.py parity S7
cd ~/src/BinanceFuturesJava && python3 research/r1_s1/f2b_driver.py push A10R1-S2 S7
cd ~/src/BinanceFuturesJava && python3 -c "from tools import kaggle_sim as ks; ks.wait([ks.kernel_ref('f2b-A10R1-S2-s7')]); ks.fetch('f2b-A10R1-S2-s7')"

## 11. Chot cua MASTER (2026-11-26, truoc khi co bat ky kernel nao)
- Ban nay do agent ra soat soan theo chi dao cua MASTER, MASTER da doc va duyet. S2 CO them extra_env WFO_DISABLE_DCA=1 (dong nhat voi S1).
- Tong so phep thu: 24 o x 2 seed. Hai seed A1, S7 la hai seed dau cua danh sach 8 seed (khong chon theo ket qua).
- Pham vi: day la nghien cuu ben LONG, tach khoi chuong trinh SHORT LEVZ. Khong lien quan toi bot dang chay; khong doi jar / cau hinh live.
