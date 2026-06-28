# ADR-0008: Circuit breaker — MARGIN halt hiệu quả; DCA cap (vs avgEntry) vô hiệu cấu trúc

- **Ngày:** 2026-06-11
- **Trạng thái:** ĐÃ CHỐT (2026-06-28). Kết luận cuối: cap neo-cố-định vô dụng trên DANH MỤC; chốt MARGIN halt 0.50. Xem §Kết luận cuối.
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

## Kết luận cuối (2026-06-28) — chốt Bước 3
Đã làm đúng quy trình ADR: chọn ứng viên (iii) trần %vốn/cụm, test 006.1 rồi áp engine thật + đo full backtest.

**006.1 (1 coin) — cả 3 cap neo-cố-định CỨU ruin** (vs OFF mất 79%): (i) ddVsFirst −0.30 → mất 8.8%; (ii) maxLegs 5 → 8.8%; (iii) maxCap 5% → **5.3%**, 10% → 10.5%. Cap cũ (vs avgEntry) veto 4927 lần vẫn mất 79.6% (tái xác nhận vô hiệu cấu trúc). %vốn mất ≈ trần đặt ra (concentration limit trực giác).

**Full backtest 2021→2026 (engine thật, nhiều cụm) — cap %vốn/cụm VÔ DỤNG:** CAP10 veto **0 lần** (PnL/DD y hệt OFF), CAP5 veto **8 lần** cả 5 năm. Lý do: budget mỗi leg do `managerBudget` chia theo TỔNG vốn + cắt khi marginRatio cao → vốn phân tán qua HÀNG TRĂM cụm nhỏ, không cụm đơn nào đạt 5-10% tổng vốn. Scenario 1-coin cứu được CHỈ vì cô lập (toàn vốn dồn 1 cụm) — KHÔNG đại diện danh mục.

**Lá chắn THẬT = MARGIN halt tổng.** Quét ngưỡng (OFF + 0.50→0.90):

| Ngưỡng | totalPnl | maxDD | maxMargR | return/maxDD |
|---|---|---|---|---|
| OFF | 69379 | −58.6% | 0.99 | 3.38 |
| **0.50** | 50311 | **−29.5%** | 0.51 | **4.88** |
| 0.60 | 57139 | −36.0% | 0.61 | 4.54 |
| 0.70 | 63164 | −42.5% | 0.71 | 4.25 |
| 0.80 | 65491 | −48.6% | 0.80 | 3.85 |
| 0.90 | 68674 | −54.7% | 0.91 | 3.59 |

return/maxDD tăng đơn điệu khi siết → **chốt 0.50** (an toàn nhất: DD gần nửa, đổi 27% PnL). GATE liêm chính PASS (OFF totalPnl khớp baseline Bước 2). GỠ hẳn cap %vốn/cụm + tham số DCA_CAP_* khỏi engine/Configs (không giữ code chết).

**Áp dụng:** `BREAKER_MODE="MARGIN"`, `BREAKER_MARGIN_HALT=0.50` mặc định. Đổi PnL/DD mọi genome → bump CONFIG_VERSION **v9→v10**.

**Bài học bổ sung:** scenario cô-lập-1-coin chứng minh được "cap nào CÓ THỂ cứu" nhưng KHÔNG đại diện tác động danh mục (phân tán vốn làm cap per-cluster vô hiệu). Luôn xác nhận trên full backtest trước khi kết luận. Còn lại Bước 3: funding cost + margin-call/equity thật (maxDD hiện có thể hiểu nhẹ).
