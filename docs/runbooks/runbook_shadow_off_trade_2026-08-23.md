# RUNBOOK — Tắt trade thật → chạy SHADOW (live 242) 2026-08-23

> Mục đích: ngừng đặt lệnh thật, chuyển live sang SHADOW để thu log `[SHADOW] would-BUY` làm đối chứng/tham khảo (khi nghi WFO/HPO leak). Restart = NGƯỜI TAY (CORE.md).

## Cơ chế (đã đọc code, xác nhận)
- `BinanceOrderTradingManager.processOrderNewMarketNew()` line 160: `if ("true".equalsIgnoreCase(System.getenv("SHADOW_NO_PUSH")))` → chỉ **log `[SHADOW] would-BUY ...`**, KHÔNG push lệnh. Đọc qua `System.getenv` → **phải restart** mới áp.
- Shadow guard CHỈ nằm ở path **entry mới**. Path đóng vị thế (SL/TP/reduce-only) KHÔNG bị chặn.
- `updatePositionInfo()` line 328 = `getAllPositionInfos()` lấy vị thế từ **tài khoản Binance** lúc startup + mỗi giây → restart reconcile lại vị thế đang mở, KHÔNG mồ côi.
- **Hệ quả:** SHADOW_NO_PUSH=true → không entry mới; vị thế đang mở vẫn được đóng THẬT theo SL/TP → wind-down tự nhiên.

## Trạng thái hiện tại (2026-08-23)
- Live PID 18825 đang chạy, `conf/env.sh:35 export SHADOW_NO_PUSH=false` (đang trade thật).
- Launcher: `bin/daemon.sh` (source conf/env.sh → start.sh). Restart = `daemon.sh restart` (stop graceful ≤60s + start).

## CÁC BƯỚC (user chạy trên 242)
```
ssh -p 2222 root@103.157.218.242
cd /home/chuyennd/java/v_t_m
# 1) backup + bật shadow
cp conf/env.sh conf/env.sh.bak_$(date +%s)
sed -i 's/^export SHADOW_NO_PUSH=false/export SHADOW_NO_PUSH=true/' conf/env.sh
grep SHADOW_NO_PUSH conf/env.sh          # phải thấy =true
# 2) restart (người tay)
bin/daemon.sh restart
# 3) verify sau 1-2 phút
grep -a "SHADOW_NO_PUSH" conf/env.sh
tail -f logs/nohup.out | grep -a "\[SHADOW\] would-BUY"   # thấy would-BUY = shadow OK, không có lệnh thật
```

## Verify đã shadow (không còn lệnh thật)
- Log xuất hiện `[SHADOW] would-BUY <side> <symbol> entry ... quantity ...` khi có tín hiệu → đúng shadow.
- KHÔNG còn dòng `Create order market` dẫn tới `OrderHelper.newOrderMarket` (lệnh thật) cho ENTRY mới.
- Vị thế đang mở: vẫn thấy quản lý (updatePositionInfo mỗi giây) + đóng thật khi chạm SL/TP.

## Thu log đối chứng (mục tiêu chính)
- Log shadow ở `/home/chuyennd/java/v_t_m/logs/` (nohup.out + logback file). Dòng cần: `[SHADOW] would-BUY`.
- Đề xuất: định kỳ archive các dòng `[SHADOW]` (kèm timestamp/symbol/entry/qty/marketLevel) → sau này so với backtest tại đúng khung giờ đó (leak-free forward test = ground truth). Claude có thể lập 1 data-job gom log này (data job trên 242 được phép, KHÔNG phải deploy) nếu cần.

## Quay lại trade thật (khi muốn)
```
sed -i 's/^export SHADOW_NO_PUSH=true/export SHADOW_NO_PUSH=false/' conf/env.sh
bin/daemon.sh restart
```

## Lưu ý
- Không đóng gấp vị thế đang mở khi bật shadow — chúng tự đóng theo SL/TP. Nếu muốn flatten ngay là quyết định riêng (đóng tay trên Binance), KHÔNG bắt buộc cho shadow.
- Backtest/WFO tạm coi là THAM KHẢO tới khi có đủ log shadow đối chứng.
