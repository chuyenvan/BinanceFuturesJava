# THIẾT KẾ LẠI CẤU HÌNH: một nguồn sự thật cho mọi logic trade
2026-09-03. Lý do trực tiếp: hai kết luận sai trong 24h qua (`AI_DYNAMIC_MAX` clamp làm gate thành hằng số 1.713%; ngưỡng "0.008" không phải ngưỡng thật) đều là hậu quả của cấu hình phân tán — không ai, kể cả tác giả, nhìn được giá trị hiệu dụng.

## 1. CHẨN ĐOÁN (số liệu đã kiểm, không suy đoán)

| hạng mục | số | ghi chú |
|---|---|---|
| field `public static` trong `Configs.java` | **118** | trong đó **85 MUTABLE** (không `final`) |
| env đọc trong `Configs.java` | 40 | |
| env đọc **ngoài** `Configs.java` | **64** | rải ở 25+ file: `BinanceOrderTradingManager`, `Utils`, `WfoDataset`, `WfoWorker`, các Probe… |
| key trong `config.properties` | 35 | **18 key KHÔNG xuất hiện ở bất kỳ đâu trong code** |
| key "mồi giả" (có trong file, code hardcode giá trị khác) | ≥2 | `RATE_FEE` (file 0.001 / code 0.002), `RATE_PROFIT_STOP_MARKET` (file 0.1 / code 0.03 / chạy 0.07) |
| hằng số HPO 5 chữ số nằm trong logic | 13 | `AI_DYNAMIC_MAX=2.14135`, `AI_DYNAMIC_MULTIPLIER=1.28760`, `TS_PROFIT_MULTIPLIER=5.21847`, `TS_DYNAMIC_K=0.29774`, `BUDGET_MARGIN_RATIO_1=0.4820`, `BUDGET_DIVIDER_1=1.5578`, … |
| nơi ghi đè `Configs.*` lúc chạy | 20+ | `CpcvBatchRunner`, `WFORunner`, `WfoWorker`, `Mom15SweepProbe`, `TrailingStopSweepProbe`… |
| bản sao `config.properties` | 10+ | mỗi thư mục run một bản 48 dòng, bị `sed` vá riêng → trôi lệch |

**Ba tầng cấu hình chồng nhau, thứ tự không ai thấy**: giá trị hardcode Java → `config.properties` (chỉ vài key được đọc) → env `SIM_*` (ghi đè trong `applySimEnv()`).

**Hệ quả cụ thể đã xảy ra** (default trong code ≠ giá trị đang chạy — quên set env là hệ chạy khác hẳn):

| tham số | default code | đang chạy | nếu quên env |
|---|---|---|---|
| `MIN_MOMENTUM_15M` | **0.02284** | 0.008 | gate chặt gấp 2.9× |
| `RATE_PROFIT_STOP_MARKET` | 0.03 | 0.07 | arm sai hoàn toàn |
| `LOSER_TIME_STOP_HOURS` | **0 (TẮT)** | 168 | mất cơ chế cắt lỗ |
| `DCA_GRID_SCALE` | env-only | 1.5 | sizing về 1× |
| `SELECTOR_RANK_TOPK` | env-only | 8 | rank OFF → dùng ngưỡng tuyệt đối |

## 2. NGUYÊN TẮC THIẾT KẾ
1. **Một file = toàn bộ cấu hình.** Mọi tham số ảnh hưởng giao dịch nằm trong đúng một profile. Không `System.getenv` trong logic.
2. **Không có giá trị ngầm.** Mỗi tham số phải xuất hiện tường minh trong profile, kể cả khi bằng default.
3. **Giá trị dẫn xuất phải được in ra.** Thứ logic thực sự dùng (ngưỡng gate sau clamp, chi phí round-trip, SL khóa tại arm, chế độ ratchet) được TÍNH và LOG lúc khởi động — đây chính là thứ đã giấu lỗi.
4. **Fail-fast.** Key lạ (gõ sai) → dừng. Ngoài range khai báo → dừng. Key có trong file mà không consumer nào đọc → dừng.
5. **Bất biến.** Mọi field `final`; sweep nhận bản sao profile thay vì ghi đè global.
6. **Hash tái lập.** In `CONFIG_HASH` và ghi vào header `printDone` + manifest dataset. Mỗi kết quả truy ngược được về đúng cấu hình.
7. **Sim và live dùng CHUNG profile**, khác biệt là overlay tường minh + lệnh `diff` in ra khác biệt.

## 3. KIẾN TRÚC
```
profiles/
  base.properties          # mọi tham số + đơn vị + range hợp lệ + nguồn gốc (HPO/thủ công/đã kiểm)
  dev_c2b.properties       # overlay: chỉ những gì khác base
  live.properties          # overlay live (K, dead-zone, DCA…)
TradingProfile.java
  load(base, overlay, envWhitelist) -> immutable
  validate()   : range, kiểu, key lạ, key không consumer
  derived()    : gate_thr@score, cost_roundtrip, sl_at_arm, ratchet_mode…
  dump()       : in toàn bộ + nguồn từng giá trị (base/overlay/env) + SHA-256
Configs (façade tạm) -> đọc từ TradingProfile, giữ chữ ký cũ để migrate dần
```

## 4. DANH SÁCH XÓA (đã kiểm: không xuất hiện ở bất kỳ đâu trong code)
`AEROSPIKE_SET_NAME_FUNDING_PRED`, `AEROSPIKE_SET_NAME_PRED_40`, `BTC_TREND_REVERSE_DURATION`, `BTC_TREND_REVERSE_RATE_MAX`, `BTC_TREND_REVERSE_RATE_MIN`, `BTC_TREND_REVERSE_RATE_MIN_TRADE`, `FILE_AI_DCA_PREDICTIONS`, `FILE_ENTRY_MARKET_LEVEL`, `FUNDING_MAX_TRADE`, `FUNDING_MIN_TRADE`, `IS_KAGGLE_MODE`, `LEVERAGE_ORDER`, `NUMBER_ENTRY_EACH_SIGNAL`, `NUMBER_HOUR_FUNDING_CAL`, `NUMBER_TICKER_CAL_RATE_CHANGE`, `PROFIT_RATE`, `STABLE_SYMBOLS`, `TIME_START`
Cộng: `RATE_FEE`, `RATE_PROFIT_STOP_MARKET` trong properties = **mồi giả**, phải xóa khỏi file (giá trị thật ở code/env).
Env chết (code có đọc nhưng không script nào set): `ABLATION_MODE`, `SWEEP_*`, `SHORT_*`, `FS_*`, `FF_*`, `CPCV_*`, `BT_*`, `DCA_GRID_SCALAR`, `DCA_TIER_MARGIN_CAPS`, `WFO_FROZEN_GENOME`… → hoặc xóa, hoặc đưa vào profile tường minh.

## 5. ĐÒN BẨY ĐÃ CÓ SẴN TRONG CODE MÀ CHƯA BẬT (phát hiện khi rà)
- `CONF_SIZE_MODE/LO/HI/FMIN/FMAX` — **sizing theo độ tự tin selector** đã code đầy đủ (nội suy tuyến tính p6 → hệ số size `FMIN 0.3 … FMAX 3.0`, mốc `LO 0.68 / HI 0.95`), mặc định `MODE=0` (tắt), **chưa từng chạy thử**.
- `SIZE_MULT` — nhân trực tiếp budget mỗi lệnh.
- `MAX_CONCURRENT` — trần vị thế đồng thời.
⇒ Đúng ba đòn bẩy "sizing theo rank" đã đề xuất — không cần code mới, chỉ cần pre-reg và chạy.

## 6. LỘ TRÌNH (mỗi bước có parity gate byte-identical)
- **B1 (đã làm hôm nay)**: `DumpConfig` — in cấu hình hiệu dụng + giá trị dẫn xuất + `CONFIG_HASH`. Không đổi hành vi. Kết quả cho C2b: `CONFIG_HASH=42d651b45acd0e5e`; `gate_thr` chạm trần từ `score ≥ 0.30` (0.01713), `score 0.15 → 0.01030`, `score 0.05 → 0.00343`; `cost_roundtrip = 0.01000`; `arm 0.07 → SL khóa 0.0350`; ratchet LIÊN TỤC.
- **B2**: sinh `profiles/base.properties` từ chính dump này (đảm bảo trung thành) + `TradingProfile.load/validate/dump`; `Configs` đọc từ profile. Parity: printDone byte-identical.
- **B3**: xóa 18 key chết + 2 mồi giả khỏi mọi `config.properties`; bật fail-fast key lạ. Parity.
- **B4**: gỡ 64 `getenv` ngoài `Configs` (từng file, parity sau mỗi file); chuyển field sang `final`; sweep probe dùng bản sao profile.
- **B5**: ghi `CONFIG_HASH` vào header `printDone` + manifest dataset.

## 7. CÂU HỎI CÒN MỞ (chưa trả lời được, không đoán)
- `CAPITAL_START` đọc qua `Configs.getDouble` trong `BudgetManager` (đường live) — nhưng sim dùng `BudgetManagerSimple`; nguồn vốn 35,000 của sim cần truy lại.
- 13 hằng số HPO đến từ vòng tối ưu cũ trên dữ liệu đã ghi nhận là "range đã nhiễm" — cần quyết định: giữ, hay đưa vào profile và kiểm lại từng cái.

---

# B3 (2026-09-03) — KET QUA RA SOAT KENH CAU HINH THU HAI

B2 (commit ccde0ca) da lam cho **env** di qua mot cong duy nhat (`Cfg`) + `TRADING_PROFILE`.
B3 ra soat tiep va phat hien: **con hai kenh cau hinh nua**, va mot trong hai la lo hong nghiem trong.

## B3.1 — Lo hong nang nhat: config.properties cua ban chay KHONG NAM TRONG GIT

`parity2.sh` (va moi `dev_*.sh` truoc do) lay cau hinh bang:

```bash
cp -f $B/G1_giveback5/config.properties config.properties
```

tuc la **copy tu mot thu muc thi nghiem cu**. Hau qua do duoc:

| Do luong | Ket qua |
|---|---|
| So ban `config.properties` tren o dia | 155 file |
| So bien the KHAC NHAU (md5) | 24 |
| Ban trong repo vs ban dang chay | KHAC NHAU |

Khac biet cu the giua repo va ban chay (`devrun/C2b/config.properties`):

| Key | repo | ban chay | Anh huong |
|---|---|---|---|
| `AEROSPIKE_NAMESPACE` | `ticker` | `test` | doc sai cum du lieu |
| `AEROSPIKE_HOST_226` | `103.157.218.226` | `127.0.0.1` | doc sai host |
| `TIME_RUN` | `20210101` | `20220101` | doc sai pham vi |
| 11 key chi co o ban chay | — | `RATE_FEE`, `LEVERAGE_ORDER`, `IS_KAGGLE_MODE`... | xem B3.2 |

=> **Khong ai tai lap duoc mot lan chay chi tu repo.** Do la vi pham truc tiep nguyen tac
"moi cau hinh tuong minh, tap trung mot noi".

**Sua:** them `configs/sim_dev.properties` VAO GIT lam ban chuan cho sim/backtest tren Oracle;
run script copy tu file do. `config.properties` trong repo giu vai tro ban cho tool/live.

## B3.2 — 20 key trong file chay ma KHONG AI DOC (gia tri trong file la sai su that)

Kiem bang cach grep chuoi ten key tren toan bo `src/` (khong chi `Configs.java` — bai hoc tu
false-positive `CAPITAL_START` truoc day):

```
AEROSPIKE_SET_NAME_FUNDING_PRED  AEROSPIKE_SET_NAME_PRED_40
BTC_TREND_REVERSE_DURATION  BTC_TREND_REVERSE_RATE_MAX  BTC_TREND_REVERSE_RATE_MIN
BTC_TREND_REVERSE_RATE_MIN_TRADE  FILE_AI_DCA_PREDICTIONS  FILE_ENTRY_MARKET_LEVEL
FUNDING_MAX_TRADE  FUNDING_MIN_TRADE  IS_KAGGLE_MODE  LEVERAGE_ORDER
NUMBER_ENTRY_EACH_SIGNAL  NUMBER_HOUR_FUNDING_CAL  NUMBER_TICKER_CAL_RATE_CHANGE
PROFIT_RATE  RATE_FEE  RATE_PROFIT_STOP_MARKET  STABLE_SYMBOLS  TIME_START
```

Nguy hiem nhat (nguoi doc file se tin sai):

| Key | File noi | Code thuc su dung |
|---|---|---|
| `RATE_FEE` | 0.001 | **0.002** (hardcode `Configs:119`) |
| `RATE_PROFIT_STOP_MARKET` | 0.1 | **0.03** hardcode, run C2b **0.07** qua env |
| `LEVERAGE_ORDER` | 1 | khong ai doc |
| `NUMBER_ENTRY_EACH_SIGNAL` | 4 | khong ai doc |
| `IS_KAGGLE_MODE` | false | da retire boi TASK-112 |

**Sua:** xoa het khoi ca hai file; `Configs` co danh sach `KNOWN_PROPS` va **canh bao** khi file
xuat hien key khong ai doc; `CONFIG_STRICT=1` -> dung han. Da test: chay voi file cu -> rc=2.

## B3.3 — 8 key CO NGUOI DOC nhung KHONG CO trong bat ky file nao (cau hinh vo hinh)

Tat ca deu co null-check nen khong crash — chung **am tham chay bang default hardcode**, khong
xuat hien o dau ca:

| Key | Default dang chay | Y nghia |
|---|---|---|
| `NUMBER_ORDER_BUDGET` | 50 | **BASE_BUDGET = CAPITAL_START/50 = 700 USDT/lenh** |
| `HARD_STOP_LOSS_RATE` | 0 (tat) | SL cung cho lenh chua arm |
| `TS_GIVEBACK_RATIO` | 0.5 | ti le nha lai dinh trailing |
| `TS_MIN_GAP` | 0.01 | san gap khi `TS_GIVEBACK_FLOOR=true` |
| `TIME_STOP_HOURS` | 0 (tat) | time-stop lenh chua arm |
| `DISABLE_PREDICT_SYMBOL` | false | **cong tac tat TOAN BO sleeve selector** |
| `USE_SMART_CACHE` | false | ha tang |
| `WFO_STATIC_RANK` | false | ha tang |

**Sua:** 4 key giao dich dau + `CAPITAL_START` nay di qua `Cfg` (env/profile > properties > default)
va duoc khai bao TUONG MINH trong `profiles/c2b.properties`. `DumpConfig` in them
`derived.capital_start | order_budget | base_budget_per_leg`.

## B3.4 — Tham so giao dich lach cong Cfg

B2 chi doi `System.getenv` trong `Configs.java` (85 cho). Con **197 cho** khac trong `src/main`.
Ra soat: nhung cho la THAM SO GIAO DICH thi profile khong kiem soat duoc — dat trong profile thi
bi bo qua, dat qua env thi bi fail-fast tu choi => **khong con duong nao dat duoc**:

| File | Key |
|---|---|
| `GateRollingThreshold` | `SIM_GATE_ROLLING_PCT`, `SIM_GATE_ROLLING_DAYS` (dung cho RG95/RG97) |
| `WfoWorker`, `VerifyOneWindow` | `ABLATION_MODE` |
| `SimulatorMarketLevelTicker1MStopLoss` | `SEL_BACKTEST_SET`, `SEL_BACKTEST_HORIZON_IDX` |
| `WFOGateRunner` | `GATE_AB_LABELS` |
| `BinanceOrderTradingManager` (live) | `TS_LIVE_MIN_LOCK`, `LIVE_LOSER_TIME_STOP_HOURS`, `LIVE_LOSER_TS_BUFFER`, `TS_PRED_GAP`, `TS_PNOPUMP_WEAK_THR` |
| `DetectEntrySignal2TradeNormal` (live) | `LIVE_ENTRY_GRID_MIN` |

**Sua:** tat ca doi sang `Cfg.get` / `Cfg.getOr`. Giu nguyen `System.getenv` cho **kill-switch**
(`SHADOW_NO_PUSH`, `OI_STALE_HALT`, `OI_STALE_HALT_MS`, `SIM_END_DATE`) — mot cong tac an toan
khong nen phu thuoc vao file cau hinh; chung nam trong `INFRA_KEYS`.

**Chong tai pham:** `tools/check_cfg_gateway.sh` grep `src/main` tim tham so giao dich doc
`System.getenv` truc tiep va **fail** neu co. Chay truoc moi commit/build.

## B3.5 — Loader properties coi dong comment co dau '=' la mot key

`Configs` chi kiem `line.contains("=")`, nen dong
`# TASK-112 (2026-07-02): ... (Oracle = backtest, ...)` sinh ra mot key rac.
**Sua:** bo qua dong trong va dong bat dau `#`.

## B3.6 — Bat loi GO SAI TEN KEY trong profile

Truoc day go sai ten key -> code roi ve default -> lan chay "thanh cong" voi cau hinh khac y muon,
khong ai biet. Nay `Cfg.auditProfile()` (goi tu `DumpConfig`) bao moi key trong profile ma khong ai doc.
Da test: doi `SELECTOR_RANK_TOPK` -> `SELECTOR_RANK_TOPKK` => bao dung 1 key.

## B3.7 — SECRET trong repo

`config.properties` co 3 dong kieu YAML (khong co dau `=` nen parser **bo qua hoan toan** —
chua bao gio co tac dung), trong do mot dong chua API key cua AI gateway
(`virtual-key-gw-ds-4-flash: ${...:sk-...}`).

**Da xoa 3 dong.** Nhung key da nam trong lich su git => **PHAI ROTATE key ben gateway.**
Xoa file khong lam key an toan tro lai.

## Kiem chung B3

| Kiem tra | Ket qua |
|---|---|
| `tools/check_cfg_gateway.sh` | OK (khong con cho lach) |
| `DumpConfig` ENV vs PROFILE | CONFIG_HASH **28f7c17882b0b339** ca hai, diff chi khac 2 dong log `[CFG]` |
| `derived.base_budget_per_leg` | 700.00 (= 35000/50) — lan dau tien nhin thay so nay |
| `CONFIG_STRICT=1` + file properties cu | rc=2, liet ke dung 20 key rac |
| Profile go sai ten key | bao dung `SELECTOR_RANK_TOPKK` |
| `audit profile` voi c2b.properties | OK, ca 22 key deu duoc doc |
| Parity sim `P_env3` / `P_prof3` vs C2b | xem PROCESS_LOG (chay sau khi build B3) |

## Con lai (B4/B5)

- B4: bo `final` cho cac field bi probe gan lai runtime (`ExitParamSweepProbe`) — hoac tach ra
  interface sweep rieng; hien tai co 20+ cho mutate runtime.
- B5: ghi `CONFIG_HASH` + `PROFILE_HASH` vao header `printDone.csv` va manifest dataset, de moi
  ket qua tu mang theo cau hinh sinh ra no.
- Cau hoi mo: 13 hang so HPO 5 chu so thap phan (`TS_DYNAMIC_K=0.29774`, `TS_PROFIT_MULTIPLIER=5.21847`,
  `BUDGET_MARGIN_RATIO_1=0.4820`...) chua co can cu — can quyet dinh giu hay do lai.
- Chua dung: `CONF_SIZE_MODE/LO/HI/FMIN/FMAX` (sizing theo confidence), `SIZE_MULT`, `MAX_CONCURRENT`
  — da code day du, default OFF, chua chay lan nao.
