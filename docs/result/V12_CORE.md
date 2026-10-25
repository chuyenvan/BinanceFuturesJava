# V12_CORE — vòng 2a: nối đường lệnh THẬT c3_live (C1, C3, C8 hành động, C12 adapter, U3 market level)

Branch tích hợp `v1.2/c3-live` (worktree `~/claude_master/v12/c3live`) từ `16de49a6` + merge `v1.2/safe` (51a668cc) + `v1.2/lib` (262449e0).
Agent v12core (Claude Opus), 2026-10-25. Không push, không merge sang branch khác, không deploy, không gọi Binance, không đụng 242.

## 0. Risk-first (đọc trước)

1. **CHƯA ĐƯỢC BẬT `LIVE_ADAPTER=live` với tiền thật sau vòng này.** Vị thế c3_live mở ra **chưa có đường thoát**: trailing STOP_MARKET
   sau arm, time-stop 168h, X14 đều là vòng 2b (C6). `TsMktExt.decideEnabled` còn TẮT ở c3_live (`!profileLive`). Hiện chỉ FLATTEN
   (kill-switch) đóng được cụm thật. `LIVE_ADAPTER=dry` thì an toàn (không mạng).
2. **Chưa có reconcile (C9) và kế toán fill qua user-data stream (C7).** Sổ thật chỉ biết fill qua response RESULT / `queryOrder`;
   phí, fill muộn, vị thế bị sàn đóng (thanh lý/stop kích) chưa về sổ. Stop mồ côi chỉ được dọn khi cụm đóng qua `C3LiveFlattener`.
3. **C4 giữ latch (MASTER 10-25)**: C4 = `U ≥ U_MAX` tính trên sổ thật/totalMarginBalance. Khi sập mạnh equity giảm ⇒ U có thể chạm
   0,60 ⇒ latch NO_NEW_ENTRY **tới khi owner reset** (chặn cả DCA) ⇒ lệch sim ở đúng lúc crash-buy cần DCA. Spec GOLIVE §5.2 ghi C4 "tự nhả";
   tôi làm đúng quyết định MASTER — đề nghị MASTER xem lại C4.
4. **Feature thị trường của gate (LiveFeaturePipeline / cross-sectional funding / MarketDataInline) CHƯA loại TradFi** ở c3_live — chỉ
   market level (rateDown/Up/15M) và ALT_EW (bộ lọc sẵn, TsMktExt đang tắt ở c3_live). Đổi input model khi chưa có sim (P1) — để MASTER quyết.
5. Executor 1 luồng **chờ cửa sổ an toàn 10 s** khi timeout (trước `queryOrder`) ⇒ trong đợt 24 leg nếu sàn chập chờn, các leg sau trễ
   thêm ~10 s/leg lỗi. Cố ý (an toàn > tốc độ), tham số `LIVE_C3_RESEND_SAFE_MS`.
6. `Utils.sendSms2Telegram` (cơ chế sẵn có, token hardcode — owner "kệ đã") khi lỗi HTTP gọi `printStackTrace` ⇒ stack có thể chứa URL
   có token ra stderr. Không sửa (ngoài phạm vi, không thêm token mới).
7. c3_live **không còn rpush** sang queue LEGACY kể cả khi `LIVE_ADAPTER` tắt (an toàn hơn: queue đó đặt lệnh tài khoản CHÍNH).
   Đây là đổi hành vi duy nhất của profile c3_live khi adapter tắt (c3_shadow không đổi).

## 1. Commit

| commit | nội dung |
|---|---|
| `694b2f62` | merge `v1.2/safe` (không xung đột) |
| `779b3a01` | merge `v1.2/lib` (không xung đột) — build xanh 492 test |
| `bb8c43f6` | C8: kill-switch C1/C5 tự gỡ latch sau 30′ liên tục sạch + Telegram; C2/C3/C4/C6/A40 giữ latch |
| `5ef2c702` | C1/C3/C4/C5/C12: `LiveBookC3`, `C3LiveOrderExecutor`, `C3LiveEntry`, `C3LiveFlattener`, `C3LiveEquity`, `DryGateway`, `GatewayFactory`, `C3LiveAlerts`; stop `workingType` mặc định MARK_PRICE |
| `205dfa7d` | nối vào `DetectEntrySignal2TradeNormal`, `LegacySymbols`, `BinanceOrderTradingManager`, `OpsHooks`, `TsMktExt`/`MarketIndexFilter`, `CoinRankManager.peekCoinTier`; `c3live.runtime.{C3LiveRuntime, C3LiveHook}` |
| `d4bcb736` | `C3LiveEntry.onLeg` tuần tự hoá (tick selector/market có thể chạy song song) |
| (commit này) | `docs/result/V12_CORE.md` |

## 2. Việc × tiêu chí GOLIVE_SCENARIO × test × trạng thái

| mã | tiêu chí (GOLIVE §2 / task MASTER) | làm gì | test | trạng thái |
|---|---|---|---|---|
| C1(a) | giữ chỗ margin đồng bộ TRƯỚC gửi (pending), xác nhận/huỷ theo fill; 24 ứng viên cùng tick, equity 10 000 ⇒ tổng margin ≤ 6 000; leg k throttle `1−U/U_MAX` đúng `managerBudget` tới 1e-6 | `c3live.book.LiveBookC3` (cụm/legs/qty/giá TB/margin/tsFirstLeg/legCount/peak/armed/stopPrice/stopClientAlgoId/closeCid; PENDING→SENDING→CONFIRMED/CANCELLED, UNKNOWN); `U = margin(pending+confirmed)/vốn`; sizing gọi đúng `TradeUtils.managerBudget` | `C3LiveEntryTest.twentyFourCandidatesThrottleMatchesManagerBudgetAndUmax` (F_BASE ép 0,2 để chạm trần: \|throttle−(1−U/U_MAX)\| ≤ 1e-6 mọi leg, U tính độc lập = Σ notional đã giữ, Σ ≤ 6 000); `defaultConfigCapsAt45PctAndSumBelowUmax` (cấu hình thật: ≤ 450/leg, Σ ≤ 6 000); E2E | ĐẠT |
| C1(b) | DCA grid đọc sổ thật | `LiveBookC3.gridStates()`; `C3LiveHook.dcaDue` + leg "chỉ live" (`createOrderBuyRequest0(..., liveOnly=true)`) khi sổ giấy không tới bậc; entry DCA: phải đang giữ, không leg treo/không đang đóng, `DcaUtils.shouldDcaGrid`, legIdx = legCount, TIER_3 chặn DCA | `C3LiveEntryTest.dcaGridOnRealBook`, `LiveBookC3Test.gridStatesOnlySettledClusters` | ĐẠT (unit; chưa replay −50/−75/−90 trên đợt DEV thật — để C12 e2e 2b) |
| C1(c) | vị thế C3 thật KHÔNG bị `LegacySymbols` coi là LEGACY | `LegacySymbols.compute/reconcile(real, paper, c3liveOwned)`; call site BOTM truyền `C3LiveHook.ownedSymbols()` (tắt ⇒ rỗng ⇒ như cũ) | `C3LiveLegacyAndAltEwFilterTest.realC3PositionsAreNotLegacy` | ĐẠT |
| C1(d) | guard trùng coin thấy vị thế thật | `C3LiveEntry`: leg mở cụm bị chặn nếu `LiveBookC3.isHolding` (gồm pending) | `gateOrderKillSwitchUniverseModeGuard` (HOLDING) | ĐẠT |
| C1(e) | sổ giấy chạy song song làm twin | đường giấy không đổi; c3_live luôn `shadowHandleOrder` (không rpush) | build/parity | ĐẠT |
| C1 persist | `run/c3live_book.json` atomic, khôi phục restart, file hỏng ⇒ fail-closed | tmp + ATOMIC_MOVE mỗi thay đổi; hỏng ⇒ `.corrupt_<ms>` + `healthy()=false` ⇒ chặn mở mới; ghi lỗi ⇒ không gửi lệnh | `LiveBookC3Test.persistAndRestoreAllFields`, `corruptFileFailsClosed` | ĐẠT |
| C3 | `cid = c3-<symbolToken>-<barMin>-<leg>` ≤36 hợp lệ; bỏ rpush mù; gateway trực tiếp qua executor riêng; timeout/unknown ⇒ `queryOrder` theo cid trước retry; khoá xử lý persist qua restart; 1 000 lượt ngẫu nhiên 0 trùng | `C3LiveCids` (token dài/non-ASCII ⇒ `x<sha10>`); `C3LiveOrderExecutor`: `markSending` persist TRƯỚC gửi; `isDefinitelyNotExecuted` ⇒ huỷ; còn lại ⇒ UNKNOWN ⇒ chờ ≥ `safeRetry` (≥ recvWindow) ⇒ `queryOrder`: có ⇒ áp; không có ⇒ gửi lại CÙNG cid (≤3); lỗi tra ⇒ giữ UNKNOWN (luồng định kỳ tra, không gửi lại); sau restart: PENDING ⇒ huỷ, SENDING/UNKNOWN ⇒ chỉ tra, KHÔNG gửi lại | `C3LiveOrderExecutorTest.thousandRandomTrialsZeroDuplicates` (sàn giả KHÔNG tự chặn cid trùng; 5 % reject, 15 % timeout trước, 25 % timeout SAU khi khớp, 8 % crash JVM trước/sau, 25 % lỗi tra ⇒ **0 cid khớp > 1 lần / 1 000**, sổ khớp sàn 100 %, >20 restart); `ackThenTimeout…`, `absentAfterTimeout…`, `definitelyNotExecuted…`, `restartPendingNeverSent…`, `cidFormatAndLimits` | ĐẠT |
| 3 (nối) | thứ tự kiểm `killSwitchArmed && allowNewEntry && isBuyable && checkSymbol` ⇒ sizing min(pilot,equity)·4,5 % cap, U_MAX ⇒ `SymbolRules.sizeMarketBuy` (bỏ leg nếu fail) ⇒ pending ⇒ `newMarketOrder` ⇒ audit | `C3LiveHook.onLeg` gọi ngay sau cầu dao mật độ trong `createOrderBuyRequest` (leg đã qua gate); `C3LiveEntry.decide` đúng thứ tự (thêm `pushAllowed` đầu tiên; kiểm sổ thật LEGACY/HOLDING/DCA nằm giữa `isBuyable` và `checkSymbol` để không tốn REST); sizing fail ⇒ dòng audit `status=SKIP reason=sizing:<lý do>` | `gateOrderKillSwitchUniverseModeGuard` (KS chặn cả TradFi; TradFi/không niêm yết ⇒ 0 call REST mode guard; multiAssets=false ⇒ MODE_GUARD, 0 lệnh), `sizingFailureSkipsLegWithAuditLine`, `capitalIsMinPilotAndEquity` | ĐẠT |
| U3 market | market level/ALT_EW c3_live dùng `marketIndexMembers()`; c3_shadow giữ nguyên | `DetectEntry…checkMarketLevelChange2Trade`: 4 map rate chỉ nhận symbol ∈ index khi hook bật (null ⇒ như cũ; chưa có snapshot ⇒ không lọc + WARN 10′); ALT_EW: `MarketIndexFilter` (runtime đặt) dùng trong `TsMktExt.computeDay` | `C3LiveLegacyAndAltEwFilterTest.altEwMemberFilter`; parity (tắt ⇒ không lọc) | ĐẠT (feature gate: CHƯA — §0.4) |
| 4 FLATTEN | `requiredAction()==FLATTEN` ⇒ đóng hết reduce-only chia lô ≤5 lệnh/10 s qua RateGuard, huỷ stop, Telegram, dừng mở mới | `C3LiveFlattener.step()` (thread `C3LIVE-OPS` 5 s): qty = \|positionAmt\| sàn (lỗi ⇒ qty sổ); cid `c3x-<tok>-<min>-<n>` persist trước gửi; timeout ⇒ tra lần sau, không gửi mù; đóng xong ⇒ huỷ `stopClientAlgoId` + mọi stop mở của symbol ⇒ xoá cụm; cụm còn leg mua treo ⇒ chờ; Telegram lúc bắt đầu + xong; chặn mở mới = latch FLATTEN | `C3LiveFlattenerTest` (3), E2E | ĐẠT |
| C6 (quyết định) | stop sau arm `newStopMarket` 5 tham số closePosition=true; đóng bằng đường khác ⇒ huỷ stop; workingType MARK_PRICE | `C3LiveClientConfig` mặc định `MARK_PRICE` (lý do: tránh râu nến giá last/contract ở coin thanh khoản mỏng kích stop giả; `LIVE_C3_STOP_WORKING_TYPE=CONTRACT_PRICE` để quay lại); `LiveBookC3.setStop/clearStop`; `C3LiveFlattener.closeCluster(sym, reason)` (cho time-stop/X14 2b) huỷ stop sau khi đóng | `C3LiveClientTest.stopMarketUsesAlgoApi` (đổi kỳ vọng sang MARK_PRICE), `C3LiveFlattenerTest.closeTimeout…CancelsStop`, `DryGatewayTest` (closePosition) | MỘT PHẦN (trailing manager 2b) |
| C8 KS | C1, C5 tự gỡ sau 30′ liên tục sạch + Telegram; C2/C3/C4/C6/A40 giữ tới script owner; sau cờ c3_live | `KillSwitchEngine.Params.autoReleaseMs/autoReleaseCodes`; `cleanSince` theo mã (đạt ⇒ xoá mốc; hết đạt ⇒ đặt mốc; latch nạp từ file ⇒ đếm từ periodic đầu); chỉ chạy ở mode ACT (= c3_live); `OpsConfig`: `LIVE_KILLSW_AUTORELEASE_MIN` (30, 0 = tắt) chỉ khi act | `KillSwitchAutoReleaseTest` (6): C1 tái phát reset đồng hồ, 29′ chưa gỡ/30′ gỡ, persist; C5 gỡ nhưng C3 giữ; A40 FLATTEN không bao giờ tự gỡ; autoRelease=0 = hành vi v1.2/safe; latch nạp file; OpsConfig act=30′/log=0 | ĐẠT |
| C8 nguồn | KHÔNG dùng sổ giấy làm nguồn C6/A40 khi c3_live; chỉ `onBook` sổ thật | `OpsHooks.onPaperBook/onPaperTick` no-op khi `LIVE_PROFILE=c3_live`; `C3LiveRuntime` gọi `OpsHooks.onBook(openCount, marginUsed, totalMarginBalance)` mỗi 15 s; A40 = `attachEquitySource(C3LiveEquity)` | E2E (A40 ⇒ FLATTEN) | ĐẠT (onBook call site chưa có test runtime — runtime cần JVM thật) |
| Q1b | `EquitySource` = totalMarginBalance tài khoản con, cache ≤60 s; vốn = min(`LIVE_C3_PILOT_CAPITAL`=10 000, tmb) | `c3live.risk.C3LiveEquity` (ttl kẹp ≤60 s; lỗi ⇒ null, không dùng số cũ quá ttl, báo C3) | `C3LiveFlattenerTest.equityCapitalIsMinPilotTmbAndCached` | ĐẠT |
| C12 adapter | `DryGateway`: khớp ở giá ref (close 1m), `[LIVE-DRY]` cùng cột, không mạng; chọn theo `LIVE_ADAPTER`; live ⇒ `C3LiveClient.create`, key lỗi ⇒ từ chối push, WARN, KHÔNG crash | `c3live.adapter.{DryGateway, GatewayFactory}`; `C3LiveRuntime.get()` null ⇒ hook no-op + WARN + Telegram | `DryGatewayTest` (2), `C3LiveE2ETest.dryAdapterOneLiveDryLinePerLegNoLiveLines` (24 leg ⇒ 24 dòng `[LIVE-DRY]` 12 cột đúng cid, 0 dòng live) | ĐẠT (mock e2e đầy đủ: 2b) |
| Telegram | cơ chế sẵn có, không token mới, không log token | `C3LiveAlerts` (async 1 thread, hàng đợi 100, escape HTML) → `Utils.sendSms2Telegram`; `OpsHooks.setAlert` | — | ĐẠT (§0.6) |
| E2E | 1 tick sập 24 ứng viên end-to-end (sizing, U_MAX, idempotency, audit, KS chặn khi latch) | `C3LiveE2ETest.oneCrashTick24CandidatesEndToEnd`: KS ACT thật + universe (TradFi bị loại) + AccountModeGuard + C3LiveEquity + managerBudget + SymbolRules + sổ persist + executor; 1 leg timeout SAU khi sàn nhận ⇒ 1 lệnh/cid; latch C3 ⇒ tick 2 (24 entry + DCA) = 0 lệnh; C3 KHÔNG tự gỡ sau 40′; A40 ⇒ FLATTEN 24 cụm ≤5/10 s, stop huỷ, vị thế 0, Telegram | ĐẠT |

## 3. Validation

- `mvn -o -q package -DskipTests=false` (HEAD `d4bcb736`): **EXIT 0, 523 test, 0 fail, 0 error, 2 skip** (base merge 492; +31 mới:
  LiveBookC3Test 4, C3LiveOrderExecutorTest 6, C3LiveEntryTest 6, C3LiveE2ETest 2, C3LiveFlattenerTest 3, DryGatewayTest 2,
  KillSwitchAutoReleaseTest 6, C3LiveLegacyAndAltEwFilterTest 2; sửa 1 kỳ vọng `C3LiveClientTest` CONTRACT_PRICE→MARK_PRICE).
  Test sẵn có bắt được 1 vi phạm của tôi (`TsMktExtTest.realPositionPathDoesNotReferenceTsExt`) ⇒ tách `MarketIndexFilter`, không sửa test.
- **Bytecode** `target/classes` base `779b3a01` (786 lớp) ↔ HEAD (821): **771 giống hệt**, 15 đổi = đúng 9 file nguồn sửa (+ inner `$1`/`$TickGate`
  do dịch số dòng): `C3LiveClientConfig$Builder`, `KillSwitchEngine(+$CodeState,$Params)`, `OpsConfig`, `OpsHooks(+$1)`, `CoinRankManager(+$1)`,
  `LegacySymbols`, `TsMktExt`, `BinanceOrderTradingManager`, `DetectEntrySignal2TradeNormal(+$1,$TickGate)`; thêm `MarketIndexFilter` + 34 lớp c3live.
- **Lý do byte-identical khi cờ tắt** (c3_shadow/sim): mọi nhánh mới chặn bởi `C3LiveHook.enabled()` (= `LIVE_PROFILE=c3_live` && `LIVE_ADAPTER∈{dry,live}`,
  static final) / `OpsConfig.isC3Live` / mode ACT (chỉ c3_live) / `MarketIndexFilter` null; `marketIndexOrNull()` tắt ⇒ null ⇒ không lọc;
  `ownedSymbols()` tắt ⇒ rỗng ⇒ `reconcile` cùng tập; push: `isLive()` false ⇒ biểu thức cũ; `peekCoinTier` chỉ gọi khi hook bật.
- **Parity offline 2026-10-22** (`~/claude_master/v12/core_parity/`, driver = bản sao `safe_parity/drv.py`, jar md5 `29e709b0…` = HEAD d4bcb736,
  cache tự dựng (cache chia sẻ của safe_parity đã bị xoá), chỉ đọc harness/segs/Vision; `core_parity/core_compare.json`):
  **CTL gate 1440/1440 phút bit** (rows 1440/1440, bad_min 0); 4 file `out_BT`, `out_NEW2`, `fund_BT`, `fund_NEW2` (giải nén)
  **md5 trùng 100 %** với lượt jar `dcae2e2b` (`safe_parity/d22_base`: 2c7c336d…, 2c7c336d…, 1a6d1521…, f4acab23…). CTL fund 0,9443
  (79 phút, cột f3) giống hệt base (sẵn có, không do v12). strace: chỉ `connect` AF_UNIX nscd, **0 kết nối AF_INET**.
  Lưu ý: parity chỉ chứng minh đường cờ TẮT; đường c3_live (cờ bật) chỉ có unit/mock/e2e test.
- Không gọi Binance/242; không REST; `PrivateConfig.java` chỉ chép để biên dịch (gitignored, không commit/in); jar ở Oracle.

## 4. CHƯA LÀM — vòng 2b

1. **C6 trailing manager**: arm +7 % ⇒ `newStopMarket` 5 tham số closePosition=true (MARK_PRICE) qua `C3LiveCids`/clientAlgoId; dời khi
   mức mới cao hơn ≥1 tick VÀ ≥0,1 % (`SymbolRules.roundStopPriceForLong`); time-stop 168h + TS_MKT_EXT X14 (bật `TsMktExt` cho c3_live,
   đã có `MarketIndexFilter`) ⇒ `C3LiveFlattener.closeCluster(sym, "TIME_STOP"|"X14")`; replay 3 đợt DEV so sổ giấy 100 %.
2. **C7 fill accounting / user-data stream** (`ORDER_TRADE_UPDATE` listenKey tài khoản con, phí, partial, fallback REST + WARN).
3. **C9 reconcile** start + hằng giờ: `positions()` + `openStops()` + sổ ⇒ sàn thắng qty/giá, thiếu SL ⇒ tạo, SL mồ côi ⇒ huỷ, lệch ⇒ chặn entry;
   đối chiếu equity |sổ − tmb|/tmb > 1 % ⇒ Telegram + chặn mở mới (Q1b).
4. **C12 mock e2e đầy đủ** (mở/DCA −50/−75/−90/arm/dời SL/time-stop/X14/restart/kill-switch) + replay đợt DEV qua DryGateway (G-DRY).
5. **O2 scripts owner** (`golive_*.sh`: bật dry, dump exchangeInfo ra `LIVE_C3_EXCHANGEINFO_FILE`, resume/reset…).
6. Feature gate loại TradFi (§0.4) — chờ MASTER/P1 sim. `GATE_QUOTA_SKIP_WHEN_FULL` vẫn đo U trên sổ GIẤY (twin) — lệch nhỏ khi sổ thật/giấy khác nhau.

## 5. Cấu hình mới (mặc định = tắt / hành vi cũ)

| key | mặc định | ý nghĩa |
|---|---|---|
| `LIVE_ADAPTER` | (trống = OFF) | `dry` / `live`; cần `LIVE_PROFILE=c3_live` |
| `LIVE_C3_PILOT_CAPITAL` | 10000 | vốn tính size = min(giá trị này, totalMarginBalance) |
| `LIVE_C3_EQUITY_TTL_MS` | 60000 (kẹp ≤ 60 000) | cache account() |
| `LIVE_C3_BOOK_FILE` | `run/c3live_book.json` | sổ thật |
| `LIVE_C3_RESEND_SAFE_MS` | 10000 | chờ trước queryOrder khi timeout (≥ recvWindow 5 000) |
| `LIVE_C3_ORDER_MAX_ATTEMPTS` | 3 | số lần gửi tối đa 1 cid (chỉ sau khi xác nhận không có) |
| `LIVE_C3_FLATTEN_MAX_ORDERS` / `_WINDOW_MS` | 5 / 10000 | chia lô FLATTEN |
| `LIVE_C3_EXCHANGEINFO_FILE` | `run/c3live_exchangeInfo.json` (.gz được) | exchangeInfo cho dry |
| `LIVE_C3_DRY_EQUITY` | = pilot | vốn giả của DryGateway |
| `LIVE_KILLSW_AUTORELEASE_MIN` | 30 (chỉ mode act) | C1/C5 tự gỡ; 0 = tắt |
| `LIVE_C3_STOP_WORKING_TYPE` | **MARK_PRICE** (đổi từ CONTRACT_PRICE) | workingType stop |

Push thật cần đủ: `LIVE_PROFILE=c3_live`, `LIVE_ADAPTER=live`, `LIVE_KILLSW_MODE=act`, `SHADOW_NO_PUSH=false`, `LIVE_ENTRY_ENABLED=true`, không có
`run/KILL_SWITCH`, key file hợp lệ. Dry chỉ cần `LIVE_PROFILE=c3_live`, `LIVE_ADAPTER=dry`, `LIVE_KILLSW_MODE=act` (thiếu act ⇒ mọi leg KS_NOT_ARMED).

## 6. API công khai cho vòng 2b

```java
// c3live.book
public final class LiveBookC3 { LiveBookC3(File fileOrNull, double leverage);
  boolean healthy(); double marginUsed(); double pendingMargin(); boolean isHolding(String); boolean hasUnresolved(String); boolean isClosing(String);
  int legCount(String); int openCount(); Set<String> ownedSymbols(); Optional<ClusterView> cluster(String); List<ClusterView> clusters();
  Optional<LegView> leg(String cid); List<LegView> unresolvedLegs(); List<LiveDcaGridC3.GridState> gridStates();
  boolean reserve(String sym, String cid, int legIdx, long barMin, String level, double refPx, BigDecimal qty, double margin, long now);
  boolean markSending(String cid, long now); void markUnknown(String cid, String note, long now); void noteOpen(String cid, long orderId, long now);
  boolean confirm(String cid, BigDecimal execQty, double avgPx, long orderId, long now); boolean cancel(String cid, String reason, long now);
  boolean markClosing(String sym, String closeCid, String reason, long now); void clearCloseCid(String sym, long now); boolean removeCluster(String sym, String reason, long now);
  void setStop(String sym, double stopPrice, String clientAlgoId, long now); void clearStop(String sym, long now); void updatePeak(String sym, double px, long now);
  enum LegState { PENDING, SENDING, UNKNOWN, CONFIRMED, CANCELLED } }
// ClusterView: symbol, tsFirstLeg, legCount, confirmedQty, avgPrice, confirmedMargin, pendingMargin, firstEntryPrice, peak, armed, stopPrice,
//   stopClientAlgoId, closeCid, closeReason, closeAttempts, closeSentMs, hasUnresolved, legs
// c3live.exec
public final class C3LiveCids { static String entry(String sym, long barMin, int leg); static String close(String sym, long minute, int attempt); static long barMin(long startMs); }
public final class C3LiveOrderExecutor { C3LiveOrderExecutor(ExchangeGateway, LiveBookC3, ApiObserver, FillObserver, LongSupplier clock, Sleeper, long safeRetryMs, int maxAttempts, Executor);
  void submit(String cid); int resolveUnresolved(boolean startup); String stats(); interface ApiObserver/FillObserver/Sleeper }
// c3live.entry
public final class C3LiveEntry { static Builder builder(); Result onLeg(LegInput in, long nowMs); Map<Outcome,Long> counts(); LiveBookC3 book(); }
// c3live.risk
public final class C3LiveEquity implements EquitySource { C3LiveEquity(ExchangeGateway, double pilot, long ttlMs, LongSupplier, ApiObserver); Double totalMarginBalance(); Double capital(); }
public final class C3LiveFlattener { C3LiveFlattener(ExchangeGateway, LiveBookC3, Supplier<KillSwitchEngine.Action>, Consumer<String> alert, ApiObserver, LongSupplier, int maxOrders, long windowMs, long safeRetryMs);
  int step(); int closeCluster(String symbol, String reason); }
// c3live.adapter
public final class DryGateway implements ExchangeGateway { DryGateway(Supplier<ExchangeInfo>, Function<String,BigDecimal> refPrice, BigDecimal equity, OrderAuditLog, LongSupplier); }
public final class GatewayFactory { enum Mode {OFF,DRY,LIVE; static Mode parse(String)}; static Result create(Mode, Function<String,String> env, Function<String,BigDecimal> ref, BigDecimal dryEquity, LongSupplier, OrderAuditLog); }
// c3live.runtime
public final class C3LiveRuntime { static C3LiveRuntime get() /*null = tat/loi*/; C3LiveEntry entry(); LiveBookC3 book(); Set<String> marketIndexOrNull(); void putRef(String, double); }
public final class C3LiveHook { static boolean enabled(); static void onLeg(String, KlineObjectSimple, MarketLevelChange); static List<String> dcaDue(Map<String,KlineObjectSimple>);
  static Set<String> marketIndexOrNull(); static Set<String> ownedSymbols(); }
// ops
KillSwitchEngine.Params.autoReleaseMs / autoReleaseCodes; OpsConfig.KEY_KILLSW_AUTORELEASE_MIN
// tradecore
LegacySymbols.reconcile(Set real, Set paper, Set c3LiveOwned); MarketIndexFilter.set/get; CoinRankManager.peekCoinTier(String)
```

## 7. File đổi

Mới: `src/main/java/com/binance/chuyennd/c3live/{book/LiveBookC3, exec/C3LiveCids, exec/C3LiveOrderExecutor, entry/C3LiveEntry,
risk/C3LiveEquity, risk/C3LiveFlattener, adapter/DryGateway, adapter/GatewayFactory, alert/C3LiveAlerts, runtime/C3LiveRuntime,
runtime/C3LiveHook}.java`, `tradecore/selector/MarketIndexFilter.java`; test `c3live/{book,exec,entry,risk,adapter}/*Test.java`,
`c3live/entry/C3LiveFixtures.java`, `ops/KillSwitchAutoReleaseTest.java`, `tradecore/selector/C3LiveLegacyAndAltEwFilterTest.java`.
Sửa: `trading/DetectEntrySignal2TradeNormal.java`, `trading/BinanceOrderTradingManager.java`, `tradecore/selector/{LegacySymbols, TsMktExt}.java`,
`tradecore/CoinRankManager.java`, `ops/{KillSwitchEngine, OpsConfig, OpsHooks}.java`, `c3live/client/C3LiveClientConfig.java`,
test `c3live/client/C3LiveClientTest.java` (1 dòng).
Artefact ngoài repo (Oracle): `~/claude_master/v12/core_parity/` (drv.py, jar, d22_core), `~/claude_master/v12/c3live_wk/` (log build, base779 để diff bytecode).
