# TASK D — Alpha mới: trigger sự kiện không tương quan MOM15 (thiết kế khung MASTER 2026-09-21)

Người soạn: MASTER. Thực thi: agent Sonnet. Chủ quyết định: Uni (đã chốt: đóng breadth, chuyển TASK D).
Trạng thái: **KHUNG — chưa chạy.** Bước đầu là recon + thiết kế feature, KHÔNG lao vào build/backtest ngay.

## 0. Vì sao TASK D (bối cảnh đóng breadth)
Đường power của T170 là "tăng số cược độc lập" (power_wall). Hướng breadth (hạ gate lấy nhiều lệnh) đã đóng sau 5 round NULL: breadth có alpha nhưng UW là nút thắt nội tại, và phòng thủ per-regime vượt số sự kiện độc lập 4.5 năm cho phép fit. **Đường còn lại: tăng số NGÀY có cược bằng một TRIGGER MỚI, không tương quan với gate MOM15 hiện tại.** T170 chỉ vào lệnh ~110/1644 ngày (77% giờ trống) — nếu có một nguồn tín hiệu độc lập (không dựa momentum 15m) thì nó thêm cược ở những ngày MOM15 im lặng ⇒ tăng số cược độc lập thật (khác breadth: breadth thêm lệnh cùng cơ chế → tương quan cao; trigger mới thêm lệnh cơ chế khác → ít tương quan).

Ứng viên (từ `docs/EVENT_DATA_SURVEY.md`, TASK4 bước 1): **listing/delisting event** (khả thi nhất; token unlock đã loại vì lookahead risk + coverage kém).

## 1. LUẬT (không nới)
An toàn (HOLDOUT 2026/242/push/thư mục bảo vệ/index.lock); 1 job nặng/lần; PREREG trước; đo tầng xếp hạng phải CPU không GPU; Kaggle-variant chỉ so Kaggle, Oracle chỉ so Oracle; logging chuẩn. **Cổng tái lập T170 md5 `efb793e2` nếu chạm sim.**

## 2. BA RÀNG BUỘC PHƯƠNG PHÁP BẮT BUỘC (bài học các round trước)
1. **Lookahead trên event data**: announcement time ≠ effective time. Listing/delisting có ngày công bố và ngày hiệu lực khác nhau; feature phải dùng thông tin CHỈ tới thời điểm giao dịch được (causal). Kiểm kỹ timestamp nguồn — đây là lý do token-unlock bị loại.
2. **Missingness-as-subset-indicator (bài học OFI)**: event feature chỉ phủ một subset nhỏ symbol/ngày (không ngẫu nhiên) → NaN-mask tự nó thành chỉ báo. Noise control BẮT BUỘC dùng ĐÚNG NaN-mask với candidate; nếu noise cũng "thắng" thì không quy cho nội dung feature.
3. **Đo tầng xếp hạng trước, không tầng equity** (power_wall): rank-IC/edge CPU trên CONFIRM trước; chỉ khi có edge tầng xếp hạng mới cân nhắc sim tầng equity. Nested SELECT/CONFIRM, block-bootstrap-72h, inflate(k).

## 3. BƯỚC 1 — RECON nguồn dữ liệu event (0-sim, làm TRƯỚC)
Đọc `docs/EVENT_DATA_SURVEY.md` (commit `c9c5c23`) + xác định chính xác:
- Nguồn listing/delisting: Binance API/announcement nào cho ngày listing & delisting của mọi symbol trong universe? Có FREE không (như aggTrades ở TASK3)? Coverage lịch sử 2021-2025 đủ không?
- Timestamp: mỗi event có announcement_time VÀ effective_time riêng không? (bắt buộc cho causal — RÀNG BUỘC 1).
- Coverage: bao nhiêu symbol/ngày có event? (phủ subset nhỏ → RÀNG BUỘC 2).
- Giả thuyết alpha cụ thể: listing mới → pump/vol tăng (long momentum sớm)? delisting → dump (tránh/short)? Hình dạng edge kỳ vọng, cửa sổ thời gian sau event.
- Trigger này có THẬT không tương quan MOM15 không: event xảy ra ở ngày/symbol nào so với ngày T170 vào lệnh — overlap thấp = độc lập thật.
Output: `docs/RECON_EVENT_ALPHA.md` — nguồn, coverage, timestamp causal-safe, giả thuyết đo được. Cổng GO/NO-GO: có nguồn causal-safe + coverage đủ + giả thuyết đo được → GO thiết kế feature; nếu không (như token unlock) → NO-GO, báo MASTER.

## 4. BƯỚC 2 — ĐO EDGE TẦNG XẾP HẠNG (chỉ khi Bước 1 GO)
PREREG trước. Build feature event causal (announcement→effective an toàn). Đo edge:
- Nếu là feature cross-section (rank symbol): rank-IC CPU trên CONFIRM, noise control cùng NaN-mask (RÀNG BUỘC 2), so Kaggle-baseline nếu chạy Kaggle.
- Nếu là trigger timing (ngày có event → vào lệnh): đo forward return sau event vs baseline, số ngày event trùng/không trùng ngày MOM15 (độc lập thật), edge có sống qua cost không.
Verdict tầng xếp hạng: có edge (CI loại 0, noise control không thắng) → Bước 3; NULL → dừng, ghi power_wall.

## 5. BƯỚC 3 — SIM (chỉ khi Bước 2 có edge)
Thiết kế sau khi có edge. Trigger event như một nguồn admission SONG SONG với MOM15 (thêm cược ngày MOM15 im), giữ cổng OFF byte-identical + tái lập T170. Đo số cược độc lập tăng thật (ICC/n_eff), risk (maxDD/UW/khẩu vị), CAGR. Đối chứng chống confound.

## 6. Ý nghĩa
Đây là đường power khác breadth — nếu edge event thật + độc lập MOM15, nó tăng số cược độc lập mà không tăng phơi nhiễm cùng-hướng (không dính UW-trap của breadth). NULL ở bất kỳ bước → ghi power_wall, đường power qua dữ liệu hiện có + event FREE coi như cạn; khi đó chỉ còn dữ liệu trả phí (L2 depth Tardis ~$4.5-14.8k/năm, TASK3) hoặc tích cược thật qua shadow forward.

## 7. Mỗi bước: cập nhật project memory, báo MASTER GO/NO-GO hoặc verdict.
