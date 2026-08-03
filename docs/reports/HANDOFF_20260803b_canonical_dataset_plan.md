# HANDOFF 2026-08-03 (b) — PLAN dataset CANONICAL leak-free (lối A) + trạng thái dọn dẹp

> Uni chốt: dừng vá lẻ leak, build 1 dataset CANONICAL leak-free (lối A = bỏ window sớm), đặt tên chuẩn,
> deprecate/xóa tất cả bản cũ. Làm ở phiên TỈNH TÁO (data-critical, có dep Kaggle). File này = plan + gate.

## Đã dọn phiên này (2026-08-03)
- **Xóa cứng** (giải phóng ~5GB, 91%→88%): quarantine severe-leaked (`wfo_ds_ret2_4h`, `wfo_dataset_v4`,
  `wfo_dataset_leaked_restricted`) + 6 old contaminated (`wfo_dataset`, `_v3`, `_v5`, `_v6`, `_clean`, `_wf_v3`).
- **Giữ bằng chứng**: `/home/ubuntu/claudedata/_LEAKED_QUARANTINE/wf_pred_ret2_predict_wf_20260101.bin.LEAKED`
  (94.7M) — dùng cho regression-test guard.
- **Guard code** (commit bac70fa): `WfoDataset.buildFundingFromWfFiles` throw khi predict_wf overlap ts-range.
- **Doc** `STRATEGY_CONSOLIDATED.md`: banner deprecate nguồn leaked.
- CHƯA đụng: `wfo_ds_maxfav3_*`, `wfo_ds_ret2wf_4h(_ff)` (SẠCH, đang dùng), `wfo_dataset_wf` (554M, tự-khai
  leakfree-2022+, chưa verify), `oiz/ev2/maxdep` (generator khác, chưa audit), Kaggle `chuyendinh/wf-pred-ret2`
  (còn leak, Uni gỡ tay).

## 2 lỗ hổng gốc đã xác định (phải sửa TRƯỚC khi re-gen)
1. **`gen_funding_wf_predictions.py` fold-0 `block_lo=ts_min`**: file predict_wf fold ĐẦU (vd 20220101) phủ cả
   2021 (IS-region, model đã thấy). Có ở MỌI dir kể cả `wf_pred_ret2wf/`. MILD (không future-leak; OOS sạch;
   frozen n=1 không dính) nhưng cần khử cho canonical.
2. **buildFundingFromWfFiles không dedup** → đã guard (throw on overlap).

## PLAN A — canonical leak-free (bỏ window sớm)
1. **Sửa gen script**: cutoff đầu tiên đặt muộn (vd OOS đầu = 2023-01-01 → model có ≥2 năm train sạch trước
   MỌI window). Fold-0 không còn `block_lo=ts_min` (mỗi file = đúng 1 OOS block ~90 ngày, range disjoint).
2. **Re-gen predict_wf** (selector) trên Kaggle (OI 138M >23GB RAM) → dir mới `wf_pred_LF_<date>/`. Gate đã
   leak-free (train_gate_fold.py per-fold) — re-gen lại nếu đổi cutoff cho khớp fold.
3. **Re-export** `ExportWfoDataset` với `WFO_FUNDING_PRED_DIR=wf_pred_LF_<date>`, `WFO_SET_PRED=ai_pred_market_gate_wfo`,
   `WFO_SEL_HORIZON_IDX=0` (4h). Guard sẽ tự chặn nếu còn overlap.
4. **Manifest TRUNG THỰC + tự-validate** (sửa ExportWfoDataset stamp nguồn THẬT, không env-default): bắt buộc
   `leakFreeFrom=<ngày>`, `VALIDATED_BY`, `horizonIdx`, `codeGitSha`, md5 từng predict_wf nguồn, `maxFoldSpanDays<=100`.
5. **Validate độc lập** (agent/script, đọc bin): (a) mọi fold disjoint + span ~90 ngày; (b) OOS đầu ≥ cutoff train;
   (c) market/pred/funding ts-align (%60000==0, snapshot selector đổi tại %900000==0); (d) gate per-fold WF;
   (e) NaN/coverage; (f) không ts nào xuất hiện ở >1 fold. Ký PASS vào manifest.
6. **Đặt tên chuẩn + deprecate**: `wfo_ds_LF_<YYYYMMDD>_h4h_v1`. Loader từ chối dataset có `leakFreeFrom=unknown`.
   Sau khi bản mới PASS → xóa/deprecate `ret2wf_4h(_ff)`, `maxfav3_*`, `wfo_dataset_wf`.

## Quy ước tên (chống nhầm về sau)
`wfo_ds_LF_<date>_h<horizon>_<selector>_v<n>` — LF=leak-free đã validate. Manifest thiếu `leakFreeFrom`/`VALIDATED_BY`
= tool load REJECT. Không bao giờ đặt tên "clean" cho bản chưa sửa funding.

## Nợ kỹ thuật còn treo (từ phiên trước, sau khi có canonical thì đo lại trên nền sạch)
- Grid-align `SIM_SELECTOR_MAX_STALE_MIN`: sweep N {0,2,3,5} + instrument entry-offset (proof entries ở mốc 15m).
- DCA bypass-gate: flag coi DCA_LEVEL1 như BIG_DOWN → tách edge DCA khỏi nhiễu AI-gate (kết luận "DCA no edge" bị nhiễu).
- Trailing giveback 0.3 + rank-K: đo lại trên canonical (kết quả cũ trên ret2wf_ff — OOS sạch nên vẫn tham khảo được).
