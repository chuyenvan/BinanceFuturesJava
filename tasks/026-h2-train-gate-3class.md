---
id: 026
status: CANCELLED
depends_on: [025]
touches_live_process: false
writes_242_data: false
resource: kaggle
checkpoint: true
max_retry: 2
report: docs/reports/026.md
require_review: true
---

# TASK-026: H2 — Train GATE 3-class (harness riêng, Kaggle) (§4)

- **status:** BLOCKED — sau khi 025 cho ra `gate_dataset_vN` + fingerprint.
- **owner:** _(điền khi claim)_ · **updated:** _(điền)_
- **Spec:** `docs/H1_GATE_SPEC.md` §4 + §1 C2 (threshold X/Y). 2-harness: đây H2-TRAIN, tách hẳn H1-DATA.

## Việc (theo §4)
1. **Đọc dataset versioned + VERIFY fingerprint** trước train (khớp hash mới chạy). Chạy **Kaggle** (RUNBOOK).
2. **CV:** purged K-fold + embargo = H (chống leak overlap label) + sample-weight uniqueness.
3. **3-class hoá:** áp threshold X(H)/Y(H) lên return thô (gate_return) → **quét grid** X(24h)∈{−10,−12,−15,−20%}, Y=0.6|X|, H∈{4,12,24h}. KHÔNG re-export.
4. **Imbalance:** lớp GIẢM ~0.92% → class-weight mạnh/focal. Metric = **precision/recall lớp GIẢM + lift**, KHÔNG accuracy tổng.
5. **Rule baseline:** "breadth thấp AND funding cao → block". Model phải **BEAT rule** mới giữ.
6. **Importance** MDA/SHAP → tỉa feature trùng (đã cờ §3.2a).
7. **OOS đông lạnh** 12T cuối — chạm 1 lần cuối, KHÔNG tune trên đó.

## Output
- Model + report: precision/recall lớp giảm, lift, beat-rule, importance, OOS. Beat-rule + OOS đạt → mới đưa gate vào serve.

## An toàn
- Chỉ train (Kaggle, đọc dataset). KHÔNG đụng live/serve cho tới khi report đạt + user duyệt.

## Acceptance
- [ ] Verify fingerprint dataset trước train.
- [ ] purged K-fold + embargo + sample-weight; grid threshold.
- [ ] Metric lớp-giảm + lift; beat rule baseline; importance; OOS 1 lần.
- [ ] Report đủ để quyết đưa gate vào serve hay không.

## (Code điền)
- **CV + threshold grid kết quả:** …
- **Beat-rule + lift lớp giảm:** …
- **Importance + OOS:** …
