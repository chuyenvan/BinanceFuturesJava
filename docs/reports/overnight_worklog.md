# OVERNIGHT WORKLOG - Ra soat & dung lai luong co provenance (2026-07-01 dem)

Mandate (Uni ngu): gac tinh chinh, tap trung AUDIT -> DOC -> VERSION -> danh dau du lieu -> don/archive tai lieu -> dung lai WFO co day du vet. Khong dung tru khi gap quyet dinh PnL/phuong phap khong the tu quyet.

## Tien do
- [x] PHASE A - Audit luong end-to-end (doc-only).
- [x] PHASE B - docs/PIPELINE_PROVENANCE.md (commit 435d98e).
- [x] PHASE C - Tich hop he tai lieu + sua framing leakage dung L0 (commit b605dd3). KHONG archive bua: docs von to chuc tot, chi bo sung + lien ket.
- [x] PHASE D - Dong dau provenance code: WfoDataset manifest (commit f37e325) + StrategyWfoTask env-config window (commit aeb2d30). Compile OK.
- [~] PHASE E - WFO leak-free: THIET KE + RUNBOOK + dua code train vao git (dong GAP #4). KHONG tu chay rebuild vi phai viet code inference moi (script sinh predict full-history khong co trong git) -> rui ro artifact "sach gia". De runbook san sang cho Uni greenlight.

## TOM TAT BUOI SANG (doc truoc)
DA XONG (core mandate - traceability):
1. PIPELINE_PROVENANCE.md - ban do luong + registry artifact + leakage + gaps + quy uoc version.
2. Sua framing leakage dung doctrine L0 (strategy-WFO loai 1 dung pred co dinh HOP LE cho cau hoi tham-so; dong gop moi: con so OOS tuyet doi bi thoi phong ~13/15 window).
3. WfoDataset dong dau provenance (git SHA + model + leakFreeFrom) - dataset tuong lai tu mang vet.
4. Code train model VAO GIT (ml/training/) - dong GAP #4 "khong luu code model".
5. docs/reports/LEAKFREE_WFO_RUNBOOK.md - cach dung strategy-WFO leak-free.

CAN UNI QUYET (mo khoa rebuild leak-free): xem RUNBOOK muc 5 (4 diem, deu co mac dinh an toan).
VIEC LON CON LAI (da-phien): viet code funding per-fold + gate reuse -> set v3wf -> dataset_wf -> chay WFO -> so verdict.

## Phat hien lon
LEAKAGE trong STRATEGY WFO (xac nhan bang chung): funding selector v2 train<=2024-12 nhung sinh prediction full-history 2021->2026 bang chinh model do -> ~13/15 window OOS truoc 2025-06 la in-sample (ro ri). Chi ~3 window cuoi sach. "88% OOS-duong" phan lon khong hop le.
Tai san sach ton tai nhung CHUA noi vao strategy-WFO: gate per-fold (wfo_models/fold_*, train_gate_fold.py). Funding KHONG co ban per-fold (gap chinh).

## Quyet dinh tu xu ly (ghi de Uni review)
- Viet doc ASCII thuan (ky tu box-drawing lam hong Write transport).
- KHONG tu chay rebuild leak-free WFO tu dau neu smoke khong sach 100% - de tranh tao artifact "sach gia" (dung tinh than do khong doan). Uu tien A-D chac chan + chuan bi san E.
