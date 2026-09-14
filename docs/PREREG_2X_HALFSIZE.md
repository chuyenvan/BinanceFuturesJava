# PREREG_2X_HALFSIZE — 2x so lenh x 1/2 von/lenh (giu hieu qua ~ T170, rui ro thap hon)

Chot TRUOC khi chay sim. Nen: DEV mo rong 18 fold (2021Q3..2025Q4), dataset `wfo_ds_x1_2021`
(bins baked-in `predwf_map_s1a2_x1_2021`), jar HEAD (KHONG doi code Java, KHONG rebuild logic).
`SIM_END_DATE=20251231`, holdout 2026 NGUYEN VEN. KHONG cham 242 (TICKER_SOURCE=file, doc offline
bin tu WFO_DATA_DIR). KHONG tune (config co dinh duoi day). KHONG git push.

## 1. Y tuong + co hoc
Muc tieu: **2x so lenh, moi lenh 1/2 von** => giu gross exposure ~ khong doi (2x count x 1/2 size),
nhung nhieu vi the dong thoi nho hon => **da dang hoa cao hon => variance/rui ro (maxDD, underwater) thap hon**,
trong khi hieu qua tong (CAGR) giu ~ baseline T170.

Ghi chu co hoc (trung thuc):
- Neu halve sizing DEU cho MOI lenh ma KHONG doi gi khac va scale ap SAU throttle (post-hoc), equity path
  chi co ti le => maxDD%/UW BAT BIEN. Nhung o sim nay knob `SIM_F_BASE` ap TRUOC throttle:
  `budget = equity * F_BASE * throttle / ladder * ratio`, voi `throttle = clamp(1 - (marginRunning/equity)/U_MAX,0,1)`.
  Leg nho hon => marginRunning tang cham hon => throttle CAO hon => cho phep NHIEU leg dong thoi hon.
  Do la CHINH kenh da dang hoa ta muon do. Vay 1/2 F_BASE khong phai scale tuyet doi thuan — no tuong tac
  voi throttle, va ket hop voi noi gate + gian K de dat 2x lenh.
- Sim mo hinh concurrency + compounding => maxDD/UW se PHAN ANH da dang hoa. Do la phep do dung.

## 2. Knob giam size 1/2
`F_BASE` (Configs.java:155, default 0.03) DA co knob doc tu profile: `SIM_F_BASE` (Configs.java:545,
`if ((v=Cfg.get("SIM_F_BASE"))!=null) F_BASE=parse(v)`). KHONG can them code, KHONG rebuild.
1/2 size => **`SIM_F_BASE=0.015`**. (Khong dung SIM_SIZE_SCALE vi knob F_BASE da ton tai — theo pre-reg.)

## 3. Baseline + 3 config (CO DINH — khong tune)
Baseline = **X1_GS_T170_2021** (profile `x1_gs_t170.properties`: gate SIM_GATE_DYN_SCALE=1.70, K=SELECTOR_RANK_TOPK=8,
F_BASE=0.03 mac dinh), printDone md5 **efb793e2**, n=1089, dataset wfo_ds_x1_2021.

Ba config (TAT CA `SIM_F_BASE=0.015`), noi gate + gian K de ~2x lenh:
- **V1**: SIM_GATE_DYN_SCALE=1.30 + SELECTOR_RANK_TOPK=12 + SIM_F_BASE=0.015
- **V2**: SIM_GATE_DYN_SCALE=1.30 + SELECTOR_RANK_TOPK=16 + SIM_F_BASE=0.015
- **V3**: SIM_GATE_DYN_SCALE=1.50 + SELECTOR_RANK_TOPK=16 + SIM_F_BASE=0.015

Moi profile = copy `x1_gs_t170.properties`, chi doi 3 key tren (moi key khac giu y nguyen).

## 4. Cong (BAT BUOC — fail thi DUNG)
- **(a) Reproduction**: chay baseline `x1_gs_t170.properties` (F_BASE mac dinh, gate1.70, K8) tren
  wfo_ds_x1_2021 voi jar hien tai => printDone md5 phai = **efb793e2** (n=1089). Xac nhan jar hien tai
  (co ban va ShadowBookC3 sau 422b23e) KHONG doi duong sim.
- **(b) Knob-parity**: chay profile giong baseline nhung THEM `SIM_F_BASE=0.03` (= gia tri mac dinh) =>
  phai byte-identical efb793e2. Chung minh knob `SIM_F_BASE` o gia tri mac dinh VO HAI.
Ca hai fail => DUNG, bao master.

## 5. Cham diem (x1_rates.py, CI khoi-72h x1.21 da bao k=3 multiplicity)
Moi config vs baseline. Do:
- **n** (boi so so voi 1089; muc tieu 1.8-2.2x).
- **size%/leg thuc do** = mean(margin / equity-at-entry) tren leg-0; muc tieu ~ 1/2 baseline.
- **Chat luong**: win% / TSloss% / meanP — trong CI baseline (khong xau ngoai CI) ?
- **Rui ro**: maxDD% & UW <= baseline ?
- **Hieu qua**: CAGR ~ baseline (trong ~2pp) ?

## 6. QUYET DINH (chot TRUOC khi chay)
**WIN** neu ton tai >=1 config dat DONG THOI:
1. n ~ 2x baseline (1.8-2.2x),
2. size/leg ~ 1/2 baseline,
3. chat luong KHONG xau ngoai CI (moi rate chat luong trong CI hoac tot hon),
4. **maxDD & UW <= baseline** (rui ro thap hon),
5. CAGR trong ~2pp baseline (giu hieu qua).
Neu KHONG config nao dat => bao cai GAN NHAT + trade-off. KHONG tune them config.

## 7. Rang buoc
- Config co dinh (khong tune ep 2x). Reproduction + knob-parity TRUOC.
- KHONG cham 242, KHONG git push. Holdout 2026 nguyen (SIM_END_DATE=20251231).

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_011zpgT8SsGrmcqzxbC93PQT
