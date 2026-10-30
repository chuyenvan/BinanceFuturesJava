# PREREG_PARITY_V12_DRY — thước parity cho cửa sổ DRY v1.2 (c3_live, UNIVERSE_A1) so với backtest A1

- **Ngày chốt:** 2026-10-30 (+07). Viết và commit **TRƯỚC** khi deploy dry v1.2 và trước bất kỳ phép đo nào trên dữ liệu
  của cửa sổ. Sau khi thấy số: không đổi nguồn, universe, ngưỡng, luật phân loại, định nghĩa "ngày sạch". Mọi thay đổi =
  ADDENDUM riêng, có ngày, ghi lý do, ghi rõ viết trước hay sau khi thấy số (như ADD2/ADD3 của v1.1).
- **Gốc kế thừa:** `docs/prereg/PREREG_PARITY_V11_WINDOW.md` (`481701b2`) + ADDENDUM 1 (`fea9fb97`) + ADDENDUM 2
  (`4eef2788`) + ADDENDUM 3 (`67ce404a`) — gọi chung "v1.1". **Mọi điều không nhắc ở đây giữ nguyên như v1.1** (thước
  OFF-BT/OFF-NEW2/LIVE, `HARNESS_OFFLINE=1` và các lớp chặn mạng, nguồn Vision, hai lượt D/M, dung sai `|a−b| ≤ 1e-6·(1+|b|)`,
  bảng chỉ số §4, luật nhãn K1″/K2/K3′/K4/K5/K6′ theo ADD1–3 từ ngày đầu cửa sổ, lưu trữ §7). Văn bản này chỉ liệt kê
  phần **đổi** và phần **thêm**.
- **Đối tượng:** 242, process strategy/trade `v_t_m` chạy jar v1.2/c3-live do owner deploy bằng
  `ops/c3live/deploy_v12_dry_r4.sh` (jar + md5 thật lấy từ log deploy `NJ_MD5`; hiện là r4f `dbe20705…`, nếu MASTER đổi sang
  bản sau thì ghi md5 vào D1, không cần ADDENDUM khi đường tín hiệu không đổi — đổi đường tín hiệu ⇒ ADDENDUM + mở cửa sổ mới).
  Env dry: `LIVE_PROFILE=c3_live`, `LIVE_ADAPTER=dry` (không key), `SHADOW_NO_PUSH=true`, `UNIVERSE_A1=1`,
  `UNIVERSE_A1_EXCHANGE_INFO=run/c3live_exchangeInfo.json` (cron root làm mới mỗi 15′), `C3_CAPITAL=10000`, phần còn lại
  của env v11 giữ (`LIVE_TS_MKT_EXT=1`, K24+skipFull, `LIVE_RANK_TIEBREAK=symbol`, …).
- **Đối chứng (backtest A1):** cấu hình sim của `docs/result/GOLIVE_QUARTERLY_2026_A1.md` (`428ad486`) = luật/tham số gói X14
  không đổi, universe **A1 = A0 − TradFi − INDEX** (prereg `PREREG_HO2026_NOTF.md`). Trên dữ liệu cửa sổ, "backtest A1" =
  thước OFF-BT (§1) chạy với bộ lọc A1 ở **mọi tầng** như sim A1.
- **Ràng buộc:** như v1.1 — không đọc Aerospike 242, chỉ đọc file 242 qua `ssh … cat|zcat|tar cf -` về Oracle, không ghi
  file lên 242, không Binance REST, chỉ file tĩnh `data.binance.vision` (+ file exchangeInfo dry đọc từ 242).

## 1. Thước (đổi so với v1.1)

| ký hiệu | đổi gì |
|---|---|
| **OFF-BT-A1** | harness `V11FeatHarness` mode `BT` dựng từ **class của đúng jar dry đang chạy** (không phải jar v1.1 `eea5adec`), bật `UNIVERSE_A1=1` với `UNIVERSE_A1_EXCHANGE_INFO` = bản exchangeInfo PIT của ngày D (§2.2); đi qua `ExportGateDataset.replayToCsv` với `UniverseA1Filter.filterMinutes` + `MarketDataInlineGenerator` A1 (code r4d) |
| **OFF-NEW2-A1** | cùng harness mode `NEW2` (gọi `LiveFeaturePipeline` của jar dry, có `UniverseA1Filter.filter`) — CTL: OFF-NEW2-A1 ≡ OFF-BT-A1 100 % |
| **LIVE** | như v1.1 (`feat_dump`, `sel_dump`, `s1_dump`, `predictionSymbol`, `run/gate_ratio_live.bin`, `full.log`) **+** sổ dry c3: `run/c3live_book.json`, ledger `run/` (`LiveBookC3.LEDGER_NAME`), journal lệnh, log `[UNIVERSE-A1]`, `[C3-LIVE*]`, `run/c3live_exinfo_refresh.state`, `logs/exinfo_refresh.log` |

## 2. Universe (phần phải đổi vì A1)

1. **Tầng lọc (khai từ code r4d–r4f):** A1 áp ở MarketBigChangeDetector (breadth/MD), LiveFeaturePipeline (snapshot
   feature/basket), AltEwIndex + TsMktExt (`run/ts_ext_daily.csv.a1`), S1/ứng viên, gate; R7 thực thi đọc **cùng file**
   exchangeInfo. **R4 (§6) phải kiểm lại bản đồ tầng này trên jar thật** trước khi chấm; tầng nào live lọc mà sim A1 không lọc
   (hoặc ngược lại) ⇒ DỪNG, ADDENDUM trước khi chấm.
2. **U_D^A1 (offline):** = U_D của v1.1 §2.2 (tập symbol store 242 suy từ dump/log, bỏ symbol Vision 404) ∩ A1 PIT:
   symbol bị loại tại phút M khi `contractType` chứa TRADIFI hoặc `underlyingType = INDEX` **và** `M ≥ onboardDate` (đúng
   `UniverseA1Filter` PIT). Nguồn phân loại = chính file `run/c3live_exchangeInfo.json` của dry (bản `.lastgood` gần nhất
   có `serverTime ≤ D 23:59 UTC`, kéo về Oracle hằng ngày, lưu sha256). Không có bản nào của ngày D ⇒ phần phụ thuộc
   universe của ngày D = KHÔNG ĐO ĐƯỢC.
3. **Kiểm chéo sim A1 (R6, §6):** tập A1 theo bộ phân loại live vs tập A1 theo bộ phân loại sim (HO2026_NOTF) trên cùng
   exchangeInfo: liệt kê chênh lệch; chênh không giải thích được bằng PIT/niêm yết ⇒ DỪNG, ADDENDUM.
4. **K3′ (giữ luật ADD1, đổi tập):** S_M = symbol **A1** có mốc niêm yết/huỷ trong [M−1440′, M]; symbol TradFi/INDEX
   không bao giờ vào S_M (đã bị loại khỏi mọi phép tính).
5. **K7 (mới, đếm như K3′, chứng minh bằng drop):** lệch do **độ trễ làm mới exchangeInfo**: symbol A1 niêm yết tại t_L mà
   file exchangeInfo live tại M có `serverTime < t_L` (cron 15′, URGENT > 45′). Chỉ gán K7 khi phép drop các symbol đó
   làm lệch biến mất (dung sai §4 v1.1). Không chứng minh ⇒ K5.
6. **S1-I:** tập loại = **coin c3 dry đang giữ** (từ `c3live_book.json`/journal theo phút); LEGACY = ∅ (dry không có LEGACY
   — kiểm từ log `[LEGACY]` (nếu có) và sổ dry: không symbol LEGACY nào; khác ∅ ⇒ DỪNG, điều tra trước khi chấm).
7. **TSX:** cờ live (`[TS-EXT]` trên `ts_ext_daily.csv.a1`) vs cờ Vision tính trên U^A1 cùng luật `AltEwIndex`.

## 3. Chỉ số, ngưỡng, verdict ngày — GIỮ NHƯ v1.1

P1-F, P1, P1-m, MD, FUND, NET, S1-I, S1-m, S1-V, GV-I, GV-O, P2, P3, TSX, CTL: định nghĩa/ngưỡng/lượt D–M y nguyên v1.1 §4
(và ADD1 §2 báo cáo tích luỹ r/q ≥ 0,9 / ≥ 0,8), chỉ thay universe theo §2. Verdict ngày: **ĐẠT** (mọi ngưỡng đạt, K5 = 0),
**XÁM** (đạt ngưỡng, K5 > 0 ⇒ điều tra trước lượt kế, không đổi ngưỡng), **TRƯỢT** (không đạt ngưỡng). Phút K1″–K7 vẫn tính
vào ngưỡng (nhãn chỉ để giải thích). Guard D9 giữ: ngày pull INCOMPLETE tối đa XÁM, không bao giờ ĐẠT.

**Thêm (chỉ báo cáo, không ngưỡng):**
- **T-DEC:** mọi cặp (phút, symbol) gate PASS live = tập PASS offline? (= P2 nhìn theo tập; lật nặng đã do P2 chấm.)
- **T-BOOK:** mỗi lệnh vào dry (journal) có PASS tương ứng ở offline cùng phút (được phép chậm 1′ do thực thi); size theo
  `C3_CAPITAL=10000` và equity c3 dry; lệnh đóng dry: lý do (TRAILING/TIME_STOP/X14) + giá so close 1m Vision.
- **KPI dry** (PnL c3, maxDD, số đợt/cụm/leg, win %, U, phơi nhiễm) đặt cạnh dải 8 seed của GOLIVE_QUARTERLY_2026_A1 (quy
  về số ngày) — **mô tả, không phán quyết** (7–14 ngày quá ngắn).

## 4. Dry KHÔNG có LEGACY ⇒ KPI LẠC QUAN (khai rõ, không được dùng KPI dry làm bằng chứng hiệu quả live)

Dry trên 242 khởi động **phẳng, sổ c3 mới, không LEGACY, `LIVE_ADAPTER=dry`** ⇒ so với live tài khoản chính: (a) không có
44 vị thế LEGACY tranh slot/symbol (`skip-LEGACY`, MERGED, LOST_FOREIGN, chặn symbol 24 h không bao giờ xảy ra); (b) khớp
giả lập (không trượt giá, không hàng đợi, không độ trễ ACK/stream thật, không lỗi −2019/418/429 từ lệnh thật); (c) phí/funding
theo mô hình dry; (d) không có rủi ro ký quỹ Multi-Assets. Mọi KPI dry ghi kèm nhãn "LẠC QUAN (dry, không LEGACY)". Parity
tín hiệu (§3) **không** bị ảnh hưởng bởi (a)–(d) ngoại trừ S1-I (tập loại khác live thật) — ghi rõ.

## 5. Cửa sổ, "ngày sạch", ngày restart / thiếu dữ liệu

- **Mở cửa sổ:** nến quyết định đầu tiên sau khi deploy dry hoàn tất (dòng `MainClass` đầu tiên của log sau deploy, xác
  nhận bằng log deploy `deploy_v12_dry_r4.sh` kết thúc mã 0; hậu kiểm 120 s 0 LATCH). Cửa sổ v1.1 kết thúc tại thời điểm deploy này.
- **Độ dài:** tối thiểu **7 ngày UTC sạch** (không bắt buộc liên tiếp), tính từ ngày UTC đầy đủ đầu tiên sau mở cửa sổ.
- **Ngày sạch** = đủ MỌI điều kiện (kiểm cơ học từ file đã kéo về, ghi bảng trong D<n>):
  1. pull242 `COMPLETE` + `STATUS=OK`; `feat_dump` ≥ 1440 − (phút warm-up đã liệt kê) dòng BTCUSDT; `sel_dump`/`s1_dump`
     đủ 24 giờ; Vision ≥ 99 % U_D^A1;
  2. **0 restart JVM `v_t_m`** trong ngày (đếm dòng `MainClass` / PID đổi) — r4g tắt reset 12h nên mọi restart là sự kiện
     phải có nguyên nhân; ngày có restart = KHÔNG SẠCH (vẫn chấm các phút đo được, ghi verdict, nhưng không tính vào 7);
  3. **ngân sách / bộ đếm:** `LIVE_FEAT_DUMP` không chạm "DU TICK"/"CHAM TRAN" trong ngày (bài học 10-25: env 3000 ⇒ dump tự
     tắt 50 h sau restart); jar ≥ r4g: ngân sách tính theo ngày UTC (log `[LIVE_FEAT_DUMP] … Ngan sach theo ngay UTC=true`); jar r4f: ngân sách TỔNG từ lúc
     khởi động ⇒ env `LIVE_FEAT_DUMP` phải ≥ số phút cửa sổ + dự phòng (242 hiện 200 000 ≈ 138 ngày); mọi cờ ngân sách khác của shadow
     liệt kê ở D1 với giá trị env và thời điểm cạn dự kiến > hết cửa sổ;
  4. **mapper:** 0 dòng `[MAPPER]` id CỤC BỘ / `UNKNOWN-` / `[MAPPER-REFRESH]` lệch trong log trading; `[MAPPER-DUP]` chỉ
     được phép với tập id trùng đã biết `{1=[BTCUSDT, XUSDT]}` (khác tập này ⇒ không sạch); (bài học 10-27: restart lộ id
     trùng ⇒ AI init FAIL, entry bị chặn);
  5. **ingestor:** 0 `[OI-GUARD]` chặn, 0 `KLINE_STALE`, 0 `[FEAT-PIPE]` gap/no_snap/partial; collectData tự restart
     ("Too many symbol price errors") ≤ 2 lần trong ngày (10-30 có 15 lần ⇒ ngày như vậy KHÔNG sạch);
  6. **exchangeInfo:** `c3live_exinfo_refresh.state` `fails=0` cuối ngày, tuổi file ≤ 45′ ở mọi lần `[UNIVERSE-A1]` reload,
     0 `STALE` ngừng mua;
  7. 0 kill-switch LATCH (C1–C6/A40) — LATCH ⇒ không sạch (dù ở dry).
- **Phút loại khỏi chấm** (liệt kê, như v1.1): phút không có dòng feat_dump; warm-up sau restart (từ `MainClass` tới tick
  `[FEAT-PIPE]` đầu tiên có feature); phút trong khoảng dump tắt. **Không loại phút nào khác** để cứu ngưỡng.
- **Ngày thiếu dữ liệu** (pull INCOMPLETE, file 242 mất, Vision trễ): phần không đo được = KHÔNG ĐO ĐƯỢC (không bao giờ là
  ĐẠT), chấm gộp khi có; nếu 242 đã xoay/mất file ⇒ ngày đó vĩnh viễn KHÔNG ĐO ĐƯỢC, không tính sạch.
- **Kết luận cửa sổ:** **ĐẠT** = ≥ 7 ngày sạch, mỗi ngày sạch ĐẠT hoặc XÁM-đã-đóng (K5 đã điều tra, có nguyên nhân ghi sổ
  trước khi chấm ngày kế), **0 TRƯỢT** ở mọi ngày đo được (kể cả ngày không sạch). **TRƯỢT** ở bất kỳ ngày nào ⇒ cửa sổ
  TRƯỢT; sau khi sửa (ADDENDUM + jar mới nếu đổi code) mở cửa sổ mới, đếm lại từ 0. Ngày không sạch không làm cửa sổ TRƯỢT
  nhưng sự cố phải có nguyên nhân gốc trước khi kết luận ĐẠT.

## 6. Tái kiểm harness TRƯỚC khi chấm (thêm vào R0–R3 của v1.1, chạy lại R0–R3 trên jar dry)

- **R4 (bản đồ tầng A1):** đọc code jar dry + log 1 giờ live: liệt kê mọi tầng gọi `UniverseA1Filter` (§2.1); OFF-BT-A1 phải
  lọc đúng các tầng đó; so với sim A1 (Kaggle `nt-x14-*` A1) tầng nào lệch ⇒ DỪNG.
- **R5 (ngày sập tham chiếu 10-30):** chạy OFF-BT-A1 và OFF-NEW2-A1 trên Vision 2026-10-30 (khi đã phát hành): CTL phải 100 %
  (ALL33 + p15 + basket + Tool1 #1–40) và cờ TSX khớp `AltEwIndex` A1; ghi số phút gate PASS offline A1 của 10-30 làm tham
  chiếu (không so với shadow v1.1 vì v1.1 có TradFi — chỉ báo kèm).
- **R6 (universe sim ↔ live):** §2.3.

## 7. Ngày sập = phép thử trọng điểm

- **Định nghĩa cơ học (Vision 1m, tính trước khi xem kết quả parity của ngày):** ngày UTC D là **ngày sập** nếu tồn tại
  khung 60′ trong D có `ret(BTCUSDT) ≤ −2,5 %` **hoặc** median `ret` 60′ của 50 symbol U^A1 có quoteVolume lớn nhất ngày D−1
  `≤ −5 %`. (Tham chiếu: 10-30 hai đợt 03:30–04:00 BTC −2,68 %, median alt −6,64 %; 06:00–09:10 BTC −3,21 %.)
- **Yêu cầu riêng cho ngày sập** (ngoài §3): báo cáo đầy đủ P2 theo từng phút trong [đáy − 60′, đáy + 120′] (pass live/
  offline, r/q, thr, q_t trước/sau burst — 10-30 q_t tăng +31 % sau burst lúc 05:01); T-DEC và T-BOOK liệt kê từng lệnh;
  `[GATE-RATIO]` mọi giờ. Ngày sập TRƯỢT ⇒ cửa sổ TRƯỢT (như §5). Ngày sập không sạch vì collectData restart dồn dập
  (như 10-30) ⇒ vẫn chấm đủ, ghi rõ; không tính vào 7 ngày sạch.
- **Cửa sổ không có ngày sập:** kết luận ĐẠT kèm nhãn **"CHƯA THỬ SẬP"**; MASTER quyết kéo dài hoặc chấp nhận (ghi
  ADDENDUM). Không thay ngày sập bằng replay offline (R5 chỉ là kiểm harness).

## 8. Lưu trữ, đầu ra

- Kéo về Oracle hằng ngày (chỉ đọc 242) như v1.1 §7 **+** `run/c3live_book.json`, ledger, journal lệnh dry, các bản
  `run/c3live_exchangeInfo.json(.lastgood)` (sha256 theo giờ), `logs/exinfo_refresh.log`, `run/c3live_exinfo_refresh.state`,
  log collectData (đếm restart, `[MAPPER*]`).
- `docs/result/PARITY_V12_DRY_D<n>.md` + JSON mỗi lượt; script `research/parity_v12/` (tách khỏi `parity_v11/`, dùng lại hàm,
  không sửa script v1.1 đang chấm cửa sổ cũ). D1 ghi: md5 jar, env dry thực tế (không in secret), bảng ngân sách, R4–R6.
- Văn bản này **không** chạy đo nào. Không đọc số của cửa sổ dry trước khi commit.
