# V12_ROUND2D — vòng 2d: MAJ-2b + MIN-18 + MIN-19 + hậu kiểm LATCH (A1_DELTA_2C @4dd8ddaf)

Branch `v1.2/c3-live` (worktree `~/claude_master/v12/c3live`), tiếp từ `9c5a786f`. Agent v12exit (Claude Opus), 2026-10-25.
Báo cáo audit: `~/claude_master/v12/a1/docs/result/A1_DELTA_2C.md`; proof `docs/result/a1audit/2c/ProofFlat.java`.
Không push, không merge, không deploy, không gọi Binance, không đụng 242.
Ngưỡng C6 = −40 % là đúng (MASTER xác nhận 10-25); test (b) của vòng 2c giữ nguyên.

| commit | nội dung |
|---|---|
| `019f64f0` | MAJ-2b (FlatConfirm (iii) = (a)+(b)+(c)) + MIN-18 (gỡ UNKNOWN cần 2 lần đọc nhất quán) + `AccountSnapshot.positions` |
| `2547174c` | MIN-19: đỉnh C6 + acct_peak gắn nhãn adapter; khác nhãn → bỏ qua |
| `2b3628d1` | Hậu kiểm LATCH đếm theo mốc thời gian, gồm log đã xoay, fail-closed + pin jar 2d + test 242 giả 35/35 |
| (commit docs) | tài liệu này + `docs/result/round2d/` |

## 0. Risk-first

1. **(b) dựa vào mảng `positions` của `GET /fapi/v3/account` — CHƯA XÁC MINH với sàn thật.**
   - Code đọc mảng đó. Nếu sàn không trả mảng hoặc mảng thiếu `positionAmt`, (b) không bao giờ thoả, nên bot **không bao giờ** kết luận phẳng qua (iii).
   - Hệ quả là fail-safe: giữ cụm và stop; chỉ còn (i) stream `pa=0`, (ii) lệnh đóng/stop của bot khớp, hoặc owner xử lý.
   - Cần kiểm ở canary K0 (đọc account khi đang có vị thế).
2. **Còn stop `c3s-` NEW mà vị thế đã thật sự phẳng** (owner đóng tay, hoặc sàn thanh lý trong lúc mất stream) → bot giữ cụm **vô thời hạn**.
   - Có 1 Telegram WARN.
   - Stop sống tiếp là vô hại (closePosition reduce-only), nhưng sổ giữ 1 "cụm ma": chiếm margin sổ và chặn vào lệnh symbol đó cho tới khi owner huỷ stop (lần đọc sau tự kết luận) hoặc stream nối lại kèm `ACCOUNT_UPDATE`. Đây là đúng thiết kế MASTER.
3. **Kết luận phẳng bằng (iii) nay mất ≥ 60 s** (3 lần đọc cách ≥ 30 s; `confirmPendingFlat` chạy mỗi nhịp 5 s).
   - Không ảnh hưởng các đường thường: time-stop/X14/FLATTEN có lệnh đóng FILLED đủ qty → (ii) kết luận ngay; stop kích có trạng thái FINISHED/FILLED → (ii); stream `pa=0` → (i).
4. **Gỡ chặn UNKNOWN_POSITION chậm hơn:** cần 2 lần đọc cách ≥ 30 s, và lần đọc thứ 2 có thể chỉ tới ở lượt hằng giờ nếu stream đang sống. Bảo thủ, có chủ đích.
5. **MIN-19 chỉ phủ đỉnh** (C6 + acct_peak). Các trạng thái khác trong file latch (latch đang bật, sự kiện C2) của dry vẫn mang sang nếu chuyển dry→live mà không rollback.
   - Rollback đã đổi tên `killsw_latch.json` + `c3live_killsw_peak`.
   - Script chuyển dry→canary chưa có; khi viết phải đổi tên file latch.
6. **Hậu kiểm LATCH so timestamp log với `date` của shell 242** (cùng TZ).
   - Nếu TZ của JVM lệch TZ shell theo chiều âm thì không thấy dòng start → FAIL + rollback. Đây là fail-closed, nhưng có thể FAIL giả. Định dạng log thật `dd/MM/yyyy HH:mm:ss.SSS` đã đối chiếu từ log 242 kéo về (`pull242/…/full.log`).

## 1. Finding × fix × test

| mã | sửa | test | trạng thái |
|---|---|---|---|
| **MAJ-2b** | Xem "Chi tiết MAJ-2b" dưới bảng | Xem "Chi tiết MAJ-2b" dưới bảng | **ĐÃ SỬA** |
| MIN-18 | `Reconciler.unknownCheck`: vị thế lạ chỉ coi là "hết" khi ≥ 2 lần đọc nhất quán cách ≥ 30 s; lần đọc thấy lại thì xoá mốc; `confirmPendingFlat` cũng chạy khi có mốc UNKNOWN đến hạn | `unknownBlockNotReleasedByOneEmptyRead`; sửa `unknownPositionBlocksEntryUntilGone` | ĐÃ SỬA |
| MIN-19 | Xem "Chi tiết MIN-19" dưới bảng | `KillSwitchC3LivePeakTest` +2 (xem dưới bảng) | ĐÃ SỬA |
| MIN hậu kiểm LATCH | Xem "Chi tiết hậu kiểm LATCH" dưới bảng | `test_fake242` **35/35**, mới #10/#11/#12 (xem dưới bảng) | ĐÃ SỬA |

**Chi tiết MAJ-2b — sửa** (`FlatConfirm` (iii) phải đủ cả 3 điều):
- (a) ≥ 3 lần đọc positionRisk liên tiếp, cách nhau ≥ 30 s, đều vắng/0. Lần đọc < 30 s không được tính; lần đọc thấy vị thế thì xoá mốc.
- (b) `account().positions` (`/fapi/v3/account`, thêm `AccountSnapshot.positions`; live/dry/mock đều có) vắng symbol hoặc amt = 0. Mảng null → không đủ.
- (c) 0 algo `c3s-` NEW cho symbol. Còn stop → giữ cụm + stop + **Telegram WARN 1 lần**.
- Thêm điều kiện: 0 lệnh thường mở.
- Dùng chung cho Reconciler và Flattener; alert được nối vào runtime.

**Chi tiết MAJ-2b — test:**
- Hồi quy ProofFlat `proofFlatRegressionGlitchNeverCancelsStopOfRealPosition`: glitch, 6 lần đọc 10–30 s → không huỷ stop, không xoá cụm.
- Thiếu (a) `conditionA_needsThreeReadsThirtySecondsApart`: đọc < 30 s không tính; lần thứ 3 mới phẳng.
- Thiếu (b) `conditionB_accountPositionsMustAlsoBeFlat`: account còn vị thế / mảng null → giữ.
- Thiếu (c) `conditionC_openOwnStopBlocksFlatConclusionWithSingleAlert`: giữ, đúng 1 Telegram; owner huỷ stop → phẳng.
- `positionReappearsClearsSuspicion`, `startupWithMissingPositionKeepsClusterUntilConfirmed`.
- Flattener: `positionsMissingDoesNotFinalizeUntilConfirmed` (3 lần cách 30 s) và `openOwnStopKeepsClusterInFlattener`.

**Chi tiết MIN-19 — sửa:**
- `Params.peakTag` = adapter (`OpsHooks.build` lấy từ `LIVE_ADAPTER`: dry|live|off).
- File đỉnh C6 ghi `"<đỉnh> adapter=<nhãn>"`; file latch ghi `acct_peak_adapter`.
- Nạp đỉnh khác nhãn hoặc không nhãn → **BỎ QUA + WARN**; đỉnh lấy lại từ tmb thật đầu tiên.
- c3_shadow (`peakTag=null`) giữ định dạng cũ.

**Chi tiết MIN-19 — test** (`KillSwitchC3LivePeakTest` +2):
- `dryPeaksIgnoredWhenAdapterChangesToLive`: dry 12000 → live tmb 10000 → NONE, cả 2 đỉnh = 10000, có WARN.
- `untaggedOldPeakFileIgnoredForC3Live`.

**Chi tiết hậu kiểm LATCH — sửa:**
- Lúc restart ghi mốc `run/.v12_start_epoch`.
- Đếm `[KILLSW] LATCH|NAP LATCH|FAIL-CLOSED` trên các dòng có timestamp ≥ mốc. Đọc `full.log` + `full.log.N` + `*.gz` mới hơn mốc; dòng không có timestamp theo dòng trước.
- Hỗ trợ cả `dd/MM/yyyy …` và `yyyy-MM-dd …`.
- Không đọc được, thiếu mốc, thiếu `full.log`, hoặc không thấy dòng `MainClass` sau mốc → giá trị khác 0 → **FAIL + rollback tự động**.

**Chi tiết hậu kiểm LATCH — test mới:**
- #10: mất log → `no_log` → FAIL + rollback.
- #11: log xoay, LATCH nằm ở `full.log.1` → `LATCH_COUNT=1` → FAIL + rollback.
- #12: log xoay, không LATCH → `LATCH_COUNT=0 files=2`, qua bước này.

## 2. Validation

- **Build** `mvn -o package -DskipTests=false`: **600 test, 0 fail, 0 error, 1 skip** (skip có sẵn). Vòng 2c: 593.
  - ReconcilerTest 15→19, C3LiveFlattenerTest 4→5, KillSwitchC3LivePeakTest 8→10.
- **Jar dry 2d** (build từ cây = `2547174c`, mã Java = HEAD): md5 **`6829a6ed00c72453b053c952eed01633`**.
  - Nằm ở `~/claude_master/v12/jar/binance-java-sdk-1.2.4.jar_v12dry_2d`; `deploy_v12_dry.sh` pin jar này.
  - Jar 2c (`…_v12dry_2c`, ff717f38, còn MAJ-2b) đã xoá.
  - Pin `killsw_reset.sh` giữ `6f8d8348…` (file không đổi).
- **Parity offline cờ TẮT 2026-10-23** (cách A1, cache tự dựng, `~/claude_master/v12/r2d_parity/`): **ĐẠT.**
  - md5 sau khi giải nén khớp jar dcae2e2b 4/4:
    - out_BT = out_NEW2 = `e0918a333a52be3aefe2a3b62a5ac8f4` (1 441 dòng);
    - fund_BT = `a81b3b03915a44d418ee23488d71d226`;
    - fund_NEW2 = `8dea3f700aaddfd6abad961af1c65ea7`.
  - CTL gate 1440/1440, bit = 1.
  - CTL fund y hệt ref (f3 0,94586, cand 0,99750 — có sẵn).
  - strace: 0 AF_INET ngoài loopback.
  - Chi tiết: `docs/result/round2d/r2d_compare.json`.
- Đường c3_shadow trong vòng này chạm:
  - `KillSwitchEngine`: nhánh mới chỉ khi `peakTag != null`, tức chỉ ở c3_live;
  - `OpsHooks.build`: nhánh c3live.
  - Các lớp c3live khác không nằm trên đường shadow.

## 3. Còn mở

1. Xác minh `positions` trong `/fapi/v3/account` ở canary K0 (§0.1).
2. Script chuyển dry → canary/live: chưa có. Khi viết phải đổi tên `killsw_latch.json` (đỉnh đã tự bỏ qua theo nhãn) (§0.5).
3. Từ vòng trước: MIN-9 (cid cùng phút), symbolConfig không kèm symbol (K0), MIN-7 manage-only chưa có test runtime, các điểm canary của V12_EXIT §4.
4. A1 audit delta vòng 2d.

## 4. Interface đổi

```java
public FlatConfirm(ExchangeGateway, ApiObserver, Consumer<String> alert, long minGapMs, int minReads)   // + ctor 3 tham so cu
FlatConfirm.DEFAULT_MIN_GAP_MS = 30_000; DEFAULT_MIN_READS = 3; long minGapMs()
AccountSnapshot(…, long timeMs, List<PositionInfo> positions); List<PositionInfo> getPositions()   // null = khong biet
KillSwitchEngine.Params.peakTag; static String OpsHooks.adapterTag(String)   // package-private
```

## 5. File đổi

- **Main:** `c3live/recon/{FlatConfirm,Reconciler}`, `c3live/risk/C3LiveFlattener`, `c3live/runtime/C3LiveRuntime`, `c3live/api/AccountSnapshot`, `c3live/client/C3LiveClient`, `c3live/adapter/DryGateway`, `ops/{KillSwitchEngine,OpsHooks}`.
- **Test:** `c3live/recon/ReconcilerTest`, `c3live/risk/C3LiveFlattenerTest`, `ops/KillSwitchC3LivePeakTest`, `c3live/mock/MockExchangeGateway`.
- **Script:** `ops/c3live/deploy_v12_dry.sh`, `ops/c3live/test/test_fake242.sh`.
