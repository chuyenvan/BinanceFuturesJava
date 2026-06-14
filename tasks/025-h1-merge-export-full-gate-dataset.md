# TASK-025: H1 — Ghép feature + label → export FULL dataset gate + validate chung (§3)

- **status:** BLOCKED — sau khi 015 (A) + 017 (B-now) + 018 (B-crowd) PASS validate RIÊNG. Là bước cuối H1-DATA.
- **owner:** _(điền khi claim)_ · **updated:** _(điền)_
- **Spec:** `docs/H1_GATE_SPEC.md` §3 (đầy đủ).

## Input
`gate_return.csv` (012, label) + feature A (015) + B-now (017) + B-crowd (018). Key `t` (15m).

## Việc (theo §3)
1. **Ghép** trên `t` (đủ label + mọi feature). Báo #dòng trước/sau join (warmup MA200 ~200 ngày, OI từ ~2021-12 cắt bao nhiêu).
2. **Validate CHUNG** toàn bảng: (a) corr/dedup >0.95 → **cờ liệt kê, KHÔNG tự drop**; (b) leakage (feature ≤t, label t+H tách rõ; proxy dịch ±1 bước); (c) determinism hash 2 lần; (d) align cùng tập t; (e) NaN/Inf + warmup nhất quán (không 0-giả); (f) drift bậc-thang theo năm; (g) statistical screen degenerate.
3. **Export FULL:** `gate_dataset_vN_YYYYMMDD` (parquet+csv) + **manifest+fingerprint** (hash, #dòng/cột, range, feature list+task nguồn, commit hash, CONFIG_VERSION, lifecycle/DIED dùng). 2 tầng validate (input `validate_data` 011 + output recompute+cross-audit). Ghi OOS cutoff khuyến nghị vào manifest (KHÔNG split).

## An toàn / tài nguyên
- Đọc feature/label (outputs + 226), ghi `outputs/`. Chạy 226. SLF4J.

## Acceptance
- [ ] Dataset versioned + manifest+fingerprint đầy đủ.
- [ ] Validate chung (a–g) PASS, kèm corr-flag drop-list để Desktop/user quyết.
- [ ] 2 tầng validate (input+output) + OOS cutoff ghi manifest.

## (Code điền)
- **#dòng trước/sau join + nguyên nhân cắt:** …
- **Validate chung (a–g) + drop-list:** …
- **Dataset version + fingerprint:** …
