# RESULT_LIVE_EQ_SIM — dong bo tang-1 universe + trailing hinge nhanh SHADOW sang net015 (khop SIM)

Pre-reg: docs/prereg/PREREG_LIVE_EQ_SIM.md. Code SHA base HEAD aa46fb1 (branch module). Chi Oracle.
KHONG cham 242, KHONG push, KHONG sua sim baseline, KHONG deploy, KHONG tune.

## 1. RECON (file:dong THAT)
- Tang-1 loc universe (Funding pNoPump -> maxThres -> pool): DetectEntrySignal2TradeNormal.java
  660-681 (predictBatch; maxThres 661; LATEST_SEL_PNOPUMP.put 666; selectorRankPool.put 667;
  preds[0]>maxThres 676; sortedCandidates.put 680).
- Chon pool + gate value: DetectEntry 340 (selPool = TOPK>0 ? selectorRankPool : sortedCandidates),
  350-352 (EntryPoolGate.choose s1Pool), 361 buildValueMap (net015-mapped selMapPred), 369-383
  (SELECTOR_GATE_NET015_RAW hunk co san), 398 (symbolPred = s1Order ? selMapPred : entry.getKey()).
- Trailing hinge STRONG/WEAK (ban le TS_PNOPUMP_WEAK_THR=0.29): TradeUtils.calRateLossDynamicBuyPNoPump
  (TradeUtils.java:28) — KHONG SUA. Callers:
  * SHADOW/PAPER: ShadowBookC3.trailRate (ShadowBookC3.java:232) <- vi tri dong bo.
  * LEGACY THAT: BinanceOrderTradingManager.tsGap:485 doc LATEST_SEL_PNOPUMP (Funding) -> :490. KHONG SUA.
- Legacy real-money: DetectEntry:85-104 (LATEST_SEL_PNOPUMP + paperSymbolPred; ghi chu 90-91 "duong THAT
  van dung pNoPump Funding") — GIU NGUYEN. LegacySymbols.isLegacySymbol skip trong vong entry giay
  (DetectEntry ~395) => shadow book KHONG bao gio giu symbol legacy.
- net015 value provider: Net015ValueLive.java (pwin tren float[45], P(win)=probabilities[:,1]).
- Cfg key: SELECTOR_ va TRAIL_ deu la TRADING_PREFIXES (Cfg.java:54-56) -> doc qua profile/env, null=OFF.

## 2. HAI FLAG MOI (default OFF = byte-identical HEAD)
- SelectorTier1Source.java (MOI) — key SELECTOR_TIER1_NET015. ON: DetectEntry tang-1 loop dung
  net015-raw (1 - P(win), buildNet015Tier1() qua Net015ValueLive tren CUNG featureArrays[45]) lam
  diem so cho selectorRankPool + maxThres + sortedCandidates. Funding VAN chay: symbol2FundingPred /
  LATEST_SEL_PNOPUMP / selPnp GIU preds[0] (Funding) -> legacy khong doi. net015 hong => BO ung vien
  tang-1 (KHONG thay bang pNoPump), giong luat C3.
- TrailHingeSource.java (MOI) — key TRAIL_HINGE_NET015. ON: ShadowBookC3.trailRate dung
  net015-mapped cua symbol (DetectEntry.LATEST_SEL_MAPPRED = DUNG gia tri gate/sim) thay symbolPred
  luc mo. Chu ky trailRate(peak, symbolPred) giu nguyen (overload delegate) => caller cu byte-safe;
  them overload trailRate(peak, symbolPred, symbol) + 2 caller (ShadowBookC3:273,288) truyen p.symbol.
Diff: DetectEntry +52/-8, ShadowBookC3 +22/-4, 2 file class moi. TradeUtils/Configs/EntryGate/sim: KHONG dung toi.

## 3. CONG (a)(b)(c) — DEU PASS
- (a) SIM parity byte-identical (flag VANG => OFF): devrun X1_C3_FULL_LIVEQSIM_OFF (profile
  x1_c3_full.properties, reuse dataset /home/ubuntu/wfo_ds_x1) -> printDone.csv:
  md5 = 2478e90d4e6147bf4cc64f75967ef47d = baseline X1_C3_FULL_PARITY_R. b:111428, done:2266/2266,
  2267 dong. [GATE] n_cand=15162720 n_pass=2056. => BYTE-IDENTICAL HEAD.
- (b) mvn -o package: Tests run 127, Failures 0, Errors 0, Skipped 0. BUILD SUCCESS. jar build duoc
  (target/binance-java-sdk-1.2.4.jar, Oracle STUB-key, chi de test/parity).
- (c) probe wiring net015: tang-1 (buildNet015Tier1) va hinge (LATEST_SEL_MAPPRED) doc CUNG model
  net015 (Net015ValueLive.pwin) ma gate dang dung (buildValueMap/buildRawNet015). Net015ValueLive-in-Java
  vs bins predwf_G015x26: spearman 1.000000, max|d| 4.77e-07 (artifact /home/ubuntu/l4/pwin_java.f32 vs
  rows.bin; RESULT_SELECTOR_NET015_GATE cong (c)). => gia tri net015 nhanh shadow = net015 gate,
  spearman ~1 BY CONSTRUCTION. (KHONG chay sim bien the ON: day la dong bo, khong tim alpha.)

## 4. LEGACY (62 vi the THAT) DUOC GIU NGUYEN THE NAO
- Duong dong tien THAT KHONG di qua bat ky nhanh nao 2 flag cham:
  * Trailing that: BinanceOrderTradingManager.tsGap -> LATEST_SEL_PNOPUMP (Funding pNoPump) -> KHONG SUA.
  * Luat dong / paperSymbolPred / LATEST_SEL_PNOPUMP init: KHONG SUA. Tang-1 (flag ON) VAN ghi
    LATEST_SEL_PNOPUMP = preds[0] (Funding) => nuoi legacy nhu cu.
  * Ban le trailing shadow o LOP KHAC (ShadowBookC3); LegacySymbols bi skip khoi vong entry giay
    => shadow book khong chua symbol legacy => flag KHONG the cham vi the that.
- Tach legacy-vs-shadow o trailing = tach theo LOP (BinanceOrderTradingManager vs ShadowBookC3):
  AN TOAN, khong can co runtime; xac nhan qua LegacyIsolationTest (15) + ShadowBookC3Test PASS.

## 5. BUOC USER CAN DE BAT (env flag + rebuild jar may user + deploy)
1. Rebuild jar THAT tren may user (PrivateConfig that; agent KHONG build jar deploy):
   cd <repo>; /path/mvn -o package
2. Bat co (chon 1 hoac ca 2) qua env HOAC them vao profile giao dich (neu chay TRADING_PROFILE):
   - env: export SELECTOR_TIER1_NET015=true ; export TRAIL_HINGE_NET015=true
   - profile: them dong SELECTOR_TIER1_NET015=true / TRAIL_HINGE_NET015=true
   LUU Y fail-fast: neu da dat TRADING_PROFILE thi PHAI khai trong profile (dat qua env se DUNG cung
   vi trung nguon tham so giao dich). Model onnx net015: mac dinh
   /home/ubuntu/g3x26/g015x26_f15_cut20251001.onnx (doi qua NET015_MODEL_ONNX neu can).
3. Restart tien trinh live (nen bundle voi 1 restart khac). Default (khong dat) = OFF = byte-identical.

## 6. Luu y / lech
- Tang-1 net015 la RAW (khong quantile-map). Full parity map-level tang-1 (LiveBuildMap) can S1 rank
  (OI history 2 thang tren 242) = tier-2, VAN VUONG blocker OI nhu docs/audit/AUDIT_SELECTOR_MODEL_PARITY.md.
  Raw bao toan RANK trong tick (quantile-map don dieu) nen khop cach sim ap maxThres tren score net015.
- maxThres GIU NGUYEN hang so (KHONG tune) — chi doi NGUON diem so tu Funding sang net015, dung nhu sim.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_011zpgT8SsGrmcqzxbC93PQT
