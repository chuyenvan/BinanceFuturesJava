# PREREG_E2E_REPLAY_V12 — ERRATA 3 (CHỐT 2026-11-16 đêm, MASTER; TRƯỚC khi dựng fixture 11-05 và trước lượt chính thức)

**Căn cứ:** A1 vòng 2 (`~/claude_master/v12/A1_E2E_V12_R2.md`) trên harness `1302fd81`: KHÔNG duyệt, 2 lỗi chặn của HARNESS/bộ chấm (B1, B2).
Chưa có lượt replay nào trên fixture 11-05. Ghi nhận trung thực: để tìm B1, A1 đã ĐỌC đầu vào thô của 11-05 (thứ hạng trong `sel_dump`
phút 22:51 và danh sách LEGACY ngày đó) — là dữ liệu đầu vào, không phải kết quả replay; không tiêu chí chấm jar nào được nới ở đây.

## E9. R-OLD phải tái lập ĐÚNG cấu hình của bản dry thật ngày 11-05 (B1)
- Bản dry ngày 11-05 chạy với coin LEGACY bị loại khỏi c3 (`C3_EXCLUDE_LEGACY_HELD` chưa đặt false; đổi sang false ngày 11-10). Prereg §4
  chỉ ghi "2 cờ TẮT" nên R-OLD của harness chạy với `C3_EXCLUDE_LEGACY_HELD=false` ⇒ replay sẽ mua coin LEGACY mà bản thật không mua,
  U lệch kéo theo budget của mọi leg sau đó lệch > 1e-4 mà không gắn nhãn được ⇒ E2 FAIL do harness.
- Sửa: lượt **R-OLD** (và chỉ R-OLD) đặt `C3_EXCLUDE_LEGACY_HELD=true` + danh sách LEGACY lấy từ dữ liệu ngày 11-05 đã kéo về
  (`pull242/2026-11-05`, file/dòng log nguồn + md5 ghi vào result.json). Các lượt khác giữ `false` như prereg §1.
- Nhãn `LEGACY-11-05` của E2 vì vậy không còn cần cho leg bị loại; giữ lại cho trường hợp danh sách LEGACY trong ngày thay đổi (phải
  chỉ ra dòng log). Ngưỡng E2 (≥ 20/23, budget |Δ|/b ≤ 1e-4, mọi lệch phải có nhãn khai trước) GIỮ NGUYÊN. File `tools/e2e/labels_1105.csv`
  (có thể rỗng) phải commit TRƯỚC lượt chính thức; không được thêm nhãn sau khi thấy kết quả.

## E10. U phải được tính ĐỘC LẬP (B2)
- Bộ chấm đang lấy `margin_before` (U) do chính jar báo để tính budget kỳ vọng ⇒ U sai nhưng nhất quán với budget vẫn PASS. Sửa: REF tính
  U độc lập từ `fills.csv` (margin các leg đã khớp / C_eff theo đặc tả); thêm tiêu chí vào S1 và D1: |U_REF − U_jar| ≤ 1e-6 cho MỌI SUBMIT.
- Thêm vào S1: `eq_at` (equity jar dùng khi tính size) ≡ `eq_at` của REF (sai số tương đối ≤ 1e-6) cho mọi SUBMIT.

## E11. Sửa lỗi harness khác (không đổi tiêu chí)
- REF-nến giữ symbol thêm 1 phút sau cụm `ARM_CUNG_NEN` ⇒ có thể làm E1 FAIL oan khi symbol vào lại top-K ngay phút sau: trạng thái
  "đang giữ" của REF cho cụm có nhãn lấy theo phút thoát của REF-nhịp.
- Khoá chạy 1 lần: việc ghi errata vào file khoá phải thành công mới được chạy lại; một errata chỉ mở khoá ĐÚNG 1 lần.
- result.json ghi md5 file giá trị env 242 đã dùng và md5 `labels_1105.csv`.
- Câu chữ: nhịp exit của live là 10 s (`C3LiveRuntime:78`), không phải 15 s; rig và REF-nhịp phải dùng đúng nhịp của production
  (nếu rig đang cấp nhịp +0/15/30/45 s thì ghi rõ đó là độ phân giải của ĐẦU VÀO giá, không phải nhịp exit).

## E12. Phân xử N7–N13 (A1 vòng 2) — ghi nhận, không đổi tiêu chí
- N7: điều kiện thị trường ở live tính trên universe A1, sim không lọc — khác biệt có chủ đích đã ghi (AUDIT_GOLIVE_1116_D, D7); phần
  "ticker khả dụng" là lệch nhỏ chưa ghi ⇒ thêm vào danh sách giới hạn của gate.
- N8: `DIED_SYMBOLS=BTCDOM,USDC` lấy từ `config.properties`, khớp repo và sim.
- N9: thứ tự BIG_DOWN → DCA → selector: live = sim (đã đúng sau ERRATA 1).
- N10: cache equity 60 s — thuộc khác biệt N4 đã ghi; ràng buộc bằng `eq_at` (E10).
- N12, N13: cùng họ N5 (xử lý theo nhịp trong nến); ghi vào danh sách giới hạn của gate.

## E13. Quy trình
Dev sửa E9–E11 trên fixture 10-30 → A1 duyệt lại phần thay đổi → MASTER chạy lượt chính thức 11-05 đúng 1 lần.
