# ROUND3K — K5 "TRƯỢT" do sàn tự EXPIRED stop closePosition + prior-loss cũ sau CANARY_RESET

Branch `v1.2/c3-live`, trên `a8448ab0` (3j). Chỉ code + test + pin + doc; **không** gọi Binance, **không** ssh ghi 242
(chỉ đọc), **không** chạy canary/flatten, **không** đụng `~/claude_master/canary_*`, **không** push, **không** `git config`,
**không** in/sửa `PrivateConfig`.

## 1. Yêu cầu → sửa → test

| # | yêu cầu (MASTER) | sửa | test |
|---|---|---|---|
| R1a | K5: sàn tự kết thúc stop `closePosition` (ALGO_UPDATE `X=EXPIRED/CANCELED`, đúng caid) ngay sau khi vị thế về 0 ⇒ **kết thúc hợp lệ**, ghi `stopEnd`, không TRƯỢT | `canary/CanaryEngine.java:2392` `k5()`: tách `guardOk`; gọi `stopEndExchangeReject(...)`; ghi `stopEnd = GUARD_CANCELED | EXCHANGE_TERMINAL | NONE`; giữ nguyên mọi assert cũ | `CanaryK5StopExpiredTest` T1 (đường guard), T3 (fixture thật 10-29), T2 (ma trận từ chối) |
| R1b | **Chỉ** chấp nhận khi: caid thuộc canary, vị thế sàn = 0 **đã xác nhận** (positionRisk + account), stop là `closePosition`, sự kiện **sau** lệnh đóng | `CanaryEngine.java:2448` `stopEndExchangeReject(entries, sid, sym, sinceMs, positionFlat, closePositionStop)`: trả lý do từ chối; `k5` tính `flat` từ `posAmt` + `acctAmt` **trước** khi quyết định | T2: `caid la` / `sai symbol` / `TRIGGERING` / `trước mốc` / `stop qty` ⇒ từ chối; T5 qty-mode; T4 end-to-end |
| R1c | `EXPIRED/CANCELED` khi vị thế **≠ 0** vẫn là **lỗi** (mất stop ⇒ đặt lại / đóng khẩn cấp) | `k5`: `exchangeTerminalWhy="vi the != 0"` → chỉ còn đường guard; fail message có `[vi the != 0]`; phiên canary TRUOT ⇒ `canary_early_run.sh` flatten (đường sẵn có) | T4: mock `keepPositionOnSell` + `expireStopsOnSellFill` ⇒ K5 **TRUOT**, `stopEnd=NONE`, `vi the con` cùng báo |
| R1d | Rà **đường PRODUCTION** (OwnStopGuard, TrailingStopManager, Reconciler, C3LiveRuntime): stop bị huỷ/expire khi vị thế còn ⇒ **đặt lại ngay** | `fill/FillAccounting.java:275` `onAlgoUpdate` bắt `CANCELED/EXPIRED`; `:284/:305` `onStopTerminal` bỏ stop active/pending khỏi sổ **ngay** để `TrailingStopManager` đặt lại; log + Telegram `STOP MAT` | `StopExpiredRePlaceTest` (3 ca) |
| R2 | `CANARY_PRIOR_LOSS_USDT` đúng ở **mọi** lần gọi JVM; tính lại `cl_cum_loss` **ngay sau reset**; bỏ sub-shell làm mất biến; thêm test fake242 | `ops/c3live/canary/canary_lib.sh`: `cl_early_reset` gọi `cl_cum_loss check` sau `mv`; `cl_cum_loss` đặt + export `CL_CUM_PRIOR_AT`; `cl_run` in `PRIOR_USED cmd=… prior=… tinh_luc=…` mỗi lần; `canary_early_run.sh` ghi dòng `prior dung cho phien` | fake242 mục 21 (3 assert) |
| R3 | Build + jar 3k + md5 + **cả** `CANARY_JAR` **và** `CANARY_JAR_MD5`; kiểm md5 bằng lệnh thật; fake242 trên git archive; A1 test byte-identical | `canary_lib.sh:34-35` → `…jar_v12dry_3k` + `fea29aea127886a63f60d23b3b9846dc` | xem §4 |

## 2. R1 — vì sao K5 TRƯỢT và cách sửa (không nới assert nào khác)

Phiên 10-29 (`report_20261029_112139/files/canary_20261029_112031_step_K5.jsonl`):
`c3x-ZECUSDT-29887460-1` FILLED 0.016 @1236,60 (T=…645611); `ALGO_UPDATE caid=c3s-ZECUSDT-29887460-1 X=EXPIRED`
(T=…645571, **+4 ms**); journal **0** dòng `cancelStop`. Code cũ đòi `lastCall("cancelStop").ok` ⇒ TRƯỢT oan.

Sau 3k: `k5()` chấp nhận **hoặc** guard cancel **hoặc** terminal của sàn, nhưng terminal chỉ khi **đủ 4 điều kiện**
(caid `c3s-` đúng stop của cụm canary; stop `closePosition` = `!stopQtyMode`; `positionRisk` **và** `account().positions`
đều 0; sự kiện `ts >= ts` lệnh đóng). `waitNoOwnStops`, "vị thế 0", "account phẳng", "0 algo mở" **giữ nguyên**.

`st.data` mới: `stopClosePosition`, `exchangeTerminal`, `exchangeTerminalWhy`, `stopEnd` (audit được, không phải suy luận).

### 2.1 Call-site đã rà (production)

| call-site | hành vi trước 3k | sau 3k |
|---|---|---|
| `fill/FillAccounting.java:275` `onAlgoUpdate` | chỉ đánh dấu `lastExitReason` khi `TRIGGERING/TRIGGERED/FINISHED`; **bỏ qua** `CANCELED/EXPIRED` | `:284` nếu terminal + cụm còn vị thế (hoặc còn leg chưa rõ) ⇒ `:305 onStopTerminal`: `book.retireActiveStop` + `removeOrphanStop` (stop đã chết, không đưa vào orphan) hoặc `clearPendingStop`; WARN + Telegram `STOP MAT` |
| `exit/TrailingStopManager.java:189` (không có giá) / `:271` `place(... "ARM")` | chỉ đặt stop khi `stopClientAlgoId == null` | **giữ nguyên**; nay là nơi đặt lại sau khi `onStopTerminal` gỡ stop — nhịp `EXIT_EVERY_MS` = **10 s** (`runtime/C3LiveRuntime.java:68,386`) |
| `exit/TrailingStopManager.java:385` `resolvePending` | pending `CANCELED/EXPIRED/REJECTED` ⇒ bỏ + đặt lại nhịp sau | giữ nguyên (đường pending) |
| `recon/Reconciler.java:410-413` | mỗi giờ: stop active không có trong `openStops` ⇒ `retireActiveStop` (đặt lại ở nhịp exit sau) | giữ nguyên — **dự phòng**; trước 3k đây là đường **duy nhất** khi sàn huỷ stop ⇒ có thể mất bảo vệ tới **1 h** |
| `recon/OwnStopGuard.java:68` | chỉ huỷ khi cả 2 nguồn vị thế phẳng / stop thay thế đang mở; `GONE` nếu không còn trên sàn | giữ nguyên (không nới điều kiện huỷ) |
| `risk/C3LiveFlattener.java:242 finalizeClosed` | đóng cụm ⇒ guard huỷ stop còn lại | giữ nguyên |
| `runtime/C3LiveRuntime.java:459` `trailing.step(px)` | — | mỗi 10 s; stop vừa bị gỡ sẽ được đặt lại trong nhịp kế tiếp |

Ghi chú "đặt lại NGAY": stream-driven (ms) + nhịp exit 10 s; **không** thêm vòng quét REST mới (tránh tăng weight).

## 3. R2 — prior loss cũ sau CANARY_RESET (bằng chứng 10-29)

`CANARY_CUMLOSS.md`: 09:55:22 `prior=0,0195`; 09:55:48 reset `run/canary → run/canary_prev_20261029_095515`;
09:55:31 → 11:11:23 keycheck/preflight + 11:21:43 keycheck cuối vẫn `0.0195`; trong khi K1…cleanup dùng `0,0397`.
Nguyên nhân: `canary_early_all.sh` tính `cl_cum_loss` **một lần trước reset**, biến ở tiến trình cha không được cập nhật;
`canary_early_run.sh` chạy bằng `bash` (tiến trình con) tự tính lại nên phần K đúng, nhưng các `cl_run` của cha thì không.

Sau 3k:
- `cl_early_reset` (`canary_lib.sh`) sau `mv` gọi `cl_cum_loss check` ⇒ `CL_CUM_PRIOR`/`CL_CUM_PRIOR_AT` cập nhật **ngay**;
  `export` để tiến trình con thấy; `canary_early_run.sh` vẫn tự tính lại ở đầu phiên (nguồn sự thật 242).
- `cl_run` in `PRIOR_USED cmd=<cmd> prior=<x> tinh_luc=<time>` **mỗi** lần gọi JVM ⇒ audit được từng lần.
- File kết quả phiên thêm dòng `prior dung cho phien (CANARY_PRIOR_LOSS_USDT): … — tinh luc …`.
- Giá trị thật hiện tại (đọc chỉ-đọc qua 242, 30/10 08:10): **0,1422 USDT** = 0,0195 (10-27) + 0,0201 (10-28) + 0,1025 (10-29);
  `prior` cho phiên mới (khi `run/canary` còn là phiên 10-29) = **0,0397**; sau reset/archive = **0,1422**.
- fake242 mục 21: dựng `run/canary` lỗ 0,0201 + `run/canary_prev_*` lỗ 0,0195, `CANARY_RESET=1` ⇒ cleanup thấy **0.0195**,
  preflight/status/step sau reset thấy **0.0396**, JVM nhận `CANARY_PRIOR_LOSS_USDT=0.0396`, file kết quả ghi 0.0396.

## 4. Build / jar / pin / test

- `mvn -o package -DskipTests=false` (JDK 11, maven 3.9.9): **Tests run: 793, Failures: 0, Errors: 0, Skipped: 1 — BUILD SUCCESS**
  (3j: 785; +8 = 5 `CanaryK5StopExpiredTest` + 3 `StopExpiredRePlaceTest`).
- Jar: `~/claude_master/v12/jar/binance-java-sdk-1.2.4.jar_v12dry_3k`, 100 405 775 bytes,
  md5 **fea29aea127886a63f60d23b3b9846dc**.
- `canary_lib.sh:34-35`: `CANARY_JAR` → `…_3k` **và** `CANARY_JAR_MD5` → `fea29aea…` (3j quên đường dẫn).
  Kiểm thật: `bash -c 'CANARY_MODE=early; . canary_lib.sh; md5sum < "$CANARY_JAR" | cut -c1-32'` = `fea29aea…` ⇒ `MD5_PIN_OK`.
- `A1AdversarialTest.java` md5 `d300ebb063f1f191dcd1391996aa915a`, `A1G3Test.java` md5 `3faefd287394e24eed09e569076d823e`
  — **không có trong** `git diff a8448ab0 --name-only` (byte-identical).
- fake242 (chạy trên **git archive** HEAD, không dùng cây làm việc): xem §5.

## 5. fake242 trên git archive

`git archive HEAD | tar -x -C /tmp/arc3k && bash ops/c3live/test/test_fake242.sh /tmp/fake3k`:
kết quả `TEST PASS n/n` (điền ở §5.1), gồm mục mới **21** cho prior-loss. Các mục cũ 1–20 giữ nguyên.

### 5.1 Kết quả

- Lần 1 (08:03–08:15): **152/153**, 1 FAIL `cl_run: CANARY_IP_WEIGHT_CAP=1700 toi JVM canary` — do mục **20c cũ** so khớp
  **nguyên dòng** `fake_env.log`; tôi đã lỡ thêm `PRIOR=…` vào cùng dòng. Sửa: prior ghi ra **file riêng** `fake_prior.log`,
  **không sửa** test cũ (20c trở lại PASS).
- Lần 2 (08:14–08:25, `git archive HEAD`): **TEST PASS 151/151, RC=0** — 147 kiểm cũ trong khung giờ + 4 kiểm mục 21
  (3j: 147/147 trong khung giờ, 149/149 ngoài khung giờ). `diff -r /tmp/arcchk/ops /tmp/arc3k/ops` = **giống hệt**
  (chỉ khác `CanaryK5StopExpiredTest.java` — file test không dùng trong fake242).
- Mục 21: `cleanup` (trước reset) `prior=0.0195`; sau reset `preflight/status/step` `prior=0.0396`; JVM nhận
  `CANARY_PRIOR_LOSS_USDT=0.0396`; file kết quả ghi `prior … 0.0396` + `tinh luc …`.

## 6. Bất thường / giới hạn

- Mock gọi guard **đồng bộ** nên T1 không tái hiện race 4 ms; ca EXPIRED thật được chứng minh bằng **T3 fixture nguyên văn**
  + T4 (đường từ chối) + test production.
- `onStopTerminal` dùng ước lượng vị thế theo sổ (`confirmedQty − exitQty`) + cờ `hasUnresolved`; nếu sàn báo stop chết
  đúng lúc fill đóng chưa xử lý xong, hệ có thể đặt lại 1 stop trong ≤ 10 s rồi `closedOnExchange` huỷ khi phẳng
  (an toàn: guard chỉ huỷ khi cả 2 nguồn phẳng).
- Chưa chạy canary thật (luật task); K5→K8 vẫn cần phiên canary sau khi MASTER duyệt jar 3k.
- Không sửa `A1*Test`, `CanaryLimits`, `RateGuard`, `CanaryGateway` phần guard.
