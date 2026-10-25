# V12_ROUND2C — vòng 2c: sửa CRIT-1 + MAJ-1 + MAJ-2 + MIN theo A1_AUDIT_V12 (@a896595f)

Branch tích hợp `v1.2/c3-live` (worktree `~/claude_master/v12/c3live`), tiếp từ `a896595f`. Agent v12exit (Claude Opus), 2026-10-25.
Báo cáo audit: `~/claude_master/v12/a1/docs/result/A1_AUDIT_V12.md` (branch `audit/a1` @3771705b).
Không push, không merge, không deploy, không gọi Binance, không đụng 242 (script chỉ chạy thử trên "242 giả" ở Oracle).

Commit vòng này (author "Claude agent", trailer đủ):

| commit | nội dung |
|---|---|
| `a577b1ef` | CRIT-1: C6 của c3_live dùng tmb thật so với đỉnh RIÊNG |
| `e6d4a356` | MAJ-1 + MAJ-2 (+ MIN-6 phần reconcile: nhận lại stop khi restart) |
| `dcf45e29` | MIN-5 (nạp sẵn symbolConfig), MIN-6 (trailing vẫn đặt stop khi sổ hỏng), MIN-7 (manage-only + thử tạo lại) |
| `321b7d44` | Universe theo quyết định MASTER (INDEX loại, PREMARKET = crypto) + test trên dump thật |
| `ff549d47` | MIN-1: Utils.java trả lại EOL CRLF gốc |
| `8e7a0bee` | Script owner: pin md5 killsw_reset.sh, hậu kiểm LATCH + rollback tự động, rollback có time_ok |
| (commit docs) | tài liệu này + `docs/result/round2c/` |

## 0. Risk-first (đọc trước)

1. **Lệch so với yêu cầu ở test CRIT-1 (b):** MASTER viết "tmb giảm 25 % so với đỉnh riêng thì latch đúng ngưỡng C6". Ngưỡng C6 trong code
   (và trong KILLSW_MENU / killsw_1018) là **−40 %** (`KillSwitchEngine.C6_DD`), nên giảm 25 % **KHÔNG** latch. Test khoá đúng hành vi hiện
   có: −25 % → NONE, −39,99 % → NONE, −40 % → FLATTEN. **Ngưỡng không bị đổi.** Nếu ý MASTER là C6 = −25 % thì đó là đổi ngưỡng, cần owner chốt.
2. **C6 và A40 ở c3_live nay cùng nguồn (tmb thật), cùng ngưỡng −40 %, cùng hành động FLATTEN**, nhưng đỉnh lưu ở hai chỗ:
   - C6: `run/c3live_killsw_peak` (khoá mới `LIVE_C3_KILLSW_PEAK_FILE`);
   - A40: `acct_peak` trong file latch.
   - `reset_peak=1` đặt lại cả hai. Hai đỉnh chỉ có thể lệch nhau khi một trong hai file hỏng hoặc bị xoá tay.
3. **CHƯA XÁC MINH với sàn:** `GET /fapi/v1/symbolConfig` không kèm symbol có trả đủ mọi symbol không (MIN-5).
   - Symbol vắng hoặc sai cấu hình → giữ đường cũ: kiểm và sửa ở leg đầu (vẫn đúng, chỉ chậm hơn).
   - Lỗi hoặc không hỗ trợ → thử lại sau 5′; gateway không hỗ trợ thì tắt nạp sẵn.
   - Cần kiểm ở canary K0.
4. **MAJ-2, bằng chứng (iii) chỉ đếm lệnh THƯỜNG đang mở** (`openOrders(sym)`), không đếm stop algo. Lý do: stop `closePosition` của bot
   vẫn có thể còn trên sàn sau khi vị thế đã bị đóng ngoài bot. Hệ quả: khi `positionRisk` trả rỗng giả **hai lần liên tiếp, cách nhau ≥ 5 s**,
   bot vẫn sẽ kết luận phẳng. Đây là đúng tiêu chí MASTER đặt ra; xác suất thấp hơn trước rất nhiều (trước chỉ cần 1 lần).
5. **MIN-7 manage-only không có unit test của runtime** (C3LiveRuntime đọc `Cfg` tĩnh). Đã kiểm bằng đọc code và build.
   - Dòng log khởi động có cờ `MANAGE_ONLY`, kèm Telegram.
   - Runtime tạo lỗi (ví dụ quyền key file sai) → thử lại mỗi 60 s, ERROR thưa 10′, Telegram thưa 30′. Khi sửa xong thì tự lên, không cần restart.
6. **Input model c3_live đổi thêm một chút:** ALLUSDT (INDEX) ra khỏi market index của c3_live (marketIndex 514 trên dump thật). Đường c3_shadow/sim không đổi (parity §3).
7. **MIN-6:** khi sổ không ghi được, trạng thái stop chỉ còn trong RAM.
   - Nếu JVM chết, lúc restart Reconciler **nhận lại** stop `c3s-` có giá cao nhất của cụm đã arm, thay vì huỷ.
   - Nếu sổ persist không kịp ghi trạng thái arm, cụm trông như chưa arm và stop đó bị huỷ như trước. Lúc đó trailing sẽ arm lại khi giá còn ≥ +7 %.

## 1. Finding × fix × test × trạng thái

| mã | sửa | test | trạng thái |
|---|---|---|---|
| **CRIT-1** | Xem "Chi tiết CRIT-1" ngay dưới bảng | `KillSwitchC3LivePeakTest` (8, xem dưới bảng); `test_fake242` #9 (LATCH → rollback tự động) | **ĐÃ SỬA** |
| **MAJ-1** | `Reconciler.blocks` khởi tạo sẵn `BLOCK_STARTUP`, chỉ gỡ khi `startup()` đọc sàn + đối chiếu XONG | `ReconcilerTest.entryBlockedBeforeStartupReconcile`; phần Reconciler của `proofKsRegression` | **ĐÃ SỬA** |
| **MAJ-2** | Xem "Chi tiết MAJ-2" dưới bảng | `ReconcilerTest` 3 test mới + `C3LiveFlattenerTest` 1 test mới (xem dưới bảng) | **ĐÃ SỬA** |
| MIN-1 | Utils.java trả lại CRLF; diff với 16de49a6 còn 2 dòng thật | `git diff --stat 16de49a6`: 3 dòng | ĐÃ SỬA |
| MIN-2 | Không sửa. X14 bật cho profile c3_live kể cả khi adapter tắt — giống c3_shadow (env 242 `LIVE_TS_MKT_EXT=1`) nên sổ giấy twin = shadow; không triển khai cấu hình đó | — | GHI NHẬN |
| MIN-3 | Không sửa. Vị thế c3_live ở tài khoản con, không lẫn danh sách tài khoản chính; C3LiveEntry chặn LEGACY | — | GHI NHẬN |
| MIN-4 | Không sửa. ×tier sau trần 4,5 % là cố ý để parity sổ giấy | — | GHI NHẬN |
| MIN-5 | Xem "Chi tiết MIN-5/6/7" dưới bảng | `AccountModeGuardTest` +2: đợt 24 leg 0 REST `symbolConfig`; cấu hình sai vẫn sửa ở leg đầu; lỗi thì thử lại sau 5′ | ĐÃ SỬA |
| MIN-6 | Xem "Chi tiết MIN-5/6/7" dưới bảng | `TrailingStopBookFailTest` (thư mục sổ chỉ đọc → vẫn đặt + dời stop, 1 Telegram); `ReconcilerTest.startupAdoptsOwnStop…` | ĐÃ SỬA |
| MIN-7 | Xem "Chi tiết MIN-5/6/7" dưới bảng | build + đọc code (không test runtime, §0.5) | ĐÃ SỬA (chưa có test runtime) |
| MIN-8 | Không sửa. Time-stop/X14 cần giá để quyết định defer. Cụm đã arm có stop trên sàn; feed chết thì C1 latch | — | GHI NHẬN |
| MIN-9 | Không sửa. Cid trùng khi đóng rồi mở lại cùng symbol trong CÙNG phút bar: hiếm, sửa phải đổi format cid + test idempotency của executor → để vòng sau / canary | — | MỞ (thấp) |
| MIN-10 | Giải bằng luật universe MASTER (§2): ALLUSDT/BTCDOMUSDT → `Reason.INDEX` | §2 | ĐÃ SỬA |
| MIN-11 | Test phân loại TradFi trên dump thật | `SymbolUniverseLiveTest.realDumpBuyableHasNoTradFiAndExpectedMembers` | ĐÃ SỬA |
| MIN-12 | Xem "Chi tiết MIN-12/13" dưới bảng | `test_fake242` 31/31 (8 mục mới) | ĐÃ SỬA |
| MIN-13 | Giới hạn còn: 242 giả không chạy JVM thật. Bù bằng: test CRIT-1 dựng engine qua đúng `OpsHooks.build`; deploy thật có hậu kiểm LATCH trên log JVM thật | — | MỘT PHẦN |
| MIN-14 | Không sửa. C3 dùng chung bộ đếm REST với tài khoản chính: bảo thủ, tự gỡ sau 30′ + 3 OK | — | GHI NHẬN |
| MIN-15 | Không sửa. exchangeInfo dry tĩnh lúc deploy | — | GHI NHẬN (đã có ở V12_EXIT §0.5) |
| MIN-16 | Không sửa. Race mồ côi stop / DCA–setTrail: hiếm; stop mồ côi được dọn mỗi giờ | — | GHI NHẬN |
| MIN-17 | Chấp nhận (A40 vẫn chạy) | — | GHI NHẬN |

**Chi tiết CRIT-1 — sửa:**
- `OpsHooks.newEngine` → `OpsHooks.build(...)`. Ở c3_live dựng engine với `Params.c6OwnPeak=true`, `paperEquity=null`, file đỉnh `OpsConfig.c3LivePeakFile()`. Mặc định là `run/c3live_killsw_peak`; nếu cấu hình trỏ trùng file shadow thì bỏ cấu hình đó, dùng mặc định và WARN.
- `KillSwitchEngine.onPaper` khi `c6OwnPeak`:
  - không sàn PAPER_EQUITY;
  - đỉnh = tmb hợp lệ đầu tiên;
  - equity ≤ 0 hoặc NaN → giữ trạng thái C6.
- `reset_peak=1` → đỉnh C6 = NaN và xoá file đỉnh riêng.
- Đường c3_shadow: cùng constructor như v1.1.
- Script `killsw_reset.sh`: đổi chữ mô tả.
- Rollback: đổi tên `run/c3live_killsw_peak` thành `.rb_TS`.

**Chi tiết CRIT-1 — 8 test trong `KillSwitchC3LivePeakTest`:**
- (a) có file shadow 35015,29 + PAPER_EQUITY 35000, gọi onBook(10000) ×20 → NONE, đỉnh 10000, file shadow không đổi byte/mtime;
- hồi quy ProofKs;
- đối chứng đường nối cũ → FLATTEN;
- (b) −25 %/−39,99 %/−40 %, đỉnh tăng 12000 → 7200 latch;
- equity không hợp lệ;
- (c) reset_peak=0 giữ đỉnh, reset_peak=1 đặt lại + xoá/ghi lại file, restart nạp file riêng;
- cấu hình file;
- đường shadow giống hệt constructor v1.1 (cùng log, cùng đỉnh).

**Chi tiết MAJ-2 — sửa:**
- Lớp mới `c3live.recon.FlatConfirm`, dùng chung cho Reconciler và Flattener.
- Chỉ kết luận phẳng khi có một trong các bằng chứng:
  - (i) `ACCOUNT_UPDATE pa=0` (đường FillAccounting sẵn có);
  - (ii) stop của bot FINISHED/FILLED, hoặc lệnh đóng của bot FILLED với `executedQty` ≥ qty sổ;
  - (iii) 2 lần đọc positionRisk liên tiếp cách ≥ 5 s đều phẳng VÀ `openOrders(sym)` rỗng.
- Chưa đủ bằng chứng → giữ cụm và stop, WARN, chặn vào lệnh symbol đó.
- `Reconciler.confirmPendingFlat()` gọi mỗi nhịp ops 5 s.

**Chi tiết MAJ-2 — test:**
- `ReconcilerTest` thêm 3:
  - rỗng 1 lần: không huỷ stop / giữ cụm;
  - 2 lần cách < 5 s: vẫn giữ; ≥ 5 s: huỷ;
  - vị thế xuất hiện lại: xoá nghi ngờ;
  - restart khi positions thiếu symbol.
- `C3LiveFlattenerTest.positionsMissingDoesNotFinalizeUntilConfirmed`.

**Chi tiết MIN-5/6/7:**
- MIN-5: `ExchangeGateway.symbolConfigs()` (gọi một lần cho mọi symbol; có bản live, dry và mock). `AccountModeGuard.prefetch/prefetchIfDue`: lúc start rồi mỗi giờ, cache ~70′, lỗi thì thử lại sau 5′. Runtime nạp cho `universe.tradableSymbols()`.
- MIN-6: `TrailingStopManager.send` khi sổ hỏng vẫn đặt/dời stop + ERROR + Telegram (thưa 10′). `Reconciler.startup` nhận lại stop `c3s-` cao nhất của cụm đã arm mà sổ mất tham chiếu.
- MIN-7: `C3LiveRuntime.get()`:
  - tạo lỗi → thử lại mỗi 60 s;
  - mọi nhánh lỗi đều ERROR (thưa 10′) + Telegram (thưa 30′);
  - phần vào lệnh (universe, modeGuard, entry) lỗi → MANAGE-ONLY (trailing, time-stop, X14, reconcile, FLATTEN vẫn chạy; hook bỏ leg);
  - `attachEquitySource` chỉ gọi khi tạo xong.

**Chi tiết MIN-12/13 — deploy:**
- pin md5 `killsw_reset.sh` = `6f8d8348…`;
- kiểm `rollback_v12.sh` có mặt và đúng cú pháp;
- sau restart chờ 120 s: có ≥ 1 dòng `[KILLSW] LATCH|NAP LATCH|FAIL-CLOSED` → **rollback tự động** (`YES_AUTO=1 FORCE_TIME=1`) và báo FAIL;
- các vòng kiểm sau đó: `FAIL` nếu có LATCH.

**Chi tiết MIN-12/13 — rollback:**
- `time_ok` giống deploy (khẩn cấp dùng `FORCE_TIME=1`);
- `YES_AUTO` chỉ dành cho deploy gọi.

## 2. Universe (quyết định MASTER)

- Buyable = status TRADING + contractType PERPETUAL + **underlyingType ≠ INDEX**, cộng các điều kiện cũ: USDT, không TradFi, ASCII, delivery ≥ 7 ngày, snapshot không cũ.
  - Chỉ số tổng hợp (ALLUSDT, BTCDOMUSDT) loại khỏi cả buyable lẫn market index: `Reason.INDEX`.
- `TradFiClassifier.DEFAULT_CRYPTO_UNDERLYING` thêm `PREMARKET`:
  - PREDICTUSDT không còn bị coi là TradFi, bị loại vì status `PENDING_TRADING`;
  - khi chuyển TRADING + PERPETUAL thì tự vào (có test).
- Dump thật `exchangeInfo_20261025_1457.json.gz` (log test):

  | listed | TRADIFI_PERPETUAL | buyable | marketIndex | TradFi trong buyable | TradFi trong index |
  |---|---|---|---|---|---|
  | 932 | 225 | **513** | 514 | **0** | **0** |

  - Lý do loại: NOT_TRADING 138, NOT_USDT 44, TRADFI 224, NOT_PERPETUAL 4, EXCLUDED 1, INDEX 2.
  - MDTUSDT loại (TRADFI), POWRUSDT có, ALLUSDT loại (INDEX).
  - So với A1 (514): giảm 1 = ALLUSDT.
- Không có dump → test bị skip.

## 3. Validation

- **Build** `mvn -o package -DskipTests=false`: **593 test, 0 fail, 0 error, 1 skip** (skip có sẵn). Vòng 2b: 574.
  - Test mới/sửa: KillSwitchC3LivePeakTest 8, ReconcilerTest 10→15, C3LiveFlattenerTest 3→4, TrailingStopBookFailTest 1, AccountModeGuardTest 7→9, SymbolUniverseLiveTest 6→8 (sửa 1 assert BTCDOM → INDEX).
- **Jar** (build từ cây = `ff549d47`): md5 **`ff717f380688a358c6830a7e0fadba04`**.
  - Nằm ở `~/claude_master/v12/jar/binance-java-sdk-1.2.4.jar_v12dry_2c`; `deploy_v12_dry.sh` mặc định trỏ vào đây.
  - Jar 2b `…_v12dry` (a55be721, còn CRIT-1) đã xoá khỏi `jar/`; bản lưu ở `exit_parity/jar` chỉ để audit.
- **Parity offline cờ TẮT** (giống cách A1: `drv.py`, mỗi lượt tự dựng cache, `~/claude_master/v12/r2c_parity/`): **ĐẠT cả 2 ngày.**

  | ngày | out_BT = out_NEW2 | fund_BT | fund_NEW2 | trùng jar dcae2e2b |
  |---|---|---|---|---|
  | 2026-10-23 | `e0918a33…` (1 441 dòng) | `a81b3b03…` | `8dea3f70…` | 4/4 ✓ |
  | 2026-10-22 | `2c7c336d…` (1 441 dòng) | `1a6d1521…` | `f4acab23…` | 4/4 ✓ |

  - CTL gate 1440/1440 cả 2 ngày (only_ref/only_new 0, mọi cột bit = 1).
  - CTL fund y hệt jar ref: 10-23 f3 0,94586 + cand 0,99750; 10-22 f3 0,94425 — đặc tính có sẵn của harness, A1 đã ghi.
  - strace: 0 connect AF_INET ngoài loopback (BT + 3 segment NEW2 mỗi ngày); rc 0.
  - Chi tiết: `docs/result/round2c/r2c_compare.json`.
- **Script owner** `test_fake242.sh`: **31/31 PASS**. Mới:
  - md5 pin killsw;
  - kiểm 0 LATCH sau start;
  - rollback từ chối ngoài khung giờ;
  - đổi tên đỉnh C6;
  - LATCH → rollback tự động: env về c3_shadow, jar cũ, process chạy c3_shadow.
- Đường c3_shadow chạm các lớp cũ: `KillSwitchEngine`, `OpsHooks`, `OpsConfig` (nhánh mới chỉ khi `C3LIVE` hoặc `c6OwnPeak`) và `Utils` (chỉ EOL, nội dung = 2b).
  - Quyết định không đổi: `shadowPathIdenticalToV11Construction` + parity.
  - Bytecode diff vòng này để A1.

## 4. Còn mở

1. Câu hỏi ngưỡng C6 (§0.1).
2. MIN-9 (cid cùng phút) — để vòng sau / canary.
3. Kiểm `symbolConfig` không kèm symbol ở canary K0 (§0.3).
4. A1 audit lại vòng 2c (bytecode diff + đọc nguồn) trước G-CODE.
5. Như V12_EXIT §4: canary xác minh −4130, URL WS, ALGO_UPDATE, −2021; dry-run parity trên 242 sau 11-18.

## 5. Cấu hình mới

| key | mặc định | ý nghĩa |
|---|---|---|
| `LIVE_C3_KILLSW_PEAK_FILE` | `run/c3live_killsw_peak` | đỉnh C6 riêng của c3_live (không được trùng `LIVE_KILLSW_STATE_FILE`) |

Script: `KILLSW_MD5`, `RB_SH`, `LATCH_WAIT_S` (deploy); `FORCE_TIME`, `YES_AUTO` (rollback).

## 6. API công khai mới/đổi

```java
// ops
static KillSwitchEngine OpsHooks.build(Mode, String label, Sink, boolean c3live, File shadowPeakFile, File c3livePeakFile,
    DoubleSupplier paperEquity, Supplier<Float> uMax, long nowMs, KillSwitchEngine.Params)          // package-private
KillSwitchEngine.Params.c6OwnPeak; OpsConfig.c3LivePeakFile(); OpsConfig.KEY_C3LIVE_KILLSW_PEAK_FILE
// c3live.recon
public final class FlatConfirm { FlatConfirm(ExchangeGateway, ApiObserver, long minGapMs); boolean observeFlat(String sym, long now, String who);
  void clear(String); void retainOnly(Set<String>); boolean isPending(String); boolean anyDue(long); Set<String> pending(); }
Reconciler(…, File reanchorFile, FlatConfirm flat); Report confirmPendingFlat(); Set<String> flatPending(); Report.flatPending
// c3live.risk
C3LiveFlattener(…, long safeRetryMs, FlatConfirm flat)
// c3live.api / guard
default List<SymbolConfig> ExchangeGateway.symbolConfigs();   // C3LiveClient, DryGateway, Mock cai
int AccountModeGuard.prefetch(Collection<String>); int prefetchIfDue(Collection<String>); int prefetchedCount()
// c3live.universe
SymbolUniverseLive.Reason.INDEX; TradFiClassifier.DEFAULT_CRYPTO_UNDERLYING += PREMARKET
```

## 7. File đổi

- **Main:** `ops/{KillSwitchEngine,OpsHooks,OpsConfig}.java`, `utils/Utils.java` (EOL); `c3live/recon/{Reconciler,FlatConfirm(mới)}.java`, `c3live/risk/C3LiveFlattener.java`, `c3live/exit/TrailingStopManager.java`, `c3live/guard/AccountModeGuard.java`, `c3live/api/ExchangeGateway.java`, `c3live/client/C3LiveClient.java`, `c3live/adapter/DryGateway.java`, `c3live/runtime/{C3LiveRuntime,C3LiveHook}.java`, `c3live/universe/{SymbolUniverseLive,TradFiClassifier}.java`.
- **Test:** `ops/KillSwitchC3LivePeakTest` (mới), `c3live/exit/TrailingStopBookFailTest` (mới), `c3live/recon/ReconcilerTest`, `c3live/risk/C3LiveFlattenerTest`, `c3live/guard/AccountModeGuardTest`, `c3live/universe/SymbolUniverseLiveTest`, `c3live/mock/MockExchangeGateway`.
- **Script:** `ops/killsw_reset.sh` (chữ), `ops/c3live/{deploy_v12_dry,rollback_v12}.sh`, `ops/c3live/test/test_fake242.sh`.
