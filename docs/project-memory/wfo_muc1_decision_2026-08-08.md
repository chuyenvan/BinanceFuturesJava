# QUYẾT ĐỊNH 2026-08-08 (tối): QUAY VỀ MỨC 1 — đóng luồng WFO, hoãn canonical-1m

> Chốt sau khi rà `docs/reports/` (handoff 29/7–2/8) + đọc code `gen_funding_wf_predictions.py`.
> Liên quan: `wfo_data_status.md`, `wfo_rerun_2026-08-08_ce.md`, `wfo_kaggle_parallel_plan_2026-08-08.md`.

## 1. Vì sao quay lại

Loop WFO **02/8 đã đủ tốt** (verdict M): selector 4h, rank-K8, features có filter, lưới **15 phút**,
label ~42.6M, `WFO_HARNESS_FIX` frozen → %OOS-dương **88%**. Nguồn: `ENTRY_ALPHA_STATE_AND_PLAYBOOK.md §7`
+ `START_HERE_20260802.md`. Kết luận gốc: *"KHÔNG build model/data mới, sửa harness"*.

Đợt canonical-1m (04/8, task 251) phình data ×30 (15m→1m + filtered→unfiltered = 636M/~100GB) VÀ **tự
đẻ purge-leak** (PURGE_STEPS=288 = 4.8h thay vì 72h ở lưới 1m — leak này KHÔNG có ở loop 15m). Cái giá
(train chỉ vừa khít Kaggle 30GB, đắt) không đáng để "đóng luồng". → **Hoãn canonical-1m, đóng luồng ở Mức 1.**

## 2. Đã DỪNG (08/8 tối)

- Xoá trigger **launcher label shards** (`trig_0139...`) + trigger **verify/merge 07:00** (`trig_01G74...`).
- 3 shard Kaggle 2021/2022/2025 đang chạy: để tự xong, **bỏ output** (Kaggle CLI không kill sạch giữa chừng).
- Đợt re-export label 1-phút 636M **KHÔNG dùng cho Mức 1** — dừng hẳn.
- Kaggle đã dọn còn ~59GB/100 (turn trước).

## 3. Định nghĩa 3 mức (để không lẫn)

- **Mức 0** = loop 02/8, tất cả 15m. Verdict M. Dataset `wfo_ds_ret2wf_4h_ff` (99.5MB) CÒN NGUYÊN trên Kaggle.
- **Mức 1** = train 15m (rẻ) + predict/backtest 1 phút (khớp model live chạy theo phút). **KHÔNG cần label 1m.**
- **Mức 2** = tất cả 1m unfiltered (canonical hiện tại, 636M). HOÃN.

## 4. Phát hiện code (quan trọng — Mức 1 không free)

`ml/training/gen_funding_wf_predictions.py` dùng **một `SELECTOR_GRID_MIN` duy nhất** cho cả horizon-steps,
purge, lọc-lưới tool1 VÀ join label. `train_predict_fold` cắt cùng một `feat_df` cho cả train (`ts<cutoff`)
lẫn predict (`oos block`) — **cùng lưới**. `load_labels()` `raise AssertionError` nếu `step_min != GRID_MIN`.
⇒ **train-grid = predict-grid = label-grid bị khoá cứng.** Muốn "train 15m / predict 1m" THẬT phải **sửa code**.

## 5. Hai cách làm Mức 1

**Cách A (KHỎI sửa code — khuyến nghị đóng luồng trước):** selector train+predict **15m** → `build_ds`
**forward-fill pred 15m → lưới 1 phút** (`forwardFillToGrid` + `WFO_FUNDING_FILL_STALE_MS`, đã có sẵn).
Signal đổi mỗi 15m nhưng vào lệnh + SL chạy 1 phút. Không cần data 1-phút nào ngoài ticker (đã có).

**Cách B (sửa code — để dành):** tách `TRAIN_GRID=15` khỏi `PREDICT_GRID=1` trong gen script; train subset 15m
+ label 15m, predict feat 1m ở OOS. Cần tool1 1m (đã có) cho predict; **vẫn không cần label 1m**. Làm khi
Cách A cho thấy staleness 15m thật sự hại.

## 6. Dữ liệu Mức 1 cần

- **Label 15m** (~42M, nhỏ): các dataset label đã xoá đều là bản **1m-hỏng**, KHÔNG phải 15m → **re-export
  `LABEL_STEP_MIN=15`** (rẻ). Đây là export DUY NHẤT còn cần, thay cho đợt 636M đã dừng.
- **tool1 15m**: subset `ts%15m==0` từ `funding-tool1-1m-*` (đã có), hoặc bản gộp cũ `funding-tool1-features`
  (4.86GB, giữ lại lúc dọn — **[verify]** có phải 15m không).
- **`wfo_ds_ret2wf_4h_ff`** còn nguyên → re-run frozen loop lấy lại verdict M ngay, không chờ data mới.

## 7. Bước tiếp (Cách A) — CHỜ Uni xác nhận Cách A trước khi chạy

1. Re-run frozen loop trên `wfo_ds_ret2wf_4h_ff` → tái xác nhận verdict M (rank-K8, 4h, WFO_HARNESS_FIX).
2. Re-export label 15m + regenerate selector predict 15m (leak-free, `FIRST_CUTOFF=20230101`).
3. build_ds forward-fill → sim 1 phút. **N=30 confirm** (verdict M mới là N=1 shape) + bù mảng **2026 forward**
   (Kaggle geo-block Binance → dùng Oracle cho window đụng 2026).
4. Chỉ khi staleness 15m hại → Cách B.

## 8. Còn treo (không đổi, thuộc STAGE sau)

`ExportFundingLabel` exit 0 khi BLOCKED (latent); WFO jobstore bẩn + trỏ box 226 retire; Oracle repo không
git → `code_sha=unknown` làm `WfoDataset.export()` throw ở build_ds.
