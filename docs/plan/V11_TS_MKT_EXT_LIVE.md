# V11_TS_MKT_EXT_LIVE — port TS_MKT_EXT X14 sang live (sổ GIẤY c3_shadow), gói v1.1

Ngày 2026-10-20. Owner 10-20 đã quyết: X14 vào gói v1.1, chạy shadow trên 242; cửa sổ promotion chính thức bắt đầu khi gói v1.1 chốt.
Plan này commit TRƯỚC khi viết code. Nhánh code `v1.1/ts-mkt-ext` từ `66cb6196` (= jar v11b `d7824f6d` đang chạy 242).
Phạm vi agent: code + build + kiểm offline + runbook. KHÔNG deploy, KHÔNG đọc/ghi 242, không Binance REST.

## 1. Luật sim (nguồn sự thật — luật đóng băng, không tune)

| # | Điểm | Sim (file:dòng) | Live chốt |
|---|---|---|---|
| S1 | Chỗ áp | `SimulatorMarketLevelTicker1MStopLoss.java:1042-1058` (`~/src_wt_bcd`, `feat/ts-mkt-ext` a8690d46, jar sim cc0f9d11): nhánh LOSER_TIME_STOP, cụm **chưa arm** (`priceSL == null`), neo `clusterFirstLegTime` (fallback `timeStart`) | `ShadowBookC3.tick` nhánh `(b)` time-stop (`ShadowBookC3.java:399`), cụm `priceSL == null`, neo `tsFirstLeg` (= clusterFirstLegTime). |
| S2 | "Lỗ" | KHÔNG có điều kiện giá: "loser" = chưa arm trailing. Không so giá với entry. | Giữ đúng: không thêm điều kiện PnL (cụm chưa arm mà đang lãi < 7 % cũng được kéo dài, như sim). |
| S3 | Hoãn | `age > 168h ∧ EXT_HOURS>0 ∧ age ≤ (168+336)h ∧ floorDiv(time, 86400000) ∈ EXT_DAYS` ⇒ không cắt ở tick này, xét lại tick sau (`:1044-1050`) | `age > 168h ∧ LIVE_TS_MKT_EXT=1 ∧ age ≤ 504h ∧ cờ(ngày UTC của now) = ON` ⇒ không cắt. Không có trạng thái "đã kéo dài": quyết định lại mỗi nhịp 10 s. |
| S4 | Cờ tắt giữa chừng / quá 504h | nhánh `else if (age > 168h)` cắt ngay ở tick đầu tiên của ngày không cờ, hoặc khi age > 504h (`:1051-1057`), giá `min(open, close)` | cắt ngay ở nhịp đầu tiên ngày không cờ hoặc age > 504h, giá = giá realtime nhịp đó (giữ cách v11b cắt time-stop; reason ledger vẫn `TIME_STOP_168H`). |
| S5 | `time` | khoá phút của `time2Tickers` = open time nến 1m (ms UTC) (`:229`) | `System.currentTimeMillis()` của nhịp exit (lệch ≤ 1 phút quanh 00:00 UTC). |
| S6 | DCA/ladder | luật trên cụm đã merge, neo leg đầu; DCA/BIG_DOWN vẫn chạy bình thường trong lúc hoãn; trailing arm bình thường | Như sim: `addLeg` không đổi `tsFirstLeg`; DCA grid/arm/ratchet không đụng. |
| S7 | Định nghĩa cờ | `tsx_flags.py` / `tsx_ho.py:flags()`: `L = cumsum(ew_r)`, `eod = L.groupby(floor('D')).last()`, `dd = exp(eod − eod.rolling(31, min_periods=1).max()) − 1`, cờ ngày d+1 ⟺ `dd(d) ≤ −0,30` | `dd(d) = exp(P(d) − max_{k∈[d−30,d]} P(k)) − 1` với `P(k) = Σ_{j=d−29..k} S_j`, `P(d−30)=0`, `S_j` = tổng EW ngày j; cờ(D) = `dd(D−1) ≤ −0,30`. Tương đương đại số với sim khi đủ 31 ngày liền (rolling theo HÀNG = theo ngày lịch). |
| S8 | ALT_EW phút | `edge_attr_build.py` `logret`/`build_index` (trích ast trong `tsx_ew_local.py`): r = ln close(t) − ln close(t−1m) cùng symbol, nến liền kề (Δts = 60 000), `qv>0` cả hai nến, `isfinite`, bỏ `BTCUSDT`,`ETHUSDT`, cắt ±0,5, **TB đều** theo phút (pandas groupby mean); ts = open time UTC | Giống hệt, float64 (`Math.log`). Universe = mọi symbol có nến trong record phút `kline_1m_opt` (đã +USDT) trừ BTC/ETH. |
| S9 | Biên tháng | `logret` chạy TỪNG THÁNG (`read_month`) ⇒ phút 00:00 UTC ngày 1 mỗi tháng KHÔNG có return (index bắt đầu 00:01; 2026-09 có 43 199 phút) | **Tái lập** (cờ parity): xoá trạng thái nến trước khi đổi tháng UTC ⇒ ngày 1 tối đa 1 439 phút. Mục đích: bit-parity với index sim. |
| S10 | Ngày cờ | `SIM_LOSER_TS_EXT_DAYS` = danh sách ngày UTC (`Configs.java:922-933` a8690d46) tính trước từ Vision | Tính live hằng ngày từ dữ liệu của chính live (mục 2). |

Mơ hồ ở sim và lựa chọn: (i) "lỗ" = chưa arm (S2); (ii) tick ở sim là nến 1m, live là nhịp 10 s giá realtime — giữ nguyên cách v11b; (iii) sim
kiểm time-stop TRƯỚC arm trong cùng nến, live (v11b) kiểm arm trước — khác sẵn có từ v11b, không đổi; (iv) biên tháng (S9) là đặc tính
dựng index của sim, live tái lập để cờ trùng.

## 2. Dữ liệu live cho ALT_EW
- Nguồn: Aerospike set `kline_1m_opt` mà chính JVM live đang đọc (`DataManagerAerospikeFloatSim.readDataFromAerospikeCustom`, client
  `getReadClient()` = `AEROSPIKE_READ_CLUSTER` của 242). KHÔNG Vision, KHÔNG REST. Giá/qv trong store là float32 (`KlineObjectSimple`) ⇒
  ln(float32) — sai số ~1e-7 tương đối/nến; offline đo ảnh hưởng lên cờ bằng cách ép float32 dữ liệu Vision (mục 5a).
- Đọc từng khối 60 phút (nghỉ 200 ms giữa khối) để không chiếm executor 2 luồng dùng chung của live.
- Tổng ngày `S_j`, số phút có EW `n_j` lưu file `run/ts_ext_daily.csv` (key `LIVE_TS_EXT_FILE`; ghi bởi chính app, cùng kiểu
  `run/legacy_symbols.csv`). Sau restart: nạp file, chỉ đọc Aerospike cho ngày thiếu trong [D−30, D−1].
- Thiếu dữ liệu: nếu một ngày trong 30 ngày `[D−30, D−1]` vắng hoặc `n_j < 1296` (90 % của 1440; ngưỡng chất lượng dữ liệu, chọn trước;
  Vision 2021-07→2026-09 thấp nhất 1348) ⇒ cờ(D) = **NA ⇒ OFF** + `WARN [TS-EXT]`.

## 3. Lịch tính
- Cờ(D) tính ở nhịp đầu tiên sau **00:03 UTC (07:03 +07)** của ngày D (độ trễ an toàn cho collector chốt nến 23:59).
- Nếu ngày D−1 chưa đủ phút (< 1440, ngày 1 tháng < 1439) thì thử lại mỗi phút tới **00:20 UTC (07:20 +07)**; quá hạn ⇒ tính với
  phần có (áp luật thiếu dữ liệu ở trên). Ngày đã chốt được ghi file, không tính lại.
- Khoảng 00:00 UTC → lúc có cờ(D) (tối đa 00:20), và 20 phút đầu sau khởi động khi chưa có cờ hôm nay: trạng thái **PENDING ⇒ GIỮ**
  (không cắt) các cụm trong cửa sổ 168h < age ≤ 504h; hết hạn mà vẫn chưa có ⇒ OFF + WARN. Lý do: cắt là không đảo được, giữ vài phút
  thì đảo được; lệch so với sim tối đa ~20 phút giữ thêm ở ngày cờ chuyển ON→OFF.
- Khởi động lại giữa ngày: cờ hôm nay tính lại ngay từ file (không cần Aerospike). Quyết định hoãn không có trạng thái (S3) ⇒ restart
  không làm mất/kéo dài sai một cụm nào.

## 4. Ràng buộc sống còn — chỉ sổ GIẤY c3_shadow
- Bật ⟺ `LIVE_TS_MKT_EXT=1` ∧ `LIVE_PROFILE=c3_shadow` (`LiveProfileC3.on() ∧ !isLive()`). Mặc định 0 ⇒ mọi nhánh mới không chạy,
  `ShadowBookC3.tick` = v11b. `c3_live` ⇒ không bật (+WARN).
- Chỉ gọi từ `ShadowBookC3.tick` (sổ giấy). Đường vị thế THẬT (LEGACY 44) — `BinanceOrderTradingManager.processDynamicTP_SL` /
  `initSLFirst` — KHÔNG gọi lớp mới (time-stop ở đó vốn chỉ là dòng log và `timeStopApplies` loại legacy). Thêm chốt kép: symbol
  `LegacySymbols.isLegacySymbol` ⇒ không bao giờ hoãn (về đúng hành vi v11b). Unit test chứng minh cả hai (kể cả test quét mã nguồn
  `BinanceOrderTradingManager.java` không tham chiếu lớp mới).

## 5. Log `[TS-EXT]`
- Khởi động: `[TS-EXT] BAT|TAT key=… profile=… extHours=336 thr=-0.30 file=…`.
- Mỗi lần chốt cờ: `[TS-EXT] flag day=<D> flag=ON|OFF|NA dd=<dd(D−1)> altEwIdx=<1+dd> P=<P(D−1)> max30=<maxP> max30Day=<k> minN=<min n_j> src=file|aero`.
- Mỗi cụm: `[TS-EXT] defer-START sym age_h flag`, `[TS-EXT] defer-END sym age_h reason=FLAG_OFF|MAX_504H` (kèm cắt), và
  `ARMED/CLOSED` nếu kết thúc bằng trailing; tóm tắt mỗi giờ `[TS-EXT] status flagToday=… deferring=N [...]`.
- Thiếu dữ liệu / PENDING quá hạn / lỗi đọc: `WARN [TS-EXT] …`.

## 6. Kiểm (fail ⇒ dừng, không build gói)
- (a) Code ALT_EW/cờ của live chạy trên kline Vision (Kaggle `vz-kline1m-*`) 2025-12→2026-09 và 2021-12→2022-12: EW phút khớp
  `ew_2026.npz`/`index.npz` (cùng ts, max|Δ| ≤ 1e-9); cờ 2026-01-01..09-30 = 15 ngày `20260205-20260214,20260216-20260217,20260224-20260225,20260611`
  (ho_flags.json); cờ 2022 = cờ DEV năm 2022 (78 ngày). Thêm: ép float32 — báo số ngày cờ đổi (kỳ vọng 0) và max|Δdd|.
- (b) Cờ=0: harness `V11FeatHarness` jar mới vs jar d7824f6d bit-exact trên 2 cửa sổ cũ; diff class jar chỉ ở lớp đã sửa/thêm.
- (c) Replay quyết định time-stop (hàm `decide` live + cờ live) trên trade list `tsx-ho-x14-s42` so với sim: mọi lệnh time-stop của sim
  phải có phút cắt = phút đầu tiên `decide = CUT`; mọi lệnh kết thúc trong cửa sổ hoãn phải có `decide = DEFER` suốt từ 168h tới lúc đóng.
- Unit test: ALT_EW/cờ trên mẫu tay, lỗ/lãi, đúng 168h/504h, cờ bật/tắt giữa chừng, PENDING, restart (file), LEGACY, cờ=0.
