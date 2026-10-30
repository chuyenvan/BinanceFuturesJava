# ROUND4F — sửa A1 (audit 4e): MAJOR-L1 (chỉ LIVE) + MINOR-1 phí + MINOR-2 bộ kiểm exchangeInfo

Branch `v1.2/c3-live`, trên `f61948aa` (R4e). Ràng buộc giữ nguyên (không push, không `git config`, Oracle không gọi Binance,
không ssh/chạy gì trên 242, không đụng canary, không in/sửa `PrivateConfig`). Mọi test A1 byte-identical.

**`A1R4eRaceTest.java`: KHÔNG chép được.** File `~/claude_master/a1_r4e_race/A1R4eRaceTest.java` có **0 byte** (kiểm 3 lần
trong vòng, tạo lúc 16:11). Chép nguyên văn 1 file rỗng không kiểm được gì nên không thêm vào repo; cần A1 gửi lại nội dung.
Kịch bản race được phủ bằng `C3MainAccountR4fTest` (dưới).

## 1. Phát hiện → sửa → test

| # | phát hiện (A1) | sửa | test |
|---|---|---|---|
| MAJOR-L1 | `recoverC3Exit` tính `miss = q − c.exitQty` từ ảnh chụp cũ (lấy trước khi đọc sàn); Reconciler và FillAccounting khoá khác monitor ⇒ stream có thể đóng cụm giữa lúc gọi REST ⇒ realized/phí ghi **2 lần**; `addFillCosts` vẫn cộng `realizedSinceAnchor` cho cụm đã xoá | (1) Ghi khớp khôi phục qua `FillAccounting.bookRecoveredExit` — **cùng khoá** `synchronized` với stream; đọc lại cụm **sống**, cụm đã đóng ⇒ **không ghi**. (2) Chống trùng theo **tradeId**: stream `t` (`UserStreamEvents.OrderUpdate.tradeId`) ↔ userTrades `id` (`TradeFill.tradeId`); `LiveBookC3` giữ tradeId đã ghi theo cụm (`trade_ids`, persist) và của cụm đã đóng (`recent_trade_ids`, ≤ 5000, persist). (3) Stream: `addFillCosts(sym, tradeId, …)` — khớp đã ghi (REST tới trước) ⇒ bỏ phí/realized **và** exit qty; cụm đã xoá ⇒ chỉ cộng tổng kể từ mốc nếu khớp **mới** (tradeId chưa thấy); không có tradeId mà cụm đã xoá ⇒ chỉ phí, không realized. (4) Khớp khôi phục không có tradeId ⇒ không ghi + KHẨN. Bỏ hẳn phép tính `miss` | `C3MainAccountR4fTest.streamBeforeAndAfterRecovery_sameEquity_noDoubleCount`: ảnh chụp cụm lấy TRƯỚC, sự kiện stream giữ trong bộ đệm; thứ tự A (stream → REST) và B (REST → stream muộn) cho **cùng** exit qty / exit avg / realized / phí / lý do / equity c3 (so `assertArrayEquals`), realized = (giá thoát − 1,0)·qty đúng **1 lần**, phí > 0 |
| MINOR-1 | `C3LiveClient.userTrades` chỉ parse qty/price/orderId/time ⇒ mất phí | parse `id`, `commission`, `commissionAsset`, `realizedPnl`. Phí: USDT/stable trừ thẳng; tài sản khác quy theo giá `<ASSET>USDT` (giá realtime 242 — như canary MIN-4); không có giá ⇒ ghi **thận trọng** 0,05 % notional (≥ phí thật, taker không giảm) + cảnh báo (dùng chung cho stream). Realized vẫn = (giá − giá vào c3)·qty (BigDecimal như stream); `realizedPnl` của sàn chỉ để đối chiếu khi KHÔNG MERGED (lệch ⇒ WARN). `!tradesOk && q > 0` ⇒ **KHẨN**, không ghi kết quả một phần. DryGateway: tradeId = orderId (1 khớp/lệnh) ở cả stream `t` lẫn userTrades | `recoveredFees_usdtDeducted_bnbConverted_unknownConservativeWithAlert` (USDT 0,01 + BNB 0,00002×600 + XYZ thận trọng, khớp trùng bị bỏ, ghi lại ⇒ 0); `partialUserTradesFailure_urgentAndNoPartialBooking` (userTrades lỗi 1/2 lệnh ⇒ KHẨN, exit qty 0) |
| MINOR-2 | Bộ kiểm không đồng nhất: bước chuẩn bị chỉ kiểm `NU > 0` | 1 file `ops/c3live/exinfo_validate.py` (pin `EXV_MD5`) dùng cho: **PRE** (chạy từ nội dung qua `python3 -I -c`, không ghi file trên 242), **bước chuẩn bị** (chép lên `ops/`, kiểm md5 trên 242) và **cron** `exinfo_refresh_242.sh` (bỏ khối Python riêng). Bước 4c: chạy làm mới **1 lần ngay** sau khi cài cron, bắt buộc rc 0 + `fails=0` (chứng minh cron chạy được: python3, curl, bộ kiểm, quyền ghi); FAIL ⇒ khôi phục env + gỡ cron + dừng trước restart | fake242 §26: PRE từ chối file có 1 symbol thiếu `underlyingType` (trước: lọt), md5 bộ kiểm sai, refresh + deploy dùng chung file, làm mới lần đầu FAIL ⇒ dừng (env sạch, cron gỡ, bot cũ cùng pid), XONG có `OK lam_moi_lan_dau rc=0 fails=0`; §24 cập nhật thông điệp |

## 2. Số liệu

- `mvn -o package` (nice): **851 test, 0 fail, 0 error, 1 skip** (R4e 848 + `C3MainAccountR4fTest` 3).
- fake242: **217/217** (R4e 211 + 6 §26), chạy trên cây làm việc = commit `b2502d6f` (pin `NJ`/`NJ_MD5` đổi trước §22; test đặt `NJ` riêng).
- Jar `~/claude_master/v12/jar/binance-java-sdk-1.2.4.jar_v12_r4f` md5 `dbe20705984d04ba68668a49da8bf5ef` (`NJ_MD5`).
- `RB_MD5` `57ee2baf384a22dfeb2f293c12108577` (rollback không đổi), `EXR_MD5` `48f32c40a5f53215e397f08fa2503370`, `EXV_MD5` `94d2f39d9eb4fe177d92b683f22f7bbd` — kiểm bằng `md5sum` thật.
- Bộ kiểm trên snapshot thật 10-27: `symbols=936 TradFi=229 onboardDate=936 underlyingType=936`, rc 0.

## 3. Lệnh owner (11-18, trên ORACLE)

```
bash ~/claude_master/v12/c3live/ops/c3live/deploy_v12_dry_r4.sh
```

Từ chối trước 2026-11-18 07:54 +07 (trừ `FORCE=1` khi MASTER báo); chạy thử `DRY=1 …` trước. Rollback tay:
`FORCE_TIME=1 bash ~/claude_master/v12/c3live/ops/c3live/rollback_v12.sh <TS>`.
