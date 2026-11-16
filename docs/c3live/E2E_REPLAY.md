# E2E_REPLAY — kiểm thử end-to-end lớp thực thi v1.2 (c3_live) trên NGÀY SẬP 2026-10-30

- **Ngày chốt:** 2026-11-05 (+07). Viết + commit **TRƯỚC** khi viết code harness và trước khi chạy bất kỳ replay nào.
  Sau khi thấy số: không đổi dữ liệu vào, mô hình khớp, tiêu chí, ngưỡng. Đổi = ADDENDUM có ngày, ghi viết trước/sau khi thấy số.
- **Đối tượng:** code production nhánh `v1.2/c3-live` HEAD `33a81398` (gồm 4n `1f505414` = jar dry r4n, ops `f451ee38`, 4o-B).
  Harness chỉ nằm trong `src/test/**` + `tools/e2e/**`; **KHÔNG sửa code production**. Bug production ⇒ báo (file:dòng, kịch bản), không sửa.
- **An toàn:** worktree `~/claude_master/v12/e2e_wt`, `PrivateConfig` STUB, `config.properties` không host 242 (chỉ local,
  skip-worktree, không commit), `LIVE_IS_SHADOW_HOST=true` cho mọi mvn/java, không Aerospike/Redis/REST/WS thật, không ghi 242.
  Chạy qua `flock ~/claude_master/locks/oracle_heavy.lock nice -n 10`, `-Xmx2g -T 1`, kiểm free ≥ 4000 MB, đĩa ≥ 15G.

## 1. Câu hỏi
Trên dữ liệu thật của ngày sập 10-30 (2 đợt: 03:30–04:00 và 06:00–09:10 +07), jar v1.2 (r4n) ở lớp thực thi có: vào lệnh đủ và
đúng khi gate burst nhiều symbol, DCA, arm +7 % → STOP_MARKET closePosition, dời stop, kill-switch C1–C6/A40, đối soát,
LEGACY-busy/MERGED, chịu tải rate — không mồ côi, không exception, sổ = sàn — kể cả khi tiêm lỗi?

## 2. Dữ liệu vào (cố định)
| thành phần | nguồn | ghi chú |
|---|---|---|
| cửa sổ | `START = 2026-10-29 07:00 +07` (1793232000000) → `END = 2026-11-01 07:00 +07` (1793491200000) | 3 ngày UTC 10-29..10-31; đồng hồ giả |
| giá 1m | Binance Vision `~/claude_master/parity_v11w/vision/klines_1m/<D>/<S>.zip` (đã có, không tải thêm) | chỉ symbol xuất hiện trong ứng viên + BIG_DOWN + BTCUSDT |
| ứng viên selector mỗi phút | `sel_dump` live 242 (top-24: ts, symbol, selectorScore, rank, gateValue, p15) từ `~/claude_master/pull242/2026-10-2{9}..31/dumps` | p15/gateValue = giá trị live (shadow v1.1); xem §6 giới hạn |
| buffer gate | `pull242/2026-10-31/run/gate_ratio_live.bin.gz` (live) | khởi tạo = bản ghi `ts < START`; phần `[START, END)` chỉ dùng cho E2a |
| BIG_DOWN | dòng `[SHADOW] would-BUY … market level: BIG_DOWN` trong `full.log` pull242 cùng cửa sổ | nhánh không qua gate rolling, đưa thẳng vào đường lệnh |
| exchangeInfo | `~/claude_master/v12/fixtures/exchangeInfo_20261027_1140.json.gz` (fixture R5) | SymbolRules + universe A1 (TradFiClassifier.universeA1, fail-closed như `UniverseA1Filter`) |
| held (đối chứng E2b) | `~/claude_master/gst1030/shadow_events.txt` | quy ước `gst_l.py`/R4h |

## 3. Mô hình (cái gì là production THẬT, cái gì giả)
- **Tầng quyết định (production thật):** mỗi phút `GatePreFilter.runSelector(pool, 24, a1Excluded, legacy, held, …)` →
  `AIRejectFilter.entryGate(AiPredictionData(ts, p15), gateValue, true, bookFull)` → `LiveGateRollingRatio` (pct 0,999950829,
  90 ngày, persist file tạm) — đúng vòng mà `DetectEntrySignal2TradeNormal` gọi. `held` = `GatePreFilter.heldPredicate(C3_LIVE_BOOK)`
  đọc **sổ c3 của chính harness** (vòng kín: thoát lệnh làm đổi held). `bookFull` = U ≥ U_MAX theo sổ c3 (như `GATE_QUOTA_SKIP_WHEN_FULL`).
  PASS ⇒ `C3LiveEntry.onLeg` như `C3LiveHook.onLeg` (ref = close nến quyết định, sizing = giá khớp dự kiến, tierMul = 1, tier3 = false).
- **DCA:** mỗi phút như `C3LiveHook.dcaDue`: `book.gridStates()` × `DcaUtils.shouldDcaGrid(first, close, legCount)` ⇒ leg `DCA_LEVEL1`.
- **Lớp thực thi (production thật, nối dây y `C3LiveRuntime`/`MainAccountRig`):** LiveBookC3, C3Scope, C3ScopedGateway (policy
  `ProductionRatePolicy`), C3StreamScope, FillAccounting, C3LiveOrderExecutor (+FillPriceResolver), Reconciler (qty), OwnStopGuard,
  C3LiveFlattener, TrailingStopManager (CLOSE_POSITION, arm 0,07), C3StopProtector, C3MergedGuard, C3LegacyRefresher, C3MainEquity
  (vốn 10 000), KillSwitchEngine ACT (params = `OpsConfig.killSwitchParams(true)` + file tạm), UserStream (F1).
  Khác runtime: đồng hồ giả, executor đồng bộ (`Runnable::run`), nhịp ops 5 s / exit mỗi nhịp giá (15 s) thay 10 s.
- **Sàn giả `FakeExchange1m`** (mở rộng `MockExchangeGateway`, test): mỗi phút 4 nhịp giá O→(H,L theo chiều nến)→C
  (+15/+30/+45/+60 s); MARKET mua khớp tại open nến kế tiếp (lệnh quyết định ≈ +66 s); STOP SELL kích khi giá nhịp ≤ stopPrice,
  khớp tại giá nhịp (bi quan); phí taker 0,05 %; sự kiện user-stream ORDER_TRADE_UPDATE/ACCOUNT_UPDATE/ALGO_UPDATE; vị thế về 0 ⇒
  sàn tự EXPIRE stop closePosition (mặc định cùng lô sự kiện; F4: +4 ms, lô riêng). Giá stop = giá nhịp (không có MARK riêng).
- **Chế độ DRY (phụ):** cùng nối dây nhưng sàn = `DryGateway` production (mua khớp tại ref, stop kích qua `onPrices`) — đúng thứ
  242 dry đang chạy.

## 4. Lượt chạy
| id | held | universe | sàn | lỗi tiêm |
|---|---|---|---|---|
| E2a | ∅ (như live v1.1: chỉ vị thế thật) | v1.1 (không A1) | — (chỉ tầng quyết định) | — |
| E2b | shadow_events (quy ước R4h) | v1.1 | — | — |
| R0 | sổ c3 harness | A1 | FakeExchange1m | không |
| R0-DRY | sổ c3 harness | A1 | DryGateway | không |
| F1 | như R0 | A1 | Fake | user stream rớt 03:40:00–03:52:00 +07 10-30 |
| F2 | như R0 | A1 | Fake | 429 (`RATE_LIMIT`) 3 lệnh MARKET liên tiếp + 2 lần đặt stop trong phút burst đầu đợt 1; F2b: 6 lần liên tiếp |
| F3 | như R0 | A1 | Fake | ACK FILLED thiếu avgPrice (cả cửa sổ) |
| F4 | như R0 | A1 | Fake | EXPIRE stop closePosition đến +4 ms sau fill đóng (lô riêng) |
| F5 | như R0 | A1 | Fake | LEGACY giữ 2 symbol PASS đầu tiên của đợt 1 (trước START) + bot LEGACY mua 1 symbol c3 đang giữ (MERGED) |
| F6 | như R0 | A1 | Fake | (a) DD giả: income FUNDING_FEE −4 500 USDT trên 1 symbol c3 lúc 10-30 10:00 +07; (b) C1: ngừng cấp nến BTC 5′ lúc 10-30 12:00 +07 |

## 5. Tiêu chí ĐẠT (tất cả cố định trước)
**Tiền đề D0:** `GateHeldReplay1030R4hTest` PASS trên worktree (q giờ 04 = 0,00756445155; đợt 2 mới = 8 symbol).

**Tầng quyết định**
- **E2a (bám buffer live):** r harness nạp trong `[START, END)` = bản ghi buffer live cùng khoảng, so như multiset (ts, bit float):
  khớp ≥ 99,9 %, lệch chỉ được giải thích bằng phút thiếu sel_dump/skipFull (liệt kê). Không đạt ⇒ dừng, không chấm R0.
- **E2b (neo MASTER):** q giờ 04 10-30 = 0,00756445155 (|Δ| ≤ 1e-9 tương đối) và tập symbol mới đợt 2 (04:00–11:00) = {CAP, CT, DOS, IDOL,
  IRYS, NIL, PARTI, Q}.
- **E1 (R0 ≡ REF độc lập):** `tools/e2e/check_ref.py` dựng lại bằng numpy (không dùng Java) từ cùng đầu vào + cờ held/legacy/a1/bookFull
  trong trace: q mỗi giờ (|Δ| ≤ 1e-9 tương đối) và tập PASS (phút, symbol) **trùng 100 %**; mỗi PASS có đúng 1 lần gọi `onLeg`.
  "Số lệnh/symbol khớp OFF-BT-A1": tập lệnh R0 = tập PASS REF trừ từ chối hợp lệ (X1). Báo kèm (không ngưỡng) so shadow v1.1 (26+2).

**Lớp thực thi (R0, R0-DRY, F1–F6 đều phải giữ X2–X8 trừ khi mục F ghi khác)**
- **X1 vào lệnh:** mọi PASS (không held/LEGACY/A1) ⇒ `SUBMITTED`, ngoại trừ outcome hợp lệ {U_MAX, BUDGET_SMALL, SIZING, HOLDING,
  DCA_*, KS_BLOCKED khi có latch hợp lệ}; mỗi trường hợp liệt kê lý do. `ERROR/BAD_INPUT/NO_RULES/MODE_GUARD/RESERVE_FAIL/NO_EQUITY/
  BOOK_UNHEALTHY/RECON_BLOCKED/NOT_BUYABLE` = 0 (NOT_BUYABLE chỉ chấp nhận nếu REF cũng loại theo A1).
- **X2 khớp một lần:** mỗi cid c3 MUA xuất hiện trên sàn ≤ 1 lệnh; leg SUBMITTED ⇒ sổ xác nhận qty = qty sàn (BigDecimal bằng) và
  giá = giá khớp sàn (|Δ|/giá ≤ 1e-9); không leg treo PENDING/SENDING/UNKNOWN quá 60 s (giả) sau ACK.
- **X3 arm + stop:** cụm có giá nhịp > VWAP·1,07 ⇒ ARM; trong ≤ 61 s (giả) có đúng 1 STOP_MARKET SELL c3 closePosition mở trên
  sàn, stopPrice = round-down(priceSL, tick) ≤ giá hiện tại. Từ đó tới khi đóng: tại mọi nhịp có đúng 1 stop c3 mở (cho phép 2 trong
  đúng bước thay đặt-rồi-huỷ), không khoảng trống > 61 s.
- **X4 dời stop:** stopPrice chỉ tăng; mỗi lần dời ≥ 1 tick và ≥ 0,1 %.
- **X5 không mồ côi:** mỗi nhịp kiểm (sau ân hạn 61 s): vị thế c3 trên sàn ⇔ cụm mở trong sổ; stop c3 mở chỉ ở symbol có vị thế > 0;
  cuối cửa sổ: 0 stop c3 trên symbol phẳng.
- **X6 đối soát:** cuối cửa sổ và mỗi giờ: qty sổ = qty c3 sàn từng symbol (bằng tuyệt đối); realized sổ vs Σrp sàn và phí sổ vs Σphí
  sàn: |Δ| ≤ 1e-6·max(1,|x|); `Reconciler` không chặn (`allowsEntry` true cho mọi symbol) trừ F5/F6 khi chặn có lý do ghi trong log.
- **X7 0 exception:** 0 sự kiện log mức ERROR từ `com.binance.chuyennd.c3live.*`/`ops.*`, 0 Throwable thoát ra harness. F1–F6: ERROR chỉ
  chấp nhận nếu chính lỗi tiêm sinh ra và được liệt kê trong kỳ vọng.
- **X8 kill-switch:** R0/R0-DRY: 0 latch, hoặc latch C2 chỉ khi có ≥ 3 lệnh trượt bất lợi > 2,5 % trong 24h (đếm độc lập từ fill vs ref) — báo.
- **X9 rate:** weight REST c3 mỗi phút giả (bảng weight `C3LiveClient` W_*) ≤ 600 (`ownCap` ProductionRatePolicy); lệnh/10 s ≤ 150
  (½ giới hạn 300). Báo đỉnh phút burst.
- **X10 DCA:** mỗi lần `shouldDcaGrid` đúng cho cụm đang giữ ⇒ leg DCA SUBMITTED (hoặc từ chối hợp lệ X1); DCA khớp ⇒ arm reset
  (stop cũ huỷ) như `TrailingStopManager` mục 5. Không có DCA tự nhiên ⇒ ghi "KHÔNG XẢY RA" + kịch bản tổng hợp S-DCA (giá −mức grid
  trên 1 symbol của R0) phải đạt.

**Kỳ vọng lỗi tiêm**
- **F1 WS rớt:** mọi leg khớp trong khoảng rớt được sổ xác nhận qua REST (resolve/reconcile) ≤ 60 s sau khớp; stop vẫn đặt cho cụm arm;
  sau nối lại không cộng trùng (X6); fallback REST chạy (≥ 1 lần/khoảng); 0 vị thế lạ.
- **F2 429:** 429 trên MARKET ⇒ leg huỷ giữ chỗ (lỗi chắc chắn không khớp), KHÔNG gửi lại cùng quyết định, không cid trùng; F2 (3 lỗi):
  không latch C3; F2b (6 lỗi liên tiếp): latch C3 (NO_NEW_ENTRY) rồi tự gỡ sau ≥ 30′ sạch + ≥ 3 call OK; 429 trên stop ⇒ stop được đặt ở
  nhịp sau hoặc `C3StopProtector` đóng cụm ≤ 61 s — không cụm arm nào trần > 61 s.
- **F3 thiếu avgPrice:** giá vào sổ = giá khớp sàn (X2) qua stream/userTrades; không C2 giả; không leg UNKNOWN treo.
- **F4 EXPIRE +4 ms:** không đặt lại stop trên symbol phẳng, không cảnh báo vị thế lạ/UNKNOWN, không ERROR, X5/X6 giữ.
- **F5 LEGACY/MERGED:** 2 symbol LEGACY: đếm hạng + nạp r nhưng outcome `LEGACY`, 0 lệnh c3 trên symbol đó, hạng 25 không thế chỗ;
  symbol MERGED: `C3MergedGuard` gắn MERGED, stop chuyển qty reduceOnly = qty c3, thoát c3 chỉ bán qty c3; cuối: vị thế sàn = qty LEGACY
  (bằng tuyệt đối), LEGACY khác không bị lệnh c3 nào chạm.
- **F6a DD:** latch FLATTEN (C6 hoặc A40) ≤ 11′ sau tiêm; mọi cụm c3 đóng ≤ 2′ sau latch; 0 stop c3 mở sau đó; 0 SUBMITTED sau latch
  (outcome KS_BLOCKED); LEGACY không bị chạm (chỉ F5 có LEGACY; F6 chạy không LEGACY). **F6b C1:** latch C1 ≤ 5′ sau khi ngừng nến BTC;
  leg trong latch = KS_BLOCKED; tự gỡ sau ≥ 30′ sạch; sau gỡ vào lệnh lại bình thường.

**Kết luận:** ĐẠT = D0, E2a, E2b, E1 và mọi X/F đạt. Mục nào trượt ⇒ TRƯỢT mục đó, phân loại: (i) bug production (bằng chứng
file:dòng + kịch bản tái hiện), (ii) giới hạn harness (§6), (iii) dữ liệu. Không sửa tiêu chí sau khi thấy số.

## 6. Giới hạn đã biết (khai trước)
1. p15/gateValue lấy từ sel_dump live v1.1 (đặc trưng có TradFi), KHÔNG phải OFF-BT-A1 tính lại từ Vision: OFF-BT-A1 của ngày UTC 10-29
   (chứa cả 2 đợt sập theo +07) chưa dựng trong parity_v12 (chỉ R5 ngày UTC 10-30). Sai lệch p15 live↔offline đo ở parity (P1).
2. sel_dump chỉ có top-24 ⇒ khi A1 bỏ symbol TradFi khỏi top-24, hạng 25+ không quan sát được ⇒ R0 có thể thiếu tối đa (số ô TradFi
   trong top-24 ở phút PASS) leg so với A1 thật — đếm và báo.
3. Giá stop = giá nến 1m nội suy 4 nhịp (không MARK, không sổ lệnh) ⇒ thời điểm/giá thoát xấp xỉ; không đo PnL.
4. Executor đồng bộ, không đa luồng ⇒ không bắt race luồng (race đã có test riêng A1R4e).
5. tierMul = 1 (CoinRankManager cần Aerospike) ⇒ size có thể khác live ở coin tier ≠ 1.
6. DRY/Fake không có -2019/thanh lý/ADL/funding thật (trừ F6a).

## 7. Đầu ra
`src/test/java/com/binance/chuyennd/c3live/e2e/replay/*` (harness, JUnit bỏ qua nếu thiếu dữ liệu), `tools/e2e/prep_fixture.py`,
`tools/e2e/check_ref.py`, kết quả `~/claude_master/e2e1105/out/<run>/{trace_dec.csv.gz,outcomes.csv,events.csv,result.json}` và
`docs/c3live/E2E_REPLAY_RESULT.md` (bảng tiêu chí ĐẠT/TRƯỢT).
