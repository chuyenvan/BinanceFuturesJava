# TASK B2 Bước 3 — Phòng thủ UNIVERSAL: drawdown-throttle (phép thử dứt khoát cho breadth) — thiết kế MASTER 2026-09-21

Người soạn: MASTER. Thực thi: agent Sonnet. Chủ quyết định: Uni ("thử phòng thủ universal 1 lần cuối").
Tiền đề: 3 vòng breadth trước — TASK B (pacing-size) NULL; B2 regime-gate cứu 2022 lộ 2025; chẩn đoán 2025 (`DIAG_UW2025_SOURCE.md` `89063f8`) = nén-alpha-biên trong bull-nhiễu, CONC_CAP 0/9 không cứu. Kết luận: mỗi loại giai đoạn xấu cần một detector riêng → overfit trap trên 4.5 năm. Bước này thử MỘT cơ chế phòng thủ KHÔNG nhắm regime cụ thể, nhắm trực tiếp trạng thái nội tại "hệ đang dưới nước", để tách bạch: UW có giải được bằng bất kỳ cơ chế phơi-nhiễm nào không, hay là nội tại của breadth.

## 0. LUẬT — như B2 (không nới)
An toàn (HOLDOUT 2026/242/push/thư mục bảo vệ/index.lock); **1 job nặng/lần** (`free -g`≥12G, `pgrep java` rỗng → **dừng shadow-c3 trước chuỗi sim, bật lại ngay sau, ghi mốc**); PREREG commit trước; cổng tái lập T170 md5 `efb793e2468ca3a7318da0f0ad23d4fc`; **cổng OFF byte-identical** flag mới; khẩu vị hiện hành `x1_rates.py --appetite current --k`; logging chuẩn.

## 1. GIẢ THUYẾT + DỰ BÁO GHI TRƯỚC (quan trọng — chống giải-thích-xuôi)
H: Trên nền gate 1.0 (breadth), một **drawdown-throttle** — giảm phơi nhiễm mới khi equity đang dưới đỉnh cũ (rolling max), causal, KHÔNG cần biết loại giai đoạn xấu — kéo UW ≤ 200 mà giữ n_eff ≥ 1.5× T170. Vì cả bear-2022 lẫn bull-nhiễu-2025 đều biểu hiện là "hệ dưới nước", một cơ chế theo dd nội tại nhắm được CẢ HAI cùng lúc mà chỉ 1 tham số (ít overfit hơn nhiều-detector).

**🔴 DỰ BÁO CỦA MASTER (ghi TRƯỚC khi chạy)**: nhiều khả năng **NULL** — drawdown-throttle gần như chắc giảm maxDD (giảm size khi dưới nước), NHƯNG có nguy cơ **kéo dài UW** vì giảm phơi nhiễm lúc dưới nước = ít vốn để phục hồi = hồi chậm hơn = thời gian dưới nước không giảm hoặc tăng. Đây đúng cơ chế đã làm TASK B (pacing-size) NULL: UW quyết bởi *nhịp phục hồi*, không phải *biên độ lỗ*. Nếu dự báo đúng ⇒ bằng chứng mạnh **UW là nội tại của breadth long-only** (không cơ chế phơi-nhiễm nào giải được), ⇒ đóng hướng breadth dứt khoát. Nếu SAI (UW về ≤200 mà n_eff giữ) ⇒ giải trọn vẹn, tin tốt lớn.

H0 (NULL): UW không về ≤200; HOẶC đối chứng giảm-đều (R0) đạt ngang DT (phòng thủ theo-dd không hơn giảm-chung).

## 2. CƠ CHẾ (khoá trong PREREG, tối thiểu tham số, causal)
`dd(t) = equity(t)/rolling_max_equity(≤t) − 1` (≤0), tính từ equity nội tại của chính hệ, causal tuyệt đối (chỉ dùng ≤ t).
`mult(t) = clip( 1 − |dd(t)| / D , floor , 1 )` — phơi nhiễm mới (size hoặc gate-scale) co tuyến tính theo độ sâu drawdown, chạm `floor` khi `|dd| ≥ D`. Hai tham số, chọn theo LÝ LẼ (không quét):
- `D` = độ sâu dd mà tại đó thu về mức phòng thủ tối đa. Đề xuất `D = 0.15` (= nửa ngưỡng maxDD khẩu vị 30%, lý lẽ: bắt đầu phòng thủ mạnh khi đã mất nửa "ngân sách" rủi ro). Agent chốt 1 giá trị, ghi lý lẽ.
- `floor` = mức phơi nhiễm tối thiểu = tỉ lệ exposure T170/gate-1.0 (~0.2, để lúc dưới nước sâu hệ co về ~mức T170 chứ không tắt hẳn — giữ khả năng phục hồi). Agent tính từ dữ liệu, chốt trước.
Cắm tầng SIZING (điểm cắm `PacingSizing`/`VolTargetSizing` đã có, byte-identical OFF). KHÔNG lookahead.
⚠️ Nếu agent thấy dạng "giảm size" chắc chắn kéo dài UW (theo dự báo), được phép thêm 1 biến thể dạng **admission** (dừng mở lệnh MỚI khi dd sâu, giữ lệnh đang mở để phục hồi) — nhưng khai báo trong PREREG là biến thể thứ 2 (k tăng), vì admission đổi tập lệnh (confound). Mặc định chỉ dạng sizing.

## 3. BIẾN THỂ (k trong PREREG)
Baseline (không tính k): **T170**, **gate-1.0**. 
- **DT (chính)**: gate 1.0 + drawdown-throttle sizing §2.
- **R0 (đối chứng, đã có từ Bước 2)**: gate 1.0 giảm đều khớp tổng số lệnh ≈ DT (tách phòng-thủ-theo-dd khỏi giảm-chung). Nếu R0 cũ (gate 1.18) không khớp lượng DT, chỉnh lại cho khớp, ghi rõ.

## 4. TIÊU CHÍ (khoá trước; UW là chính)
- **u1 breadth**: n_eff_total(DT) ≥ 1.5× n_eff_total(T170).
- **u2 khẩu vị**: PASS hiện hành, **đặc biệt UW ≤ 200** (toàn kỳ VÀ mọi năm) + CAGR ≥ cận dưới CI-72h(k) T170.
- **u3 vs incumbent**: maxDD ≤ −14.8% VÀ UW ≤ 115.
- **u4 theo-dd đúng**: UW(DT) < UW(R0) VÀ UW(DT) < UW(gate-1.0 no-throttle) — bằng chứng throttle GIẢM (không tăng) UW; nếu UW(DT) ≥ UW(gate-1.0) thì xác nhận dự báo (throttle kéo dài UW).
- THẮNG = DT đạt u1-u4; NULL = u2 vỡ (UW>200) hoặc DT không hơn R0/gate-1.0 ở UW; HỖN HỢP = còn lại.

## 5. ĐO — metric tổng hợp/phân phối (KHÔNG khoá sym,start). Cùng cửa sổ 2021-07-01..2025-12-31, Oracle ARM64. Báo per-year.

## 6. QUY TRÌNH
PREREG `docs/prereg/PREREG_DD_THROTTLE.md` (cơ chế §2 + D/floor + biến thể + u1-u4 + dự báo §1 + phán quyết) commit TRƯỚC → code (throttle vào điểm cắm sizing, OFF byte-identical) → cổng OFF T170 md5 → dừng shadow-c3 → sim tuần tự (T170 verify, DT, R0 nếu cần chỉnh) → bật shadow-c3 verify → tính u1-u4 (`bigdown_struct.py`+`x1_rates.py`) → `docs/result/RESULT_DD_THROTTLE.md` verdict → commit branch `module` (KHÔNG push) → dọn wfo_ds tạm, giữ printDone/sim.out.
OFF không byte-identical → DỪNG, báo MASTER.

## 7. Ý NGHĨA (điểm quyết định lớn)
- THẮNG ⇒ breadth giải được bằng phòng thủ universal ⇒ shadow paper song song ≥1 tháng trước khi bàn đổi incumbent.
- **NULL ⇒ ĐÓNG HƯỚNG BREADTH LONG-ONLY dứt khoát**: ghi `power_wall.md` kết luận đầy đủ — UW là nội tại của breadth (đã thử size-pacing, regime-per-type, universal-dd-throttle; không cơ chế phơi-nhiễm nào giải được vì giảm phơi nhiễm = phục hồi chậm = UW không đổi). Chuyển TASK D (alpha mới: tăng số cược bằng trigger không tương quan MOM15) như đường power còn lại.

## 8. Sau khi xong: cập nhật project memory (`round_2026-09-20...md` + `MEMORY.md`), báo MASTER: bảng T170/gate-1.0/DT/R0 (n_eff, ICC, maxDD, UW, CAGR+CI, per-year), u1-u4 ✅/❌, verdict, đối chiếu DỰ BÁO §1 (throttle giảm hay kéo dài UW), cổng OFF PASS, mốc shadow, diff Java.
