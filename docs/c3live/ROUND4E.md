# ROUND4E — sửa A1 (audit 4c + 4d): MAJOR-1 exchangeInfo đóng băng + MINOR-1..4

Branch `v1.2/c3-live`, trên `41fb7814` (R4d). Ràng buộc giữ nguyên: không push, không `git config`, Oracle không gọi Binance,
không ssh/chạy gì trên 242, không chạy script canary/deploy thật, không đụng `~/claude_master/canary_*`, không in/sửa
`PrivateConfig`. Mọi test A1 **byte-identical** (A1Adversarial/A1G3/A1R4Test và `A1R4bTest` = bản siết của A1 trong repo, không sửa).

## 1. Phát hiện → sửa → test

| # | phát hiện (A1) | sửa | test |
|---|---|---|---|
| MAJOR-1 | Snapshot exchangeInfo đóng băng suốt dry-run (A1 + R7 cùng file) ⇒ coin niêm yết sau deploy bị loại ở cả hai phía, backtest thì có ⇒ lệch hệ thống. Live: R7 đọc API, A1 đọc file đóng băng; `checkA1SameSource` chỉ chạy ở dry | **Làm mới trên 242**: `ops/c3live/exinfo_refresh_242.sh` (cron root, marker `# C3LIVE_EXINFO_REFRESH`, phút `3,18,41,48` — mỗi ≤ 23', ngoài cửa sổ [27,40]). Mỗi lần: `curl` → `run/c3live_exchangeInfo.json.new` → `python3 -I` kiểm JSON, `serverTime` > 0 **và mới hơn** file hiện tại, > 100 symbol, **mọi** symbol có `onboardDate` + `underlyingType`, ≥ 50 TF, số symbol giảm ≤ 10 % ⇒ hợp lệ: `.lastgood` + `mv -f` (nguyên tử); không: giữ file cũ, đếm lỗi liên tiếp, lần 3 (rồi mỗi 4 lần) ⇒ Telegram qua `tg.env` của watchdog 242 (không đọc được ⇒ `run/ALERT_PENDING_exinfo.txt`), hồi phục ⇒ báo. Phân loại TF/INDEX vẫn CHỈ ở Java (`UniverseA1Classifier`); script chỉ kiểm nguồn thô. **JVM**: A1 đã reload theo mtime (≤ 60 s). **Gap tìm thấy**: R7 chỉ refresh mỗi 15' ⇒ `C3LiveRuntime.a1SourceTick` refresh R7 **ngay** khi mtime file đổi (cùng nhịp ops) ⇒ hai phía đổi universe gần như đồng thời; file cũ > 45' ⇒ KHẨN (thưa 30', lớp dự phòng cho Telegram phía 242). **Live — chọn: R7 đọc CÙNG file làm mới ở cả dry lẫn live** (`GatewayFactory.freshFileSource`, không bao giờ đọc API cho universe) + kiểm tuổi `serverTime` ≤ 45' (cũ ⇒ R7 từ chối snapshot mới, giữ cũ; quá 60' ⇒ STALE, không mua). Lý do: một nguồn ⇒ không thể lệch theo cấu trúc; phương án "mở rộng `checkA1SameSource` sang live + so tuổi/serverTime" chỉ lấy mẫu định kỳ, hai nguồn vẫn có thể khác nội dung giữa hai lần kiểm. (Bộ lọc giá/lot `SymbolRules` ở live vẫn từ gateway — không phải quyết định universe.) **Deploy**: PRE kiểm `python3`, `crontab`, marker **chưa** có; bước 4c (sau kiểm file A1, trước restart, bot cũ còn chạy) chép script (pin `EXR_MD5`, `bash -n`), sao lưu crontab, cài 1 dòng, xác nhận giữ nguyên các dòng cron khác; lỗi ⇒ khôi phục env + gỡ marker + dừng. CHK: file < 30' + đúng 1 dòng cron. Rollback: gỡ theo marker (`crontab -l` lỗi lạ ⇒ FAIL, không bao giờ ghi đè) | `UniverseA1ListingRefreshTest` (snapshot thật: symbol "niêm yết sau deploy" bị loại ở A1 + không mua được ở R7; file làm mới tới ⇒ vào **cả hai**; file quá 45' ⇒ R7 từ chối); fake242 §25: làm mới hợp lệ (listing mới, `.lastgood`), thiếu `onboardDate` / `serverTime` không mới hơn / giảm > 10 % / JSON hỏng ⇒ giữ file cũ, Telegram đúng lần 3, không spam, hồi phục; deploy cài cron (giữ dòng cron khác, md5 script trên 242), CHK, status, PRE từ chối khi cron đã có, rollback gỡ cron, file cũ > 30' ⇒ FAIL + rollback |
| MINOR-1 | Chỉ kiểm stop active ⇒ stop pending/mồ côi đã kích bị gắn LOST_FOREIGN (KHẨN giả + chặn 24 h) | `C3MergedGuard.recoverC3Exit` (dùng ở `Reconciler` trước khi gắn LOST_FOREIGN và ở mọi lần đóng do phẳng): bằng chứng trên **mọi** `c3s-` (active/pending/mồ côi FINISHED/TRIGGERED → `actualOrderId`) và `c3x-`; có ⇒ lý do `TRAILING_STOP`/lý do đóng, nạp phần khớp còn thiếu từ `userTrades` của các orderId (VWAP) + realized (giá − giá vào c3)·qty (gross: `userTrades` của gateway không mang phí) ⇒ equity c3 không bị thiếu khi mất stream; không đọc được `userTrades` ⇒ KHẨN "realized có thể thiếu" | `C3MainAccountR4eTest` (mất stream, stop mồ côi kích ⇒ `TRAILING_STOP`, exit qty = qty, realized > 0, không KHẨN/không chặn/không journal LOST_FOREIGN) |
| MINOR-2 | Khoá PID check-then-write (TOCTOU) | `mkdir` nguyên tử ở foreground **trước** câu hỏi YES; file YES nằm **trong** khoá; job ghi pid của nó (nhận khoá), foreground bỏ trap; khoá mồ côi (pid chết) ⇒ `mv` nguyên tử + so pid rồi mới lấy lại | fake242 §25 (job khác đang giữ ⇒ từ chối trước YES; khoá mồ côi ⇒ lấy lại, huỷ ⇒ khoá xoá); §23 D1 cập nhật |
| MINOR-3 | Dry: `[C3-LIVE-SCOPE] TU CHOI` chỉ có thể là lỗi c3 | CHK: FAIL trong dry. `[OI-GUARD-2] STALE` vẫn INFO, hiện trong `c3live_status.sh` (kèm tuổi exchangeInfo, trạng thái làm mới, cron, dòng init A1) | fake242 §23 (SCOPE ⇒ FAIL + rollback; vô hại còn reanchor + OI STALE), §25 status |
| MINOR-4 | ssh/scp tới 242 không thử lại | `s242`/`s242in`/`c242`: 3 lần cách `SSH_RETRY_S` (10 s) **chỉ khi lỗi kết nối** (rc 255; scp: rc ≠ 0); `s242in` giữ nội dung heredoc cho mỗi lần. Áp cho: kiểm PRE, chép jar/script, khôi phục env, kiểm A1, cài/gỡ cron, LATCH, CHK, xoá PAUSE và **mọi** ssh của rollback. **Không** thử lại bước chuẩn bị (append env) và restart (không idempotent) — đã có xử lý lỗi riêng (khôi phục env / rollback tự động) | fake242 §25 (rollback: ssh rớt 2 lần ⇒ thử lại ⇒ xong); §23 (ssh rớt hẳn ⇒ rc 2 vẫn đúng) |

## 2. Số liệu

- `mvn -o package` (nice): **848 test, 0 fail, 0 error, 1 skip** (R4d 846 + `C3MainAccountR4eTest` 1 + `UniverseA1ListingRefreshTest` 1).
- fake242: **211/211** (R4d 199 + 12: §23 SCOPE TU CHOI ⇒ FAIL, §25 11 kiểm), chạy trên cây làm việc = commit `4e15746e` (pin `NJ`/`NJ_MD5` đổi trước §22; test đặt `NJ` riêng).
- Jar `~/claude_master/v12/jar/binance-java-sdk-1.2.4.jar_v12_r4e` md5 `2f69f693da550b233f979bf707659194` (pin `NJ`/`NJ_MD5`).
- `rollback_v12.sh` md5 `57ee2baf384a22dfeb2f293c12108577` (`RB_MD5`); `exinfo_refresh_242.sh` md5 `db6aa6512797fddf4efe305112988d80` (`EXR_MD5`) — kiểm bằng `md5sum` thật.
- A1 test md5 không đổi; code canary 0 file đổi; `deploy_v12_dry.sh` + pin cũ giữ.

## 3. Lệnh owner (11-18, trên ORACLE)

```
bash ~/claude_master/v12/c3live/ops/c3live/deploy_v12_dry_r4.sh
```

Từ chối trước 2026-11-18 07:54 +07 (trừ `FORCE=1` khi MASTER báo). Chạy thử `DRY=1 …` (chỉ đọc; PRE kiểm thêm `python3`,
`crontab`, cron chưa cài). Gõ `YES` 1 lần ⇒ job nền, Telegram kết quả. rc: 0 XONG · 1 DỪNG/đã rollback · 2 ROLLBACK LỖI (PAUSE
còn — chạy đúng lệnh in ra) · 3 XONG nhưng PAUSE còn. Rollback tay (gỡ cả cron làm mới):
`FORCE_TIME=1 bash ~/claude_master/v12/c3live/ops/c3live/rollback_v12.sh <TS>`.
