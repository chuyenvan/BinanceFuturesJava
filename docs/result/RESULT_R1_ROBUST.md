# RESULT_R1_ROBUST — fade R1 chấm theo NGÀY (0-sim)

Pre-reg: `docs/prereg/PREREG_R1_ROBUST.md` (`9ce3c459`, chốt TRƯỚC đo) · Nguồn: R1 `3fea4f50` (per-trade n = 10 991), R1c (n = 10 977), lineage v2 `e5b89a31`.
Script: `research/analysis/r1_robust.py` · Số: `docs/result/RESULT_R1_ROBUST.json` (md5 9365d29c). Chạy < 5 s, chỉ đọc CSV. 0 stream 1m, 0 Kaggle, 0 Java, 0 chạm 242, không đọc 2026.

## Kết luận: luật pre-reg **BỀN** (D1 ✔ D2 ✔ D3 ✔ cho cả S_B24 và S_B12) — nhưng R1 vẫn **NO-GO** (G1 gãy cả với CI cluster-ngày; không ô nào đổi trạng thái).
Chấm theo ngày KHÔNG làm tín hiệu yếu đi mà ngược lại: mean theo ngày S_B24 **+0,424%** (pooled +0,170%), 4/4 năm +0,38…+0,54%.
Lý do: ngày đông lệnh (≥ 50 lệnh/ngày: 6 ngày, 513 lệnh) là ngày LỖ (mean −1,21%, ΣPnL −6,19 = −33% tổng) — cụm theo ngày đang kéo pooled XUỐNG, không thổi lên.
Lo ngại của R3 (2 ngày sập) KHÔNG áp dụng cho R1: 2025-10-10 chỉ 22 lệnh (+3,9% ΣPnL), 2024-08-05 chỉ 1 lệnh.

Cảnh báo (risk-first): (i) day-weighted = ước lượng thống kê, KHÔNG phải chiến lược chạy được (số lệnh/ngày chỉ biết sau ngày; trọng số 1/m_d là look-ahead);
(ii) n hiệu dụng ≈ 5 000 (deff ≈ 2,2), không phải 10 991; (iii) post-hoc ngoài pre-reg: bỏ 10 ngày DƯƠNG nhất ⇒ S_B24 pooled còn +0,064% (10 ngày = 64% ΣPnL) — đuôi ngày dày cả 2 phía;
(iv) slippage tại spike vẫn chưa mô hình (giới hạn R1 §8 giữ nguyên).

Parity (bắt buộc): S_B24 pooled +0,1699% CI block-72h raw [−0,0297; +0,3686]% = R1 (khớp tới 1e-6); R1c S_TK24 vs R1 S_B24 cùng (sym,t): 10 977/10 977 khớp, lệch tối đa 0. **PASS**.
Kiểm độc lập (`r1r_check`, không import script): day-weighted 0,004237 / 0,003625 khớp; ngày theo phút entry t+1 khớp; DGB lệnh exit 2024-04-02 07:45 > last_real 2024-04-01 09:59 (delist) xác nhận.

## Bảng 7 phép đo (S_B24 chính · S_B12 phụ; net/lệnh, %)
| # | phép đo | S_B24 | S_B12 |
|---|---|---|---|
| base | pooled n 10 991; CI block-72h raw | +0,170 [−0,030; +0,369] | +0,101 [−0,093; +0,289] |
| 1 | mean THEO NGÀY (1 318 ngày); median | **+0,424**; +0,679 | **+0,363**; +0,508 |
| 1 | CI block-72h chuỗi ngày raw / inflate ×1,89 | [+0,191; +0,640] / [−0,016; +0,833] | [+0,163; +0,559] / [−0,014; +0,734] |
| 1 | theo năm 2022/23/24/25 (mean theo ngày) | +0,54 / +0,38 / +0,39 / +0,40 (4/4) | +0,46 / +0,33 / +0,37 / +0,31 (4/4) |
| 2 | bỏ top-k theo abs(ΣPnL ngày) k=1/3/5/10: pooled | +0,210 / +0,217 / +0,220 / +0,234 | +0,144 / +0,197 / +0,195 / +0,191 |
| 2 | bỏ top-k theo số lệnh k=1/3/5/10: pooled | +0,143 / +0,188 / +0,239 / +0,233 | +0,099 / +0,150 / +0,204 / +0,190 |
| 2 | (ngoài pre-reg) bỏ top-k ngày DƯƠNG nhất k=1/3/5/10 | +0,143 / +0,118 / +0,099 / +0,064 | +0,087 / +0,068 / +0,052 / +0,018 |
| 3 | lệnh/ngày (ngày có lệnh): mean / median / p90 / p99 / max | 8,3 / 5 / 20 / 38 / 124 (143/1 461 ngày trống) | như B24 |
| 3 | top-10 ngày theo n: % n ; % ΣPnL | 6,3% ; **−28,8%** | 6,3% ; −75,9% |
| 3 | 2025-10-10: n ; ΣPnL ; mean ; % ΣPnL | 22 ; +0,73 ; +3,33% ; +3,9% | 22 ; +0,68 ; +3,10% ; +6,1% |
| 3 | 2024-08-05: n ; mean ; % ΣPnL | 1 ; −10,11% (SL) ; −0,5% | 1 ; −10,11% ; −0,9% |
| 3 | bỏ 2 ngày sập: pooled | +0,164 | +0,096 |
| 4 | loại lineage: index/stable 15 (BLUEBIRD 4, DEFI 2, FOOTBALL 9) + sau last_real 1 (DGB) + trước first_real 0 | n 10 975, +0,166 [−0,033; +0,364], 4/4 năm; Δ −0,004pp | n 10 975, +0,098; Δ −0,004pp |
| 5 | SL-rate theo n_trig_day 1 / 2–4 / 5–9 / 10–19 / 20–49 / ≥50 | 21,5 / 23,7 / 27,6 / 28,9 / 28,1 / 27,9% | 17,9 / 20,5 / 24,4 / 25,8 / 26,1 / 25,0% |
| 5 | mean net theo bucket trên | +1,02 / +0,59 / +0,10 / +0,15 / +0,26 / **−1,21** | +0,87 / +0,57 / +0,06 / +0,10 / +0,23 / −1,93 |
| 5 | ngày n ≥ 20 (top-10%, 135 ngày): % lệnh vs % SL; ρ Spearman(n, SL-rate) | 35,5% vs 36,0%; ρ +0,11 (969 ngày ≥3) | 35,5% vs 37,1%; ρ +0,15 |
| 5 | top-10 ngày theo số SL chiếm % SL | 6,8% | 6,9% |
| 6 | ICC trong ngày (cặp) / ICC ANOVA (kiểm) | 0,067 / 0,041 | 0,063 / 0,035 |
| 6 | deff (m̄_w 19,2) ; n_eff ICC ; n_eff bootstrap ngày ; n_eff block-72h | 2,22 ; 4 959 ; 5 027 ; 4 934 | 2,14 ; 5 135 ; 5 196 ; 4 989 |
| 7 | CI cluster-ngày pooled raw / inflate | [−0,032; +0,357] / [−0,211; +0,524] | [−0,086; +0,279] / [−0,252; +0,437] |
| 7 | G1 72h → G1 ngày ; GO | ✘ → ✘ ; ✘ | ✘ → ✘ ; ✘ |

## 7. G1–G6 với CI cluster-ngày (6 ô short; G2–G6 giữ định nghĩa R1) — CHỈ BÁO CÁO
| ô | mean | CI 72h raw | CI ngày raw | CI ngày inflate | G1 72h→ngày | G2 | G3 | G4 SL | G5 | G6 long | GO |
|---|---|---|---|---|---|---|---|---|---|---|---|
| S_A4 | +0,009 | [−0,130; +0,139] | [−0,127; +0,136] | [−0,247; +0,249] | ✘→✘ | ✔ 3/4 | ✔ | ✘ 27,9% | ✔ | ✔ −0,210 | ✘ |
| S_A12 | +0,030 | [−0,098; +0,146] | [−0,091; +0,147] | [−0,199; +0,251] | ✘→✘ | ✔ 3/4 | ✔ | ✘ 30,8% | ✔ | ✔ −0,240 | ✘ |
| S_A24 | +0,040 | [−0,087; +0,155] | [−0,081; +0,156] | [−0,188; +0,259] | ✘→✘ | ✔ 3/4 | ✔ | ✘ 31,6% | ✔ | ✔ −0,268 | ✘ |
| S_B4 | +0,027 | [−0,183; +0,213] | [−0,172; +0,208] | [−0,348; +0,368] | ✘→✘ | ✔ 3/4 | ✔ | ✔ 19,5% | ✔ | ✔ −0,267 | ✘ |
| S_B12 | +0,101 | [−0,093; +0,289] | [−0,086; +0,279] | [−0,252; +0,437] | ✘→✘ | ✔ 4/4 | ✔ | ✔ 24,9% | ✔ | ✔ −0,346 | ✘ |
| S_B24 | +0,170 | [−0,030; +0,369] | [−0,032; +0,357] | [−0,211; +0,524] | ✘→✘ | ✔ 4/4 | ✔ | ✘ 27,6% | ✔ | ✔ −0,450 | ✘ |
**0/6 ô đổi trạng thái.** CI cluster-ngày gần như trùng block-72h (n_eff 5 027 vs 4 934) ⇒ block-72h của R1 đã hấp thụ cụm theo ngày; R1 NO-GO không do cách cluster.

## R1c (báo kèm, phép 1)
| ô | n | pooled | mean theo ngày (ngày) | CI 72h chuỗi ngày raw / inflate | năm + |
|---|---|---|---|---|---|
| S_TK24 | 10 977 | +0,170 | +0,424 (1 317) | [+0,191; +0,640] / [−0,017; +0,833] | 4/4 |
| S_LM24 (fill LIMIT) | 8 274 | +0,111 | +0,287 (1 248) | [+0,047; +0,538] / [−0,167; +0,762] | 4/4 |

## Diễn giải
- Cụm theo ngày có thật (ICC 0,04–0,07, deff ≈ 2,2) nhưng tác động lên dấu là NGƯỢC với lo ngại R3: ngày "guồng toàn thị trường" (nhiều trigger) cho fade
  kém/âm (pump lan rộng = continuation có tính hệ thống), ngày ít trigger (pump riêng lẻ) cho fade tốt (+0,6…+1,0%). SL-rate tăng nhẹ theo n/ngày
  (21,5% → ~28%) nhưng SL KHÔNG dồn vào vài ngày (top-10 ngày = 6,8% SL; ngày n ≥ 20 chiếm 36,0% SL vs 35,5% lệnh); khoản lỗ ngày đông đến từ cả lệnh không-SL.
- Mean theo ngày CI raw > 0 nhưng inflate ×1,89 chạm 0 (lo −0,016%) ⇒ nếu dùng chính G1 của R1 trên chuỗi ngày vẫn KHÔNG qua (sát nút).
- Lineage: không đổi gì đáng kể (16 lệnh, Δ −0,004pp); không có lệnh trước first_real.
- Bỏ top ngày âm/đông làm mean TĂNG; bỏ top ngày dương làm mean giảm tới +0,064% (k=10) nhưng vẫn > 0. Phân phối ΣPnL ngày đuôi dày hai phía.

## Ý tưởng tiếp (KHÔNG chạy; cần pre-reg mới + holdout 2026)
1. Bản chạy được của "trọng số ngày": giới hạn ex-ante (k trigger đầu tiên mỗi ngày UTC, hoặc trần lệnh mở đồng thời) — đo trên DEV, chốt k trước.
2. Breadth filter ex-ante: số trigger trong 1–4h trước làm proxy "guồng toàn thị trường" (bỏ fade khi breadth cao). Cả 2 đều là selector mới ⇒ chịu inflate.

## Tái lập
`python3 research/analysis/r1_robust.py` (đọc `~/claude_master/1002/r1_cache/trades_r1.csv`, `~/claude_master/1002/r1c_cache/trades_r1c.csv`, `data/meta/symbol_lineage_v2.csv`) → JSON md5 9365d29c.
