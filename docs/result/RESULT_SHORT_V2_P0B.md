# RESULT — SHORT_V2 Pha 0B: squeeze-predictability của model LONG

Ngày 2026-10-02 · Pre-reg `docs/prereg/PREREG_SHORT_V2_P0B.md` (**11df71fd**, commit TRƯỚC khi đo) · Script
`research/analysis/short_v2_p0b_squeeze.py` · JSON `docs/result/RESULT_SHORT_V2_P0B.json`. Chạy 1 lần, không tune.
Pha 0B chỉ thông tin (không kill). `lp = −score` (cao = selector long thích). maxFav từ 1h close ⇒ **cận DƯỚI** squeeze.

**Kết luận 1 dòng: "mức có ích" (S1 d0 pSQ10 ≤ 0,6× universe ở 4/4 năm) — KHÔNG ĐẠT (0/4 năm; tỉ lệ 0,88 / 0,83 / 0,89 / 0,69).**

## 1. Nguồn & leak-free (chi tiết ở pre-reg §1)
- S1 `pred_s1a2x1.parquet`: WFO 16 fold OOS, purge 72h, `leakFreeFrom=2022-01-01` ⇒ dùng được. Tick đầu tiên thực tế 2022-01-03 16:15.
- pNoPump (`LATEST_SEL_PNOPUMP`, Funding `.onnx`): **chỉ live, không có panel DEV OOS ⇒ BỎ.**
- p15 `p15_dev.csv`: WFO 21 fold OOS (AUDIT_G2FLAT3 Q3) ⇒ dùng được. predRisk4H: **IN-SAMPLE**, chỉ đối chứng.

## 2. Sanity — PASS toàn bộ
| kiểm | kết quả |
|---|---|
| Snapshot S1 (tick đầu/ngày) 2022/23/24/25 | 244 / 137 / 225 / 336 snapshot · 32.501 / 24.749 / 61.073 / 143.050 coin-snap · median 133/179/259/435 coin |
| S1 toàn tick (phụ) | 2.926 / 508 / 2.260 / 11.307 tick · 0,39M / 0,09M / 0,62M / 5,17M dòng |
| Lưới p15 00:00 UTC | 365 / 365 / 366 / 358 ngày · 49.253 / 65.853 / 97.223 / 155.002 coin-ngày |
| Nhãn hợp lệ (toàn tick S1) | 95,39% (178.465 dòng bị loại vì cửa sổ vượt 2026-01-01) |
| Causal | entry > tick ở 100% dòng (tối thiểu +15′); cửa sổ cuối = 2026-01-01 00:00 ≤ seal; S1 ts ≥ 2022-01-01; p15 lấy ts ≤ snap−2′ |
| AUC 2024 S1→SQ10: rank-formula vs sklearn | 0,595003724 = 0,595003724 (khớp < 1e-9) |
| Spot-check nhãn (3 qua grid + 3 đọc lại raw `CLOSES_1H.bin` độc lập) | 6/6 khớp < 1e-5 |

**Lưu ý thiết kế (không phải lỗi):** S1 chỉ có ở tick selector — số ngày có tick rất không đều (2023 chỉ 137 ngày) và tập trung theo
regime. Kết quả S1 là "trên các ngày selector hoạt động", không phải lưới đều. Pool toàn kỳ bị 2025 chi phối (55% dòng).

## 3. AUC theo năm
| score | nhãn | 2022 | 2023 | 2024 | 2025 | toàn kỳ |
|---|---|---|---|---|---|---|
| S1 `lp` (pool, tick đầu/ngày) | SQ10 | 0,546 | 0,565 | 0,595 | 0,579 | 0,581 |
| S1 `lp` (pool) | SQ20 | 0,583 | 0,588 | 0,631 | 0,638 | 0,626 |
| S1 `lp` (trong-snapshot, mean) | SQ10 | 0,580 | 0,579 | 0,561 | 0,631 | 0,594 |
| S1 `lp` (trong-snapshot, mean) | SQ20 | 0,639 | 0,631 | 0,628 | 0,700 | 0,658 |
| S1 `lp` (pool, TOÀN tick — phụ) | SQ10 | 0,621 | 0,562 | 0,547 | 0,606 | 0,609 |
| p15 (lưới 00:00, market-level) | SQ10 | 0,648 | 0,595 | 0,601 | **0,502** | 0,546 |
| p15 (lưới 00:00) | SQ20 | 0,664 | 0,606 | 0,616 | **0,519** | 0,565 |
| p15 trên tập snapshot S1 (phụ) | SQ10 | 0,533 | 0,406 | 0,541 | 0,501 | 0,502 |
| predRisk4H **[IN-SAMPLE, không dùng kết luận]** | SQ10 | 0,432 | 0,500 | 0,444 | 0,501 | 0,477 |

Spearman(`lp`, maxFav_7d) cross-section, mean theo năm, CI95 block-7d (2000 rep, seed 20260905, không inflate):
2022 **+0,123** [0,093; 0,153] · 2023 **+0,124** [0,084; 0,164] · 2024 **+0,112** [0,078; 0,145] · 2025 **+0,193** [0,165; 0,222] ·
toàn kỳ +0,145 [0,128; 0,163]. Dương, ổn định 4/4 năm, CI ngoài 0 — nhưng độ lớn nhỏ (AUC ~0,56–0,63 cho SQ10).

## 4. Decile S1 (d0 = `lp` thấp nhất = ít pump nhất theo model), toàn kỳ (pool tick đầu/ngày)
| | n | pSQ10 | pSQ20 | mean retEnd_7d | median retEnd_7d |
|---|---|---|---|---|---|
| universe | 261.361 | 0,400 | 0,172 | −0,27% | −1,70% |
| d0 | 26.536 | **0,313** | **0,104** | −0,44% | **−1,03%** |
| d1 | 26.088 | 0,341 | 0,115 | −0,34% | −1,05% |
| d5 | 25.873 | 0,397 | 0,162 | −0,41% | −1,57% |
| d8 | 26.013 | 0,461 | 0,230 | −0,10% | −2,66% |
| d9 | 26.456 | **0,528** | **0,316** | +0,23% | **−4,83%** |

Theo năm (universe → d0 → d9; pSQ10 | pSQ20 | median retEnd):
| năm | universe | d0 | d9 | d0/univ pSQ10 |
|---|---|---|---|---|
| 2022 | 0,398 · 0,153 · −1,87% | 0,350 · 0,113 · −2,03% | 0,486 · 0,253 · −3,37% | 0,88 |
| 2023 | 0,398 · 0,166 · +0,35% | 0,332 · 0,111 · +0,42% | 0,500 · 0,276 · −2,19% | 0,83 |
| 2024 | 0,469 · 0,212 · +1,06% | 0,418 · 0,162 · +1,61% | 0,547 · 0,316 · −1,56% | 0,89 |
| 2025 | 0,371 · 0,161 · −3,12% | 0,256 · 0,075 · −1,97% | 0,534 · 0,337 · −7,53% | 0,69 |
Mean retEnd d0 vs universe: 2022 −1,69/−1,62% · 2023 +1,85/+2,13% · 2024 +2,35/+2,53% · 2025 −1,75/−1,57%.

## 5. Decile p15 (market-level: NGÀY chia theo decile p15; biên theo năm), lưới 00:00
| năm | universe pSQ10 · pSQ20 · median | d0 (p15 thấp) | d5 | d9 (p15 cao) | d0/univ pSQ10 |
|---|---|---|---|---|---|
| 2022 | 0,345 · 0,127 · −2,06% | 0,200 · 0,054 · −1,19% | 0,448 · 0,190 · −2,55% | 0,484 · 0,237 · −0,24% | 0,58 |
| 2023 | 0,338 · 0,127 · +0,15% | 0,189 · 0,055 · −0,95% | 0,416 · 0,169 · +2,29% | 0,453 · 0,189 · +0,75% | 0,56 |
| 2024 | 0,407 · 0,170 · 0,00% | 0,268 · 0,075 · −1,67% | 0,361 · 0,133 · −2,09% | 0,585 · 0,292 · +3,77% | 0,66 |
| 2025 | 0,338 · 0,140 · −2,04% | 0,316 · 0,112 · −3,75% | 0,363 · 0,169 · −0,58% | 0,341 · 0,155 · −3,48% | **0,94** |
Toàn kỳ (biên toàn DEV; số coin/ngày tăng theo năm nên pool lệch về 2025): d0 0,258 · 0,081 · −0,56% · d9 0,380 · 0,169 · −1,50%.
predRisk4H **[IN-SAMPLE]**: không đơn điệu, AUC < 0,5 ở 2022/2024 — chỉ ghi nhận, không dùng.

## 6. Hai quan sát then chốt cho Pha 1 (chỉ đọc số, không mở rộng)
1. **S1 d0 = "YÊN", không phải "GIẢM".** d0 có pSQ10 thấp hơn universe (0,313 vs 0,400; pSQ20 0,104 vs 0,172) nhưng **bleed
   KHÔNG mạnh hơn**: median retEnd_7d d0 −1,03% vs universe −1,70% (kém hơn), và kém universe ở 3/4 năm (2023/2024/2025);
   mean d0 âm hơn universe nhẹ ở 4/4 năm (−0,07 / −0,28 / −0,18 / −0,18 pp; toàn kỳ −0,17 pp) — đến từ bớt đuôi phải,
   không phải giảm mạnh hơn (median kém 3/4 năm). Bleed-median mạnh nhất lại ở **d9**
   (median −4,83%, 2025 −7,53%) — đi kèm pSQ20 cao nhất (0,316). Tức `lp` xếp theo **biên độ hai đuôi**: d9 vừa squeeze nhiều nhất
   vừa giảm-median nhiều nhất; d0 ít biến động cả hai chiều. Dùng S1 làm gate "loại coin sắp pump" sẽ hạ pSQ nhưng đồng thời bỏ bớt bleed.
2. **Thông tin squeeze có nhưng yếu và không đủ làm gate độc lập.** AUC SQ10 S1 0,55–0,60 (pool) / 0,56–0,63 (trong-snapshot),
   SQ20 cao hơn (0,58–0,70); Spearman ổn định 4/4 năm. p15 (market-level) mạnh hơn ở 2022–2024 (d0/univ 0,56–0,66) nhưng
   **gãy năm 2025** (AUC 0,50; d0/univ 0,94) và gần như vô dụng trên chính các ngày selector chạy (AUC 0,50 toàn kỳ, 2023 0,41).
   ⇒ Hợp lý nhất cho Pha 1: đưa `lp` (và p15) vào **làm feature** của selector short có nhãn path-aware, không làm gate cứng.
