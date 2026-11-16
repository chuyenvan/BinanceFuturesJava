# PREREG_E2E_REPLAY_V12 — ERRATA 1 (CHỐT 2026-11-16 ~19:45 +07, MASTER; TRƯỚC khi dựng fixture 11-05 và trước lượt chính thức)

**Căn cứ:** chỉ từ fixture PHÁT TRIỂN 10-30 và đọc code (dev `fa9b4cac`, báo cáo `~/claude_master/v12/E2E_V12_DEV.md`; A1 độc lập
`~/claude_master/v12/A1_E2E_V12.md`). Chưa có số nào của fixture 11-05. A1 phân xử từng điểm theo SIM engine A3 (`~/claude_master/r3_wt`) và
tài liệu có trước 11-16, không theo code live. Mỗi sửa đổi dưới đây chỉ rộng bằng đúng khác biệt đã chứng minh; mọi tiêu chí / dung sai
không nêu ở đây GIỮ NGUYÊN.

## E1. Sửa đặc tả (đặc tả §3 của prereg viết thiếu; live = sim)
- **N2 — cổng p15 cho leg DCA:** leg DCA grid phải qua cổng phẳng `MIN_MOMENTUM_15M` (p15 thị trường ≥ 0,008) ở CẢ live và sim
  (sim `createOrder:2286-2301`). Thêm vào đặc tả REF.
- **N6 — điều kiện thị trường của DCA grid:** DCA grid chỉ được xét ở phút có BIG_DOWN hoặc `isDcaAlt` (live
  `DetectEntrySignal2TradeNormal:472-516`, sim `Simulator:340-420`), không phải mọi phút. Rig và REF của bản `fa9b4cac` xét mỗi phút =
  LỖI HARNESS/REF ⇒ phải sửa cả hai. REF tự tính điều kiện thị trường từ nến 1m theo công thức của sim (ghi công thức vào SPEC), không
  lấy từ output replay.
- **N4 — vốn tính size:** `C_eff = min(C3_CAPITAL, E)`, E = equity c3 theo mark (avail + margin). Phần "vốn giảm khi lỗ" khớp sim (sim
  dùng equity); phần "không phình theo lãi" là khác biệt có chủ đích đã ghi (`ROUND4.md:86`). Công thức sizing §3 đổi `C` → `C_eff`; REF
  tính E ĐỘC LẬP từ fills + giá mark của fixture; dung sai S1/D1 giữ 1e-5 trên budget, thêm |E_REF − E_replay|/E ≤ 1e-6.
- **N1 — time-stop:** phân tích code cho thấy KHÔNG lệch phút so với sim (live cắt ở b0 + 168 h + 75 s, sim ở nến b0 + 168 h + 1′).
  X1 cho cụm TIME_STOP: phút thoát ≡ REF (0 lệch); giá thoát ∈ [L, H] của nến đó; loại cụm TIME_STOP khỏi trung bình Δ giá.

## E2. Override khai thêm
- **N3:** thêm `LIVE_TS_MKT_EXT=0` vào danh sách override (X14 tắt trong replay; giới hạn đã ghi ở §7). Bộ chấm đọc `ts_ext` thật của
  11-05…11-14: cụm nào ở live sẽ được X14 hoãn time-stop thì gắn nhãn `X14_HOAN` và loại khỏi X1 (báo số lượng).

## E3. Khác biệt live ≠ sim CHƯA TỪNG GHI NHẬN (báo owner; không sửa jar trong phép thử này)
- **N5 — arm và kích stop trong cùng nến 1m:** live (nhịp 15 s) có thể arm trailing rồi khớp stop trong CÙNG phút; sim
  (`BLOCK_INTRABAR`) không cho khớp ở chính nến arm. Trên 10-30: 4/22 cụm thoát sớm 1 phút (Δ giá −0,26 / −0,01 / +0,03 / 0 %), 1 cụm
  dời SL trong chính phút thoát.
  - X1 phút thoát: cụm có sự kiện ARM hoặc dời SL trong CHÍNH phút thoát được phép lệch đúng −1 phút, gắn nhãn `ARM_CUNG_NEN`; các cụm
    còn lại vẫn ≥ 98 % cùng phút, phần dư ≤ ±1 phút. Báo cáo riêng số cụm `ARM_CUNG_NEN` và Δ giá của chúng.
  - Ghi vào "giới hạn / khác biệt đã biết" của gate file và danh sách Đợt 3.

## E4. Sửa cách chấm X1 về giá (lỗi thiết kế phép đo, không nới dung sai)
- Sàn giả khớp STOP tại giá nhịp (thường là L) ⇒ Δ giá khớp trộn lẫn mô hình sàn giả với hành vi jar. Tiêu chí giá của X1 đổi thành:
  **giá STOP mà jar ĐẶT (stopPrice của lệnh) so với SL của REF: lệch ≤ 2 tick** cho mọi cụm thoát bằng stop/trailing. Giá khớp của sàn
  giả chỉ BÁO CÁO (trung bình, min) — không chấm. Ngưỡng cũ [−0,8 %; 0] / −1,5 % bỏ khỏi tiêu chí PASS, giữ làm số báo cáo.

## E5. Siết thêm
- **D1 tự nhiên** được đưa vào kết luận: nếu có ≥ 1 DCA tự nhiên trong lượt chính thức thì phút đến hạn + legIdx + budget phải ≡ REF,
  lệch ⇒ FAIL (trước đây chỉ S-DCA quyết định). Không có DCA tự nhiên ⇒ ghi "KHÔNG XẢY RA", S-DCA quyết định như cũ. S-DCA phải tổng hợp
  cả điều kiện thị trường (E1/N6) và p15 (E1/N2).
- **Khoá chạy 1 lần:** `run_official_1105.sh` tạo file khoá cố định (không theo timestamp) ngay khi bắt đầu; đã có khoá ⇒ từ chối, trừ khi
  có errata mới của MASTER (ghi tên errata vào biến môi trường và vào result.json).
- Rig không được đọc `config.properties` của worktree cho key mà 242 không đặt: dùng mặc định trong code của JAR; liệt kê các key đó
  trong result.json.

## E6. Quy trình sau errata
Dev sửa (N6, E4, E5, C_eff, nhãn) trên fixture 10-30 → A1 duyệt lại phần thay đổi → MASTER cho chạy lượt chính thức 11-05 (1 lần).
