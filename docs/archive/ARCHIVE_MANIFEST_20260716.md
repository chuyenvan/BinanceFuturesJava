# ARCHIVE MANIFEST — 2026-07-16 (dọn docs/reports)

> Bằng chứng cho master/Uni review. **CHỈ MOVE, KHÔNG XOÁ, KHÔNG commit** (reversible qua git).
> Nguyên tắc: chỉ move file RÕ RÀNG transient/superseded và KHÔNG được tham chiếu bởi doc canonical
> (index/CORE/SESSION_START/decisions/insights/reference/runbooks) hay bởi report còn giữ.
> Không chắc → GIỮ NGUYÊN. Đích: `docs/archive/reports/`.

## Tổng quan
- Trước: `docs/reports/` = 75 file. Sau: 57 file. **Đã move: 18 file** → `docs/archive/reports/`.
- Đã kiểm reference bằng grep tên file trong toàn bộ `docs/**/*.md` trước khi move.
- KHÔNG đụng: golden/, rules/, decisions/, reference/, runbooks/, insights/, CORE.md, SESSION_START.md, index.md.

## Danh sách file đã move (from → to + lý do)

| # | File | From | To | Lý do |
|---|------|------|----|-------|
| 1 | OVERNIGHT_BRIEF_20260711.md | docs/reports/ | docs/archive/reports/ | Brief overnight 07-11, đã bị NEXT_SESSION_TODO_20260714 + SESSION_START thay thế. Không ref canonical. |
| 2 | OVERNIGHT_BRIEF_20260712.md | docs/reports/ | docs/archive/reports/ | Brief overnight 07-12; kết luận (ret2>maxfav3) đã bị handoff 07-14 đảo (maxfav3 nhỉnh hơn). Không ref canonical. |
| 3 | ORCHESTRATION_20260712.md | docs/reports/ | docs/archive/reports/ | Log điều phối campaign 07-12, phiên cũ. Không ref canonical. |
| 4 | 025.md | docs/reports/ | docs/archive/reports/ | Log task-025 (ghép dataset gate), tháng 6, pre-campaign. Kết luận đã hấp thụ vào FINDINGS. Không ref canonical. |
| 5 | 026.md | docs/reports/ | docs/archive/reports/ | Log task cũ (tháng 6). Không ref canonical/kept. |
| 6 | 038.md | docs/reports/ | docs/archive/reports/ | Log task cũ (tháng 6). Không ref canonical/kept. |
| 7 | 039a.md | docs/reports/ | docs/archive/reports/ | Log task-039a (funding selector retrain, 06-21). 4 file 039* chỉ tham chiếu lẫn nhau, move cùng cụm. |
| 8 | 039b.md | docs/reports/ | docs/archive/reports/ | Log task-039b, cụm 039. Không ref canonical/kept. |
| 9 | 039c.md | docs/reports/ | docs/archive/reports/ | Log task-039c, cụm 039. Không ref canonical/kept. |
| 10 | 039d.md | docs/reports/ | docs/archive/reports/ | Log task-039d, cụm 039. Không ref canonical/kept. |
| 11 | 042.md | docs/reports/ | docs/archive/reports/ | Log task cũ (tháng 6). Không ref canonical/kept. |
| 12 | 043.md | docs/reports/ | docs/archive/reports/ | Log task cũ (tháng 6). Không ref canonical/kept. |
| 13 | 104.md | docs/reports/ | docs/archive/reports/ | Report-104 A/B gate MOM15 (chạy 06-18). Không ref canonical/kept. |
| 14 | 106.md | docs/reports/ | docs/archive/reports/ | Log task cũ (tháng 6). Không ref canonical/kept. |
| 15 | 107.md | docs/reports/ | docs/archive/reports/ | Report-107 ổn định gate WFO per-quý (06-26). Chỉ được ref bởi archive/insights/CONTEXT_HANDOFF (đã archive). |
| 16 | 133.md | docs/reports/ | docs/archive/reports/ | Task-133 GATE-0 verify alignment (07-07, ĐO xong). Tự chứa, không ref canonical. Move cùng .worker.log + .csv. |
| 17 | 133.worker.log | docs/reports/ | docs/archive/reports/ | Worker log của task-133 (transient stdout), move cùng cụm 133. |
| 18 | coverage_133.csv | docs/reports/ | docs/archive/reports/ | Output CSV chỉ được 133.md tham chiếu; move cùng cụm 133. |

## File CÂN NHẮC nhưng GIỮ LẠI (không move — có lý do)
- `overnight_worklog.md` — GIỮ: được `insights/WFO_ROADMAP.md` (canonical) tham chiếu là "nhật ký phiên".
- `013.md`, `036.md`, `037.md`, `041.md` — GIỮ: được AGENTS.md / decisions/0010 / 0011 tham chiếu.
- `141.md`, `142.md` — GIỮ: được report `151.md` (còn giữ, task gần đây) tham chiếu, tránh gãy link.
- `146.md`, `150-156.md` (+worker.log) — GIỮ: campaign đang chạy (SESSION_START liệt kê task 146,150-156 active).
- `BUGHUNT_WFO_20260713`, `DATA_FLOW_AUDIT_20260713`, `KAGGLE_*`, `ramcache_ticker_142`,
  `KAGGLE_DATA_VERIFY_METHODS` — GIỮ: được handoff LIVE `NEXT_SESSION_TODO_20260714.md` tham chiếu (việc đang làm).
- `TRACE_FF_ret2_vs_maxfav3_20260713.md`, `trace_MAXFAV3.txt`, `trace_RET2WF.txt` — GIỮ: là dữ liệu của
  Task3a ĐANG CHẠY (chốt ret2 vs maxfav3).
- `LEAKFREE_WFO_RUNBOOK`, `wfo_leaked_funding_v1_report`, `wfo_leakfree_funding_v2_report`,
  `wfo_strategy_window`, `dca_primary_20260711`, `trailing_stop_sweep_139` — GIỮ: được canonical
  (insights/WFO_ROADMAP, runbooks/NIGHT, STRATEGY_CONSOLIDATED, reference, insights/dca) tham chiếu.

## Hoàn tác (nếu cần)
- `git status` sẽ hiện 18 file rename docs/reports/ → docs/archive/reports/.
- Hoàn tác: `git checkout -- docs/` hoặc move ngược lại. Chưa commit.
