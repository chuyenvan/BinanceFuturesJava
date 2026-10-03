# RESULT S1_FEAT_GEOM — **NO-GO** (2/5 điều kiện trượt: c1 ΔCAGR, c2 ΔCalmar CI) ⇒ đóng hướng feature S1 trên DEV

Pre-reg `docs/prereg/PREREG_S1_FEAT_GEOM.md` (9cac7d87, chốt TRƯỚC đo). JSON `docs/result/s1_feat_geom.json` (+ `.parity`).
Scripts `research/analysis/s1_geom_{store,feat,kernel,sim}.py`. Manifest store `data/meta/OHLCV_1H_v2_MANIFEST.json`.

## 0. Kết luận
- Arm G (KEEP9 + 9 GEOM, TB seed 42/7) vs CTRL (K42+S7 cùng recipe GPU): **ΔCAGR +2,46pp CI inflate 1,18 [−0,20; +5,09]**,
  **ΔCalmar +0,83 [−0,05; +1,78]**, maxDD ngày −10,05 vs −12,10, 3/4 năm dương, SL% 13,41 ≤ 13,83, noise gain hạng 19/19.
  ⇒ c1 (≥ +3,3pp) TRƯỢT, c2 (cận dưới > 0) TRƯỢT sát (−0,05), c3/c4/c5 ĐẠT ⇒ **NO-GO** theo luật khoá.
- Đây là thay đổi S1 đầu tiên trong chuỗi có **mọi ước lượng điểm cùng dấu dương** (2 seed, G và GN, tầng model và tầng sim),
  nhưng hiệu ứng (~+2,5pp CAGR) **nhỏ hơn MDE80 1v1 3,3pp** và CI chứa 0 ⇒ DEV không phân biệt được với nhiễu retrain. Không tune lại.
- Vs B0: G +1,80pp [−0,95; +4,68], Calmar +0,20 [−0,33; +1,44] — không vượt B0. frac gap R50 = 0,17.
- Theo pre-reg: **đóng hướng feature S1 trên DEV**. Nếu muốn giữ GEOM, chỉ hợp lệ như giả thuyết cho dữ liệu MỚI (forward/2026), không chạy lại trên DEV.

## 1. Store OHLCV_1H_v2 (dữ liệu)
`/home/ubuntu/java/fsrun/OHLCV_1H_v2.bin` md5 `86f1061cccbdc69fca8f2ec4a0c4eec0`, **10 009 699 rec**, 626 sym (USDC bị STABLE loại), 300 MB,
ts_h 2021-01-01 01:00 → 2026-01-01 00:00. Stream Aerospike 60 tháng 1 620 s (3 proc). Lineage: bỏ đuôi settle 314 225 giờ (head 0).
Sanity: **S1 close == CLOSES_1H_v2 720/720** (30 sym × 24h); toàn bộ 9,99M cặp join khớp tuyệt đối (max |rel| = 0);
**S2 high ≥ max(o,c), low ≤ min(o,c): 0 vi phạm**; NaN 0; phủ (ts,sym) v2 trong store 99,99999 %.

## 2. Feature + cổng tái lập
- **Cổng KEEP9 PASS**: builder `x1_feat_v2_build.py` chạy lại (393 s) → 10 265 224 dòng, (ts,sym) trùng hết, **0 ô lệch bit** trên 1M mẫu
  và trên toàn bảng (9 cột). Sửa duy nhất về bộ nhớ: chỉ stack 9 cột KEEP9 (bản stack-tất-cả bị OOM-kill 23 GB lần 1; giá trị từng cột độc lập).
- GEOM: unit 6/6, CAUSALITY 200 mẫu × 5 feature mismatch 0, range PASS (atr_ratio = 0 ở 144/9,95M ô — 24h nến phẳng, hợp lệ).
  Phủ dòng ledger 99,3–99,7 % (dòng keep9 96,4–96,8 %: phần thiếu = giờ settle v1). File `geom_x1.parquet` md5 6903e178.

## 3. Tầng model (OOS 16 fold, 6 573 909 dòng, chỉ báo cáo)
| arm | edge5 % | IC rel5 | lift@16 % | xs~ORIG | top16∩ORIG |
|---|---|---|---|---|---|
| ORIG | 15,42 | 0,1730 | 7,66 | — | — |
| K42 / S7 (CTRL) | 15,03 / 15,91 | 0,1744 / 0,1744 | 7,35 / 7,40 | 0,984 / 0,981 | 0,897 / 0,888 |
| G42 / G7 | 17,42 / 18,15 | 0,1748 / 0,1753 | 8,05 / 8,17 | 0,927 / 0,925 | 0,806 / 0,796 |
| GN42 / GN7 | 17,11 / 18,08 | 0,1750 / 0,1752 | 8,29 / 8,20 | 0,925 / 0,924 | 0,805 / 0,797 |

CONFIRM (block-72h, k=2): Δedge5 G−CTRL toàn kỳ +2,31 [+0,50; +4,06]; SELECT (2022–23) −0,11 (ngưỡng 0,17, không vượt);
CONFIRM (2024–25) **+2,91 [+0,85; +4,98]** ⇒ lợi ích offline dồn vào 2024–25 (edge5 2025: 22,5 vs 19,5). noise_cal GN−G −0,19 [−0,55; +0,15] (chứa 0).
IC vs rel5 gần như không đổi (+0,0006) — GEOM đổi thứ tự đỉnh (top-16 overlap 0,80 vs 0,89) chứ không đổi xếp hạng toàn cục.
Importance gain (G, TB 16 fold): rk_dd_7d 114, rk_ret_3d 104, ret_14d 71, vol_7d 70, **rk_dist_low24 63**, ret_3d 46, **range7d 46**, …, pos24 12, rk_pos24 11.
Tổng total_gain GEOM ≈ 21 % (range7d 7,9 %, rk_dist_low24 4,6 %). **noise (GN): gain 3,3 vs min KEEP9 15,8 (rk_oi_delta24h), hạng 19/19, total_gain ~0 % ⇒ c5 ĐẠT**.

## 4. Sim (Kaggle, cửa sổ MTM 2022-01-01..2025-12-30; parity B0REF5 md5 ff3ce513 n 2517 eq 131 908 PASS; MAP_PARITY 16/16 PASS)
| arm | n | ΣPnL | CAGR | maxDD ngày | Calmar | win% | SL% | UW MTM ngày | ∩B0 % | 2022 / 23 / 24 / 25 ROI |
|---|---|---|---|---|---|---|---|---|---|---|
| G42 | 2068 | 99 676 | 35,85 | −9,21 | 3,89 | 86,8 | 13,15 | 87 | 73,8 | 15,2 / 56,9 / 40,8 / 33,6 |
| G7 | 2085 | 95 716 | 34,88 | −10,88 | 3,21 | 86,1 | 13,67 | 117 | 71,3 | 11,6 / 54,8 / 41,8 / 35,0 |
| **G (TB)** | 2077 | 97 696 | **35,36** | −10,05 | **3,55** | 86,4 | 13,41 | 102 | 72,5 | 13,4 / 55,9 / 41,3 / 34,3 |
| GN (TB) | 2076 | 97 727 | 35,37 | −10,48 | 3,38 | 86,3 | 13,61 | 89 | 72,6 | 12,3 / 54,2 / 40,1 / 38,3 |
| CTRL (K42+S7) | 2089 | 87 853 | 32,90 | −12,10 | 2,72 | 86,1 | 13,83 | 141 | 81,4 | 10,8 / 55,1 / 40,4 / 29,3 |
| B0 | 2083 | 90 422 | 33,56 | −10,02 | 3,35 | 86,3 | 13,83 | 87 | 100 | 11,1 / 54,1 / 43,4 / 29,5 |

Δ (paired block-10d NREP 2000, CI inflate 1,18): G−CTRL CAGR +2,46 [−0,20; +5,09], maxDD +2,06 [−0,37; +4,29], Calmar +0,83 [−0,05; +1,78];
GN−CTRL +2,47 [−0,45; +5,78] / Calmar +0,66 [−0,03; +2,14]; GN−G +0,01 [−1,99; +3,02]; G−B0 +1,80 [−0,95; +4,68]; CTRL−B0 −0,66 [−3,50; +2,21].
Từng seed vs CTRL: G42 +2,94 (Calmar +1,17 [−0,03; +2,12]), G7 +1,98, GN42 +3,06, GN7 +1,87 — không seed nào ≥ 3,3pp.
Theo năm G−CTRL: 2022 +2,6 / 2023 +0,8 / 2024 +0,9 / 2025 **+5,0** (GN: +1,5 / −0,9 / −0,2 / +9,0) ⇒ lợi ích dồn 2025.

## 5. Chấm luật (arm G, TB 2 seed)
| điều kiện | giá trị | kết quả |
|---|---|---|
| c1 ΔCAGR vs CTRL ≥ +3,3pp | +2,46 | **TRƯỢT** |
| c2 ΔCalmar CI inflate cận dưới > 0 | [−0,05; +1,78] | **TRƯỢT** (sát) |
| c3 ≥ 3/4 năm dương | 4/4 (+2,6/+0,8/+0,9/+5,0) | ĐẠT |
| c4 SL% ≤ CTRL | 13,41 ≤ 13,83 | ĐẠT |
| c5 noise gain < min gain KEEP9 | 3,3 < 15,8 | ĐẠT |
⇒ **NO-GO**. GN (đối chứng) ≈ G (Δ +0,01pp): model không khớp nhiễu; harness sạch.

## 6. Vì sao NO-GO / đọc kết quả
1. Hiệu ứng cùng chiều nhưng cỡ ~+2,5pp CAGR ≈ 3 sd seed (0,83pp), dưới MDE80 1v1 3,3pp; CI thời gian ±2,6pp ⇒ không tách được khỏi 0 ở Calmar.
2. Lợi ích tập trung 2025 (offline edge5 và sim đều vậy; SELECT 2022–23 offline ≈ 0) ⇒ có thể là chế độ thị trường 2025 (universe rộng, nhiều coin mới),
   không phải cải thiện đồng đều — thêm lý do không hạ ngưỡng sau khi thấy kết quả.
3. Vs B0 chỉ +1,8pp (CI chứa 0): B0 vốn là realization may mắn về Calmar (f0b9d8e6), nên G chưa vượt được mốc deploy.
4. Pre-reg khai P(GO) 15–20 %; kết quả rơi vào vùng "dương nhưng dưới ngưỡng" — đúng loại kết quả DEV không đủ sức phân xử.
⇒ Đóng hướng feature S1 trên DEV. GEOM + store OHLCV_1H_v2 giữ lại làm tài sản dữ liệu; mọi kiểm tiếp phải trên dữ liệu chưa thấy (2026+).

## 7. Hash / truy vết
B0 = selab-p0 (B0REF5 cùng đợt md5 ff3ce513, n 2517, eq 131 908 PASS). bins sha (moc21 + map 16): xem JSON `bins_sha256`; deploy-check P0 407e2aba.
Kernel train `chuyendinh/s1-geom-gpu` (xgboost 3.2.0, T4, 4 arm × ~180 s). Dataset `s1-geom-x1-20261003` (geom_x1.parquet md5 6903e178) + `s1-featv2-x1-20260919` (keep9 1aa3b974).
Sim kernel `sim-geom-{g42,g7,gn42,gn7}`, code_sha 9cac7d87, kaggle_sim HEAD NOWRITE242. Không chạm 242/shadow, không sửa .java, không Java sim trên Oracle.
