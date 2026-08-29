# Fanout WFO khớp-live (K5, DCA-off) + kết quả arm — 2026-08-21

Mục tiêu (theo user): cập nhật backtest = config live (arm15) rồi fanout full-18w, rà env cho khớp live.

## RÀ ENV — phát hiện vênh quan trọng
Env live thật (đọc /proc/<pid>/environ bot 242): `SELECTOR_RANK_TOPK=5, SIM_MIN_MOMENTUM_15M=0.008, SIM_RATE_PROFIT_STOP_MARKET=0.05, SIM_TS_PROFIT_MULTIPLIER=3.0 (arm15), TS_PRED_GAP=1, SHADOW_NO_PUSH=false`. **KHÔNG có biến DCA nào** → live chạy **DCA tắt**.
- Backtest WFO canonical (run_worker.py) lại đặt **`DCA_GRID_ENABLED=true` + `DCA_TIER_MARGIN_ENABLED=true`** (legs -30/-50/-70%). → Toàn bộ số WFO lâu nay (18748…) là chiến lược CÓ DCA-grid, KHÁC live. Đã tắt DCA để khớp live.
- WFO không mô phỏng được pred-gap (jar worker cũ hơn tính năng) → fanout = "live trừ pred-gap".

## KẾT QUẢ (full-18w, K5, DCA-off, jar Aug9/jul16, cùng data/predwf_G015)
| Config | FULL_18w | 12w | quý dương | WFE med | maxDD |
|---|---:|---:|:--:|---:|---:|
| baseline cũ: arm26 + **DCA-on** | 18,748 | 13,842 | 16/18 | — | ~19% |
| arm26 + **DCA-off** (=live trừ arm/predgap) | **19,840** | 13,540 | 15/18 | 0.226 | 19.3% |
| "arm15" + DCA-off (đợt 1, thực chất arm26) | 19,811 | 13,529 | 15/18 | 0.226 | 19.3% |

## arm15 KHÔNG kiểm được bằng backtest — 3 cơ chế đều tắc
1. **(đợt1) pin qua range `WFO_TSMULT_LO=HI=3`**: no-op. Harness `WFO_N_SAMPLES=1` → HPO eval SEED=Configs default (5.2185); range chỉ tác dụng khi N>1. (Đính chính `arm_sweep_rootcause`: "degenerate range ép gene kể cả khi không search" SAI với N=1.)
2. **(B) swap oiseed hook-jar**: THẤT BẠI — hook-jar = jar live mới, đổi code đọc data → **lỗi đọc data trên worker Kaggle** (ARM26hook chỉ 7/18 window=9259 KHÔNG reproduce 19840; ARM15hook FAILED=1). Reproduce-check bắt được. Đã restore jar về jul16.
3. **(B') build jar WFO-tương thích + hook**: BỊ CHẶN — commit WFO-tương thích 8741f85 **không tự compile** (thiếu `config/PrivateConfig.java` gitignore + tham chiếu `legCount` là symbol thêm ở commit sau). HEAD build được thì lại WFO-incompatible (= oiseed). Xác định + dựng đúng commit worker-jar = fragile, nhiều giờ.
- **(A') N_SAMPLES>1**: cũng KHÔNG sạch — bật full HPO search (đổi MỌI gene, không cô lập arm) hoặc no-op nếu fitness degenerate.

→ **Không có đường rẻ nào cô lập arm trong harness hiện tại.** Chỉ hook tĩnh (cần jar tương thích data) mới làm được — và dựng jar đó là task dev riêng (gỡ secrets/deps + đúng commit).

## KẾT LUẬN CUỐI
1. **DCA-off ≥ DCA-on** (19,840 vs 18,748, maxDD tương đương): DCA-grid backtest không giúp, hơi hại. **Live tắt DCA = đúng.** Kết quả CHẮC (jar chuẩn). Lần đầu backtest khớp cơ chế DCA của live.
2. **arm15 chưa có bằng chứng backtest.** Prior mạnh: arm kém nhạy trên blended (bull che crash), WFO stage1 N=30 tự chọn ~arm24% (sát 26%) → arm15 nhiều khả năng ≈ arm26 trên tổng. Hạ arm 26→15% ở live = tinh chỉnh discretionary trong biên nhiễu.
3. **KHUYẾN NGHỊ: (C)** dừng đuổi số arm15 (giá trị thấp/công cao), dồn sức đòn bẩy data ủng hộ mạnh: **time-stop max-hold (không SL-giá) + lọc/size coin mới-list** (bằng chứng ở doc collapse_coin_dataanalysis).

## Trạng thái infra (đã dọn sạch, verify 2026-08-21 ~15:00 +07)
- worker jar java-run-lc = jul16 (hook removed), dataset ready. run_worker.py = canonical (K5, DCA-on, no pin). Không job java chạy. wfo_ds tạm đã xoá. git worktree E:\wfobuild đã remove, repo live nguyên (branch module @842c327).
- Reports: REPORT_ARM26K5DCAoff.md (=19840, VALID). Các REPORT arm15/hook = no-op/broken (bỏ qua).
- Nếu tương lai muốn số arm15: dev task = thêm hook `SIM_TS_PROFIT_MULTIPLIER` vào codebase worker đúng commit (fix PrivateConfig + legCount + deps) → rebuild java-run-lc → fanout ARM26rep(reproduce 19840)+ARM15(env 3.0) → restore.
