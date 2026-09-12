# RESULT_SELECTOR_NET015_GATE — tier-1 net015-raw gate (LUOI AN TOAN fallback)

Pre-reg: docs/PREREG_SELECTOR_NET015_GATE.md. Code: GateValueSource.java (moi) + 3 hunk
DetectEntrySignal2TradeNormal.java (flag SELECTOR_GATE_NET015_RAW, default OFF).

## 4 cong — DEU PASS
- (a) Sim parity byte-identical: X1_C3_FULL_TIER1OFF printDone md5 = 2478e90d4e6147bf4cc64f75967ef47d
      = baseline X1_C3_FULL_PARITY_R, b:111428, n=2266. Code tier-1 co mat, flag OFF => byte-identical.
- (b) mvn -o package: Tests run 125, Failures 0, Errors 0. jar cf4eb162 (Oracle STUB-key, chi de test/parity).
- (c) net015-in-Java (Net015ValueLive) vs bins predwf_G015x26: spearman 1.000000, max|d| 4.77e-07 (agent).
- (d) admit net015 2.01% vs Funding_Classifier 20.49% (offline 2025Q4) — do model, KHONG phai trang thai live.

## DINH CHINH PHAM VI (quan trong)
242 hien tai (LIVE_PROFILE=c3_shadow + S1RankerLive, map khoe): gate DA dung net015-MAPPED
(symbolPred ~0.30, [GATE] thr [0.017..0.023]), map_thieu=0 s1_skip=0 tren 4543 tick => KHONG lan nao
roi ve Funding pNoPump. Vay gate live DA parity voi sim. Nhanh !s1Order (Funding, admit 10x) KHONG chay.
=> tier-1 net015-raw la LUOI AN TOAN cho fallback (khi map/S1 hong, vd OI history hut) => dung net015-raw
thay vi Funding 10x. KHONG phai fix dang active. Con so 10x la counterfactual offline.

## DEPLOY (uu tien THAP, defensive)
Can rebuild jar (doi code) + env SELECTOR_GATE_NET015_RAW=true. Nen BUNDLE voi 1 restart khac neu deploy,
khong can restart rieng. jar deploy THAT: user tu build (PrivateConfig that). Tier-1 KHONG can S1/OI/map.
Full parity map-level = tier-2 (vuong OI 2 thang tren 242).
