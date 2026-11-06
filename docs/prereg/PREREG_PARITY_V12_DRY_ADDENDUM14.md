# PREREG_PARITY_V12_DRY — ADDENDUM 14: guard độ đủ phút ở live ([MINUTE-INCOMPLETE]) và cách tính trong parity (2026-11-06, TRƯỚC khi chạy r4r)

Quyết định MASTER (ROUND 4r). **Khai:** viết SAU khi thấy lệch thật ở live phút 11-04 23:46Z (nến chốt 627/752 symbol, vì WS
connection #4 với 125 symbol rớt; live tính trên 504 symbol, ngày thường 509–513). Code guard: c3live `7913b1b9`. Viết trước khi
jar r4r chạy trên 242. Chưa chấm ngày nào có guard.

## 1. Hành vi live (CHỈ có ở live; sim/harness KHÔNG mô phỏng)
- Tại tick quyết định (~giây :06), ngay sau `tickerWindow.read`, live đếm số symbol có nến ở phút vừa chốt (`co`). So với
  `can` = ⌈99 % × trung vị số symbol của 60 phút trước⌉. Nếu có dưới 30 phút lịch sử thì bỏ qua guard.
- `co ≥ can`: không đọc thêm, không đổi gì. Kết quả trùng từng byte với r4q.
- `co < can`: đọc lại mỗi 2 s, chậm nhất tới giây +20 sau khi phút chốt.
  - Đủ trong hạn: log `[MINUTE-WAIT]`, đọc lại cửa sổ và quyết định bình thường trên phút đã đủ.
  - Vẫn thiếu: log `[MINUTE-INCOMPLETE] phut=… co=… can=… trung_vi60=… cho=…ms doc_lai=… => KHONG mo lenh moi …`.
    Phút đó fail-closed: không mở lệnh mới, kể cả entry, DCA và paper (`createOrderBuyRequest0` log `[MINUTE-INCOMPLETE] chan lenh moi`).
    Quản lý vị thế, trailing và stop giữ nguyên.
- Tắt guard bằng `LIVE_MINUTE_GUARD=0`. Lúc khởi động, log `[MINUTE-GUARD] BAT|TAT`.
- Sim/replay/harness (`replayToCsv`, E2E, `day_*` của parity) **không** có guard, vì dữ liệu offline là Vision/REST đã đủ.
  Vì vậy, phút guard chặn sẽ lệch có chủ đích so với sim.

## 2. Cách tính trong parity (cố định trước)
1. Phút live có dòng `[MINUTE-INCOMPLETE] … KHONG mo lenh moi` gọi là **phút MI**. Phút MI bị **loại khỏi K5**, mọi nguồn lệch.
2. Phút MI **phải được đếm và báo cáo** trong `day_report_v12`:
   - `mi_minutes` (danh sách phút + `co/can`);
   - `mi_blocked_legs` (số dòng `chan lenh moi`);
   - `mi_wait_recovered` (số dòng `[MINUTE-WAIT]`).
   Một ngày có `mi_minutes > 0` thì ghi thêm nhãn mô tả "MI=n". Nhãn này chỉ để mô tả, không đổi kết luận ngày.
   Nếu cần ngưỡng, MASTER quyết riêng; ADD này không đặt ngưỡng.
3. Phút **`[MINUTE-WAIT]`** (thiếu rồi đủ trong hạn) **không** được loại. Chúng vẫn tính K5 như thường, vì live quyết định trên phút đủ.
4. Phút live lệch nhưng không có dòng MI vẫn theo các nhãn K hiện hành (ADD1–ADD13). Guard không mở thêm lối thoát nào cho K5.
5. Không thấy dòng `[MINUTE-GUARD] BAT` trong log ngày đó thì phần này không áp dụng (r4q trở về trước).

## 3. Số liệu nền (ingestor, `[KLINE V9 ws_settle] … Total: N`, từ QF3 11-01 → 11-06 16:56, 8 217 phút)
- 752 symbol ở 8 211 phút. Chỉ 6 phút dưới ngưỡng:
  - 11-05 06:46 (+07) = 11-04 23:46Z: 627;
  - 11-05 09:07: 626;
  - 11-05 20:56: 655;
  - 11-05 21:05: 624;
  - 11-05 21:06: 568;
  - 11-06 15:59: 730.
- Ngày 11-01..11-04: 0 phút kích hoạt, nên ngày thường không đổi.
- Số đếm trước QF3 không đại diện, vì REST bù sau, nên không dùng.

## 4. Test (c3live `MinuteCompletenessGuardTest`, 9/9)
- Tái hiện 23:46Z (627/752): chờ tới giây +18..+20, rồi fail-closed.
- Phút đủ: không đọc thêm, cửa sổ trùng từng byte.
- Bù muộn trong hạn: quyết định trên phút đủ.
- Ngưỡng biên 744/745.
- Tick sau hạn: không chờ.
- Thiếu lịch sử: bỏ qua guard.
- Ngày sập: 300 phút, nhiều kết nối rớt, có REST bù muộn; mọi phút thiếu đều bị gắn cờ, không phút nào trễ quá +20 s.
- Vị trí gắn guard (source check).
