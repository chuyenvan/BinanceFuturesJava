# ADR-0008: Circuit breaker — MARGIN halt hiệu quả; DCA cap (vs avgEntry) vô hiệu cấu trúc

- **Ngày:** 2026-06-11
- **Trạng thái:** đã chấp nhận (kết luận đo lường) — hướng định nghĩa lại cap còn OPEN (chờ chọn + test).
- **Bối cảnh:** TASK-006 (breaker 4 mode FULL) + TASK-006.1 (scenario DCA LUNA cô lập tầng DCA).

## Vấn đề
DCA-không-giới-hạn có đúng là cơ chế ruin (FINDINGS §1)? Phanh nào chặn được?

## Bằng chứng
- **006** (FULL 2021→2026, data thiếu coin chết): MARGIN halt 0.70 → maxDD −58%→**−43%** (đổi ~10% PnL), margin trần 0.99→0.71. DCA cap −0.30 → PnL/DD ~y nguyên (vô dụng) — nhưng chưa kết được vì thiếu coin chết.
- **006.1** (scenario LUNA $91→$0, ép 1 cụm, KHÔNG Aerospike): OFF 75 nhồi → mất **99.1% vốn** (ruin xác nhận). ON(−0.30) veto **4311 lần nhưng lỗ Y HỆT 99.1%**, clusterDd-max −1.0.

## Phân tích
DCA cap đo `clusterDd = (price − avgEntry)/avgEntry`. `avgEntry` vol-weighted **bám theo giá** khi nhồi (BIG_DOWN `isAll=true` nhồi mỗi −15%, kéo avgEntry tụt) ⇒ clusterDd quanh −15% suốt pha sụt từng bước, chỉ chạm −30% khi giá đã sụp thẳng và **vốn đã cạn ~99%**. ⇒ cap vô hiệu **CẤU TRÚC** (đo DD vs mốc TRÔI theo chính hành vi nhồi).

## Quyết định
1. **Bỏ DCA cap hiện tại** (DD vs avgEntry, −0.30) — vô hiệu cấu trúc, KHÔNG phải vì thiếu coin chết.
2. **Định nghĩa lại ràng buộc DCA theo VỐN/CONCENTRATION** (mốc cố định), ứng viên — chọn + test trên scenario 006.1 trước khi áp:
   - (i) DD vs **ENTRY-ĐẦU** (cố định) thay avgEntry.
   - (ii) trần **SỐ LEG**/cụm.
   - (iii) trần **%VỐN**/cụm (chặn concentration 1 coin).
3. **Giữ MARGIN halt 0.70** làm guardrail (ràng buộc tổng margin/vốn — hiệu quả). Số tuyệt đối lạc quan (data thiếu coin chết + funding tắt); ngưỡng quét sau.

## Bài học
Ràng buộc rủi ro phải neo vào **vốn/exposure (mốc cố định)**, KHÔNG vào DD-so-avgEntry (mốc trôi theo chính hành vi nhồi). Đây là lý do MARGIN hiệu quả còn DCA-cap-vs-avgEntry vô hiệu.

## Hệ quả
- Hướng bước 3 (ruin): redefine DCA cap (chọn i/ii/iii) → test scenario 006.1 (rẻ, không Aerospike) → áp nếu cứu được. MARGIN halt giữ.
- Đánh giá định lượng TỔNG (qua chu kỳ, nhiều coin chết) vẫn cần full backfill [B] (ADR-0007).
