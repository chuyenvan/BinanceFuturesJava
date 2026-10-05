# PREREG_R1_ROBUST — robustness của fade R1 khi chấm theo NGÀY (0-sim)

Chốt TRƯỚC khi đo. Nguồn: R1 `3fea4f50` (`docs/result/RESULT_SHORT_V3_R1.md`), per-trade `~/claude_master/1002/r1_cache/trades_r1.csv`
(n = 10 991), R1c `~/claude_master/1002/r1c_cache/trades_r1c.csv` (n = 10 977). Động cơ: re-audit R3 `625c3163` — sự kiện dồn cụm
theo ngày làm pooled mean lệch. Lineage: `data/meta/symbol_lineage_v2.csv` (DATA_AUDIT_20261003, `e5b89a31`).
0-sim: KHÔNG stream lại 1m, KHÔNG Kaggle, KHÔNG Java, KHÔNG chạm 242/shadow, KHÔNG thêm biến thể exit/trigger. DEV ≤ 2025.
Script: `research/analysis/r1_robust.py` (đọc CSV, numpy/pandas) → `docs/result/RESULT_R1_ROBUST.{md,json}`.

## Quy ước (khóa)
- Ô: **S_B24 (chính)**, **S_B12 (phụ)**; cột `S_B24_net`, `S_B12_net` (net sau phí 0,112% RT + funding exact, đúng như R1). Lý do exit `_r`: 0 TIME / 1 SL / 2 TRAIL.
- Thời điểm lệnh `ems = (t+2)·60 000 − 1` (cuối phút entry t+1, y hệt CI R1). NGÀY = ngày lịch UTC của `ems`; NĂM = năm UTC của `ems`.
- CI block-72h: y hệt R1 (`blk = ems // 72h`, NREP 2000, seed 20260905, thống kê Σsum/Σcount, phân vị 2,5/97,5; inflate nửa-độ-rộng × 1,89).
- CI cluster-ngày: như trên nhưng `blk = ngày UTC` (resample ngày có hoàn lại, Σsum/Σcount), cùng NREP/seed/inflate.
- Parity bắt buộc trước khi báo: tái tạo pooled S_B24 mean +0,170% và CI raw [−0,030; +0,369] (±0,001pp) từ CSV; lệch ⇒ VOID, không báo số.
- R1c chỉ dùng: (i) parity S_TK24 trên 10 977 = S_B24 cùng (sym,t) (lệch ≤ 1e-9); (ii) báo kèm day-weighted của S_TK24/S_LM24 ở phép 1 (chỉ báo cáo).

## 7 phép đo (KHÓA trên S_B24 và S_B12, không đổi lệnh)
1. **Trọng số theo ngày**: mỗi ngày lịch có ≥1 lệnh = 1 quan sát (= mean net các lệnh trong ngày). Báo: n_ngày, mean theo ngày, median,
   CI block-72h trên chuỗi ngày (blk = ngày_ms // 72h) raw & inflate ×1,89, theo năm (mean theo ngày mỗi năm, số năm > 0).
2. **Bỏ top-k ngày**, k ∈ {1, 3, 5, 10}: (a) theo |ΣPnL ngày| (ΣPnL = tổng net các lệnh trong ngày); (b) theo số lệnh/ngày.
   Báo pooled mean còn lại, n còn lại, và day-weighted mean còn lại. Thứ hạng xếp trên CHÍNH ô đang đo (B24 / B12 riêng), hoà → ngày sớm hơn trước.
3. **Phân phối lệnh/ngày**: số ngày lịch DEV (1 461) có/không lệnh; mean/median/p90/p99/max lệnh/ngày (trên ngày có lệnh);
   top-10 ngày theo số lệnh chiếm % n và % ΣPnL; 2 ngày sập **2025-10-10** và **2024-08-05**: n, ΣPnL, mean, SL-rate, % ΣPnL tổng,
   và pooled mean khi bỏ 2 ngày đó.
4. **Lineage sạch**: loại lệnh có (a) `status ∈ {index, stable/fiat-like}`; hoặc (b) phút entry < `first_real_ts` hoặc phút exit (`_k`) > `last_real_ts`
   của symbol; symbol không có trong lineage ⇒ đếm riêng, giữ trong base, báo. Báo n bị loại theo lý do, pooled mean & CI block-72h & theo năm sau loại, Δ so với base.
5. **SL theo ngày**: `n_trig_day` = số lệnh R1 trong ngày. SL-rate theo bucket n_trig_day {1, 2–4, 5–9, 10–19, 20–49, ≥50};
   % lệnh SL nằm trong top-10% ngày theo n_trig_day so với % lệnh nói chung ở các ngày đó; top-10 ngày theo số SL chiếm % SL;
   corr Spearman (theo ngày, ngày có ≥ 3 lệnh) giữa n_trig_day và SL-rate ngày; ΣPnL của lệnh SL thuộc bucket ≥ 20.
6. **Tương quan chéo trong ngày**: ICC = ρ̂ trung bình cặp trong cùng ngày = Σ_d[(Σx)² − Σx²] / (Σ_d m_d(m_d−1) · s²), x = net − mean, s² = var pooled.
   Design effect = 1 + (m̄_w − 1)·ρ̂, m̄_w = Σm²/Σm; n_eff = n / deff. Thêm n_eff thực nghiệm = n · var_iid(mean) / var_cluster-ngày(mean) (var bootstrap cluster-ngày).
7. **Verdict lại luật R1 (G1–G6)** trên 6 ô short S_A4..S_B24, chỉ thay CI block-72h bằng CI cluster-ngày ở G1 (G2–G6 giữ định nghĩa R1).
   Báo ô nào đổi trạng thái G1/GO. CHỈ BÁO CÁO — R1 vẫn là NO-GO đã chốt, vòng này không mở GO mới.

## Luật kết luận "BỀN theo ngày" (khóa, áp cho S_B24; B12 báo cùng luật, không quyết)
BỀN ⇔ cả 3: (D1) mean theo ngày > 0 và ≥ 3/4 năm mean-theo-ngày > 0; (D2) pooled mean > 0 sau MỌI phép bỏ top-k ở phép 2 (8 phép);
(D3) pooled mean sau lọc lineage > 0. Gãy bất kỳ ⇒ "KHÔNG BỀN" (nêu điều kiện gãy). CI ngày chứa 0 là thông tin, không phải điều kiện của luật này
(R1 đã NO-GO ở G1). n_eff báo để định cỡ, không phải điều kiện.

## Không làm
Không tune ngưỡng, không lát mới (tier/regime), không thêm exit/trigger, không đọc 2026, không sửa file R1/R1c gốc.
