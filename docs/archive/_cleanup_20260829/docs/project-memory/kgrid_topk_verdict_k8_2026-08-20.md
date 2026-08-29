# Grid SELECTOR_RANK_TOPK (Kaggle full-18w) — K=8 tối ưu — 2026-08-20

## Bối cảnh
Sau khi phát hiện live thiếu cap TOPK (over-entry), cap live về K5. Grid K để tìm K tối ưu.
Chạy Kaggle fanout full-18w (drive_exp18), cùng jar/env, chỉ khác SELECTOR_RANK_TOPK.
LƯU Ý fix hạ tầng: `.sl03bak` cũ (15/08) thiếu glob `ticker_bundle.dat` → mọi fanout Kaggle fail
"MISSING ticker" từ 15/08. Đã patch .sl03bak thêm bundle glob (backup .prebundle). Oracle-local WFO
KHÔNG dùng (ticker local 1886 file không đủ range → số sai; single-pass ExitParamSweepProbe cũng sai vì thiếu DCA grid).

## Kết quả (Kaggle full-18w, đúng config canonical DCA/giveback/moveSL0.05)
| K | FULL_18w | TOTAL_12w | posRatio lenient | WFE |
|---|---:|---:|---:|---:|
| 5 (live cũ) | 18748 | 13842 | 89% | 16/18 |
| **8** ⭐ | **20247** | **15571** | 89% | 16/18 |
| 10 | 19532 | 14588 | 89% | 16/18 |
| 12 | 18851 | 14945 | 83% | 15/18 |
| 15 | 17303 | 14150 | 78% | 14/18 |

Inverted-U, đỉnh K=8: total cao nhất (+8% full, +12.5% 12w so K5) mà ổn định giữ nguyên (89%/16-18).
Quá K10 total giảm + ổn định tụt (K12 83%, K15 78%). K5 (live cũ) hơi chặt, bỏ lỡ ~12% lãi.

## Hành động
- **Live đổi K5→K8** (2026-08-20): sed conf/env.sh `SELECTOR_RANK_TOPK=8` + daemon restart. KHÔNG rebuild jar
  (code cap đọc env SELECTOR_RANK_TOPK). Verify pid 31551 env=8, SHADOW_NO_PUSH=true (shadow off push giữ nguyên),
  moveSL 0.05/momentum 0.008 nguyên, 0 exception. Backup env.sh.bak_k8_20260820.
- run_worker.py restore K5 canonical (5 worker=5) sau grid.

## Bài học
- Local A/B ExitParamSweepProbe (−71% uncapped) SAI vì thiếu DCA grid → luôn so cùng config đầy đủ (WFO fanout).
- Oracle-local WFO ticker không đủ → dùng Kaggle bundle 14GB (full) mới chuẩn.
