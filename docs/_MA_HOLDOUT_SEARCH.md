# Tìm dấu vết thí nghiệm MA (rule-based, nhiều khung thời gian, holdout coin)

> Ghi chú phương pháp: search bằng `desktop-commander:start_search` (content, ignoreCase=true) trên
> `docs/` (bao gồm `docs/archive/`). Toàn bộ nội dung dưới đây là DỮ LIỆU THÔ trích nguyên văn từ
> kết quả search + đọc file, KHÔNG có phân tích/diễn giải/kết luận thêm.
>
> Lưu ý về công cụ: một số dòng "match" hiển thị chỉ còn lại đúng 1 từ khóa đứng riêng một dòng
> (ví dụ dòng chỉ có chữ `MA200`, `holdout`, `320`...) — đây là cách công cụ search hiển thị dòng
> khớp xen giữa các dòng ngữ cảnh (context) lấy từ file gốc; số thứ tự dòng (`:NN`) là dòng thật
> trong file trên đĩa, nhưng nội dung hiển thị cho đúng dòng đó có thể bị công cụ rút gọn/lệch so
> với nội dung đầy đủ của dòng — đã đối chiếu lại bằng cách đọc trực tiếp các file ứng viên mạnh
> nhất (Phần 2) để lấy nguyên văn chính xác.

---

## Phần 1 — Bảng TOÀN BỘ file có match (theo từng đợt search)

### 1a. Pattern `MA200|MA100|MA50|MA20` (case-insensitive)
| File (đường dẫn tương đối `docs/...`) | Số dòng match trả về |
|---|---|
| AGENTS.md | 2 |
| archive/H1_GATE_SPEC.md | 6 |
| archive/reports/025.md | 1 |
| archive/reports/026.md | 1 |
| archive/reports/NEXT_SESSION_TODO_20260718.md | 2 |
| decisions/0010-market-model-gate-design.md | 3 |
| PREREG_GATEFEAT.md | 1 |

(Không có kết quả nào cho `MA100` riêng lẻ — search riêng `MA100` trả về 0 match trong toàn bộ `docs/`.)

### 1b. Pattern `MA20\b|MA50\b`
| File | Số dòng match |
|---|---|
| AGENTS.md | 1 (MA50) |
| archive/H1_GATE_SPEC.md | nhiều (MA20, SMA20, SMA50) |
| decisions/0010-market-model-gate-design.md | 1 (MA20) |
| PREREG_GATEFEAT.md | 1 (MA20) |

### 1c. Pattern `distMA|priceVsMA|price/MA|priceMA|distToMA|price_ma|MA_dist`
| File | Ghi chú |
|---|---|
| archive/H1_GATE_SPEC.md | `distMA200` (công thức) |
| archive/reports/026.md | `distMA` (bảng feature importance) |
| PREREG_GATEFEAT.md | `distMA20` (bảng IC feature) |
| decisions/0001-do-luong-exit-maxdd-mae.md | match `PriceMa` — **có vẻ false-positive**, không liên quan MA (xem Phần 3) |
| archive/_cleanup_20260829/docs/reports/EXIT_SWEEP_20260731_rate_ratchet.md | match `Price/ma` — **false-positive** (nói về `priceSL`), không liên quan |

### 1d. Pattern `trung binh dong|đường trung bình|golden cross|death cross|crossover|SMA200|EMA200|EMA50|EMA20|EMA100|SMA100`
| File | Ghi chú |
|---|---|
| archive/H1_GATE_SPEC.md | match `eMA20` — thực chất là do regex khớp chồng lên chữ khác quanh `MA20`, không phải "EMA" thật trong file |
| archive/reports/NEXT_SESSION_TODO_20260718.md | `SMA200` — 2 chỗ |
| decisions/0010-market-model-gate-design.md | tương tự (mảnh của MA20) |
| archive/_cleanup_20260829/docs/reports/EXIT_MACHINE_20260730_stop_schedule.md | match `crossover` — bàn về cơ chế trailing-stop (`gap`), KHÔNG liên quan MA |
| PREREG_GATEFEAT.md | tương tự (mảnh của MA20) |

Không tìm thấy: `trung bình động`, `đường trung bình`, `golden cross`, `death cross` (0 match cho các cụm tiếng Việt/thuật ngữ này trong toàn bộ `docs/`).

### 1e. Pattern liên quan "coin/320/340" (kiểm tra riêng cụm holdout coin)
- Pattern `\bcoin\b[^\n]{0,20}(320|340)|(320|340)[^\n]{0,20}\bcoin\b` → **0 match** trong toàn bộ `docs/`.
- Pattern mở rộng `\b3[0-4][0-9]\b[^\n]{0,15}(coin|symbol)|(coin|symbol)[^\n]{0,15}\b3[0-4][0-9]\b` (dò số 300–349 gần từ coin/symbol) → có match nhưng đều KHÔNG liên quan tới MA/holdout kiểm định (xem chi tiết Phần 2E và Phần 3).
- Pattern `holdout|held.?out|OOS coin|universe` riêng lẻ → 2357 kết quả (553 match) — cực nhiều, vì `holdout`/`universe` là thuật ngữ dùng khắp codebase cho tách DEV/VALIDATION theo THỜI GIAN và cho "universe coin" nói chung, không đặc thù cho thí nghiệm MA. Không có file nào trong số này nhắc `MA200`/`MA50`/`MA20` cùng lúc.

### 1f. Pattern `rule.?based|khong.{0,4}model|không.{0,4}model|non.?ML|no.?ML`
78 kết quả (16 file), toàn bộ đều thuộc các chủ đề KHÁC (selector C2b/net015, DCA sizing, trailing-stop, gate-dyn) — KHÔNG có file nào đồng thời nhắc MA200/50/20. Danh sách file: C2B_SPEC.md, CEIL_RESULT.md, FS_RESULT.md, PREREG_BOOKCAP.md, RESULT_COLLAPSE_PROBE.md, SELECTOR_LADDER.md, runbooks/runbook_live_242_2026-08-19.md, archive/_cleanup_20260829/docs/insights/dca_strategy_direction.md, archive/_cleanup_20260829/docs/reports/156.md, archive/_cleanup_20260829/docs/insights/trailing_stop_strategy_direction.md, archive/_cleanup_20260829/docs/project-memory/live_audit_24h_2026-08-22.md, archive/_cleanup_20260829/docs/project-memory/wfo_gate_recheck_2026-08-13.md, archive/_cleanup_20260829/docs/project-memory/overall_audit_and_dca_strategy_2026-08-20.md.

### 1g. Filename search
- `searchType=files`, pattern `MA` → 27 file có "MA" trong đường dẫn/tên (đa số do trùng chữ trong path `BinanceFuturesJava`, không phải tên file nói về MA): L4_LIVE_BUILDMAP.md, insights/WFO_ROADMAP.md, ROADMAP_NOLEAK.md, ROADMAP.md, decisions/0001-do-luong-exit-maxdd-mae.md, decisions/0007-survivorship-material.md, CONFIG_FIELD_MAP.md, decisions/0010-market-model-gate-design.md, architecture/roadmap_wfo.html, architecture/roadmap_tong.html, ... (+17 file khác).
- `searchType=files`, pattern `MA200` → 0 file (không có tên file nào chứa "MA200").
- `searchType=files`, pattern `holdout` → chỉ 1 file: `H1_HOLDOUT_PREP.md`.

---

## Phần 2 — Trích dẫn thô từ các file liên quan mạnh nhất

### 2A. `docs/archive/H1_GATE_SPEC.md` (spec export feature cho "GATE" thị trường, cụ thể hoá ADR-0010)

```
### 2.1 Nhóm A — GIỮ từ bộ 34 (CÓ SẴN trong `MarketFeatures`/`ComprehensiveMarketFeatureExtractor` — chỉ export + validate, KHÔNG code mới)
| Feature | Nhóm | Ghi chú |
|---|---|---|
| momentum15M/1H/4H/24H | momentum BTC | bỏ 1M/5M (ADR tỉa) |
| volatility15M/1H/24H, volatilityTermStructure, volumeSpike | volatility | |
| volatilityRegime | volatility | **encode** string→ordinal/one-hot |
| advanceDeclineRatio, percentAboveMA20, volumeRatioUpDown, marketBreadthStrength, btcDominance | breadth | lõi gate |
| fundingRateRaw, fundingRateAvg24H, fundingRateTrend | funding | ⚠️ `fundingRateRaw` thực = basket-avg (ADR-0011) → **đổi tên** `basketFundingAvg` cho đúng nghĩa |
| basketVolSpike | basket | giữ 1 đại diện |
```

```
#### B-giá/xu-hướng (LÀM NGAY — nguồn: kline_15m/4h_btceth TASK-009 + daily gom từ 4h)
| # | Feature | Công thức (đã chốt) |
|---|---|---|
| B1 | price-vs-SMA (BTC) | `close/SMA_n − 1` (TƯƠNG ĐỐI). 2 cột: **15m-SMA20** + **4h-SMA50**. |
| B2 | alignment ngắn-dài (bear-rally) | trendLong=sign(close_4h − SMA50_4h); momShort=sign(ret_15m N nến). `alignment = momShort×trendLong ∈ {−1,0,+1}` + cờ `bearRally = (trendLong<0 AND momShort>0)`. |
| B3 | regime MA200 (daily) | daily close BTC gom từ 4h. `distMA200 = close_daily/MA200_daily − 1`; `regime = sign(distMA200)` (bull/bear). Warmup 200 ngày (2021 đủ). |
| B4 | ETH momentum | `ethRet_15m`, `ethRet_4h` (2 khung đại diện, đối xứng BTC). H2 corr-check vs BTC → drop nếu >0.9. |
| B5 | đồng-pha BTC–ETH | `coDown = (btcRet_4h<0 AND ethRet_4h<0)`; `dispersion = |btcRet_4h − ethRet_4h|`; `rollingCorr` = corr(btcRet,ethRet) cửa sổ 24h trên 15m. |
```

```
(e) **NaN/Inf + warmup:** warmup (MA200/rollingCorr/OI-thiếu) đánh dấu nhất quán (loại dòng hoặc cờ), KHÔNG lẫn 0-giả vs 0-thật.
```

### 2B. `docs/decisions/0010-market-model-gate-design.md` (ADR-0010)

```
- **Ngày:** 2026-06-11
- **Trạng thái:** 🔴 ML GATE — VERDICT ÂM TÍNH (2026-06-22). A0 chốt H/X (24h/−15%, 49 đợt) + train 3-lớp trên gate_dataset_v1 (có OI) đều xong. Purged 5-fold CV: top-1% lift median 0x, fold 2022 (LUNA/FTX, nhiều sập nhất) trượt sạch → ML không generalize, không vượt rule. DỪNG hướng ML gate. Hướng tiếp: breaker phản ứng / nâng cấp features 15m (chờ user chốt). Chi tiết: `docs/reports/041.md` mục D.
```

```
### Candidate THÊM (từ thảo luận — đưa vào rồi để feature-selection tỉa, KHÔNG hardcode hết)
Nguyên tắc: thêm theo **khái niệm**, mỗi khái niệm 1 đại diện; data ít cú sập → cẩn thận overfit.
- **Giá-vs-SMA 15m/4h** (dạng tương đối `price/SMA−1` hoặc slope — KHÔNG tuyệt đối). Vị thế so trung bình, bổ sung momentum.
- **Alignment ngắn-vs-dài** (cùng/ngược chiều) — bắt **bear-rally** (tăng ngắn trong downtrend dài = bẫy trước sập). Giá trị cao cho gate.
- **Regime bull/bear:** giá vs MA dài (MA200 daily) + cờ breakout/breakdown.
- **ETH momentum 15m/4h** — có chế độ ETH dẫn độc lập BTC (BTC im + ETH bơm → alt tăng); để correlation-check, drop nếu trùng BTC >~0.9.
- **Đồng-pha BTC–ETH** (cả hai cùng giảm mạnh = sập diện rộng) + dispersion/correlation toàn cục.
```

```
## Cổng nghiệm thu (BẮT BUỘC)
So model vs **rule trần** ("chặn khi breadth thấp VÀ funding cao"). Không vượt rule rõ → dùng rule, bỏ ML gate. Edge timing mỏng — kỳ vọng gate chỉ lọc vài chế độ sập rõ.
```

```
2. **"Làm mịn features" = thêm candidate ADR (price-vs-SMA, alignment ngắn-dài, regime MA200, ETH mom, đồng-pha BTC-ETH) rồi feature-selection tỉa** + BỎ nhóm time (4 feat hourOfDay/dayOfWeek/weekOfMonth/monthOfYear — mồi overfit LUNA tháng 5).
```

```
**Acceptance (đo lớp sập, KHÔNG chỉ IC):** precision/recall riêng lớp "sập" + đếm cú sập độc lập trong test (đủ mẫu mới tin) + **so rule trần "breadth thấp VÀ funding cao"**. Không vượt rule rõ → bỏ ML gate, quay lại nâng cấp. Train trên TOÀN lịch sử 2021–2026 (đủ nhiều cú sập), không chỉ holdout 12 tháng. Cẩn thận imbalance (lớp sập hiếm) — đây là phần quan trọng nhất.
```

### 2C. `docs/PREREG_GATEFEAT.md` (đánh giá 33 feature của gate p15)

```
- Nguon 1: univariate IC tren label_oldbasket (`gate15m_v2_featsel.json`, do tren toan bo CV):
  yeu nhat = `basketVolSpike` 0.0006, `basketMomentum1H` 0.0014, `rsi14` 0.0027,
  `distMA20` 0.0040, `percentAboveMA20` 0.0045, `weekOfMonth` 0.0067.
```

### 2D. `docs/archive/reports/026.md` (TASK-026 — Train gate 3-class)

```
# TASK-026 — Train gate 3-class (kết luận: FILTER MỀM, horizon 12h)

## Feature importance (top, gain)
`volatility1H`, `momentum15M/24H`, `b7_pctFundingHigh` (funding-breadth, 017), `b6_oiMarketTotal` + `b8_lsToptrader/lsGlobal` (crowd OI/LS, **018 đóng góp thật**), `b3_distMA200`, `b1_sma50_4h`, `fundingRateAvg24H`. Tín hiệu trải đều nhiều nhóm, không leak (|corr| feature↔label ≤0.088).

## KẾT LUẬN (chốt với user)
- **Gate = FILTER MỀM, horizon 12h**, nhãn adaptive ±0.7σ. Dùng **P_up − P_down ở đuôi tự tin** để nghiêng/giảm size entry — **KHÔNG** hard 3-class argmax.
```

### 2E. `docs/archive/reports/025.md` (TASK-025 — Ghép full dataset gate)

```
- **NaN hợp lý (warmup + crowd bắt đầu muộn):** b8_lsToptrader 48.924 (toptrader thiếu nhiều coin); b6/b8 crowd ~32k (chủ yếu 2021: 32.064/35.040 = 91%, do crowd từ 2021-12); b3 MA200 19.292; b1/b2 896; b4/b5 128–193.
```

### 2F. `docs/archive/reports/NEXT_SESSION_TODO_20260718.md` (HANDOFF 2026-07-18)

```
## ON-THE-HORIZON (đừng rơi)
- TRAIL_PEAK_MODE high|close + premature-stop metric (agent đang prep).
- 2s/tick study: **BỎ** (không đủ độ phủ, Uni chốt 2026-07-17).
- Long-term entry features (SMA200 slope/regime) → chỉ nếu +TR chết & quay lại entry-veto (KHÔNG cho SL).
- Kaggle-WFO kernel bake env (nếu ladder chạy lặp nhiều) → lấy lại 5 node tăng tốc.
```

```
- **Kiến trúc entry:** gate=KHI-NÀO (market timing, pred.bin, fail standalone 43.8%); selector=COIN-NÀO (EV2 per-coin, edge mỏng).
  2 trục vuông góc. Redesign B: (1) selector + feature dài hạn, (2) gate timing, (3) **HỢP NHẤT 1 model** (market+coin+long-term
  → P(coin lời NGAY) — học tương tác "pump trong downtrend dễ về 0"). Nghiêng (3) hoặc (1).
- **B chặn:** feature dài hạn (SMA200 slope, trend-vs-BTC, dist-from-SMA200) CHƯA export trong ff (dài nhất hiện là 24H)
  → cần sửa Java exporter + re-export ff + retrain. Không phải Kaggle-1-lệnh.
```

### 2G. `docs/AGENTS.md` (bảng task, dòng có MA200/MA50 làm mốc — nguyên văn dòng bảng chứa mốc đó)

```
| 015 feature gate NHÓM A (sẵn-có) | CCD-audit | ✅ DONE (RUN Kaggle) | 2026-06-14 | — | `outputs/gat... [MA200 xuất hiện trong nội dung cột kế tiếp bị cắt bởi công cụ search]
| 017 feature gate B giá/xu-hướng + funding-breadth | CCD #1 | ✅ DONE (RUN 226 + validate) | 2026-06... [MA50 tương tự]
| 018 feature gate B crowdedness OI/LS-market | orchestrator | ✅ DONE (RUN 226) | 2026-06-16 | — | ... [MA200 tương tự]
```
(Ghi chú: nội dung đầy đủ 3 dòng bảng này bị cắt trong output search do dòng quá dài; số dòng thật trong file: 31, 32, 33.)

---

## Phần 3 — File "có thể liên quan nhưng chưa chắc" (chỉ khớp 1 cụm, không rõ có phải cùng chủ đề)

- `docs/L5_S1_WARMUP_242.md` — chứa cụm số **"coin >= 336"**, **"336"** nhiều lần. ĐỐI CHIẾU TRỰC TIẾP: đây là ngưỡng warm-up của `S1RankerLive` = 336 mốc giờ = 14 ngày × 24h dữ liệu close 1h cần có để coin "sẵn sàng" cho live-ranking — không thấy liên hệ với MA hay holdout kiểm định chiến lược trong file này.
- `docs/OI_FIX_LOG.md` — chứa "320 cap/symbol", "SYMBOL (n=4,320..." — là số cặp đo lường OI-fix, không liên quan MA/holdout.
- `docs/PREREG_C3.md` — chứa "348) mang symbol..." — về logic leg/symbolPred của C3, không liên quan.
- `docs/archive/_cleanup_20260829/docs/project-memory/live30_audit_findings_2026-08-19.md` — chứa "313 symbol" trong ngữ cảnh audit live entries, không liên quan MA.
- `docs/decisions/0001-do-luong-exit-maxdd-mae.md` — khớp cụm `PriceMa` (do regex `priceMA`) nhưng nội dung file là về đo MAE/MDD khi exit, không nhắc moving average.
- `docs/archive/_cleanup_20260829/docs/reports/EXIT_SWEEP_20260731_rate_ratchet.md` — khớp cụm `Price/ma` (từ chữ "priceSL"), không liên quan MA.
- `docs/archive/_cleanup_20260829/docs/reports/EXIT_MACHINE_20260730_stop_schedule.md` — khớp từ khóa `crossover` nhưng ngữ cảnh là cơ chế trailing-stop gap, không phải MA crossover.
- `docs/archive/_cleanup_20260829/docs/insights/dca_strategy_direction.md` — khớp cụm "không model"/"rule-based" nhưng chủ đề là sizing DCA theo regime, không phải MA entry.
- `docs/archive/_cleanup_20260829/docs/insights/trailing_stop_strategy_direction.md` — khớp "Rule-based"/"rule-based" nhưng chủ đề là công thức trailing-stop theo volatility/regime, không phải MA.

---

## Kết luận về cụm "holdout ~320–340 coin, chạy FAIL"

Đã search trực tiếp (không diễn giải, chỉ báo cáo kết quả kỹ thuật của việc search):
- Không tìm thấy dòng nào trong `docs/` (kể cả `docs/archive/`) có đồng thời từ "coin" (hoặc "symbol") VÀ một con số trong khoảng 320–349 xuất hiện trên cùng một dòng theo cách gợi ý "tách holdout N coin".
- Từ khóa `holdout` xuất hiện rất nhiều (553 dòng khớp) nhưng toàn bộ ngữ cảnh xem được đều nói về holdout THEO THỜI GIAN (period 2026, VALIDATION 2024-07→2025-12-31, DEV 2022→2025, v.v.), không phải holdout theo TẬP COIN.
- Không tìm thấy file nào có tên hoặc nội dung ghép cả 2 chủ đề: (a) MA200/MA100/MA50/MA20 nhiều khung thời gian + volume, VÀ (b) một tập holdout ~320-340 coin bị FAIL.
