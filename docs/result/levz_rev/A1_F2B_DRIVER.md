# A1_F2B_DRIVER - audit doc lap driver FAMILY2B (A1, 2026-11-26)
Doi tuong: ~/claude_master/vz_e1_wt/research/r1_s1/f2b_driver.py (sha256 fd79de9cd2ccace735e9b2ea400eaed0e7491579895a27c8e0601035d3481e70),
test_f2b_driver.py (7bb8a077b16f7232e8cfddf7c3b5d538b73845f6492d4b724423321609022591). Prereg 5f917679 (file worktree == commit).
Khong goi Kaggle, khong java/mvn, khong sua file nao (tru file nay). Moi lenh driver chay voi spy mang + F2B_STATE_DIR tam, -B.

## KET LUAN: PASS-WITH-MINOR (dieu kien: commit driver+test truoc push - muc C1)

## 1. Ngu nghia key tu Java @a8690d46 (tu doc)
- Cfg.get: co TRADING_PROFILE -> key giao dich CHI doc tu file profile; key INFRA (WFO_DISABLE_DCA, SIM_END_DATE, HOLDOUT_UNSEAL...) doc tu ENV.
  Kernel ghi overrides vao prof_run.properties (ten key nguyen van, str(v)) -> Configs doc duoc. extra_env -> env.update sau khi xoa env
  tham so giao dich -> den JVM (WFO_DISABLE_DCA khong co tien to giao dich, khong bi xoa).
- SIM_PRE_ARM_SL (Configs:512, parse :946 Float): chi bat khi < 0 (PreArmSlUtils.enabledVal); duong/0 = TAT (khong loi). Ti le tren firstEntryPrice.
  Kich khi bar.low <= fep*(1+SL), chi khi priceSL==null (chua arm); exit = min(stop, min(open,close)). Log "PREARM_SL sym=".
- SIM_TAKE_PROFIT_RATE (:188, parse :947): >0 bat; dieu kien close >= fep*(1+TP), exit = dung muc TP. Log "TAKEPROFIT sym=", status TAKE_PROFIT_DONE.
- SIM_TAKE_PROFIT_ONLY (:190, parse :948): Boolean.parseBoolean -> "true" dung, "1" = FALSE (comment Configs ghi "=1" la SAI/gay nham).
  tpOnly = TP>0 && ONLY -> bo HAN nhanh arm/updateStatusNew/trailing (sim:1102-1103) -> priceSL luon null -> SL va time-stop luon hieu luc.
- Thu tu 1 nen (sim:1005-1118): PRE_ARM_SL -> LOSER_TIME_STOP(+X14 defer) -> COND_EXIT -> TP -> arm/trailing. Cung nen SL(low) va TP(close): SL thang. KHOP prereg muc 2.
- SIM_LOSER_TIME_STOP_HOURS (:499, parse ~:942): profile 168; ap cum chua arm. Nhanh A: ap suot doi lenh (khong bao gio arm).
- SIM_LOSER_TS_EXT_HOURS mac dinh 0 (:166); profile tsx KHONG co key nay (da kiem prof jar tsx 94f52f2a + prof_run.properties that cua r1-a3-a1:
  2 dong X14 chi den tu overrides) -> bo key = tat X14 that. Dong log "[TSX] extHours=..." CHI in khi EXT_HOURS>0.
- WFO_DISABLE_DCA (:359) = "1".equals(env) -> DcaProcessor.getDCA tra rong (:30) truoc nhanh grid; 2 call-site leg DCA_LEVEL1 (sim:367, :398) deu qua getDCA.
  BIG_DOWN/selector khong mua coin dang giu (symbolLocked = active ids sim:345; selector !isSymbolRunning) -> khong co duong them leg khac.
- Sizing (TradeUtils.managerBudget + sim:1448-1496): leg = equity x F_BASE x clamp(1-U/U_MAX) / sum(DCA_GRID_WEIGHTS) x tierMultiplier x (w0 x SCALE) (FIX_B2).
  U_MAX mac dinh 0.60 (profile khong dat). S1: 0.015x6/4 = 2.25 %; S2 (1,0,0,0): sum=1 -> 0.0075x6/1 = 4.5 %. Khong co tran 4.5 % trong sim. KHOP.
- Nhanh B: TP=0 -> khong TP; arm khi peak >= priceEntry x 1.07 (profile), gap 0.03/0.03 (OV), X14 giu. SL chi truoc arm. KHOP.
- Configs: toan bo khoi parse SIM_* nam trong 1 try/catch -> mot gia tri loi lam BO QUA IM LANG moi key sau no (chi in "SIM env override parse error").
Prereg sai/thieu: (i) cong thuc muc 3 thieu he so tierMultiplier (CoinRankManager.getBudgetMultiplier) - chung moi o, khong doi ket luan;
(ii) muc 9 "tsxDeferTicks = 0": Java KHONG in chu "tsxDeferTicks"; dau hieu dung = KHONG co dong "[TSX] extHours=" (nhanh A);
(iii) muc 10 duong dan lenh sai (~/src khong co research/r1_s1) - DEV da neu; (iv) "TAKE_PROFIT_DONE profit = +10 %" chua biet cot profit
printDone co tru phi khong -> chi smoke moi xac nhan; (v) muc 3 "leg 0,375 %" cho bay DCA_GRID_ENABLED=false: ladder van chia sum(weights) -> voi 1,0,0,0 la 0,75 % (khong anh huong vi da cam).

## 2. Duong overrides/extra_env (doi chieu run that)
- run.py base sinh lai == /home/ubuntu/kaggle_sim/r1-a3-<seed>/run.py DA PUSH (A1, S7) tung byte; run.py f2b chi khac DUNG 1 dong CFG.
- kernel-metadata f2b == r1-a3 tru id/title; id = chuyendinh/sim-f2b-... (khac sim-r1-a3-*). result.json r1-a3 overrides == tsx-x14 (A1, S7),
  SIM_LOSER_TS_EXT_DAYS == flags.json ranges. Profile that dung trong kernel = sim-jar-tsx/prof_r4_kg0_k16_f015_g155.properties (log kernel).

## 3. 12 lenh dry (6 o x A1/S7) vs bang go tay: 12/12 KHOP
A05R05-S1 {SL -0.05, TP 0.025, ONLY true, bo X14, env WFO=1}; A10R1-S2 {-0.10, 0.10, true, bo X14, W 1,0,0,0, FB 0.0075, env};
A20R2-S1 {-0.20, 0.40, true, bo X14, env}; B10-S1 {-0.10, giu X14, env}; B20-S2 {-0.20, giu X14, W, FB, env}; NEN = overrides r1-a3 that, env {}.
Gia tri them deu kieu str; sim_end 20251231; dataset_sources 11 (A1) / 12 (S7, them gate-abl-seed7) == r1-a3, KHONG co dataset 2026
(ticker toi wfo-ticker-2025h2). 0 goi mang, workdir khong doi, khong tao f2b_state. list: 25 dong dung bang.
Duong 2026: SIM_END_DATE env=20251231 + HoldoutSeal (chi mo bang env HOLDOUT_UNSEAL - bi chan boi whitelist extra_env) + dataset khong co 2026.

## 4. Test + mutant
test_f2b_driver: 17/17 OK. Mutant (ban copy mktemp): BAT 16/19: TP R2 he so 3; R05 sai; quen bo X14; S2 quen F_BASE; ONLY="1"; SL duong;
seed S13; bo PARITY_OK; parity_ok bo md5; sim_end 20260101; tag NEN = r1-a3; WFO="true"; bo chan FREE=0; R.build ghi workdir that;
them dataset 2026; NEN co extra_env; smoke tag = tag luoi.
SONG 3: M4 xoa FORBIDDEN (tuong duong - whitelist van chan); M13 whitelist them DCA_GRID_SCALE (bi check (a) che, khong test rieng);
M17 bo so jar_sha256 trong parity_compare (khong test) -> NHO.

## 5. Loi
CHAN (quy trinh, khong sua code):
- C1 f2b_driver.py, test_f2b_driver.py, F2B_DEV.md CHUA commit (git status ??) - trai docs/rules/backtest.md:13 "Commit TRUOC khi chay; KHONG chay
  working-tree ban" + prereg muc 6. Sua: MASTER commit (sha trung muc nay) truoc smoke; ghi commit vao pushed/<tag>.json (hien chi ghi PREREG).
NHO:
- N1 f2b_driver.py:450-451 SMOKE_PATS "tsxDeferTicks" khong bao gio khop (Java in "[TSX] extHours=.. deferTicks=") -> dem luon 0, tao an tam gia.
  Sua: thay bang "[TSX] extHours=" (nhanh A phai = 0; NEN/B phai = 1).
- N2 SMOKE_PATS thieu "SIM env override parse error" (phai 0), "HARD SL -10.00%" (DumpConfig xac nhan doc SL), "Loaded Symbol Mapper"; khong tu kiem
  profit TP = +0.10 (doc tay printDone cot profit/status), khong kiem mapper>=800 (result.json symbol_mapper co in).
- N3 :308-315 PARITY_OK chi chua seed + md5 (cong khai trong result.json r1-a3) -> gia mao/sot lai de; khong gan ref/thoi diem/md5 file.
  Sua: parity_ok bam lai out/f2b-nen-<seed>/**/printDone.csv va so md5_ref; luu ref + ts fetch.
- N4 :399 parity mac dinh BLOCKING (ks.wait toi 13 h) - nen doi mac dinh --no-wait (ce-buttons). Co --no-wait (da xac nhan).
- N5 Khong co lenh luoi/hang doi: 48 push tay -> de sinh vong bash ad-hoc (ce-buttons:35). Nen them lenh "grid" (lap cell x seed, free_slots, dung khi FREE=0) hoac di qua pipeline.
- N6 :404 parity: neu out/f2b-nen-<seed>/result.json da ton tai thi bo wait va fetch lai (co the doc version dang chay); ks.fetch khong ghi de sim.out cu.
- N7 Test khong bao M13/M17 (xem muc 4).

## 6. CHUA kiem / chi smoke moi xac nhan
jar cc0f9d11 that build tu a8690d46; cot profit printDone voi TP (+10 % co tru phi?); full.log khong roll (200 MB, r1-a3 ~1 MB - an toan);
noi dung bundle sim-x1-2021-bundle co du lieu >= 2026 hay khong (sim bi chan boi SIM_END_DATE + HoldoutSeal); tierMultiplier thuc te.

## Vong 2 (2026-11-26) - ban sua N1-N6 + C1
Audit: f2b_driver.py acbcb9de72f4a0871bbe06ba7e090adb265eaf7bd41464cf2b0e94690c820997 (827 dong),
test_f2b_driver.py 4e111e6776330109e8bc5f4c735c8cf4dd23174b3042c92b6400372c6eabdb74 (trung sha MASTER). Ca 3 file van `??` (chua commit).
KET LUAN CUOI: PASS-WITH-MINOR. Khong co loi CHAN trong code. Dieu kien RUN: MASTER commit 2 file dung sha tren (git_guard se chan neu chua).

1. Bang/build/check khong doi: 12 lenh dry (6 o x A1/S7) lai == bang go tay vong 1 (12/12), run.py base == run.py r1-a3 da push, f2b khac 1 dong CFG,
   metadata == r1-a3 tru id/title, id sim-f2b-*. list/dry/status (state rong): 0 goi mang, khong ghi workdir/out/state.
   status: chi goi ks._status khi CO marker chua fetch (mang, chi doc); khong free_slots, khong push/fetch.
2. grid (:704-779): thu tu co dinh CELLS x (A1,S7); bo qua o khi parity_ok(seed) sai; dung khi nrun >= --max-slots hoac NoSlot; marker ghi ngay sau
   push -> goi lai: o da push = DANG_CHAY (ca khi _status loi), _push con chan AlreadyPushed; o LOI khong push lai; fetch chi khi COMPLETE; 1 vong,
   khong sleep. Tag/ref chi f2b-*/sim-f2b-*, _fresh_fetch tu choi slug khong f2b- -> khong cham r1-a3.
3. smoke_check voi log gia: clean PASS; FAIL dung cho parse error, JAR khac (ca khi chi log khac), thieu TAKEPROFIT, thieu PREARM_SL, leg DCA_LEVEL1,
   "[TSX] extHours=336" (nhanh A; nhanh B khong fail), mapper 700, thieu printDone. Log that r1-a3-a1: mapper 863 doc tu full.log + sim.out (dung
   dong "Loaded Symbol Mapper: 863 symbols"), TSX=1, parse_err=0; printDone that dem 63 leg DCA_LEVEL1 (khop).
4. git_guard: `??` / sua sau commit / staged -> NotCommitted (exit 5); khong co bien moi truong vuot rao trong code. Lo hong ly thuyet: git update-index
   --assume-unchanged/--skip-worktree, hoac GIT_DIR/GIT_INDEX_FILE ke thua env; chi canh 2 file (r1_a3_driver da commit, kaggle_sim co assert md5).
5. Test: 35/35 OK tai cho; ban copy 34/35 (test_real_git_state_readonly can repo git - du kien). Mutant phan moi: BAT 14/16 (grid push khi chua parity;
   QUEUED coi la chua push; + bo chong trung; vuot max-slots; smoke bo parse error / TSX / mapper / DCA; git_guard bo file ban; _fresh_fetch dung out cu /
   bo kiem tag; fetch khi chua COMPLETE; kernel loi push lai; parity_ok bo bam dia). LOT 2: NoSlot break->continue (gan tuong duong, chi them goi API);
   _fresh_fetch cho slug r1-a3 (rao phong thu, tag_of khong bao gio sinh).
NHO moi:
- V1 _push :473 khong kiem loi trong response kernels_push (Kaggle tra .error, khong raise) -> marker ghi cho push hong -> o ket DANG_CHAY (STATUS_ERR)
  mai, chiem nrun. Sua: neu getattr(r,"error",None) -> khong ghi marker, raise.
- V2 grid: nrun chi dem o luoi (khong dem f2b-nen / smoke / kernel khac); free_slots goi lien tiep co the tre (kernel vua push chua QUEUED) ->
  nen lay budget = min(max_slots - nrun, free_slots() dau vong).
- V3 smoke nhanh B/NEN khong kiem co dong [TSX] > 0 (X14 phai con) - doc tay.
Chi smoke moi xac nhan: jar cc0f9d11 build tu a8690d46; cot profit TP (+0.10 co tru phi?); dong "HARD SL" co xuat hien khong; Kaggle status ngay sau push.
