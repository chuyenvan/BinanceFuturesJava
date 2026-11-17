# PREREG_DIAG_NOTRADE_1117 — chẩn đoán "thị trường giảm mạnh mà dry không vào lệnh" + tuổi model (CHỐT 2026-11-17 ~09:10 +07, MASTER; TRƯỚC khi đo)

**Loại:** CHỈ ĐO, không đổi chiến lược / model / cấu hình. Câu hỏi của owner 11-17: BTC giảm từ ~80k xuống ~61k mà không có lệnh nào —
model hoặc khâu nào đó có tính sai không; model train tới đâu; go-live có cần train lại không.
Trạng thái đã biết trước khi đo: dry c3 không có SUBMIT nào từ 2026-11-05 22:53; ngưỡng gate live q ≈ 0,0095 (buffer nhiễm 30/10, D-02), bản
lọc 720 bản ghi cho q ≈ 0,00791; model live cut 2025-12-31; parity các ngày SẠCH xác nhận feature / p15 / gate của live khớp replay offline.

## Câu hỏi và cách đọc (ghi trước)
- **Q1 Thị trường:** đường giá BTC và rổ alt đều trọng số (universe live) từ 2026-10-25 tới ngày Vision mới nhất; 10 đợt giảm 15 phút và 60 phút
  sâu nhất của rổ alt trong giai đoạn; so với các phút gate MỞ ở 10-30 và 11-05. Đọc: đợt giảm gần đây là "trượt chậm" hay có cú sập ngắn cỡ
  các ngày gate mở.
- **Q2 Đầu ra model:** theo ngày từ 10-25: max và p99 của p15 thị trường, max của tỉ số gate r (giá trị so với ngưỡng q), số phút r ≥ 0,9·q.
  Đọc: p15 có "phẳng bất thường" không (so phân bố 10-25…11-05 với 11-06…nay).
- **Q3 Phản thực tế của gate:** số phút r ≥ q theo ngày từ 11-06 với q ∈ {q_t live tại phút đó; 0,00791 (buffer bỏ 720 bản ghi 30/10); 0,00766
  (bỏ thêm 30/10 07:26 và 15/10 09:29–09:30)}. Mỗi phút đạt: liệt kê.
- **Q4 Nếu Q3 có phút đạt với q sạch mà live không đạt:** chạy rig replay (harness e2e-v12, đúng byte jar live, 2 cờ grid bật, C = 10 000 và
  1 000) trên cửa sổ 11-06 → ngày Vision mới nhất với buffer đã lọc: số leg, DCA, lý do thoát, PnL từng cụm (chỉ báo cáo; rig khớp ở sàn giả).
- **Q5 Model:** ngày cắt dữ liệu train của model live (p15 + S1), cửa sổ train, nhịp train lại trong sim WFO (bao lâu một lần, model tại mỗi
  thời điểm bao nhiêu tuổi), kết quả HO 2026 theo quý đã có (HO4). Đo suy giảm trên dữ liệu live: AUC và độ khớp hiệu chuẩn của p15 (và hạng
  S1) theo tháng, dùng feat_dump / sel_dump live (10-21 → nay) + nến Vision, theo ĐÚNG định nghĩa nhãn lúc train; so với con số validation
  của model lúc train. Nếu không dựng lại được nhãn đúng định nghĩa ⇒ ghi "KHÔNG ĐO ĐƯỢC", không thay bằng nhãn tự đặt.

## Luật quyết định (ghi trước)
1. Q3: nếu với q = 0,00791 có ≥ 1 phút đạt trong 11-06 → nay mà q live không đạt ⇒ kết luận "buffer nhiễm đang làm mất lệnh"; MASTER xem lại
   quyết định hoãn lọc buffer (tối 16/11) và trình owner phương án lọc TRƯỚC micro. Nếu 0 phút ⇒ "không vào lệnh là đúng thiết kế với dữ liệu
   này"; giữ lịch.
2. Q2: nếu max p15 hằng ngày của 11-06 → nay thấp hơn p10 của phân bố max p15 hằng ngày năm 2026 (lấy từ dữ liệu sẵn có) ở > 50 % số ngày ⇒
   nghi feature / model stale ⇒ điều tra tiếp trước micro. Ngược lại ⇒ không có dấu hiệu.
3. Q5: nếu AUC p15 tháng 10–11/2026 thấp hơn AUC validation lúc train > 0,05 (tuyệt đối), hoặc sim WFO chưa từng dùng model già hơn tuổi model
   live hiện tại ⇒ khuyến nghị train lại + kiểm chứng holdout TRƯỚC PILOT (không trước micro: micro kiểm đường lệnh, và đổi model làm mất
   cửa sổ parity). Nếu không ⇒ không cần train lại trước pilot, đặt lịch train định kỳ theo nhịp WFO của sim.
4. Không kết luận nào ở đây được dùng để đổi tham số chiến lược. Mọi thay đổi (lọc buffer, train lại) cần prereg riêng.
