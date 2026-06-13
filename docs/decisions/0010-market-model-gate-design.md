# ADR-0010: Thiết kế lại model market = GATE (label / features / dùng)

- **Ngày:** 2026-06-11
- **Trạng thái:** ⏳ ĐỀ XUẤT — ngã ba 1+2 đã chốt; còn quét H/X + feature-selection. Train ở P2 sau khi có data đầy đủ (ADR-0009 P1).
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
