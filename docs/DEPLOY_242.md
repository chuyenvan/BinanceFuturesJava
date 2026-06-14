# DEPLOY_242 — Runbook deploy GỘP 242 (016 + 019 + gỡ-crawl) [TASK-023 P3]

> ⛔ **KHÔNG tự deploy.** Runbook để **user duyệt thời điểm + tự bấm chạy**. CCD chỉ chuẩn bị.
> Mục tiêu: gộp 3 thay đổi vào MỘT jar → restart 242 **một lần** (tránh nhiều lần gián đoạn ingest).

## 0. Cái gì trong jar này (3 commit, đều trên branch `module`)
| Commit | Task | Đụng process nào trên 242 |
|---|---|---|
| `3704b6e` | 016 — TickerFuturesHelper clamp limit [1,1500] + guard -1003-rate 8s | **Ingest** (BinanceDataIngestor) |
| `027830b` | 019 — wire `setProductionMode(true)` + funding flush heartbeat | A → **Trading** (BinanceOrderTradingManager); B → **Ingest** |
| `b231b6d` | 023-P1 — gỡ `startHistoryCrawl` khỏi OI ingestor + fix catch-câm forward | **Ingest** |

⇒ **Phải restart CẢ HAI process live** trên 242: ingest + trading. (019-A nằm ở trading; 016/019-B/gỡ-crawl nằm ở ingest.)

> Hai entry-point (CLAUDE.md): ingest = `websocket.BinanceDataIngestor.main()`; trading =
> `trading.BinanceOrderTradingManager.main()`. Mỗi process ghi PID qua `Utils.writePid2File()`
> (`APP_PID_DIR`/`APP_MAIN_CLASS` từ `daemon.sh` ngoài repo) và tự re-exec khi `Utils.reset(...)`.

## 1. Tiền điều kiện (trước khi build)
- [ ] Branch `module` có đủ 3 commit trên; `git log --oneline -6` thấy `b231b6d`/`027830b`/`3704b6e`.
- [ ] (Khuyến nghị) đã chạy `AerospikeStateScan` TRÊN 226 để có **mốc TRƯỚC deploy** của `funding_data`/`open_interest`/`kline_*` trên 242 (STATUS_RECON §5) → so sánh sau restart biết deploy có tác dụng.
- [ ] Không có HPO/job nặng của user đang chia tài nguyên 242 (242 là live, không chạy backtest — chỉ cần chắc ingest/trading hiện tại ổn để rollback về được).

## 2. Build jar mới
```bash
# trên máy build (226 hoặc dev có mvn — xem CLAUDE.md "mvn wrapper").
git -C <repo> checkout module && git -C <repo> pull
mvn -o package          # ra target/binance-java-sdk-1.2.4.jar (fat jar)
# sanity: jar có class đã sửa
unzip -l target/binance-java-sdk-1.2.4.jar | grep -E "OpenInterestIngestor2AerospikeNew|FundingFeeManager|AerospikeStateScan"
```
- [ ] Build PASS (compile + shade).

## 3. Backup jar đang chạy trên 242 (ĐỂ ROLLBACK)
```bash
# trên 242, tại thư mục chạy jar (CWD có config.properties/redis.config).
cp <run_dir>/binance-java-sdk-1.2.4.jar <run_dir>/binance-java-sdk-1.2.4.jar.bak.$(date +%Y%m%d_%H%M)
ls -la <run_dir>/*.jar*           # xác nhận đã backup
```
- [ ] Có file `.bak.<ts>` — đây là điểm rollback.

## 4. Copy jar mới lên 242
```bash
scp target/binance-java-sdk-1.2.4.jar <user>@103.157.218.242:<run_dir>/binance-java-sdk-1.2.4.jar
# verify checksum 2 đầu khớp
md5sum target/binance-java-sdk-1.2.4.jar           # máy build
ssh <user>@242 "md5sum <run_dir>/binance-java-sdk-1.2.4.jar"
```
- [ ] md5 hai đầu KHỚP.

## 5. Restart 2 process theo PID-FILE (⛔ KHÔNG pkill/killall java)
> Live ghi PID qua `Utils.writePid2File` vào `APP_PID_DIR`. Dùng cơ chế restart chuẩn của hệ
> (`daemon.sh` ngoài repo) — **chỉ kill đúng PID trong pid-file của process đó**, không đụng PID khác
> (Aerospike/Redis/HPO). Thứ tự đề xuất: **ingest trước** (data nền) rồi **trading**.

```bash
# trên 242 — minh hoạ; thay bằng lệnh daemon.sh thực của hệ.
# 5a. INGEST:
cat $APP_PID_DIR/<ingest_main_class>.pid        # đọc PID hiện tại
kill <pid_ingest>                               # SIGTERM, đợi thoát sạch
# daemon.sh sẽ re-exec ingest bằng jar mới (hoặc start tay theo daemon.sh)
# 5b. TRADING:
cat $APP_PID_DIR/<trading_main_class>.pid
kill <pid_trading>
# daemon.sh re-exec trading bằng jar mới
```
- [ ] Cả 2 process lên lại, pid-file cập nhật PID mới.

## 6. VERIFY sau restart (đọc log 242 ~10–15 phút)
- [ ] **Ingest sống:** log có `Rest-Kline-Loop` (mỗi phút) + `OI-Forward-Loop` (~5'); **HẾT `-1130`** (016 OK).
- [ ] **HẾT dòng `OI-History-Crawl`** ở khởi động ingest (xác nhận gỡ-crawl `b231b6d` đã vào — đây là tín hiệu trực tiếp jar mới đang chạy).
- [ ] **019-A:** log trading có `🔄 FundingFeeManager: BẬT production refresh (mỗi 30 phút)` lúc init + sau đó `🔄 FundingFee refresh: cập nhật N symbol` mỗi 30'.
- [ ] **019-B:** log ingest có heartbeat `💤 Funding flush idle … phút` (khi chưa tới kỳ settle) và `✅ Đã đồng bộ Funding Rate …` khi có settle.
- [ ] **Ghi 242 lần đầu verify được (007-B/C):** `price_realtime` BTC cập nhật; `open_interest` có record mới (forward poll). → chạy `AerospikeStateScan` TRÊN 226 lần 2: `funding_data`/`open_interest` ts 242 phải **TIẾN** so mốc trước deploy (§5 STATUS_RECON).
- [ ] **Reporter/Telegram** vẫn chạy (007-B/D): nến/cảnh báo định kỳ.
- [ ] Không có exception lặp lại bất thường trong `error.log`.

## 7. Rollback (nếu ingest gap bất thường / lỗi lặp / không verify được)
```bash
# trên 242
cp <run_dir>/binance-java-sdk-1.2.4.jar.bak.<ts> <run_dir>/binance-java-sdk-1.2.4.jar
# restart lại 2 process theo bước 5 (về jar cũ)
```
- [ ] Sau rollback: ingest/trading về trạng thái trước deploy; ghi lại lý do rollback để soi tiếp.

## 8. Sau deploy thành công
- [ ] Cập nhật `docs/AGENTS.md`: 016 → DONE+deployed; 019 → DONE (đã verify live); 023 → DONE.
- [ ] Điền số 242 sau-deploy vào `docs/STATUS_RECON.md §5`.

---
### Lưu ý an toàn
- ⛔ TUYỆT ĐỐI không `pkill java`/`killall java` (giết nhầm Aerospike/Redis/HPO). Chỉ kill đúng PID pid-file.
- Deploy 1 lần cho cả 3 thay đổi → 1 lần gián đoạn ingest duy nhất. Đừng tách lẻ.
- `config/PrivateConfig.java` chứa key live commit trong repo (SECURITY) — KHÔNG echo secret khi thao tác deploy/log.
