# TASK-022: Verify basis 1m (premiumIndex / mark / index) từ data.binance.vision — phát hiện 014

- **status:** REVIEW — BƯỚC 1 VERIFY xong (`docs/basis_verify.md`); chờ user chốt dùng + schema → mới sang BƯỚC 2 backfill.
- **owner:** CCD-basis · **updated:** 2026-06-14
- **Lý do:** TASK-014 đánh giá `premiumIndexKlines` + `markPriceKlines` + `indexPriceKlines` (1m, từ 2019-12) = **CAO** — basis (perp − spot) ở granularity phút, bổ trợ funding (funding chỉ 8h thô). Verify nguồn trước; backfill sau khi chốt dùng + chốt schema.

## Chạy ở đâu
**Kaggle** (tải + parse vision) — tách khỏi 226, KHÔNG đụng 020/021 đang chạy. Theo `RUNBOOK_kaggle_multi_cpu`.

## ⚠️ Phạm vi: CHỈ VERIFY (bước 1). KHÔNG backfill, KHÔNG ghi Aerospike ở task này.
- Backfill (bước 2) chỉ làm SAU khi user chốt dùng basis (gate hay selector) + chốt schema — tránh prep data thừa.

## BƯỚC 1 — VERIFY (báo cáo ra file để Desktop/user soát)
Tải mẫu 3 loại cho BTC + 1 alt (vd 1 coin list muộn), trả lời:
1. **Granularity + schema:** mỗi loại (premiumIndex/mark/index) cột gì, đơn vị, granularity 1m thật? timezone create_time.
2. **Coverage per-coin:** firstSeen mỗi loại (alt chỉ có từ ngày list); range tới nay; gap.
3. **Định nghĩa basis — quan trọng:** `premiumIndexKlines` là cái gì (premium rate sẵn?) vs tự tính `mark/index − 1`? Ba nguồn (mark, index, premiumIndex) **cái nào cần lưu** để biểu diễn basis — chọn **1 đại diện** (tránh nhồi 3 cột trùng).
4. **Quan hệ với funding:** basis (1m) so funding (8h) tại vài mốc — basis có "dẫn" funding không (định tính), để biết giá trị bổ trợ.
5. Dedup + gap.
→ Ghi **1 file** (vd `outputs/basis_verify.md` hoặc trong task) cho Desktop/user đọc → quyết dùng + schema → mới sang bước 2.

## BƯỚC 2 — BACKFILL (CHỜ user chốt; spec sau)
- Set Aerospike basis 226 (+242 qua 226), schema thống nhất (1 đại diện basis, granularity chốt). Như mẫu backfill funding/OI.

## An toàn
- Bước 1 chỉ tải + đọc + dump mẫu (Kaggle). KHÔNG ghi Aerospike/không đụng live/ingest. Throttle tải.

## Acceptance (bước 1)
- [ ] File verify: granularity/schema 3 loại + coverage per-coin + **định nghĩa basis + chọn 1 đại diện** + quan hệ funding + dedup/gap.
- [ ] Đủ để Desktop/user quyết dùng basis (gate/selector) + schema trước khi backfill.

## (Code điền) → CHI TIẾT: `docs/basis_verify.md`
- **Granularity/schema 3 loại:** cả 3 = kline chuẩn 12 cột, **1m thật** (1440 bar/ngày, step 60000ms, 0 gap, ts unique). `open_time` epoch **ms UTC**. `premiumIndex.close` = **premium RATE** (~6e-4, unitless); `mark.close`/`index.close` = **giá USDT**. volume/quote/taker = 0; count: premiumIndex=12, mark/index=60.
- **Coverage per-coin:** BTC từ **2020-01** (KHÔNG phải 2019-12 — đính chính 014); alt firstSeen = ngày list (ENA 2024-04), 3 nguồn đồng bộ. Range → nay; mẫu 0 gap/0 dup.
- **Định nghĩa basis + đại diện chọn:** **CHỌN `premiumIndexKlines.close`** (1 cột rate; là input funding; so sánh được giữa coin). corr với `(mark−index)/index` = 0.895 nhưng KHÁC (premiumIndex mượt hơn). KHÔNG lưu mark/index cho mục đích basis.
- **Quan hệ basis↔funding:** premiumIndex 1m là **input trực tiếp dựng funding 8h** (tái tạo khớp: avgP+clamp(interest−avgP,±0.05%) → 0.0001 = funding thực). Funding kẹp sàn 0.01%/8h trong khi premium 1m dao động 0.013–0.10% → **basis 1m mang nhiều info hơn, sớm hơn 8h → bổ trợ CAO** (xác nhận 014).
- **CHỜ USER CHỐT (trước BƯỚC 2):** (1) dùng basis? (khuyến nghị CÓ); (2) đại diện = premiumIndex.close; (3) granularity lưu (1m hay aggregate 5m/15m); (4) schema 226(+242) align GMT+7 như funding/OI.
