# PREREG_E2E_REPLAY_V12 — ERRATA 2 (CHỐT 2026-11-16 tối, MASTER; TRƯỚC khi dựng fixture 11-05 và trước lượt chính thức)

**Căn cứ:** vòng 2 của dev (`cdde0a8f`, `docs/c3live/E2E_REPLAY_V12_DEV_RESULT.md`), chỉ từ fixture PHÁT TRIỂN 10-30. Chưa có số nào của
fixture 11-05. Mọi điều không nêu ở đây giữ nguyên theo prereg + ERRATA 1.

## E7. Giá stop của cụm arm / dời SL trong chính phút thoát (N11, mở rộng E3 + E4)
- Hiện tượng (10-30, lượt S-TS): ở cụm QUSDT, jar dời SL ngay trong phút thoát (nhịp 15 s) nên stopPrice jar đặt lệch SL của REF-nến
  +244 tick ⇒ trượt E4. Đây là cùng một khác biệt live ≠ sim đã ghi ở E3 (live xử lý theo nhịp trong nến, sim `BLOCK_INTRABAR`), không
  phải khác biệt mới.
- Không miễn chấm. Thay vào đó thêm **REF-nhịp**: REF áp ĐÚNG luật trailing của đặc tả (arm, ratchet, khoảng trail) lên chuỗi giá nhịp
  trong nến mà rig được cấp (lấy từ ĐẦU VÀO fixture, không lấy từ output replay), cài độc lập bằng numpy.
  - Nhãn `ARM_CUNG_NEN` do **REF-nhịp quyết định** (REF-nhịp có ARM hoặc dời SL trong phút thoát của nó), KHÔNG đọc từ sự kiện của replay.
  - Cụm có nhãn: |stopPrice jar đặt − SL của REF-nhịp| ≤ 2 tick, và phút thoát ≡ phút thoát của REF-nhịp.
  - Cụm không nhãn: như ERRATA 1 E4 (so với REF-nến).
  - Nếu jar thoát kiểu "arm cùng nến" mà REF-nhịp KHÔNG gắn nhãn (hoặc ngược lại) ⇒ FAIL.
  - Báo cáo riêng: số cụm có nhãn, Δ giá và Δ phút của chúng so với REF-nến (= mức lệch live ↔ sim do nhịp trong nến).

## E8. Các nghi vấn N7–N10 của vòng 2 — xử lý tạm, CHỜ A1 xác nhận trước lượt chính thức
- N7 (điều kiện thị trường tính trên universe A1 ở live; sim không lọc A1; lệch 14/4319 phút trên 10-30): REF dùng universe A1 (đặc tả
  live, khác biệt có chủ đích đã ghi); báo cáo số phút lệch so với bản không lọc.
- N8 (`DIED_SYMBOLS` và key hạ tầng không có mặc định trong JAR): lấy từ danh sách trắng 242; liệt kê trong result.json.
- N9 (thứ tự BIG_DOWN / DCA trước selector): theo thứ tự production; A1 đối chiếu với sim.
- N10 (equity E có cache 60 s ở live): REF mô hình đúng cache 60 s nếu A1 xác nhận đó là hành vi có chủ đích; nếu không thì ghi
  "LỆCH-CHƯA-GHI" và báo owner.
- A1 bác bỏ điểm nào ⇒ MASTER ra errata tiếp TRƯỚC lượt chính thức; không chạy 11-05 khi còn điểm treo.
