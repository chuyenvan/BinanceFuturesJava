# OVERNIGHT WORKLOG - Ra soat & dung lai luong co provenance (2026-07-01 dem)

Mandate (Uni ngu): gac tinh chinh, tap trung AUDIT -> DOC -> VERSION -> danh dau du lieu -> don/archive tai lieu -> dung lai WFO co day du vet. Khong dung tru khi gap quyet dinh PnL/phuong phap khong the tu quyet.

## Tien do
- [x] PHASE A - Audit luong (doc-only): trace end-to-end. Ket qua trong PIPELINE_PROVENANCE.md.
- [x] PHASE B - Tai lieu provenance: docs/PIPELINE_PROVENANCE.md (ban do luong that + registry artifact + leakage + gaps + quy uoc version + ke hoach leak-free).
- [ ] PHASE C - Don/archive tai lieu: ra docs, archive stale/dupe/sai, sua index.
- [ ] PHASE D - Dong dau provenance (code): mo rong manifest WfoDataset (git SHA + model-provenance).
- [ ] PHASE E - WFO leak-free: thiet ke (xong, trong provenance muc 7) + (neu smoke sach) chay.

## Phat hien lon
LEAKAGE trong STRATEGY WFO (xac nhan bang chung): funding selector v2 train<=2024-12 nhung sinh prediction full-history 2021->2026 bang chinh model do -> ~13/15 window OOS truoc 2025-06 la in-sample (ro ri). Chi ~3 window cuoi sach. "88% OOS-duong" phan lon khong hop le.
Tai san sach ton tai nhung CHUA noi vao strategy-WFO: gate per-fold (wfo_models/fold_*, train_gate_fold.py). Funding KHONG co ban per-fold (gap chinh).

## Quyet dinh tu xu ly (ghi de Uni review)
- Viet doc ASCII thuan (ky tu box-drawing lam hong Write transport).
- KHONG tu chay rebuild leak-free WFO tu dau neu smoke khong sach 100% - de tranh tao artifact "sach gia" (dung tinh than do khong doan). Uu tien A-D chac chan + chuan bi san E.
