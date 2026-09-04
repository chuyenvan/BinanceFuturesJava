# C2B_PROVENANCE — BO BA provenance cua cau hinh tot nhat C2b

Sinh luc: 2026-09-04 (Oracle). Tong hop provenance day du cua C2b. C2b chay tren
`WFO_FUNDING_PRED_DIR=/home/ubuntu/predwf_map_s1a2` (`profiles/c2b.properties:23`,
`profiles/c2b_min.properties:23`). Bins do la ket qua cua **3 thanh phan** duoi.

## BO BA

### (a) Thu hang S1 (selector) — TAI LAP byte-identical + backup
- Xem `docs/S1_PROVENANCE.md`. Chay 2 lan doc lap cho **bins byte-identical 10/10 fold**, khop
  deploy `predwf_map_s1a2/` va backup Kaggle `chuyendinh/predwf-map-s1a2-bins` tung byte.
- Ket luan: **tai lap duoc, verify duoc.**

### (b) Hop nhat build_map — DETERMINISTIC, trong git
- `research/pipeline/build_map.py` (trong git, branch module). Ham thuan tuy: giu NGUYEN multiset
  P(win) per-tick cua G015x26, chi hoan gia tri theo thu hang S1 (`rank method=first`). Khong random.
- Ket luan: **tai lap duoc tu source, deterministic.**

### (c) Phan phoi gate G015x26 — DONG BANG, KHONG tai lap duoc
- Xem `docs/G015X26_PROVENANCE.md`. Input cua build_map (dong 28):
  `/home/ubuntu/claudedata/predwf_G015x26/predict_wf_*.bin` (16 file, file dau `199ad42e...`).
- Train tren export Tool1 2021 **da mat** => **KHONG tai lap duoc** (khac `predwf_G015_v2`, rho
  0.18991, `aed0732c...`, la ban tai lap dung cho phan tich, KHONG deploy).
- Da **DONG BANG + backup**: manifest 16 file co-located; backup Kaggle PRIVATE
  `chuyendinh/predwf-g015x26-gate` (v1), verify tai-lai-so-hash **PASS**.

## KET LUAN

C2b **bao ton duoc va verify duoc TOAN BO** (3/3 thanh phan co manifest + backup off-disk da
verify). NHUNG **KHONG dung lai duoc 100% tu source** vi thanh phan (c): phan phoi gate G015x26 la
artifact dong bang tu mot seed/export da mat, chi giu duoc chu khong sinh lai duoc. (a) va (b) tai
lap duoc; (c) chi bao ton duoc. Neu mat ca deploy `predwf_G015x26/` lan backup Kaggle o (c) thi mat
gate cua C2b vinh vien.
