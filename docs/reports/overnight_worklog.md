# OVERNIGHT WORKLOG - Ra soat & dung lai luong co provenance (2026-07-01 dem)

Mandate (Uni ngu): gac tinh chinh, tap trung AUDIT -> DOC -> VERSION -> danh dau du lieu -> don/archive tai lieu -> dung lai WFO co day du vet. Khong dung tru khi gap quyet dinh PnL/phuong phap khong the tu quyet.

## Tien do
- [x] PHASE A - Audit luong end-to-end (doc-only).
- [x] PHASE B - docs/PIPELINE_PROVENANCE.md (commit 435d98e).
- [x] PHASE C - Tich hop he tai lieu + sua framing leakage dung L0 (commit b605dd3). KHONG archive bua: docs von to chuc tot, chi bo sung + lien ket.
- [x] PHASE D - Dong dau provenance code: WfoDataset manifest (commit f37e325) + StrategyWfoTask env-config window (commit aeb2d30). Compile OK.
- [~] PHASE E - WFO leak-free: THIET KE + RUNBOOK + dua code train vao git (dong GAP #4). KHONG tu chay rebuild vi phai viet code inference moi (script sinh predict full-history khong co trong git) -> rui ro artifact "sach gia". De runbook san sang cho Uni greenlight.

## TOM TAT BUOI SANG (doc truoc)
DA XONG (core mandate - traceability):
1. PIPELINE_PROVENANCE.md - ban do luong + registry artifact + leakage + gaps + quy uoc version.
2. Sua framing leakage dung doctrine L0 (strategy-WFO loai 1 dung pred co dinh HOP LE cho cau hoi tham-so; dong gop moi: con so OOS tuyet doi bi thoi phong ~13/15 window).
3. WfoDataset dong dau provenance (git SHA + model + leakFreeFrom) - dataset tuong lai tu mang vet.
4. Code train model VAO GIT (ml/training/) - dong GAP #4 "khong luu code model".
5. docs/reports/LEAKFREE_WFO_RUNBOOK.md - cach dung strategy-WFO leak-free.

CAN UNI QUYET (mo khoa rebuild leak-free): xem RUNBOOK muc 5 (4 diem, deu co mac dinh an toan).
VIEC LON CON LAI (da-phien): viet code funding per-fold + gate reuse -> set v3wf -> dataset_wf -> chay WFO -> so verdict.

## Phat hien lon
LEAKAGE trong STRATEGY WFO (xac nhan bang chung): funding selector v2 train<=2024-12 nhung sinh prediction full-history 2021->2026 bang chinh model do -> ~13/15 window OOS truoc 2025-06 la in-sample (ro ri). Chi ~3 window cuoi sach. "88% OOS-duong" phan lon khong hop le.
Tai san sach ton tai nhung CHUA noi vao strategy-WFO: gate per-fold (wfo_models/fold_*, train_gate_fold.py). Funding KHONG co ban per-fold (gap chinh).

## Quyet dinh tu xu ly (ghi de Uni review)
- Viet doc ASCII thuan (ky tu box-drawing lam hong Write transport).
- KHONG tu chay rebuild leak-free WFO tu dau neu smoke khong sach 100% - de tranh tao artifact "sach gia" (dung tinh than do khong doan). Uu tien A-D chac chan + chuan bi san E.

## UPDATE 2026-07-02 (Uni day, review)
- Uni DUYET ca 4 diem RUNBOOK muc 5 (tham so per-fold=single; purge 72h; dung gate leak-free; chap nhan verdict leak-free lam chuan). => rebuild leak-free da duoc greenlight ve phuong phap.
- Uni hoi "sao phai export lai data": DO LAI -> data feature/label/OI train full-history CON DU tren Oracle (train_ff 22 quy + train_label 9.4GB + oi_percoin_full 3.4GB). => KHONG can export lai feature (dung roadmap "1 lan dung chung"). Chi regenerate PREDICTION (per-fold) + rebuild WFO dataset (chi doi pred/funding, market giu nguyen). Da sua RUNBOOK muc 1 + 6.

## UPDATE 2026-07-02 (BUOC 1-2 leak-free: SMOKE PASS + full run launched)
- BUOC 1: viet ml/training/gen_funding_wf_predictions.py (walk-forward per-fold, assert chong leak, xuat 26B).
- OOM lan 1: OI 113M dong (cadence 5m) lam OOM SIGKILL (do exit 137). Fix: grid-filter OI ve 15m (lossless
  cho merge tai moc 15m) cat 113M->38M. Fix 1 dong.
- SMOKE 1 fold PASS: exit 0, features 3.9M merge OK, CUTOFFS=17 (khop WFO train-12), fold 0 train ts_max
  2021-12-28<cutoff 2022-01-01 (purge 72h giu), bin 26.0B/rec dung, prob in [0,1] nan%=0 endianness dung.
- BUOC 2: launch full 17-fold detached (OUT_DIR=wf_pred). Uoc ~1-1.5h. Cho xong roi BUOC 3 (gate) + 4 (dataset+WFO).

## UPDATE 2026-07-02 (BUOC 2 xong, BUOC 3-4 CHAN - can Uni quyet infra)
- BUOC 2 funding leak-free: 17 fold chay xong tren Oracle -> predict_wf_*.bin (~104MB, phu 2022-01..2026-03),
  leak-assert giu moi fold. Deliverable core HOAN TAT + validate.
- BUOC 3-4 CHAN boi infra (do duoc, khong the tu quyet an toan):
  1. 226 disk 97% day (3.3G trong) -> nap set v3wf + export dataset rui ro lap dia; giai phong = xoa data (pha huy).
  2. gate leak-free set ai_pred_market_gate_wfo CHUA nap Aerospike (chi _smoke); full o wfo_gate_pred.csv.
  3. Option B (bypass Aerospike, dung tren Oracle): pred.bin tu wfo_gate_pred.csv = TAM THUONG (khop format
     [ts][predReturn15M][predRisk4H]). NHUNG funding.bin doi tai tao serialization Snappy "data" blob +
     decodeFundingMapToPrimitiveArray (KHAC 26B predict bin) -> rui ro sai format cao. Chua an toan unattended.
- => DUNG thuc thi BUOC 3-4. Cho Uni quyet: (a) giai phong dia 226 de di Path A, HOAC (b) duyet dau tu lam
  Option B chac chan (co verify md5 vs funding.bin cu), HOAC (c) scope window (khuyen 2024+). Xem RUNBOOK.

## UPDATE 2026-07-02 (DINH CHINH: blocker 226 SAI - Aerospike o Oracle-local)
- Uni chi ra: pipeline dung Aerospike LOCAL tren Oracle, KHONG phai 226. Do lai: config active
  ~/java/simulator/config.properties co AEROSPIKE_HOST_226=127.0.0.1:3222, AEROSPIKE_NAMESPACE=test
  -> getClient226() tren Oracle = local. asd chay tren Oracle (port 3222). Oracle disk 65G trong (56%).
  => "blocker 226 disk 97%" cua minh SAI (kiem nham server 226). BUOC 3-4 lam het tren Oracle, khong ket dia.
- BUOC 2 validate: 17/17 bin, tat ca mod26=0, phu 2022-01..2026-01. EXIT_CODE=0.
- BUOC 3a: load funding -> Aerospike Oracle set funding_selector_pred_1m_v3wf. Smoke 1 file PASS (511k rec,
  0 loi, connect 127.0.0.1). Full 17 file dang chay (pid 89894).
- Plan iteration 1: funding-leak-free (giu market pred hien tai) -> rebuild dataset -> WFO 17 window ->
  so verdict vs ban ro ri (cb0032b). Co lap tac dong fix funding. Gate leak-free = iteration sau.

## UPDATE 2026-07-02 (BUOC 4 chan boi scanAll + phat hien provenance rot)
DA XONG: BUOC 1-2 (funding leak-free 17 fold, validate). BUOC 3a: nap v3wf -> Oracle-local 127.0.0.1 ns=test
(3.72M rec, 0 loi) - NHUNG co the nham asd/ns (xem duoi).

CHAN o BUOC 4 (export dataset) + PHAT HIEN QUAN TRONG (do duoc, dung tinh than provenance):
1. ExportWfoDataset scanAll -> "Unsupported Server Feature" tren asd Oracle 127.0.0.1:3222. JAR CU CUNG LOI
   (market=0 pred=0 funding=0) -> khong phai build cua Claude; la tinh trang asd/client hien tai. Can Uni:
   asd Oracle co ho tro scanAll khong? Dataset cu (2026-06-29) export o dau (226? asd khac?)?
2. Set DOC THAT la HANG SO hardcode trong DataManagerAerospikeFloatSim, KHAC nhan manifest:
   - funding: AEROSPIKE_SET_NAME_FUNDING_PRED = "funding_pred_1m_v5" (dong 49) - KHONG phai
     funding_selector_pred_1m_v2 (nhan manifest) hay v3wf. => env WFO_SET_FUNDING cua Claude CHI doi nhan
     manifest, KHONG doi set doc that. Muon doc v3wf phai sua hang so nay (env-configurable) + rebuild.
   - market: AEROSPIKE_SET_NAME_MARKET_DATA = "market_data_object" (nhan manifest ghi "market_data").
   => PROVENANCE ROT that: manifest dataset cu GHI SAI nguon so voi code doc. (Dung van de goc Uni lo.)
3. Set nguon (market_data_object, ai_pred_market_full_basket_v2, funding_pred_1m_v5) thay tren 226 ns=ticker;
   Oracle config ns=test -> co the v3wf nap nham cho. Can Uni xac nhan topology: asd/ns nao giu set nguon.

CAN UNI QUYET/CHI DAN:
- Topology: export doc tu asd nao (Oracle-local hay 226), ns gi? Vi sao scanAll loi tren Oracle asd?
- Neu dong y: Claude sua AEROSPIKE_SET_NAME_FUNDING_PRED (+ market/pred) thanh env-configurable that su
  (khong chi manifest), nap v3wf dung asd/ns, va giai quyet scanAll (co the export tren 226 neu asd do scan duoc).
- Funding leak-free bins (~/claudedata/wf_pred, 17 file) + set v3wf da san sang, chi cho thong topology.
