# ADR-0010: Thiết kế lại model market = GATE (label / features / dùng)

- **Ngày:** 2026-06-11
- **Trạng thái:** 🟡 ĐANG TRIỂN KHAI (việc 4) — chốt hướng 2026-06-21 (xem mục cuối). Còn A0 (đo phân bố sập để chốt H/X) + data export + train.
- **Bối cảnh:** ADR-0009 (pivot). Đã chốt với user: **market = gate** (không chọn coin — funding lo). Sửa lỗi label `max-high`.

## Nhiệm vụ (1 câu)
GATE mức thị trường: quyết "thời điểm t có cho hệ MỞ long mới không" + điều tiết mức. KHÔNG per-symbol.

## Lỗi label cũ (`futureReturn15M` + `maxDrawdownNext4H`)
1. `max-high` = đỉnh look-forward → lạc quan. 2. horizon 15M quá ngắn. 3. `maxDrawdownNext4H` avg-low = proxy vol-spike (gần rule). 4. avg-basket → lẫn timing với chọn coin.

## Label — CHỐT: classification 3 lớp
**Forward return thị trường trong H giờ tới (close-to-close)** → 3 lớp: **`giảm ≥ X%` / trung tính / `tăng ≥ X%`**.
- Gate điều tiết 3 mức: sắp-sập → chặn; trung tính → vào bình thường; thuận → mạnh tay hơn.
- Thay CẢ `futureReturn15M` lẫn `maxDrawdownNext4H`.
- **Lưu ý train:** lớp "giảm mạnh" thiểu số → **xử imbalance** (cái quan trọng nhất, đừng để học qua loa). Vế "thuận long" edge mỏng + chồng selector → đừng kỳ vọng nhiều, đo vs rule.
- **Quét:** H ∈ {4H, 12H, 24H}; X ∈ {−15%, −20%}.

## Phạm vi đo — CHỐT: thị trường rộng
BTC + ETH (đầu tàu) + breadth + funding extreme + regime. KHÔNG dùng basket top-giảm (để selector).

## Features

### Giữ từ bộ 34
- **Cốt lõi:** BREADTH (`advanceDeclineRatio`, `percentAboveMA20`, `marketBreadthStrength`, `volumeRatioUpDown`) + FUNDING (`fundingRateRaw/Avg24H/Trend`) + VOLATILITY (`volatility*`, `volatilityTermStructure`, `volumeSpike`).
- **Tỉa:** momentum BTC 6 khung → 15M/1H/4H/24H.
- **Bỏ:** GROUP 5 TIME (mồi overfit — học "tháng 5 sập" vì LUNA).
- **Encode:** `volatilityRegime` (string) → ordinal/one-hot.
- **Để selector:** GROUP 3 BASKET (giữ mỗi `basketVolSpike`).

### Candidate THÊM (từ thảo luận — đưa vào rồi để feature-selection tỉa, KHÔNG hardcode hết)
Nguyên tắc: thêm theo **khái niệm**, mỗi khái niệm 1 đại diện; data ít cú sập → cẩn thận overfit.
- **Giá-vs-SMA 15m/4h** (dạng tương đối `price/SMA−1` hoặc slope — KHÔNG tuyệt đối). Vị thế so trung bình, bổ sung momentum.
- **Alignment ngắn-vs-dài** (cùng/ngược chiều) — bắt **bear-rally** (tăng ngắn trong downtrend dài = bẫy trước sập). Giá trị cao cho gate.
- **Regime bull/bear:** giá vs MA dài (MA200 daily) + cờ breakout/breakdown.
- **ETH momentum 15m/4h** — có chế độ ETH dẫn độc lập BTC (BTC im + ETH bơm → alt tăng); để correlation-check, drop nếu trùng BTC >~0.9.
- **Đồng-pha BTC–ETH** (cả hai cùng giảm mạnh = sập diện rộng) + dispersion/correlation toàn cục.

## Cổng nghiệm thu (BẮT BUỘC)
So model vs **rule trần** ("chặn khi breadth thấp VÀ funding cao"). Không vượt rule rõ → dùng rule, bỏ ML gate. Edge timing mỏng — kỳ vọng gate chỉ lọc vài chế độ sập rõ.

## OPEN
- H ∈ {4H,12H,24H}, X ∈ {−15%,−20%} — quét khi train.
- Feature-selection tỉa nhóm candidate (correlation + importance).

---

## Cập nhật 2026-06-21 — chốt hướng triển khai (việc 4, user duyệt)

Bối cảnh: model market 15m cũ (regression futureReturn15M, IC 0.52 de-overlap thật) đã có code+đã train nhưng KHÔNG dùng (IC ngang model đang chạy → thay vô nghĩa). Quyết định: làm GATE MỚI theo ADR này, mục đích **chặn-sập**. Nếu không hiệu quả → quay lại nâng cấp features model cũ.

**Chốt:**
1. **Label = 3-lớp chặn-sập** (không phải regression 15m). 15m không bắt được sập (realized %>3%=0.1%, %>6%=0%; edge chỉ vùng nảy ~1% — xem FINDINGS §2a). Gate phải nhìn forward H giờ để thấy chế độ sắp sập.
2. **"Làm mịn features" = thêm candidate ADR (price-vs-SMA, alignment ngắn-dài, regime MA200, ETH mom, đồng-pha BTC-ETH) rồi feature-selection tỉa** + BỎ nhóm time (4 feat hourOfDay/dayOfWeek/weekOfMonth/monthOfYear — mồi overfit LUNA tháng 5).
3. **THÊM OI (mới, ngoài bộ candidate gốc của ADR):** OI hiện có per-coin (TASK-039: oi_delta24h, oi_z, ls_global, ls_toptrader, taker_buy). Gate là MARKET-LEVEL nên phải **aggregate per-coin → market**: ví dụ ΔOI% toàn thị trường, taker buy/sell ratio toàn TT, long/short ratio toàn cục (median/mean qua coin). KHÔNG bê thẳng OI per-coin vào gate basket. Đưa vào rồi feature-selection tỉa.

**A0 (đo TRƯỚC khi chốt H/X) — đo không đoán:** với mỗi (H,X) đếm số **cú sập độc lập** (de-overlap theo H) trong 2021–2026. Số mẫu lớp "sập" quyết định cấu hình, không chốt mò. Cần chuỗi giá thị trường (BTC hoặc rổ) — KHÔNG có sẵn (226 không có python-aerospike/file giá), phải viết tool Java `ExportMarketCloseSeries` đọc Aerospike ticker → CSV BTC/market 15m close, rồi Python đếm sập.

**Acceptance (đo lớp sập, KHÔNG chỉ IC):** precision/recall riêng lớp "sập" + đếm cú sập độc lập trong test (đủ mẫu mới tin) + **so rule trần "breadth thấp VÀ funding cao"**. Không vượt rule rõ → bỏ ML gate, quay lại nâng cấp. Train trên TOÀN lịch sử 2021–2026 (đủ nhiều cú sập), không chỉ holdout 12 tháng. Cẩn thận imbalance (lớp sập hiếm) — đây là phần quan trọng nhất.

**Rủi ro đã lường:** horizon dài → ít mẫu de-overlap (futureReturn24H chỉ ~360 điểm/12 tháng — FINDINGS §2b) + lớp sập hiếm dễ overfit vài cú lịch sử (LUNA/FTX). A0 sẽ cho biết (H,X) nào đủ mẫu.

---

## A0 KẾT QUẢ + CHỐT H/X (2026-06-22)

Định nghĩa BTC-only ban đầu SAI trọng tâm (mẫu cực hiếm). Định nghĩa đúng = **breadth trên top-50% coin theo vol-1d**: tại mốc t, % coin top giảm ≥X% trong H giờ tới ≥ 50% → "cú sập thị trường". Đo full 2021–2026 (189,792 mốc 15m, tool `ExportMarketBreadthCrash`).

Số đợt sập độc lập (de-overlap):

| H \ X | −10% | −15% | −20% |
|---|---|---|---|
| 4h | 68 | 17 | 5 |
| 12h | 118 | 34 | 15 |
| 24h | 156 | **49** | 27 |

**CHỐT: H=24h, X=−15%, breadth≥50% top-50%-vol** (49 đợt). Phụ: 12h/−15% (34). Lý do: −10% quá nhạy (2.59% thời gian), −20% mỏng ở H ngắn; −15%/24h là "sập diện rộng thật" đủ mẫu chia regime. Chi tiết: `docs/reports/041.md`.
