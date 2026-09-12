# PRE-REG — tier-1: nguon symbolPred cua GATE LIVE tu Funding_Classifier -> net015-raw

Ngay 2026-09-12. Tiep noi `docs/AUDIT_SELECTOR_MODEL_PARITY.md` (master duyet GO).
KHONG SSH 242, KHONG git push, KHONG sua sim baseline, KHONG deploy, KHONG tune.

## 1. Muc tieu + scope
- Dua nguon `symbolPred` ma **gate live** (EntryGate.threshold trong duong
  DetectEntrySignal2TradeNormal) dung tu `Funding_Classifier_Final.onnx` (pNoPump)
  sang **net015-RAW** = `1 - P(win)` cua `Net015ValueLive` (onnx x26 fold cut20251001).
- **RAW**, KHONG quantile-map (map can S1 rank / OI history — de tier-2).
- **LIVE-ONLY**. Sim (SimulatorMarketLevelTicker1MStopLoss) KHONG doi 1 byte.
- Ly do: audit do lech LON — Funding_Classifier admit ~10x nhieu hon net015
  (20.49% vs 2.01% slot top-8, 20% quyet dinh doi). Muc tieu tier-1: dong khe admit.

## 2. XAC DINH: CONFIG-ONLY hay CAN-REBUILD
**CAN-REBUILD (can sua code).** Ly do doc thang tu duong code
(DetectEntrySignal2TradeNormal:380):
```java
Float symbolPred = s1Order ? selMapPred.get(symbol) : entry.getKey();
```
Chi co HAI nguon ton tai: `entry.getKey()` = pNoPump (khong co flag), va
`selMapPred` = net015 DA quantile-map (chi khi `LIVE_PROFILE=c3_shadow` + co S1).
**Khong co duong net015-RAW, khong co flag nao bat duoc no bang config.** => phai
them code (mot flag moi + nhanh tinh net015-raw). Rebuild jar.

## 3. Thiet ke — SAU 1 FLAG MOI, default OFF (byte-safe)
- Flag moi: key `SELECTOR_GATE_NET015_RAW` (tien to `SELECTOR_` = tham so giao dich,
  doc qua `Cfg.get`; khong khai / khac "true"/"1" => OFF). Doc 1 LAN luc class nap
  (class `tradecore/selector/GateValueSource.java`), khong doc trong vong nong.
- OFF (mac dinh, gom sim + live hien tai): khong nhanh moi nao chay =>
  **hanh vi byte-identical HEAD**.
- ON (chi tac dung khi `!s1Order`, tuc khong dung C3 mapped): sau khi co pool selPool,
  tinh net015-raw cho tung coin (`Net015ValueLive.pwin` tren `selFeat45`), **re-key**
  selPool theo `1-pwin` (tang dan, thap=tot) => rank + top-K + `symbolPred` (gate +
  trailing) deu la net015-raw. Chua san sang (model hong / thieu feature) => BO TICK
  (khong thay bang pNoPump), giong luat C3.
- `selFeat45` phai duoc nap khi flag ON (hien chi nap khi `LiveProfileC3.on()`): doi
  dieu kien thanh `LiveProfileC3.on() || GateValueSource.net015Raw()` (byte-safe khi ca hai OFF).

## 4. CONG BAT BUOC truoc deploy
- (a) **sim byte-identical**: `printDone.csv` cua `X1_C3_FULL` (profile x1_c3_full,
  flag VANG => OFF) md5 = `2478e90d4e6147bf4cc64f75967ef47d` (= baseline
  X1_C3_FULL_PARITY_R). Chung minh KHONG dung sim.
- (b) `mvn -o -q clean package` (test all) PASS + jar build duoc.
- (c) **wiring**: net015 chay trong JAVA (`Net015ValueLive`, dung lop ma flag goi) ==
  net015 bins `predwf_G015x26` tren cung candidate, spearman ~1. (Da co artifact
  `L4ReplayHarness` -> `/home/ubuntu/l4/pwin_java.f32` vs `rows.bin`.)
- (d) **admit rate**: khi symbolPred = net015-raw, admit top-8 ~2% (tu 20.49% cua
  Funding_Classifier), dyn_thr khop net015 (`docs/AUDIT_SELECTOR_MODEL_PARITY.md` 2.4).
- Bat ky cong FAIL => DUNG, revert, bao. Khong tune.

## 5. Luat cung
Chi Oracle. KHONG cham 242, KHONG push, KHONG sua sim baseline, KHONG deploy, KHONG train,
KHONG tune. Jar deploy that user tu build (PrivateConfig that) — agent KHONG build jar deploy.
