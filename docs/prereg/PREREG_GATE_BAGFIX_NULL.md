# PRE-REG — GATE_BAGFIX_NULL (Pha C chương trình GATE)

- Ngày chốt: 2026-10-04, TRƯỚC khi sinh pred.bin / đẩy kernel của vòng này. MASTER chốt thiết kế; không đổi arm/luật/thước sau khi thấy số.
- Nền: `docs/result/RESULT_GATE_SEEDBAND.md` (7bd71b41; pre-reg f79670a9 / 11b61a9d), `research/analysis/gate_seedband_driver.py`, `research/analysis/gate_ablation_driver.py` (quy tắc ánh xạ đơn điệu nhánh `MAPPED` của RND/RULE/H60). Driver vòng này: `research/analysis/gate_bagfix_null_driver.py`.
- Tham chiếu A1 = B0@K24 (`n700-a1`, printDone d9abf35f, n 3526; pred.bin gốc md5 5dd6bb4c = seed 42). Dải 8 seed = {A1, gabl-seed7, gsb-s13, gsb-s21, gsb-s99, gsb-s123, gsb-s777, gsb-s2024} — có sẵn, KHÔNG chạy lại. BAG8 cũ (gsb-bag8) và NULLB cũ (gsb-nullb, rng 20261004) dùng lại; NULLB cũ = null #0.
- Ràng buộc: 0 sửa .java, 0 build, 0 Java sim trên Oracle; sim chỉ Kaggle, kernel = `tools/kaggle_sim.py` HEAD (md5 8b60b00a, NOWRITE242) + khối chèn `pred_ds` y nguyên GATE_ABLATION/GATE_SEEDBAND; ≤ 2 kernel song song. Dữ liệu ≤ 2025-12-31. df trước mỗi bước ghi; < 500 MB ⇒ dừng. pred.bin chỉ 1 bản/arm, dataset Kaggle = hardlink.

## 1. Câu hỏi
- Q1 BAG8 sau ánh xạ đơn điệu về phân phối p15 gốc (BAG8M) có nằm trong/trên dải seed không? (test: bagging tốt nhưng bị méo thang đo — BAG8 cũ co đuôi p15 ⇒ mở ít phút hơn).
- Q2 Bagging theo HẠNG (RBAG8) khác BAG8M không?
- Q3 Phân phối null: 4 hoán vị khối 30 ngày nữa + NULLB cũ = 5 null; gate thật (8 seed) cách null bao nhiêu sd?

## 2. Arm (CỐ ĐỊNH, 6 kernel K24, B0 overrides + `SELECTOR_RANK_TOPK=24` như A1)
Ký hiệu: DEV = các phút có ts < 2026-01-01 00:00 +07 (`GA.SEAL`; tiền tố liên tục của pred.bin, n_DEV = 2 500 260 − 420 = 2 499 840; driver assert). p0 = p15 pred.bin gốc (seed 42). P_s = p15 thô của 8 seed: 42 = p0, 7 = `gabl/pred_SEED7` (b737fb6d), 13/21/99/123/777/2024 = `gsb/pred_S*` (md5 như PREREG_GATE_SEEDBAND §6); md5 từng thành phần assert trước khi dùng. 420 phút ≥ 2026 giữ p0 ở mọi arm (sim dừng 2025-12-31).
Ánh xạ đơn điệu QM(x): trên DEV, `order = DEV[argsort(x[DEV], kind="stable")]` (hoà ⇒ theo thứ tự chỉ số), `y[order] = sort(p0[DEV])` ⇒ y là hoán vị đúng tập giá trị p0 trên DEV theo thứ tự của x (= `GA.gen` nhánh MAPPED, giới hạn vào DEV).

| arm | p15 | tag Kaggle | dataset |
|---|---|---|---|
| BAG8M | QM(x), x = trung bình float64 của 8 P_s (cộng theo thứ tự 42, 7, 13, 21, 99, 123, 777, 2024 như `GSB.bag`, KHÔNG cast float32 trước khi xếp) | gbn-bag8m | chuyendinh/gate-bn-bag8m |
| RBAG8 | QM(x), x = trung bình float64 của 8 rank-pct; rank-pct_s = `pandas.Series(P_s[DEV]).rank(method="average", pct=True)` (hạng trung bình hoà / n_DEV) | gbn-rbag8 | gate-bn-rbag8 |
| NULL1..NULL4 | đúng thủ tục NULLB cũ (`GSB.nullb`): p0 trên DEV, khối = floor((ts − ts_đầu)/30 ngày) (58 khối), `numpy.random.default_rng(k).permutation(58)`, k = 1, 2, 3, 4; ghép giá trị khối theo thứ tự hoán vị rồi đặt tuần tự lên vị trí ts gốc | gbn-null1..4 | gate-bn-null1..4 |

KHÔNG thêm arm, KHÔNG đổi pct/ngưỡng (`SIM_GATE_ROLLING_PCT` 0.999950829, DCA_LEVEL1/warm-up 0,008 giữ nguyên), KHÔNG thử trọng số/seed khác. Thứ tự đẩy: BAG8M + RBAG8 trước, rồi NULL1..4.

## 3. Cổng
- **G0** (mỗi pred.bin; commit md5 bổ sung TRƯỚC khi đẩy kernel; G0 trượt ⇒ không đẩy arm đó, báo MASTER):
  (a) format `GA.g1`: n = 2 500 260, header/size như gốc, `ts` + `risk4h` byte-identical, p15 hữu hạn;
  (b) spot-check 3 mốc `GA.SPOT` (2022-06-13, 2024-08-05, 2025-10-10: phút đầu ngày + phút max p0) — ghi p0 vs arm;
  (c) multiset p15 trên DEV == multiset p0 trên DEV (sort bằng nhau tuyệt đối) cho cả 6 arm; 9 decile (10…90%) p15 DEV của BAG8M/RBAG8 khớp p0 ± 1e-6; 420 phút ≥ 2026 == p0.
- **G2 quota**: n lệnh/năm (đóng 2022–2025) và phút gate-mở/năm (phút phân biệt có ≥ 1 entry PREDICT_SYMBOL_TRADE, 2022–2025) trong [0,75; 1,25] × A1 (732 / 146,5). Báo riêng phút mở 2022 (A1 170; seed 106–170; BAG8 cũ 101). BAG8M/RBAG8 trượt G2 ⇒ "không diễn giải" arm đó. Null trượt G2 ⇒ loại khỏi phân phối null (báo kèm bản đủ 5); < 3 null hợp lệ ⇒ Q3 "không diễn giải được".
- **Parity Kaggle** từng run (y nguyên GATE_SEEDBAND): jar sha 7368be46, mapper ≥ 800, `SELECTOR_RANK_TOPK=24` + B0OV trong prof_run, `pred_md5_base` = 5dd6bb4c, `pred_md5_used` = md5 arm, log Java "md5 verified". Trượt ⇒ run VOID.

## 4. Thước (cố định)
- Cửa sổ 2022-01-01..2025-12-30, MTM ngày rebase 2021-12-31 (`N.arm_metrics`, MTM `R.run_mtm` cost legacy) — y nguyên GATE_SEEDBAND: CAGR22, maxDD = `dd_mtm22` (kèm `dd_mtm` toàn kỳ), Calmar22, UW22, PnL 2022–25, n/năm, phút gate-mở/năm (+ theo năm).
- Ghép cặp vs A1: bootstrap lợi suất NGÀY MTM block 10 ngày, NREP 2000, seed 20260905 (`SAD.daily_boot`) cho ΔCAGR22; ΔPnL theo ngày đóng (`N.pnl_boot`). Inflate half-width × √(2 ln k), **k = 6** (6 arm mới) = 1,893. Thêm cặp **RBAG8 − BAG8M** (cho Q2). Báo theo năm + theo quý.
- Vị trí trong dải 8 seed (dải tính lại từ dữ liệu, phải khớp RESULT_GATE_SEEDBAND: CAGR22 mean 34,18 / sd 3,58 / median 33,54; Calmar22 median 1,455): percentile = 100 × #{seed: giá trị ≤ arm}/8 cho CAGR22, Calmar22, dd_mtm22, UW22, ΔPnL.
- Jaccard (2022–2025): tập phút gate-mở và tập lệnh (sym|phút vào); TB(arm, seed_i) trên 8 seed; Jaccard cặp đôi seed TB 28 cặp (tính lại, kỳ vọng 0,656 / 0,586). Báo kèm Jaccard BAG8M~BAG8, RBAG8~BAG8M.
- Có/không 2022 (mọi arm, kể cả A1/7 seed/BAG8/NULLB cũ): thêm CAGR23 / maxDD23 / Calmar23 trên equity MTM cuối ngày (b+unP, `R.load_daily`) cửa sổ 2022-12-31..2025-12-30 (rebase 2022-12-31) — chỉ báo cáo.

## 5. Luật diễn giải (cố định)
- **Q1 (BAG8M)** và RBAG8 (cùng luật): ghi percentile trong dải; vị trí CAGR22: < min seed ⇒ "dưới dải", min…max ⇒ "trong dải", > max ⇒ "trên dải". **"Ứng viên giảm phương sai"** ⇔ CAGR22 ≥ median seed (33,54) AND Calmar22 ≥ 0,9 × median Calmar22 seed AND |dd_mtm| ≤ 40 AND |dd_mtm22| ≤ 40 AND Jaccard phút TB(arm, seed_i) > Jaccard phút cặp đôi seed (0,656) (và arm đạt G2 + parity, nếu không ⇒ "không diễn giải"). Không có cổng "> A1".
- **Q2**: RBAG8 "khác" BAG8M ⇔ CI inflate (k = 6) của ΔCAGR22 (RBAG8 − BAG8M, bootstrap MTM ngày ghép cặp) không chứa 0; ngược lại "không phân biệt được". Báo kèm ΔPnL ghép cặp, Jaccard phút/lệnh RBAG8~BAG8M, kết luận Q1-luật của từng arm.
- **Q3**: tập null = NULLB cũ + NULL1..4 đạt G2 + parity. mean/sd (ddof=1) CAGR22 null; **d = (mean CAGR22 8 seed − mean null)/sd null**. d ≥ 3 ⇒ "gate có giá trị timing rõ"; 1 ≤ d < 3 ⇒ "có nhưng mỏng"; d < 1 ⇒ "không đo được". Chỉ báo cáo: d trên Calmar22, d trên CAGR23 (không 2022), d bản đủ 5 null nếu có null trượt.
- Báo bản có/không 2022 cho mọi arm. Không tune. Mọi thứ ngoài pre-reg = chỉ báo cáo.

## 6. md5 pred.bin (điền sau khi sinh, commit bổ sung TRƯỚC khi đẩy kernel)
| arm | md5 pred.bin | G0 (fmt / multiset DEV / 2026 = p0 / decile maxdiff) | spearman vs gốc | ghi chú |
|---|---|---|---|---|
| BAG8M | `a56d99b6880166ebe63033715a766285` | PASS (True/True/True/0.0e+00) | 0.9984 | spearman(x, p0)_DEV 0.99838; x float32 == BAG8 cũ: True |
| RBAG8 | `e571ce90757172e53131db35b09deeb8` | PASS (True/True/True/0.0e+00) | 0.9984 | spearman(x, p0)_DEV 0.99840; x float32 == BAG8 cũ: None |
| NULL1 | `8490f16b807f0bdf12a0a5a8ac97bce7` | PASS (True/True/True/0.0e+00) | 0.0055 | rng 1, 58 khối, perm[:6] [40, 6, 28, 30, 14, 20] |
| NULL2 | `b681c3e93e2004e5b12e5b8f90fab884` | PASS (True/True/True/0.0e+00) | 0.0852 | rng 2, 58 khối, perm[:6] [47, 23, 38, 6, 40, 48] |
| NULL3 | `730fb2729cdc42464b6b8fd1ee7e94e4` | PASS (True/True/True/0.0e+00) | 0.1434 | rng 3, 58 khối, perm[:6] [22, 0, 3, 37, 52, 2] |
| NULL4 | `d03842d878a0b0f69ea459aaf0473e7e` | PASS (True/True/True/0.0e+00) | 0.1302 | rng 4, 58 khối, perm[:6] [57, 37, 54, 23, 18, 35] |

Spot-check 3 mốc (p0 → arm) trong `~/claude_master/1004/gbn/g1.json`; G0 đầy đủ `g0.json`. Sinh bằng `gate_bagfix_null_driver.py gen` (commit 8ee3b238), 11 s, RSS 0,89 GB.
