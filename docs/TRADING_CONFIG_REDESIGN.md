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
