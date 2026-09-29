# PLAN — DEPLOY R4 LIVE 1' V3 (jar B4+B5 + profile R4) — THIẾT KẾ, KHÔNG thực hiện

Trạng thái: **THIẾT KẾ (chưa deploy)** · 2026-09-29 · branch `module` · **KHÔNG restart shadow-c3**.
Nguồn: `RESULT_PASS_SPEED_V2.md` (B5) + `RESULT_PASS_SPEED.md` (B4) + `RESULT_RESET_RULE_P2/P3.md` (R4).
**MASTER giao deploy sau 2026-09-30 03:00Z. Task này CHỈ viết plan, KHÔNG chạm 242/shadow-c3.**

---

## 0. MỤC TIÊU
Deploy lên **shadow-c3** (Oracle, paper) jar **mới** (B4 + B5) với profile **R4** để chạy nhịp **1'**:
`SELECTOR_RANK_TOPK=16` · `LIVE_ENTRY_GRID_MIN=1` (selector mỗi phút) · `ENTRY_CASCADE=0` (KHÔNG cascade cắt rank).
Giữ nguyên `SHADOW_NO_PUSH=true` + `LIVE_PROFILE=c3_shadow` (paper). KHÔNG chạm 242.

## 1. RÀNG BUỘC CỨNG (giữ nguyên từ runbook §8-§9)
- `LIVE_PROFILE=c3_shadow` + `SHADOW_NO_PUSH=true` **KHÔNG đổi** (paper, không ra lệnh thật).
- Redis cum RIÊNG `127.0.0.1:7301` — **TUYỆT ĐỐI không trỏ Redis 242** (blpop cướp lệnh bot live).
- KHÔNG deploy lên 242. KHÔNG SSH 242.
- B5 đã **bỏ market-only skip** (parity); jar mới = HEAD (B4 OI cache + B5 parity) + profile R4.

## 2. CHUẨN BỊ JAR
1. Build HEAD (`module`) đã qua `mvn -o test` **184 PASS** (B6 PASS-SPEED-V3): `cd /home/ubuntu/src/BinanceFuturesJava && mvn -o package -DskipTests`.
2. Ghi sha256 jar mới (build B6 hiện tại: `31a24f90…`; B5 trước là `4deeed58…`).
3. Đối chiếu 3 jar: 242 (KHÔNG đổi) / shadow đang chạy (`78387f30…`, build cũ 20/09) / build HEAD mới.

## 3. BACKUP (trước mọi thay đổi)
```bash
cd /home/ubuntu/shadow_c3/app
cp -p target/binance-java-sdk-1.2.4.jar target/binance-java-sdk-1.2.4.jar.bak_$(date +%Y%m%d_%H%M%S)
cp -p conf/env.sh conf/env.sh.bak_$(date +%Y%m%d_%H%M%S)
```
Ghi lại đường dẫn 2 file backup vào audit deploy.

## 4. THAY ĐỔI ENV (chỉ 3 dòng / thêm 2 dòng — KHÔNG sửa gì khác)
`conf/env.sh`:
```bash
# R4-1M: selector K=16 + nhịp 1' + KHONG cascade
export SELECTOR_RANK_TOPK=16        # (cu: 8)
export LIVE_ENTRY_GRID_MIN=1         # (cu: khong khai = 15) -> selector moi phut
export ENTRY_CASCADE=0               # (mac dinh 0 = tat) -> ghi ro, KHONG cascade
```
Không đổi: `LIVE_PROFILE=c3_shadow`, `SHADOW_NO_PUSH=true`, `SIM_GATE_DYN_SCALE=1.70`, KEEPLEG0
(`DCA_GRID_WEIGHTS=1,1,1,1` / `DCA_GRID_SCALE=6.0`), `SIM_FIX_B1/B2/B3`, `MARKET_SCAN_MIN=1`/`PRIORITY=1`,
`CONC_CAP_PERCOIN_ENABLED/PCT=0.15`, `S1_MODEL_ONNX`, `PAPER_EQUITY=35000`, `EXCHANGE_INFO_PATH`.

## 5. DEPLOY JAR + RESTART
```bash
cd /home/ubuntu/shadow_c3/app
cp -f /home/ubuntu/src/BinanceFuturesJava/target/binance-java-sdk-1.2.4.jar target/binance-java-sdk-1.2.4.jar
bin/daemon.sh restart      # hoặc: systemctl restart shadow-c3
bin/daemon.sh status       # verify RUNNING
```

## 6. XÁC MINH 2H — TIÊU CHÍ PASS (từ task B5)
Theo dõi `logs/full.log` (logback RIÊNG) + `health.log` (cron mỗi giờ):
| tiêu chí | ngưỡng |
|---|---|
| p50 1 lượt | **≤ 1s** (đo `[PASS-TIMING]`; B6 bench steady p50 ~0.64s) |
| p95 1 lượt | **≤ 3s** (B6 bench p95 ~2.1s) |
| max 1 lượt (kể cả tick đầu giờ) | **≤ 5s** (B6: tick đầu giờ KHÔNG chặn nhờ OI double-buffer + S1 prefetch; cold-start ~28s là warmup 1 lần, không phải tick định kỳ) |
| phút có `[GATE]` | **≥ 95%** phút (selector 1' ⇒ `[GATE]` mỗi phút) |
| S1 score | **≥ 400 coin/tick** (universe ~660 coin, giữ S1 full) |
| `warm-up CHUA DU` | **0** dòng |
| ERROR mới | **0** (so danh sách ERROR nền đã biết) |
| free mem | **≥ 4G** (RSS shadow ~2.6–3.2G) |
| `[MAP]` universe | FULL (~660+ coin), KHÔNG bị cắt (bằng chứng giữ S1 full) |
| `SHADOW_NO_PUSH` / `LIVE_PROFILE` | `true` / `c3_shadow` **giữ nguyên** (kiểm `[CADENCE-SPLIT]`/`[R4-1M]` header + không có lệnh thật) |

## 7. ROLLBACK (ngay nếu FAIL)
```bash
cd /home/ubuntu/shadow_c3/app
cp -f target/binance-java-sdk-1.2.4.jar.bak_<TS> target/binance-java-sdk-1.2.4.jar
cp -f conf/env.sh.bak_<TS> conf/env.sh
bin/daemon.sh restart
bin/daemon.sh status        # verify RUNNING
# xác nhận log trở lại SELECTOR_RANK_TOPK=8 / không có LIVE_ENTRY_GRID_MIN=1
```

## 8. KỶ LUẬT
- **Thứ tự shadow → 242** (owner duyệt riêng cho 242, KHÔNG làm ở đây).
- Viết `docs/audit/DEPLOY_R4_LIVE_1M_V3_<date>.md` (sha256 jar, diff env KHÔNG in secret, số đo 2h).
- Nếu FAIL → rollback + báo, KHÔNG tự sửa tiếp.
