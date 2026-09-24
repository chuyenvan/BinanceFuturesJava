# RESEARCH: SL / EXIT TÙY BIẾN THEO SELECTOR (symbolPred) & S1 RANK

Phiên RECON + DESIGN (chỉ đọc + phân tích). KHÔNG chạy sim, KHÔNG sửa code logic.
Repo: BinanceFuturesJava, branch `module`. Sim nghiên cứu:
`SimulatorMarketLevelTicker1MStopLoss` + `OrderTargetInfoTest`.

## 1. TÓM TẮT
- Duong TRAILING gap ĐÃ tùy biến theo symbolPred/rank (STRONG/WEAK cap; X3 rank-cap).
- Cái CÒN FIX CỨNG theo hằng số ("theo D"): (a) TIME-STOP, (b) HARD SL %, (c) ngưỡng ARM.
- symbolPred (Float) VÀ selRank (Integer) CÓ SẴN trên object cụm tại MỌI đường exit của sim
  => thiết kế tùy biến các mục trên là KHẢ THI, phần lớn config-only + sửa nhỏ nhánh exit.

## 2. RECON — CƠ CHẾ EXIT/SL HIỆN TẠI (file:dòng + hằng số)

| Cơ chế | File:dòng | Hằng số / key | Ghi chú |
|---|---|---|---|
| Trailing gap cap (STRONG) | Configs.java:140 | `TS_MAX_GAP=0.08` (SIM_TS_MAX_GAP) | gap tối đa khi mạnh |
| Trailing gap cap (WEAK) | Configs.java:141 | `TS_MAX_GAP_WEAK=0.03` (SIM_TS_MAX_GAP_WEAK) | gap khi yếu |
| Giveback ratio | Configs.java:173 | `TS_GIVEBACK_RATIO=0.5` | gap=min(peak*0.5, cap) |
| Ngưỡng ARM (sim) | Configs.java:169 | `RATE_PROFIT_STOP_MARKET=0.03` | arm SL khi maxRate>=3% |
| Ngưỡng ARM (live C3) | LiveProfileC3.java:38 | `ARM_RATE=0.07` | chỉ sổ giây C3 |
| Bản lề STRONG/WEAK theo symbolPred | Configs.java:173 | `TS_PNOPUMP_WEAK_THR=0.29` | symbolPred>0.29 => WEAK |
| Trailing cap theo RANK (X3) | Configs.java:421 | `TS_CAP_STRONG_RANK=0` (off) | selRank<=N => STRONG |
| TIME-STOP 168h (live/C3) | LiveProfileC3.java:39 | `TIME_STOP_HOURS=168` | CHỈ live C3 + BOTM:544; sim KHÔNG có |
| LOSER TIME-STOP (sim) | Configs.java:389; Sim:682-687 | `LOSER_TIME_STOP_HOURS=0` | cắt phẳng cụm chưa arm sau N giờ |
| COND EXIT (F2, sim) | Configs.java:~394; Sim:697-704 | `COND_EXIT_HOURS=0`,`COND_EXIT_MIN_FAV=0` | cắt có điều kiện MFE<min |
| PRE-ARM HARD SL (X2, sim) | Configs.java:405; Sim:663-676 | `PRE_ARM_SL=0f` | hard SL % trên firstEntryPrice |
| Chọn cap trailing | TradeUtils.java:28 (pNoPump), :55 (rank) | — | trailFromCap dùng chung |
| trailRate (sim) | OrderTargetInfoTest.java:366 | dùng this.symbolPred / this.selRank | X3 rank khi cap>0 |

### 2.1 "SL theo D" = fix cứng ở đâu (không phụ thuộc symbolPred/rank)
Các đường THỜI GIAN + HARD SL đều dùng HẰNG SỐ đơn (giờ hoặc %), không đọc symbolPred/rank:
- TIME-STOP 168h: `LiveProfileC3.TIME_STOP_HOURS=168` (LiveProfileC3.java:39), áp ở
  ShadowBookC3.java:258 và BinanceOrderTradingManager.java:544. Sim NGHIÊN CỨU KHÔNG dùng.
- LOSER_TIME_STOP_HOURS (Sim:682-687): `time - anchor > N*3600000` — N là hằng số.
- COND_EXIT_HOURS (Sim:697-704): tương tự, hằng số giờ + ngưỡng MFE hằng số.
- PRE_ARM_SL (Sim:663-676): `firstEntryPrice*(1+PRE_ARM_SL)` — % hard SL hằng số.
- Ngưỡng ARM: `RATE_PROFIT_STOP_MARKET=0.03` (sim) — hằng số, quyết định cụm nào được đặt SL.

Đường ĐÃ tùy biến (không cần thêm gì): trailing gap cap qua `calRateLossDynamicBuyPNoPump`
(theo symbolPred vs 0.29) và X3 `calRateLossDynamicBuyRank` (theo selRank vs TS_CAP_STRONG_RANK).

## 3. FEASIBILITY — symbolPred & S1 rank có sẵn ở exit?
CÓ (sim). Cụ thể trên `OrderTargetInfoTest`:
- `public Float symbolPred;` (dòng 101) — set ở createOrder:1035, chép sang cụm ở mergeOrder:859
  (clusterSymbolPred). Fix B1 đảm bảo cụm mang đúng symbolPred.
- `public Integer selRank;` (dòng 106) — set ở createOrder:1039, chép sang cụm ở mergeOrder:865
  (clusterSelRank). null với leg DCA/BIG_DOWN (không qua selector).
Cả hai đọc được ở TẤT CẢ nhánh exit (updateStatusNew/trailRate, PRE_ARM_SL, LOSER_TIME_STOP,
COND_EXIT) vì đều thao tác trên `orderMulti` (chính object cụm). => KHÔNG cần plumbing lưu thêm.

Feasibility phía LIVE (tham khảo, KHÔNG ưu tiên phiên này):
- ShadowBookC3.Pos: có `symbolPred` (dòng 61) + `rank` (ctor:67) => shadow C3 khả thi tương tự.
- BinanceOrderTradingManager (live thật): trailing tra pNoPump per-coin lúc tick (BOTM:490)
  nhưng KHÔNG lưu selRank per-position => time-stop/SL theo rank ở live thật CẦN plumbing.

## 4. ĐỀ XUẤT (≤3) — ưu tiên đổi ít, default = byte-identical, đo được trên DEV 2021

Nguyên tắc chung: mọi key mới default = TẮT (giữ hằng số hiện tại) => khi tắt IEEE-exact,
không đổi số lệnh/gate, chỉ chạm ĐƯỜNG EXIT, KHÔNG đụng entry/gate/sizing.

### ĐỀ XUẤT B (ƯU TIÊN 1) — TIME-STOP tùy biến theo rank/symbolPred
- Biến điều khiển: `selRank` (chính) hoặc `symbolPred` (phụ, khi selRank==null).
- Công thức: `hours = (selRank != null && selRank <= RANK_N) ? HOURS_STRONG : HOURS_WEAK`
  với HOURS_STRONG > HOURS_WEAK (coin tin cậy cao giữ lâu hơn; coin điểm thấp cắt sớm).
  Áp vào NHÁNH LOSER_TIME_STOP (Sim:682-687) — cụm CHƯA arm (priceSL==null).
- Key config MỚI: `SIM_LOSER_TS_HOURS_STRONG`, `SIM_LOSER_TS_HOURS_WEAK`, `SIM_LOSER_TS_RANK_N`.
  Default: cả hai = `SIM_LOSER_TIME_STOP_HOURS` hiện tại (key mới trống) => byte-identical.
- Phạm vi: chỉ nhánh time-stop trong Sim + Configs (đọc key). KHÔNG đụng entry/gate.
- Kỳ vọng (collapse-risk / T170): cụm điểm thấp là nguồn tail-loss/zombie chính; cắt sớm giảm
  đuôi trái; cụm điểm cao được leash dài tránh cắt oan winner => cải thiện phân phối T170.
- Độ khó: CONFIG-ONLY + sửa nhỏ 1 nhánh (chọn hours theo selRank). KHẢ THI NGAY.

### ĐỀ XUẤT A (ƯU TIÊN 2) — HARD SL % (PRE_ARM_SL) tùy biến theo rank/symbolPred
- Biến điều khiển: `selRank` (fallback symbolPred khi null).
- Công thức: `preArmSl = (selRank <= RANK_N) ? SL_STRONG : SL_WEAK`, với |SL_STRONG| > |SL_WEAK|
  (coin tin cậy cao chịu drawdown sâu hơn trước hard-cut; coin điểm thấp cắt chặt).
- Key config MỚI: `SIM_PRE_ARM_SL_STRONG`, `SIM_PRE_ARM_SL_WEAK`, `SIM_PRE_ARM_SL_RANK_N`.
  Default: cả hai = `SIM_PRE_ARM_SL` hiện tại (0=off) => byte-identical khi tắt.
- Phạm vi: `PreArmSlUtils` (hiện `hit(firstEntryPrice, minPrice)` chỉ nhận giá) + call-site Sim:663.
  Cần TRUYỀN selRank vào PreArmSlUtils => sửa chữ ký hàm (light plumbing, có unit test sẵn).
- Kỳ vọng: hard SL là chốt chặn tail-loss; nới cho coin tin cậy giảm cắt oan, siết coin điểm thấp
  giảm biên độ thua mỗi lệnh xấu => giảm collapse-risk.
- Độ khó: CONFIG + LIGHT PLUMBING (đổi chữ ký PreArmSlUtils truyền selRank). Sim-only, exit-only.

### ĐỀ XUẤT C (ƯU TIÊN 3) — Ngưỡng ARM tùy biến theo symbolPred/rank
- Biến điều khiển: `symbolPred`/`selRank`.
- Công thức: `armRate = (selRank <= RANK_N) ? ARM_STRONG : ARM_WEAK` thay `RATE_PROFIT_STOP_MARKET`
  ở cổng profit-arm (Sim:708). Coin tin cậy cao arm muộn (nuôi xa) / thấp arm sớm (chốt nhanh).
- Key config MỚI: `SIM_ARM_RATE_STRONG`, `SIM_ARM_RATE_WEAK`, `SIM_ARM_RATE_RANK_N`.
  Default: cả hai = `RATE_PROFIT_STOP_MARKET` => byte-identical.
- Phạm vi: cổng arm Sim:708-709 (maxPrice>=entry*(1+armRate)). Vẫn exit-side (quyết định đặt SL),
  nhưng GẦN entry hơn 2 đề xuất trên => rủi ro tương tác cao hơn, ưu tiên thấp.
- Độ khó: CONFIG + sửa điều kiện cổng arm. Cần audit kỹ vì đổi cụm nào được arm.

## 5. KHUYẾN NGHỊ CHẠY TRƯỚC
Chạy ĐỀ XUẤT B trước: đổi ít nhất, biến có sẵn, default byte-identical, tác động trực tiếp lên
nguồn collapse-risk (loser/zombie chưa arm), đo sạch trên DEV mở rộng 2021 bằng sweep
(RANK_N × HOURS_STRONG/WEAK). Sau đó A, rồi C.
