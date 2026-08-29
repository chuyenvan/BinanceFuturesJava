# 🔴 LỖI TOÀN VẸN DỮ LIỆU: label export gộp quý QUÁ SỚM (race)

> Phát hiện 2026-08-08 04:40 ICT. Đây là lỗi CHẶN — mọi dữ liệu label đã push lên Kaggle
> đều nghi ngờ thiếu dòng. KHÔNG train/backtest trên bộ label hiện tại cho tới khi xử lý xong.

## 1. Hiện tượng

Job label (`ExportFundingLabel`, PID 243175) kết thúc **EXIT=0** với dòng
`✅ Xong toàn bộ: 636.512.182 dòng emit, 778 coin | 20210101 → 20260701`.
Nhìn log thì như thành công. Nhưng **không phải**.

## 2. Bằng chứng quyết định — quý 2024Q4 (ĐÃ PUSH lên Kaggle)

Dòng thời gian trích từ `label_export_pb.log`:

```
19:45:54  đóng file quý 20241001_to_20250101 ( 9.066.253 dòng)
20:04:45  đóng file quý 20241001_to_20250101 ( 9.520.087 dòng)
20:50:48  đóng file quý 20241001_to_20250101 (10.069.457 dòng)
21:38:38  đóng file quý 20241001_to_20250101 (     4.321 dòng)
21:38:49  ✅ Đã gộp quý 20241001_to_20250101   <=== GỘP TẠI ĐÂY
21:52:15  đóng file quý 20241001_to_20250101 (     4.318 dòng)
22:24:34  đóng file quý 20241001_to_20250101 (11.859.598 dòng)   <=== NGUYÊN 1 PARTITION
00:04:15  đóng file quý 20241001_to_20250101 (    12.954 dòng)
01:16:31  đóng file quý 20241001_to_20250101 (    21.482 dòng)
03:12:36  đóng file quý 20241001_to_20250101 (    17.191 dòng)
```

- Tổng dòng thật của quý: **40.575.661**
- Có trong file đã gộp (trước 21:38:49): **28.660.118**
- **Bị bỏ sót: 11.915.543 dòng = 29,4%**

Khớp với dị thường kích thước đã thấy mà lúc đó tôi chưa truy: 2024Q3 = 1,454 GB nhưng
2024Q4 chỉ 0,863 GB (**−41%**), trong khi số coin tăng dần theo thời gian nên quý sau phải
LỚN hơn quý trước.

## 3. Nguyên nhân

Điều kiện kích hoạt gộp quý sai: nó fire khi *một số* partition đã đóng quý, chứ không đợi
**cả 4** partition. Các partition chạy lệch nhau rất xa (partition 3 chậm hơn ~45 phút), nên
partition chậm ghi tiếp vào `.partN.pb` **sau khi** file quý đã được gộp và (với các quý đã push)
đã bị xoá local.

Mỗi quý bị "đóng" nhiều hơn 4 lần (2024Q4: 9 lần; 20251001_to_20260101: 13 lần) — partition
mở/đóng lại cùng một quý nhiều lượt, xác nhận gộp một lần là không đủ.

## 4. Phạm vi thiệt hại

| Nhóm | Số quý | Tình trạng | Khôi phục được? |
|---|---|---|---|
| Đã push Kaggle (2021Q1 → 2025Q1) | 18 | Nghi thiếu dòng; 2024Q4 xác nhận thiếu 29,4% | ❌ file `.partN.pb` đã bị xoá ⇒ **phải export lại** |
| 2025Q2, 2025Q3, 2025Q4, 2026Q1 | 4 | **Chưa gộp bao giờ**; parts còn nguyên trên đĩa | ✅ gộp lại được (format `.pb` nối byte thuần) |
| 2026Q2 (20260401_to_20260701) | 1 | **Chưa từng được mở** — 0 lần xuất hiện trong log | ❌ chưa có dữ liệu |

⚠️ **Coverage thật kết thúc ở 2026-04-01, không phải 2026-07-01** như TASK-251 yêu cầu — dù
log "Xong toàn bộ" ghi `20210101 → 20260701` (đó là khoảng cấu hình, không phải khoảng đã ghi).

## 5. Vì sao verify trước đó không bắt được

Các lần verify chỉ so **size file local với size trên Kaggle** (khớp byte 863.302.705 ✓).
Điều đó chỉ chứng minh upload không hỏng, **không** chứng minh file đủ dòng. Bài học: verify
phải đối chiếu **số dòng thực tế so với số dòng log kỳ vọng**, không chỉ so size upload.

## 6. Việc phải làm (chờ Uni quyết)

1. Sửa điều kiện gộp: chỉ gộp khi **đủ cả 4 partition** đóng quý, hoặc bỏ hẳn gộp trong lúc
   chạy và gộp một lượt ở cuối.
2. Gộp lại 4 quý còn parts (2025Q2 → 2026Q1) — làm được ngay, không tốn Aerospike.
3. Export lại 18 quý đã push (~9h) — hoặc chấp nhận thiếu dòng nếu đánh giá được là vô hại
   (KHÔNG khuyến nghị: 29,4% ở một quý là quá nhiều, và phần thiếu là nguyên một partition
   = một nhóm coin cụ thể, tức thiếu có hệ thống chứ không ngẫu nhiên).
4. Làm rõ vì sao 2026Q2 không được mở (ticker thiếu 01→07/2026 có thể là nguyên nhân).
5. Thêm kiểm tra hậu-export: tổng dòng trong file quý phải khớp tổng dòng log của quý đó.
