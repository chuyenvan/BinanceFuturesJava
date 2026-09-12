# PRE-REG — LIVE_EQ_SIM: dong bo NHANH SHADOW/ENTRY-MOI cua live sang net015 (khop SIM)

Ngay 2026-09-12. Tiep noi docs/AUDIT_SELECTOR_MODEL_PARITY.md + docs/RESULT_SELECTOR_NET015_GATE.md.
Chi Oracle. KHONG SSH 242, KHONG git push, KHONG sua sim baseline, KHONG deploy, KHONG train, KHONG tune.

## 1. Muc tieu + scope
Dua TANG-1 (loc universe/pool + maxThres cho ENTRY MOI) va BAN LE trailing STRONG/WEAK cua nhanh
SHADOW/PAPER ve net015 cho KHOP SIM (universe tu net015 + maxThres tren score net015 + trailing hinge
theo net015). GIU NGUYEN duong Funding cho vi the LEGACY THAT (62 vi the):
- Gate + rank DA net015/S1 (giu nguyen, khong dung toi).
- Duong dong tien THAT (Funding pNoPump + luat dong HEAD) TUYET DOI khong doi.

## 2. HAI FLAG MOI (default OFF = byte-identical HEAD)
- SELECTOR_TIER1_NET015 (tien to SELECTOR_, doc 1 lan qua Cfg.get o SelectorTier1Source):
  ON => tang-1 loop dung net015-raw (1 - P(win), Net015ValueLive tren CUNG float[45] da cho vao
  Funding_Classifier) lam diem so cho selectorRankPool + maxThres + sortedCandidates. Funding VAN
  chay: LATEST_SEL_PNOPUMP/symbol2FundingPred/selPnp GIU preds[0] (Funding) cho legacy. net015 hong
  => BO ung vien tang-1 (KHONG thay bang pNoPump), giong luat C3.
- TRAIL_HINGE_NET015 (tien to TRAIL_, doc 1 lan qua Cfg.get o TrailHingeSource):
  ON => ban le trailing STRONG/WEAK cua vi the SHADOW (ShadowBookC3.trailRate) dung net015-mapped
  cua symbol (LATEST_SEL_MAPPRED = DUNG gia tri gate/sim) thay symbolPred luc mo.

## 3. TACH LEGACY vs SHADOW o duong trailing (AN TOAN)
- Vi the THAT (legacy): trailing qua BinanceOrderTradingManager.tsGap -> doc LATEST_SEL_PNOPUMP
  (Funding pNoPump) -> calRateLossDynamicBuyPNoPump. KHONG dung toi -> VAN Funding.
- Vi the SHADOW/PAPER: trailing qua ShadowBookC3.trailRate (LOP KHAC HAN). Flag chi tac dong o day.
- LegacySymbols skip trong vong entry giay => shadow book KHONG bao gio giu symbol legacy.
=> Tach theo LOP, an toan tuyet doi; flag KHONG the cham vi the that.

## 4. CONG BAT BUOC (parity fail => DUNG + revert + bao)
- (a) sim byte-identical: printDone.csv cua X1_C3_FULL (profile x1_c3_full, flag VANG => OFF) md5 =
  2478e90d4e6147bf4cc64f75967ef47d (= baseline X1_C3_FULL_PARITY_R, b:111428, n=2266).
  Sim KHONG goi DetectEntry/ShadowBookC3/Net015 (chi comment) nen doi live KHONG cham sim; cong (a)
  chung minh khong pha code dung chung (Configs/TradeUtils/EntryGate KHONG sua).
- (b) mvn -o package (test all) PASS + jar build duoc.
- (c) probe wiring: tang-1 + hinge (khi ON) doc DUNG Net015ValueLive.pwin — cung model powering gate
  (buildValueMap/buildRawNet015). Net015ValueLive vs bins predwf_G015x26 = spearman 1.000000, max|d|
  4.77e-07 (RESULT_SELECTOR_NET015_GATE cong (c) + L4ReplayHarness /home/ubuntu/l4/pwin_java.f32).
  => gia tri net015 nhanh shadow = net015 gate, spearman ~1 by construction.
Ghi chu: KHONG chay sim bien the ON de "toi uu" — day la dong bo, khong tim alpha. Full parity
map-level tang-1 (LiveBuildMap, can S1 rank) van vuong blocker OI 2 thang tren 242 (nhu audit).

## 5. Luat cung
Chi Oracle. KHONG cham 242, KHONG push, KHONG sua sim baseline, KHONG deploy, KHONG train, KHONG tune.
Jar deploy THAT: user tu build (PrivateConfig that). Parity fail => dung + revert + bao.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_011zpgT8SsGrmcqzxbC93PQT
