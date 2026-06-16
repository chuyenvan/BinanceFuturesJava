---
id: 039
status: TODO
depends_on: [037, 038, 024]
touches_live_process: false
writes_242_data: false
resource: kaggle
checkpoint: true
max_retry: 2
report: docs/reports/039.md
require_review: true
---

# TASK-039: Funding F5 — ghép feature + train SELECTOR + beat rule (OOS)

- **status:** TODO. `depends_on: [037, 038]` (feature) + `[024]` (label triple-barrier 47.86M dòng đã xong).
- **Nền:** ADR-0011 §5.2/§5.5 + §2.2 (khung đo).

## Việc
- **Ghép:** feature (037 + 038) + label triple-barrier (024) → dataset train selector. Align mốc, **de-overlap per-symbol** (horizon), purge.
- **Train** (XGBoost — như `train_fundingfee_xgboost_optuna`): split theo thời gian, **KHÔNG shuffle, KHÔNG scale** (live không có scaler), purge horizon. **KHOÁ thứ tự lớp** — ADR-0011 §6: `symbolPred = pred[0] = P(fail)`, rank ưu tiên P(fail) THẤP; đổi thứ tự output = sai dấu âm thầm.
- **Đo:** conditional hit-rate / LIFT vs base-rate + z-test (chính); rank-IC/t-stat/block-bootstrap (phụ). Gate: LIFT≥1.20, N≥100, z≥2, |t-IC|≥2. Holdout 12 tháng.
- **ACCEPTANCE KINH TẾ (§5.5):** selector phải **BEAT rule baseline** (vd "funding-percentile cao + volume-z cao + OI tăng") trên OOS → không beat thì dùng rule, bỏ ML (như gate).

## ❗ Chốt trước khi train (open ADR-0011 §4.1)
- **Target `+6%` hay `+40%`** (selector phục vụ chiến lược DCA nào)? — user CHỐT khi vào 039 (chưa quyết).

## Validate (require_review)
- Pre-register gate (LIFT/z/N/IC) + beat-rule TRƯỚC khi xem kết quả. OOS holdout 12T. Không look-ahead (purge + expanding). Khoá thứ tự lớp.

## (Code / Kết quả điền)
