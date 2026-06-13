# H1_GATE_SPEC — Spec export GATE (label + features) cho H1

> Cụ thể hoá ADR-0010 (market = gate) thành thứ EXPORT được. Quy trình kỷ luật (theo user):
> **(1) chốt LABEL → export label + validate RIÊNG → (2) từng FEATURE: tính + validate RIÊNG → (3) ghép → validate CHUNG → (4) hoàn chỉnh mới export FULL dataset.**
> Mỗi mảnh phải tự đứng vững trước khi nhập đống. Funding để sau (chưa chốt).

---

## §1. LABEL GATE — mô tả kỹ (CẦN CHỐT trước khi làm gì tiếp)

### 1.1 Bản chất (từ ADR-0010, không đổi)
Gate quyết tại thời điểm `t`: **có cho hệ MỞ long MỚI không + điều tiết mức** (chặn / bình thường / mạnh tay). KHÔNG chọn coin (funding lo). Label = **forward return thị trường trong H giờ tới, close-to-close**, phân 3 lớp. Đo TIMING ENTRY tại `t`, KHÔNG phải kết quả cả cụm DCA (cụm do DCA/breaker quản riêng).

### 1.2 Các điểm CẦN CHỐT (kèm đề xuất của tôi)

**[C1] "Forward return thị trường" = đo của ĐẠI LƯỢNG NÀO?** ADR nói scope rộng nhưng label phải là MỘT số.
- (A) **BTC** close-to-close — sạch, dẫn dắt, 1 chuỗi ổn định; nhưng bỏ lỡ cú alt sập khi BTC đứng yên (alt-season xả).
- (B) **Median forward return của universe alt còn sống** (`lifecycle.isAlive(t)`) — đo TRỰC TIẾP cái hệ long-only-alt thực sự chịu; nhiễu hơn BTC nhưng median đủ robust.
- (C) kết hợp BTC+ETH (đầu tàu).
- **✅ CHỐT (B): Median forward return của alt còn sống.** `alt` = universe USDT-perp TRỪ BTC; "còn sống tại [t,t+H]" = **có close tại CẢ t và t+H** (coin delist giữa khoảng tự loại; KHÔNG cần chờ lifecycle/010 — chỉ cần có-data). Dùng **median** (không mean) để robust với outlier. BTC/ETH vào FEATURE đầu tàu, không làm label.

**[C2] Ngưỡng 3 lớp — tuyệt đối hay phân vị? X giảm / Y tăng?**
- **Tuyệt đối** (giảm ≤ −X% / giữa / tăng ≥ +Y%): nghĩa rõ ("sập ≥15%"), khớp hành động gate (chỉ chặn khi nguy hiểm THẬT); nhược: imbalance + phụ thuộc H.
- **Phân vị** (tercile / p15 hai đuôi): cân bằng lớp, tự scale theo H; nhược: lúc thị trường yên, "giảm nhẹ vô hại" vẫn bị gán lớp giảm → **nhiễu nhãn**, sai mục đích gate.
- **✅ CHỐT: NGƯỠNG TUYỆT ĐỐI** cho lớp GIẢM (gate bắt SẬP thật) + **ngưỡng tăng `Y` RIÊNG, không đối xứng** X.
- **✅ scale theo H bằng vol-scaling √H** (return std ~ √thời gian): neo `X(24h) ∈ {−15%,−20%}` → `X(H) = X(24h)·√(H/24)`. Ví dụ neo −15%: 4h≈−6.1%, 12h≈−10.6%, 24h=−15%. `Y(H) = 0.6·|X(H)|` (nhỏ hơn vì tăng-mạnh hiếm hơn sập), quét quanh. **Các ngưỡng này là GRID quét ở H2, KHÔNG cứng ở H1** (xem 1.3–1.4).

**[C3] Tần suất sample `t` + chống chồng lấn (leakage):**
- Gate chạy mỗi phút live, nhưng label H=24h khiến mẫu mỗi-phút chồng lấn ~1440 lần → train sẽ "ăn gian". Đề xuất: **sample mỗi 15m** (thưa bớt) + **purged K-fold, embargo = H, sample-weight theo uniqueness** (López de Prado). Embargo BẮT BUỘC = H. **⬚ CHỐT bước sample: 15m? ___**

**[C4] Horizon H:** quét `{4H, 12H, 24H}` (ADR). Chọn cuối theo eval kinh tế + thắng rule, không chốt tay giờ. (Giữ nguyên.)

**[C5] Imbalance + cách ĐO:** lớp "giảm mạnh" thiểu số. Xử bằng class-weight (balanced), KHÔNG oversample mù. **Metric chính = precision/recall của LỚP GIẢM + lift vs base-rate**, TUYỆT ĐỐI không dùng accuracy tổng (lớp trung tính áp đảo → accuracy giả cao). Vế "tăng/mạnh tay" edge mỏng + chồng selector → đo vs rule, đừng kỳ vọng. (Giữ nguyên ADR.)

### 1.3 Công thức (đã chốt C1+C2)
```
# H1 EXPORT: chỉ RETURN THÔ (median alt còn sống), KHÔNG threshold cứng
retMktMedian(t,H) = median over {sym ∈ altUSDT, có close(t) & close(t+H)} của [close_sym(t+H)/close_sym(t) − 1]
# xuất cho mỗi H ∈ {4H,12H,24H} → 3 cột return thô + #coin tham gia median

# H2 (train) mới 3-class-hoá bằng ngưỡng (quét được mà KHÔNG re-export):
label = GIẢM nếu ret ≤ −X(H); TĂNG nếu ret ≥ +Y(H); else TRUNG_TÍNH
```
- ⚠️ **Tách "đo return" (H1, tốn) khỏi "chọn ngưỡng" (H2, rẻ):** H1 xuất return thô; threshold X(H)/Y(H) áp ở H2 để quét nhiều mà không export lại — đúng ranh giới 2-harness.
- Feature dùng `[.., t]`; return dùng `[t, t+H]` — guard look-ahead. close-to-close, KHÔNG max/min.

### 1.4 Export RETURN + validate RIÊNG (TASK-012 — làm ngay, KHÔNG chờ 009/010)
- Export `retMktMedian(t,H)` mọi `t` (sample 15m), mỗi H ∈ {4,12,24h} → file return thô (+ #coin tham gia median mỗi t — để biết độ tin).
- **Validate return (độc lập):** (a) phân bố return mỗi H (đuôi trái — kiểm có cú sập); (b) recompute-compare vài mốc bằng đường khác (median tính tay); (c) look-ahead: return chỉ chạm `[t,t+H]`, không dùng giá > t+H; (d) **cross-audit cú sập lớn** (LUNA 2022-05, FTT 2022-11) → return âm SÂU; (e) #coin median đủ lớn (universe-alive mỏng ở 2021 đầu → cảnh báo nếu <N coin). PASS mới sang features.
- (3-class hoá + phân bố lớp + imbalance: kiểm ở H2 khi áp threshold.)

---

## §2. FEATURES GATE — chi tiết (label đã PASS ở TASK-012; mỗi feature validate RIÊNG → ghép → full)

### Nguyên tắc (theo user)
Mỗi feature (hoặc nhóm cùng nguồn) export + **validate RIÊNG** trước; chỉ khi từng cái đứng vững mới ghép → validate CHUNG → export full. Mọi feature align `t` với `gate_return.csv` (cùng sample 15m). Feature chỉ dùng dữ liệu `[.., t]` (look-ahead clean).

### 2.1 Nhóm A — GIỮ từ bộ 34 (CÓ SẴN trong `MarketFeatures`/`ComprehensiveMarketFeatureExtractor` — chỉ export + validate, KHÔNG code mới)
| Feature | Nhóm | Ghi chú |
|---|---|---|
| momentum15M/1H/4H/24H | momentum BTC | bỏ 1M/5M (ADR tỉa) |
| volatility15M/1H/24H, volatilityTermStructure, volumeSpike | volatility | |
| volatilityRegime | volatility | **encode** string→ordinal/one-hot |
| advanceDeclineRatio, percentAboveMA20, volumeRatioUpDown, marketBreadthStrength, btcDominance | breadth | lõi gate |
| fundingRateRaw, fundingRateAvg24H, fundingRateTrend | funding | ⚠️ `fundingRateRaw` thực = basket-avg (ADR-0011) → **đổi tên** `basketFundingAvg` cho đúng nghĩa |
| basketVolSpike | basket | giữ 1 đại diện |

### 2.2 Nhóm B — CANDIDATE (CODE MỚI). Mỗi feature **1 đại diện**, importance tỉa ở H2. Hai khối: giá/xu-hướng (làm ngay) + crowdedness vĩ mô (một phần chờ 013).

#### B-giá/xu-hướng (LÀM NGAY — nguồn: kline_15m/4h_btceth TASK-009 + daily gom từ 4h)
| # | Feature | Công thức (đã chốt) |
|---|---|---|
| B1 | price-vs-SMA (BTC) | `close/SMA_n − 1` (TƯƠNG ĐỐI). 2 cột: **15m-SMA20** + **4h-SMA50**. |
| B2 | alignment ngắn-dài (bear-rally) | trendLong=sign(close_4h − SMA50_4h); momShort=sign(ret_15m N nến). `alignment = momShort×trendLong ∈ {−1,0,+1}` + cờ `bearRally = (trendLong<0 AND momShort>0)`. |
| B3 | regime MA200 (daily) | daily close BTC gom từ 4h. `distMA200 = close_daily/MA200_daily − 1`; `regime = sign(distMA200)` (bull/bear). Warmup 200 ngày (2021 đủ). |
| B4 | ETH momentum | `ethRet_15m`, `ethRet_4h` (2 khung đại diện, đối xứng BTC). H2 corr-check vs BTC → drop nếu >0.9. |
| B5 | đồng-pha BTC–ETH | `coDown = (btcRet_4h<0 AND ethRet_4h<0)`; `dispersion = |btcRet_4h − ethRet_4h|`; `rollingCorr` = corr(btcRet,ethRet) cửa sổ 24h trên 15m. |

#### B-crowdedness vĩ mô (user chốt thêm) — **AGGREGATE toàn thị trường = GATE** (KHÁC per-coin = selector ADR-0011)
| # | Feature | Công thức | Phụ thuộc |
|---|---|---|---|
| B7 | funding-breadth | từ `funding_data` hiện có (KHÔNG chỉ basket-avg): `pctFundingHigh` = % coin funding > ngưỡng cao (percentile lịch sử); `fundingDispersion` (độ tản funding cross-coin). Long-crowded diện rộng. | **LÀM NGAY** |
| B6 | OI-market | `oiMarketTotal` = Σ `sum_open_interest_value` toàn universe; `oiDelta24h` = Δ% 24h; `oiPriceDiverge` = OI tăng + giá ngang (đòn bẩy tích tụ). | **CHỜ 013** |
| B8 | LS-market | `lsGlobal` = agg `count_long_short_ratio`; `lsToptrader` = agg top-trader; `takerBuySell` = agg taker ratio. Một phía quá tải. | **CHỜ 013** |

⚠️ Crowdedness (funding/OI/LS) đều đo cùng khái niệm → dễ trùng. Giữ **ít đại diện**, H2 corr-check + importance tỉa mạnh. Aggregate cross-coin lúc tính phải GỒM coin backfill (không lọc DIED — như cảnh báo ở TASK-015).

### 2.3 BỎ
- GROUP 5 TIME (hourOfDay/dayOfWeek/weekOfMonth/monthOfYear) — mồi overfit (học "tháng 5 sập" vì LUNA).
- momentum1M, momentum5M (tỉa).
- Label cũ futureReturn15M / maxDrawdownNext4H — thay bằng `gate_return.csv` (TASK-012).
- (candidate khác trùng → tỉa bằng importance ở H2, KHÔNG bỏ tay; chỉ TIME bỏ chắc.)

### 2.4 Validate RIÊNG mỗi feature (trước khi ghép)
(a) range/phân bố (percentile; giá trị bất thường/clip?); (b) NaN/Inf→0 đúng (không lẫn 0 thật vs lỗi); (c) recompute mẫu bằng đường khác ~5 mốc; (d) look-ahead: chỉ dùng dữ liệu ≤ t (feature 15m/4h: nến đóng ≤ t); (e) align: mỗi `t` khớp `gate_return.csv`.

### 2.5 Ghép → validate CHUNG → export full
Sau khi MỌI feature PASS riêng: ghép 1 bảng (key `t`) → validate chung: correlation/dedup (drop trùng >0.95 — vd ETH-mom vs BTC-mom), leakage toàn bảng (không feature nào chạm tương lai), determinism (chạy 2 lần khớp), align đủ dòng với gate_return. → §3.

### 2.6 Thứ tự task cho CCD
1. **Nhóm A (sẵn-có)** — export + validate từng group. → **TASK-015**.
2. **Nhóm B giá/xu-hướng + funding-breadth (B1-B5, B7 — LÀM NGAY)** — code mới dùng 15m/4h + funding hiện có. → **TASK-017** (sau A).
3. **Nhóm B crowdedness OI/LS (B6, B8 — CHỜ 013)** — sau khi 013 verify+backfill xong. → TASK-018.
4. Ghép + full — sau khi A+B PASS (§3).

## §3. EXPORT FULL + VALIDATE CHUNG — (sau §1+§2)
Dataset versioned + fingerprint; validate 2 tầng (input tái dùng `validate_data` cải tiến + output recompute + cross-audit độc lập); statistical screen. **Chi tiết sau.**

---
Tham chiếu: ADR-0010 (gate), REBUILD_ROADMAP (H1/H2). Funding: ADR-0011 (chưa chốt — làm sau gate).
