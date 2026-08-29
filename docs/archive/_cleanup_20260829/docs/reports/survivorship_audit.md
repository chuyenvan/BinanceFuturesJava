# Survivorship audit — TASK-132 PHA 1 (ĐO thuần, không backfill)

- **Ngày đo:** 2026-07-05 (CCD opus)
- **Phạm vi:** PHA 1 = ĐẾM + ước lượng ảnh hưởng. KHÔNG backfill (PHA 2 → NEEDS_HUMAN).
- **Nguồn số:** `outputs/aerospike_coverage.csv` + `outputs/survivorship_missing_symbols.csv` (TASK-001/002,
  snapshot 2026-06-09), manifest WFO ` /d/claudedata/ccd128/manifest.txt` (export 2026-07-02),
  và listing Binance data.vision crawl LIVE hôm nay (HTTP 200, KHÔNG geo-block).

---

## 0. TÓM TẮT 1 DÒNG

Gap survivorship = **~39 coin crypto delisted** (LUNA/FTT/RAY/SRM/WAVES/DODO/ANC/AUDIO…) vẫn thiếu khỏi
universe dataset — **không đổi** so với đo TASK-001. `market.bin` KHÔNG đếm được symbol (nó là chuỗi feature
market-level, không có chiều symbol). Ảnh hưởng: material nhưng đã được định lượng GIÁN TIẾP (golden CRASH
+5507 = lãi giả) và backfill đã bị HOÃN có chủ đích (ADR-0007[C]/ADR-0009). Đo trực tiếp mức méo feature cần
chạy `SurvivorshipFeatureCheck` trên 242/226 → **PHA 2, NEEDS_HUMAN**.

---

## 1. SurvivorshipBac0 / SurvivorshipFeatureCheck LÀM GÌ (đọc code)

| Tool | Làm gì | Đã enumerate universe lịch sử thật (gồm delisted)? |
|---|---|---|
| `SurvivorshipBac0.java` | Java thuần. Liệt kê universe từ data.vision S3 (2021→nay, phân trang) TRỪ ticker1m coverage → tập USDT-perp thiếu hoàn toàn; tải klines từng coin thiếu đo drawdown/died/QV; cổng quyết. | **CÓ.** Nó chính là tool enumerate universe lịch sử thật (kể cả coin đã về 0). |
| `SurvivorshipFeatureCheck.java` | Read-only. Tại ~8 mốc (quanh LUNA 2022-05, FTT 2022-11 + mốc thường), tính lại feature market-level (`MarketBigChangeDetector.calMarketData`: rateDownAvg/rateUpAvg/rateDown15MAvg) theo 2 cấu hình: GỒM vs LOẠI 30 core coin die → % khác biệt. | **KHÔNG** enumerate universe. Nó ĐO mức survivorship *méo feature* — đúng lớp mà `market.bin` chứa. Cần Aerospike 242 (`getClient242`). |

→ Hai tool đã tồn tại và ĐÃ enumerate + đã có công cụ đo méo feature. PHA 1 hôm nay = tái xác nhận số + refresh.

---

## 2. PHÁT HIỆN CHÍNH: `market.bin` KHÔNG CÓ CHIỀU SYMBOL

Câu hỏi task ("đếm bao nhiêu symbol trong market.bin") dựa trên giả định sai về cấu trúc dataset WFO.

`WfoDataset.java` (dòng 25, 134-143): `market.bin = [count:int]` rồi `count × [ts:long][3 float:
down,up,down15m]`. Tức là `TreeMap<Long, MarketDataObject>` — **chuỗi thời gian feature market-level đã tổng
hợp**, mỗi entry = 1 mốc phút với 3 số (rateDownAvg/rateUpAvg/rateDown15MAvg). **Không có symbol nào lưu trong
market.bin.**

Bằng chứng manifest (`/d/claudedata/ccd128/manifest.txt`):
```
marketCount=2804363          ← ĐẾM MỐC PHÚT, không phải symbol
marketRange=1609459200000..1778646900000   ← 2021-01-01 → 2026-05-13 UTC
md5_market=65ac483da50558d1328d4bc8543aba76 (khớp wfo_data_validation_20260704.md ✅)
```

⇒ **Không thể đếm symbol từ market.bin.** Survivorship trong WFO không nằm ở "thiếu dòng symbol" mà nằm CHÌM
trong (a) feature market-level đã tổng hợp trên universe-còn-sống mỗi thời điểm, và (b) pred.bin/funding.bin
xếp hạng universe. Lớp symbol nằm ở **ticker1m coverage** (nguồn tính ra các feature này), không ở market.bin.

---

## 3. ĐẾM SYMBOL — universe lịch sử vs trong dataset

Bộ lọc chung (như `keep()`): đuôi `USDT`, không `_`, không `USDC`, không `BTCDOMUSDT`.

| Đại lượng | Số | Nguồn |
|---|---:|---|
| Universe USDT-perp TỪNG tồn tại (data.vision) — snapshot 2026-06-09 | **730** | ADR-0007 / TASK-001 |
| Universe USDT-perp TỪNG tồn tại — **crawl LIVE 2026-07-05** | **788** | data.vision (đã verify) |
| Symbol trong dataset (ticker1m coverage, nền của WFO) — snapshot 2026-06-09 | **711** | `aerospike_coverage.csv` (711/750 sau lọc) |
| Thiếu hoàn toàn (universe 2026-06-09 − coverage) | **39** | TASK-001 |
| Thiếu hoàn toàn (universe LIVE 788 − coverage 711) | 78 (thô) | crawl hôm nay |

### ⚠️ Bẫy đo — 78 KHÔNG PHẢI 78 coin delisted
Chênh 78 − 39 = **+39 symbol MỚI** xuất hiện trong universe giữa 09/06 → 05/07. Phân loại 40 symbol
new-missing (78−38 cũ có klines):

- **39/40 là perp cổ phiếu/ETF token-hóa MỚI NIÊM YẾT** (Binance mở 2025-26): ADBE, ASML, NFLX, GME, COST,
  EBAY, CRWD, SMCI, RIVN, KLAC, LRCX, AMAT, SONY, ZM, HIMS, DKNG, TQQQ, SQQQ, UVXY, IWM, XLE, EWZ, URNM… →
  **KHÔNG phải coin chết** mà là instrument MỚI, thiếu chỉ vì coverage snapshot (09/06) chưa quét chúng.
- **1/40 là crypto delisted thật:** `LENDUSDT` (Aave LEND cũ) — trước không có monthly klines, nay có.

→ **Gap survivorship THẬT (coin crypto delisted) = ~39, KHÔNG ĐỔI.** Báo cáo 78 là sai lệch. Các perp cổ phiếu
mới còn nằm NGOÀI cửa sổ WFO (dataset kết thúc 2026-05-13) nên không ảnh hưởng backtest hiện tại.

### Chênh lệch = coin delisted thiếu
**39 symbol crypto USDT-perp delisted** thiếu khỏi universe dataset (38 có klines ở snapshot cũ; +LENDUSDT nay
có klines; trong đó 2 là rác meme `我踏马来了USDT`, `龙虾USDT` → ~37 coin thật).

---

## 4. ĐO ĐẶC TÍNH TẬP THIẾU (từ survivorship_missing_symbols.csv, 38 coin có klines)

- **drawdown trung bình = −60.9%**; **12/38 diedNearZero** (close cuối < 10% max).
- Top sập: LUNAUSDT −99.7%, ANCUSDT −99.7%, DODOUSDT −98.1%, RAYUSDT −97.6%, FTTUSDT −97.1%, AUDIOUSDT
  −96.2%, DGBUSDT −95.7%, GALUSDT −94.8%, SRMUSDT −89.7%, ANTUSDT −88.5%, WAVESUSDT −80.6%.
- **Không phải mẫu ngẫu nhiên** — 100% là coin đã chết/bị bỏ. 30 trong số này là `CORE30` trong
  `SurvivorshipFeatureCheck`.

---

## 5. ƯỚC LƯỢNG ẢNH HƯỞNG

**Định tính (nặng):** bot long-only + DCA-nhồi-loser + KHÔNG hard-SL (martingale). Coin về-0 = kịch bản kích
hoạt tail-risk tệ nhất; thiếu chúng ⇒ backtest NÉ đúng cú sập ⇒ PnL/maxDD/worstSingleLoss LẠC QUAN GIẢ. 39
coin ≈ 5.3% universe nhưng là 100% đuôi tệ.

**Định lượng gián tiếp (đã có, ADR-0007):** golden CRASH `20220401→20221231` (đúng thời LUNA/FTT sập) cho PnL
**+5507**, maxDD chỉ **−6286**, numTrades ~785/tháng (≈39% mật độ Recent). "Crash tệ nhất lịch sử lại lãi" =
artifact THIẾU coin chết + universe 2022 nhỏ. Đây là bằng chứng số cho mức phồng.

**Định lượng trực tiếp (méo feature market.bin):** = output của `SurvivorshipFeatureCheck` (GỒM vs LOẠI CORE30
tại 8 mốc). **CHƯA chạy trong PHA 1** (cần đọc Aerospike 242/226 — vượt hàng rào "không đụng compute nặng"). →
đẩy sang PHA 2.

---

## 6. KẾT LUẬN PHA 1

1. `market.bin` = feature market-level, **không đếm được symbol**; lớp symbol nằm ở ticker1m coverage.
2. Gap survivorship = **~39 coin crypto delisted** (đã xác nhận lại, không đổi so 09/06). Tăng universe
   730→788 hôm nay là **perp cổ phiếu/ETF mới**, KHÔNG phải delisted → không được tính vào survivorship.
3. Ảnh hưởng: **material** (100% đuôi chết, dd TB −60.9%, 12 died-near-zero, khớp chiến lược no-SL), nhưng đã
   được định lượng gián tiếp đủ mạnh và backfill đã HOÃN có chủ đích (ADR-0007[C]/ADR-0009): sim đọc node 242
   không phải 226; entry rank theo PREDICTION không theo ticker (backfill ticker đơn lẻ ⇒ ΔPnL=0); funding fee
   đang tắt.

---

## 7. ⏭️ PHA 2 — NEEDS_HUMAN (Uni duyệt)

Backfill 38-39 coin chết vào dataset là **việc nặng, đụng data pipeline + node tiền-thật 242**. Trước khi
backfill, việc rẻ nên làm là **chạy `SurvivorshipFeatureCheck`** (read-only 242) để có con số méo-feature trực
tiếp — nhưng vẫn cần Uni duyệt vì chạm Aerospike compute. Trọn gói backfill (nếu duyệt): tải ticker 38 coin +
GEN lại market+funding prediction 2022 (inference lịch sử nặng, trần ADR-0005) + bật `updateFundingFee` + ghi
242 → chạy lại golden CRASH so `baseline-CRASH` → diff = survivorship định lượng. **KHÔNG tự làm trong task này.**

*Crawl data.vision hôm nay: HTTP 200, KHÔNG geo-block (không PENDING).*
