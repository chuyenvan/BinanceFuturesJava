# RÀ SOÁT handoff 30/7–3/8 + trạng thái harness (đến 2026-08-13)

Nguồn: `docs/reports/HANDOFF_*` trong repo (Windows). Đã đọc: 29/7 (entry_alpha_harness), 30/7 (exit_min_ratchet), 1/8 (dca_grid_exit), 2/8 (leg1_edge_dca_reframe), 2/8b (dcaoff_verdict_guard), 3/8 (giveback03_frozen), 3/8b (canonical_dataset_plan). Kiểm chứng trạng thái hiện tại: `git status`, `Configs.java`, dataset Oracle.

## A. Thiếu gì trong chuỗi handoff
1. **Không có HANDOFF 31/7.** Nhảy thẳng 30/7 → 1/8. Có report số liệu `EXIT_SWEEP_20260731_rate_ratchet.md` được 1/8 tham chiếu, nhưng KHÔNG có file prefix HANDOFF cho ngày 31/7. Phiên 31/7 gộp vào 30/7-tối hay thiếu bản nối-mạch — nên xác nhận.
2. **Chuỗi handoff DỪNG ở 3/8b.** Không có handoff 4–12/8. Toàn bộ việc từ ~8/8 (nghiên cứu grid×ngưỡng selector 1m/3m/5m/15m — chính là việc đang chạy) **không có HANDOFF**, chỉ nằm ở project docs `claude/wfo_*`. Nên viết 1 handoff nối mạch khi chốt (nếu vẫn theo quy ước repo).

## B. Harness — kết luận gốc "harness tự bóp chính nó"
Từ 29/7 (VERDICT M): bottleneck KHÔNG phải gate/selector/regime → là **WFO/HPO harness loại bỏ chính window đang lãi** qua constraint `TOO_MUCH_CAPITAL_LOCK` + `TOO_FEW_TRADES`; cộng **fitness mismatch** (HPO chọn theo Calmar×factor nhưng chấm theo raw-PnL-WFE) và **HPO argmax overfit w15**.

## C. ĐÃ GỠ (và phần lớn đang ACTIVE)
1. **Entry no-trades → rank-K8** (`SELECTOR_RANK_TOPK=8` + `SIM_MIN_MOMENTUM_15M=0.008`): mọi window có lệnh, PnL dàn đều, hết dồn w15. [2/8]
2. **Harness P0+P1** (`WFO_HARNESS_FIX=true`, default OFF byte-identical, test 13/13; commit sau `dab4d48`):
   - P0 (HPOFitnessCalculatorV4): ramp `TOO_FEW` xuống dưới mọi reject → hết ordering inversion (chính là fitness mismatch).
   - P1 (StrategyWfoTask.aggregate): OOS coi `CAPITAL_LOCK/TOO_FEW/UNSTABLE` là **report-only**; chỉ `ZERO_TRADES/BURN_ACCOUNT/OVER_MAXDD` disqualify.
   - Hiệu quả: posRatio strict 6% → **lenient 88% (14/16)**.
   - **→ ĐANG ACTIVE trong MỌI run selector của tôi** (log `aggregate[HARNESS_FIX=true]`).
3. **Bỏ WFE khỏi verdict frozen** (Uni chốt): verdict = **%OOS-dương ≥70% + maxDD-OOS ≤50%**. WFE = OOS/IS của một *search* → vô nghĩa với config frozen. [2/8b]
4. **Wipe bug** (jobstore 226 dùng chung namespace `wfo_jobs`, job-id không tách tag → reset đè mất verdict, chính là vụ mất confirm_n30): vá **autosnap** trước reset (commit `1a25a63`). [2/8b,3/8]
5. **maePeak/MFE metric = 0** (chưa copy peak sang done-order): fix (commit `fe00232`). [3/8]
6. **TS_GIVEBACK_RATIO env-fallback** (trước chỉ đọc properties, không sweep qua env): fix (commit `4195c03`). [3/8]
7. **Leak guard**: `buildFundingFromWfFiles` throw khi predict_wf overlap ts-range (commit `bac70fa`). [3/8b]
8. **Code đã COMMIT hết** — `git status` hiện chỉ còn 3 file untracked (backup `.bak_*` + 1 json rác). Nợ "chưa commit" của các phiên 29/30/1-8 đã sạch.

## D. CÒN PHẢI GỠ (đến hôm nay)
1. **Genome chưa freeze thật** — cờ Java `WFO_FREEZE_GENOME` **CHƯA có trong Configs.java** (đã verify). Hệ quả: 14/16 gene còn range mở → N>1 = search = overfit (bằng chứng: frozen 88% > loose N=30 69%). Buộc phải chạy frozen n=1; muốn đo WFE-frozen thật thì cần cờ này + rebuild jar. HOÃN.
2. **Namespace tách-theo-tag** — `WFO_STATE_SET` per-tag **CHƯA có**. Hiện chỉ có autosnap (workaround) + luật "jobstore serial, không 2 fanout song song". Cần rebuild jar mới xử đúng gốc. HOÃN.
3. **Verdict tool tự in PASS cho frozen** — `WFO_VERDICT_NO_WFE` **CHƯA có**. Đang đọc tay 2 tiêu chí → dễ hiểu nhầm khi thấy "FAIL" do WFE (đúng như log hiện tại của tôi in "WFE median tren 9/16").
4. **Canonical leak-free dataset (Plan A, 3/8b) CHƯA build** — không có `wfo_ds_LF_*` lẫn `wf_pred_LF_*` trên Oracle. 2 leak gốc: (a) `gen_funding fold-0 block_lo=ts_min` (fold đầu phủ IS-region 2021) — MILD, **đã né bằng `FIRST_CUTOFF=20230101`** trong pipeline selector hiện tại nhưng chưa có bản canonical validate + manifest tự-kiểm; (b) buildFunding dedup — đã guard. Việc: sửa gen cutoff muộn, re-gen predict_wf, re-export, manifest `leakFreeFrom/VALIDATED_BY`, đặt tên `wfo_ds_LF_<date>_h4h_v1`.
5. **STEP3 rank-K sweep** (rk05/rk08/rk12) mới chạy **w0/w1** (log trên Oracle) → **chưa full-16, chưa kết luận**.
6. **N=30 confirm trên harness đã sửa** — thực tế đã bị **thay bằng "frozen n=1 + 2 tiêu chí"** (vì N>1 frozen = overfit). Verdict M gốc đòi N=30 non-w15. Cần Uni xác nhận đây là quyết định cuối, kẻo lẫn tiêu chí giữa 2 nhánh.
7. **Nợ đo lường/thiết kế còn treo** (không chặn nhưng chưa đóng): g008↔label lệch pha ~4' (15m label vs feature); `SIM_SELECTOR_MAX_STALE_MIN` sweep + proof entry ở mốc 15m; time-stop 48h ✗ recovery sâu 100–267 ngày; `%hold>7d` ~5–6% vs constraint 2%; **audit label-leak theo timestamp trong pipeline Python `pred.bin` — chưa từng làm**; DCA-cũ market-gated `shouldDca` (biến thể duy nhất chưa test) để tách edge DCA khỏi nhiễu AI-gate.

## E. Liên hệ việc ĐANG chạy (quan trọng — có dính không?)
- Nghiên cứu grid×ngưỡng selector (1m/3m/5m/15m × 0.008/0.015/0.03/rateMin) của tôi chạy **trên harness ĐÃ SỬA** (HARNESS_FIX=true active), selector train `FIRST_CUTOFF=20230101` (né fold-0 leak), và tôi **chỉ dùng win4–13 (OOS 2023+)**, verdict tự tính raw PnL/window + Sharpe/t (**không dùng WFE**) → đúng tinh thần các fix ở C. ⇒ Số của tôi **không dính** các bug harness đã fix, OOS-clean.
- Cảnh báo còn lại chỉ là: (i) chưa chạy trên **canonical dataset validate** (mức leak MILD đã né, chưa chứng thực bằng manifest); (ii) nhánh selector-study KHÁC nhánh strategy_window exit/DCA của handoff — chung harness, các mục D1–D3 là hạ-tầng/verdict, không làm sai PnL win4–13.

## F. Đề xuất ưu tiên nếu muốn "gỡ cho sạch"
1. (rẻ, giá trị cao) Kết luận **STEP3 rank-K full-16** — đang dở, gần xong.
2. (trung bình) Build **canonical LF dataset** theo Plan A rồi đo lại các verdict best trên nền sạch — đây là thứ khiến mọi số "chính thức" đáng tin.
3. (rẻ) Thêm cờ `WFO_VERDICT_NO_WFE` để hết đọc tay/nhầm "FAIL".
4. (đắt, chỉ khi cần WFE-frozen thật) `WFO_FREEZE_GENOME` + `WFO_STATE_SET` per-tag — cần rebuild fat-jar.
5. Chốt dứt điểm: verdict tiêu chuẩn cuối cùng là **frozen n=1 + (%OOS≥70, maxDD≤50)** hay vẫn giữ **N=30**? (D6)
