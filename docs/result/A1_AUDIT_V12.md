# A1_AUDIT_V12 — audit độc lập branch `v1.2/c3-live` @ a896595f

Auditor: a1audit (Claude Opus, KHÔNG phải người viết code), 2026-10-25. Chỉ đọc + build/test trong worktree riêng
`~/claude_master/v12/a1` (branch `audit/a1` từ a896595f). Không sửa `v1.2/c3-live`, không push, không đụng 242, không gọi Binance.
Base so sánh: 16de49a6 = jar `dcae2e2b` (đang chạy shadow). Mọi chứng cứ chạy lại được: `~/claude_master/v12/a1_parity/`.

## 0. Kết luận risk-first

**G-CODE: TRƯỢT** — phần byte-identical c3_shadow ĐẠT (§1), nhưng còn **1 CRIT + 2 MAJ mở** (GOLIVE §3: "0 CRIT/MAJ mở; có CRIT ⇒ không deploy").

| mã | mức | tóm tắt | chặn |
|---|---|---|---|
| CRIT-1 | CRIT | C6 kill-switch ở c3_live đo DD của totalMarginBalance tài khoản con (~10 000) so với **đỉnh sổ GIẤY** (sàn PAPER_EQUITY=35 000 + file `run/killsw_peak`=35 015,29 do c3_shadow ghi) ⇒ dd = −0,714 ⇒ **latch FLATTEN ~15 s sau mỗi lần khởi động**; owner reset (cả `reset_peak=1`) không gỡ được (latch lại ở onBook kế) | dry (0 leg vào) + canary/live |
| MAJ-1 | MAJ | `Reconciler.blocks` khởi tạo RỖNG ⇒ `allowsEntry()=true` TRƯỚC khi `startup()` chạy (ops thread) ⇒ entry có thể đi trước reconcile khởi động / `resolveUnresolved(true)` / `checkGlobal` (fail-open theo cấu trúc) | canary/live |
| MAJ-2 | MAJ | Danh sách positions đọc OK nhưng **thiếu symbol** (vd `[]` lúc sàn trục trặc) bị coi là "đã phẳng" ⇒ `closedOnExchange`/`finalizeClosed` **huỷ mọi stop + xoá cụm** khi vị thế có thể còn (fallback REST mỗi 10 s khi mất stream, hourly, time-stop/X14/FLATTEN) | canary/live |

TradFi thật: phân loại bằng `contractType=TRADIFI_PERPETUAL` (225/932) đúng tuyệt đối trên dump thật — **0 TradFi lọt vào buyable (514)**,
1 crypto bị loại "thừa" (PREDICTUSDT, PENDING_TRADING, underlyingType=PREMARKET). Chi tiết §2.

Không thấy đường nào trong code mới gửi lệnh tài khoản CHÍNH; không log key/secret/signature (grep + log test 0 hit). Concurrency: không
thấy race CRIT (LiveBookC3 synchronized toàn bộ); 2 race MIN ghi §5.

## 1. G-CODE byte-identical (cờ TẮT) — ĐẠT

### 1a. Build lại
`mvn -o package -DskipTests=false` tại a896595f (PrivateConfig chép từ `~/src_wt_pxcache` chỉ để biên dịch, gitignored, không commit/in):
**BUILD SUCCESS, 574 test, 0 fail, 0 error, 1 skip** (`SymbolMapperSnapshotRepairTest`, có sẵn). Jar A1 md5 `eaebb861…` (khác `a55be721…`
của tác giả là bình thường — timestamp trong jar; so sánh bằng nội dung lớp §1c).

### 1b. Parity offline (driver = bản sao `exit_parity/drv.py`, harness `research/parity_v11` OFFLINE, mỗi lượt TỰ dựng cache, không chia sẻ)
| ngày | file (giải nén) | jar dcae2e2b (ref) | jar A1 a896595f | trùng |
|---|---|---|---|---|
| 2026-10-22 | out_BT / out_NEW2 | 2c7c336d… (1 441 dòng) / 2c7c336d… | 2c7c336d… / 2c7c336d… | ✓ / ✓ |
| 2026-10-22 | fund_BT / fund_NEW2 | 1a6d1521… (48 685) / f4acab23… | 1a6d1521… / f4acab23… | ✓ / ✓ |
| 2026-10-23 | out_BT / out_NEW2 | e0918a33… (1 441) / e0918a33… | e0918a33… / e0918a33… | ✓ / ✓ |
| 2026-10-23 | fund_BT / fund_NEW2 | a81b3b03… (49 204) / 8dea3f70… | a81b3b03… / 8dea3f70… | ✓ / ✓ |

- **CTL gate (NEW2 vs BT) bit 1440/1440 phút, only_ref 0, only_new 0, mọi cột bit = 1.0** cho CẢ 2 ngày, cả 2 jar.
- CTL fund: 10-22 cột f3 bit 0,94425 (cả ref lẫn A1, y hệt); 10-23 f3 0,94586 + cand 0,99750 (cả ref lẫn A1, y hệt) ⇒ đặc tính restart/funding
  có sẵn của harness, KHÔNG do v1.2 (md5 fund trùng tuyệt đối giữa 2 jar).
- md5 10-22 trùng cả số tác giả công bố (`exit_compare.json`). strace: 0 connect AF_INET không-loopback, 0 tới 242 (BT + 3 segment NEW2, 2 ngày,
  2 jar); rc 0; 0 dòng log nghi vấn. Chi tiết `~/claude_master/v12/a1_parity/a1_compare.json`.

### 1c. Bytecode diff (jar `dcae2e2b` ↔ jar A1 a896595f, mọi lớp `com/binance/chuyennd/**`)
- 622 lớp ref, 736 lớp A1: **596 giống hệt byte**, 0 xoá, 114 thêm (109 `c3live.*` + `ops/EquitySource`, `KillSwitchEngine$Action`,
  `KillSwitchEngine$Params`, `selector/C3TrailRate`, `selector/MarketIndexFilter`), **26 đổi**.
- 26 lớp đổi thuộc đúng 14 file nguồn tác giả khai (V12_SAFE/CORE/EXIT). 10 lớp inner chỉ đổi bảng số dòng: `javap -c -p` (bỏ số hằng pool) = **0 dòng
  khác**: `LiveFeaturePipeline$1/$Result/$SettleInfo`, `LiveGateRollingRatio$1/$SeedResult`, `KillSwitchEngine$CodeState/$Mode/$Resolved`,
  `OpsHooks$1`, `CoinRankManager$1`, `DetectEntrySignal2TradeNormal$1/$TickGate`.
- Diff nguồn từng lớp cũ (16de49a6→a896595f, `--ignore-cr-at-eol`) và kết luận khi cờ tắt (c3_shadow/sim):

| lớp | thay đổi | đổi QUYẾT ĐỊNH khi cờ tắt? |
|---|---|---|
| `DetectEntrySignal2TradeNormal` | (1) `c3Idx = C3LiveHook.marketIndexOrNull()` (tắt ⇒ null ⇒ `inIdx=true`); (2) `dropTradFi(...)` (tắt ⇒ trả CHÍNH map, `new HashMap<>(…)` giữ nguyên như cũ); (3) `tradFiDrop` null; (4) nhánh `C3LiveHook.enabled()` (static final false); (5) điều kiện shadowHandleOrder `on() && (isLive() \|\| cũ)` — c3_shadow `isLive()=false` ⇒ biểu thức cũ; (6) C10: log `[FAIL-CLOSED]` khi `predictData==null` + cột n_pass log | **Không** (chỉ log) |
| `LiveFeaturePipeline` | C11 `seedExclLast` (cờ `LIVE_SEED_EXCLUDE_DECISION_MIN`, mặc định 0 ⇒ `seed()` cũ); `filt()` với `snapFilter==null` ⇒ trả nguyên | Không |
| `AIRejectFilter`, `LiveGateRollingRatio` (C10) | NaN/Inf ⇒ REJECT chỉ khi `LiveGateRollingRatio.isOn()` (key LIVE); r/q không hữu hạn ⇒ NaN, không nạp buffer | Chỉ khi NaN + key live (ngoại lệ có khai). **A1 kiểm độc lập** buffer 242 (đọc chunk GRR1+snappy bằng Python tự viết): 802 000 record tới ts 1792886820000, **0 NaN / 0 ±Inf / 0 chunk hỏng** |
| `KillSwitchEngine`, `OpsHooks`, `OpsConfig` | ACT/latch/C2 có dấu/A40/C4 công suất/tự gỡ — mọi nhánh mới chặn bởi `mode==ACT` (chỉ c3_live) hoặc `C3LIVE`; mode LOG: `allowNewEntry` luôn true, `requiredAction` NONE, không I/O file latch; log khởi động mode log giữ nguyên chuỗi | Không (KS mode log vốn chỉ log) |
| `TsMktExt` | `filterMembers` (MarketIndexFilter null ⇒ nguyên map); `decideEnabled` bỏ `!profileLive` | Không cho c3_shadow (xem MIN-2) |
| `LegacySymbols`, `BinanceOrderTradingManager`, `CoinRankManager` | overload `reconcile(real, paper, owned)` (tắt ⇒ owned rỗng ⇒ cùng tập); `peekCoinTier` chỉ gọi khi hook bật | Không |
| `Utils`, `HttpRequest`, `P2PTelegramNotifier` | bỏ `printStackTrace`/stack; log qua `redactSecrets` (Utils: 1 327 dòng diff là đổi CRLF→LF, thay đổi thật 2 dòng) | Không (chỉ nhánh log lỗi) |

Kết luận 1: **đường c3_shadow/sim byte-identical về quyết định** (parity + bytecode + đọc nguồn). Ngoại lệ C10 đã chứng minh 0 NaN.

## 2. TradFi THẬT (fixture `exchangeInfo_20261025_1457.json.gz`, 932 symbol, serverTime 1792913909766)

Phân tích Python độc lập (`a1_parity/tf.py`, không import repo) + chạy chính `SymbolUniverseLive` của jar A1 (`a1_parity/chk/UniCheck.java`) — hai bên khớp.

- Trường phân biệt: **`contractType`** ∈ {PERPETUAL 703, **TRADIFI_PERPETUAL 225**, CURRENT_QUARTER 2, NEXT_QUARTER 2}.
  `underlyingType` ∈ {COIN 703, EQUITY 187, HK_EQUITY 15, COMMODITY 8, KR_EQUITY 8, PREMARKET 5, INDEX 3, CN_EQUITY 2, FX 1}.
  `underlyingSubType` có nhãn `TradFi` đúng 225 symbol = đúng tập TRADIFI_PERPETUAL (4 cái kèm `Pre-IPO`: ANTHROPIC, OPENAI, OURA, MOONSHOT).
  status: TRADING 794, SETTLING 136, PENDING_TRADING 2. quoteAsset: USDT 887, USDC 39, USD1 3, U 2, BTC 1.
- Classifier: luật `contractType chứa TRADIFI` bắt cả 225; luật `underlyingType ∉ {COIN, INDEX}` bắt thêm 1: **PREDICTUSDT** (PERPETUAL,
  PREMARKET, "Pre-Market", PENDING_TRADING) — crypto pre-market bị loại thừa (bảo thủ; hiện không TRADING).
- Kết quả universe (jar A1): listed 932, alive 794, **tradable 520, buyable 514** (520 − 5 non-ASCII − 1 DELIVERY_SOON VELODROMEUSDT
  deliveryDate 1793178000000 < now+7d); lý do loại: TRADFI 224 (SPCXUSD1 tính vào NOT_USDT), NOT_TRADING 138, NOT_USDT 44, NOT_PERPETUAL 4,
  EXCLUDED 2 (BTCDOM, USDC). **TradFi lọt buyable = 0; TradFi trong market index = 0** (market index 515).
- Đối chiếu proxy SYMLIFE `live_low_activity_1023.csv` (116): 114 là TRADIFI_PERPETUAL; 2 còn lại MITOUSDT, PTBUSDT = crypto SETTLING
  (đúng không phải TradFi). Proxy **thiếu 111** TradFi đang TRADING (vd UNITREE) ⇒ đúng là phải dùng exchangeInfo.
- Mẫu: IBKR/UNITREE(CN_EQUITY)/NAVER(KR_EQUITY)/JPM/TENCENT(HK_EQUITY)/XAU(COMMODITY)/USDBRL(FX) ⇒ TRADFI loại. **MDTUSDT nay là cổ phiếu
  Medtronic** (TRADIFI_PERPETUAL, onboard 2026-10-21) ⇒ loại đúng (ticker cũ của coin MDT bị tái dùng). **POWRUSDT** = crypto TRADING ⇒ buyable
  (sửa lỗi DIED tĩnh cũ). PAXGUSDT = COIN/RWA ⇒ buyable. **ALLUSDT** = PERPETUAL/INDEX TRADING ⇒ vào universe + market index (xem MIN-10).
- Non-ASCII: 5 (币安人生, 我踏马来了, 龙虾, 牛来, 哈基米 USDT) ⇒ tradable nhưng NON_ASCII không mua, không vào market index (cờ mặc định).
- Delivery: PERPETUAL có deliveryDate ≠ 4133404800000: 137, trong đó TRADING chỉ VELODROMEUSDT ⇒ DELIVERY_SOON đúng. STALE: snapshot +61′ ⇒ STALE (fail-closed).
- rateLimits thật: REQUEST_WEIGHT 2400/1′, ORDERS 1200/1′, ORDERS 300/10″ (RateGuard dùng 50 %).
- Test có fixture thật: `SymbolRulesTest.invariantsOnRealDumpIfPresent` **chạy (không skip) và ĐẠT** (7/7 lớp). Đây là test DUY NHẤT
  dùng dump thật và chỉ kiểm bất biến làm tròn qty/stop — **không có unit test nào kiểm phân loại TradFi trên dump thật** (MIN-11; A1 đã kiểm ngoài repo).

## 3. Đường tiền thật (đọc code)

| hạng mục | kết quả | bằng chứng |
|---|---|---|
| thứ tự kiểm trước push | ĐẠT: pushAllowed → KS armed (ACT) → latch/C4 (DCA: chỉ latch) → universe.isBuyable (TradFi/non-ASCII/delist<7d/STALE) → book.healthy → reconAllows → LEGACY → HOLDING/DCA grid → AccountModeGuard.checkSymbol → SymbolRules → equity → managerBudget/U_MAX → legBudget → cap 4,5 % → ×tier → sizeMarketBuy → reserve(PENDING, persist) → executor | `C3LiveEntry.decide` :207–288 |
| sizing | ĐẠT: vốn = `min(LIVE_C3_PILOT_CAPITAL=10000, tmb)` (`C3LiveEquity.capital`), `managerBudget(null, marginUsed, cap)`; `marginUsed` = confirmed + **pending** (`LiveBookC3.marginUsed` :396); cùng thứ tự cap→tier như sổ giấy (DetectEntry :1238 managerBudget, :1248 cap, :1275 ×tier) | — |
| idempotency | ĐẠT: cid `c3-<tok>-<barMin>-<leg>` persist SENDING trước gửi; persist lỗi ⇒ không gửi; timeout ⇒ chờ ≥ recvWindow rồi `queryOrder`; restart: PENDING huỷ, SENDING/UNKNOWN chỉ tra. Test 1 000 lượt có sàn giả độc lập (đếm execCount theo cid) — không tautology | `C3LiveOrderExecutor.place` :114–170; test :97–149 |
| FLATTEN | ĐẠT (≤5 lệnh/10 s, reduce-only qty sàn, huỷ stop) — trừ MAJ-2 (positions thiếu symbol ⇒ coi phẳng) | `C3LiveFlattener` |
| trailing stop | ĐẠT: Algo `POST /fapi/v1/algoOrder` STOP_MARKET `closePosition=true` `workingType=MARK_PRICE`; dời = đặt mới (clientAlgoId `c3s-`, pending persist trước) rồi huỷ cũ; ngưỡng ≥1 tick VÀ ≥0,1 %; −4130 ⇒ qty+reduceOnly; −2021 ⇒ đóng MARKET; huỷ khi đóng (`closedOnExchange`/`finalizeClosed` huỷ mọi `c3s-` của symbol); dùng CHÍNH `ShadowBookC3.trailRate` (`C3TrailRate`); replay song song với `ShadowBookC3` thật (không chép logic) | `TrailingStopManager`, `ExitParityEngine` |
| time-stop / X14 | ĐẠT (chỉ khi chưa arm, như sổ giấy; `TsMktExt.deferTimeStop`); MIN-8: không có giá ⇒ không đánh giá | `TrailingStopManager.stepOne` |
| reconcile | startup + hourly + fallback ĐẠT về logic; **MAJ-1** (cửa sổ trước startup), **MAJ-2** (thiếu symbol = phẳng) | `Reconciler` |
| user stream | ĐẠT: listenKey keepAlive 30′, backoff 1→60 s, xoay URL, fallback REST 10 s + Telegram sau 5′, bù REST khi nối lại; log listenKey chỉ 4 ký tự | `UserStream` :247–253 |
| kill-switch MASTER | Chính sách đúng trong engine: C1/C5 tự gỡ 30′, C3 tự gỡ 30′ + 3 OK, C4 công suất (không latch, DCA chạy, gỡ ≤85 vị thế & U≤U_MAX−0,05), C2/C6/A40/STATE latch owner. **CRIT-1** làm C6 sai nguồn đỉnh | `KillSwitchEngine` :431–480, :632–720 |
| tài khoản CHÍNH | ĐẠT: package c3live không tham chiếu ClientSingleton/PrivateConfig/Redis/rpush; c3_live luôn `shadowHandleOrder` (không rpush) kể cả adapter tắt. Ghi chú: đường quản lý vị thế LEGACY của tài khoản chính (có sẵn từ trước, chạy cả ở c3_shadow) vẫn chạy trong cùng JVM — không phải đường mới | grep; DetectEntry :1368–1375 |
| key/secret/signature | ĐẠT: key file root-only 600 + owner + thư mục cha không ghi được bởi group/other + không symlink; exception không chứa URI; `toString` che; grep log 0; build log (574 test) 0 lần xuất hiện vector KEY/SECRET test, 0 `signature=`, 0 `X-MBX-APIKEY`, 0 token bot | `C3LiveKeys`, `C3LiveClient.call` :388–480 |

## 4. CRIT / MAJ chi tiết (bắt buộc sửa trước dry/canary)

### CRIT-1 — C6 của c3_live dùng đỉnh equity sổ GIẤY ⇒ FLATTEN latch ngay khi khởi động, owner không gỡ được
- Nguồn: `OpsHooks.newEngine()` :70–73 (không đổi theo profile) tạo engine với `paperEquity = LiveProfileC3::paperEquity` (PAPER_EQUITY) và
  `peakFile = LIVE_KILLSW_STATE_FILE` mặc định `run/killsw_peak` (file c3_shadow đang ghi). `C3LiveRuntime.opsLoop` gọi
  `OpsHooks.onBook(openCount, marginUsed, tmb)` mỗi 15 s (`C3LiveRuntime.java` :292) ⇒ `KillSwitchEngine.onPaper`: lần đầu `peak = max(peak_file, PAPER_EQUITY)`,
  `C6 = dd(tmb, peak) ≤ −0,40` ⇒ ACT ⇒ `latchFor("C6")` ⇒ **FLATTEN**.
- Số thật 242 (log kéo về 2026-10-24, dòng `08:00:00.931 [KILLSW] HOURLY … peak=35015.29`; `paperEquity=35000.0` 26 lần): tmb tài khoản con
  ≈ 10 000 BFUSD (dry: `LIVE_C3_DRY_EQUITY` = pilot 10 000) ⇒ dd = 10 000/35 015,29 − 1 = **−0,7144**.
- Chứng minh chạy được (`a1_parity/chk/ProofKs.java`, dựng engine y như OpsHooks với jar A1): onBook(0, 0, 10 000) ⇒
  `action=FLATTEN allowNewEntry=false codes=[C6]`; ghi file reset `reset_peak=1` ⇒ NONE; onBook kế ⇒ **FLATTEN lại** (reset_peak chỉ đặt
  lại đỉnh A40, không đặt lại `peak` của C6; file `run/killsw_peak` vẫn còn).
- Hệ quả: dry trên 242 ⇒ mọi leg `KS_BLOCKED`, 0 dòng `[LIVE-DRY]` ⇒ G-DRY không đo được; live ⇒ FLATTEN mọi cụm + không bao giờ mở mới.
  Test không bắt được vì `C3LiveE2ETest`/`C3LiveExitE2ETest` dựng engine với `paperEquity=10 000`, `peakFile=null`; script deploy không
  kiểm dòng `[KILLSW] LATCH`.
- Sửa đề xuất (để MASTER chốt): ở c3_live (`OpsConfig.isC3Live`) C6 dùng đỉnh RIÊNG từ tmb (không sàn PAPER_EQUITY, file đỉnh riêng vd
  `run/c3live_killsw_peak`, hoặc gộp C6 vào A40 vì cùng ngưỡng −40 % cùng nguồn tmb); `reset_peak=1` đặt lại cả đỉnh C6; test dựng engine
  qua đúng đường OpsHooks với PAPER_EQUITY=35 000 + file đỉnh có sẵn 35 015,29; deploy kiểm "0 dòng `[KILLSW] LATCH`" sau start.

### MAJ-1 — cửa sổ vào lệnh trước reconcile khởi động
- `Reconciler.blocks` (:100) = TreeMap rỗng lúc tạo; `BLOCK_STARTUP` chỉ đặt khi `startup()` ĐỌC SÀN LỖI. `startup()` chạy ở lần lặp đầu của thread
  `C3LIVE-OPS` SAU `refreshRefData` (REST exchangeInfo) + `checkGlobal` + `resolveUnresolved(true)`; trong lúc đó luồng quyết định có thể gọi
  `C3LiveEntry.onLeg` ⇒ `reconAllows=true`. Chứng minh: `new Reconciler(...).allowsEntry("BTCUSDT") = true, blocks={}` trước `startup()`.
- Thực tế: với `LIVE_C3_EXCLUDE_TRADFI_FEATURES=1` runtime được tạo sớm lúc seed (nhiều phút trước tick đầu) nên hiếm khi trúng; nhưng
  không có bảo đảm cấu trúc (cờ =0, REST chậm, restart sát phút quyết định) ⇒ vị thế lạ/lệch equity/leg treo chưa được xét khi lệnh mới đi.
- Sửa: khởi tạo `blocks.put(BLOCK_STARTUP, "chua doi chieu khoi dong")`; gỡ khi `startup()` OK (code đã có `blocks.remove`). Thêm test.

### MAJ-2 — "không thấy trong positions" = "đã phẳng" ⇒ huỷ stop + xoá cụm
- `Reconciler.reconcileClusters` :206 `p == null ⇒ ex = 0 ⇒ closedOnExchange` (huỷ mọi stop `c3s-` của symbol, xoá cụm, ledger);
  `C3LiveFlattener.closeOne` :128 `pos.get(sym) == null ⇒ qty 0 ⇒ finalizeClosed(...flat_on_exchange)` (huỷ stop, xoá cụm).
- Kích hoạt: `checkPositions()` mỗi 10 s khi MẤT user stream (đúng lúc sàn trục trặc), `hourly()`, time-stop/X14/FLATTEN.
  Một phản hồi `positionRisk` 200 nhưng rỗng/thiếu ⇒ vị thế THẬT mất stop sàn + rời sổ (sau đó Reconciler báo "vị thế lạ" và chặn mở mới,
  nhưng vị thế không còn trailing/time-stop). Xác suất thấp, hậu quả lớn, sửa rẻ.
- Sửa: chỉ kết luận phẳng khi có bằng chứng dương (user stream `ACCOUNT_UPDATE pa=0`, hoặc lệnh đóng/stop của bot FILLED, hoặc 2 lần đọc
  liên tiếp cách ≥ 10 s đều thiếu VÀ danh sách không rỗng cho các cụm khác); danh sách rỗng trong khi sổ có cụm confirmed ⇒ coi là lỗi đọc.

## 5. MIN (không chặn, nên sửa/ghi nhận)

1. Utils.java đổi CRLF→LF (diff 1 327 dòng che mất 2 dòng thật) — khó review; nên giữ EOL gốc.
2. `TsMktExt.decideEnabled` bỏ `!profileLive` ⇒ X14 bật cho profile c3_live kể cả khi `LIVE_ADAPTER` tắt (sổ giấy twin). Hiện không triển khai
   cấu hình đó; ghi nhận.
3. `LegacySymbols.reconcile(real, paper, c3liveOwned)`: vị thế c3_live ở TÀI KHOẢN CON không bao giờ có trong danh sách vị thế tài khoản CHÍNH ⇒
   loại `c3liveOwned` không cần; nếu trùng symbol (tài khoản chính có vị thế X trong khi c3_live giữ X) thì vị thế CHÍNH X rời LEGACY ⇒ áp luật
   thoát C3 (arm 0,07/ratchet/time-stop) lên tiền tài khoản chính. Hiện không xảy ra (tài khoản chính không mở mới; C3LiveEntry chặn LEGACY).
4. `×tierMultiplier` sau trần 4,5 % (giống sổ giấy) ⇒ TIER_1 ×1,2 = 5,4 % vốn/leg — đúng parity, nhưng "trần 4,5 %" không tuyệt đối.
5. Độ trễ đợt sập: `AccountModeGuard.checkSymbol` gọi REST `symbolConfig` (+ có thể set) cho MỖI symbol mới trên luồng quyết định trong khoá
   `C3LiveEntry`, rồi executor 1 luồng gửi tuần tự ⇒ đợt 24 leg có thể trễ vài giây cho leg cuối (tăng trượt C2). Gợi ý: nạp sẵn
   `GET /fapi/v1/symbolConfig` (không symbol = tất cả) lúc start/6h; đo ở canary.
6. Sổ không ghi được (đĩa đầy) ⇒ `TrailingStopManager.send` KHÔNG đặt/dời stop ⇒ vị thế đã arm mất bảo vệ mới; cân nhắc vẫn đặt stop (idempotent
   qua queryStop) + Telegram.
7. `C3LiveRuntime.create()` lỗi (vd key file sai sau restart) ⇒ `INSTANCE=null` vĩnh viễn ⇒ vị thế đang mở KHÔNG được quản lý (time-stop, X14,
   reconcile, dời stop) tới restart; chỉ nhánh gateway null có Telegram. Gợi ý: chế độ "chỉ quản lý" hoặc Telegram cho mọi nhánh lỗi.
8. Time-stop/X14 chỉ đánh giá khi có giá price_realtime; feed chết ⇒ không time-stop (stop sàn vẫn còn cho cụm đã arm).
9. Cùng symbol đóng rồi mở lại trong CÙNG phút bar ⇒ cid `c3-<tok>-<barMin>-0` lặp; nếu lần gửi sau timeout, `queryOrder(cid)` có thể trả lệnh
   cũ đã FILLED ⇒ xác nhận nhầm. Hiếm; thêm hậu tố seq.
10. ALLUSDT (PERPETUAL, underlyingType=INDEX, TRADING) vào universe + market index (BTCDOM cùng loại bị loại bằng UNIVERSE_EXCLUDE);
    PREDICTUSDT (PREMARKET) bị coi TradFi. MASTER quyết: thêm `ALLUSDT:intentional` vào UNIVERSE_EXCLUDE?
11. Chưa có unit test phân loại TradFi trên dump thật (A1 đã kiểm ngoài repo: 0 lọt) — thêm test khoá con số 225/514.
12. Script deploy: `KILLSW_SH` mặc định trỏ vào worktree tác giả (đổi được, không pin md5); hậu kiểm thiếu "0 `[KILLSW] LATCH`"; rollback không có `time_ok`.
13. `test_fake242.sh` kiểm luồng script (23/23 PASS khi A1 chạy lại) nhưng log "sau start" là chuỗi giả do chính test ghi ⇒ không kiểm được JVM thật
    (giới hạn đã biết — CRIT-1 lọt qua đây).
14. C3 (lỗi API liên tiếp) dùng chung bộ đếm với REST tài khoản CHÍNH (`updatePositionInfo`) ⇒ sự cố REST tài khoản chính cũng latch C3 của c3_live
    (bảo thủ, tự gỡ). Ghi nhận.
15. Dry: exchangeInfo tĩnh lúc deploy ⇒ STALE vô hiệu, symbol niêm yết sau deploy = NOT_LISTED (tác giả đã ghi).
16. Race nhỏ: trailing (thread OPS) đặt stop mới đồng thời stream (`closedOnExchange`) huỷ stop ⇒ có thể còn 1 stop `c3s-` mồ côi tới lượt quét
    hằng giờ; DCA confirm (thread EXEC) có thể bị `setTrail` (thread OPS) ghi đè reset arm — thực tế gần như không xảy ra (DCA −50 % khi đã arm +7 %).
17. Hourly reconcile đọc lỗi ⇒ không chặn (A40 vẫn hoạt động) — chấp nhận được.

## 6. Fail-open (mục 4 checklist)

| tình huống | hành vi hiện tại | đánh giá |
|---|---|---|
| equity null / account() lỗi | `capital()=null` ⇒ NO_EQUITY; A40 giữ trạng thái + C3 đếm lỗi | đúng (đóng) |
| universe rỗng / chưa có / cũ > 60′ | NO_SNAPSHOT / NOT_LISTED / STALE ⇒ không mua | đúng (đóng) |
| market index chưa có | market level KHÔNG lọc TradFi + WARN 10′ | mở có chủ đích (không phải cổng tiền) |
| feature filter TradFi chưa có universe | không lọc + WARN | như trên |
| exchangeInfo thiếu | rules null ⇒ NO_RULES; trailing không đặt stop + WARN | đóng (stop: xem MIN-6 tương tự) |
| AccountModeGuard đọc lỗi | MODE_GUARD (global/symbol) ⇒ không mua | đúng (đóng) |
| book file hỏng lúc nạp | `.corrupt_<ms>`, healthy=false ⇒ BOOK_UNHEALTHY; vị thế sàn ⇒ "vị thế lạ" ⇒ chặn + Telegram | đúng |
| book ghi lỗi | không gửi entry; trailing không đặt stop | entry đúng; stop: MIN-6 |
| latch file hỏng | latch NO_NEW_ENTRY code STATE (owner) | đúng |
| latch file bị xoá khi đang latch | ghi lại | đúng |
| user stream mất | fallback REST 10 s + Telegram 5′ | đúng; nhưng MAJ-2 |
| reconcile startup đọc lỗi | BLOCK_STARTUP, thử lại 30 s | đúng |
| reconcile **chưa chạy** | **cho vào lệnh** | **sai — MAJ-1** |
| positions thiếu symbol / rỗng | coi phẳng ⇒ huỷ stop + xoá cụm | **sai — MAJ-2** |
| KS không ở ACT | KS_NOT_ARMED | đúng |
| prediction null / NaN gate | 0 entry / REJECT (C10) | đúng |
| runtime tạo lỗi | không push (đóng) nhưng không quản lý vị thế cũ | MIN-7 |
| HTTP 5xx / −1007 / timeout lệnh | TIMEOUT_UNKNOWN_STATE ⇒ tra theo cid sau cửa sổ ≥ recvWindow | đúng |
| mã lỗi lạ 4xx | coi "chắc chắn không khớp" ⇒ huỷ giữ chỗ (nếu thật ra đã khớp ⇒ Reconciler báo vị thế lạ, không nhân đôi) | chấp nhận |

## 7. Concurrency (mục 5)
Luồng: quyết định (tick selector/market, khoá `C3LiveEntry`), `C3LIVE-EXEC` (1 luồng), `C3LIVE-OPS` (5 s: flatten, trailing, reconcile, onBook),
`C3LIVE-STREAM` (FillAccounting, fallback), KS periodic (15 s). `LiveBookC3`: MỌI hàm `synchronized`, view bất biến; `C3LiveEntry.onLeg`
tuần tự hoá kiểm trùng + U + reserve; executor bỏ qua leg `inFlight`; `confirm/cancel` idempotent; `nextStopSeq/setTrail` no-op khi cụm đã xoá.
Không tìm thấy race dẫn tới lệnh trùng/over-size ⇒ không viết test stress (không có nghi vấn cụ thể); 2 race MIN ở §5.16.

## 8. Chất lượng test (mục 6)
`mvn -o package`: 574 test, 0 fail, 1 skip. Đọc kỹ: `C3LiveOrderExecutorTest.thousandRandomTrialsZeroDuplicates` (sàn giả đếm độc lập — tốt),
`ExitReplayParityTest/ExitParityEngine` (chạy song song `ShadowBookC3` THẬT — không chép logic), `C3LiveEntryTest.twentyFour…` (so với chính
`managerBudget` — kiểm nối dây, không kiểm công thức), `ReconcilerTest` (10), `C3LiveExitE2ETest` (9), `KillSwitchCapacityTest`,
`KillSwitchAutoReleaseTest`, `NoSecretInClassesTest` (quét lớp đã biên dịch), `SymbolRulesTest` (dump thật), `test_fake242.sh`.
Lỗ hổng: (a) KS trong e2e dựng với paperEquity=10 000 + không file đỉnh ⇒ che CRIT-1; (b) không test "vào lệnh trước startup" (MAJ-1);
(c) không test positions rỗng (MAJ-2); (d) không test TradFi trên dump thật; (e) fake242 tự ghi log mong đợi.

## 9. Script owner (mục 7)
`bash -n` 6/6 OK; `test_fake242.sh` A1 chạy lại: **23/23 PASS**, không còn process giả. Đọc kỹ: chặn ngày 2026-11-18 08:00 +07 (FORCE_DATE),
`time_ok` (:10–:44, tránh 07/19, 00:50–01:20, 12:50–13:20), DRY, YES in hoa, backup jar/env/start.sh + khôi phục env khi FAIL, md5 jar
cục bộ + trên 242, không in key (env chỉ thêm 8 dòng không bí mật; status chỉ in `LIVE_C3_*` = đường dẫn), rollback đổi tên sổ dry `.rb_<TS>`.
Thiếu: MIN-12; CRIT-1 cần thêm hậu kiểm LATCH. `LIVE_SEED_EXCLUDE_DECISION_MIN` để 0 ở dry là đúng GOLIVE §2 ("C11 OFF tới ngày D").

## 10. Điểm CHƯA XÁC MINH với sàn thật — xếp rủi ro + bài kiểm canary đề xuất (cho MASTER viết prereg G-CANARY)

| điểm | rủi ro | hậu quả nếu sai | fallback trong code |
|---|---|---|---|
| Lệnh với ký quỹ BFUSD, USDT=0 (Multi-Assets) — `newMarketOrder` được nhận? | CAO | không vào được lệnh (−2019) | không |
| Algo API `closePosition` thứ 2 cùng chiều (−4130?) | CAO | dời stop thất bại / có khoảng trống | qty+reduceOnly xen kẽ |
| URL private WS (`/private/ws/` vs `/ws/`) + định dạng ORDER_TRADE_UPDATE/ACCOUNT_UPDATE | TRUNG BÌNH | kế toán fill chậm (REST 10 s) | xoay URL + fallback REST |
| `ALGO_UPDATE` + cid/ot lệnh MARKET sinh khi stop kích | TRUNG BÌNH | lý do đóng = EXTERNAL + Telegram giả | sổ vẫn đúng nhờ `pa=0` |
| −2021 khi trigger đã vượt mark | THẤP–TB | không đóng kịp | đóng MARKET |
| `newOrderRespType=RESULT` trả FILLED + avgPrice | THẤP | phải tra lại | `queryOrder` |
| weight/rateLimits + header X-MBX-USED-WEIGHT-1M | THẤP | 429/418 | RateGuard 50 % |
| BFUSD trôi số dư / phí trả bằng tài sản khác ⇒ đối chiếu equity 1 % | TRUNG BÌNH | chặn mở mới giả | reanchor owner |

Kịch bản canary đề xuất (tài khoản con, 1 symbol thanh khoản cao có MIN_NOTIONAL 5 USDT, vd XRPUSDT; notional mỗi lệnh 20 USDT; tổng rủi ro < 2 USDT):
- K0 (chỉ đọc): account (tmb ≈ 10 000, multiAssets=true, dualSide=false), symbolConfig CROSSED/1x, exchangeInfo, listenKey + kết nối WS (ghi URL nào chạy), keepAlive ≥ 65′.
- K1 vào lệnh: 1 leg MARKET BUY 20 USDT qua executor ⇒ RESULT FILLED; ORDER_TRADE_UPDATE ≤ 2 s; sổ CONFIRMED; C2 tính có dấu; ledger/audit 12 cột.
- K2 stop: đặt closePosition STOP_MARKET MARK_PRICE ở −20 % (A), rồi closePosition ở −19 % (B) ⇒ ghi chấp nhận/−4130; huỷ A; `openAlgoOrders` = 1; `queryStop` theo clientAlgoId.
- K3 −2021: stop SELL trigger trên mark ⇒ ghi mã; bot đóng MARKET reduce-only.
- K4 stop kích thật: dời stop tới mark −0,15 % ⇒ kích; ghi ALGO_UPDATE + ORDER_TRADE_UPDATE (cid, ot) ⇒ sổ đóng lý do TRAILING, 0 stop mồ côi.
- K5 time-stop/X14 path: mở leg 2, gọi `closeCluster(TIME_STOP)` ⇒ phẳng, stop huỷ.
- K6 restart: kill JVM khi có vị thế + stop ⇒ khởi động lại ⇒ reconcile khôi phục 12 trường, không stop trùng, KHÔNG có lệnh nào trước dòng "reconcile khoi dong" (kiểm MAJ-1 đã sửa).
- K7 mất stream: URL sai đứng đầu ⇒ xoay URL + fallback REST; positions rỗng giả lập KHÔNG được làm mất stop (kiểm MAJ-2 đã sửa — trên mock trước).
- K8 đối chiếu equity: sau K1–K5 lệch ≤ 1 %; ghi phí/funding/BFUSD.
- Tiêu chí ĐẠT: 0 lệnh trùng cid, 0 stop mồ côi sau mỗi bước, sổ = sàn (qty/avg) 100 %, 0 latch KS ngoài kịch bản (kiểm CRIT-1 đã sửa),
  weight dùng < 50 % giới hạn, 0 key/secret/signature trong log, mỗi điểm bảng trên có kết quả ghi lại (mã chấp nhận/từ chối).

## 11. Artefact
`~/claude_master/v12/a1_parity/`: `build.log`, `jar/`, `22_ref 22_a1 23_ref 23_a1/` (parity), `a1_compare.json`, `bc/` (lớp giải nén), `tf.py/tf.out`
(TradFi), `chk/UniCheck.java`, `chk/ProofKs.java`, `buf.py` (C10 buffer), `fake242.out`.
Bản sao nhỏ trong repo: `docs/result/a1audit/` (ProofKs.java, UniCheck.java, tf.py + tf.out, buf.py, cmp.py, drv.py, a1_compare.json).
Thư mục lượt parity, cache, lớp giải nén, jar A1 và `target/` đã XOÁ sau khi lấy số (tái lập: build lại a896595f + `drv.py`).
