# AUDIT_SHADOW_LIVE_20260926 — Kết quả THẬT của kênh shadow trên Oracle (READ-ONLY)

- **Ngày đọc:** 2026-09-26 ~16:13-16:18 (GMT+7), host Oracle `instance-20260622-1647` (arm64).
- **Repo:** `/home/ubuntu/src/BinanceFuturesJava`, branch `module`, HEAD `96a08e5`.
- **Ràng buộc đã giữ:** chỉ ĐỌC — không `systemctl start/stop/restart/reload`, không sửa file production,
  không chạm host 242, không đọc/in key/token, không `pgrep -af`, không kill/xóa/di chuyển, không chạy Java/sim/WFO.
  Output tool để nhỏ (`head`/`tail`/`grep -c`/`sed -n`). Chỉ commit file audit này, **KHÔNG push**.

---

## 1. Kiểm kê kênh có trên Oracle

| kênh | unit / đường dẫn | trạng thái | dữ liệu đọc được từ Oracle? |
|---|---|---|---|
| **shadow_c3 (LIVE PAPER, T170)** | `shadow-c3.service`; `/home/ubuntu/shadow_c3/app` | `active (running)` | **CÓ** — ledger.csv, open_positions.csv, health.log, full.log, error.log |
| Redis riêng của shadow | `shadow-c3-redis.service`; port 7301 | `active (running)` | CÓ (state store paper) |
| live thật (bot 242) | **không có unit trên Oracle** | — | **KHÔNG** — chạy trên host **242**, không truy cập theo ràng buộc ⇒ cần owner xác nhận nếu muốn số liệu |
| liq-collector | `liq-collector.service` | `active (running)` | không phải kênh trade (thu thập dữ liệu) |

`systemctl list-units --type=service | grep -i shadow` ⇒ **đúng 2 unit**: `shadow-c3-redis`, `shadow-c3`.
Không có kênh live/paper nào khác trên Oracle. `/home/ubuntu/shadow*` ⇒ chỉ `/home/ubuntu/shadow_c3` (+ `shadowlog.sh`).

---

## 2. Trạng thái dịch vụ

- `systemctl is-active shadow-c3` ⇒ **active**; `shadow-c3-redis` ⇒ **active**.
- `MainPID=1945023`, `ExecMainStartTimestamp=2026-09-26 15:19:46 +07` ⇒ **process hiện tại mới chạy ~55 phút**
  (máy uptime 17 ngày). `NRestarts=29` (Restart=always, RestartSec=15). health.log cho thấy JVM đổi PID nhiều lần
  (…1933921 → 1945023), tức shadow **tự restart định kỳ ~vài giờ**, không phải crash im lặng; 100 dòng health gần nhất **0 `DOWN`**.
- **Jar đang chạy vs HEAD — LỆCH (đã xác nhận):**
  - Jar đang chạy: `/home/ubuntu/shadow_c3/app/target/binance-java-sdk-1.2.4.jar`, build **2026-09-20 22:06**,
    md5 `51be593c39c2…`, **sha256 `e3bf2d21cdce…`**.
  - Bản build ở HEAD: `target/binance-java-sdk-1.2.4.jar`, build **2026-09-24 08:37**,
    md5 `d5adc67810a6…`, **sha256 `c2b0c9634526…`**.
  - ⇒ khớp đúng cặp lệch đã biết trước (`e3bf2d21…` vs `c2b0c963…`). **Jar chạy CŨ HƠN build HEAD 4 ngày.**
- Không đọc unit file của host 242 (không chạm 242). `health.sh` chạy bằng cron `0 * * * *`, ghi `health.log` mỗi giờ.

### `CONC_CAP_PERCOIN=15%` — có hiệu lực?
- File `app/conf/env.sh` **đã có** `CONC_CAP_PERCOIN_ENABLED=true` (dòng 67) và `CONC_CAP_PERCOIN_PCT=0.15` (dòng 68).
- **Có backup** trước khi sửa: `env.sh.bak_20260918`, `env.sh.bak_20260919_pre_flatgrid`, `env.sh.bak_20260924_130113`
  (cả 3 bản backup đều **0** lần xuất hiện `CONC_CAP_PERCOIN` ⇒ là bản *trước* thay đổi, đúng nghĩa backup).
- `/proc/1945023/environ` **có** 2 tên biến `CONC_CAP_PERCOIN_ENABLED` và `CONC_CAP_PERCOIN_PCT` (chỉ đọc TÊN, không in giá trị).
  Process hiện tại start **15:19:46 hôm nay**, sau thời điểm sửa env.sh (24/09 13:01)
  ⇒ **CONC_CAP_PERCOIN ĐÃ CÓ HIỆU LỰC** (không cần restart để kiểm; restart đã xảy ra tự nhiên).
- ⚠️ Nhưng **chưa có cơ hội tác động**: không có entry mới nào từ 20/09 ⇒ `blocked=0` (không quan sát được hành vi cap).
- `HOLDOUT_UNSEAL` / `HOLDOUT_SEAL`: **KHÔNG** xuất hiện trong `env.sh` lẫn `/proc/<pid>/environ` ⇒ chưa cấu hình/unseal bằng env trên Oracle.

---

## 3. KẾT QUẢ THẬT (từ ledger/health/log có sẵn)

Cửa sổ dữ liệu rõ ràng: ledger.csv phủ **2026-09-06 15:29 → 2026-09-26 16:14** (entry đầu 06/09 15:29;
entry mới nhất **20/09 05:34**; exit mới nhất **26/09 16:14** — vừa xảy ra trong lúc audit).

| chỉ số | giá trị | nguồn / cận |
|---|---|---|
| Số lệnh **đã đóng** | **69** | `ledger.csv` (69 dòng) |
| Số lệnh **đang mở** | **5** | `open_positions.csv` (G/B2/PATH/AKE/ONE) |
| Realized PnL (gross) | **+1.454,90 USDT** | `ledger.csv` cộng cột pnl (không trừ phí/funding) |
| Full window (06/09→26/09) | +1.454,90 | — |
| 7 ngày gần nhất (exit ≥ 19/09) | **+713,77** | 4 lệnh time-stop 168h gần đây: −18,04 / −19,90 / −4,03 / −67,10 |
| Unrealized (MTM, gross) | **−477,23 USDT** | 5 vị thế mở, giá fapi lúc 16:1x; ret −7,8% … −52,4% |
| **Net MTM** | **+977,67 USDT = +2,79%** trên paperEquity 35.000 | realized + unrealized, **KHÔNG trừ phí/funding** |
| Equity | `PAPER_EQUITY=35000`; realized-equity 36.454,90 | không có file equity curve/MTM chạy định kỳ trên Oracle |
| **maxDD** | **KHÔNG có số chuẩn** — chỉ xấp xỉ realized-only **−803 (−2,29% paperEquity)** | xem §5 |
| **UW** | **KHÔNG có** cho shadow | UW là chỉ số SIM (số ngày underwater); shadow không ghi equity curve ⇒ không tính được |
| Time-stop 168h | 11/69 lệnh đóng bằng `TIME_STOP_168H` (còn lại 58 `TRAILING_STOP`) | `ledger.csv` |
| would-BUY / would-CLOSE / createOrder | 60 / 57 / **0** | `health.log` dòng mới nhất — `createOrder=0` xác nhận **không có lệnh thật** (paper OK) |

### Concentration (CONC_CAP)
- 5 vị thế mở, notional ghi sổ (entry) mỗi coin 230-249 USDT ⇒ **conc mỗi coin 0,66-0,71%**, **tổng 3,39%** trên 35.000.
- **Đỉnh conc trong sổ mở hiện tại = 0,71% (AKEUSDT)** — **rất xa** trần 15% ⇒ cap chưa từng bind.

### `gatePassCuoi` — ⚠️ KHÔNG TỒN TẠI
- `grep -c gatePass health.log` ⇒ **0**. `bin/health.sh` **không** có field `gatePassCuoi` ⇒ **watchdog vẫn thiếu** như đã biết.
- Đọc trực tiếp `full.log` (từ 18/09 18:20): **524 dòng `[GATE]`**, tất cả `n_pass=0`;
  dòng gate mới nhất `26/09 16:03:04 … scale=1.7000 topk=8 … n_cand=8 n_rej=8 n_pass=0`.
  **Không có bất kỳ dòng `n_pass>0` nào trong toàn bộ log hiện có** ⇒ *chưa từng gate pass* trong cửa sổ quan sát được.
- Hệ quả: **0 entry mới từ 20/09 05:34** (banner `base=0.008` biến mất; jar 20/09 22:06 chuyển sang gate đóng scale 1.70).

### Lỗi gần đây
- `full.log`: **ERROR = 4675**, WARN = 61. **Toàn bộ ERROR tập trung 21/09 21:16-21:17**
  (`AerospikeFloatSim: InvalidNode` — outage Aerospike, không phải lỗi logic/tiền).
  `error.log` mtime **21/09 21:17** ⇒ **0 ERROR mới trong ~5 ngày qua**.
- WARN mới: 49 dòng `OnnxInferenceManager: Scaler missing …Scaler_Return15M.onnx` (xuất hiện mỗi lần JVM start: 07:17 / 11:18 / 15:19 hôm nay) + 12 dòng Aerospike. Không có WARN về tiền/vị thế.

### Tài nguyên
- `df -h /` ⇒ **15G avail / 194G, 93% used** (trước đó từng 97%).
- `free -g` ⇒ total 23G, used 6G, **available 16G**. RSS shadow ~2,1-2,6G (khớp ước lượng 2,6-3,2G cũ).
- Watchdog đĩa: `health.sh` có ghi `disk=` mỗi giờ ⇒ **có**, giá trị mới nhất `disk=15G`.

### Liveness
- Tick cuối `26/09 16:00:06`, `[S1] score 600 coin @16:03:04`, `[SHADOW] closed SYNUSDT reason=TIME_STOP_168H pnl=-67.10 @16:14:01`.
  ⇒ kênh **đang chạy sống**, chỉ là **không vào lệnh mới**.

### `ledger_from_log.csv` (parser `tools/shadow_vs_sim.py`)
- 60 dòng, `ts_exit` **rỗng toàn bộ** ("60 lệnh chưa đóng") — dù nhiều lệnh đã đóng trong `ledger.csv`.
  Cửa sổ parse chỉ tới entry **20/09 05:14**. ⇒ coi file này là **số liệu parse thiếu/không tin được**, dùng `ledger.csv`.

---

## 4. Đối chiếu runbook `docs/runbooks/AGENT_RUNBOOK.md`

### §0.9 (mục 9) — **CÒN SAI, nặng**
Nguyên văn dòng đang sai (mục 9, dòng 56-59):

> **9. Shadow C3 Oracle — DA TAT** (`docs/experiment/L2_PORT_C3.md`; trang thai 2026-09-07:
>    `health.log` bao `DOWN` lien tuc tu **2026-09-06 19:00Z**, pid mat. Dong bang tai luc tat:
>    `wouldBUY=30 wouldCLOSE=4 createOrder=0 errLines=0 ledgerRows=4`. Cron `health.sh` van cai.
>    **L4 KHONG khoi dong lai.** …

Thực tế hôm nay: `shadow-c3` **active**, PID 1945023, `health.log` **UP liên tục**, ledger 69 lệnh / realized +1.454,90.
**Đề xuất câu sửa (KHÔNG tự sửa file):**

> **9. Shadow C3 Oracle — DANG CHAY (paper).** Trạng thái 2026-09-26: `shadow-c3.service` **active**,
> `NRestarts=29` (tự restart vài giờ/lần), `health.log` UP liên tục, ledger 69 lệnh đã đóng / realized +1.454,90,
> 5 vị thế mở. **Nhưng 0 entry mới từ 2026-09-20 05:34**: `[GATE] n_pass=0` mọi tick (gate đóng scale 1.70;
> xem `docs/DIAG_FORWARD_PIPELINE.md`). Jar chạy (`sha256 e3bf2d21…`, build 20/09 22:06) **lệch** build HEAD (`c2b0c963…`).
> Muốn tắt: `cd /home/ubuntu/shadow_c3/app && bin/daemon.sh stop`.

### §0.8b (mục 8b, dòng 50-52) — **chưa xác minh được từ Oracle**
Nguyên văn: *"**Shadow trên 242 hien khong sinh tin hieu**: 66 vi the cu giu `marginRunning` ⇒ `u = 0.81 >= U_MAX 0.60`
⇒ `managerBudget` tra null ⇒ 0 dong `would-BUY` tu 27/08."*
Đây là phát biểu về **host 242** — không đọc từ Oracle được (ràng buộc không chạm 242) ⇒ **cần owner xác nhận**, audit không kết luận.
Phần liên quan *shadow phải chạy Oracle với Redis riêng* thì **đúng và đang được tuân thủ** (`shadow-c3-redis` port 7301 active).

---

## 5. Phần KHÔNG đọc được / thiếu (không suy diễn)

1. **UW** — không có cho shadow (chỉ số SIM). Không tính được vì shadow không lưu equity curve ngày.
2. **maxDD chuẩn** — không có file equity/MTM định kỳ trên Oracle. Chỉ xấp xỉ **realized-only −803 (−2,29%)** từ đường cum realized của `ledger.csv`; **KHÔNG gồm unrealized** nên không phải maxDD thật.
3. **Unrealized/net tại mốc cố định 7 ngày/30 ngày** — Oracle không ghi MTM; số unrealized ở §3 do audit tự lấy giá fapi **một lần** lúc 16:1x (không phải chuỗi lịch sử), và **gross, chưa trừ phí/funding**.
4. **Số liệu kênh live thật** (bot 242) — không nằm trên Oracle và không được phép truy cập ⇒ **cần owner xác nhận**.
5. **`ledger_from_log.csv`** — parser điền thiếu (`ts_exit` rỗng, cửa sổ dừng 20/09) ⇒ không dùng.
6. **Nguyên nhân 29 lần restart** — chỉ suy ra "tự restart định kỳ" từ PID đổi trong `health.log`; log journal hiện tại không ghi restart-cause rõ (không truy sâu để giữ phạm vi READ-ONLY).

---

## 6. Tóm tắt một dòng

Kênh **shadow_c3 (paper) đang CHẠY** trên Oracle (active, UP, 0 lệnh thật), **69 lệnh đã đóng / realized +1.454,90 / 5 lệnh mở (all underwater, unrealized −477,23) / net MTM +977,67 (+2,79%)**,
**conc 3,39% (xa trần 15%)**, **`CONC_CAP_PERCOIN` đã có hiệu lực nhưng chưa bind**, **`gatePassCuoi` KHÔNG tồn tại (watchdog thiếu) và chưa từng gate pass (n_pass=0 mọi tick)**,
**jar chạy lệch HEAD (`e3bf2d21…` vs `c2b0c963…`)**, **runbook §0.9 "Shadow C3 Oracle — DA TAT" vẫn SAI**.
