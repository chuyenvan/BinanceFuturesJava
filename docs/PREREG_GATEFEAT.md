# PREREG_GATEFEAT — đánh giá 33 feature V3FULL của gate p15, bớt feature yếu (WFO OOS)

Viet TRUOC khi chay bat ky fold train nao. Khong sua sau khi thay ket qua.
Batch tu yeu cau user 2026-09-09: "tai hien baseline roi nghien cuu tang chat luong gate p15
bang cach danh gia 33 features hien tai can them/bot nhu the nao; moi lan them/bot = 1 chu
trinh chay test danh gia roi moi quyet dinh."

## 0. Trang thai truoc khi viet (da chay, khong phai phan cua pre-reg nay)
- **Phase 1 (tai hien baseline) DA XONG**: predict lai p15 tu feature store + 21 model ONNX goc,
  so voi `claudedata/wfo_gate_pred.csv` hien hanh: **19/19 fold DEV PASS** (spearman >= 0.999997,
  max|d| ~1e-4 chi la nhieu lam tron %.8f). => store `gate_dataset_full.csv.gz`, model
  `wfo_models/fold_{0..20}`, va file p15 dang chay la NHA'T QUAN.

## 1. Phat bieu van de va pham vi
- Gate p15 = `predReturn15M` (XGBRegressor, 33 feature V3FULL market-level, label_oldbasket).
  Duoc WFOGateRunner train per-fold (expanding, OOS 3 thang, 21 fold) va predict OOS -> p15.
- Cau hoi: trong 33 feature hien tai, feature nao YEU (bot khong mat chat luong gate)?
- **PHAM VI**: chi ablation trong 33 feature SAN CO cua store (`gate_dataset_full.csv.gz`),
  KHONG them feature ngoai (them = doi extractor Java + replay Aerospike hang chuc gio,
  can pre-reg rieng + user chi dinh feature candidate). Khong dung 2026 (holdout seal).
- **Gioi han so chu trinh trong pre-reg nay**: Stage 0 (control) + toi da **6 chu trinh bot**
  theo thu tu feature yeu nhat (muc 4). Muon bot tiep qua 6 -> pre-reg moi.

## 2. Vi sao can Stage 0 (CONTROL) — retrain-noise
Theo tien le `docs/PREREG_G015ABL.md` + `docs/BENCH_DEVICE.md` muc 7.4: retrain-lai-tu-dau
XGBoost (subsample=0.8, colsample_bytree=0.8) co the tu nhien lech khoi model san xuat mot
khoang bang nen nhieu multi-seed. Vi vay:
- **Moi chu trinh bot feature so voi Stage 0 (retrain day du 33 feature, cung script/cung may/
  cung seed), KHONG so truc tiep voi `X1_C3_FULL_PARITY`/model goc.**
- Stage 0 dong thoi la cong hoi quy: p15 cua Stage 0 phai dat spearman >= 0.999 voi
  `wfo_gate_pred.csv` (neu retrain deterministic) — neu KHONG dat (retrain-noise lon), ghi ro
  bien do noise va van so cac chu trinh voi Stage 0.

## 3. Pipeline chuan cho MOI chu trinh (kể cả Stage 0)
1. Train 21 fold expanding tren Oracle (CPU, venv `/home/ubuntu/envs/xgb-env/bin/python`),
   DUNG hyperparam cua `ml/gate/train_gate_fold.py`: XGBRegressor depth=4, n_estimators=150,
   lr=0.05, subsample=0.8, colsample_bytree=0.8, min_child_weight=10, seed=42,
   GATE_PURGE_MS=15 phut (label_oldbasket). Chi khac: **bo cot feature theo chu trinh**.
2. Predict OOS tung fold tu feature store (KHONG replay Aerospike — dung `h1_p15_repro.py` style).
3. Ghep chuoi OOS 19 fold DEV (2021-04-01 -> 2025-12-31) -> file p15 cua chu trinh.
4. Cham diem tren chinh chuoi OOS do (KHONG nhin 2026).

## 4. Thu tu chu trinh bot — bat dau tu feature YEU nhat
Can cu xep hang (chot TRUOC, khong doi sau khi xem ket qua):
- Nguon 1: univariate IC tren label_oldbasket (`gate15m_v2_featsel.json`, do tren toan bo CV):
  yeu nhat = `basketVolSpike` 0.0006, `basketMomentum1H` 0.0014, `rsi14` 0.0027,
  `distMA20` 0.0040, `percentAboveMA20` 0.0045, `weekOfMonth` 0.0067.
- Nguon 2: featsel BACKWARD greedy cu da loai: `momentumAcceleration`, `fundingRateRaw`,
  `monthOfYear` (30 feature con lai IC 0.4769 > 33 feature 0.4694 — do CV cu, can kiem lai o WFO OOS).
- **Thu tu 6 chu trinh (moi chu trinh bot DUNG 1 feature, tich luy tren ket qua giu lai):**
  1. Bot `basketVolSpike` (univariate yeu nhat).
  2. Bot `basketMomentum1H`.
  3. Bot `rsi14`.
  4. Bot `monthOfYear` (bi BACKWARD cu loai).
  5. Bot `momentumAcceleration` (bi BACKWARD cu loai).
  6. Bot `fundingRateRaw` (bi BACKWARD cu loai).
  Sau moi chu trinh: CHAM DIEM roi QUYET DINH giu/bot (muc 5) TRUOC khi sang chu trinh ke.
  Feature nao bi "giu lai" (khong bot duoc) -> loai khoi danh sach chu trinh sau.

## 5. Tieu chi quyet dinh (chot TRUOC)
Metric chinh cua gate (tien le model-quality/analyze.py): **Spearman IC(pred15, realized)
de-overlap 15m** tren chuoi OOS, tach theo fold va gop; phu: **lift top-decile +1%/+2%/+3%**
(tan suat realized > nguong trong top 10% pred so voi base).
- So sanh: chu trinh k so voi Stage 0 (CUNG 19 fold OOS, paired per fold).
- CI: bootstrap block 72h x1.21 (tien le PREREG_X1/K12/5MGRID), hoac neu n_eff qua nho thi
  ghi ro va dung phan phoi per-fold (19 diem) lam chan doan, KHONG tu ha nguong.
- **QUYET DINH BOT feature** khi: IC trung binh OOS khong giam ngoai CI so voi Stage 0
  (tuc bot khong mat chat luong) — uu tien giam so feature (don gian hoa, giam overfit).
- **GIU feature** khi IC giam ngoai CI theo huong xau.
- Bat ky ket luan nao cung bao cao ca IC lan lift; neu 2 metric trai chieu -> bao ro, quyet
  dinh theo IC (metric chinh da khai bao).
- Sau 6 chu trinh (hoac som hon neu da bot het feature yeu): tong hop danh sach feature
  bot-duoc vs giu-lai, DE XUAT 1 config gate moi (33 - cac feature da bot) cho buoc sim.
  **Sim 48 thang KHONG nam trong pre-reg nay** — chay rieng sau khi user duyet config thang.

## 6. Chat luong gate KHONG phai equity — luu y doc ket qua
Gate p15 chi la mot thanh phan (quyet dinh WHEN). IC/lift OOS tot hon KHONG dam bao sim tot
hon (tien le F4: n_eff nho, gate value chua chung minh doc lap — CI_REAUDIT #9). Muc tieu cua
pre-reg nay la **cao thien chat luong DU BAO cua p15** (IC/lift), khong tuyen bo thang sim.

## 7. Environment / ranh buoc
- Chay tren Oracle, 1 tien trinh Python tuan tu (4 core). Khong dong cham Java sim (1 slot JVM).
- Disk: can ~2-3G tam cho model/fold cua tung chu trinh; xoa sau khi cham diem.
- KHONG chay qua 2025-12-31, KHONG doc 2026. KHONG sua feature extractor Java.
- Ket qua moi chu trinh ghi vao `docs/RESULT_GATEFEAT.md` (them dong, khong sua ket qua cu).
