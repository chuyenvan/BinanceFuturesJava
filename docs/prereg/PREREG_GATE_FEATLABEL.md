# PREREG_GATE_FEATLABEL — biến thể FEATURES của gate, đo CHẤT LƯỢNG trên ĐÚNG tập được admit bởi gate `G2` (ratio)

**Trạng thái: CHỐT TRƯỚC — CHƯA TRAIN, CHƯA CHẠY, CHƯA SIM.** Owner duyệt trước khi làm bất kỳ bước nào.
Ngày chốt: 2026-09-30 · Nhánh `module` · Xuất phát: `docs/plan/REVIEW_GATE_FEATLABEL.md`.
Sau khi thấy số: **KHÔNG sửa thiết kế**; nếu NULL ⇒ ghi NULL, không bịa số.

## 0. CÂU HỎI (hẹp, và KHÔNG phải câu mở gate)

**KHÔNG** hỏi *"làm sao mở gate để ×2 `n`"* — câu đó đã **NULL** (`REVIEW_GATE_FEATLABEL §3.1`; dưới `G2` tỉ lệ pass do `SIM_GATE_ROLLING_PCT` quyết, `GateRollingRatio.java:19-24`).
Vòng này hỏi **đúng 1 câu còn trống**: *"dưới gate `MODE=ratio` (G2), biến thể feature tốt hơn về **xếp hạng** có làm **chất lượng trên ĐÚNG tập được admit** tốt hơn không?"*
Lý do còn trống: **mọi** vòng feature/label gate trước đây (`GATEFEAT` `d01d59a0`; `GATE_H72` `d39f0158`; `GATE_TOPK_LABEL_SIM` `0d0bdd5c`) đều đo trên **ngưỡng CỐ ĐỊNH** (T170 scale 1,70 / `X1_C3_FULL` scale 1,0), **chưa vòng nào đo dưới `G2`**.

**Kỳ vọng GHI TRƯỚC: `NULL`** (theo `GATEFEAT`: IC +0,0159 → sim 0/5; và `GATE_TOPK_LABEL_SIM`: đổi label ⇒ mở 2× ⇒ vỡ chất lượng). Đây là pre-reg để **đóng ô trống bằng số**, không phải để kỳ vọng thắng.

## 1. BIẾN THỂ — khoá, TỐI ĐA 4

Nền chung: gate p15, XGBRegressor theo đúng `ml/gate/train_gate_fold.py` (depth=4, n_estimators=150, lr=0,05, subsample=0,8, colsample_bytree=0,8, min_child_weight=10, seed=42, purge 15m, label `label_oldbasket`), WFO expanding 19 fold DEV (`2021-04-01..2025-12-31`), feature đọc theo thứ tự V3FULL.

| tag | khác biệt DUY NHẤT | nguồn |
|---|---|---|
| **V0** | control: retrain đủ **33 feature** | cổng hồi quy/nhiễu retrain |
| **V1** | bỏ 6 feature ⇒ **27 feature** (`rsi14, monthOfYear, fundingRateRaw, hourOfDay, dayOfWeek, weekOfMonth`) | `GATEFEAT` CYC7 — IC OOS **0,5494 vs 0,5335 (+0,0159, P=1.000)** |
| **V2** | bỏ 3 feature ⇒ **30 feature** (`rsi14, monthOfYear, fundingRateRaw`) | `GATEFEAT` CYC_COMBO — IC **0,5483 (+0,0148)** |
| **V3** | **label khác** (`label_selector` của `ExportGate15mV2`, hoặc net-of-cost `ret15m`) | ⛔ **KHÔNG có trong store** (`gate_dataset_full.csv.gz` = ts + 33 feat + `label_oldbasket`, đã kiểm) ⇒ **VÒNG SAU / CẦN EXPORT MỚI**, không chạy ở vòng này |

**Bỏ V3 khỏi vòng này** (cần `WFOGateRunner`/`ExportGateDataset` chạy lại, `GATE_AB_LABELS`): ghi rõ là **thiếu dữ liệu**, không phải lựa chọn thiết kế.

## 2. TẦNG 1 — OFFLINE (bắt buộc, chặn trước sim)

**Cổng DỪNG: không vượt tầng 1 ⇒ KHÔNG sim, ghi NULL.** Chi phí: **CPU, ~1–2 h/biến thể, 0 GPU, 0 sim, 0 Java** (venv `/home/ubuntu/envs/xgb-env`).

1. Train 21 fold như §1 cho V0/V1/V2 → p15 chuỗi OOS 19 fold DEV (không nhìn 2026).
2. **Tái lập bộ admit của `G2`** một cách CAUSAL từ chính p15: `r = p15/(max(0,26787, sp/0,15·1,2876)·1,55)`,
   `PASS ⟺ r > q_t` với `q_t` = phân vị `SIM_GATE_ROLLING_PCT=0,99995083` trên cửa sổ cuộn **90 ngày** của chính `r`, cập nhật mỗi giờ, **chỉ dữ liệu quá khứ** (KHÔNG dùng p15 của V1/V2 để dựng q_t — dùng chung chuỗi p15 của V0 làm mốc chuẩn, để chỉ đổi **xếp hạng**, không đổi **tỉ lệ**).
   Nguồn `sp` (symbolPred) + p15: `wfo_ds_x1_2021` / `pred.bin` (≤ 2025-12-31).
3. **Thước đo** (trên ĐÚNG tập admit, không phải toàn pool):
   - `lift@admit` = `mean(label_oldbasket | admit) / mean(label_oldbasket | toàn tick)`;
   - `rank-IC` de-overlap 15m trong tick giữa p15 và `label_oldbasket`;
   - `n_admit` (kiểm số sự kiện **không tăng** — kỳ vọng ≈ nhau).
4. **CI**: bootstrap block-72h **ghép cặp** V1−V0 / V2−V0, N=2000, seed **20260905**, `inflate(k)`;
   k=2 (2 biến thể) ⇒ nhân `1,1774`.
5. **CỔNG QUA TẦNG 1** (phải đạt **CẢ HAI**, đọc theo chiều TỐT HƠN):
   - `Δlift@admit` **dương ngoài CI**; **VÀ**
   - `Δrank-IC` **không âm ngoài CI**.
   - Nếu 2 thước trái chiều ⇒ ghi rõ, **mặc định NULL** (không tự hạ nguồn).

## 3. TẦNG 2 — SIM (chỉ khi tầng 1 qua)

Nền `profiles/g2_flat3.properties` **nguyên trạng**; chỉ thay `WFO_SET_PRED` = set p15 của biến thể.
**Cổng DỪNG: `P1` phải tái lập `printDone.csv` md5 `650c386f0d0dfea334af9d55ca2f21d4` (n 2517)** trước khi đọc số biến thể.
Luật 4 tầng §9 (`docs/runbooks/RISK_APPETITE.md`): `n` (mục tiêu) · `Calmar_MTM ≥ 0,90×1,877 = 1,689` · `conc ≤ 4,09 %` · T1 MTM phút · T2 (`q* ≥ 15`, top-1 ≤ 25) · T3 (`win% ≥ −2,0 pp`, `TSloss% ≤ +2,5 pp`, CI block-72h N=2000 seed 20260905).
**Chi phí:** Kaggle CPU ~30–45 phút/chân, **0 quota**, **0 sim Oracle**. DEV ≤ 2025-12-31, **0 chạm 2026**.

## 4. LUẬT QUYẾT ĐỊNH

| kết quả | hành động |
|---|---|
| Tầng 1 NULL (mặc định kỳ vọng) | **ĐÓNG ô "feature/label gate dưới ratio gate"** — giữ 33 feature; không sim |
| Tầng 1 PASS, tầng 2 không vượt 4 tầng §9 | NULL — ghi "chất lượng model-tier không chuyển thành sim dưới ratio gate" |
| Tầng 1 + tầng 2 PASS | đề xuất owner đổi config 27/30 feature **chỉ khi** `n` **và** `Calmar_MTM` **và** `conc` cùng đạt — **owner quyết**, không tự deploy |

## 5. GIỚI HẠN KHAI TRƯỚC

1. **Không phải lever `n`.** `n_admit` kỳ vọng **không tăng** (tỉ lệ pass do `pct` quyết). Nếu thấy `n` đổi mạnh ⇒ nghi lỗi tái lập q_t, phải dừng và soát.
2. **q_t dựng lại bằng Python có thể lệch** so với `GateRatioBuffer` Java (cập nhật mỗi giờ, warm-up 7 ngày). Tầng 1 chỉ cần **nhất quán giữa V0/V1/V2**; nếu lệch hệ thống ⇒ ghi rõ, dùng **chính q_t của V0** cho cả 3.
3. Đây là lần thử **thứ ≥ 31** trên cùng DEV ⇒ multiplicity cao; ngưỡng đọc **theo CI đã nhân `k`**, không thêm biến thể sau khi thấy số.
4. `label_selector`/net-of-cost (V3) **chưa có dữ liệu** ⇒ kết luận vòng này **không** nói gì về trục label dưới ratio gate.
5. **Không chạm** 242/ONNX/`NUM_FEATURES`/`extractFeatures45`/LIVE; **không push** file dữ liệu.
