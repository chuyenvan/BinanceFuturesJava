# PREREG_PARITY_V11_WINDOW — thước parity ĐỊNH KỲ cho cửa sổ promotion gói v1.1, KHÔNG đọc Aerospike 242

- **Ngày chốt:** 2026-10-21 (+07), viết và commit **TRƯỚC** khi chạy bất kỳ phép đo nào trên dữ liệu của cửa sổ.
  Sau khi thấy số: không đổi nguồn, universe, ngưỡng, luật phân loại. Mọi thay đổi = ADDENDUM riêng có ngày, ghi lý do.
- **Đối tượng:** 242, gói v1.1 = jar `eea5adec…` (nhánh `v1.1/ts-mkt-ext` `627e9b34`), env v11b 6 dòng + `LIVE_TS_MKT_EXT=1`,
  c3_shadow. **Cửa sổ:** từ `2026-10-21 07:53:59 (+07)` = nến quyết định đầu tiên `1792543980000` (00:53 UTC), tối thiểu 4 tuần
  (`PREREG_SHADOW2_PROMOTION.md` ADDENDUM c mục D). Tiêu chí gốc giữ nguyên: (ii') P1–P3, (vi-b); tài liệu này chỉ thay
  **nguồn offline** (Vision thay Aerospike 242) và khai rõ phần nào đo được ở D+1, phần nào phải chờ.
- **Ràng buộc:** không đọc Aerospike 242 dưới mọi hình thức; 242 chỉ đọc file (log/dump/buffer) qua `ssh … cat|zcat|tar cf -`
  stream về Oracle, không ghi file nào lên 242; không Binance REST; chỉ file tĩnh `data.binance.vision`.

## 1. Thước (ruler)

| ký hiệu | là gì | dùng cho |
|---|---|---|
| **OFF-BT** | `V11FeatHarness` mode `BT` (= `ExportGateDataset.replayToCsv` + vòng Tool1), class của jar `eea5adec`, chế độ `HARNESS_OFFLINE=1`, `SIM_RANK_TIEBREAK_SYMBOL=1`, md died `BTCDOM,USDC` | thước backtest cho mọi chỉ số |
| **OFF-NEW2** | cùng harness mode `NEW2` (gọi chính `LiveFeaturePipeline` + `LiveTickerWindow` của jar), seed theo giờ restart thật lấy từ log `MainClass` | đối chứng code: OFF-NEW2 ≡ OFF-BT phải 100 % trên cùng dữ liệu |
| **LIVE** | `feat_dump`, `sel_dump`, `s1_dump`, `storage/data/predictionSymbol/<ngày>/<ts>.features`, `run/gate_ratio_live.bin`, log `full.log` (+ archived) của 242 | đại lượng live |

`HARNESS_OFFLINE=1` (khai trước, kiểm ở §6): (a) kline 1m chỉ từ file cache cục bộ dựng từ Vision, thiếu file ⇒ dừng;
(b) `SimpleSymbolMapper` dùng store file cục bộ (snapshot thứ tự chữ cái của universe; tính bất biến theo id phải được chứng
minh ở §6 R1); (c) `FundingFeeManager` nạp từ file funding Vision monthly; (d) chặn cứng nhiều lớp: config host Aerospike
giả `offline.invalid` + `AEROSPIKE_READ_CLUSTER` giả (226, không bao giờ 242), stub `com.aerospike.client.AerospikeClient`
đứng trước jar trên classpath — mọi constructor ⇒ log ERROR + `Runtime.halt(97)`; `SecurityManager` chặn mọi connect/resolve
không phải loopback ⇒ `halt(98)`; wrapper fail nếu log có dấu vết đường đọc Aerospike bị nuốt (`AEROSPIKE_READ_CLUSTER`,
`Loaded Symbol Mapper`, `Init funding fee data` từ Aerospike); chạy dưới `strace -f -e trace=connect` và đếm connect tới
`103.157.218.242` (phải = 0).

## 2. Nguồn offline

1. **Kline 1m:** Vision UM `daily/klines/<SYM>/1m/<SYM>-1m-<D>.zip` (phát hành D+1), ép float32 bằng `Float.valueOf(String)`
   (= `KlineObjectSimple.convertString2Kline`: open/high/low/close/quote-volume cột 1/2/3/4/7). Lưu zip gốc + md5 trên Oracle.
2. **Universe U_D:** = tập symbol của store 242 lấy KHÔNG qua Aerospike: hợp các tập symbol trong cache 242 đã có trên Oracle
   (cache 10-14..17 và 10-19..20, đọc trước đây) ∪ symbol xuất hiện trong `s1_dump`/`sel_dump`/`predictionSymbol` của ngày D;
   bỏ symbol không có file Vision ngày D (404). Kiểm: |U_D| so với `nsym=` (`[FEAT-PIPE] ticks=…`) và `… N symbol trong bo nho`
   (`[TICKER-CACHE]`) của log; lệch ⇒ ghi, các phút liên quan nhãn K3.
3. **Funding:** Vision UM `monthly/fundingRate` (lake `~/claude_master/1016/carry/fund/funding-<năm>.parquet`, nguồn Vision
   monthly; kiểm lại tháng gần nhất bằng tải trực tiếp). Vision **không có fundingRate daily** (đã kiểm 404) và tháng M chỉ
   phát hành đầu tháng M+1 ⇒ **ở D+1 không có funding của tháng hiện tại**.
4. **OI #41–45, S1 f7 (lsg) / f8 (rank OI):** live tra set `oi_feat_*` 242 tính sẵn; tái lập từ Vision `metrics` 5m cần dựng
   lại pipeline OI ⇒ **NGOÀI PHẠM VI**, dùng giá trị live (tiêm) như PARITY_1020/PARITY_V11_1020.
5. **Cờ TS-EXT:** Vision UM 1m daily (như 1) + `TsxLiveOffline` (code `AltEwIndex` của jar v11c), universe live.
6. **q_t:** file buffer `run/gate_ratio_live.bin` đọc bằng `cat` (chỉ đọc) + log `[GATE-RATIO] q_t9`.

## 3. Tần suất, hai lượt chấm

- **Lượt D (hằng ngày, sơ bộ):** chạy khi Vision ngày D (UTC) đã phát hành cho ≥ 99 % symbol của U_D; Vision trễ ⇒ chạy gộp
  2 ngày/lần (không bỏ ngày). Phút chấm = mọi phút quyết định có trong `feat_dump` thuộc [max(1792543980000, D 00:00 UTC),
  D 23:59 UTC]. Đại lượng phụ thuộc funding tháng hiện tại được **tiêm từ live** (§4) ⇒ kết quả lượt D là SƠ BỘ cho các chỉ số đó.
- **Lượt M (hằng tháng, chính thức cho phần funding):** khi Vision monthly `fundingRate` tháng M có cho ≥ 99 % symbol U,
  chạy lại toàn bộ các ngày của tháng M trong cửa sổ, KHÔNG tiêm funding. Phán quyết chính thức P1/P2 theo (ii') lấy từ lượt M
  (lượt D không bao giờ tự thành TRƯỢT cho phần funding; nhưng TRƯỢT ở phần không-funding của lượt D là TRƯỢT).
- **Tập phụ thuộc funding (khai từ code, kiểm ở §6 R1):** gate 33: `fundingRateRaw`, `fundingRateAvg24H`, `fundingRateTrend`;
  Tool1 45 (0-based `f0..f44`): `f17..f25` (coinFundingRate, basketFundingAvg, fundingRateAvg24H, fundingRateTrend,
  fundingPercentileCoin, fundingZCoin, fundingPersistence, fundingSum24h, fundingAbs) và `f32` (fundingRankCS); OI `f40..f44`.
  Nếu R1 cho thấy cột khác cũng phụ thuộc funding ⇒ dừng, ADDENDUM trước khi chạy cửa sổ.

## 4. Chỉ số và ngưỡng

Khớp 1 giá trị: `|a − b| ≤ 1e-6·(1 + |b|)` (NaN = NaN). rel p15 = `|p15_live − p15_off| / |p15_off|`.

| mã | chỉ số | lượt D | lượt M | ngưỡng / trạng thái |
|---|---|---|---|---|
| **P1-F** | 33 feature gate (feat_dump BTCUSDT) vs OFF-BT: % phút ALL-khớp; từng feature | 30 cột không-funding | 33 cột | báo cáo; mỗi phút lệch phải có nhãn §5 |
| **P1** | p15: `p15_off` = ONNX `Model_Regressor_Return15M` trên vector OFF-BT (lượt D: 3 cột funding thay bằng live) | ✔ (sơ bộ) | ✔ (chính thức) | **median rel ≤ 1e-4 VÀ rel ≤ 1e-3 ở ≥ 98 % phút** (= (ii') P1) |
| P1-m | p15 ONNX trên vector live vs `p15_out` live | ✔ | ✔ | 100 % ≤ 1e-6 (kiểm model/thứ tự cột) |
| **MD** | `rateDownAvg/rateUpAvg/rateDown15MAvg` feat_dump vs `r_down/r_up/r_down15` OFF-BT | ✔ | ✔ | báo cáo %; phút lệch có nhãn |
| **FUND** | Tool1 #1–40 (predictionSymbol live vs fund_BT): % dòng, % phút ALL-khớp | bỏ f17–f25, f32 | f0–f39 | báo cáo; phút lệch có nhãn |
| **NET** | net015 `1−P(win)` (ONNX `g015x26_f15_cut20251231`) trên vector OFF (lượt D: f17–f25, f32 tiêm live; mọi lượt: f40–f44 tiêm live) vs trên vector live | ✔ | ✔ | báo cáo % ≤ 1e-6, max |Δ| |
| **S1-I** | thứ tự top-24 `sel_dump` == sort(score↑, symbol↑) của `s1_dump` bỏ LEGACY/coin đang giữ; |selectorScore| == |score| | ✔ | — | **100 %** (code, không phụ thuộc dữ liệu); < 100 % ⇒ XÁM + điều tra |
| S1-m | ONNX S1 `s1a2x1_cut20251231` trên f0..f8 live == score live | ✔ | — | 100 % ≤ 1e-6 |
| **S1-V** | f0..f6 tính lại từ close 1h Vision (close nến 1m phút h−1), f7/f8 tiêm live ⇒ score ⇒ top-24: % khớp f0..f6, score, Jaccard, Spearman, trùng thứ tự | ✔ | — | báo cáo (không ngưỡng: OI ngoài phạm vi, close 1h live nạp lúc chưa settle) |
| **GV-I** | `gateValue` sel_dump == luật `LiveBuildMap.assign` trên pw live + thứ tự S1 live | ✔ | — | 100 % |
| **GV-O** | `gateValue` với pw OFF (NET) + thứ tự S1 live | ✔ | ✔ | báo cáo % |
| **P2** | quyết định PASS theo cặp (phút, ứng viên): ngưỡng thực `thr = q_t·max(DYN_MIN, gv/0,15·1,2876)·1,55` (DYN_MIN 0,26787), live: p15_live, gv_live, q_t log; offline: p15_off, gv_off, q_t replay. Lật nặng = quyết định khác VÀ `|p15−thr|/thr > 1 %` ở phía bất kỳ | ✔ (sơ bộ) | ✔ (chính thức) | **lật nặng = 0** (≥ 1 ⇒ TRƯỢT); lật biên chỉ báo cáo; báo số cặp r/q ≥ 0,9 (P2 chỉ thật sự được thử khi có cặp gần ngưỡng); `[GATE] n_pass` log == pass_live tính lại |
| **P3** | `q_t9` log mỗi giờ vs q replay causal (`GateRatioBuffer`: q tính đầu giờ trên record ts ∈ [h−90d, h), giờ có restart: record flush trước restart) từ buffer đọc bằng cat | ✔ | — | **rel ≤ 1e-6 mọi giờ** (q_t9 `%.9g` nay đo được 1e-6) |
| **TSX** | cờ `[TS-EXT] flag day=D` live == cờ Vision cùng luật (universe live); `[TS-EXT] day … sum_ew n_min` vs S_j Vision | ✔ (cần Vision D−1) | — | **cờ trùng** (ON/OFF lệch ⇒ TRƯỢT parity (vi-b)); NA ghi sổ; |ΔS_j| báo cáo, kỳ vọng bit-exact khi n_min live = 1440 |
| CTL | OFF-NEW2 vs OFF-BT cùng dữ liệu Vision: ALL33 + p15 + basket + Tool1 #1–40 | ✔ | ✔ | 100 % (lệch ⇒ lỗi harness/code ⇒ dừng đo, điều tra) |

Phút loại khỏi chấm (liệt kê): phút không có dòng feat_dump; phút warm-up sau restart mà live không có feature
(vd 07:53 lỗi `[FEAT-PIPE] khong co feature snapshot`).

## 5. Phân loại MỌI phút lệch (cơ học, áp sau khi tính, không chọn tay)

Một phút M lệch (ở bất kỳ chỉ số P1-F/P1/MD/FUND/NET/GV-O/S1-V) nhận MỌI nhãn khớp:
- **K1 — collector ghi đè sau quyết định:** có cửa sổ `[LIVE-KLINE]` (10') kết thúc trong [M−20', M+10'] với
  `reread_overwritten>0` hoặc `decided_on_unsettled>0` (S1-V: thêm `s1_close_rewritten>0`). Vision là dữ liệu cuối ⇒ không tái lập
  được trạng thái "unsettled" (giới hạn vốn có, như PARITY_V11_1020 21:39).
- **K2 — dữ liệu Vision/store khác:** (a) cache Vision thiếu ≥ 1 symbol của U_D tại phút nào trong [M−20', M] mà symbol đó có
  nến ở phút trước và sau (lỗ Vision); hoặc (b) ngày của M có `[TS-EXT] day … n_min` live < 1440 (store 242 thiếu phút); hoặc
  (c) `[FEAT-PIPE]` có `gap_minutes/no_snap/partial > 0` trong khối 60 tick chứa M.
- **K3 — khác universe:** |U_D| ≠ `nsym` live gần nhất, hoặc U thay đổi (niêm yết/huỷ) trong [M−1440', M].
- **K4 — chờ funding/OI:** chỉ dùng ở lượt M nếu funding Vision monthly thiếu symbol (≤ 1 %); OI đã tiêm nên không dùng.
- **K5 — CHƯA GIẢI THÍCH:** không có nhãn nào.

Trạng thái lượt: nếu P1/P2/P3/TSX/S1-I/GV-I/CTL đạt ngưỡng và K5 = 0 ⇒ **ĐẠT**; đạt ngưỡng nhưng K5 > 0 ⇒ **XÁM** (điều tra
trước lượt kế, không đổi ngưỡng); không đạt ngưỡng ⇒ **TRƯỢT** (theo (ii') / (vi-b)). Phút K1–K3 vẫn TÍNH vào ngưỡng P1/P2
(không loại phút để cứu ngưỡng) — nhãn chỉ để giải thích.

## 6. Tái kiểm harness offline (điều kiện TRƯỚC khi chấm cửa sổ)

- **R0 (chặn mạng):** test tự động: (a) `getClient242()`, `getClientOracle()`, `getReadClient()` trong JVM con ⇒ exit 97 + log
  marker; (b) `new Socket("103.157.218.242", 3222)` ⇒ exit 98 (chặn trước syscall connect, xác nhận bằng strace);
  (c) chạy harness thật dưới strace: 0 connect tới 103.157.218.242 / bất kỳ IP ngoài loopback.
- **R1 (provider offline không đổi kết quả):** harness offline trên đúng cache 242 đã lưu (cửa sổ 1: 720' restart 10-16 20:00:05;
  cửa sổ 2: 411' restart 10-17 08:00:32), mapper file, funding Vision tới 2026-09-30 ⇒ so với `harness/s6/{out,fund}_{BT,NEW2}`
  và `s6/seg2/…`: **mọi cột ngoài tập phụ thuộc funding (§3) bit-identical, tập dòng Tool1 trùng**. Cột funding lệch là kỳ vọng
  (thiếu funding tháng 10); chỉ được khẳng định ở lượt M.
- **R2 (dữ liệu):** cache Vision vs cache 242 cùng phút, từng ô (symbol, phút, 5 trường): báo % bit-exact; mọi ô lệch liệt kê.
- **R3 (đầu-cuối):** harness offline trên cache Vision của 2 cửa sổ vs s6: cột không-funding phải trùng ở mọi phút không có ô
  R2 lệch trong [M−1440', M] (phút có ô lệch: nhãn K2, liệt kê). Có lệch không giải thích ⇒ không chấm cửa sổ.

## 7. Lưu trữ (ràng buộc để lượt M khả thi)

Lượt M cần `feat_dump`, `sel_dump`, `s1_dump`, `predictionSymbol`, log `[GATE-RATIO]/[GATE]/[LIVE-KLINE]/[FEAT-PIPE]/[TS-EXT]/MainClass`
và buffer của toàn cửa sổ ⇒ kéo về Oracle hằng ngày (chỉ đọc 242). Thiếu file của 1 ngày ⇒ ngày đó = KHÔNG ĐO ĐƯỢC (ghi rõ,
không coi là ĐẠT).

## 8. Đầu ra

`docs/result/PARITY_V11_WINDOW_D<n>.md` mỗi lượt + JSON máy đọc; script `research/parity_v11/`.
