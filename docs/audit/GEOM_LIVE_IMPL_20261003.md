# GEOM_LIVE_IMPL — đưa 9 feature GEOM lên đường LIVE S1 (chuẩn bị shadow #2)

Ngày 2026-10-03 · branch `feat/geom-live` (từ `origin/module` cf5c90e4) · KHÔNG deploy, KHÔNG chạm 242, KHÔNG merge.
Bối cảnh: `docs/result/RESULT_S1_FEAT_GEOM.md` = **NO-GO** theo pre-reg (dCAGR +2,46pp CI [-0,20;+5,09] < +3,3pp).
Shadow #2 vì vậy là **quan sát A/B**, không phải bước promote.

## 1. Đường S1 live hiện tại (đọc code, không suy diễn)

| Khâu | Live (`S1RankerLive`) |
|---|---|
| Nguồn giá | Aerospike-242 `ticker/kline_1m_opt` (WAN), key phút GMT+7 `yyyyMMdd-HHmm`; close(t) = `priceClose` nến 1m `open_time = t-1m`; warm-up 384 h, sau đó 1 bản ghi/giờ |
| Feature | `S1FeatureLive.computeTick` (KEEP9); 2 cột OI từ `getMetricMap242RecentBatch`; rank `rk_*` trên **universe selector** (`selPnp.keySet()`) |
| Model | **ONNX** (`S1_MODEL_ONNX`, shadow #1 = `/home/ubuntu/s1_model/s1a2x1_cut20251231.onnx`), onnxruntime Java 1.16.3; score = −predict (thấp = tốt) |
| Quantile-map | **CÓ chạy live**: `LiveBuildMap.assign` (bản Java của `x1_build_map.py`) — S1 chỉ quyết định THỨ HẠNG, multiset P(win) của `net015` (`NET015_MODEL_ONNX`) gán theo hạng → `symbolPred = 1 − P(win)` |

⇒ "Apply GEOM" = **thay model S1 (9→18 input) + thêm 9 cột GEOM**; `LiveBuildMap`/net015 KHÔNG đổi (map chỉ dùng thứ hạng S1).
Bins sim (`predwf_map_*`) không dùng ở live.

## 2. Thiết kế (tối thiểu, gated)

- `tradecore/selector/GeomFeatureLive` — thuần tính toán, chép đúng `s1_geom_feat.py::geom_mats`: rolling `min_periods=n//2`
  (12/84), `TR = fmax(H−L, fmax(|H−Cp|,|L−Cp|))` (ngữ nghĩa `np.fmax`), `pos*` chỉ khi range>0, `atr_ratio` chỉ khi ATR168>0,
  mọi giá trị không hữu hạn → NaN; `rk_*` = rank pct (average, NaN loại khỏi mẫu số) trên **mọi symbol có giá trị trong giờ** (như offline: toàn store), KHÔNG phải universe selector.
- `tradecore/selector/GeomFeatProvider` — bar 1h giờ ĐÓNG từ 60 nến 1m `[ts_h−60m, ts_h−1m]` (quy ước `s1_geom_store.month`):
  high = max(maxPrice>0), low = min(minPrice>0), close = close hữu hạn cuối; bỏ STABLE; tên `+USDT`.
  **Thay lineage F_HEAD/F_TAIL** (live không biết tương lai): bỏ bar giờ có `Σ totalUsdt == 0` (`REQUIRE_VOLUME`).
  Lịch sử 170 h (169 cần + 1). Đọc Aerospike **batch 60 key/giờ** (client/ns/set y hệt S1 KEEP9). Giờ cuối đọc lại tới khi `now ≥ ts_h + 120 s` (phút cuối có thể chưa chốt).
  Thiếu lịch sử / nguồn lỗi → `null` → S1 **BỎ tick** + log `ERROR [S1-GEOM]` (không fallback, không NaN toàn cột).
- `S1RankerLive` (diff +66/−7): `geomOn = (LIVE_S1_GEOM_ENABLED == "true")` đọc trong constructor; ON → model `S1_GEOM_MODEL_ONNX`
  (kiểm input `[?,18]`, sai → broken), provider tạo; vector = KEEP9 rồi GEOM9, symbol thiếu GEOM → NaN. OFF → không tạo provider,
  model/path/default/vòng lặp ma trận y hệt cũ (`assemble(..., null)`).
- `research/s1live/GeomParityProbe` — chỉ ĐỌC: `geom` replay provider trên cụm chỉ định; `onnx` chạy ORT Java trên mẫu.
- `research/analysis/geom_live_model.py` — `feat` (tái lập geom_x1), `train <CUT>`, `parity`.

### Key env (mới)
| Key | Mặc định | Ý nghĩa |
|---|---|---|
| `LIVE_S1_GEOM_ENABLED` | unset = false | chỉ chuỗi `true` mới bật (tiền tố `LIVE_` ⇒ là tham số giao dịch: nếu dùng `TRADING_PROFILE` phải khai trong profile) |
| `S1_GEOM_MODEL_ONNX` | (bắt buộc khi ON) | ONNX 18 input; thiếu ⇒ S1 broken, log ERROR |

## 3. Bảng sim ↔ live từng feature

| Feature | Offline (`s1_geom_feat.py`) | Live (`GeomFeatureLive`) | Parity 7 ngày |
|---|---|---|---|
| pos24 | (C−min L24)/(max H24−min L24) nếu >0 | y hệt | max\|Δ\| = 0 (88 717 dòng) |
| pos7d | như trên, 168 h | y hệt | 0 (88 638) |
| dist_high24 | C/max H24 − 1 | y hệt | 0 |
| dist_low24 | C/min L24 − 1 | y hệt | 0 |
| atr_ratio | mean TR24 / mean TR168 (minp 12/84) | y hệt (hữu hạn cả khi giờ hiện tại không có bar) | 0 (88 820) |
| range7d | (max H168 − min L168)/C | y hệt | 0 |
| rk_pos24 / rk_dist_low24 / rk_atr_ratio | `rank(axis=1,pct=True)` toàn store | rank trên mọi symbol có bar (đã lọc qv=0) | 0 / 0 / 0 |

Nguồn bar: offline = store `OHLCV_1H_v2.bin` (từ `test.kline_1m_opt`, lineage-filter); live = 60 nến 1m/giờ từ `ticker.kline_1m_opt` (242), filter qv>0.

## 4. Model S1-GEOM

Không có model lưu từ vòng GEOM (kernel Kaggle chỉ xuất pred). Train lại **trên CPU Oracle**, recipe y hệt
`s1_geom_kernel.py` arm G42 (KEEP9+GEOM9, seed 42, 300 cây depth 4 …), chỉ đổi `device=cpu`. Input:
`geom_x1.parquet` tái lập bằng chính `s1_geom_feat.geom()` → **md5 6903e178 = vòng GEOM** (byte-identical);
KEEP9 `feat_v2_x1_keep9.parquet` md5 1aa3b974; ledger `cand_dev_x1_lite`.

| Model | Train | sha256 json / onnx | mem=json | \|json−onnx\| py-ORT | \|json−onnx\| Java-ORT (5000 mẫu) |
|---|---|---|---|---|---|
| `s1geom_g42_cut20251001` (đối chứng) | 3 485 834 | fa25eb9f… / adf505c5… | 0 | 2,86e-6 (3,5M OOS) | 1,32e-6 |
| **`s1geom_g42_cut20251231` (LIVE)** | 6 911 775 (tới 2025-12-27 16:30) | 461baf6b… / 7166583b… | 0 | 1,91e-6 (30 924) | 1,91e-6 |

- Tiêu chí ≤1e-6 tuyệt đối **TRƯỢT** (1,3–2,9e-6): sai số thứ tự cộng float32 của TreeEnsemble; model KEEP9 đang chạy shadow #1 cũng 2,62e-6.
  Tác động chức năng: top-16 ONNX vs JSON cùng X = **345/345 tick trùng tuyệt đối**.
- CPU vs GPU (cùng fold 20251001, 3 499 202 dòng OOS so `kout/pred_G42.parquet`): spearman 0,991, per-tick TB 0,990 (p05 0,970),
  top-16 overlap TB **0,90** (min 0,625; trùng tuyệt đối 564/6 772). ⇒ model live ≠ model đã sim; khác cỡ nhiễu seed (CTRL K42 vs S7 0,89).
  Model cut20251231 CHƯA có sim DEV riêng (Java sim DEV trên Oracle bị cấm).
- File: `~/claude_master/1003/geom_live/model/` (+ `.manifest.json`, `.orttest.csv`).

## 5. Parity offline ↔ live-replay

Cửa sổ: 168 giờ đóng 2025-12-25 01:00 → 2026-01-01 00:00 UTC (7 ngày CUỐI DEV). Replay = **chính `GeomFeatProvider`** đọc
Aerospike Oracle `127.0.0.1:3222 test.kline_1m_opt` (đúng nguồn đã dựng store) — warm-up 10 200 bản ghi 2,4 s, 168 giờ 6 s.
"7 ngày gần nhất" thật (10-2026) **không** làm: Aerospike Oracle không có kline_1m_opt gần đây (probe RecordNotFound), chỉ 242 có ⇒ tránh đọc WAN 242.

- 9 cột: 88 940 dòng (ts,sym) chung, **max\|Δ\| = 0,0 cả 9 cột** (float64 bit-exact, đọc CSV `round_trip`), mẫu NaN trùng 100%,
  0 dòng chỉ-offline, 138 dòng chỉ-Java (1 symbol `币安人生USDT`, cả 9 cột NaN ⇒ không vào rank).
- Lỗi tìm được và đã sửa: bản đầu (không lọc qv) có 85 symbol đã delist vẫn ghi giá hằng số, qv = 0 trong Aerospike
  (offline bỏ bằng lineage F_TAIL) ⇒ `rk_dist_low24` lệch tới 0,099 (chỉ 0,19% dòng ≤1e-6), top-16 TB 0,976 ⇒ thêm `REQUIRE_VOLUME`.
  Store chỉ có 7 998/10 009 699 dòng qv = 0 trong vùng lineage (live sẽ coi là NaN — lệch còn lại, rất nhỏ).
- Top-16 trên ứng viên ledger (177 939 dòng, 345 tick, model cut20251231): offline (geom_x1 + KEEP9, XGB json) vs replay
  (GEOM Java + KEEP9, ONNX): **341/345 trùng tuyệt đối**, overlap TB 0,9957, min 0,625. 4 tick lệch đều do 106 dòng ở 3 giờ
  thủng dữ liệu (ts_h 1767052800000, 1767088800000, 1767186000000) **không có key KEEP9** — offline left-merge cho 18 cột NaN,
  live cho atr_ratio từ cửa sổ. Lọc dòng có key KEEP9: **345/345**. (KEEP9 live hiện có cùng loại lệch ở giờ thủng.)
- Tiêu chí rank: so ≤1e-6 trên universe offline; khác biệt universe (symbol chết, giờ thủng) liệt kê riêng như trên.

## 6. Unit test (JUnit 4) — `mvn -o test`: 226 test, 0 fail (BUILD SUCCESS)

- `GeomFeatureLiveTest` (7): lặp lại `unit_tests()` của s1_geom_feat.py (ramp H=L=C; dải ±2 — chú ý comment python
  "TR = 5" sai, đúng là 4, assert python chỉ kiểm atr_ratio = 1); min_periods 11→NaN / 12→có 24h / <84→NaN 168h (warm-up thiếu
  ⇒ NaN **như pandas offline**: offline không loại dòng, để NaN cho XGB xử lý missing); `np.fmax` của TR; nến phẳng → NaN;
  rank pct (tie trung bình, NaN loại khỏi mẫu số, thứ tự cột).
- `GeomFeatProviderTest` (5): gộp bar (close = phút hữu hạn cuối, giá 0 → NaN, STABLE, `+USDT`, không close → không bar,
  qv = 0 → bỏ); warm-up 170 batch rồi 1 batch/giờ, khớp tuyệt đối tính tay; giờ chưa chốt đọc lại, đã chốt không đọc; nguồn lỗi → null; key GMT+7.
- `S1GeomGateTest` (4): parse key; **OFF: ma trận = vòng lặp cũ bit-for-bit**; ON: 18 cột KEEP9 rồi GEOM9, thiếu GEOM → NaN;
  **instance thật OFF: `geom == null`** (không có I/O GEOM).

## 7. Bằng chứng OFF byte-identical

1. So `.class` base cf5c90e4 vs branch (cùng JDK, `mvn -o compile`): 667 class trùng sha256, **chỉ `S1RankerLive.class` khác**, +4 class mới
   (`GeomFeatureLive`, `GeomFeatProvider`, `GeomFeatProvider$MinuteSource`, `GeomParityProbe`) — `cls_diff.txt`.
2. `S1RankerLive` chỉ được gọi từ `DetectEntrySignal2TradeNormal.buildS1Pool` (live, dưới `LiveProfileC3`) và probe research ⇒ sim/backtest không đi qua.
   Vì (1)+(2) **không chạy Kaggle P0** (không cần; quota giữ nguyên).
3. Trong `S1RankerLive` khi OFF: không tạo provider (test), path model + default y hệt, ma trận bit-identical (test). Khác duy nhất:
   thêm `Cfg.get("LIVE_S1_GEOM_ENABLED")` → key vào tập ASKED (chỉ dùng trong `auditProfile` để báo key profile không ai đọc ⇒ không đổi hành vi).

## 8. Artifact

`~/claude_master/1003/geom_live/jar/`: `binance-java-sdk-1.2.4.jar` sha256 **c1f6838baf63225eebbf70ac681a3d595eac764a11351a7536a36ae6a3e674ea**
(build từ cây = commit này, phần `src/main`), `s1geom_g42_cut20251231.onnx` sha256 7166583b…a5066 + manifest; `SHA256SUMS`.

## 9. Kế hoạch shadow #2 (CHỈ kế hoạch — chưa tạo thư mục/service nào)

Thời điểm: **sau mốc 2026-10-07 17:01** (khi shadow #1 bật lại `LIVE_GATE_ROLLING_*` theo ghi chú 2a-prearm) để hai shadow cùng cấu hình gate.

1. `~/shadow_c3b/app` = bản sao `~/shadow_c3/app` **chỉ cấu hình**: `bin/`, `conf/env.sh`, `config.properties`, `logback.xml`, `redis.config`;
   KHÔNG copy `logs/ feat_dump/ run/ storage/ ledger` (sổ/vị thế riêng, bắt đầu rỗng).
2. Jar: `jar/binance-java-sdk-1.2.4.jar` (c1f6838b…) → `app/target/`. Model: copy `s1geom_g42_cut20251231.onnx` → `/home/ubuntu/s1_model/` (đối chiếu sha).
3. `conf/env.sh` = env B0 của shadow #1 tại thời điểm copy, **thêm**:
   `LIVE_S1_GEOM_ENABLED=true`, `S1_GEOM_MODEL_ONNX=/home/ubuntu/s1_model/s1geom_g42_cut20251231.onnx`, giữ
   `SHADOW_NO_PUSH=true`, `LIVE_IS_SHADOW_HOST=true`, `LIVE_WRITE_242_ENABLED` unset/false (không ghi 242), `JAVA_TOOL_OPTIONS -Xms3g -Xmx3g` như #1.
4. Redis/cổng: shadow #1 phụ thuộc `shadow-c3-redis.service` ⇒ #2 cần redis RIÊNG (`shadow-c3b-redis.service`, cổng khác, sửa `redis.config`);
   kiểm `ss -ltn` mọi cổng app mở (nếu có) để không trùng #1. Aerospike: chỉ ĐỌC 242 (S1/OI/GEOM) — không cần namespace/set riêng.
5. Service `shadow-c3b` = clone `shadow-c3.service`, `WorkingDirectory=/home/ubuntu/shadow_c3b/app`, `Requires=shadow-c3b-redis.service`, journald.
6. RAM: Oracle 23 G; đo 22:05 dùng ~6–8 G (shadow #1 RSS ~3,9 G, asd ~3 G, node ~1 G). #2 thêm ~4 G ⇒ ~11–12 G thường trực;
   job research nặng phải hạ trần (ulimit) ≤ 8 G khi #2 chạy để còn ≥2 G đệm.
7. **Khuyến nghị A/B sạch**: shadow #1 đang chạy jar build 10-02 (≠ cf5c90e4). Cùng mốc 10-07 nên chuyển #1 sang CÙNG jar này với GEOM OFF
   (OFF = hành vi cf5c90e4) ⇒ khác biệt duy nhất giữa #1/#2 là cờ GEOM + model.
8. Kiểm ngày đầu #2: log `[S1-GEOM] BAT` (model `[?,18]`), `[GEOM] warm-up … ms` (WAN), `grep -c "ERROR.*S1-GEOM"` = 0 sau warm-up,
   số symbol có GEOM/giờ ≈ số coin `[S1] score`.

### So A/B theo tuần (cùng thước, tuần T2 00:00 → CN 23:59 GMT+7, chỉ lệnh MỞ trong tuần)
| Chỉ số | Nguồn | Ghi chú |
|---|---|---|
| n lệnh vào | ledger mỗi shadow | |
| PnL giấy (% vốn, gộp + TB/lệnh) | ledger | cùng PAPER_EQUITY |
| SL% (tỷ lệ thoát bằng SL) | ledger | sim GEOM: 13,41% vs CTRL 13,83% |
| top-16 overlap #1 vs #2 mỗi tick | `sel_dump` / `LATEST_SEL_RANK` | sim: G vs ORIG 0,80 |
| tick bị bỏ do GEOM chưa sẵn | log ERROR `[S1-GEOM]` | phải ≈ 0 ngoài warm-up |

Không kết luận promote trước khi có pre-reg riêng (vòng sim là NO-GO; 1 tuần ~ vài chục lệnh không đủ lực thống kê).

## 10. Rủi ro còn lại

1. **Model live ≠ model đã sim**: retrain CPU (GPU Kaggle không được phép); vs G42 GPU cùng fold top-16 0,90. cut20251231 chưa có sim DEV.
2. ONNX↔XGB 1,3–2,9e-6 (> 1e-6 tuyệt đối, cùng cỡ model KEEP9 đang chạy); top-16 không đổi (345/345).
3. Parity làm trên bản sao Oracle `test` (cùng định dạng); dữ liệu live 242 `ticker` 10-2026 chưa replay (tránh đọc WAN 242).
   Giả định chưa kiểm trên 242: `totalUsdt` được ghi (nếu = 0 mọi bản ghi ⇒ không có bar ⇒ #2 bỏ MỌI tick, lộ qua ERROR — fail-safe, không lệch âm thầm).
4. Chi phí WAN: warm-up ~10 200 bản ghi phút (~87 MB, TB 8,6 KB/bản ghi ở Oracle) **chặn** `scoreAll` (synchronized) lần đầu
   (local 2,4–4 s; WAN chưa đo); thường trực 60 bản ghi/giờ + đọc lại giờ chưa chốt (~0,5–1,5 MB/giờ). KEEP9 chỉ 1 bản ghi/giờ.
5. Giờ thủng dữ liệu: symbol không có key KEEP9 offline (18 cột NaN khi train) nhận GEOM một phần ở live (0,06% dòng ứng viên trong 7 ngày).
6. `REQUIRE_VOLUME` xấp xỉ lineage: giờ qv = 0 trong vùng sống (0,08% store) live coi là thiếu.
7. Rank GEOM trên toàn thị trường (đúng offline) — khác quy ước rank KEEP9 live (trong universe selector; có sẵn, không đụng).
8. `LIVE_FEAT_DUMP`/`sel_dump` KHÔNG ghi 9 cột GEOM ⇒ chưa có vết audit feature cho #2 (thêm sau nếu cần).
9. `oracle_heavy.lock`: file rỗng mồ côi từ 21:48:39 (không phải job này, không process giữ). Parity cuối chạy trực tiếp (ulimit 10 G, máy rảnh),
   không xoá lock. 2 tiến trình `gl_chain2.sh` của job này còn chờ lock (không được phép kill) — đã chặn bằng `parity/.done`
   (python thoát ngay), khi lock biến mất chúng chỉ ghi/xoá lock rồi kết thúc.

## 11. Tái lập

```
D=~/claude_master/1003/geom_live; cd $D
python3 geom_live_model.py feat                  # geom_x1.parquet md5 6903e178 (= vòng GEOM)
python3 geom_live_model.py train 20251001        # đối chứng CPU vs GPU G42
python3 geom_live_model.py train 20251231        # model LIVE
java -cp jar/binance-java-sdk-1.2.4.jar com.binance.chuyennd.research.s1live.GeomParityProbe \
     geom 127.0.0.1 3222 test 1766624400000 1767225600000 parity/java_geom_dev7d.csv
java -cp ... GeomParityProbe onnx model/s1geom_g42_cut20251231.onnx model/s1geom_g42_cut20251231.orttest.csv parity/ort_java_20251231.csv
GEOM_PARITY_FORCE=1 python3 geom_live_model.py parity parity/java_geom_dev7d.csv model/s1geom_g42_cut20251231.{json,onnx}
```
Kết quả: `parity/parity_result.json`, `model/*.manifest.json`, `cls_diff.txt`, `mvn_test_full.log`.
