# PREREG_S1_V2 (NHÁP) — S1 KEEP9 + GEOM + nhóm cứu (funding, OFI), chấm end-to-end theo §9 A-20261003

> **TRẠNG THÁI: NHÁP — CHỜ MASTER DUYỆT. CHƯA CHẠY GÌ.** Không train, không sim, không Kaggle cho tới khi MASTER chốt các ô §9 và commit bản chốt (đổi tên bỏ `_DRAFT`).

- **Nguồn:** `docs/audit/REAUDIT_S1_FEATURE_ROUNDS_20261003.md` (+ `reaudit_s1_feat_rounds.json`), `RESULT_S1_FEAT_GEOM.md` (`cf5c90e4`), `RESULT_S1_HPO_BAG_FEATGRP.md`, `RESULT_S1_FREE_OFI_V3_MULTISEED.md`, `RESULT_S1_RETRAIN_NOISE.md` (`f0b9d8e6`), `RISK_APPETITE.md` §9-AMENDMENT A-20261003.
- **Phạm vi:** DEV ≤ 2025-12-31, 16 fold 20220101..20251001. KHÔNG 242/shadow, KHÔNG sửa .java, KHÔNG Java trên Oracle, KHÔNG dữ liệu 2026, KHÔNG deploy.

## 1. Câu hỏi
Xếp chồng các nhóm feature có bằng chứng dương (GEOM đã sim; funding/carry G2 và OFI mới chỉ offline) lên S1 KEEP9 có tăng **PnL ròng chuỗi B0** (ΔCAGR MTM) ngoài nhiễu thời gian không?

## 2. Nền và đối chứng (cố định)
- **Nền deploy:** B0 = S1 KEEP9 seed 42, bins deploy `~/predwf_map_s1a2_x1` (sha P0 `407e2aba`), sim tag `selab-p0`, parity B0REF md5 `ff3ce513` (n 2517, eq 131 908) — phải PASS lại trong đợt (B0REF6).
- **CTRL chính = CTRL4** = S1 KEEP9 retrain cùng recipe GPU, seed {42, 7, 13, 21} — sim **đã có** `s1rn-k42/s7/s13/s21` (cùng jar `7368be46`, cùng kaggle_sim `8b60b00a`, profile B0). Lý do dùng 4 seed (khai TRƯỚC, không phụ thuộc arm mới): audit cho thấy cặp K42+S7 thấp hơn TB 4 seed −0,64 pp ⇒ CTRL 2 seed làm phồng Δ. Chi phí 0.
- **Tham chiếu V2a = GEOM** = KEEP9 + 9 GEOM, đã có 4 run `geom-g42/g7/gn42/gn7` (GN = GEOM + 1 cột nhiễu, GN − G +0,01 pp). V2a **không** nằm trong họ GO (kết quả đã biết: ΔCAGR vs CTRL4 +1,82 [−0,09; +3,81]); chỉ dùng để báo **phần tăng thêm** của V2b/V2c.

## 3. Arm (k = 2, khai trước)
| arm | feature (thứ tự cột cố định) | n cột | seed |
|---|---|---|---|
| **V2b** | KEEP9 + GEOM9 + G2 funding6 (`fund_last, fund_sum_3d, fund_sum_7d, fund_trend, fund_z_30d, rk_fund_sum_3d`) | 24 | 42, 7 (P4: + 13, 21) |
| **V2c** | V2b + OFI2 (`ofi_1h`, `aggr_buy_ratio_1h`; NaN giữ nguyên như harness OFI V3) | 26 | 42, 7 (P4: + 13, 21) |
| VN (chẩn đoán, KHÔNG sim) | V2c + `noise` N(0,1) seed 20260905 | 27 | 42 |
Recipe train = đúng `s1_geom_kernel.py` / CTRL (XGBRanker rank:ndcg topk 8, rel5 g1lite 72h, 300/4/0,05, sub/col 0,8, mcw 50, purge 72h, xgboost 3.2.0, Kaggle T4); CHỈ đổi danh sách feature. Inflate √(2 ln 2) = **1,18**.

## 4. Cổng hợp lệ (FAIL ⇒ DỪNG, không đọc số)
1. **KEEP9 byte-identical** (builder `x1_feat_v2_build.py`, 1M mẫu + toàn bảng) — như GEOM.
2. **Funding rebuild:** build TỪNG cột `fund_*` (tránh OOM stack-tất-cả) ⇒ retrain KEEP9+G2 seed 42 **CPU** 18 fold trên Oracle (~13′) phải tái lập `~/s1hpo/pred_p3_G2.parquet`: `rank_exact_match_frac ≥ 0,999999` (cách định nghĩa cổng FEATGRP §0). FAIL ⇒ cột funding build lại khác gốc ⇒ dừng V2b/V2c.
3. **OFI:** join từ output Kaggle `ofi-v3-build-s0..s9`; coverage dòng pool ≥ 0,95 (gốc 0,951); tái lập edge5 candidate seed 42 của OFI V3 (`+1,6501 pp` CONFIRM, sai lệch ≤ 0,01 pp) trên harness OFI.
4. **Causality/leak:** `assert tr.ts.max() < cut` 16/16 fold mọi arm; ts < 2026.
5. **MAP_PARITY** 16/16 (map `s1a2x1` trên bins deploy, A1) + **B0REF6** md5 `ff3ce513`.
6. **Noise (VN):** gain của `noise` < min gain KEEP9 (như c5 GEOM). FAIL ⇒ HARNESS_NGHI_NGỜ, dừng.

## 5. Cổng dừng offline C0 (trước khi tốn sim, khai trước)
Δedge5 g1lite CONFIRM 2024–25 (TB seed của arm − TB `G42,G7`) phải **> 0** (ước lượng điểm). Arm trượt C0 ⇒ KHÔNG sim, verdict NO-GO, ghi số. (V2c so với V2b nếu V2b qua C0; nếu V2b trượt, V2c so với G.)

## 6. Thước + luật GO (§9 A-20261003; mỗi arm V2b, V2c chấm độc lập, TB seed của arm vs TB CTRL4)
Thước: equity MTM ngày (b + unP) từ `sim.out`, cửa sổ 2022-01-01..2025-12-30 (equity từ 2021-12-31), **paired moving-block bootstrap 10 ngày, NREP 2000, seed 20260905**, cùng chỉ số khối cho mọi arm (`SAD.daily_boot`), họ arm = trung bình theo replicate.

**GO ⟺ đồng thời:**
- **C1** ΔCAGR(arm − CTRL4) > 0 **và** cận dưới CI inflate 1,18 > 0.
- **C2** maxDD MTM phút ≤ 40 % (mọi seed của arm).
- **C3** Calmar_MTM(arm) ≥ 0,90 × Calmar_MTM(CTRL4) (mặc định §9.3 tới khi owner chốt X của A.4).
- **C4** ≥ 3/4 năm 2022–2025: ΔROI năm (arm − CTRL4) ≥ 0.
- **C6** rào T1 còn hiệu lực: UW ≤ 250 ngày, quý xấu nhất ≥ −20 %, 0 năm âm, conc 1 coin ≤ 15 %.
- **C5 (ĐỀ XUẤT — MASTER bật/tắt TRƯỚC khi chạy):** ΔCAGR chỉ tính 2022–2024 ≥ 0 (ước lượng điểm). Lý do: mọi bằng chứng dương (GEOM, G2, OFI) dồn 2025; C5 chặn GO chỉ nhờ một chế độ thị trường.

**Chỉ báo cáo (không quyết):** win%, SL%, TSloss% (T3 thông tin), n lệnh, overlap B0, ΔCAGR vs B0, **phần tăng thêm** V2b − V2a(GEO4) và V2c − V2b (CI raw), từng seed vs CTRL4, Δedge5/IC/lift@16 tầng model, gain share từng nhóm.
**Diễn giải trước:** GO ở V2c nhưng không ở V2b ⇒ ghi công cho OFI chỉ khi V2c − V2b cận dưới CI raw > 0; ngược lại ghi "xếp chồng". GO cả hai ⇒ chọn V2b nếu V2c − V2b CI chứa 0 (rẻ hơn LIVE).

## 7. Kỳ vọng khai TRƯỚC + lực
- V2a (đã biết) +1,8 pp. **V2b kỳ vọng +2,5 pp (khoảng +1 … +4)**: GEOM +1,8 + funding (quy đổi +1,3 … +1,7) × hệ số chồng lấp ~0,5. **V2c kỳ vọng +2,8 pp (+1 … +4,5)**.
- Lực: nửa độ rộng CI thời gian 4v4 đo được ±1,95 pp ⇒ với inflate 1,18 cần Δ quan sát ≳ **+2,3 pp** để qua C1; thêm nhiễu seed (sd CAGR 0,83 pp/run ⇒ sd của hiệu TB 2 seed vs 4 seed ≈ 0,72 pp) ⇒ MDE80 ≈ **3,9 pp** (2 seed) / **3,6 pp** (4 seed): thời gian chi phối, thêm seed lợi ít.
- **P(GO) ước:** V2b ~30 %, V2c ~35 %, ≥ 1 arm ~45 %. Kết cục khả dĩ nhất: dương dưới ngưỡng (như GEOM).

## 8. Chi phí + thứ tự (1 job nặng/box, lock `oracle_heavy.lock`, RAM ≤ 6 GB)
1. Build `fund_*` từng cột trên Oracle (~15–30′ CPU) + cổng 4.1–4.2 (CPU retrain 18 fold ~13′).
2. Ghép OFI từ output Kaggle OFI V3 (đã build, ~25 h CPU đã tiêu) + cổng 4.3; upload dataset Kaggle mới (KEEP9 + GEOM + G2 + OFI, md5 ghi vào JSON).
3. Kaggle GPU train: 4 arm-seed + VN ≈ 5 × 3–4′ (P4: 8 + 1). Cổng 4.4, 4.6; C0.
4. Map + MAP_PARITY; sim Kaggle CPU 4 kernel (P4: 8) × ~1,5 h (song song theo slot) + B0REF6.
5. Chấm (~30′ Oracle) → `docs/result/RESULT_S1_V2.md` + `s1_v2.json`.
Tổng ≈ 0,5 ngày công Oracle + ~1,5–3 h wall Kaggle.

## 9. Ô MASTER phải chốt trước khi chạy
- [ ] Số seed/arm: **2 (42, 7)** theo brief, hay **P4 (42, 7, 13, 21)** — khớp CTRL4 từng seed, MDE chỉ giảm ~0,3 pp, chi phí sim ×2.
- [ ] Bật **C5** (chặn GO chỉ nhờ 2025) hay chỉ báo cáo.
- [ ] Giữ **V2c (OFI)** dù LIVE đắt (stream aggTrades realtime, ONNX 26 input) hay thay V2c bằng V2b-4seed.
- [ ] Owner chốt X của A.4 (Calmar) — nếu chưa, C3 = 0,90×.

## 10. Kết cục ⇒ hành động
- GO ⇒ KHÔNG deploy trực tiếp: đề xuất shadow A/B (như `SHADOW2_GEOM_PLAN.md`) + pre-reg forward 2026; owner duyệt.
- NO-GO cả 2 ⇒ **đóng hướng feature S1 trên DEV** (lần này dứt điểm: đã chấm đúng thước, đúng đối chứng); GEOM/funding chỉ còn là giả thuyết forward.
- Ngoài phạm vi: thêm nhóm feature khác, HPO, đổi nhãn, lưới thời gian (đều đã bác đúng — audit §5).
