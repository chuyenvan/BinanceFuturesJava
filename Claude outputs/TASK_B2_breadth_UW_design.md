# TASK B2 — Theo đuổi breadth: GIẢI UW (thiết kế MASTER, 2026-09-21)

Người soạn: MASTER. Thực thi: agent Sonnet (khi bridge Oracle sẵn). Chủ quyết định: Uni (đã chọn "theo đuổi breadth").
Trạng thái: **THIẾT KẾ — chưa chạy.**

## 0. Vì sao vòng này tồn tại (kết quả TASK B)
Hạ gate 1.70→1.0 (P3, pacing bigdown γ=0.5) cho: n_eff ×1.8 (606→1089), **CAGR 34.17% > T170 29.27%** (breadth CÓ alpha, không phải noise), maxDD kéo về −14.28% — NHƯNG **UW = 248 ngày >> khẩu vị 200 và >> T170 92**. Cổng OFF byte-identical đã PASS (flag `SIZE_PACING_MODE` sạch, `PacingSizing.java`).
Ba điều đã học, khoá làm tiền đề vòng này:
1. **Nút thắt DUY NHẤT của breadth là UW**, không phải maxDD/CAGR. Giải được UW → breadth thắng.
2. **Pacing-SIZE không giải được UW** (giảm size đổi biên độ lỗ, không đổi nhịp thắng/thua). Đo trực tiếp: P0 (giảm đều) và P3 (giảm theo bigdown) đều UW 221-248.
3. **Flash-bigdown-24h (BD1a) KHÔNG phải nguồn UW** (t4 TASK B FAIL, ngược hướng). UW dài đến từ giai đoạn phục hồi chậm / xu hướng giảm kéo dài (bear multi-week), tập trung ở 2025 (P3 UW 2025 = 232).

⚠️ **Tension phải thừa nhận trước**: breadth = giữ nhiều lệnh long; UW ngắn = ít lệnh long trong bear. Long-only trong bear kéo dài tất yếu dưới nước lâu. Có thể KHÔNG thắng được cả hai. Điều đáng đo: regime filter CHỈ trong bear (giữ breadth ở uptrend/sideway, giảm/cắt ở bear) có cân bằng được không. Nếu không, kết luận trung thực: breadth ở rủi ro-UW cố định không khả thi long-only → cần công cụ khác (short/hedge — đã đóng; hoặc alpha timing-exit).

## 1. LUẬT (không nới) — như TASK B
An toàn (HOLDOUT/242/push/thư mục bảo vệ/index.lock); 1 job nặng/lần (`free -g`≥12G, `pgrep java` rỗng, **dừng shadow-c3 trước sim, bật lại sau, ghi mốc**); PREREG commit trước khi tính số; cổng tái lập T170 md5 `efb793e2468ca3a7318da0f0ad23d4fc`; cổng OFF byte-identical mỗi flag mới; khẩu vị hiện hành (maxDD≤30/UW≤200/quý≥−15/coin≤15%) qua `x1_rates.py --appetite current`; CI `--k`; logging chuẩn.

## 2. BƯỚC 1 — CHẨN ĐOÁN NGUỒN UW (0-sim, làm TRƯỚC, ~0.5 ngày)
**Không thiết kế cơ chế pacing trước khi biết UW đến từ đâu** (bài học TASK B: đoán regime sai → sim phí).

Dữ liệu: printDone/sim.out của T170 (`X1_GS_T170_2021`), gate-1.0 baseline (`X1_C3_FULL_2021`), và **P0/P3 của TASK B** (đã có sim.out, tìm run tag trong `docs/RESULT_PACING_BIGDOWN.md` / `/home/ubuntu/java/devrun/`). BTC 1h `CLOSES_1H.bin`. Tái dùng `bigdown_struct.py`/`c3_rates.py`.

Câu hỏi (commit `docs/PREREG_UW_DIAG.md` khoá metric trước):
1. **Định vị chuỗi UW dài nhất** của gate-1.0 và P3: bắt đầu/kết thúc ngày nào, sâu bao nhiêu, là 1 chuỗi hay nhiều. So cùng lịch với T170 (T170 dưới nước 92 ngày ở đâu?).
2. **Regime BTC trong chuỗi UW đó**: BTC vs MA200, drawdown BTC từ đỉnh, slope trend. Xác định UW dài trùng bear/sideway kéo dài hay không → **ĐỊNH NGHĨA REGIME cho pacing bước 2 lấy từ đây**, không đoán.
3. **Kênh/lệnh nào giữ hệ dưới nước**: trong chuỗi UW, các lệnh đang mở/đang lỗ là lệnh-lõi (có cả ở T170) hay lệnh-biên (chỉ gate 1.0 thêm)? Lệnh biên có ROI âm hơn trong bear không? (dùng đo tổng hợp/phân phối, KHÔNG khoá (sym,start) — match_rate 32.6% không tin được.)
4. **UW do đào sâu hay do không phục hồi**: trong chuỗi UW, equity đi ngang-âm (giữ lệnh lỗ, không thoát) hay dao động quanh đáy (vào-ra liên tục)? Phân biệt: cần regime-filter-admission (đừng vào thêm) hay cần exit nhanh hơn.
5. **T170 làm gì khác trong cùng giai đoạn** khiến UW nó chỉ 92: nó dừng vào lệnh (gate chặt tự lọc bear?) hay thoát sớm? — đây là manh mối cơ chế cần sao chép ở gate thấp.

Output `docs/DIAG_UW_SOURCE.md` + script + json, commit. **Cổng quyết định cho bước 2**: định nghĩa regime UW cụ thể (đo được, causal) + xác định cơ chế đúng là admission-filter hay exit — nếu chẩn đoán cho thấy UW là tính chất long-only-trong-bear không tránh khỏi mà không giết breadth, ghi NO-GO + kết luận vào `power_wall.md`.

## 3. BƯỚC 2 — PACING NHẮM UW (sim, chỉ sau bước 1, thiết kế chi tiết CHỐT SAU chẩn đoán)
Khung (điền sau bước 1). Nền gate 1.0 (breadth). Biến thể theo cơ chế chẩn đoán chỉ ra:
- **Nếu UW = vào lệnh trong bear kéo dài** → **R-regime**: giảm/dừng admission khi cờ **bear-multi-week** causal bật (định nghĩa từ bước 1, ví dụ BTC < MA200 N ngày, KHÁC flash-24h). Đối chứng **R0**: giảm size đều cùng mức trung bình (tách "nhắm bear" khỏi "giảm đều", như P0/P3 trước).
- **Nếu UW = không thoát/phục hồi chậm** → hướng exit (thoát nhanh trong bear) — nhưng đụng exit logic core, recon trước như A-recon.
- Cân nhắc **P2 rate-limit admission** (giãn nhịp vào, tầng admission — confound tập lệnh, khai báo rõ) nếu chẩn đoán cho thấy tích lũy đồng thời là vấn đề.

Tiêu chí (khoá trước, sửa từ TASK B để **UW là tiêu chí chính**):
- u1 breadth: n_eff_total ≥ 1.5× T170.
- u2 khẩu vị: PASS toàn bộ, **đặc biệt UW ≤ 200** (đây là cái TASK B vỡ) + CAGR ≥ CI-floor T170.
- u3 vs incumbent: maxDD ≤ −14.8% VÀ **UW ≤ 115** (không thua T170 quá 25%).
- u4 cơ chế: chuỗi UW dài nhất của biến thể regime **ngắn hơn** biến thể đối chứng giảm-đều (bằng chứng nhắm đúng regime, không phải giảm đều).
- THẮNG = biến thể regime đạt u1-u3 VÀ u4; NULL = không đạt u2 (UW vẫn vỡ) hoặc đối chứng ngang biến thể regime; HỖN HỢP = còn lại.

Quy trình chạy như TASK B §6 (PREREG → code điểm cắm → cổng OFF byte-identical → dừng shadow → sim tuần tự → bật shadow → tính u1-u4 → RESULT → commit, không push). Điểm cắm: nếu là admission-filter/rate-limit → tầng admission (`CONC_CAP`-style, A-recon xác nhận có tiền lệ byte-identical); nếu là size-theo-regime → tầng sizing (`PacingSizing` đã có, mở rộng).

## 4. Ý nghĩa quyết định
THẮNG ⇒ shadow paper song song ≥1 tháng trước khi bàn đổi incumbent. NULL/HỖN HỢP ⇒ ghi `power_wall.md`: breadth-long-only bị chặn cứng bởi UW-trong-bear, không giải được ở rủi ro cố định ⇒ đóng hướng breadth; chuyển alpha mới (TASK D) hoặc timing-exit.

## 5. Sau mỗi bước: cập nhật project memory (`round_2026-09-20...md` + `MEMORY.md`), báo MASTER số + verdict + mốc shadow + diff.
