# RESULT_SHORT_V3_R1B — SELECTOR tại phút trigger (HistGB trên 10 991 lệnh R1)

Pre-reg: `docs/prereg/PREREG_SHORT_V3_R1B.md` (`85a9b1ca`, chốt TRƯỚC đo) · Program: `PROGRAM_SHORT_V3.md` ADDENDUM 1 §R1b (`df2ce308`) · nguồn lệnh: R1 `3fea4f50`
Script: `research/analysis/short_v3_r1b_selector.py` (`feat` → `model`) · Số: `docs/result/RESULT_SHORT_V3_R1B.json` · feature/score per-trade:
`~/claude_master/1002/r1_cache/r1b_feats.parquet`, `r1b_scores.parquet` (ngoài repo). DEV 2022–2025, 2026 không dùng. 0 Java, 0 sửa .java, 0 chạm 242.

## Kết luận: **NO-GO** — gãy 3/6 điều kiện (C1 IC, C2 CI, C4 SL-rate)
Model tại trigger KHÔNG tách được continuation: rank-IC OOS trung bình **+0,019** (cần > 0,05), SL-rate tercile-TOP **27,5%** ≈ ALL 27,9% ≈ BOT 27,5%.

| điều kiện (M24 / net_B24) | ngưỡng | đo | đạt |
|---|---|---|---|
| C1 rank-IC OOS (TB 6 fold) & số fold dương | > +0,05 & ≥ 5/6 | **+0,0187** & 5/6 (pooled +0,0105) | ✘ |
| C2 net TOP ngoài CI raw & inflate 1,18 | lo > 0 | +0,235%, raw [−0,106; +0,568], infl [−0,167; +0,629] | ✘ |
| C3 net TOP > 0 cả 2023/2024/2025 | 3/3 | +0,168 / +0,472 / +0,152 | ✔ |
| C4 SL-rate TOP | ≤ 25% | **27,5%** | ✘ |
| C5 stress TOP − 0,10% | > 0 | +0,135% | ✔ |
| C6 permutation IC | ∈ [−0,02; +0,02] | −0,0080 | ✔ |

## 1. Feature (khoá pre-reg §3) — 13 GIỮ, 1 BỎ
| f | tên | nguồn thực tế | coverage | ghi chú |
|---|---|---|---|---|
| f1 | r60 | trades_r1.csv | 100% | p50 8,8% |
| f2 | r15 | Aerospike 1m t, t−15 | 100% | |
| f3 | ext24 | Aerospike 1m t, t−1440 | 99,93% | |
| f4 | volratio | W0/Mnen R1 | 100% | |
| f5 | wick | H/L/C nến t (`kline_1m_opt`) | 100% | |
| f6 | fund_now | `/tmp/fund_cache.npz`, **PROXY TRỄ** = rate settle gần nhất ≤ t | 99,7% | trễ p50 2,3h, p90 6,1h |
| f7 | fund_sign | f6 < 0 | 99,7% | |
| f8 | dOI_60 | — | — | **BỎ**: `oi_percoin_full.bin` chỉ có `oi_delta24h`/`oi_z`, không có OI thô; derivs_store từ 2026-09 |
| f9 | takerLS | `oi_percoin_full.bin` `taker_buy` 5m, ts ≤ (t+1)·60000 − 300000 | 97,1% | 2022 71,8%; 2023–25 ≥ 99,9% |
| f10 | tier | cột `tier` R1 | 93,4% | NA 6,6% (< 20 ngày lịch sử) |
| f11 | listing_age | min(CLOSES_1H first, qv-cache first), cap 365 | 100% | p10 33 ngày, 44% chạm cap |
| f12 | btc_bull | cột `regime` R1 | 100% | |
| f13 | btc_r60 | Aerospike BTCUSDT t, t−60 | 100% | |
| f14 | n_trig_day | tập 10 991, t' ∈ [t−1440, t−1] | 100% | p50 13, p90 31 |

## 2. Sanity (PASS cả 5)
- **S1 tái lập R1:** n = 10 991; mean net_B24 = **+0,1699%** (R1 +0,170%, ±0,005 ✔); mean net_B12 = +0,1015% (R1 +0,101% ✔).
- **S2 khớp dữ liệu:** đọc lại 41 865 phút Aerospike (41 366 phút gốc + 499 phút lùi cho 9 cặp thiếu bản ghi); C[t] = `c_t` cand **100%**,
  Cf[t−60] = `cf60` **100%** (lệch tương đối < 1e-6).
- **S3 causality (assert theo dòng, PASS):** phút nguồn 1m ≤ t; fundingTime ≤ (t+1)·60000−1; OI ts ≤ (t+1)·60000−300000; listing_day ≤ t; f14 chỉ t' ≤ t−1.
- **S4 fold không rò:** max exit (B24/B12) train < start − 72h ở cả 6 fold (bảng §3); mỗi lệnh 2023–2025 thuộc đúng 1 fold test.
- **S5 tất định:** fit M24 fold 2023H1 hai lần ⇒ dự báo trùng khít (max |Δ| = 0).
Model: sklearn 1.7.2 `HistGradientBoostingRegressor(max_leaf_nodes=15, learning_rate=0.05, max_iter=300, min_samples_leaf=100,
l2_regularization=0, max_features=0.8, early_stopping=False, random_state=20260905)` — không tune.

## 3. Rank-IC theo fold (OOS) + tercile theo fold (net_B24 %)
| fold | n train | n test | max exit train | cắt purge | IC M24 | IC M12 (phụ) | IC perm | TOP | MID | BOT |
|---|---|---|---|---|---|---|---|---|---|---|
| 2023H1 | 1 133 | 713 | 2022-12-28 16:56 | 2022-12-29 | +0,0116 | +0,0353 | −0,0158 | +0,348 | +0,197 | +0,138 |
| 2023H2 | 1 837 | 842 | 2023-06-27 13:47 | 2023-06-28 | +0,0065 | +0,0588 | −0,0021 | +0,016 | +0,317 | −0,711 |
| 2024H1 | 2 674 | 1 291 | 2023-12-28 14:46 | 2023-12-29 | +0,0515 | +0,0267 | +0,0073 | +0,701 | −0,251 | −0,101 |
| 2024H2 | 3 973 | 1 177 | 2024-06-27 18:38 | 2024-06-28 | +0,0289 | +0,0257 | +0,0167 | +0,221 | +0,147 | −0,469 |
| 2025H1 | 5 135 | 2 020 | 2024-12-28 23:54 | 2024-12-29 | +0,0451 | +0,0127 | −0,0397 | +0,670 | +0,280 | +0,207 |
| 2025H2 | 7 133 | 3 813 | 2025-06-27 21:10 | 2025-06-28 | **−0,0314** | −0,0091 | −0,0145 | −0,122 | −0,233 | **+0,596** |
| **TB 6 fold** | | | | | **+0,0187** (5/6 +) | +0,0250 (5/6 +) | **−0,0080** | | | |
| pooled | | | | | +0,0105 | +0,0122 | | | | |
Sai số chuẩn Spearman ≈ 1/√n_test = 0,016–0,037 ⇒ mọi IC fold nằm trong ±2 SE của 0. Fold lớn nhất 2025H2 (39% OOS) IC ÂM và BOT tốt nhất.
Permutation: IC(score_perm, nhãn xáo) TB −0,008; IC(score_perm, nhãn thật) TB +0,008 ⇒ pipeline không rò, và IC thật (+0,019) chỉ cách nền ~0,01–0,03.

## 4. Tercile ghép 6 fold (OOS 2023–2025, n = 9 856)
### 4a. M24 — net_B24 (chính)
| nhóm | n | net mean | median | CI raw | CI inflate ×1,18 | win | SL | 2023 / 2024 / 2025 | SL 2023 / 24 / 25 |
|---|---|---|---|---|---|---|---|---|---|
| **TOP** | 3 283 | **+0,235%** | +2,77% | [−0,106; +0,568] | [−0,167; +0,629] | 67,7% | **27,5%** | +0,168 / +0,472 / +0,152 | 25,7 / 26,0 / 28,7 |
| MID | 3 285 | −0,007% | +2,71% | [−0,309; +0,305] | [−0,364; +0,361] | 66,0% | 28,6% | +0,262 / −0,061 / −0,055 | 27,4 / 27,7 / 29,3 |
| BOT | 3 288 | +0,153% | +2,71% | [−0,118; +0,441] | [−0,167; +0,492] | 66,4% | 27,5% | −0,322 / −0,276 / +0,461 | 30,6 / 29,0 / 26,0 |
| ALL OOS | 9 856 | +0,127% | — | [−0,086; +0,335] | — | — | 27,9% | +0,036 / +0,045 / +0,186 | — |
TOP − ALL = +0,11pp; TOP − BOT = +0,08pp. Stress TOP − 0,10% = **+0,135%** (C5 ✔ ở điểm ước lượng, nhưng CI raw đã chứa 0).
n theo năm TOP: 517 / 822 / 1 944.

### 4b. M12 — net_B12 (phụ, không vào luật GO)
| nhóm | n | net mean | median | CI raw | CI inflate ×1,18 | win | SL | 2023 / 2024 / 2025 |
|---|---|---|---|---|---|---|---|---|
| TOP | 3 283 | +0,245% | +2,66% | [−0,012; +0,513] | [−0,058; +0,561] | 66,6% | 25,3% | +0,384 / +0,222 / +0,218 |
| MID | 3 285 | −0,248% | +2,37% | [−0,518; +0,016] | [−0,567; +0,063] | 63,4% | 26,4% | +0,221 / −0,160 / −0,411 |
| BOT | 3 288 | +0,188% | +2,55% | [−0,118; +0,493] | [−0,172; +0,548] | 64,9% | 23,8% | −0,403 / +0,081 / +0,390 |
| ALL OOS | 9 856 | +0,062% | — | [−0,137; +0,261] | — | — | 25,2% | +0,067 / +0,048 / +0,066 |
B12 cũng không qua (CI raw lo −0,012; SL 25,3% > 25%); BOT > 0 và MID < 0 ⇒ quan hệ score–net không đơn điệu.

## 5. Net theo decile score (M24, ghép theo fold; 0 = score thấp nhất)
| decile | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|---|---|
| n | 989 | 985 | 985 | 986 | 985 | 986 | 986 | 985 | 985 | 984 |
| net % | +0,339 | −0,301 | +0,378 | +0,391 | −0,466 | −0,047 | +0,272 | +0,324 | +0,121 | +0,260 |
| SL % | 26,0 | 30,6 | 27,1 | 25,7 | 31,4 | 28,3 | 27,3 | 26,9 | 27,9 | 27,6 |
Không đơn điệu; decile thấp nhất (+0,34%) ngang decile cao nhất (+0,26%). SL-rate 25,7–31,4% không theo thứ tự score.

## 6. Importance (permutation trên test mỗi fold, scorer = Spearman IC, 5 lần lặp; M24)
| feature | ΔIC TB | 2023H1 / 23H2 / 24H1 / 24H2 / 25H1 / 25H2 |
|---|---|---|
| btc_r60 | +0,0119 | +0,020 / +0,021 / +0,011 / +0,010 / +0,008 / 0,000 |
| n_trig_day | +0,0101 | −0,011 / +0,030 / +0,007 / +0,013 / +0,035 / −0,014 |
| r15 | +0,0087 | +0,017 / +0,007 / +0,017 / +0,015 / −0,002 / −0,003 |
| ext24 | +0,0058 | +0,015 / +0,004 / +0,012 / +0,007 / −0,013 / +0,010 |
| takerLS | +0,0048 | −0,006 / −0,005 / +0,028 / +0,008 / +0,014 / −0,010 |
| r60 | +0,0042 | |
| wick, fund_now, fund_sign, tier | ≈ 0 (−0,0001…+0,0003) | |
| btc_bull | −0,0015 | |
| volratio | −0,0044 | |
| listing_age | −0,0058 | (âm = feature gây nhiễu OOS) |
Mức importance lớn nhất (+0,012 IC) ≈ 1 SE ⇒ không feature nào mang tín hiệu OOS rõ.

## 7. Ablation KHÓA (chỉ báo cáo, không chọn)
| biến thể | IC fold 23H1 / 23H2 / 24H1 / 24H2 / 25H1 / 25H2 | IC TB | fold + | TOP net | TOP SL | TOP CI raw | TOP 2023 / 24 / 25 |
|---|---|---|---|---|---|---|---|
| Đủ 13 feature | +0,012 / +0,007 / +0,052 / +0,029 / +0,045 / −0,031 | +0,0187 | 5/6 | +0,235% | 27,5% | [−0,106; +0,568] | +0,168 / +0,472 / +0,152 |
| A1 bỏ f6–f9 (crowding) | +0,053 / +0,019 / +0,053 / +0,004 / +0,040 / −0,028 | +0,0234 | 5/6 | +0,193% | 27,8% | [−0,125; +0,507] | +0,141 / +0,210 / +0,199 |
| A2 bỏ f10–f14 (context) | +0,029 / −0,012 / +0,053 / +0,019 / +0,018 / −0,027 | +0,0131 | 4/6 | +0,143% | 27,8% | [−0,152; +0,421] | +0,189 / +0,090 / +0,154 |
| A3 chỉ f1–f5 (giá/vol) | +0,069 / −0,037 / +0,070 / −0,013 / −0,012 / −0,004 | +0,0120 | 2/6 | +0,185% | 27,9% | [−0,084; +0,462] | +0,297 / +0,280 / +0,114 |
Không biến thể nào gần C1; mọi biến thể TOP SL 27,5–27,9% (= ALL). Bỏ crowding không làm xấu đi ⇒ funding/taker tại t không thêm thông tin OOS.

## 8. Mô tả post-hoc (KHÔNG phải test, không ảnh hưởng phán quyết): Spearman đơn biến trên toàn DEV 2022–2025 (in-sample)
| feature | IC vs net_B24 (all; 2022/23/24/25) | IC vs SL (all) |
|---|---|---|
| r15 | +0,040 (+0,083/+0,063/+0,069/+0,017) | +0,003 |
| fund_now | +0,039 (+0,032/+0,066/+0,077/+0,036) | +0,007 |
| fund_sign (=f6<0) | −0,037 (4/4 năm âm) | +0,007 |
| ext24 | +0,031 | +0,029 |
| r60 | +0,030 (4/4 +) | +0,033 |
| btc_r60 | −0,029 (4/4 −) | −0,005 |
| n_trig_day | +0,028 (4/4 +) | −0,007 |
| btc_bull | +0,024 (4/4 +) | +0,010 |
| còn lại (volratio, wick, takerLS, tier, listing_age) | \|IC\| ≤ 0,016 | \|IC\| ≤ 0,031 |
|IC(feature, SL)| ≤ 0,033 với mọi feature ⇒ **không feature nào tại t nhận diện được lệnh continuation (SL)**. Tín hiệu đơn biến dấu ổn định
(r15, fund_now, n_trig_day, btc_r60) chỉ cỡ 0,03–0,04 và tác động lên ĐỘ LỚN lãi, không lên xác suất SL; fund_now một phần là cơ học
(funding > 0 ⇒ short NHẬN carry, đã nằm trong net).

## 9. Vì sao NO-GO (tóm tắt)
1. **IC quá nhỏ:** +0,019 (TB fold) / +0,011 (pooled) so với ngưỡng 0,05; SE fold 0,016–0,037 ⇒ không phân biệt được với 0. Lý thuyết: với
   σ(net_B24) = 7,0%/lệnh (đo), IC 0,02 chỉ dịch mean tercile-top khoảng 0,02 × 7,0% × 1,09 ≈ +0,15pp — đúng như đo (TOP − ALL +0,11pp), không đủ kéo CI lên khỏi 0.
2. **Continuation không đoán được tại t:** SL-rate TOP 27,5% = BOT 27,5% = ALL 27,9%; decile SL không theo score; |IC(feature, SL)| ≤ 0,033.
   Lệnh short thua là pump tiếp diễn ≥ +10% trong 24h — thông tin quyết định nằm SAU t (dòng lệnh/thanh lý tiếp theo), không trong giá/volume/
   funding settle/taker 5m tại t.
3. **Không ổn định theo thời gian:** fold 2025H2 (n 3 813, 39% OOS) IC −0,031, BOT +0,60% > TOP −0,12%. C3 (3/3 năm TOP > 0) đạt nhưng
   2023 TOP +0,17% chỉ nhờ ALL 2023 đã ≈ 0 và tercile nhỏ (n 517).

## 10. Giới hạn
- f6 là proxy TRỄ (funding settle gần nhất, trễ p50 2,3h) — không phải predicted funding tại t; f8 BỎ (không có OI thô DEV); f9 trễ thêm 1 slot 5'.
- Tercile/decile theo phân phối score CỦA fold test (không dùng nhãn) — live cần ngưỡng causal; không ảnh hưởng kết luận NO-GO.
- `max_features=0.8` của sklearn chọn feature theo NÚT (LightGBM `feature_fraction` theo CÂY) — khác nhỏ đã ghi pre-reg.
- Slippage tại spike chưa mô hình (net là CẬN TRÊN, như R1). 2025 chiếm 59% OOS. Kiểm nhiều lần (M24, M12, 3 ablation) — mọi biến thể đều NO-GO nên không cần hiệu chỉnh.
- Mục 8 là in-sample post-hoc trên toàn DEV, chỉ để mô tả.

## 11. Amend cho vòng sau (KHÔNG chạy; mỗi ý cần pre-reg mới)
1. Thông tin tách continuation có lẽ nằm ở dữ liệu vi cấu trúc forward (OI thô 1m, liquidation, orderbook, predicted funding) — chỉ có từ
   derivs_store 2026-09 ⇒ cần thu thập forward, không làm được trên DEV hiện có.
2. Nếu vẫn muốn khai thác 4 tín hiệu đơn biến dấu ổn định (r15+, fund_now+, n_trig_day+, btc_r60−): pre-reg một điểm số tuyến tính rank-sum
   CỐ ĐỊNH (không học) và test trên dữ liệu chưa thấy (2026 niêm phong hoặc forward) — rủi ro: đã thấy số trên DEV ⇒ chỉ holdout mới hợp lệ.
3. Đổi bài toán: thay vì lọc lệnh, giảm thiệt hại continuation bằng exit (SL theo thời gian/cấu trúc) — nhưng R1 đã khoá lưới exit; cần vòng riêng.
4. Không nên tune thêm model trên DEV này: IC thật ~0,01–0,02 ≈ nền permutation, dư địa chỉ là overfit.

## 12. Tái lập
`python3 research/analysis/short_v3_r1b_selector.py feat` (≈ 2,5 phút: 41 865 phút Aerospike + 1 lượt quét `oi_percoin_full.bin`)
→ `python3 research/analysis/short_v3_r1b_selector.py model` (≈ 20 giây). Đầu vào: `r1_cache/trades_r1.csv`, `cand_*.parquet`,
`/tmp/fund_cache.npz`, `p0a_cache/qv`, `CLOSES_1H.bin`, `claudedata/oi/oi_percoin_full.bin` (+ `symbol_map.csv`).
