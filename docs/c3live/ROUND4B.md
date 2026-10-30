# ROUND4B — sửa A1 R4 (1 MAJOR + 7 MINOR) + chuẩn bị dry-run 11-18 trên tài khoản chính

Branch `v1.2/c3-live`, trên `95024bfc` (R4). Cùng ràng buộc R4: không push, không `git config`, không gọi Binance, không ssh/chạy
gì trên 242, không chạy script canary/deploy thật, không đụng `~/claude_master/canary_*`, không in/sửa `PrivateConfig`.
A1 R4 không thấy lệnh ghi nào ngoài phạm vi.

## 1. Phát hiện → sửa → test

| # | phát hiện (A1) | sửa | test |
|---|---|---|---|
| MAJOR-1 | spec "sàn **≠** ledger c3", code chỉ bắt **>**: LEGACY bán vào long c3 khi mất stream / qua restart ⇒ startup "sàn thắng" hạ sổ c3; `hourlyQty` chặn (A) EQUITY_MISMATCH vì LEGACY | `C3MergedGuard.observe`: sàn **<** qty c3 mở (sàn > 0, không leg treo) mà KHÔNG có bằng chứng thoát c3 ⇒ MERGED (đang chạy: 2 lần đọc cách ≥ 3 s; khởi động: NGAY, trước Reconciler). Bằng chứng định lượng như canary 3h: `evidencedExit` = executedQty lệnh `c3x-` (closeCid) + stop `c3s-` FINISHED/TRIGGERED ⇒ executedQty của `actualOrderId` (max với exitQty sổ); sàn ≥ confirmed − bằng chứng ⇒ giải thích được, không MERGED. Sàn = 0 vẫn đi đường "phẳng" (FlatConfirm). `Reconciler.setMergedPredicate`: startup KHÔNG ghi đè sổ c3 từ sàn cho symbol MERGED; `hourlyQty` bỏ qua symbol MERGED | `A1R4Test` (nguyên văn, 3/3), `major1_deficitWithC3EvidenceIsNotMerged`, `major1_hourlyQtySkipsMergedAndStartupNeverLowersBook` |
| MINOR-1 | khớp STOP cid không-c3 được coi là stop c3 theo heuristic | `C3StreamScope.isC3StopFill`: CHỈ khi `orderId` = `ai` của ALGO_UPDATE `c3s-`, hoặc `queryStop(c3s-)` (active/pending/cũ) trả `actualOrderId = orderId` (lane khẩn cấp, ≤ 3 lần cách 300 ms). Còn lại = khớp LEGACY ⇒ MERGED | `minor1_c3StopFillWithoutC3CidConfirmedByQueryStop`, `minor1_legacyStopFillOnC3SymbolIsForeignAndMerged` |
| MINOR-2 | `ScopeRefusal` đếm như lỗi API ⇒ có thể latch C3 NO_NEW_ENTRY toàn hệ | marker `api.ClientSideRefusal` (ScopeRefusal implements); `C3LiveOrderExecutor`, `TrailingStopManager.send`, `C3LiveFlattener` KHÔNG gọi `onApiResult(false)` cho nó (canary không bao giờ ném ⇒ hành vi canary giữ nguyên) | `minor2_scopeRefusalIsNotCountedAsApiError` |
| MINOR-3 | MERGED: realized c3 lấy `rp` sàn (giá vào trộn LEGACY) | `C3StreamScope.c3Rp`: symbol MERGED ⇒ `rp` = (giá khớp − avgPrice sổ c3) × qty (BÁN), 0 (MUA) trước khi vào `FillAccounting` | `minor3_mergedRealizedUsesC3BookAvgNotBlendedRp` |
| MINOR-4 | `C3StopProtector.check()` giữ khóa tới 61 s trên vòng ops | vòng ops gọi `kickProtect()` (thread `C3LIVE-PROTECT`, gộp lần gọi) — không bao giờ chặn ops | (nối runtime; logic check đã có test R6) |
| MINOR-5 | `refreshLegacy` không đánh dấu LEGACY cho vị thế không-c3 | `touchLegacy` cho vị thế không-c3 khi làm mới (symbol c3 vừa chốt: chỉ sau `TOUCH_AFTER_CLOSE_MS` 60 s — REST trễ) | `A1R4Test.a1r4_legacyOpensOnJustClosedSymbolDuringGapNoGlobalBlock` |
| MINOR-6 | "≥ 200 TF" tuyệt đối dễ gãy | `sourceProblem`: bắt buộc có trường contractType/underlyingType + ≥ **50** TradFi; giảm > 30 % so lần nhận trước ⇒ CHỈ cảnh báo (Telegram), vẫn nhận | `C3UniverseStrictTest` (cập nhật theo ngưỡng mới: 40 TF từ chối; 201 → 121 cảnh báo + nhận) |
| MINOR-7 | dry không có LEGACY ⇒ KPI dry lạc quan | runtime log WARN + Telegram lúc khởi động dry; ghi rõ ở §4 | — |
| §4 (đổi) | MERGED mất stop > 61 s: trước "không đóng" | sàn ≥ qty c3 (LEGACY cùng long) ⇒ đóng ĐÚNG qty c3 (`c3x-` reduceOnly, lane khẩn cấp; `C3MergedGuard.exchangeCoversC3` đọc vị thế thô trong lane khẩn cấp) — trung tính với LEGACY. Sàn < qty c3 / âm ⇒ vẫn KHÔNG đóng | `decision4_mergedLegacyAlsoLongStopLostClosesExactlyC3Qty`, `decision4_mergedDeficitStopLostDoesNotClose` |
| §13 (đổi) | `c3live_reanchor.sh` vô nghĩa ở qty mode | script TỪ CHỐI (exit 4) khi log khởi động gần nhất có `tai_khoan=CHINH(pham vi c3)` (jar R4+); Java: file `run/c3live_reanchor.req` bị tiêu thụ + Telegram "TU CHOI ... QTY c3" (không lặp hourly mỗi 5 s) | fake242 §22 |

## 2. Dry-run 11-18 — script MỚI `ops/c3live/deploy_v12_dry_r4.sh`

Chọn script mới (an toàn hơn sửa `deploy_v12_dry.sh`: script cũ + pin + 14 kiểm fake242 cũ giữ nguyên). Lệnh owner (1 lệnh, gõ YES 1 lần):

```
bash ~/claude_master/v12/c3live/ops/c3live/deploy_v12_dry_r4.sh
```

- `NJ` = `~/claude_master/v12/jar/binance-java-sdk-1.2.4.jar_v12_r4b`, `NJ_MD5` = **`7457200a70e55b202062492f07f0ae57`**. `OLD_MD5` =
  `dcae2e2bbb1a357bc15703b416d4dccb` (jar shadow v_t_m đang chạy: `deploy_v12_dry.sh`/`rollback_v12.sh` + log
  `fix_featdump_20261027_114x.log` "OK jar_dcae2e2b" — bằng chứng mới nhất); kiểm lại trên 242 ở bước 2, khác ⇒ TỪ CHỐI.
- Từ chối trước **2026-11-18 07:54 +07** trừ `FORCE=1`. Sau YES: tự chờ khung giờ hợp lệ (phút :10-:44, tránh 07:xx/19:xx,
  00:50-01:20, 12:50-13:20; tối đa 90′) TRƯỚC khi đổi bất cứ gì; `FORCE_TIME=1` bỏ chờ (chỉ khi MASTER báo).
- PRE (chỉ đọc): jar đang chạy = OLD_MD5, 1 process, `LIVE_PROFILE=c3_shadow`, `SHADOW_NO_PUSH=true` (process + env.sh), env.sh
  chưa có `LIVE_ADAPTER/LIVE_C3_/C3_CAPITAL`, không `LIVE_ENTRY_ENABLED=true`; DỪNG nếu đã có `run/c3live_book.json`,
  `run/c3live_merged.txt`, `run/c3live_equity_c3.json`, `run/killsw_latch.json`, `run/c3live_killsw_peak`.
- ENV_ADD: `LIVE_PROFILE=c3_live`, `LIVE_ADAPTER=dry`, `LIVE_KILLSW_MODE=act`, `LIVE_KILLSW_C2_SIGNED=1`, **`C3_CAPITAL=10000`**,
  file sổ/dry/MERGED/equity, `LIVE_C3_EXCLUDE_TRADFI_FEATURES=1`.
- exchangeInfo dump (từ 242): > 100 symbol, có `"contractType":"`, có `"underlyingType":"`, ≥ 50 TRADIFI — không ⇒ DỪNG, env khôi phục.
- Restart với watchdog PAUSE (`mkdir -p` + touch, xoá sau kiểm). Sau start: 0 `[KILLSW] LATCH` (120 s); CHK: env (c3_live, dry,
  act, `SHADOW_NO_PUSH=true`, `C3_CAPITAL=10000`), `LEGACY tren tai khoan chinh`, KHÔNG `exchangeInfo KHONG hop le`, KHÔNG `STALE`,
  0 `[C3-LIVE-ORDER]`, 0 `TU CHOI`, 0 exception … FAIL hoặc WAIT quá 5×120 s ⇒ **ROLLBACK TỰ ĐỘNG** (`rollback_v12.sh TS`, đổi tên
  thêm `c3live_merged.txt`/`c3live_equity_c3.json` thành `.rb_TS`). Rollback tay: `bash .../rollback_v12.sh <TS>`.

## 3. Test

- `mvn -o package -DskipTests=false`: **Tests run: 825, Failures: 0, Errors: 0, Skipped: 1 — BUILD SUCCESS (R4: 814; +3 `A1R4Test`, +8 `C3MainAccountR4bTest`)**.
- `A1R4Test` (chép NGUYÊN VĂN từ `~/claude_master/a1_r4_scratch`, `cmp` giống hệt): 3/3 PASS (A, B trước fail nay pass; không sửa assert).
- `ops/c3live/test/test_fake242.sh` trên `git archive HEAD`: **TEST PASS 170/170 (b5d1ce91, 12:3x–12:5x trong khung giờ: 151 kiểm cũ + 19 kiểm mới §22)** (thêm §22 cho `deploy_v12_dry_r4.sh` + reanchor
  qty mode + rollback file R4; các mục cũ không đổi assert).
- A1AdversarialTest/A1G3Test byte-identical; `canary/*` không đổi.

## 4. Giới hạn dry (MINOR-7)

Dry dùng `DryGateway` (không đọc tài khoản thật): 0 vị thế LEGACY, không LEGACY-busy / MERGED, ký quỹ không bị LEGACY chiếm,
không funding thật, không rate IP chung. KPI dry (số leg, PnL, chặn) **lạc quan** so với live trên tài khoản chính; runtime log
`[C3-LIVE] DRY tren tai khoan chinh ...` lúc khởi động. Phần tài khoản chính chỉ được chứng minh bằng mock (`MainAccountRig`, A1R4Test)
cho tới micro-live.

## 5. Jar / pin

- `~/claude_master/v12/jar/binance-java-sdk-1.2.4.jar_v12_r4b`, md5 **`7457200a70e55b202062492f07f0ae57`** (pin vào `deploy_v12_dry_r4.sh`).
- Canary: `canary/*` không đổi ⇒ không bump (`…_3k` / `fea29aea…`). Lớp dùng chung đổi (executor/trailing/flattener) chỉ khác ở
  nhánh `ClientSideRefusal` mà canary không bao giờ ném. `deploy_v12_dry.sh` không đổi.

## 6. MASTER cần duyệt

1. Bằng chứng thoát c3 chỉ xét `closeCid` HIỆN TẠI của cụm (lần gửi đóng cuối) + mọi stop c3s- sổ còn tham chiếu; lần đóng cũ hơn
   khớp một phần mà sổ đã quên ⇒ MERGED (an toàn: không đóng, không hạ sổ).
2. Sàn = 0 với sổ c3 > 0 không coi là MERGED (đường phẳng 3 lần đọc ⇒ đóng cụm EXTERNAL) — LEGACY bán đúng bằng qty c3 trong lúc mất
   stream sẽ được ghi như c3 bị đóng ngoài.
3. MINOR-5: vị thế không-c3 trên symbol c3 vừa chốt bị coi LEGACY sau 60 s ⇒ chặn (A)/(B) cho phần dư c3 thật (nếu sổ sai) không còn
   kéo dài; đổi lại không bao giờ (A) vì LEGACY (R3).
4. MERGED + sàn < qty c3: stop qty vẫn = qty c3 (spec R2); reduceOnly để sàn tự kẹp khi kích.
5. Xác nhận khớp stop c3 bằng `queryStop` chạy trên luồng stream (lane khẩn cấp, ≤ ~1 s); không xác nhận được ⇒ MERGED (giả dương an
   toàn: không đóng, KHẨN, tự gỡ khi cụm đóng).

## 7. Còn mở

1. Chưa chạy trên tài khoản thật / 242 (đúng lệnh cấm). Dry 11-18 không thử được nhánh LEGACY (§4).
2. `C3LiveRuntime` vẫn không có test end-to-end; nối giống `MainAccountRig`.
