# docs/ — quy tac dat ten & so do folder

Tai lieu trong `docs/` duoc chia theo **folder con** (don 2026-09-24). **Khong doi ten file** — chi doi
folder, va moi tham chieu `docs/<ten>.md` trong repo da duoc cap nhat theo duong dan moi.

## 1. Quy tac dat (AP DUNG THEO THU TU, cai dau tien khop thang)

| # | Folder | Khop tien to / chua chuoi | Vi du |
|---|---|---|---|
| 0 | *(o lai `docs/` root)* | `AGENTS.md`, `index.md` | router/banner — script `run_106*.sh` doc truc tiep, khong di chuyen |
| 1 | `prereg/` | `PREREG_`, `preregistration_` | `PREREG_FEAT_ABLATION.md` |
| 2 | `result/` | chua `RESULT` | `RESULT_DEV2021.md`, `C4_RESULT.md`, `K12_RESULT.md` |
| 3 | `diag/` | `DIAG_` | `DIAG_RVOL15M.md` |
| 4 | `audit/` | chua `AUDIT` | `AUDIT_APPLIED.md`, `CI_REAUDIT.md` |
| 5 | `decisions/` | `DECISION_` | ADR cu (`0001-...`) dung chung folder nay |
| 6 | `design/` | `DESIGN_`, `C2B_`, `SPEC` | `DESIGN_TRADE_FLOW.md`, `C2B_SPEC.md` |
| 7 | `analysis/` | `ANALYSIS_`, `RECON_`, `PHASE1_`, `BRIEF_`, `SURVEY_`, `EVAL_`, `VALIDATE_`, `LEAK_`, `DETAIL_`, `RESEARCH_`, `GS_`, `SELECTOR_`, `SHADOW_`, `WFO_` | `EVAL_SELECTOR_FEATURES.md` |
| 8 | `runbooks/` | `AGENT_RUNBOOK`, `RISK_APPETITE`, `KAGGLE_`, chua `RUNBOOK` | `AGENT_RUNBOOK.md` |
| 9 | `data/` | `DATA_` | `DATA_GOVERNANCE_PROTOCOL.md` |
| 10 | `plan/` | `PLAN_`, `ROADMAP`, `HOLDOUT_`, `H1_HOLDOUT`, `PROPOSAL_`, `QUEUE`, `HANDOFF`, `HOLD_TO_DIE`, `CANDIDATE_`, `_MA_` | `ROADMAP.md` |
| 11 | `ops/` | `CONFIG_`, `INVENTORY_`, `BENCH_`, `SYSTEM_`, `RUNS_`, `PAIRED_`, `TRADING_`, `DEV_COLLAPSE`, `COLLECTOR_`, `OI_`, `EVENT_` | `SYSTEM_OVERVIEW.md` |
| 12 | `experiment/` | `^<MA HOA><SO>_` (vong thu / stage) | `X1_EXTEND.md`, `G015_RECIPE.md`, `L3_DEPLOY_PREP.md`, `F2_RESULT.md` *(da vao `result/` theo luat 2)* |
| 13 | `notes/` | con lai (khong khop luat nao) | `Untitled-1.md`, `power_wall.md` |
| — | `archive/` | **giu nguyen, khong di chuyen, khong sua** | `archive/_cleanup_20260829/...` |

Folder co tu truoc, **khong nam trong luat tren**, giu nguyen: `architecture/` (roadmap html),
`insights/` (1 file), `rules/` (7 file quy tac code/task), `db/` *(khong con)*.

## 2. So file moi folder (sau khi don)

| folder | so file .md | ghi chu |
|---|---|---|
| `prereg/` | 144 | pre-reg, chot TRUOC khi do |
| `result/` | 125 | ket qua do |
| `experiment/` | 30 | vong thu theo ma-so (E/F/G/X/L/W/T/H/S/K…) |
| `analysis/` | 23 | phan tich / do luong / eval / survey |
| `diag/` | 17 | chan doan |
| `decisions/` | 17 | 14 ADR cu + 3 `DECISION_*` |
| `audit/` | 14 | audit |
| `ops/` | 13 | config/inventory/system |
| `plan/` | 11 | ke hoach/roadmap/handoff |
| `runbooks/` | 10 | 4 runbook cu + 6 moi |
| `design/` | 6 | design + spec |
| `data/` | 3 | chuan du lieu |
| `notes/` | 2 (+1 html) | le |
| **root** | 3 | `AGENTS.md`, `index.md`, `PREP_STAGE2_TRAIN.md` (file cua job khac, xem §4) |
| `archive/` | 300 | giu nguyen |

## 3. Tham chieu duong dan

Da quet toan repo (`*.md`, `*.py`, `*.sh`, `*.java`, `*.properties`, `*.json`, `*.txt`, `*.html`, `*.conf`):
**2.494 tham chieu dang `docs/<ten>.md`** + **58 link markdown tuong doi** da duoc sua sang duong dan moi.
`docs/archive/**` **khong** bi sua (file lich su).

⚠️ Con **127 duong dan VO** — **tat ca la loi CO SAN** (khong do lan don nay):
- ~88 cai tro `docs/reports/*`, `docs/db/*`, `docs/insights/*`, `docs/reference/*`, `docs/project-memory/*`
  — cac folder nay da bi don vao `docs/archive/_cleanup_20260829/` tu 2026-08-29 nhung tham chieu chua sua.
- ~39 cai tro file **khong con ton tai o bat ky dau** (vd `docs/reports/017`, `docs/CORE`).
- 3 cai la chuoi bi cat trong van xuoi (`docs/archive/...` , `docs/TASK_D...design`).
Khong tu dong sua vi phai chon giua "tro vao archive" (doi y nghia lich su) va "xoa tham chieu" (xoa thong tin).

## 4. File cua job khac (chua di chuyen)

- `docs/plan/PREP_STAGE2_TRAIN.md` — do job Stage 2 prep tao **giua luc dang don** (2026-09-24) => **de nguyen o
  root**, khong `git mv` (tranh de len job dang ghi). Khi job do xong: chuyen vao `docs/plan/` theo luat 10.
- `Untitled-1.md` — ten rac, giu nguyen ten (luat: khong doi ten file), xem lai sau.

## 5. Feature set / version

Danh sach feature train duoc version hoa o **`research/pipeline/featuresets/`** (khong phai `docs/`):
`fs_v0_45.json` (dang chay) · `fs_v1_44.json` · `fs_v2_21.json` + README quy tac version.
Code train snapshot o `research/pipeline/train/`.
