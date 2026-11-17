# PREREG_PARITY_V12_DRY — ADDENDUM 23 (2026-11-17, MASTER): owner chấp nhận ngoại lệ E2 của phép thử replay (iii) cho MICRO

**ĐÂY LÀ SỬA ĐỔI SAU KHI ĐÃ THẤY KẾT QUẢ (post-hoc).** Nó không làm cho kết quả gốc thành PASS: theo đúng chữ
`PREREG_E2E_REPLAY_V12.md` + ERRATA 1–4, lượt chính thức ngày 2026-11-17 có kết luận (iii) = FAIL. Addendum này chỉ ghi lại quyết định
của owner về khẩu vị rủi ro cho giai đoạn MICRO và phạm vi của quyết định đó.

## 1. Kết quả gốc (không đổi)
- Lượt chính thức duy nhất: 2026-11-17 01:32 +07, harness `def1f034`, jar `641803565297d4065d90245e04a00f11`; kết quả commit ở worktree
  `~/claude_master/fin1114/c3_e2e` `336d28c2` (`docs/c3live/E2E_REPLAY_V12_RESULT.md`, `docs/c3live/e2e_v12_official_1105/`).
- PASS: C1, E1 (24 leg ≡ REF), S1 (24 SUBMIT; 3 leg đầu 225,0000 / 216,5647 / 208,4436), D1 S-DCA, X1 (24 cụm: 21 TRAIL + 3 TIME_STOP),
  F1, K1. D1 tự nhiên: KHÔNG XẢY RA. §6: vốn micro = 1 000 (24/24 leg đặt được ở 1 000).
- **E2 = FAIL:** 23/23 SUBMIT thật khớp symbol + phút + thứ tự; 22/23 khớp budget |Δ|/b ≤ 1e-4; AINUSDT lệch 1,35e-4 (35,2176 so với
  35,2224 USDT). A1 độc lập (`~/claude_master/v12/A1_E2E_OFFICIAL_1105.md`): lượt chạy nguyên vẹn; không nhãn khai trước nào áp được;
  nguyên nhân là thiếu sót đầu vào của harness (bản dry thật cache equity 60 s theo markPrice và làm mới giữa hai leg; giá size là
  price_realtime), không phải lỗi jar; code sizing / margin của jar ngày 11-05 (r4q) và jar hiện tại không khác dòng nào.
- Dữ liệu đã lưu không có giá theo giây và không cho biết pha của cache ⇒ không thể chạy lại để đạt 1e-4 mà không khớp ngược từ kết quả thật.

## 2. Quyết định của owner (2026-11-17, trong phiên làm việc với MASTER)
- Owner được trình hai phương án: (A) chấp nhận cho MICRO với ghi nhận rõ là nới sau khi thấy kết quả; (B) dựng lại E2 bằng dữ liệu theo
  giây từ nguồn ngoài (1–2 ngày, có thể vẫn không đạt). Owner trả lời: **"tôi chọn A, chấp nhận rủi ro micro"**.
- MASTER khuyến nghị A vì: lệch 0,0048 USDT trên một leg 35 USDT; nguyên nhân đã được A1 độc lập xác định bằng bằng chứng; các tiêu chí
  logic so với REF độc lập đều PASS; vốn rủi ro của MICRO là 1 000 USDT.

## 3. Phạm vi của ngoại lệ (cố định)
1. Chỉ áp dụng cho việc tạo gate **MICRO** với ĐÚNG lượt chính thức nêu ở §1 và ĐÚNG jar `641803565297d4065d90245e04a00f11`. Đổi jar ⇒
   ngoại lệ hết hiệu lực, phải chạy lại phép thử.
2. Cho mục đích tạo gate MICRO, điều kiện ADD22 §3 (iii) được coi là ĐẠT khi và chỉ khi: (a) mọi tiêu chí C1, E1, S1, D1 (S-DCA), X1, F1,
   K1 của lượt chính thức PASS; (b) E2: 23/23 khớp symbol + phút + thứ tự và ≥ 20/23 khớp budget ≤ 1e-4; (c) mọi SUBMIT lệch còn lại được
   A1 độc lập quy cho thiếu sót đầu vào của harness bằng bằng chứng, không phải lỗi jar. Cả ba điều đã thoả ở lượt §1.
3. KHÔNG áp dụng cho **PILOT**. Trước PILOT bắt buộc: so replay với sim engine trên dữ liệu 2026 ("phương án A" của prereg replay §0) và
   một phép thử độ trung thực của rig không cần ngoại lệ (ví dụ nạp giá theo giây từ nguồn độc lập), có prereg riêng.
4. Ngoại lệ này và việc DCA grid tự nhiên không xảy ra trong cửa sổ replay phải được nêu trong `docs/prereg/GATE_LIMITS_MICRO.md`
   (mục 0) để owner đọc lại ở câu hỏi YES của `golive_micro_on.sh`.

## 4. Các điều kiện khác của ADD22 §3 GIỮ NGUYÊN
(i) 7/7 ngày sạch; (ii) + smoke đo lại sau khi bật 2 cờ grid (biên bản `GMICRO_MANUAL_<ngày>.md`); (iv) kiểm sizing trên dry thật (hoặc
override có tên + lý do khi không có SUBMIT để đo); (v) script go-live bản A1 duyệt (`b9e661db7f089fc68e23b6b2c7275aa44ec090b1`, đã cài 17/11).
Vốn micro theo luật §6 của prereg replay: 1 000 USDT.
