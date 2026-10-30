# ROUND4C — sửa A1 R4b (PASS-WITH-MINOR): LOST_FOREIGN, KHẨN sau chốt, deploy dry chạy nền

Branch `v1.2/c3-live`, trên `8d51c3a2` (R4b). Cùng ràng buộc: không push, không `git config`, không gọi Binance, không ssh/chạy
gì trên 242, không chạy script canary/deploy thật, không đụng `~/claude_master/canary_*`, không in/sửa `PrivateConfig`.
`A1R4bTest.java` chép NGUYÊN VĂN từ `~/claude_master/a1_r4b_scratch` (cmp = giống hệt), PASS 1/1.

## 1. Phát hiện → sửa → test

| # | phát hiện (A1) | sửa | test |
|---|---|---|---|
| A | Cụm c3 chưa arm (không có stop `c3s-` trên sàn), sàn = 0 mà không có bằng chứng c3 (LEGACY bán đúng qty c3 khi mất stream / tay / thanh lý) ⇒ FlatConfirm đóng cụm `EXTERNAL` như c3 tự đóng; qua stream, `ACCOUNT_UPDATE pa=0` cũng đóng `EXTERNAL` ngay (kể cả khi tới TRƯỚC `ORDER_TRADE_UPDATE`, khi đó khớp c3 thật bị mất khỏi sổ) | `Reconciler` (đường phẳng): không stop c3 kích, không lệnh đóng c3 khớp, không `closeReason` ⇒ lý do `LOST_FOREIGN` + sink `C3MergedGuard.onLostForeign`: journal `status=LOST_FOREIGN` (qty c3), Telegram KHẨN, `C3Scope.blockLost` chặn mở lại symbol 24 h (persist `run/c3live_lost.txt` cạnh file MERGED, nạp lại khi restart; `entryBlockReason` kiểm đầu tiên ⇒ entry = `LEGACY`). Sổ: realized c3 CHỈ từ khớp c3 ⇒ ledger `reason=LOST_FOREIGN exit_qty=0 realized_pnl=0.0` (không PnL ảo). `C3StreamScope.account()`: `pa=0` của symbol c3 đang giữ KHÔNG chuyển cho FillAccounting — đóng cụm chỉ qua `c3x-`/`c3s-` FILLED (onSell) hoặc Reconciler (FlatConfirm + bằng chứng). `rollback_v12.sh` đổi tên `c3live_lost.txt`; deploy PRE từ chối khi có file cũ. Cụm ĐÃ arm (stop `c3s-` NEW còn trên sàn): giữ hành vi R4b — FlatConfirm KHÔNG kết luận phẳng, GIỮ cụm + stop + nhắc owner (nhánh `isHolding` của A1R4bTest) | `A1R4bTest` 1/1; `C3MainAccountR4cTest`: `a_gapLegacySellsExactC3Qty_isLostForeignBlocked24h` (ledger/journal/KHẨN 1 lần/qty, 0 lệnh c3, LEGACY không bị đụng, entry `LEGACY` trong 24 h kể cả sau restart, gỡ sau 24 h), `a_streamOnLegacySellsExactC3Qty_isLostForeignNotExternal`, `a_accountUpdateBeforeOrderUpdate_doesNotCloseCluster`, `a_c3StopCloseIsStillTrailingNotLost`, `a_gapC3StopFiredIsTrailingNotLost` |
| B | Vị thế không-c3 xuất hiện trên symbol c3 vừa chốt < 15' chỉ bị coi LEGACY-busy im lặng | `C3Scope.refreshLegacy`: 60 s ≤ now − mốc chốt < 15' và sàn có vị thế không-c3 ⇒ đúng 1 tin KHẨN cho mỗi lần chốt (khóa (symbol, mốc chốt)), kèm `qty=` và số giây sau chốt; `C3LegacyRefresher` gửi (SLF4J error + Telegram) | `b_foreignPositionAfterC3Close_urgentExactlyOnceWithQty` (stream), `b_gapForeignPositionAfterC3Close_urgentOnce` (mất stream), `b_foreignPositionLongAfterClose_noUrgent` |
| C | `deploy_v12_dry_r4.sh` chạy foreground: rớt terminal giữa chừng = dừng giữa deploy; rollback lỗi bị bỏ qua (luôn xóa PAUSE, báo như đã rollback) | Foreground CHỈ kiểm (chỉ đọc) + hỏi YES + chạy JOB NỀN `setsid nohup bash $0` (log riêng `deploy_v12dry_r4_<TS>_job_<pid>.log`, khóa 1 job bằng file PID — không dùng `flock` vì fd khóa bị process con sống lâu kế thừa, file YES dùng 1 lần — `R4_JOB=1` tự gọi không có file đó ⇒ TỪ CHỐI) + `tail --pid`; trả rc của job. Job gửi Telegram lúc bắt đầu / DỪNG / FAIL+rollback / XONG (như `cl_tg` canary: token đọc file, `curl -K -`; test: `DEPLOY_TG_SINK`). `autorb` kiểm md5 rollback + rc: xong ⇒ rc 1; lỗi ⇒ in + Telegram `PAUSE còn — chạy rollback tay: FORCE_TIME=1 bash <rollback_v12.sh> <TS>`, rc 2 (KHÔNG xóa PAUSE). Kết quả CHK rỗng / ssh lỗi / thiếu `END_CHK` ⇒ FAIL (trước: bị coi là ĐẠT). Chuẩn bị (env) lỗi giữa chừng ⇒ khôi phục env + xác nhận sạch, không được thì in lệnh tay. Không xóa được PAUSE cuối ⇒ rc 3 + Telegram | fake242 §23: foreground→job→tail→rc, Telegram bắt đầu/XONG, **ssh rớt giữa chừng** (ssh giả rc 255 ngay sau restart ⇒ rollback lỗi ⇒ rc 2, dòng `PAUSE còn — chạy rollback tay: <lệnh đúng>` ở output + Telegram, PAUSE còn; chạy đúng lệnh đó sau khi ssh lại ⇒ xong), **đóng terminal** (HUP/KILL cả nhóm foreground ⇒ job vẫn tới `=== XONG` + Telegram) |
| D1 | PRE chỉ chạy trước YES; chờ khung giờ tới 90' rồi đổi 242 mà không kiểm lại | PRE thành hàm `pre242`/`run_pre`, chạy ở foreground VÀ lại trong job ngay sau khi chờ khung giờ, trước mọi thay đổi; PRE thiếu dòng cuối (`OK dia_trong`) ⇒ DỪNG | §23: job với `run/c3live_lost.txt` mới xuất hiện ⇒ DỪNG ở "lan 2", env không đổi, Telegram DỪNG |
| D2 | `rollback_v12.sh` không pin | `RB_MD5` pin (`797132662f2e28a0e3e6e2aa4851ccfa`), kiểm ở bước cục bộ VÀ trong `autorb` trước khi chạy (khác ⇒ không chạy, báo rollback tay) | §23: `RB_MD5` sai ⇒ DỪNG; pin mặc định = md5 file trong repo |
| D3 | grep `TU CHOI`/`STALE` quá rộng: dòng vô hại (`[C3-LIVE-SCOPE] TU CHOI` ghi lên symbol LEGACY, `TU CHOI yeu cau reanchor`, `[OI-GUARD-2] oi_feat pipeline STALE`) ⇒ FAIL + rollback giả | FAIL chỉ với: `STALE snapshot=` (universe quá hạn, không mua), `KHONG tao duoc runtime`, `moi leg c3_live bi TU CHOI`, `LIVE_KILLSW_MODE=act BI TU CHOI`, `MANAGE-ONLY` (+ các kiểm cũ `exchangeInfo KHONG hop le`, `[C3-LIVE-ORDER]`, LATCH, exception). Dòng vô hại chỉ đếm `INFO TU_CHOI_vo_hai= OI_STALE= C5_GLOBAL_BLOCKED=` | §23: 3 dòng vô hại ⇒ XONG rc 0; `STALE snapshot=` ⇒ FAIL + rollback + Telegram; `KHONG tao duoc runtime` ⇒ FAIL + rollback |

## 2. Số liệu

- `mvn -o package` (nice): 834 test, 0 fail, 0 error, 1 skip (R4b 825 + `A1R4bTest` 1 + `C3MainAccountR4cTest` 8).
- fake242 (`ops/c3live/test/test_fake242.sh`): **187/187** (R4b 170 + 17 mới: §22 thêm `c3live_lost.txt`, §23 16 kiểm), chạy trên cây làm việc = commit `85d36e50` (sau commit `git status` sạch). Một lần chạy trước đó (trước khi đổi khóa sang file PID) có 2 FAIL ở §15 canary-early: JVM giả thoát rc 0 không in dòng RESULT — script canary không đổi; chạy lại PASS.
- A1: `A1AdversarialTest` / `A1G3Test` md5 không đổi (`d300ebb0…`, `3faefd28…`), `A1R4Test` 3/3, `A1R4bTest` 1/1 (cmp với scratch: giống hệt).
- Canary: 0 file thay đổi trong `c3live/canary` + `ops/c3live/canary` (không bump pin jar canary). `deploy_v12_dry.sh` + pin cũ giữ nguyên.
- Jar: `~/claude_master/v12/jar/binance-java-sdk-1.2.4.jar_v12_r4c` md5 `2fe0c6635a47d08dc3f9ac7b7f0f9168` (pin `NJ`/`NJ_MD5` trong `deploy_v12_dry_r4.sh`, kiểm bằng `md5sum` thật).
- `rollback_v12.sh` md5 `797132662f2e28a0e3e6e2aa4851ccfa` (pin `RB_MD5`).

## 3. Lệnh owner (11-18, trên ORACLE)

```
bash ~/claude_master/v12/c3live/ops/c3live/deploy_v12_dry_r4.sh
```

- Từ chối trước 2026-11-18 07:54 +07 (trừ `FORCE=1` khi MASTER báo). Chạy thử trước: `DRY=1 bash …/deploy_v12_dry_r4.sh` (chỉ đọc).
- Gõ `YES` 1 lần ⇒ job nền; đóng terminal không sao. Theo dõi: `tail -f <job_log in ra>`; kết quả qua Telegram.
- rc: 0 XONG · 1 DỪNG (chưa đổi gì / env khôi phục / đã rollback xong) · 2 ROLLBACK LỖI (PAUSE còn — chạy đúng lệnh in ra) · 3 XONG nhưng PAUSE còn (xóa tay theo lệnh in ra).
- Rollback tay: `FORCE_TIME=1 bash ~/claude_master/v12/c3live/ops/c3live/rollback_v12.sh <TS>`.
