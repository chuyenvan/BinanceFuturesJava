---
id: 146
status: REVIEW
depends_on: []
touches_live_process: false
writes_242_data: false
resource: oracle
checkpoint: false
max_retry: 1
report: docs/reports/146.md
require_review: true
---

# TASK-146: DỌN & HỢP NHẤT tài liệu docs/ (34 file → cấu trúc gọn)

## Mục tiêu (1 câu)
Gom 34 file .md rời rạc trong `docs/` thành một cấu trúc gọn, không mất thông tin, dễ điều hướng — 1 điểm
vào duy nhất (`index.md`) trỏ tới các doc CANONICAL, archive phần trùng/cũ.

## Scope
**Trong scope:**
1. Đọc toàn bộ `docs/*.md`, phân loại mỗi file vào 1 nhóm:
   - **CANONICAL** (giữ, là nguồn sự thật): `CORE.md`, `WFO_DATAFLOW.md`, `REBUILD_ROADMAP.md`,
     `SOLUTION_FRAMEWORK_20260711.md`, `STRATEGY_ROADMAP_3PART.md`, `PIPELINE_PROVENANCE.md`, `index.md`.
   - **HỢP NHẤT** (nhiều file cùng chủ đề → gộp 1): các `STRATEGY_FINDINGS_*`, `FINDINGS.md`,
     `MASTER_STRATEGY_CAMPAIGN.md`, các report chiến lược rời → gộp vào 1 `docs/STRATEGY_CONSOLIDATED.md`
     (giữ mọi số liệu + kết luận, bỏ trùng lặp).
   - **ARCHIVE** (cũ/đã thay thế, không xóa — move sang `docs/archive/`): `TRACE_backtest_drift.md`,
     `STATUS_RECON.md`, `_reconcile-report.md`, `DEPLOY_242_dot2.md`, `LIB_BINANCE_OLD.md`, `basis_verify.md`,
     `AUDIT_filter_ablation.md`, các file "một-lần" đã hết vai trò.
2. Tạo/ cập nhật `docs/index.md`: mục lục 1 trang — mỗi doc canonical 1 dòng mô tả + link; nhóm theo
   {Data, Model, Chiến lược, Vận hành/Deploy, Hạ tầng}.
3. Với mỗi file HỢP NHẤT/ARCHIVE: để lại stub 2 dòng ở vị trí cũ trỏ tới nơi mới (tránh link chết).

**Ngoài scope:**
- KHÔNG sửa nội dung kỹ thuật / số liệu (chỉ tổ chức lại + gộp trùng). KHÔNG xóa file (chỉ move/stub).
- KHÔNG đụng code, jar, 242.

## Nguyên tắc hợp nhất (chống mất thông tin)
- Mọi SỐ LIỆU ĐO ĐƯỢC + KẾT LUẬN + BÀI HỌC phải còn nguyên trong doc hợp nhất (có thể rút gọn văn, KHÔNG
  bỏ số). Nếu 2 file mâu thuẫn → GIỮ CẢ HAI + ghi chú "cần Uni xác nhận cái nào đúng", KHÔNG tự chọn.
- Trước khi move/gộp: `git mv` (giữ history), KHÔNG `rm`.

## Acceptance criteria
- [ ] `docs/index.md` là mục lục đầy đủ, mọi link sống.
- [ ] Số file .md ở docs/ (ngoài archive/) giảm rõ (mục tiêu ≤ ~15 canonical).
- [ ] `docs/archive/` chứa file cũ, mỗi file gốc có stub trỏ đi.
- [ ] `git status` sạch, dùng `git mv` (history còn).
- [ ] Report 146.md: bảng "file → nhóm → đích", danh sách mâu thuẫn cần Uni xác nhận (nếu có).

---
## (Code điền) Kết quả
Đã: (1) gộp `STRATEGY_FINDINGS_20260710.md` + `MASTER_STRATEGY_CAMPAIGN.md` → `STRATEGY_CONSOLIDATED.md`
(giữ 100% số liệu, stub ở gốc); (2) chuyển `he-thong-kien-truc-trang-thai.md` (file mới, trùng lặp
architecture.md/DATA_STATE.md/SESSION_START.md) sang `reference/ARCHITECTURE_STATE_SNAPSHOT_20260707.md`
(git mv, stub ở gốc); (3) thêm section "Chiến lược" + 1 dòng reference vào `index.md`. 10 file stub đã
gộp từ phiên trước (`AUDIT_filter_ablation.md` v.v.) — verify đúng trạng thái, không đụng lại (tránh churn).
Chi tiết đầy đủ: `docs/reports/146.md`.

## (Code điền) Phát hiện ngoài scope
Task mô tả dựa trên snapshot `docs/` cũ hơn thực tế — phần lớn "archive/hợp nhất" mô tả trong task
**đã được làm ở phiên trước** (docs/reference/ + docs/archive/ đã tồn tại, 10 stub đã đúng chỗ). Việc
thật còn lại nhỏ hơn nhiều so với mô tả ban đầu.

## (Code điền) Quyết định phát sinh
- KHÔNG gộp `FINDINGS.md` vào STRATEGY_CONSOLIDATED dù task liệt kê — khác chủ đề (model/backtest findings
  vs chiến dịch chiến lược) + bị 6 file khác trỏ trực tiếp vào. Gộp sẽ phá link + trộn nhầm chủ đề.
- KHÔNG archive `DEPLOY_242_dot2.md` / `LIB_BINANCE_OLD.md` dù task liệt kê — cả hai đang active
  (runbook chờ duyệt / nợ kỹ thuật chưa quyết), không phải "cũ/đã thay thế". Cần Uni xác nhận trước khi
  archive (câu hỏi đã gom vào report 146.md).
