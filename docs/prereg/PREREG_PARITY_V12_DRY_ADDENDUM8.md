# PREREG_PARITY_V12_DRY — ADDENDUM 8: sửa harness A1 fail-closed (2026-11-04, TRƯỚC khi sửa code)

**§0 Khai:** viết SAU khi thấy R5 TRƯỢT (commit a4ccf676, `docs/result/parity_v12_d1/r456_20261104.json`).
Đây là sửa lỗi **nhánh đo (harness nghiên cứu)**. Không đổi tiêu chí R5 hay bất kỳ tiêu chí nào khác, không đổi code
production (jar dry r4n fb6711ef, code 1f505414), không đổi `GOLIVE_QUARTERLY_2026_A1`.

## 1. Lỗi đã xác định (chỉ đọc code)
- R5 ngày 10-30, exinfo fixture 10-27 (serverTime 1793072475507): nsym OFF-BT 524, OFF-NEW2 518, khiến f12–f16 lệch ở cả 1440 phút.
  Hiệu = 6 symbol niêm yết sau snapshot (EWZS/SMR/OXY/AMGN/PFE/MELI), có trong `univ/u_20261030.txt`.
- Production: `UniverseA1Filter.excludedIn` (`UniverseA1Filter.java:214-225`): symbol ∉ snapshot và t > serverTime thì LOẠI (fail-closed).
  Live NEW2 (`LiveFeaturePipeline.java:168`) và BT production (`ExportGateDataset.java:176-177`) đều gọi hàm này.
- Harness: (a) `py/a1cls.py:24-30` thiếu luật fail-closed; (b) nhánh BT `V11FeatHarness.java:121-133` không gọi
  `UniverseA1Filter` trên snapshot phút. Vì vậy OFF-BT-A1 của harness ≠ BT production.

## 2. Sửa (cố định trước)
1. `V11FeatHarness` nhánh BT: mỗi phút `snap = UniverseA1Filter.filter(cpMap(raw), ts)` TRƯỚC `md.update`, `hm.updateHistory`,
   `extractAllFeatures`, `fund`. Đây là cùng hàm với production; khi cờ tắt thì trả nguyên map.
2. `a1cls`: thêm `fail_closed(path, syms, t_ms)` = {s ∈ syms : s ∉ snapshot ∧ t_ms > serverTime}, port y nguyên `excludedIn`.
   `day_prep.universe`: U_D^A1 loại thêm `fail_closed(EXINFO, cand, T0)`. Cách này chỉ loại khi T0 > serverTime, tức cả ngày nằm sau snapshot,
   nên trùng với lọc theo phút. Khi serverTime ∈ [T0, T1] thì để Java lọc theo phút. `day_eval.a1_excl_at` dùng cùng luật.
3. `pv_cfg`: biến `PV_R5_EXINFO` (tuỳ chọn) đổi file exinfo cho R5. `r456.py r5 [tag]` lưu kết quả vào `R5` hoặc `R5_<tag>`.

## 3. Kiểm sau sửa (tiêu chí R5 giữ nguyên: CTL rows_bit_nonfund_gate = 1.0 và rows_tol_nonfund_fund = 1.0)
- **R5 chính:** 10-30 + fixture 10-27 (như cũ). PASS/FAIL theo tiêu chí trên, quyết định R5 trong day_report_v12.
- **R5 phụ `pit1104`:** 10-30 + snapshot dry 11-04 (`exinfo_1793754061893_*`). Snapshot này không phải PIT của 10-30, nhưng chứa đủ
  symbol, nên kiểm trường hợp fail-closed không kích hoạt. Kết quả chỉ báo cáo, không thay R5 chính.
- Nếu R5 chính vẫn TRƯỢT thì không sửa tiếp. Báo MASTER kèm cột lệch.
- Ngày 11-03 chấm lại không cần thiết: exinfo = None, nên phần A1 vẫn KHÔNG ĐO ĐƯỢC.
