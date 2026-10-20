# V11_TS_MKT_EXT_OFFLINE — kiểm offline port TS_MKT_EXT X14 sang live (2026-10-20)

Spec: `docs/plan/V11_TS_MKT_EXT_LIVE.md` (86501057, commit TRƯỚC code). Code: nhánh `v1.1/ts-mkt-ext` **`627e9b34`** trên `66cb6196`.
Jar **`eea5adecaff93d3fc350e4d13b3ecb2a`** (`~/claude_master/v11_tsx/jar/binance-java-sdk-1.2.4.jar_v11c_eea5adec`).
Không đọc/ghi 242 trong các kiểm dưới (ngoại lệ ghi ở §b). Không REST. Script: `research/tsx/live/`; số thô `docs/result/ts_mkt_ext/live/`.

## Unit test (`mvn -o package`: 361 test, 0 fail, 1 skip có sẵn)
- `AltEwIndexTest` (5): EW phút tính tay (cắt ±0,5, bỏ BTC/ETH, qv=0, nến không liền kề, giá 0), biên tháng S9, cờ = công thức
  `eod − rolling(31).max()` viết lại trong test (120 ngày, |Δdd| ≤ 1e-12), ngưỡng ≤ −0,30 (±1e-12/1e-9), thiếu ngày / ngày < 1296 phút ⇒ NA,
  adapter Map (record Aerospike float32) ≡ đường mảng.
- `TsMktExtTest` (11): biên 168h (`>`) / 504h (`≤`) đúng sim; cờ ON→OFF giữa chừng ⇒ cắt ở nhịp đầu ngày OFF; cụm chưa arm đang lãi +5 %
  cũng được hoãn (S2); **cờ TẮT ⇒ cắt 169h dù ngày ON (= v11b)**; **LEGACY không bao giờ được hoãn** (cả hàm thuần lẫn sổ giấy);
  **quét mã nguồn: chỉ `ShadowBookC3.java`/`TsMktExt.java` gọi `TsMktExt.`, `BinanceOrderTradingManager.java` không nhắc lớp mới**;
  arm trong lúc hoãn ⇒ ra khỏi time-stop; DCA giữ mốc leg đầu; PENDING giữ tới 00:22 UTC rồi OFF; ân hạn khởi động 20';
  lịch 00:03 / chờ nến 23:59 / chốt 00:20; **restart giữa ngày: nạp file, 0 lần đọc store, cùng cờ + dd bit-exact**.

## (a) ALT_EW + cờ ngày bằng code LIVE trên kline Vision — **ĐẠT**
Harness `TsxLiveOffline` gọi đúng `AltEwIndex` của jar live trên bin từ parquet Kaggle `vz-kline1m-*` (đọc bằng `read_month` của
`edge_attr_build.py`, trích ast như `tsx_ew_local.py`). Đối chiếu `ew_2026.npz` (HO) và `edge_attr/index.npz` (DEV).

| | EW phút: số phút live/sim | cùng ts | max\|Δ\| | cờ ON live | cờ sim | trùng | max\|Δdd\| | lề tới ngưỡng (min\|dd+0,30\|) |
|---|---|---|---|---|---|---|---|---|
| 2025-12→2026-09 (cờ 01-01..09-30) | 437 750 / 437 750 | ✔ | 2,5e-17 | 15 | 15 (`ho_flags.json`) | ✔ `20260205-20260214,20260216-20260217,20260224-20260225,20260611` | 2,5e-14 | 0,0023 |
| 2021-12→2022-12 (cờ 2022) | 570 161 / 570 161 | ✔ | 4,8e-17 | 78 | 78 (`flags.json` DEV) | ✔ | 1,4e-14 | 0,0035 |

- **float32** (mô phỏng store Aerospike: ép close/qv về float trước `ln`): cùng tập phút, |ΔEW| ≤ 1,4e-8; cờ **trùng 15/15 và 78/78**;
  max|Δdd| 4,7e-8 (2026) / 6,5e-8 (2022) ≪ lề 0,0023.
- 0 ngày NA (Vision không ngày nào < 1296 phút trong 2 kỳ).

### (a2) Dữ liệu đúng định dạng live (record `kline_1m_opt` 242 đã cache trước đây trên Oracle, 10-13 20:20 → 10-17 07:50)
Đường adapter `AltEwIndex.feed(ts, Map<String,KlineObjectSimple>)` (đúng hàm live gọi): 738 symbol/phút (p5 = max = 738), ngày đủ
**1440/1440 phút EW** (10-14, 10-15, 10-16), S_j = −0,0388 / +0,0012 / −0,0148 — không có cờ (thị trường bình thường). Không có Vision
tháng 10 để so trị số (Kaggle 2026 dừng ở 09).

### (a3) Universe Vision (sim) vs live
- Vision 2026-09: 26,9 M cặp (sym, phút) đóng góp EW; **11 symbol** đóng góp nhưng KHÔNG có trong record 242 (738 sym, 10-13..10-17):
  5 symbol tên Unicode (`币安人生USDT`, `牛来USDT`, `龙虾USDT`, `我踏马来了USDT`, `哈基米USDT`), `BTCDOMUSDT`, `USDCUSDT`, `PROMPTUSDT`,
  `1000000BOBUSDT`, `PUMPBTCUSDT`, `STGUSDT` = 1,7 % cặp; ngày 09-30: 737 sym đóng góp, 10 trong số đó không có ở 242.
  |ΔS_ngày| khi bỏ chúng: max 0,0019, TB 0,0006 (`univ_check.json`).
- Độ nhạy cờ 2026 (float32, như store live): bỏ tập A = 7 symbol "cấu trúc" (Unicode + BTCDOM + USDC) hoặc tập B = cả 11 ⇒ cờ vẫn
  **15/15 trùng**, max|Δdd| 0,0034 (A) / 0,0045 (B) (`univ_flags.json`). Lưu ý: lớn hơn lề nhỏ nhất tới ngưỡng (0,0023) ⇒ một ngày sát
  ngưỡng có thể lật do khác universe; 2026 không ngày nào lật. Không đổi luật (live dùng universe của chính nó — đã khai ở addendum (vi-b)).

## (b) Cờ = 0 ⇒ v11b — **ĐẠT theo bytecode**, harness KHÔNG chạy lại (lý do bên dưới)
- So toàn bộ entry của jar mới vs jar 242 `d7824f6d`: **1114 resource trùng CRC**; mọi `.class` (kể cả thư viện shade) trùng CRC **trừ 9**:
  `ShadowBookC3` (sửa) + `AltEwIndex{,$DayStat,$FlagResult,$State}`, `TsMktExt{,$Decision,$Flag,$MinuteReader}` (mới).
  ⇒ mọi đường không đi qua `ShadowBookC3` (feature/gate/S1/funding/legacy — toàn bộ phạm vi `V11FeatHarness`) là cùng bytecode với
  d7824f6d ⇒ output harness bit-exact là hệ quả trực tiếp. Trong `ShadowBookC3`, cờ TẮT ⇒ 4 điểm gọi trả ngay (`enabled()` false) — unit test
  `flagOffEqualsV11b` + toàn bộ `ShadowBookC3Test`/`LegacyIsolationTest` cũ PASS.
- Khi cờ tắt: không thêm dòng log nào; khác biệt duy nhất là `Cfg.get("LIVE_TS_MKT_EXT")` thêm key vào tập ASKED (audit).
- Lệch so với plan: thêm 1 dòng log `[TS-EXT] day <ngày> sum_ew=… n_min=… src=aero` mỗi ngày đọc từ store (để đối chiếu Vision sau này).
- **Harness không chạy lại — SỰ CỐ ĐỌC 242**: `V11FeatHarness` (config `AEROSPIKE_READ_CLUSTER=242`) dùng `getReadClient()` = 242 cho
  `SimpleSymbolMapper` và `FundingFeeManager` (`getAllFundingMap` = scanAll set `funding_data`). Tôi đã khởi chạy lượt w1 LIVE (jar cũ)
  22:49:37 → 22:50:24 (có thể thêm 1 lượt khởi động bị huỷ ngay trước đó): log có "Loaded Symbol Mapper: 937 symbols from Aerospike"
  (22:49:49) và "Init funding fee data: 887 symbols" (22:49:53) ⇒ **đã ĐỌC 242** (1 key `symbol_mapper` + scan `funding_data`), không ghi
  (harness ép `Live242WriteGuard.decided=false`). Lệnh không bị classifier chặn vì là tiến trình Java. Đã dừng ngay khi nhận ra, không
  chạy lại; kết luận (b) dựa trên so bytecode ở trên. Bài học: mọi harness trong `~/claude_master/v11_settle/harness` đều đọc 242.
- Lưu ý vận hành: lúc đó trên Oracle có tiến trình mồ côi `bash run.sh` (PID 601206, từ 18:06, cwd `~/claude_master/v11_settle/harness`)
  chạy lại vòng LIVE/NEW/BT (cũng đọc symbol_mapper 242); lệnh dừng của tôi đã SIGTERM nhầm java LIVE của nó (status `LIVE exit=143`),
  nó chạy tiếp NEW/BT rồi tự kết thúc 22:50. Không phải tiến trình của phiên này.

## (c) Replay quyết định time-stop của code live trên trade list HO 2026 — **ĐẠT 8/8 seed**
`TsMktExt.decide` (code live) + cờ live (a) trên `printDone` của `tsx-ho-x14-s<seed>` (giờ +07 → UTC). Cụm = (sym, phút đóng): các leg DCA/
BIG_DOWN của cùng cụm in riêng dòng nhưng đóng cùng phút; neo = leg đầu (= `clusterFirstLegTime`). Với mỗi cụm còn mở qua 168h:
phút cắt dự đoán = phút đầu tiên `decide = CUT` tính từ neo + 168h + 1'.

| seed | cụm quá 168h | time-stop: phút cắt live = phút sim | thoát trailing sau 168h: đều đang hoãn | cụm hoãn live / sim `[TSX] deferClusters` | cắt-sau-hoãn live / sim |
|---|---|---|---|---|---|
| 42 | 57 | 54/54 | 3/3 | 12 / 12 | 9 / 9 |
| 7 | 77 | 74/74 | 3/3 | 14 / 14 | 11 / 11 |
| 13 | 65 | 61/61 | 4/4 | 15 / 15 | 11 / 11 |
| 21 | 74 | 70/70 | 4/4 | 15 / 15 | 11 / 11 |
| 99 | 63 | 60/60 | 3/3 | 14 / 14 | 11 / 11 |
| 123 | 62 | 59/59 | 3/3 | 13 / 13 | 10 / 10 |
| 777 | 72 | 68/68 | 4/4 | 16 / 16 | 12 / 12 |
| 2024 | 77 | 74/74 | 3/3 | 13 / 13 | 10 / 10 |

(Lượt đầu tính theo DÒNG printDone cho 5 seed lệch +1–2 cụm: FIGHT/SPACE có leg thứ hai cùng cụm; gộp theo cụm thì khớp — sim đếm theo
`symbol|clusterFirstLegTime`.) Replay chỉ kiểm phút quyết định (giá cắt live = giá realtime nhịp 10 s, khác `min(open,close)` của sim — giữ cách v11b).

## Rủi ro / giới hạn
1. Universe + chất lượng `kline_1m_opt` 242 trong 30 ngày seed chưa kiểm được offline (không đọc 242). Có log `[TS-EXT] day … sum_ew n_min`
   để đối chiếu với Vision khi có dữ liệu (tiêu chí (vi-b) addendum PREREG_SHADOW2_PROMOTION).
2. Nếu Aerospike 242 không giữ đủ 30 ngày `kline_1m_opt` ⇒ cờ NA ⇒ OFF (an toàn, = v11b) + WARN — runbook §2 mục 2.
3. Seed lần đầu đọc ~30 × 1441 record phút từ 242 trong luồng nền (khối 60', nghỉ 200 ms ⇒ ~3–5'); dùng chung executor 2 luồng của
   `DataManagerAerospikeFloatSim` với các đọc khác của live ⇒ có thể tăng trễ tick vài phút đầu sau deploy (đo ở kiểm 15').
4. PENDING (00:00 → ≤ 00:22 UTC và 20' đầu sau start): cụm trong cửa sổ được giữ thêm tối đa ~22' so với sim khi ngày mới OFF.
5. Hiệu ứng TS_MKT_EXT dồn vào 1 đợt sập (T2/2026); forward 4 tuần thường 0 ngày cờ ⇒ cơ chế có thể chưa được kiểm forward.
