# WFO/HPO — Thiết kế "mọi dữ liệu tĩnh, backtest không bật HistoryManager"

Ngày: 2026-06-30. Mục tiêu: WFO/HPO chạy mượt nhất — mọi dữ liệu động được export TĨNH từ trước,
backtest chỉ đọc, không tính live. Tài liệu này = (1) kết quả rà soát, (2) thiết kế static,
(3) phản biện hạn chế static, (4) kế hoạch validate.

## 1. Rà soát: trong đường WFO (SimulatorMarketLevelTicker1MStopLoss), cái gì còn "live"?

Dữ liệu sim tiêu thụ:
- kline 1m: qua smart-cache (đọc Aerospike-local 1 lần/ngày + nén CompactDayData). OK.
- market_data / ai_pred / funding_pred: ĐÃ nạp sẵn từ WfoDataset (offline). OK.
- **CoinRankManager tier/budgetMultiplier: CÒN LIVE** — đây là mảnh động duy nhất còn lại.
- funding fee: tắt khi HPO (APPLY_FUNDING_FEE=false). Không liên quan history.

Chuỗi phụ thuộc của mảnh live này:
```
sim line 642/659: CoinRankManager.getCoinTier / getBudgetMultiplier
    -> updateRanking(): HistoryManager.getSumVolume(symId, 720)  [tổng volume 12h]
        -> ring buffer nuôi bởi sim line 115: HistoryManager.updateHistoryArray(symbol2Ticker)
            -> đọc kline.totalUsdt
```

Xác nhận bằng grep toàn repo:
- `HistoryManager` trong sim: CHỈ line 115 (updateHistoryArray). Các getter (RSI/MA/return/...) KHÔNG
  gọi trong sim — chỉ tool export/validation dùng. Trong sim path, consumer ring buffer DUY NHẤT là
  CoinRankManager (qua getSumVolume).
- `totalUsdt` trong sim: chỉ qua CoinRank (sẽ thành tĩnh) + `Utils.isTickerAvailable` (fallback).

## 2. CoinRankManager — bản chất

- Xếp hạng coin theo **sumVol(720 phút)** giảm dần, tie-break tên A-Z; cập nhật mỗi **60 phút**
  (interval = time / 3_600_000). Top 20% = TIER_1, đáy 20% = TIER_3, giữa = TIER_2.
- tier -> budgetMultiplier: TIER_1=1.20, TIER_2=1.00, TIER_3=0.50 -> ảnh hưởng sizing -> ẢNH HƯỞNG PnL.
- Sim chỉ dùng `getCoinTier(symbolId,t)` + `getBudgetMultiplier(symbolId)` (KHÔNG dùng top50/getTopCoin).
- 720/60/20-80/tie-break là **HẰNG SỐ cố định**, KHÔNG nằm trong GENOME 18 gene
  (đã đối chiếu danh sách gene). => tier **BẤT BIẾN qua mọi gene, mọi sample, mọi window**.

Hệ quả: hiện tại mỗi backtest đều tái dựng ring buffer (updateHistoryArray mỗi phút × ~450 symbol) +
updateRanking mỗi giờ, dù kết quả tier y hệt nhau giữa các backtest. Đây là tính-lại-thừa thuần.
Trong smart-cache còn SAI vì CompactDayData bỏ totalUsdt (=0) -> sumVol=0 -> tier xếp theo alphabet.

## 3. Thiết kế static

### Artifact tĩnh
`coinTierStatic`: `Map<Long intervalKey, byte[symbolId -> tier]>`
- intervalKey = time / (60 * 60_000) (theo đúng công thức checkAndUpdate hiện tại).
- tier byte: 1=TIER_1, 2=TIER_2, 3=TIER_3. symbol không xếp hạng tại interval đó -> đọc về TIER_3
  (khớp getOrDefault hiện tại). top50 KHÔNG cần (sim không dùng).
- Kích thước: 5 năm × 24h ≈ 43.8k interval × ~450 byte ≈ ~20-40MB. Nhỏ.

### Export tool (Java = nguồn sự thật)
`ExportCoinTierStatic`:
- Driver mỏng: feed kline RAW (có totalUsdt thật, đọc readDataFromAerospike1M, KHÔNG qua CompactDayData)
  qua CHÍNH HistoryManager.updateHistoryArray + CoinRankManager.checkAndUpdate (live code path).
- Mỗi khi sang interval mới -> snapshot mảng symbolTiersShort -> ghi vào artifact theo intervalKey.
- Vì dùng đúng code live -> static == live BẰNG CẤU TRÚC (đây cũng là cách validate mạnh nhất).
- Output: file nén theo range (vd coin_tier_<start>_<end>.bin) trong WFO_DATA_DIR.

### Đọc + chế độ static trong CoinRankManager
- Thêm cờ `Configs.WFO_STATIC_RANK` (default false -> giữ nguyên hành vi cũ).
- static mode: `getCoinTier(symbolId,t)` = staticTier.get(t/3_600_000)[symbolId] (O(1), không cần
  HistoryManager). `getBudgetMultiplier` đọc từ đó. Loader nạp file 1 lần vào singleton lúc worker start.

### Sim
- static mode: BỎ `HistoryManager.updateHistoryArray` (line 115) hoàn toàn -> cắt overhead mỗi phút +
  cắt phụ thuộc totalUsdt của CoinRank.

## 4. PHẢN BIỆN — hạn chế / rủi ro của build tĩnh (quan trọng)

1. **Coupling tham số ranking với HPO**: an toàn HIỆN TẠI vì 720/60/ngưỡng KHÔNG phải gene. RỦI RO
   TƯƠNG LAI: nếu sau này đưa các tham số này vào GENOME để tối ưu thì data tĩnh (bake ở 1 cấu hình)
   không flex được — phải export lại theo từng cấu hình (vô nghĩa). => Chốt: chừng nào ranking params
   còn cố định thì static hợp lệ; nếu định tối ưu chúng, KHÔNG static phần đó.

2. **Leakage / nhân quả**: tier tại t dùng volume 720 phút TRƯỚC t (ring buffer ≤t). Là feature nhân
   quả, KHÔNG phải label, nên không có rò fold-boundary kiểu label. ĐIỀU KIỆN: export phải dùng đúng
   ring ≤t (đang đúng). Train và OOS đọc cùng artifact là OK vì giá trị tại t chỉ phụ thuộc ≤t.

3. **totalUsdt bị bỏ trong CompactDayData (=0)**: sau khi CoinRank thành tĩnh, consumer totalUsdt duy
   nhất còn lại là `Utils.isTickerAvailable` (`minPrice!=maxPrice || totalUsdt!=0`). Với smart-cache
   totalUsdt=0 -> isTickerAvailable rút về `minPrice!=maxPrice`. EDGE: nến giá phẳng nhưng có volume
   (minPrice==maxPrice & totalUsdt>0) -> data thật = available, smart-cache = unavailable. Hiếm (coin
   illiquid), nhưng là KHÁC BIỆT THẬT. Lựa chọn: (a) chấp nhận sau khi đo tác động, (b) thêm 1 bit
   "present" hoặc field thứ 5 vào CompactDayData. Cần ĐO trước khi quyết.

4. **Tính toàn vẹn / provenance**: artifact tĩnh là dữ liệu DẪN XUẤT từ (kline range + cấu hình ranking).
   Khi kline đổi (thêm coin/độ dài lịch sử) phải export lại. Phải gắn provenance (range + version ranking)
   để tránh dùng nhầm artifact cũ. Khớp nguyên tắc "Java là nguồn sự thật, model/data luôn match code".

5. **Active universe**: ranking chỉ xếp các symbol "active" tại interval (có nến). Export tĩnh phải dùng
   ĐÚNG định nghĩa active. Vì cả export lẫn smart-cache đều dựng từ cùng kline -> tập active khớp.

6. **⚠️ COLD-START RING vs CONTINUOUS (điểm quan trọng nhất — đã xác minh)**: `backtest()` gọi
   `HistoryManager.resetCache()` + `CoinRankManager.resetCache()` ở ĐẦU MỖI backtest. Nghĩa là live
   hiện tại tính tier trên ring **cold-start tại đầu mỗi window/phase**: 720 phút (12h) đầu mỗi
   backtest, ring chưa đầy -> tier méo (xếp hạng trên <12h volume). Sau 12h ring đầy = giống continuous.
   - Hệ quả: tier(t) live KHÔNG phải hàm của riêng t — nó phụ thuộc (điểm bắt đầu backtest, t). Cùng một
     mốc t xuất hiện trong train của nhiều window (train 12m trượt 3m -> chồng lấn) sẽ có tier cold-start
     KHÁC nhau tuỳ window. => 1 artifact tĩnh keyed theo t KHÔNG tái tạo đúng 100% behavior cold-start.
   - 2 lối:
     (A) **Static CONTINUOUS** (ring ấm liên tục, keyed theo t, window-independent): sạch, đúng nghĩa
         "volume 12h trailing", leak-safe (chỉ dùng ≤t; tier chỉ để sizing budget, KHÔNG phải feature
         model nên không nhiễm train/OOS). NHƯNG đổi PnL ở ~12h đầu mỗi backtest so với live cold-start.
     (B) **Static per-window cold-start** (reset ring tại trainStart và oosStart): tái tạo đúng live,
         validate khớp tuyệt đối — nhưng artifact phải keyed theo (window, phase), phức tạp, phải nạp
         lại theo từng job/phase. Khác biệt A vs B chỉ ở 12h đầu mỗi backtest.
   - Đề xuất: chọn (A) vì đúng tinh thần "tĩnh như các data khác" + sạch + leak-safe; nhưng vì ĐỔI PnL
     nên ĐO chênh lệch (A vs live cold-start) rồi để Uni quyết, KHÔNG tự ý đổi behavior.

7. **⚠️ TIMING CẬP NHẬT RANKING bị vướng logic lệnh (đã xác minh)**: live `checkAndUpdate` chỉ chạy
   `updateRanking` khi được gọi ĐÚNG phút-0 của giờ (`(t/60000)%60==0 && intervalKey>last`). Mà nó chỉ
   được gọi trong `createOrderBUY` (qua getCoinTier), SAU nhiều cổng reject (is50%Loss, predict==null,
   ablation, breaker). => giờ nào không có lệnh nào lọt tới dòng getCoinTier tại phút-0 thì ranking KHÔNG
   cập nhật giờ đó (giữ tier giờ trước tới lần gọi phút-0 kế). Tức timing ranking live VƯỚNG vào tín hiệu/
   gene/cổng — KHÔNG thuần "mỗi giờ", và do đó tier KHÔNG hoàn toàn gene-invariant như tưởng.
   - Static (export) cập nhật ĐỀU mỗi giờ -> SẠCH, xác định, thực sự gene-invariant. Nhưng KHÁC live ở
     các giờ mà live bỏ lỡ cập nhật. Đây là điểm thứ 2 (cùng cold/warm ở #6) khiến static "đúng hơn"
     nhưng đổi PnL vs hành vi hiện tại.
   - Theo tinh thần Uni ("build tĩnh ổn định, toàn vẹn, chất lượng tốt hơn"): chọn static sạch, rồi ĐO
     delta PnL (static vs live hiện tại) trình Uni ký duyệt — KHÔNG khẳng định khớp tuyệt đối.

### Kết luận phản biện
Ngoài (1) là ràng buộc thiết kế (đừng đưa ranking params vào gene) và (3) là edge cần đo, build tĩnh
KHÔNG có blocker. Lợi ích: ổn định (không tính-lại-thừa, không lệ thuộc thứ tự), validate được từng
phần nhỏ (so tier static vs live theo từng interval), và loại hẳn rủi ro sai im lặng kiểu totalUsdt=0.

## 5. Kế hoạch validate (ĐO delta, KHÔNG giả định khớp tuyệt đối)

Vì #6 (cold/warm) + #7 (timing update) khiến static "sạch hơn nhưng KHÁC" live, validate = ĐO delta:
1. A (tham chiếu): FILE-MODE (totalUsdt thật) + CoinRank LIVE hiện tại -> PnL_live.
2. B: FILE-MODE + CoinRank STATIC (updateHistoryArray off) -> PnL_static. Đo |B - A| (delta do cold/warm
   + timing). Trình Uni quyết static có chấp nhận được không.
3. C: SMART-CACHE + CoinRank STATIC -> PnL. So C vs B = tác động riêng totalUsdt=0 (edge flat-candle #3).
   Lượng hoá để quyết (a) chấp nhận hay (b) thêm bit present vào CompactDayData.
4. Sau khi Uni duyệt static: PnL_static (B hoặc C) thành tham chiếu mới cho mọi tối ưu tốc độ tiếp theo.

## 6. Trạng thái triển khai
- [x] Configs.WFO_STATIC_RANK (env WFO_STATIC_RANK=1)
- [x] CoinRankManager static mode: loadStaticTier + loadIntervalFromStatic (floorEntry) + exportCurrentTierBytes
      + nhánh static trong checkAndUpdate (bỏ HistoryManager khi static)
- [x] Sim: gate bỏ updateHistoryArray khi WFO_STATIC_RANK
- [x] ExportCoinTierStatic (export CONTINUOUS + load) — dùng đúng read path + HistoryManager + CoinRank live
- [x] WfoWorker: env WFO_STATIC_RANK + WFO_COINTIER_FILE (nạp tier 1 lần vào singleton)
- [x] Build local OK (compile sạch)
- [ ] Deploy jar Oracle + chạy ExportCoinTierStatic sinh file tier (range data đầy đủ)
- [ ] Validate ĐO delta: A (live) vs B (static file-mode) vs C (static smart-cache) -> trình Uni duyệt
- [ ] (sau khi duyệt) đo lại PROFILE static: sim giờ bỏ updateHistoryArray -> phần simulate giảm bao nhiêu
