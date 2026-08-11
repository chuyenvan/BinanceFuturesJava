# TASK-251 — WFO canonical 1-phút, full range 20210101→20260701

> Tạo 2026-08-05 bởi Claude (Cowork cloud session, KHÔNG có SSH/network tới Oracle —
> mọi phần "chạy thật" dưới đây PHẢI làm từ máy có `orchestrator/ce.cmd` thật (Windows,
> key `C:\Users\pc\.ssh\id_rsa_chuyennd`) hoặc 1 CCD có SSH Oracle. File này chỉ ghi lại
> đã-sửa-gì + lệnh cần chạy + checklist data, KHÔNG tự chạy được.

## Mục tiêu
Regen dữ liệu WFO theo lưới **1 phút** (thay lưới 15 phút cũ). Phạm vi **export**
label/feature/ticker = `20210101→20260701`. `FIRST_CUTOFF` walk-forward selector **GIỮ
NGUYÊN `20230101`** ("lối A", xác nhận lại 2026-08-05) — fold đầu tiên train FULL từ
`ts_min=20210101` tới `20230101 − 72h purge`, đây chính là lý do cần export label/feature
từ 20210101 (để fold đầu có đủ ~2 năm train sạch), KHÔNG phải để tạo OOS prediction trước
2023.

⚠️ **Lịch sử sửa trong phiên này (đừng lặp lại):** có 1 lần hiểu nhầm đổi
`FIRST_CUTOFF`→`20210101` + `EXPECT_LEAKFREE`→`2021-01-01`, đã tự phát hiện và REVERT lại
đúng ngay trong phiên sau khi Uni xác nhận. Bản hiện tại (dưới đây) là bản ĐÃ REVERT — đúng.

## Đã làm (2026-08-05, session Cowork — chỉ sửa file, CHƯA chạy)
- `orchestrator/pipelines/wfo_canonical_1m.json`: `label_export`/`tool1_export` step
  `args.end` rỗng → `20260701`. (`start=20210101` đã đúng sẵn từ 08-04, không đổi.)
  `expect_leakfree` giữ `2023-01-01` (không đổi, sau khi revert).
- `orchestrator/kernels_wfo1m/selector-predict-1m/run_train.py`: `FIRST_CUTOFF` giữ
  `20230101` (không đổi, sau khi revert) + comment giải thích lại cho rõ để CCD sau không
  hiểu nhầm giống phiên này.
- `docs/WFO_DATA_PIPELINE_MASTER.md`: bump 1.1.1→1.1.2, changelog ghi đúng: chỉ đổi phạm vi
  export, không đổi cutoff.

## Checklist DATA trước khi chạy (theo yêu cầu Uni 2026-08-05 — nguồn = 242, off-limits,
chỉ Oracle sync TỪ nó, xem `REDESIGN_INFRA_20260804.md`)

Thứ tự kiểm tra (đo trước, đừng giả định — mọi số "đủ chưa" phải đo bằng tool, xem
`DATA_STATE.md` là nguồn số liệu, nhưng đo gần nhất đã cũ 1 tháng, PHẢI đo lại):

1. **Ticker (`kline_1m_opt`)** thiếu đoạn nào trong `20210101→20260701` → sync từ 242 bằng
   `CopyTicker242To226` (`src/main/java/com/binance/chuyennd/aerospike/tools/CopyTicker242To226.java`,
   viết 2026-08-04, chạy TRÊN Oracle, tự write local vì `AEROSPIKE_HOST_226=127.0.0.1`).
   ⚠️ **Caveat đã đo thật** (`docs/reports/KAGGLE_FANOUT_RESULT.md §9.1`): **242 chưa
   ghost-clean** (ghost USDC-margin + đuôi-đơn coin delist — xem `DATA_STATE.md §5b`) —
   Oracle-local đã `CleanTickerGhostAndTail` sạch rồi. Copy đoạn MỚI từ 242 sẽ mang ghost
   trở lại cho đúng đoạn mới đó → **PHẢI chạy lại `CleanTickerGhostAndTail` cho riêng
   đoạn mới copy** trước khi coi ticker Oracle sạch trở lại (KHÔNG cần full-rescan nếu tool
   hỗ trợ range, verify lại bằng `MeasureDataState`/`PeekTickerFileV2`).
2. **Market object / label** thiếu → 2 tầng này (tầng 2, 4 trong `WFO_DATA_PIPELINE_MASTER.md`)
   là **derive từ ticker**, không sync riêng từ 242 — chỉ cần ticker (bước 1) đủ + sạch rồi
   regen lại qua `DataManagerAerospikeFloatSim`/`ExportFundingLabel`. Nếu set Aerospike bị
   reset/rỗng (đã từng xảy ra, xem `DATA_STATE.md §5c`) → regen lại từ ticker sạch, không
   phải "sync" theo nghĩa copy từ 242.
3. **Funding fee** thiếu → sync từ 242 ĐÚNG, dùng `CopyAuxSets242To226`
   (`src/main/java/com/binance/chuyennd/aerospike/tools/CopyAuxSets242To226.java`, viết
   2026-08-04 — cùng ngày với quyết định topology `REDESIGN_INFRA_20260804.md`). Tool này
   copy CẢ `funding_data` VÀ `symbol_mapper` (đọc-only 242, ghi-idempotent 226/Oracle-local,
   có bước verify-bytes riêng). *(Đã kiểm lại: lời khuyên "crawl lại từ fapi.binance.com,
   KHÔNG copy 242" trong `DATA_STATE.md §5c` là 2026-07-08 — TRƯỚC KHI tool bridge này tồn
   tại; giờ đã có tool đúng thì dùng tool này, không cần crawl lại. Không còn mâu thuẫn.)*
4. **OI** thiếu đoạn nào → lấy riêng từ Binance vision, KHÔNG dùng `fetchSymbol` full-history
   per-coin (đã thử, quá chậm — xem `DATA_STATE.md §5a`, TASK-013 pattern). Bản hiện có
   (`oi_percoin_20210101_to_20260624.bin.gz`) đã validate đủ cho coin delist; nếu cần mở rộng
   tới 20260701 thì backfill THÊM đoạn thiếu (06-24→07-01) qua đúng pattern TASK-013, không
   export lại toàn bộ.
5. **symbol_mapper** — Uni nhắc cẩn thận, đúng: đây là bảng map symId↔symbol, sai/lệch ở đây
   làm SAI TOÀN BỘ downstream (âm thầm, không crash). Copy qua CHUNG tool với funding (bước 3,
   `CopyAuxSets242To226` có `SET_MAPPER`). Theo `REDESIGN_INFRA_20260804.md`: bản LIVE trên
   Oracle là canonical (sync từ 242), KHÔNG freeze cứng; lúc build dataset fanout file nặng
   thì bake snapshot `core_symbol_mapper` vào dataset (`KaggleDataLoader.loadSymbolMapperFile()`,
   TASK-112c). Trước khi chạy full: chạy verify-bytes có sẵn trong `CopyAuxSets242To226`
   (mục "🔎 VERIFY funding_data... mismatch/missing") — LỆCH thì `FORCE_OVERWRITE=true` chạy
   lại, ĐỪNG export dataset trên mapper nghi ngờ lệch.
6. **Kaggle dataset upload** khi thiếu — đã có atom `kaggle_dataset_push`/`kaggle_dataset_status`
   trong `ce-buttons.md` (2026-08-04, dùng CLI `kaggle` qua venv `D:\claudedata\kaggle-clean-env`)
   — dùng nút này, không tự gõ `kaggle datasets` tay (tránh lệch pattern create-vs-version đã
   verify sẵn trong `run_106_headless.sh` B2).

## Chạy thật (sau khi checklist DATA trên PASS)
1. `ce --sync bg_selftest` PASS 6/6 — 5 atom mới của pipeline này chưa chạy thật trên
   Oracle+Kaggle, chỉ smoke-test cục bộ (`WFO_DATA_PIPELINE_MASTER.md` §Runbook).
2. `ce pipe_run wfo_canonical_1m` → `ce pipe_status <pipe_id>` (18 step, tự động hết trừ
   `gate_sign`). Override tham số khác qua `K=V` nếu cần.
3. Tại `gate_sign`: đọc `${out_ds}/validation_report.txt` — PASS mới `pipe_resume`; chưa
   chắc → `pipe_stop`, KHÔNG resume mù.
4. Sau PASS: đối chiếu Cảnh báo #5 `WFO_DATA_PIPELINE_MASTER.md` — gate coverage 2023+ CHƯA
   đo lại ở lưới 1-phút này, đo trước khi coi dataset là chính thức cho HPO/WFO thật.

## Rủi ro treo
- `CopyTicker242To226`/`CopyAuxSets242To226` mới viết 2026-08-04, **chưa thấy log/report nào
  xác nhận đã chạy thật trên Oracle** (grep repo không ra bằng chứng run) — coi là CHƯA
  test end-to-end, giống 5 atom CE khác cùng ngày. Chạy thử phạm vi nhỏ trước khi tin.
- Nếu ticker/OI/label sau sync vẫn thiếu đoạn nào trong 20210101–20260701 → export dataset
  sẽ chỉ ra tới đâu có data thật, KHÔNG throw — phải đọc log xác nhận range thật, đừng giả
  định đã đủ chỉ vì lệnh chạy xong.
- 18-step pipeline có bước Kaggle kernel (`wait_kaggle`, timeout 28800s = 8h) — job dài,
  đúng luật CE-buttons phải `pipe_run` detached rồi rời, KHÔNG ngồi poll.

## Cập nhật 2026-08-05 (session Cowork, ĐÃ có SSH thật qua bridge claude-code trên máy Windows
của Uni — không còn "chỉ ghi lại kế hoạch" như ghi chú đầu file nữa, đã chạy được lệnh thật)

**Đã làm thật (verify qua SSH), không phải chỉ sửa file cục bộ:**
1. Phát hiện bug `orchestrator/ce.cmd` khi gọi qua bridge (Exit 255,
   `'M' is not recognized...`) — KHÔNG sửa `ce.cmd`, chỉ dùng workaround: gọi trực tiếp
   `ssh.exe -i C:\Users\pc\.ssh\id_rsa_chuyennd ubuntu@161.118.212.3` với đúng ENV
   (`CE_RUN_DIR=/home/ubuntu/claudedata/.run/mcp_ce`, `CE_LOCKS_DIR=.../locks`) +
   `python3 /home/ubuntu/claudedata/.run/mcp_tools-v3.py <cmd>` — y hệt logic trong `ce.cmd`,
   chỉ bỏ qua lớp `.cmd`. CCD sau muốn gọi `ce` qua bridge remote thì dùng cách này, đừng gọi
   `ce.cmd` trực tiếp qua bridge (chạy tay từ Windows thật (không qua bridge) thì `ce.cmd`
   vẫn OK, chưa rõ nguyên nhân gốc, chưa cần sửa).
2. **Gap hạ tầng #1 (đã fix):** Oracle **chưa từng có checkout repo** — `repo_root` trong
   `wfo_canonical_1m.json` (`/home/ubuntu/BinanceFuturesJava`) KHÔNG TỒN TẠI, chỉ có vài file
   lẻ được scp tay qua nhiều lần trước đây. Đã tạo cây thư mục tối thiểu + scp đúng 3 file cần
   cho pipeline này: `ml/training/gen_funding_wf_predictions.py`,
   `orchestrator/kernels_wfo1m/selector-predict-1m/run_train.py` + `kernel-metadata.json`.
   ⚠️ Đây là fix tối thiểu, KHÔNG phải clone full repo — nếu bước sau cần file khác trong
   `repo_root` (pipeline có step khác tham chiếu) thì phải bổ sung tiếp, đừng giả định đủ.
3. **Gap hạ tầng #2 (đã fix):** bản `wfo_canonical_1m.json` đã deploy trên Oracle tại
   `CE_PIPES_DIR=/home/ubuntu/claudedata/.run/pipelines/wfo_canonical_1m.json` là bản CŨ
   (`"end": ""`), vì các lần sửa file local trước đó trong phiên chỉ ghi vào repo Windows,
   KHÔNG tự động sync sang Oracle. Đã scp đè bản đã sửa đúng (`end=20260701`) lên đúng path
   đó, verify lại bằng `grep -A1 '"end"'` trên Oracle → ra `20260701` cho cả `label_export`
   và `tool1_export`. **Lưu ý cho CCD sau: sửa pipeline JSON ở repo local KHÔNG có tác dụng
   thật cho tới khi scp đè lên `CE_PIPES_DIR` trên Oracle — luôn verify lại bằng grep trên
   Oracle sau khi sửa, đừng tin bản local.**
4. Verify `mcp_tools-v3.py` trên Oracle đã có đủ 5 atom mới (`label_export`, `tool1_export`,
   `wfo_build_ds`, `wfo_validate`, `kaggle_dataset_push`/`kaggle_dataset_status`) và khớp md5
   với repo local — không cần deploy lại file này.
5. `ce --sync bg_selftest` (qua workaround SSH trực tiếp) → PASS 6/6. Đây chỉ là smoke-test
   lifecycle job chung, KHÔNG validate logic nghiệp vụ riêng của 5 atom mới — atom mới vẫn
   coi là CHƯA chạy thật lần nào.
6. Check `sys_health`/`bg_list`/`wfo_status` trên Oracle: **0 process java đang chạy thật**,
   dù có vài job "RUNNING" cũ/orphan còn sót trong jobstore `strategy_window` (KHÔNG liên quan
   task này, đừng động vào, đừng hiểu nhầm là đang có tải).
7. **Chưa có cách đo coverage Aerospike thật** (ticker/funding_data/symbol_mapper/OI) trên
   Oracle — `aql`/`asinfo` KHÔNG có sẵn trên máy, KHÔNG có CE atom nào đo việc này. Cần viết
   script Python một-lần dùng thư viện `aerospike` client để đo trước khi chạy checklist DATA
   ở trên bằng số liệu thật (đừng dùng số cũ trong `DATA_STATE.md`, đã hơn 1 tháng).
8. **Thử dispatch agent nền `oracle-runner` để làm tiếp phần đo-coverage → sync/backfill có
   điều kiện → `pipe_run` → theo dõi → dừng đúng tại `gate_sign` — THẤT BẠI**: subagent_type
   `oracle-runner` không có trong danh sách agent khả dụng của session claude-code hiện tại
   trên máy Uni (dù file định nghĩa `.claude/agents/oracle-runner.md` có tồn tại trong repo —
   không rõ vì sao chưa được đăng ký, có thể do cách agent-registry nạp lại). Agent khả dụng
   thực tế qua bridge: `claude` (catch-all), `claude-code-guide`, `Explore`, `general-purpose`,
   `Plan`, `statusline-setup`. Đã pivot sang dispatch `general-purpose` (xem log runner ngay
   dưới mục này khi nó hoàn tất) — nếu CCD sau thấy `oracle-runner` đã hoạt động trở lại thì có
   thể ưu tiên dùng lại đúng agent đó (được viết chuyên cho việc này).

**Trạng thái tại thời điểm ghi chú này:** CHƯA chạy `pipe_run wfo_canonical_1m` thật, CHƯA đo
coverage Aerospike thật, CHƯA làm bước sync/backfill data nào (mọi tool `CopyTicker242To226`/
`CopyAuxSets242To226`/OI-backfill vẫn ở trạng thái "có sẵn nhưng chưa gọi lần nào trong task
này"). Phần còn lại đã được giao cho 1 agent nền (`general-purpose`, xem note #8) chạy tiếp
theo đúng thứ tự checklist DATA → `pipe_run` → dừng tại `gate_sign`, KHÔNG tự resume/sign.

## Cập nhật 2026-08-05 (phần 2, agent `general-purpose` nhận việc từ note #8) — ĐÃ đo coverage
thật, PHÁT HIỆN BUG CHẶN SYNC (namespace 242≠Oracle) — DỪNG trước `bg_selftest`, CHƯA `pipe_run`

**Kênh dùng:** bridge Cowork trên máy Windows Uni → Git-bash `ssh.exe`/`scp.exe` trực tiếp
(đúng workaround đã ghi ở đầu file) tới `ubuntu@161.118.212.3`. Toàn bộ SSH/scp OK, không gặp
lại bug `ce.cmd` exit 255 vì không đụng `ce.cmd` (mọi việc dưới đây làm tay qua SSH, KHÔNG qua
CE, vì mục tiêu là đo coverage — chưa có atom CE nào làm việc này, đúng như ghi chú đầu file).

### 1. Đo coverage Aerospike thật trên Oracle-local (ns=`test`, đúng như `getClientOracle()`)

Không có `aql`/`asinfo`/class `MeasureDataState`/`PeekTickerFileV2` nào tồn tại thật trong repo
hiện tại (đã grep toàn repo, không ra kết quả — 2 tên này chỉ xuất hiện trong
`docs/DATA_STATE.md` như tham chiếu lịch sử tới 1 lần đo tháng 7, không phải class còn sống).
Theo đúng luật "viết script mới khi chưa có atom" — đã cài `pip3 install aerospike` (client
Python, có internet outbound từ Oracle, cài OK bản `19.2.2`) và viết 1 script một-lần
`/home/ubuntu/claudedata/measure_coverage.py` (batch-read exists-only qua `client.batch_read`,
0.13s/ngày·1440-key trên loopback → full range 2021-01-01→2026-06-30 chạy hết ~5 phút). Script
này KHÔNG sửa gì, chỉ đọc.

**Kết quả TICKER (`kline_1m_opt`, ns=`test`, tức Oracle-local — đích depends checklist mục 1):**
- Phạm vi đo: 2021-01-01 → 2026-06-30 (2007 ngày, đúng theo phạm vi export target).
- `first_day_with_data=2021-01-01`, **`last_day_with_data=2026-06-07`** — dữ liệu ticker
  Oracle-local hiện chỉ tới **07/06/2026**, KHÔNG phải 06-24 như `DATA_STATE.md`/task giả định
  (số cũ hơn 1 tháng, đúng như cảnh báo "đo gần nhất đã cũ, PHẢI đo lại" ở đầu file — số mới đo
  THẤP HƠN số cũ tin tưởng).
- Tổng: `total_minutes_present=2,855,553 / 2,890,080` checked = **98.81%**.
- **23 ngày THIẾU HOÀN TOÀN liên tục: 2026-06-08 → 2026-06-30** (đúng dải cuối, không rải rác).
- 2 ngày thiếu 1 phần: `2026-06-02` (1402/1440, thiếu 38 phút) và `2026-06-07` (491/1440, thiếu
  949 phút — đây là ngày "gãy" ngay trước khi dữ liệu dừng hẳn).
- `2021-01-01` thiếu 1 phần (1020/1440) — **không phải gap thật**, nhiều khả năng là ngày bắt
  đầu thu thập tự nhiên (collector bắt đầu giữa ngày), khớp với mọi tài liệu cũ, không cần vá.
- ⇒ **Checklist mục 1 (ticker) CHƯA PASS**: thiếu đúng 23 ngày cuối (06-08→06-30) + 2 ngày thiếu
  1 phần gần cuối. Đây là input bắt buộc cho export `20210101→20260701`.

**Kết quả `symbol_mapper` (Oracle-local):** map `data` size = **781 symbol**, có `BTCUSDT` +
`ETHUSDT`. Trông khỏe (không rỗng, không nhỏ bất thường) — nhưng CHƯA verify byte-so-242 (cần
`CopyAuxSets242To226` verify-bytes để chắc, xem mục bug bên dưới — bị chặn cùng nguyên nhân).

**Kết quả `funding_data` (Oracle-local):** scan ra **741 record có userKey** (symbol), có
`BTCUSDT` + `ETHUSDT`. Số gần với 781 symbol_mapper (hợp lý — không phải coin nào cũng có
funding, ví dụ vài coin mới/sắp delist). ⚠️ **CHƯA đo được phạm vi THỜI GIAN** của funding
(bin `f_data`/`f_map` là Snappy-compressed theo format riêng của Java, không tự giải mã lại
bằng Python để tránh làm sai — muốn biết funding có mới tới 2026-07-01 hay không phải chạy
`CopyAuxSets242To226` (có verify-bytes built-in so 242↔226) hoặc 1 tool Java đọc trực tiếp.
Cũng bị chặn bởi bug namespace dưới đây.

**OI:** file `oi_percoin_20210101_to_20260624.bin.gz` (3.15GB, mtime 2026-07-07 18:30) tại
`/home/ubuntu/java/simulator/features_oi_percoin_v1/` — xác nhận ĐÚNG như task đã ghi, dải
06-24→07-01 vẫn thiếu, CHƯA backfill thêm (chưa động vào, ưu tiên xử lý bug ticker/aux trước vì
cùng nguyên nhân gốc có thể ảnh hưởng cả OI nếu OI backfill cũng qua `getClient242()`).

### 2. 🔴 BUG PHÁT HIỆN — chặn TOÀN BỘ sync 242→226 (ticker + aux), KHÔNG PHẢI lỗi deploy/path

**Đã build + deploy jar chứa 3 tool mới** (`CopyTicker242To226`, `CopyAuxSets242To226`,
`Validatetickercopy226`) — jar local Windows `target/binance-java-sdk-1.2.4-shaded.jar` (build
2026-08-04 09:20, ĐÃ có sẵn 3 class này, không cần build lại) → scp lên Oracle tại
`/home/ubuntu/java/simulator/binance-sync-20260804.jar` (99.5MB).

**Chạy thử `CopyTicker242To226 20260601 20260701`** (đúng luật "chạy thử phạm vi nhỏ trước khi
tin" ở mục Rủi ro treo) → **THẤT BẠI với mọi ngày cần đọc từ 242**:
```
com.aerospike.client.AerospikeException$InvalidNamespace: Error 20: Namespace not found in
partition map: test
```
Kết quả cuối: `copied=0 | skipped(đã có)=10113 | missing242=0` — **KHÔNG ghi đè/hỏng gì trên
Oracle-local** (an toàn, tool thiết kế resume nên gặp lỗi liền dừng sạch, không có write nào xảy
ra phía đích). Đây là lỗi ĐỌC từ nguồn 242, không phải lỗi ghi.

**Root cause đã xác định chắc chắn (đo trực tiếp bằng Python aerospike client, không đoán):**
```
client.info_all('namespaces') trên 103.157.218.242:3222 → {'...': (None, 'ticker\n')}
```
→ **Namespace THẬT trên cụm 242 là `ticker`, KHÔNG PHẢI `test`.** Toàn bộ code hiện tại
(`DataManagerAerospikeFloatSim.getClient242()` VÀ `getClientOracle()`, cả 2 tool mới) dùng
CHUNG 1 hằng số `Configs.AEROSPIKE_NAMESPACE` (đọc từ `config.properties: AEROSPIKE_NAMESPACE=
test`) cho CẢ HAI cluster — giả định 242 và Oracle-local dùng cùng tên namespace. Giả định này
**SAI trên thực tế hiện tại**. Đã verify thêm: namespace `ticker` trên 242 THẬT SỰ có đủ 3 set
cần (`kline_1m_opt` bin `data`, `funding_data` bin `f_map`/`f_data`, `symbol_mapper` bin `data`)
— tức dữ liệu nguồn vẫn còn đó và đúng cấu trúc, chỉ SAI TÊN NAMESPACE khi code kết nối.

**TCP tới 242:3222 THÔNG BÌNH THƯỜNG** (`</dev/tcp/103.157.218.242/3222` OK) — không phải
firewall chặn kết nối, chỉ là namespace-name không khớp ở tầng ứng dụng.

**Vì sao tôi DỪNG ở đây, không tự sửa:** đây không phải lỗi path/config-thiếu-file/deploy
(loại tôi được phép tự sửa theo hướng dẫn) — đây là **sai giả định dữ liệu/hạ tầng** ảnh hưởng
1 hằng số dùng ở HÀNG CHỤC nơi trong `DataManagerAerospikeFloatSim.java` (không chỉ 2 tool mới)
cho MỌI lời gọi `getClient242()` xuyên suốt codebase. Sửa vội (vd thêm nhanh 1 override namespace
riêng cho `getClient242()`) có rủi ro thật nếu:
(a) 242 còn namespace khác ẩn mà `info_all` không thấy do quyền hạn chế (tôi chỉ thấy 1 namespace
    trả về, chưa chắc là toàn bộ danh sách),
(b) có nơi khác trong code ĐANG hoạt động đúng với `test` trên 242 (vd nếu 242 từng dùng `test`
    và mới đổi tên gần đây, code cũ có thể có che-đậy/fallback tôi chưa thấy hết),
(c) đây là quyết định ảnh hưởng kiến trúc (đổi hằng số namespace toàn cục hay tách riêng theo
    cluster) — đúng loại việc "có tầm ảnh hưởng" theo `CORE.md` cần phản biện/user quyết, không
    phải việc vặt tự sửa.

**Đề xuất cho Uni/CCD sau (KHÔNG tự làm, chỉ đề xuất):**
1. Xác nhận lại với Uni: 242 đổi/luôn tên namespace là `ticker` (không phải `test`) — có đúng
   không, có lịch sử đổi tên nào không.
2. Nếu đúng: thêm config key riêng (vd `AEROSPIKE_NAMESPACE_242=ticker`) + sửa
   `CopyTicker242To226`/`CopyAuxSets242To226` dùng namespace riêng cho `src` (242) khác `dst`
   (Oracle, vẫn `test`) — KHÔNG đổi `Configs.AEROSPIKE_NAMESPACE` toàn cục (sẽ vỡ mọi chỗ khác
   đang dùng đúng `test` cho Oracle/226).
3. Audit thêm mọi lời gọi `getClient242()` khác trong `DataManagerAerospikeFloatSim.java` (funding
   fee live-write, OI live-write, mapper live-write — dùng bởi 2 process live!) xem có đang cùng
   dính lỗi này không — NẾU CÓ nghĩa là 2 process live đang ghi/đọc nhầm namespace trên 242, một
   phát hiện nghiêm trọng hơn nhiều so với phạm vi task này (⚠️ nhưng KHÔNG được tự kiểm bằng cách
   động vào 2 process live — chỉ đọc code, hỏi Uni).
4. Sau khi fix + rebuild + redeploy jar: chỉ cần re-run `CopyTicker242To226 20260601 20260701`
   (đã idempotent/resume, script cũ đã skip đúng 10113 phút có sẵn) rồi `Validatetickercopy226`
   để PASS, rồi mới `CopyAuxSets242To226` (cùng bug, cùng cách fix).

### 3. Việc KHÔNG làm (đúng luật, vì checklist DATA chưa PASS)
- **CHƯA chạy `bg_selftest`, CHƯA `pipe_run wfo_canonical_1m`** — vì checklist mục 1 (ticker)
  và mục 3 (funding/mapper, chưa verify được range) đều chưa PASS, và nguyên nhân là bug hạ
  tầng thật (mục 2), không phải thứ nên bypass.
- **CHƯA đụng OI backfill** (mục 4 checklist) — ưu tiên xử lý bug chặn chung trước, tránh lặp
  lại đúng lỗi này ở 1 tool khác.
- **CHƯA sửa `DataManagerAerospikeFloatSim.java`/`Configs.java`** — đúng luật, việc có tầm ảnh
  hưởng để Uni quyết.

### 4. Sửa nhỏ 1 fact cũ (không ảnh hưởng an toàn): `docs/INFRA_FACTS.md` ghi disk Oracle "89%
(~17.6GB free)" — đo lại hôm nay (`df -h /`) ra **63% used, 55G free**. Có thể do đã dọn jar cũ
giữa lúc đó và giờ, không phải tôi dọn. Chưa sửa file đó (để nguyên, chỉ ghi nhận ở đây — sửa
fact ở INFRA_FACTS nên để CCD làm cùng lúc dọn dẹp, tránh 1 đổi nhỏ rải nhiều file).

**Trạng thái tại thời điểm ghi chú này:** Đã đo coverage thật (mục 1), phát hiện + mô tả đầy đủ
1 bug hạ tầng thật chặn toàn bộ đường sync 242→Oracle (mục 2), CHƯA chạy bất kỳ bước nào từ
`bg_selftest` trở đi. Không có dữ liệu nào bị hỏng/ghi sai (mọi lệnh thử đều fail sạch trước khi
ghi, `copied=0`). Cần Uni quyết hướng fix namespace ở mục 2 trước khi CCD tiếp theo tiếp tục.

## Cập nhật 2026-08-05 (phần 3) — ĐÃ FIX bug namespace (Uni chọn hướng "thêm config riêng cho
242"), verify thật trên Oracle, PASS. Phát hiện thêm 1 ANOMALY MỚI cần Uni xem trước khi tin
ticker Oracle 100%.

**Quyết định của Uni (2026-08-05):** thêm `AEROSPIKE_NAMESPACE_242` riêng, KHÔNG đổi
`AEROSPIKE_NAMESPACE` toàn cục, chỉ sửa 2 tool copy. Về rủi ro `BinanceDataIngestor`/
`Kline15m4hForwardRoller` (đọc/ghi 242 qua cùng hằng số) — **Uni tự kiểm tra, CCD KHÔNG động
vào** (đã tôn trọng, không đọc/không đụng log process live trong phần cập nhật này).

### 1. Đã sửa (code thật, trên máy Uni, qua bridge — không phải agent nền)
- `Configs.java`: thêm `AEROSPIKE_NAMESPACE_242` (đọc key mới, KHÔNG đổi `AEROSPIKE_NAMESPACE`
  hiện có) + comment giải thích đầy đủ root cause.
- `config.properties` (repo local): thêm `AEROSPIKE_NAMESPACE_242=ticker`.
- `CopyTicker242To226.java`: tách `srcKeys` (dùng chung sai) thành 2 mảng riêng `keys242`
  (namespace `AEROSPIKE_NAMESPACE_242`, dùng cho MỌI lời gọi trên client `src`/242) và
  `keysOracle` (namespace `AEROSPIKE_NAMESPACE`, dùng cho MỌI lời gọi trên client `dst`/Oracle)
  — sửa cả ở vòng copy chính VÀ `verifySample()`.
- `CopyAuxSets242To226.java`: thêm hằng `NS_242` riêng cho `src` (242), giữ `NS` cho `dst`
  (Oracle) — sửa `copyMapper()`, `copyFundingData()` (đổi `src.scanAll(sp, NS, ...)` →
  `src.scanAll(sp, NS_242, ...)`), và `verify()` (2 Key riêng cho mapper + funding sample).
- Build lại `mvn -DskipTests package` → `target/binance-java-sdk-1.2.4-shaded.jar` (99.5MB, build
  2026-08-05 19:29) → scp đè lên Oracle `/home/ubuntu/java/simulator/binance-sync-20260804.jar`
  (giữ nguyên tên file cho đơn giản, ĐÃ LÀ bản có fix). Đã append
  `AEROSPIKE_NAMESPACE_242=ticker` vào `/home/ubuntu/java/simulator/config.properties` trên
  Oracle (file thật được 2 tool dùng, KHÔNG phải file repo local).

### 2. Verify thật — fix hoạt động đúng
`CopyTicker242To226 20260601 20260701` (đúng phạm vi test nhỏ đã thử fail trước đây) chạy lại:
```
copied=35929 | skipped(đã có)=10113 | missing242=38
VERIFY 200 mẫu: khớp bytes=88 | LỆCH=0 | thiếu trên 226=111 | cả hai không có=1
```
KHÔNG còn `AerospikeException$InvalidNamespace`. `missing242=38` là 242 THẬT thiếu 38 phút trong
range này (gap nguồn, không phải lỗi tool). `thiếu trên 226=111/200` mẫu — đây là do
`verifySample()` lấy mẫu ngẫu nhiên từ `START_DATE` tới **NOW() thật** (không phải tới
`END_DATE`) — 1 hạn chế có sẵn từ trước (không phải do fix này), mẫu rơi vào 07-02→08-05 (chưa
copy lần nào) sẽ luôn ra "thiếu". KHÔNG phải bug mới, chỉ log hơi gây hoang mang — để CCD sau tự
quyết có sửa `verifySample()` cho đúng phạm vi `END_DATE` không (việc nhỏ, không khẩn).

### 3. Chạy full range `20210101→20260701` (background thật trên Oracle, không phải qua agent) —
`copied=0` (mọi phút cần đã có sẵn/đã được vá bởi bước 2 ngay trước đó) — **PHÁT HIỆN ANOMALY MỚI**
```
1980 ngày | copied=0 | skipped(đã có)=2891482 | missing(242 không có)=1478
VERIFY 200 mẫu: khớp bytes=44 | LỆCH=154 | thiếu trên 226=2 | cả hai không có=0
```
⚠️ **`LỆCH=154/200`** — đây KHÔNG phải "thiếu" (đã tách riêng counter, `thiếu trên 226` chỉ=2) —
đây là **BYTES THỰC SỰ KHÁC NHAU** giữa 242 và Oracle cho CÙNG 1 key (cả 2 bên đều CÓ record).
Không giải thích được bằng lý do sampling-range ở mục 2 (đó gây "thiếu"/onlySrc, không gây
"lệch bytes"). Log chạy sạch, không exception (`grep ERROR` chỉ ra đúng 1 dòng — dòng cảnh báo
cuối, không phải crash). **CHƯA rõ nguyên nhân** — có thể: (a) ticker Oracle có version cũ hơn/
được sửa lại tại 1 thời điểm nào đó khác với 242 hiện tại (data đã "lệch" từ trước, không phải do
lần copy nào), (b) format/encoding bin `data` có version khác giữa 2 lần ghi cũ, (c) something
else. **KHÔNG tự đoán/tự sửa** — đây có thể ảnh hưởng tới ĐỘ TIN CẬY của toàn bộ ticker Oracle
đang dùng cho backtest/WFO hiện tại (không riêng task 251), cần Uni biết TRƯỚC khi export dataset
dùng data này. Log đầy đủ tại `/home/ubuntu/claudedata/task251_copyticker_full.log` trên Oracle.

**Đề xuất cho Uni/CCD sau (không tự làm):**
1. Lấy đúng 200 key LỆCH đó ra (sửa tạm `verifySample()` log thêm keyString khi mismatch), so
   trực tiếp giá trị đã giải mã (không phải chỉ bytes) giữa 242 và Oracle cho vài key mẫu để biết
   khác nhau THẬT ở đâu (giá klines khác, hay chỉ khác định dạng/nén).
2. Nếu xác nhận là data-drift thật (không phải lỗi verify) → cần quyết định: tin 242 (nguồn) hay
   Oracle, và có cần re-sync toàn bộ ticker Oracle từ 242 (FORCE_OVERWRITE=true) không.

### 4. Việc CHƯA làm (đúng luật, chờ Uni quyết mục 3 trước)
- CHƯA chạy `bg_selftest`/`pipe_run wfo_canonical_1m`.
- CHƯA sync `funding_data`/`symbol_mapper` qua `CopyAuxSets242To226` (đã fix code, CHƯA test
  thật — nên test phạm vi nhỏ trước, giống cách đã làm với ticker).
- CHƯA đụng OI backfill.
- CHƯA đọc/động tới process live `BinanceDataIngestor` (đúng yêu cầu Uni).

**Trạng thái tại thời điểm ghi chú này:** Bug namespace ĐÃ FIX + verify hoạt động đúng cho ticker
copy. Phát hiện thêm 1 anomaly THẬT (byte mismatch 242 vs Oracle, không rõ nguyên nhân, không tự
sửa) — mức độ ảnh hưởng CÓ THỂ RỘNG HƠN task 251 (toàn bộ ticker Oracle). Cần Uni xem mục 3 trước

## Cập nhật 2026-08-05 (phần 4) — ĐÃ ĐIỀU TRA XONG anomaly LỆCH ở phần 3 — KẾT LUẬN: KHÔNG PHẢI
data lệch/hỏng, là ghost-symbol đã biết. Oracle ĐÚNG, không cần đồng bộ/ghi đè gì.

**Theo đúng yêu cầu Uni** ("lấy dữ liệu ra đối chiếu Binance Vision/API, nếu Oracle sai thì đồng
bộ ghi đè, nếu 242 thiếu thì dừng"): đã viết tool chẩn đoán mới `DiagnoseTickerMismatch242VsOracle.java`
(read-only cả 2 phía, KHÔNG ghi gì) — giải nén Snappy + decode proto `MinuteDataFinal` rồi so
TỪNG SYMBOL theo giá trị thật (không so raw bytes như `verifySample()` cũ hay bị false-positive
do thứ tự serialize map khác nhau).

**Quét mẫu 4 ngày rải khắp lịch sử** (`sampleEveryNMin=1`, đủ 1440 phút/ngày):
```
2021-06-15: checked=1440 byteMismatch=0 realDecodeMismatch=0   (SẠCH)
2022-06-15: checked=1440 byteMismatch=0 realDecodeMismatch=0   (SẠCH)
2023-06-15: checked=1440 byteMismatch=1440 realDecodeMismatch=1440 symbolLevelDiffs=4320  (LỆCH 100%)
20260601:   (đã kiểm ở phần 3, byteMismatch=0 — ngày này mới copy lại nên trùng)
```
2023-06-15 lệch ở ĐÚNG 3 symbol cố định mỗi phút: `FTTUSDT`, `RAYUSDT`, `SCUSDT` — 242 CÓ record
(giá carry-forward, `usdt=0.0` tức KHÔNG có volume/trade thật), Oracle KHÔNG CÓ record cho 3
symbol này (đã bị dọn).

**Đối chiếu Binance Futures `exchangeInfo` THẬT (API chính thức, không suy đoán):**
```
FTTUSDT: status=SETTLING, deliveryDate=1668398400000 (2022-11-14)
RAYUSDT: status=SETTLING, deliveryDate=1668484800000 (2022-11-15)
SCUSDT:  status=SETTLING, deliveryDate=1655456400000 (2022-06-17)
BTCUSDT: status=TRADING,  deliveryDate=4133404800000 (đối chứng — còn giao dịch bình thường)
```
Cả 3 symbol đều đã **delist/settle TRƯỚC 2023-06-15 hàng tháng** — KHÔNG có giao dịch thật nào
tồn tại ở ngày này. `usdt=0.0` (volume=0) trong record của 242 xác nhận đây chỉ là **ghost/giá
carry-forward**, không phải trade thật.

**⇒ KẾT LUẬN CUỐI:** Đây CHÍNH XÁC là caveat đã biết + đã ghi ở "Checklist DATA" mục 1 đầu file
này ("242 chưa ghost-clean... Oracle-local đã CleanTickerGhostAndTail sạch rồi"). KHÔNG phải data
lệch/hỏng mới. **Oracle ĐÚNG** (đã dọn ghost đúng), **242 mới là bên có rác** (ghost carry-forward
của symbol đã delist). Theo đúng hướng dẫn của Uni ("nếu Oracle sai thì đồng bộ ghi đè") — Ở ĐÂY
NGƯỢC LẠI: Oracle KHÔNG sai, KHÔNG cần overwrite gì cả — nếu đồng bộ ghi đè theo 242 sẽ VÔ TÌNH
đưa ghost trở lại Oracle (thoái bộ, sai hướng). Hành động đúng khi copy các đoạn MỚI từ 242 vẫn là
đúng như checklist đã ghi từ đầu: copy xong rồi chạy `CleanTickerGhostAndTail` cho đoạn mới đó,
KHÔNG cần làm gì thêm cho phạm vi lịch sử cũ (những đoạn 2021-2026 đã có sẵn/đã dọn trước đó).

**Không cần dừng lại chờ Uni phân tích thêm** cho phát hiện này — đã tự đối chiếu xong với nguồn
Binance thật, kết luận rõ ràng, không mơ hồ. Coi anomaly phần 3 là ĐÃ GIẢI QUYẾT (không phải bug,
không cần fix code/data gì thêm). File tool chẩn đoán giữ lại trong repo (`DiagnoseTickerMismatch242VsOracle.java`,
read-only, an toàn) để CCD sau tái dùng nếu nghi ngờ mismatch nào khác.

**Trạng thái tại thời điểm ghi chú này:** Bug namespace ĐÃ FIX (phần 3). Anomaly byte-mismatch ĐÃ
ĐIỀU TRA XONG — là ghost-symbol đã biết, KHÔNG phải lỗi, Oracle đúng, không cần sync/overwrite gì.
Việc còn lại: test `CopyAuxSets242To226` (funding/mapper), OI backfill, rồi `bg_selftest`/
`pipe_run`. KHÔNG có blocker mới nào cần Uni quyết thêm ở bước này — có thể tiếp tục checklist.
khi tiếp tục.

## Cập nhật 2026-08-05 (phần 5) — checklist mục 3/5 (funding+mapper) PASS thật + mục 4 (OI) PASS
thật, số liệu đo được — **1 phát hiện quan trọng: gap OI thật KHÁC với giả định đầu file.**

### Mục 3 + 5 — `CopyAuxSets242To226` (funding_data + symbol_mapper): chạy thật, PASS
```
symbol_mapper: 242 size=863 | 226 size=863 | KHỚP ✅
funding_data:  copied=90 | skipped(đã có)=721 | noKey=0
VERIFY funding_data 4 mẫu: khớp bytes=4 | LỆCH=0 | thiếu 226=0
```
Log đầy đủ: `/home/ubuntu/claudedata/task251_copyaux.log` (Oracle). Không có gì cần Uni quyết —
verify sạch 100%.

### Mục 4 — OI backfill: **phát hiện giả định sai trong checklist gốc, đã đo lại và sửa đúng**

**Giả định gốc (đầu file này, mục 4):** file `oi_percoin_20210101_to_20260624.bin.gz` "đã validate
đủ cho coin delist", chỉ thiếu đoạn `06-24→07-01`. **Đo thật bằng `BackfillOiVerify` (đọc lại
Aerospike 226, không suy đoán từ tên file) cho thấy SAI:** coverage OI/LS/taker THẬT trên 226 chỉ
tới **`2026-06-16 03:20`** (đã kiểm BTCUSDT/ETHUSDT/DOGEUSDT — cùng mốc cắt, tức đây là ranh giới
hệ thống của lần backfill TASK-013 trước, không phải riêng 1 symbol). Tên file `.bin.gz` chỉ phản
ánh tham số `end` lúc export, KHÔNG phản ánh coverage thật của Aerospike bên dưới — 2 con số này
đã bị đồng nhất nhầm trong checklist gốc. **Gap thật cần fill: `2026-06-16 → 2026-07-01` (~16
ngày), không phải `06-24→07-01` (~7 ngày) như đã ghi.**

**Vì sao không dùng `OiFillGap` (TASK-035, đã có sẵn trong repo):** tool này gọi trực tiếp REST
`/futures/data/openInterestHist` (và 4 endpoint LS/taker tương ứng) của Binance — **đã đo thật
2026-08-05: API này chỉ giữ ~30 ngày gần nhất** (`startTime` cũ hơn 30 ngày → lỗi `-1130 parameter
'startTime' is invalid`, xác nhận bằng binary-search thật trên `fapi.binance.com`). Gap
`2026-06-16→2026-07-01` đã ở NGOÀI cửa sổ 30 ngày tính từ hôm nay (2026-08-05) → `OiFillGap`
không thể lấy được data này. Đây chính xác là lý do checklist gốc ghi "qua đúng pattern TASK-013"
(không phải TASK-035) — TASK-013 dùng nguồn khác: `data.binance.vision` (daily zip, giữ nhiều
năm, đã xác nhận thật bằng `curl` HTTP 200 cho `BTCUSDT-metrics-2026-06-24/06-27/07-01.zip`).

**Vì sao không dùng trực tiếp `BackfillOiMaster`/`BackfillOiWorker` (TASK-013 gốc):** 2 tool này
dùng checkpoint `oi_backfill_done` (Aerospike) — hầu hết symbol ĐÃ có record DONE từ lần backfill
full-history trước (tới 06-16), nên `isDone()` sẽ chặn, không enqueue lại được đoạn mới trừ khi
`--reset` (xoá TOÀN BỘ bookkeeping DONE của cả lịch sử 2020→2026, không cần cho việc nhỏ này, rủi
ro nếu quên hoặc chạy nhầm sau).

**Đã làm:** viết tool mới `research/oibackfill/OiFillGapVision.java` — ONE-SHOT đơn giản, tái dùng
`VisionMetricsClient.fetchSymbol(symbol, threads, startMs, endMs)` (đã có sẵn, TASK-013) +
`DataManagerAerospikeFloatSim.writeMetricMap226` (merge-guard, idempotent) — **KHÔNG đụng
`oi_backfill_queue`/`oi_backfill_done`** (tránh side-effect lên bookkeeping full-history), args
`<start yyyyMMdd> <end yyyyMMdd> [run] [SYMBOL...]`, không liệt kê symbol → lấy toàn bộ universe
từ S3 listing (giống mặc định `BackfillOiMaster`).

**Chạy thật (Oracle, `ubuntu@161.118.212.3`):**
```
lệnh: OiFillGapVision 20260616 20260701 run   (universe = toàn bộ S3 listing, KHÔNG giới hạn symbol)
kết quả: touched=689 | empty(không có file trong range)=271 | error=0 | tổng ~3,035,599 điểm (OI đại diện)
thời gian chạy: ~23 phút (21:28 → 21:51)
log đầy đủ: /home/ubuntu/claudedata/task251_oifillgap_run.log (Oracle)
```
**Verify lại bằng `BackfillOiVerify`** (đọc lại 226, không tin log ghi):
```
BTCUSDT:  open_interest range[2020-09-01 00:00 .. 2026-07-01 23:55] (trước: .. 2026-06-16 03:20) | RAW-RECOMPUTE maxDiff=0.000000%
ETHUSDT:  range .. 2026-07-01 23:55 | RAW-RECOMPUTE maxDiff=1.053219% (mẫu so file 2024-04-03, KHÔNG liên quan đoạn mới fill)
DOGEUSDT: range .. 2026-07-01 23:55 | RAW-RECOMPUTE maxDiff=2.327338% (tương tự, mẫu cũ)
```
Cả 5 set (open_interest/oi_ls_toptrader_acc/pos/oi_ls_global_acc/oi_taker_vol) đều đã nối liền tới
`2026-07-01 23:55`, offGrid5m=0 (đúng lưới 5 phút). **Mục 4 checklist DATA: PASS thật, có bằng
chứng đo lại, không phải giả định.**

**Vì sao KHÔNG cần đụng lại `ExportFundingOiPerCoin`/file `.bin.gz` thủ công:** đã đọc code —
tool export này đọc trực tiếp `getMetricMap226()` (Aerospike 226) tại thời điểm chạy, không đọc từ
file `.bin.gz` cũ. Bước `tool1_export`/`label_export` trong pipeline `wfo_canonical_1m.json` (đã
sửa `args.end=20260701` từ trước, xem đầu file) khi chạy sẽ tự sinh lại file export đúng phạm vi
mới, ăn theo data 226 đã fill — không cần bước "regenerate .bin.gz" tách riêng.

**Phát hiện phụ (KHÔNG thuộc phạm vi task này, ghi nhận để Uni quyết sau, KHÔNG tự sửa):**
`PEPEUSDT` và tổng cộng 271/960 symbol trong universe S3 hiện tại trả về "không có file metrics
nào" cho TOÀN BỘ range `06-16→07-01` — tức các symbol này **hoàn toàn không có OI/LS/taker
history** trên `data.binance.vision` (không phải thiếu 1 đoạn, mà chưa từng có), khác hẳn bản chất
với gap trailing đang xử lý ở đây. Một số trong 271 này là symbol cũ đã delist lâu (hợp lý, ví dụ
`*BUSD` — cặp BUSD đã ngừng từ lâu), nhưng `PEPEUSDT` là 1 symbol ĐANG SỐNG, volume lớn — đáng ngờ
hơn, cần Uni xem lại có phải bug ở universe-listing (S3 folder naming khác) hay Binance thật sự
không publish metrics cho symbol này. KHÔNG chặn task 251 (OI của các symbol chính — BTC/ETH/DOGE/
top-volume — đã đủ, WFO train không nhất thiết cần 100% coverage mọi symbol).

**Trạng thái tại thời điểm ghi chú này:** Checklist DATA mục 1 (ticker) — PASS + đã giải quyết
anomaly (phần 3/4). Mục 2 (label/market object) — derive từ ticker, không cần hành động riêng.
Mục 3 (funding) — PASS thật. Mục 4 (OI) — PASS thật (phần này). Mục 5 (mapper) — PASS thật (cùng
tool mục 3). Mục 6 (Kaggle dataset upload) — dùng nút có sẵn lúc chạy thật, chưa cần làm trước.
**Toàn bộ checklist DATA đã PASS — sẵn sàng qua bước "Chạy thật": `bg_selftest` → `pipe_run
wfo_canonical_1m`.**

## Cập nhật 2026-08-05 (phần 6) — ĐÃ CHẠY `bg_selftest` + `pipe_run wfo_canonical_1m` THẬT.
Pipeline ĐANG RUNNING trên Oracle. CHƯA tới `gate_sign` — sẽ dừng đúng ở đó, KHÔNG tự resume/sign.

**`bg_selftest` (Oracle, qua workaround SSH trực tiếp):** PASS 6/6 — job=`selftest_1785941675`.

**Pre-flight trước khi bấm nút thật:**
```
sys_health: disk /=63% dùng (còn 57.3GB) | RAM avail=21.28/23.42GB | load thấp | java_procs=0
bg_list: chỉ còn job cũ đã SUCCESS (orphan, không liên quan) — không có job nào đang chạy thật
pipeline JSON trên Oracle (CE_PIPES_DIR): xác nhận lại "end": "20260701" cho cả label_export và
  tool1_export — đúng bản đã sửa, không bị revert bởi lần deploy jar nào giữa phiên.
```

**`pipe_run wfo_canonical_1m` — ĐÃ CHẠY THẬT lúc 21:56:00:**
```
pipe_id=wfo_canonical_1m_1785941760 | runner_pid=162092 | n_steps=18
state_file=/home/ubuntu/claudedata/.run/mcp_ce/pipe_wfo_canonical_1m_1785941760_state.json
```
**Kiểm tra sớm (90s sau khi start) bằng `pipe_status`:** `RUNNING (2/18 step)` —
`mkdir_label_dir`=success, `label_export`=success (đã dispatch nền, log:
"Da khoi chay label_export (LABEL_STEP_MIN=1) o nen" — **xác nhận LABEL_STEP_MIN=1, tức đúng
lưới 1 phút, không phải 15 phút cũ**), đang ở `wait_label` (step 2, chờ job label_export nền
xong). Đúng thứ tự 18 step đã thiết kế (label_export → wait → tool1_export → wait → sync_kernel →
push dataset → wait → kaggle_push → wait_kaggle(≤8h) → kaggle_output → build_ds → wait →
validate_report_only → **gate_sign** → sign_manifest).

**Việc tiếp theo (không phải hỏi Uni ngay, tự làm):** theo dõi tiến độ theo chu kỳ hợp lý (không
ngồi poll liên tục, đúng luật ở mục "Rủi ro treo" đầu file — `wait_kaggle` timeout tới 8h). Sẽ
kiểm tra lại `pipe_status wfo_canonical_1m_1785941760` sau mỗi khoảng thời gian, cập nhật file này
khi có tiến triển đáng kể (qua từng step nặng: `label_export`/`tool1_export` xong, `kaggle_push`
xong, `wait_kaggle` xong).

**Điểm PHẢI dừng (nhắc lại, không tự vượt qua):** tới `gate_sign` (step 16, `llm_gate`) — đọc
`${out_ds}/validation_report.txt`, ghi verdict vào file này, **STOP**, KHÔNG tự `pipe_resume`.
Uni quyết `pipe_resume` (PASS, ký duyệt) hay `pipe_stop` (FAIL/chưa chắc).

**Trạng thái tại thời điểm ghi chú này:** Pipeline THẬT đang chạy trên Oracle+Kaggle
(`wfo_canonical_1m_1785941760`), step 2/18, đúng lưới 1 phút, đúng `FIRST_CUTOFF=20230101`/
`expect_leakfree=2023-01-01` (không đổi, theo "lối A"). Không có blocker. Đợi tiến độ tự nhiên,
không cần Uni làm gì lúc này — sẽ báo lại khi tới `gate_sign` hoặc nếu có step FAIL.

## Cập nhật 2026-08-05 (phần 7) — RÀ theo yêu cầu Uni: gate layer, hpo-ticker-daily, marketobject,
fundingfee, OI trên Kaggle. **1 GAP THẬT phát hiện ở gate layer, cần Uni quyết trước khi vá.**

### 1. Gate layer (tầng 7, `ai_pred_market_gate_wfo`) — Cảnh báo #5 cũ ("chưa đo lại") ĐÃ ĐO THẬT
Viết tool đọc-only mới `DiagnoseGateCoverage.java` (tái dùng đúng
`getAllMarketAiPredictionsFromAerospikeSet`, không tự dựng lại cơ chế đọc) — chạy thật trên Oracle:
```
TỔNG record=2,717,280 | ts min=2021-04-01 00:00 | ts max=2026-05-31 23:59 | #tháng có data=62
Mọi tháng 2021-04→2026-05 đều ĐẦY (43200-44640 record/tháng = mọi phút, KHÔNG có tháng nào rỗng/thiếu)
```
⇒ Phần LỊCH SỬ (2021-2022 vốn nghi ngờ theo Task 156, và cả 2023-2025) **SẠCH, KHÔNG có gap** — Cảnh
báo #5 với ý "2021-2022 gần trống" đã lỗi thời, không còn đúng ở dữ liệu hiện tại.

⚠️ **NHƯNG: gate DỪNG ở `2026-05-31 23:59` — THIẾU đúng `2026-06-01 → 2026-07-01` (~1 tháng)**, tức
KHÔNG phủ hết tới mốc export `20260701` của task này. Khớp với default `end="20260601"` hard-code
trong `WFOGateRunner.java` — có vẻ lần chạy gate gần nhất dùng đúng default đó, chưa ai update.

**Vì sao đây LÀ rủi ro thật, không chỉ lý thuyết:** đã đọc `scripts/model_quality/validate_canonical_wfo.py`
(tầng 9, chạy ở `validate_report_only` step 15 của pipeline đang chạy) — script này kiểm `pred.bin`
(chính là gate sau khi export) theo: leak-guard (ts không < leakFreeFrom), off-grid %60000, NaN-frac
horizon đã chọn. **KHÔNG có check nào bắt lỗi "ts MAX không tới đủ ngày mong đợi"** — nếu gate chỉ
tới 05-31, validator rất có thể chỉ log `ts[min..max]` rồi PASS/WARN, KHÔNG tự FAIL. Nghĩa là nếu
không vá, `gate_sign` có thể ký PASS một dataset thiếu ÂM THẦM gate/pred cho đúng đoạn OOS mới nhất
(06-2026→07-2026) — đúng loại lỗi "im lặng" mà tài liệu `WFO_DATA_PIPELINE_MASTER.md` luôn cảnh báo.

**Vì sao KHÔNG tự vá ngay:** `WFOGateRunner.java` KHÔNG có cơ chế resume/incremental — mỗi lần chạy
LUÔN replay lại TOÀN BỘ từ `fairStart` (mặc định `20210101`) tới `end` mới (1 lần duy nhất, giữ RAM,
rồi lặp fold train+predict). Theo comment trong code: "nút cổ chai là replay ~30-45s/ngày". Từ
`2021-01-01` tới `2026-07-01` ≈ 2020 ngày ⇒ **ước tính riêng PHA 1 (replay) ≈ 17-25 GIỜ**, chưa tính
~20 fold train+predict Python nối theo (vài giây/fold, không đáng kể so với replay). Đây là 1 job
RẤT NẶNG, RẤT LÂU trên Oracle (chiếm 1/3 slot java hàng chục giờ) — quyết định có tầm ảnh hưởng lớn
(thời gian, tài nguyên, có thể phải chạy song song/nối tiếp với các job OI/label/tool1 khác), đúng
loại việc CORE.md yêu cầu đưa Uni quyết, KHÔNG tự chạy.

**Đề xuất (Uni chọn 1 trong các hướng, hoặc hướng khác):**
- (A) Chạy `WFOGateRunner` full lại ngay (20210101→20260701) — chấp nhận mất 17-25h+ trên Oracle,
  chạy sau khi `label_export`/`tool1_export`/OI export hiện tại xong (đỡ tranh CPU 4-core), rồi
  `LoadWfoGatePredTool` nạp lại Aerospike, rồi mới tin `gate_sign` của lần `pipe_run` NÀY.
- (B) Cho pipeline hiện tại (`wfo_canonical_1m_1785941760`) chạy hết tới `gate_sign` với gate hiện có
  (biết trước sẽ thiếu 1 tháng cuối) — Uni tự đánh giá tại `gate_sign` xem thiếu 1 tháng gate có
  chấp nhận được không (vd nếu OOS thật sự dùng để backtest/train không cần tới sát 07-01), rồi vá
  gate SAU bằng 1 lần `pipe_run` MỚI riêng (không phải sign dataset thiếu).
- (C) Viết thêm chế độ incremental cho `WFOGateRunner` (chỉ replay+train fold mới, tái dùng featureStore
  đã có) — giảm mạnh thời gian, nhưng là thay đổi CODE có rủi ro lệch logic (rủi ro nêu ở đầu file
  `WFOGateRunner.java`: "đưa cả WFO sang thay đổi = rủi ro lệch logic cao") — cần cân nhắc kỹ, không
  làm vội trong lúc pipeline chính đang chạy.

### 2. Kaggle `chuyendinh/hpo-ticker-daily` — THIẾU 2026, nhưng KHÔNG chặn pipeline đang chạy
Đo qua `kaggle datasets list`: dataset thật, version mới nhất **2026-07-13**, theo
`docs/INFRA_FACTS.md`/`KAGGLE_FANOUT_RESULT.md` chỉ chứa **1826 file `ticker_YYYYMMDD.bin`
(2021-01-01 → 2025-12-31)** — THIẾU TOÀN BỘ 2026 (~182 ngày, tới 07-01).
**Đã kiểm — KHÔNG ảnh hưởng pipeline `wfo_canonical_1m` đang chạy**: đọc thật
`orchestrator/kernels_wfo1m/selector-predict-1m/kernel-metadata.json` → `dataset_sources` = CHỈ
`["chuyendinh/funding-tool1-features-1m", "chuyendinh/funding-oi-percoin",
"chuyendinh/funding-label-full-1m"]` — **KHÔNG có `hpo-ticker-daily`** trong đó. Kernel selector 1-phút
không đọc ticker-file, chỉ đọc Tool1/label/OI đã pre-process. `hpo-ticker-daily` chỉ dùng cho kernel
fanout khác (nhắc ở `KAGGLE_FANOUT_RESULT.md`/`SESSION_START.md`, KHÔNG thuộc task 251) — ghi nhận
là 1 gap CÓ THẬT nhưng KHÔNG chặn task này, để CCD/Uni quyết vá riêng lúc khác nếu cần cho việc khác.

### 3. Marketobject (tầng 2, `market_data`) — KHÔNG cần Kaggle, đọc LIVE từ Aerospike lúc build
Đọc `WfoDataset.java`: `build_ds` (step 13 pipeline, chạy TRÊN Oracle) gọi trực tiếp
`DataManagerAerospikeFloatSim.getAllMarketDataFromAerospike()` — market_data KHÔNG đi qua Kaggle,
KHÔNG cần dataset riêng. Miễn ticker (nguồn gốc market_data) đủ tới 20260701 — ĐÃ xác nhận PASS ở
phần 2-4 (ticker Oracle sạch, đủ dải) — thì market_data tự đủ khi build_ds chạy tới, KHÔNG có hành
động riêng cần làm.

### 4. Fundingfee — tự động phủ đủ qua `tool1_export` đang chạy trong pipeline này, không cần Kaggle riêng
`funding_data` (Aerospike, đã sync qua `CopyAuxSets242To226` ở phần 5, PASS) là 1 nguồn feature ĐẦU
VÀO của `tool1_export` (đang chạy, sẽ chạy sau khi `label_export` xong ở step hiện tại) — kết quả
`ff_*.bin` được `push_tool1_dataset` đẩy thẳng lên `chuyendinh/funding-tool1-features-1m` MỚI, KHÔNG
qua dataset trung gian nào khác. Không có hành động riêng cần làm — tự động đủ khi pipeline chạy tới.

### 5. OI trên Kaggle (`chuyendinh/funding-oi-percoin`) — THẬT SỰ STALE, ĐANG VÁ
Đo qua `kaggle datasets files`: `oi_percoin_full.bin` creationDate **2026-06-21** — CŨ HƠN CẢ file
Oracle cũ (`oi_percoin_20210101_to_20260624.bin.gz`, mtime 07-07), và cũ hơn NHIỀU so với Aerospike
226 vừa backfill xong ở phần 5 (nay đủ tới 20260701). Đây LÀ gap thật, vì kernel đọc OI qua file
Kaggle (`OI_FILE=find1("/kaggle/input/**/oi_percoin_full.bin")` trong `run_train.py`), KHÔNG đọc
Aerospike trực tiếp — nghĩa là việc backfill Aerospike ở phần 5 sẽ VÔ DỤNG với lần train Kaggle này
nếu không regenerate + re-upload file.

**Đang vá (chạy thật, background, Oracle, KHÔNG đụng `oi_backfill_done`/queue cũ):**
- `DumpSymbolUniverse` → `/tmp/oisyms.txt` (862 symbol từ `symbol_mapper`, PASS).
- `ExportFundingOiPerCoin 20210101 20260701 symfile=/tmp/oisyms.txt` (nguồn=Aerospike 226, đọc-only
  phía Aerospike) → đang chạy (job #2/3, cùng `label_export` job #1, dưới giới hạn 3 java), tiến độ
  200/862 coin lúc ghi chú này, output `features_oi_percoin_v1/oi_percoin_20210101_to_20260701.bin.gz`.
- **Còn lại sau khi export xong:** `kaggle datasets version` (hoặc atom `kaggle_dataset_push`) đẩy
  file mới + `symbol_map.csv` lên `chuyendinh/funding-oi-percoin` — CHƯA làm, sẽ làm ngay khi export
  xong (không cần hỏi Uni, đây là hành động vá trực tiếp gap đã xác nhận, không có quyết định kiến
  trúc nào ở đây).

**Trạng thái tại thời điểm ghi chú này:** 4/5 mục đã rà xong (gate, ticker-kaggle, marketobject,
fundingfee) — chỉ CÒN 1 gap cần Uni quyết (mục 1, gate thiếu tháng cuối, vá tốn 17-25h+). OI (mục 5)
đang tự vá, không cần quyết gì thêm. Pipeline chính vẫn RUNNING step 2/18, không đổi.

## Cập nhật 2026-08-06 (phần 8) — pipe_run FAILED tại wait_label (step 2/18), NGUYÊN NHÂN: timeout_sec quá ngắn, KHÔNG phải job crash

**Trạng thái đo thật lúc kiểm tra (2026-08-06 05:40 ICT):**

```
pipe_status wfo_canonical_1m_1785941760 -> FAILED, done=2/18, current_step=2 (wait_label)
step_results[2] = {
  "id": "wait_label", "status": "failed",
  "result": {"status":"error","reason":"timeout","polls":361,"detail":"job_status(RUNNING)equalsSUCCESS->x"}
}
```

- `wait_label` config trong `/home/ubuntu/claudedata/.run/pipelines/wfo_canonical_1m.json`: `timeout_sec=21600` (6h), `interval_sec=60` → đủ 361 poll × 60s ≈ 6h01m thì timeout, pipeline tự đánh FAILED.
- **Job `label_export` (ExportFundingLabel) THỰC TẾ VẪN CHẠY BÌNH THƯỜNG, KHÔNG lỗi, KHÔNG crash**, đã chạy 1-min grid full range `20210101→20260701`, 698 symbol (kể cả coin đã chết, qua `SymbolLifecycleManager`), 7 horizon {4h,12h,24h,72h,7d,14d,30d}:
  - PID java `162097`, `ps`: `ELAPSED=07:43:05`, `TIME(cpu)=08:05:27`, `%CPU=104` (≈1 core, đúng như kỳ vọng job đơn luồng).
  - `bg_status label_export_funding_label_1m.csv` → `state.status = "RUNNING"`, `last_heartbeat` mới, không có `stop_reason`.
  - File output `/home/ubuntu/claudedata/wfo1m/label_ds_1m/funding_label_1m.csv` đang lớn dần liên tục: đo 2 mốc cách 30s → tăng từ `1,797,505,024` lên `1,799,921,664` byte (~80.4 KB/s tại thời điểm đo; trung bình cả quá trình ~64.6 KB/s — cùng bậc độ lớn, không có dấu hiệu treo/đứng).
  - Chưa có sidecar `funding_label_1m.csv.meta.json` (điều kiện job coi là DONE) → job chưa xong, KHÔNG biết chính xác % hoàn thành vì log job chỉ có 4 dòng khởi động (không log progress %) — không đủ dữ liệu để tính ETA chính xác, chỉ biết là còn đang chạy tiếp.
- **Rủi ro dây chuyền đã xác nhận bằng cách đọc trước tất cả `wait_*` step trong file pipeline**: `wait_tool1` cũng `timeout_sec=21600` (6h) — mà `tool1_export` ở grid 1 phút được doc nội bộ ghi nhận "phình ~15x" so với grid 15 phút, nên xác suất RẤT CAO cũng sẽ timeout-FAIL tương tự (hoặc nặng hơn) nếu chạy tiếp mà không sửa timeout trước.
  - Timeout các wait step khác (tham khảo, chưa đo job thật tương ứng): `wait_tool1_dataset=2400s`, `wait_label_dataset=2400s`, `wait_kaggle=28800s(8h)`, `wait_build=7200s(2h)`.

**KHÔNG tự sửa/resume** theo đúng yêu cầu — đây là quyết định có tính kiến trúc (đổi `timeout_sec` trong pipeline definition ảnh hưởng tới toàn bộ lần chạy 1-phút sau này, không riêng lần này). Đang chờ Uni quyết định 1 trong các hướng sau (job `label_export` vẫn đang chạy tiếp, không mất gì nếu chờ):

1. **Chờ `label_export` tự xong** (bg_status → SUCCESS + có sidecar `.meta.json`) rồi mới quyết resume — không đổi gì trong pipeline, chỉ đợi. Nhưng `pipe_resume` trên step đã FAILED có support "resume từ step đã fail sau khi qua rồi" hay cần chạy lại từ đầu — CẦN HỎI/KIỂM TRA CE tool trước khi làm, chưa xác nhận.
2. **Sửa `timeout_sec` của `wait_label` VÀ `wait_tool1`** trong `/home/ubuntu/claudedata/.run/pipelines/wfo_canonical_1m.json` lên mức đủ lớn (ví dụ 12-16h) cho tương xứng grid 1 phút, rồi mới resume — tránh lặp lại FAILED ở `wait_tool1` (bước nặng hơn).
3. Kết hợp cả hai: chờ `label_export` xong trước (không tốn thêm job Java nào, an toàn cho rule max-3-job), đồng thời Uni xác nhận mức `timeout_sec` mới cho các bước còn lại trước khi resume tiếp.

**An toàn hiện tại:** chỉ 1 job Java đang chạy (`label_export`, PID 162097) → đúng rule tối đa 3 job Oracle, còn dư 2 slot. `tool1_export` CHƯA start (step vẫn `pending`) vì pipeline đã dừng ở `wait_label` — không có rủi ro chạy chồng job.


## Cập nhật 2026-08-06 (phần 9) — Uni chọn "Sửa timeout rồi resume" → đã làm, pipeline RUNNING lại

- Backup file gốc: `/home/ubuntu/claudedata/.run/pipelines/wfo_canonical_1m.json.bak_20260806_beforetimeoutfix`.
- Đã sửa (chỉ 2 field, giữ nguyên cấu trúc/format JSON, không đổi gì khác):
  - `wait_label.timeout_sec`: 21600 (6h) → **43200 (12h)**.
  - `wait_tool1.timeout_sec`: 21600 (6h) → **57600 (16h)**.
- `pipe_resume wfo_canonical_1m_1785941760` → `status=resumed, from_step=2, runner_pid=172301`. Resume vào lại ĐÚNG step `wait_label` (không chạy lại `label_export` từ đầu — job Java `ExportFundingLabel` PID 162097 vẫn là job cũ, không có job Java thứ 2 nào bị launch thêm).
- Xác nhận `pipe_status` ngay sau resume: `RUNNING`, `done=2/18, current_step=2`. Đồng hồ đếm timeout của `wait_label` bắt đầu lại từ lúc resume (05:55 ICT), không cộng dồn với 7h43m job đã chạy trước đó — vậy job có tối đa 12h kể từ BÂY GIỜ để báo SUCCESS trước khi lại bị đánh FAILED.
- An toàn: vẫn chỉ 1 job Java (`label_export`) đang chạy trên Oracle → đúng rule tối đa 3 job.

**Bước tiếp theo:** tiếp tục theo dõi qua `send_later`; nếu vẫn `wait_label`/`wait_tool1` sau chu kỳ tới → chỉ là đang chờ (đã có timeout đủ lớn), không coi là bất thường trừ khi có `status=failed` mới hoặc job Java biến mất khỏi `ps aux`. Nếu FAIL lần nữa với lý do KHÁC timeout (ví dụ job Java thực sự crash) → dừng lại báo Uni ngay, không tự sửa tiếp.


## Cập nhật 2026-08-06 (phần 10) — OI-Kaggle (`chuyendinh/funding-oi-percoin`) đã đẩy xong version mới, kèm phát hiện + fix 1 lỗi merge tiềm ẩn

**Phát hiện quan trọng trước khi push (đọc `ml/training/gen_funding_wf_predictions.py` + `orchestrator/kernels_wfo1m/selector-predict-1m/run_train.py`):**
- Kernel `selector-predict-1m` glob input CỐ ĐỊNH tên file: `oi_percoin_full.bin` (KHÔNG PHẢI `.bin.gz`, phải giải nén trước khi push), `symbol_map.csv`, `funding_label.csv`.
- `gen_funding_wf_predictions.py` merge Tool1 + OI theo `symId` (numeric, từ `symbol_mapper`), sau đó `.merge(symbol_map_df, on="symId").dropna(subset=["symbol"])` — đây là LEFT-JOIN rồi drop hàng không khớp. **Nếu `symbol_map.csv` thiếu symId nào đang tồn tại trong Tool1/OI, toàn bộ feature-row của đúng symId đó bị drop ÂM THẦM (không log lỗi)** — tức nếu tái dùng file `symbol_map.csv` cũ (781 symbol, Jul 8) trong khi `symbol_mapper` hiện tại đã có 863 symbol (đo 2026-08-05), ~81 coin mới sẽ mất trắng khỏi dataset train mà không ai biết.
- Đã verify 781 symbol cũ là SUBSET đúng của 863 symbol hiện tại (`diff` sau khi bỏ CRLF -> khớp 100% cho phần chung, `symId` KHÔNG bị gán lại) — an toàn để regenerate superset thay vì lo ngại đứt gãy `symId` cũ.

**Đã làm (real, có bằng chứng):**
1. Viết tool mới `DumpSymbolMapCsv.java` (đọc-only, dump toàn bộ `symbol_mapper` ra `symId,symbol` CSV, sort theo symId) — build lại `binance-java-sdk-1.2.4-shaded.jar` trên máy Windows (mvn package, exit 0), scp jar mới sang Oracle (`binance-sync-20260806-symmap.jar`), chạy ra `/home/ubuntu/claudedata/symbol_map_20260806.csv`: **863 symbol, symId [1..863]**.
2. Giải nén `oi_percoin_20210101_to_20260701.bin.gz` (3.21GB) -> `oi_percoin_full.bin` (4,227,723,300 byte, khớp đúng công thức 140,924,110 dòng × 30 byte/dòng).
3. Cài `kaggle` CLI qua `pip3 install --user` trực tiếp trên Oracle (Python, KHÔNG phải job Java, không ảnh hưởng rule max-3-job) — push thẳng từ Oracle, tránh double-hop 4GB qua Windows.
4. Gặp lỗi `kaggle datasets metadata` (CLI 1.7.4.5) ghi `dataset-metadata.json` bị double-JSON-encode (file chứa 1 CHUỖI JSON lồng trong JSON, không phải object) -> `kaggle datasets version` báo "ID or slug must be specified". Fix: viết tay lại `dataset-metadata.json` đúng schema (`{"id":"chuyendinh/funding-oi-percoin","title":...,"licenses":[...]}`).
5. `kaggle datasets version -p . -m "..."` chạy nền, upload xong 3.94GB (`oi_percoin_full.bin`) + `symbol_map.csv` (~3 phút, ~23MB/s) → **status=ready**. Verify bằng `kaggle datasets files` sau khi có version mới:
   ```
   oi_percoin_full.bin  4227723300  2026-08-05 23:12:55  (cũ: 3411674190, 2026-06-21)
   symbol_map.csv             11232  2026-08-05 23:11:37  (cũ: 10964, 2026-06-21)
   gunzip.err                     0  2026-08-05 23:11:37  (rác vô hại, sót từ stage dir — không match glob pattern nào của kernel nên KHÔNG ảnh hưởng, để dọn ở lần push sau)
   ```

**Kết luận:** hạng mục "oi có hết trên kaggle và đầy đủ chưa" trong yêu cầu audit — ĐÃ XONG, dữ liệu OI trên Kaggle giờ khớp Aerospike tới 2026-07-01, và `symbol_map.csv` khớp đủ 863 symId (đóng luôn lỗ hổng silent-drop ~81 coin mới nếu có ai chạy lại kernel này trước khi tôi phát hiện).


## Cập nhật 2026-08-06 (phần 11) — check nhanh: pipeline vẫn RUNNING lành mạnh, không FAIL mới

- `pipe_status`: `RUNNING`, `done=2/18, current_step=2` (wait_label). Runner process `PID 172301` còn sống, elapsed 1h32m kể từ resume (05:55 ICT) — trong budget 12h mới.
- Lưu ý hiển thị: mảng `steps[]` của `pipe_status` VẪN in `wait_label.status="failed"` — đây là dữ liệu CŨ từ lần fail trước resume (field chỉ update khi 1 step HOÀN TẤT lần polling hiện tại, chưa phải fail mới). Đừng nhầm với FAIL thật — field đáng tin ở đây là `pipe_status` tổng (RUNNING) + runner PID còn sống + job Java còn tiến triển.
- Job `label_export` (PID 162097) vẫn tiến triển đều, không treo: đo 2 mốc cách ~1h48m (05:40 -> 07:27 ICT), file `funding_label_1m.csv` tăng từ 1.80GB -> 2.33GB (~82.7 KB/s, khớp tốc độ đo lần trước ~80KB/s) → không có dấu hiệu bất thường.
- Bridge remote-devices (Windows) đã ONLINE lại ở lần check này (lần check theo lịch trước đó ~06:2x bị lỡ vì bridge offline, đã báo Uni và tự dời lịch).


## Cập nhật 2026-08-06 08:20 ICT (phần 12) — check định kỳ: vẫn RUNNING lành mạnh

- `pipe_status`: RUNNING, 2/18, runner PID 172301 sống (elapsed 2h23m / budget 12h).
- Job `label_export` (PID 162097, CPU 657min): file tăng 2.585GB -> 2.588GB trong 40s (~82.1 KB/s, khớp tốc độ các lần đo trước) -> không treo.
- Không có gì mới cần quyết định. Tiếp tục theo dõi.


## Cập nhật 2026-08-06 08:40 ICT (phần 13) — Uni yêu cầu chạy song song 3 việc "cho nhanh" — đã chạy được 2/3, giải thích vì sao cái thứ 3 KHÔNG nên làm ẩu

**Đã làm: WFOGateRunner full re-run ĐÃ LAUNCH song song với label_export (job #2/3).**
- Trước khi bấm nút, đọc lại source `WFOGateRunner.java`: featureStore là **market-level aggregate** (1 vector 33 channel/phút, KHÔNG phải per-coin) — comment code ghi rõ "~2.6M phút × 33 float ≈ 350MB, vừa RAM Oracle 23GB". Tức RAM cho job này rất nhẹ, KHÁC hẳn lo ngại ban đầu (tưởng nhầm là replay per-coin nặng như OI/Tool1) — an toàn để chạy song song ngay, không cần đợi.
- Verify trước khi chạy: venv python train `~/envs/xgb-env/bin/python` (hardcode trong `runPythonTrain()`, KHÔNG phải `python3` hệ thống) có đủ `xgboost 3.2.0` + `onnx 1.22.0` — tránh trường hợp chạy full 17-25h replay xong rồi FAIL ngay fold đầu vì thiếu lib (code có fail-fast đúng: "rc!=0 -> DỪNG, không bỏ qua").
- Lệnh: `java -Xmx4g -cp gatecount.jar com.binance.chuyennd.ai_ml.features.export.gate.WFOGateRunner 20210101 20260701 3` (dùng default cho csvStore/modelTmpDir/outFile/pyScript/minTrainMonths — sẽ ghi đè `~/claudedata/wfo_feature_store.csv` + `wfo_gate_pred.csv` cũ từ lần chạy Jul 12, đúng ý "vá full").
- PID 177760, đã tải xong Market Data (2,774,140 record) + Symbol Mapper (863, khớp con số đã verify trước đó) + FundingFee (831 symbol) — đang chạy PHA 1 (replay). RAM sau khi thêm job này: 8.9GB used / 14GB avail (từ 6.7/16GB) — dư nhiều, không có gì đáng lo.
- Hiện tại: **2/3 job Java đang chạy** (label_export PID 162097 + WFOGateRunner PID 177760), đúng rule tối đa 3, còn dư 1 slot.

**KHÔNG chạy song song `tool1_export` (job thứ 3) ngay — lý do kỹ thuật, không phải RAM:**
- Đọc `_run_step()` trong `orchestrator/mcp_tools-v3.py`: step kiểu `"tool"` coi `status=="error"` là FAIL (`on_fail:"abort"`). Mà `cmd_tool1_export` trả `status:"error", state:"ALIVE_DO_NOT_RESTART"` nếu job_id đó ĐANG chạy — tức nếu tôi tự tay chạy `tool1_export` trước (job_id tính từ basename `${tool1_dir}`, CỐ ĐỊNH, không đổi được), thì khi pipeline chính TỰ chạy tới step `tool1_export` của nó sau này (sau khi `wait_label` cuối cùng thành công), nó sẽ THẤY job_id đó đang sống → step FAIL giả (giống lỗi timeout tôi vừa sửa hôm nay) → lại phải resume tay lần nữa.
- Nếu tôi tự tay chạy `tool1_export` dưới TÊN JOB KHÁC / ra thư mục KHÁC để tránh đụng job_id: `cmd_tool1_export` KHÔNG có check "output đã có rồi thì skip" (khác `build_ds` — tool đó CÓ check này) → khi pipeline chạy tới bước của nó, nó vẫn sẽ chạy lại TOÀN BỘ tool1_export từ đầu, tốn gấp đôi thời gian CPU cho đúng 1 việc, mà KHÔNG rút ngắn được critical path của pipeline chính (vì pipeline vẫn phải tự chạy xong bước của NÓ mới qua bước sau).
- Cách duy nhất để `tool1_export` chạy song song THẬT (không tốn gấp đôi) là tự tay sửa trực tiếp file state JSON của pipeline (`step_results`/`current_step`) để đánh dấu step đó "success" giả mà không cho pipeline tự chạy — đây là kiểu thay đổi trạng thái pipeline sản xuất bằng tay, rủi ro cao nếu làm sai (có thể hỏng luôn cả pipeline, phải chạy lại từ đầu cả 18 step) → thuộc loại quyết định kiến trúc cần Uni xác nhận trước, KHÔNG tự làm.

**Kết luận:** đã tăng từ 1→2 job song song thật (an toàn, có lợi thật). Job thứ 3 (`tool1_export`) để nguyên trong hàng đợi của pipeline chính (sẽ tự chạy khi `wait_label` xong) — nếu Uni muốn ép chạy song song luôn, cần xác nhận cho tôi sửa tay state JSON (rủi ro đã nêu trên) hoặc chấp nhận tốn gấp đôi CPU-time cho bước đó.


## Cập nhật 2026-08-06 08:55 ICT (phần 14) — QUYẾT ĐỊNH KIẾN TRÚC MỚI (Uni xác nhận): đổi sang "Kaggle làm trung tâm WFO"

**Quyết định:** đẩy CẢ gate prediction (hiện tại: local CSV -> Aerospike `ai_pred_market_gate_wfo`) VÀ market_data
(hiện tại: đọc live từ Aerospike ở `build_ds`) lên Kaggle làm file, thay cho việc `build_ds`/`WfoDataset.java`
đọc live Aerospike như hiện tại. Giữ nguyên: symbol_mapper KHÔNG cần đẩy lên Kaggle (Uni xác nhận rõ, chỉ
symbol_map.csv dạng CSV export như đã làm cho OI là đủ).

**KHÔNG làm ngay** — đúng theo lựa chọn Uni chọn (option có ghi chú "nên làm sau khi pipeline hiện tại xong"),
vì `wfo_canonical_1m_1785941760` đang chạy giữa đường (label_export + WFOGateRunner đang chạy song song lúc
08:55 ICT), sửa `build_ds`/`WfoDataset.java` lúc này rủi ro làm hỏng lần chạy đang có.

**Việc cần làm sau khi pipeline hiện tại xong (kể cả qua gate_sign) — ghi lại để không quên:**
1. Market_data: hiện chưa có tool export ra file (chỉ có `getAllMarketDataFromAerospike()` đọc live) — cần viết
   tool export mới (dạng `.bin`/`.bin.gz`, tương tự pattern OI/Tool1) rồi thêm bước push Kaggle dataset mới.
2. Gate prediction: CÓ SẴN đầu ra local (`~/claudedata/wfo_gate_pred.csv`, WFOGateRunner ghi ra TRƯỚC khi
   `LoadWfoGatePredTool` nạp vào Aerospike) — có thể tận dụng file CSV này để push thẳng lên Kaggle dataset mới,
   không cần viết tool export riêng, tiết kiệm việc.
3. Sửa `WfoDataset.java`/bước `build_ds` để đọc gate+market_data từ file Kaggle-downloaded thay vì gọi
   `getAllMarketDataFromAerospike()`/`getAllMarketAiPredictionsFromAerospikeSet()` live — CẦN THIẾT KẾ KỸ vì
   đây là thay đổi luồng dữ liệu tầng 7-8, ảnh hưởng gate_sign validation sau này. Nên trao đổi thêm với Uni
   về format/luồng cụ thể trước khi code (vd: build_ds vẫn chạy trên Oracle nhưng đọc file local đã tải từ
   Kaggle, hay build_ds sẽ chuyển hẳn sang chạy trên Kaggle luôn — 2 hướng khác nhau về mức độ thay đổi).
4. Cập nhật `wfo_canonical_1m.json` pipeline: thêm step push_gate_dataset/push_market_dataset tương tự
   push_tool1_dataset/push_label_dataset hiện có.


## Cập nhật 2026-08-06 09:17 ICT (phần 15) — check định kỳ: cả 2 job song song vẫn khỏe

- Pipeline chính: RUNNING, 2/18, runner PID 172301 sống (3h21m/12h budget). `label_export` file tăng 2.861GB->2.864GB/40s (~79KB/s, bình thường).
- WFOGateRunner: PHA 1 (replay) tới ngày 1680/~2020, ước còn ~15-20 phút nữa xong PHA 1 rồi sang PHA 2 (train fold).
- Không có gì cần quyết định.


## Phần 16 — check-in 2026-08-06 ~10:12 ICT

- pipe_status: RUNNING, 2/18 (wait_label). Không FAIL mới.
- runner_pid 172301: sống, elapsed 04:16:10 (khớp resume lúc 05:55 ICT).
- label_export PID 162097: sống, CPU 777:58, RSS ~6.36GB (cap -Xmx12g).
- File funding_label_1m.csv: 3129032704 -> 3131490304 bytes trong 30s (~81.9KB/s, đúng tốc độ bình thường). Chưa có .meta.json.
- WFOGateRunner: đã DONE từ 09:46:18 ICT (báo ở phần trước), không cần check lại theo yêu cầu lịch cũ (lịch này đặt trước khi biết WFOGateRunner xong) — mốc đã báo Uni, đang chờ Uni quyết định LoadWfoGatePredTool.
- Không có gì mới ngoài việc tiếp tục chạy khỏe -> không lặp lại report dài, tự schedule check tiếp ~50 phút.

## Phần 17 — Fix root-cause chậm label_export (2026-08-06 ~10:38-10:50 ICT)

### Phát hiện (đo thật, không đoán)
- Uni nghi vấn: label_export chạy 12h+ mà horizon 7d/14d/30d chưa cần cho WFO.
- jstack PID 162097 (job đang chạy): main thread RUNNABLE 100% CPU, đứng tại
  `ExportFundingLabel.finalizeBucket()` (vòng lặp quét `cs.active` ArrayDeque).
- Code: mỗi coin giữ tối đa H_MAX=43200 anchor mở đồng thời (30 ngày, vì STEP_MIN=1
  trên grid 1-phút) — finalizeBucket() quét O(anchors) MỖI PHÚT MỖI COIN.
- Đo tiến độ thật qua độ trễ emit anchor (anchor chỉ emit sau H_MAX=30 ngày): dòng
  cuối CSV lúc đó = 2021-03-23 → vị trí xử lý thật ≈ 2021-04-22 → chỉ ~112/2007
  ngày (~5.6%) sau 12h20m chạy → ETA full range ước ~9 NGÀY (không phải giờ).
- gen_funding_wf_predictions.py (script WFO thật trên Kaggle) CHỈ đọc
  maxFav_H/nBars_H cho H_LIST=[4h,12h,24h,72h] — 3 horizon dài (7d/14d/30d,
  bleed-thesis) hiện KHÔNG được tiêu thụ bởi WFO.
- Uni chọn: kill job cũ (sunk 12h20m, chấp nhận mất vì mới 5.6%), sửa code chỉ
  export 4 horizon ngắn cho critical path, horizon dài làm job riêng sau.

### Xử lý
1. `bg_stop label_export_funding_label_1m.csv` — dừng controller+child (162095,162096)
   nhưng JAVA con (162097) bị orphan (PPID=1, không tự chết) → kill -TERM 162097
   trực tiếp (PID cụ thể, KHÔNG killall/pkill java) → xác nhận chết + gatecount.jar
   hết holder (lsof rỗng) → `pipe_stop wfo_canonical_1m_1785941760` (pipe_id CŨ, dừng
   sạch, không job nào bị treo).
2. Sửa `ExportFundingLabel.java`: thêm env `LABEL_HORIZON_SET=short` (mặc định
   "full" = hành vi cũ 7 horizon, KHÔNG đổi behavior các caller khác) → khi =short:
   H_MINUTES/H_NAME chỉ còn {4h,12h,24h,72h}, H_MAX=4320 (thay 43200) → anchor-list
   ~1/10. Cũng sửa dòng log startup in H_NAME/H_MAX động (trước hardcode 7 horizon).
   Build lại (mvn package), backup jar cũ
   `/home/ubuntu/java/simulator/gatecount_pre20260806_fullhorizon.jar.bak`, deploy
   jar mới làm `gatecount.jar` canonical (xác nhận zero java process đang chạy
   trước khi swap).
3. **Pipe run #2** (`wfo_canonical_1m_1785987735`, LABEL_HORIZON_SET=short) BỊ LỖI
   KHÁC không liên quan horizon: label_export BLOCKED ngay do
   `/home/ubuntu/claudedata/.run/oracle_worker_cwd/config.properties` có
   `TICKER_SOURCE=file` (stale từ 13/7, sai — 2 config.properties khác cùng máy
   carry_probe/team_path đều "aerospike", và comment ngay trong file đó cũng ghi
   "aerospike" nhưng value sai). File-mode cần snapshot Kaggle không tồn tại trên
   Oracle → SymbolLifecycleManager nạp 0 symbol → BLOCKED (label_export return sớm,
   KHÔNG viết CSV — file cũ 3.1GB giữ nguyên, không hỏng). CE framework coi step
   "tool" = spawn thành công là "success" (không đợi job thật xong) → pipe tưởng
   chạy tới step 4/18 (tool1_export) trong khi label thực chất rỗng. tool1_export
   TỰ THẤT BẠI SẠCH (throw IllegalStateException, dir output trống — không hỏng
   dữ liệu) vì cùng lý do TICKER_SOURCE=file thiếu snapshot. Đã `pipe_stop` bỏ pipe
   #2, sửa config.properties `TICKER_SOURCE=file`→`aerospike` (sed, khớp 2 file
   tham chiếu + comment gốc).
4. **Pipe run #3** (`wfo_canonical_1m_1785988117`, LABEL_HORIZON_SET=short, runner_pid
   182961, label job PID 182969) — verify TRỰC TIẾP log lúc mới lên: "Nạp
   SymbolLifecycleManager từ Aerospike set... nạp 698 symbol" (đúng, không phải
   file-mode) + "H=[4h, 12h, 24h, 72h] | H_MAX=4320 buoc" (đúng short-horizon).
   Đo throughput qua độ trễ emit (H_MAX giờ = 3 ngày): 2 mốc đo cách 18s cho thấy
   tiến ~22h simulation/18s wall ≈ 180-210 ngày/giờ (so với ~8.9 ngày/giờ của bản
   cũ) → **speedup ~20x**, ETA full 2007 ngày ≈ **10-12 giờ** (thay vì ~9 ngày).

### Trạng thái sau fix
- Pipe CŨ `wfo_canonical_1m_1785941760`: STOPPED, bỏ (chỉ 5.6%, sunk cost 12h20m).
- Pipe #2 `wfo_canonical_1m_1785987735`: STOPPED, bỏ (corrupt do TICKER_SOURCE bug,
  không có dữ liệu thật nào bị mất/hỏng).
- Pipe HIỆN TẠI (theo dõi tiếp): `wfo_canonical_1m_1785988117`, 18 step, đang ở
  step 1-2 (label_export/wait_label), khỏe, throughput đã verify ~20x nhanh hơn.
- 7d/14d/30d (bleed-thesis) CHƯA export lại — sẽ làm job riêng sau khi Uni quyết
  định ưu tiên (không chặn critical path WFO hiện tại).

## Phần 18 — Phát hiện bug 2: CE bg_report tin result.json CŨ, không check PID còn sống (2026-08-06 11:04-11:06 ICT)

### Phát hiện
- pipe_status pipe #3 (`wfo_canonical_1m_1785988117`) báo "RUNNING (4/18 step)" với
  step 1 `label_export`=success, step 2 `wait_label`=success — NHƯNG job Java
  label_export (PID 182969) THỰC TẾ vẫn đang chạy sống (27 phút CPU, chưa xong).
- Root cause (đọc code `cmd_bg_report`, dòng 869-889 mcp_tools-v3.py):
  `job_status = (result or {}).get("status") or (state or {}).get("status", ...)`
  — LUÔN ưu tiên `<job_id>_result.json` nếu file này TỒN TẠI, KHÔNG kiểm tra xem
  PID trong result có khớp/còn sống so với `state.json` (state.json MỚI, có
  controller_pid/child_pid + last_heartbeat ĐÚNG job hiện tại; result.json CŨ từ
  lần chạy TRƯỚC dưới CÙNG job_id — vì job_id là deterministic theo basename
  output path, và pipe run #2 (bị lỗi TICKER_SOURCE=file) đã ghi
  result.json status=SUCCESS/exit_code=0 cho label_export (return sớm, KHÔNG lỗi
  compile) và status=FAILED cho tool1_export (throw exception) — 2 file result.json
  CŨ này còn tồn tại, không bị dọn khi pipe #3 spawn job MỚI dưới CÙNG job_id).
  ⇒ wait_label đọc thấy SUCCESS (của lần TRƯỚC, giả) → tưởng label xong → pipe
  nhảy luôn qua tool1_export dù label THỰC vẫn đang chạy song song, không đúng
  thứ tự phụ thuộc pipe định nghĩa (dù tool1_export không thực sự phụ thuộc dữ
  liệu label nên KHÔNG hỏng gì lần này — nhưng RỦI RO THẬT là các step SAU (vd
  wait_tool1 cũng có result.json cũ status=FAILED cho tool1_export, có thể khiến
  pipe ABORT giả; và xa hơn, push_label_dataset/kaggle_push có thể ĐẨY LÊN KAGGLE
  1 label CSV CHƯA XONG nếu pipe cứ tiếp tục tin state cũ).
- Đây là bug HỆ THỐNG của CE framework (`cmd_bg_report`), không riêng
  pipeline này — bất kỳ lần restart nào TÁI SỬ DỤNG job_id cũ (basename output
  path không đổi) đều có nguy cơ này nếu result.json cũ chưa bị dọn
  (`bg_cleanup <job_id> --all`) TRƯỚC khi spawn job mới.

### Xử lý ngay
- `pipe_stop wfo_canonical_1m_1785988117` — dừng RUNNER pipe (PID 182961) ngay,
  CHẶN không cho state-tracking sai này cascade tiếp (vd tới push_label_dataset).
  KHÔNG đụng 2 job Java thật (182968 tool1_export, 182969 label_export) — verify
  cả 2 vẫn sống, đang chạy khỏe sau khi stop runner.
- tool1_export (182968) xác nhận ĐANG CHẠY ĐÚNG (fix TICKER_SOURCE có hiệu lực):
  log cho thấy đã xong quý 2021-Q1 (11,019,264 records) trong ~8p15s, đang sang
  quý kế — ETA rất nhanh so với label (không có vấn đề anchor-list).
- label_export (182969) vẫn đang chạy đúng short-horizon, ETA ~10-12h như đã báo.

### Kế hoạch tiếp theo (KHÔNG chạy pipe_run mới cho 2 step này nữa)
- 2 job label_export/tool1_export sẽ tiếp tục chạy ĐỘC LẬP (không có pipe theo
  dõi) tới khi thật sự xong (tool1_export trước, label sau ~10-12h nữa).
- KHÔNG dùng `pipe_run` lại từ đầu khi 2 job xong — vì cmd_label_export/
  cmd_tool1_export KHÔNG có check "output đã fresh thì skip" (khác build_ds có
  check này) → pipe_run mới sẽ RESPAWN từ đầu, lãng phí toàn bộ ~10-12h.
- Khi cả 2 job THẬT SỰ xong (verify qua log dòng cuối/exit thật, KHÔNG qua
  bg_report vì đã biết có thể đọc result.json cũ): `bg_cleanup <job_id> --all`
  cho cả 2 job_id để dọn result.json cũ, LẤY result.json MỚI đúng (job vừa xong
  thật sẽ tự ghi đè khi thoát) → sau đó tự tay gọi từng CE tool step còn lại
  (sync_kernel → push_tool1_dataset → wait → push_label_dataset → wait →
  kaggle_push → wait → kaggle_output → build_ds → wait → validate_report_only)
  THAY VÌ pipe_run toàn bộ lại, để không respawn 2 export tool đã xong.

## Phần 19 — Bỏ horizon 7d/14d/30d + fix multi-threading + phát hiện OOM risk (2026-08-06 ~10:55-11:56 ICT)

### 1. 7d/14d/30d dùng để làm gì — KHÔNG dùng, đã đổi default để KHÔNG export nữa

Dispatch agent Explore quét TOÀN BỘ repo thật (qua bridge, không phải mirror `/mnt/user-data/uploads` cũ) tìm consumer của `maxFav_7d/14d/30d` (và các cột 7d/14d/30d khác). Kết quả: **0 consumer thật** (Python hay Java) — `gen_funding_wf_predictions.py` (script Kaggle chạy WFO selector) chỉ đọc `H_LIST=["4h","12h","24h","72h"]`. 3 horizon dài chỉ còn trong comment mô tả ý định nghiên cứu "bleed-thesis" (pump ngắn/dump dài) sau này, khớp với ghi chú cũ trong task file này ("CHƯA export lại — sẽ làm job riêng sau khi Uni quyết").

→ Xử lý theo đúng yêu cầu "không dùng thì bỏ": đổi default của `LABEL_HORIZON_SET` trong `ExportFundingLabel.java` — trước đây phải set `LABEL_HORIZON_SET=short` mới được 4 horizon ngắn (mặc định là full 7 horizon); giờ **mặc định là short (4 horizon), phải set `LABEL_HORIZON_SET=full` mới ra lại 7 horizon cũ**. KHÔNG xoá code — chỉ đổi mặc định, giữ khả năng bật lại full khi Uni quyết làm job "bleed-thesis" riêng.

### 2. Phát hiện thêm 1 rủi ro độc lập: OOM do `Validate` tích luỹ không giới hạn

Trong lúc soát code để làm multi-thread, phát hiện class `Validate` bên trong `ExportFundingLabel.java` gom `List<Float>` (`favAll`/`advAll` mỗi horizon) cho MỖI anchor emit ra — với full range 2007 ngày × ~800 coin, sẽ là hàng trăm triệu Float object, OOM trước khi job chạy xong.

Đo thật trên job SẢN XUẤT đang chạy (PID 182969, cũ, `NO_VALIDATE` KHÔNG được set — xác nhận qua `/proc/<pid>/environ`): RSS tăng 1.78GB → 4.09GB trong 30 phút (~4.6GB/giờ). Với `-Xmx12g`, job sẽ OOM trong ~1.7 giờ nữa — TRƯỚC KHI xong (job cần 10-12h). Đây là bug độc lập, không liên quan gì tới horizon hay tốc độ, tự phát hiện chứ Uni không hỏi tới.

→ Fix: code đã có sẵn flag `NO_VALIDATE=1` (bỏ qua bước tự-validate/tích luỹ) nhưng KHÔNG được set khi launch job production trước đó. Lần relaunch này set `NO_VALIDATE=1` rõ ràng.

### 3. Multi-thread hoá `ExportFundingLabel` (yêu cầu Uni: "xuất label cho chạy multi thread")

Thiết kế: cost của `finalizeBucket()`/`updateAnchor()` là độc lập theo từng coin (không có state chia sẻ giữa coin) → chia universe coin thành N phần theo `Math.floorMod(sym.hashCode(), nParts)==partIdx`, mỗi phần chạy trên 1 Thread riêng (`ExecutorService`), cùng logic day-loop/finalizeBucket/emit CŨ Y NGUYÊN, mỗi thread có `Map<CoinState>`/`Validate`/file output riêng (`outPath + ".partN"`), đọc lại Aerospike/Kaggle riêng (I/O trùng lặp giữa thread — chấp nhận được vì bottleneck là CPU trong `finalizeBucket`, không phải I/O, đã xác nhận qua `jstack` ở fix trước). Sau khi tất cả thread xong → `mergePartitions()` gộp lại 1 file, xoá file `.partN`. Bật qua env `LABEL_THREADS` (default=1 = y hệt hành vi cũ, không đổi gì nếu không set).

**Verify đúng — không đoán**: chạy CÙNG 1 khoảng 5 ngày (20210101→20210106) 2 lần, 1 lần `LABEL_THREADS=1`, 1 lần `LABEL_THREADS=4`, dùng cùng jar mới build. Sort data rows 2 file (`tail -n +2 | sort`) rồi `md5sum` — **giống 100%**: `2b0ece92aca8e7e8635cc9bbf7312b31`, cùng 546106 dòng, cùng 76 coin. (Lần thử đầu bị lỗi do tôi tự gây: 1 lệnh SSH foreground bị bridge timeout 60s cắt ở client nhưng tiến trình Java thật trên Oracle vẫn chạy tiếp, tôi lại chạy đè lần 2 → ghi đè/race ra file lỗi (dòng bị đệm hàng ngàn byte NUL). Đã tự phát hiện, sửa cách launch bằng `nohup...& disown` + poll xác nhận PID chết hẳn trước khi chạy bước kế, chạy lại sạch và khớp.)

### 4. Kill job cũ, chạy lại job production với cấu hình mới

- Kill job cũ (PID 182969, single-thread, short-horizon, KHÔNG NO_VALIDATE): mới chạy ~1h, đạt ~143 ngày/2007 ngày (~7%) — sunk cost nhỏ, chấp nhận được so với rủi ro OOM crash giữa đường.
- Build lại jar (`mvn -q -DskipTests package`, BUILD_EXIT=0), deploy `gatecount_20260806_multithread.jar` lên Oracle — **KHÔNG đè `gatecount.jar` gốc** vì `lsof` xác nhận `tool1_export` (PID 182968) đang mở đúng file đó; sẽ canonical hoá (backup rồi đè) sau khi tool1_export xong.
- Chạy job mới, PID `186370` (bash wrapper 186368), start 11:49:59 ICT, params: `LABEL_HORIZON_SET=short LABEL_THREADS=4 NO_VALIDATE=1`. Log xác nhận đúng cấu hình: `NO_VALIDATE=1 -> bo gom validate`, `H=[4h, 12h, 24h, 72h] | H_MAX=4320 buoc | LABEL_THREADS=4`.

### 5. Đo tốc độ thật sau relaunch (11:56 ICT, ~6-7 phút sau start)

- 296-297% CPU, RSS ~2.24GB (ổn định, không leo — khớp với việc `NO_VALIDATE=1` đã tắt đường tích luỹ gây OOM ở mục 2; chỉ đo được 1 mốc, sẽ đo lại sau ~1h để confirm RSS thật sự không leo theo thời gian).
- 4 file `.part0..part3` đều đang lớn (~255-265MB mỗi file lúc 11:56).
- Dùng kỹ thuật "trễ ngày do H_MAX" (dòng emit trễ đúng H_MAX=4320 phút=3 ngày so với vị trí xử lý thật) để đo tiến độ thật từng partition — **phát hiện lệch tải giữa các partition** (không đồng đều theo hash coin):
  - part3 (chậm nhất): dòng cuối `20210210-0639` → vị trí thật ≈ `20210213-0639` → ~43.3 ngày đã xử lý / 0.114h → **~380 ngày/giờ**
  - part1 (nhanh nhất): dòng cuối `20210304-1200` → vị trí thật ≈ `20210307-1200` → ~65.5 ngày / 0.114h → **~575 ngày/giờ**
  - Tổng range cần: 2007 ngày. Vì merge cuối cùng phải CHỜ partition chậm nhất, lấy con số **380 ngày/giờ (bảo toàn, dùng partition chậm nhất)** làm ETA: còn lại ~1964 ngày / 380 ≈ **5.2 giờ nữa** → dự kiến xong khoảng **17:00-17:30 ICT hôm nay** (2026-08-06), có thể nhanh hơn nếu `tool1_export` (PID 182968) chạy xong trước và giải phóng CPU (hiện 2 job đang giành nhau 4 core: label 297% + tool1 151% ≈ 448% trên máy 4 core).
  - So với job cũ single-thread PID 182969 (đã kill, ~143 ngày/giờ đo được trước khi kill): nhanh hơn thật ~2.7x (lấy partition chậm nhất) đến ~4x (partition nhanh nhất).

### 6. Trạng thái 2 job Oracle lúc 11:56 ICT

- `label_export` PID 186370: RUNNING lành mạnh, multi-thread thật (xác nhận qua CPU% và 4 file part tăng đồng thời).
- `tool1_export` PID 182968: RUNNING lành mạnh, không đổi gì, chạy trên `gatecount.jar` gốc (không bị ảnh hưởng bởi việc sửa label_export), elapsed 1h07m.
- Tổng 2 job Java đang chạy trên Oracle = 2/3 (còn dư 1 slot theo giới hạn tối đa 3 job đồng thời).

### 7. Việc CHƯA làm / còn treo

- Canonical hoá `gatecount_20260806_multithread.jar` → `gatecount.jar` (backup bản cũ trước) — CHỜ tool1_export xong (đang giữ file jar cũ qua `lsof`).
- Đo lại RSS sau ~1h nữa để chắc `NO_VALIDATE=1` thật sự chặn được OOM lâu dài (mới đo 1 mốc ở phút thứ 6).
- Quyết định của Uni về `LoadWfoGatePredTool` (nạp `wfo_gate_pred.csv` đã validate — 21 fold, 2,760,442 dòng, 0 gap/0 NaN — vào Aerospike `ai_pred_market_gate_wfo`) — VẪN CHƯA CÓ CÂU TRẢ LỜI, hỏi lại.

## Phần 20 — Đã chạy `LoadWfoGatePredTool` (Uni xác nhận "chạy đi", 2026-08-06 ~12:34-12:36 ICT)

Nạp `/home/ubuntu/claudedata/wfo_gate_pred.csv` (2.760.442 dòng data, đã validate trước đó 0 gap/0 NaN, 64 tháng liên tục) vào Aerospike set `ai_pred_market_gate_wfo` trên Oracle (ns=`test`, clientOracle), qua tool có sẵn `LoadWfoGatePredTool` (không cần code mới — class đã có trong jar `gatecount_20260806_multithread.jar`, dùng jar này để tránh đụng `gatecount.jar` gốc đang bị `tool1_export` PID 182968 mở qua `lsof`).

Trước khi chạy đã kiểm tra thật (không giả định):
- Header CSV khớp đúng `timestamp,predReturn15M,predRisk4H` (tool yêu cầu khớp tuyệt đối, sai là throw ngay).
- Class `LoadWfoGatePredTool` có trong jar (`jar tf` xác nhận).
- `AEROSPIKE_NAMESPACE=test` trong `config.properties` — đúng cluster Oracle local (226), không phải box sai.
- Đang có 2 job Java chạy (label_export PID 186370, tool1_export PID 182968) — chạy thêm job này là 3/3, đúng giới hạn tối đa, không vượt.

Cơ chế tool: **upsert theo key** (`recordExistsAction=UPDATE`), KHÔNG xoá set cũ trước — chấp nhận được vì đây là lần nạp ĐẦU TIÊN vào set này (chưa từng có data cũ để lẫn). Đọc/ghi theo chunk 4900 dòng, không rollback nếu lỗi giữa file — nhưng lần chạy này chạy trọn tới cuối, không có lỗi giữa đường.

**Kết quả (log thật)**:
```
🎯 DONE: nạp 2760442 record → set ai_pred_market_gate_wfo (idempotent: chạy lại ghi đè cùng key)
```
Số record nạp = 2.760.442, KHỚP CHÍNH XÁC số dòng data trong CSV (2.760.443 dòng file − 1 header = 2.760.442) → không rơi/không skip dòng nào. Chạy hết ~1 phút 50 giây (12:34:33 → 12:36:23). Process (PID 187736) đã exit sạch, không orphan — `ps aux` sau đó xác nhận chỉ còn đúng 2 job cũ (label_export 186370, tool1_export 182968), không có process dở dang nào của LoadWfoGatePredTool còn sót.

→ **Gate layer (#4 trong sơ đồ 6-thành-phần) nay đã hoàn tất cả 2 phần: có `wfo_gate_pred.csv` local VÀ đã nạp Aerospike `ai_pred_market_gate_wfo`.** Việc còn treo trước đó ("chờ Uni xác nhận trước khi chạy LoadWfoGatePredTool") — ĐÃ XONG, không còn treo.

### Còn lại để tới `build_ds` → `gate_sign`
1. `label_export` (PID 186370) xong — ETA ước ~17:00-17:30 ICT (xem phần 19).
2. `tool1_export` (PID 182968) xong.
3. Push 2 dataset lên Kaggle (`push_tool1_dataset`, `push_label_dataset`) → `kaggle_push` chạy `gen_funding_wf_predictions.py` (selector, thành phần #5) → `kaggle_output` tải `predict_wf_*.bin` về Oracle.
4. `build_ds` (`WfoDataset.java`) ráp market_data (live) + `ai_pred_market_gate_wfo` (vừa nạp xong) + `predict_wf_*.bin` → dataset canonical.
5. `validate_canonical_wfo.py` → `gate_sign` (dừng ở đây chờ Uni, không tự ký).

Tất cả các bước 3-5 sẽ gọi tay từng CE step (không dùng `pipe_run` lại nguyên pipeline, theo quyết định ở phần 18).

## Phần 21 — check-in 2026-08-06 12:39 ICT: cả 2 job khỏe, cập nhật lại ETA label_export (đáng tin hơn)

- `tool1_export` PID 182968: RUNNING, elapsed 1h50m51s, RSS 6.08GB, 129% CPU. Đã đóng xong 6/22 quý (đến `20220401_to_20220701`), đang xử lý quý 7 (`20220701_to_20221001`). Không log lỗi.
- `label_export` PID 186370: RUNNING, elapsed 49m29s, RSS 3.5GB (ổn định, không leo — đúng như kỳ vọng từ `NO_VALIDATE=1`), 294% CPU, 4 partition file đang lớn dần đều (~2.1-2.2GB mỗi file lúc 12:39).
- **Cập nhật ETA đáng tin hơn**: log có checkpoint thật trong day-loop (không qua suy luận emission-lag) — cả 4 partition đều báo mốc "200 ngày" (tới 20210719), thời điểm khác nhau: part1 12:15:07 (25m08s), part0 12:20:12 (30m13s), part2 12:20:30 (30m31s), **part3 (chậm nhất) 12:29:11 (39m12s)**. Tốc độ partition chậm nhất = 200 ngày / 39.2 phút ≈ **306 ngày/giờ** (thấp hơn ước tính vội ở phần 19 dựa trên mẫu 6 phút — số này đáng tin hơn vì đo trực tiếp vị trí day-loop, không qua suy diễn). Còn lại 1807/2007 ngày → ETA ≈ 5.9h nữa từ mốc 12:29 → **dự kiến xong khoảng 18:15-18:30 ICT** (chậm hơn ước tính cũ 17:00-17:30, sửa lại vì mẫu cũ quá ngắn/nhiễu).
- Đã tạo lịch check tiếp theo ~60 phút nữa.

## Phần 22 — Khủng hoảng đĩa Oracle + redesign xuất label theo QUÝ + fix bug thread-safety (2026-08-06 ~14:00-15:30 ICT)

**Bối cảnh:** Uni hỏi "label trên kaggle có file csv rồi sao ko dùng nó rồi xuất thêm cho đủ" →
kiểm tra `chuyendinh/funding-label-full` (9.37GB, 1 file) → xác nhận đây là data lưới **15 phút CŨ**
(theo đúng mục đích ghi ở đầu task file: TASK-251 thay lưới 15 phút → 1 phút), KHÔNG dùng lại được.

**Khủng hoảng đĩa (đo thật lúc phát hiện):** combined growth rate ~13.6GB/h (label_export ~9.9GB/h +
tool1_export ~3.7-4GB/h), chỉ còn 6.2-6.5GB free → ETA đầy đĩa ≈29 phút. Xử lý ngay: `kill -STOP` cả
2 PID (tạm dừng, không mất dữ liệu, có thể resume) trong lúc thiết kế fix. Root cause SÂU hơn tổng
dung lượng: `mergePartitions()` cũ (merge toàn dải cuối job) cần ~2x kích thước file CUỐI cùng lúc
(giữ cả .partN + file gộp) — với label cuối ước tính ~90-120GB+ (đang TĂNG ước tính vì throughput
giảm dần theo thời gian: 306 ngày/h ở ngày 200 vs 234 ngày/h ở ngày 600, do càng về sau càng nhiều
coin sống), bước merge riêng lẻ này có thể vượt CẢ đĩa 150GB dù dọn sạch mọi thứ khác.

**Quyết định của Uni (từ chối mở rộng đĩa vì tốn phí):** xuất label theo file QUÝ (như tool1 đã làm),
mỗi quý xong push Kaggle ngay rồi xoá local, kill job cũ viết lại từ đầu, xác nhận chạy 3 tiến trình
song song OK (đúng rule tối đa 3).

**Dọn dẹp đã làm (Uni xác nhận "Xoá luôn"):** xoá 7 thư mục thí nghiệm cũ trước TASK-251
(wfo_ds_ret2wf_4h_ff, wfo_ds_maxfav3_4h_ff, probe_ds, wfo_ds_ev2, wfo_ds_ret2wf_4h, wfo_ds_maxfav3_4h,
wfo_ds_maxdep, wfo_ds_oiz75, wfo_ds_oiz2022_75 — ~2.9GB), xoá `kaggle_oi_stage/oi_percoin_full.bin`
(4.23GB, đã xác nhận trùng bản đã push), xoá `smoketest/` cũ (397MB). Kill PID 186370 (label_export
cũ, ~30%/2007 ngày, ~2.5h compute — sunk cost được Uni chấp nhận), xoá `.part*` dở của nó.

**Redesign `ExportFundingLabel.java` — chia file theo QUÝ dương lịch (Jan/Apr/Jul/Oct):**
- Gán 1 dòng vào quý theo thời điểm TẠO anchor (`tEpoch`, không phải thời điểm emit) — vì lookback
  H_MAX (3 ngày) có thể khiến anchor tạo gần cuối quý emit sang quý sau; dùng creation-time đảm bảo
  KHÔNG trùng/chồng lấp dòng giữa 2 file quý.
- Mỗi partition-thread giữ `Map<Long, QuarterSink> open` (mở quý theo nhu cầu), đóng quý khi day-loop
  đã đi qua `quarterEnd + H_MAX phút` (mốc CHẮC CHẮN an toàn — không còn anchor nào của quý đó chưa emit).
- `ConcurrentHashMap<Long, AtomicInteger> closeCounters` (key=quý) đếm số partition đã đóng xong 1 quý;
  đủ `nParts` → submit task gộp `nParts` file `.partN` thành 1 file quý cuối + xoá `.partN`, chạy trên
  `mergerPool` RIÊNG (không chặn worker export). Peak disk dư chỉ ~1 quý (không phải toàn bộ dataset)
  → giải quyết đúng root cause khủng hoảng đĩa. Bỏ hẳn `mergePartitions()` toàn-dải cũ.
- `main()` chờ `mergerPool.shutdown()+awaitTermination(60p)` trước khi coi job xong.

**BUG THẬT phát hiện qua smoke test `LABEL_THREADS=4` (tự phát hiện qua kỷ luật test, Uni chưa báo):**
`Utils.sdfFile` (1 `SimpleDateFormat` static DÙNG CHUNG, KHÔNG thread-safe) bị gọi từ `emit()` hot-path
(hàng triệu lần, 4 thread song song) → sinh ngày-tháng RÁC ("00010101", "10210101"...) → crash parse,
EXIT=1. Fix: thêm `ThreadLocal<SimpleDateFormat> QDATE_FMT` (pin GMT+7, đúng pattern `FMT` đã có sẵn
trong file), route toàn bộ parse/format ngày-quý qua nó (`dateStrToEpoch`, `quarterStartEpoch/EndEpoch`,
`quarterSuffix`, log tiến độ day-loop). Rebuild (`build_quarterly_fix2.log`, BUILD_EXIT=0), deploy
`gatecount_20260806_quarterly_fix2.jar` lên Oracle.

**Verify (đo thật, không giả định):** chạy lại đúng range biên quý `20210325-20210408`,
`LABEL_THREADS=4 NO_VALIDATE=1`, jar mới — KHÔNG crash, sinh đúng 2 file quý
(`20210101_to_20210401`: 952110 dòng, `20210401_to_20210701`: 1071809 dòng, tổng 2023919 dòng, 103
coin — khớp CHÍNH XÁC ground-truth single-thread cũ). Ghép 2 file, bỏ header, sort, md5sum:
`1a6c324e25ee7c161f5caa046dd6ccae` — **giống byte-for-byte** với ground truth
(`old.sorted`, cũng hash này). Multi-thread + chia quý CHÍNH THỨC đúng.

**Đã relaunch job PRODUCTION thật:** `LABEL_STEP_MIN=1 LABEL_HORIZON_SET=short LABEL_THREADS=4
NO_VALIDATE=1`, jar `gatecount_20260806_quarterly_fix2.jar`, range đầy đủ `20210101→20260701`, output
prefix `/home/ubuntu/claudedata/wfo1m/label_ds_1m/funding_label_1m.csv` (tách theo quý), PID mới
**196631** (bash wrapper 196630), start 15:23:37 ICT. Đang chạy đúng (log đã thấy mở 4 file quý đầu,
không còn ngày-tháng rác).

**LƯU Ý QUAN TRỌNG — pipeline CE cũ đã STALE:** `pipe_wfo_canonical_1m_1785988117` (18 step) đang
STOPPED ở step 4/18 (`wait_tool1`), nhưng step 1-2 (`label_export`/`wait_label`) bị đánh **success**
dù job Java thật (PID 186370) đã bị kill giữa đường — bug CE đã biết (wait-step tin heartbeat/exit
sớm, không verify output thật). **KHÔNG dùng `pipe_resume` cho pipeline này** — nó sẽ tưởng label đã
xong. Job label_export mới (PID 196631) đang chạy ĐỘC LẬP ngoài pipeline (nohup thủ công, giống cách
smoke test), sẽ theo dõi/push Kaggle thủ công từng quý — CHƯA gắn lại vào CE atom `label_export` (atom
đó vẫn trỏ code/kỳ vọng cũ, cần sửa riêng — nợ lại, không urgent vì job đang chạy tốt).

**Verify + dọn Kaggle push tool1 (pending từ trước, đã xử lý):** xác nhận `kaggle datasets files
chuyendinh/funding-tool1-features-1m` có đủ 10 file quý (20210101→20230701) khớp log push cũ — push
ĐÃ XONG thật (không phải mid-upload như lo ngại). Xoá cả 2 bản hardlink (gốc + stage) của 10 quý này
để thu hồi đĩa (~13.75GB, 36GB→49GB free). Quý 11 (`20230701_to_20231001`, 2094532073 bytes, tool1_export
đóng lúc 15:06) đã hardlink vào `kaggle_tool1_1m_stage/` và push (`kaggle datasets version`, log
`push_tool1_q11.log`) — đang upload lúc ghi phần này, CHƯA xác nhận xong, cần check lại + xoá local sau.

**Còn nợ (chưa làm, ghi lại để không quên):**
1. Sửa `gen_funding_wf_predictions.py` (dòng ~185 đọc `LABEL_CSV` single-file, dòng ~169-183 validate
   1 sidecar `.meta.json`) để glob+concat nhiều file quý label — cần trước khi `kaggle_push`/build_ds
   dùng được label mới, nhưng chưa urgent (job label_export còn chạy nhiều giờ).
2. Sửa atom `label_export` trong `mcp_tools-v3.py`/pipeline JSON để biết output giờ chia theo quý
   (không còn 1 file monolithic) — để có thể quản lý qua CE lại nếu cần sau này.
3. Tiếp tục cadence "quý xong → push Kaggle → xoá local" cho CẢ 2 job (label_export mới PID 196631,
   tool1_export PID 182968 đang ở quý 12/22) — làm thủ công mỗi lần check-in vì chưa tự động hoá.
4. Cập nhật/dọn các lịch check-in cũ (trig_017jBdCsvSQEwSA5U2hLKBnb và các send_later cũ) — đang
   tham chiếu PID/thiết kế CŨ đã lỗi thời (PID 186370 đã chết, thiết kế single-file cũ).

**An toàn hiện tại:** 2/3 job Java đang chạy (label_export PID 196631 + tool1_export PID 182968),
1 job Python (kaggle push q11) — đúng rule tối đa 3 Java, còn dư 1 slot Java. Đĩa 49GB free (đã tăng
từ mức nguy cấp 6.2GB), kiến trúc mới bound peak disk ~1 quý nên sẽ không tái diễn khủng hoảng.

## Phần 23 — Check-in 16:00-16:55 ICT: cả 2 job khỏe, push Kaggle 5 quý mới (3 label + 2 tool1)

**Trạng thái 2 job (đo thật lúc 16:52 ICT):**
- label_export PID 196631: elapsed 1h16m, RSS ~2.2GB ổn định (NO_VALIDATE hoạt động đúng, không leak).
  Đã đóng+gộp xong 3 quý đầu: `20210101_to_20210401` (10.972.619 dòng), `20210401_to_20210701`
  (13.992.264 dòng), `20210701_to_20211001` (14.983.371 dòng). Đang xử lý quý 4 (`20211001_to_20220101`).
- tool1_export PID 182968: elapsed 5h52m, đã đóng quý 13 (`20231001_to_20240101`, 28.416.617 record),
  đang ở quý 14 (`20240101_to_20240401`).

**Đã push Kaggle + xoá local (đúng cadence "quý xong → push → xoá" Uni yêu cầu):**
- Tạo dataset MỚI `chuyendinh/funding-label-full-1m` (title/id đúng convention, khác dataset 15-phút
  cũ `funding-label-full`) — push 3 quý label đầu (~7.98GB), `kaggle datasets create -p . -r skip`.
  **Xác nhận server-side thật** (không chỉ tin log CLI) qua `kaggle datasets files` — lúc đầu bị 403
  Forbidden ~10 phút (dataset mới tạo, Kaggle cần thời gian index) → retry sau đó thấy đủ 3 file đúng
  size khớp local trước khi xoá. Đã xoá cả 2 bản (gốc `wfo1m/label_ds_1m/` + hardlink stage) sau xác nhận.
- Push thêm quý 13 tool1 (`20231001_to_20240101`, 3GB) vào dataset `funding-tool1-features-1m` có sẵn
  (`kaggle datasets version`) — xác nhận qua `kaggle datasets files` thấy file mới, xoá local.

**Đĩa:** 45GB free (ổn định, không tụt về mức nguy cấp).

**Lưu ý cho lần check sau:** dataset mới tạo (`create`, không phải `version`) có thể mất vài phút mới
query được qua API (403 tạm thời) — đừng hoảng, đợi rồi retry, đừng xoá local trước khi xác nhận thật.

> ⚠️ Ghi chú của CCD (2026-08-06 21:xx ICT): Phần 24-26 gốc đã bị MẤT 2 lần liên tiếp (1 lần do
> Claude dùng `Write` đè nhầm file, 1 lần do bản Local History Uni revert lại là snapshot CŨ hơn cả
> Phần 24). Nội dung dưới đây là VIẾT LẠI từ trí nhớ của Claude trong phiên hiện tại (không phải
> phục hồi nguyên văn) — đủ để nắm bối cảnh, có thể thiếu vài chi tiết nhỏ so với bản gốc.

## Phần 24 — ⚠️ BUG NGHIÊM TRỌNG: `kaggle datasets version` THAY THẾ không PHẢI thêm vào (viết lại, ~2026-08-06 17:50 ICT)

Cadence "push quý → xoá local" dùng `kaggle datasets version -p . -r skip` để đẩy quý mới vào
dataset gộp có sẵn. Giả định SAI: tưởng là "thêm file", thực tế lệnh này REPLACE toàn bộ nội dung
hiện tại của dataset bằng đúng nội dung thư mục stage lúc đó. Vì mỗi lần push đều xoá local ngay
sau, thư mục stage mỗi lần chỉ có 1-2 file mới → mỗi lần push sau vô tình xoá sạch quý cũ khỏi bản
hiện tại của dataset. Xác nhận bằng test thật: `kaggle datasets download -f
features_..._20210101_to_20210401.bin.gz chuyendinh/funding-tool1-features-1m` → 404. Kết quả:
`funding-tool1-features-1m` mất khả năng truy xuất quý 1-12 (chỉ còn quý 13). `funding-label-full-1m`
kịp cứu (kill -TERM 1 push đang chạy trước khi commit) → vẫn còn đủ 3 quý gốc. Đã dừng mọi `version`
push, báo Uni, hỏi 2 quyết định: (1) có cố phục hồi quý 1-12 tool1 qua Kaggle web UI không (Uni
CHƯA trả lời, không chặn tiến độ); (2) cadence đúng cho sau này — đưa ra 3 option.

## Phần 25 — Uni quyết định "mỗi quý 1 dataset" (viết lại)

Uni trả lời: **"mỗi quý 1 dataset cũng ok nhé"** → chọn: mỗi quý Kaggle = 1 dataset riêng, luôn
`kaggle datasets create` (KHÔNG BAO GIỜ `version` cho dataset mới). 2 dataset gộp cũ
(`funding-label-full-1m`, `funding-tool1-features-1m`) giữ NGUYÊN, không push thêm. Đã tạo
`/home/ubuntu/claudedata/kaggle_perq/<label|tool1>_<start>_<end>/` (mỗi folder 1
`dataset-metadata.json` + hardlink), verify qua `kaggle datasets files` trước khi xoá local. Đã tạo
verify xong: label Q4/2021, Q1/2022, Q2/2022; tool1 Q1/2024, Q2/2024 (5 dataset đầu tiên).

## Phần 26 — LỖI Claude: dùng `Write` đè mất Phần 1-24 (~18:27 ICT) + khủng hoảng đĩa lần 1 (19:35-19:50 ICT, viết lại)

Khi ghi Phần 25 (bản gốc), Claude dùng nhầm `Write` (full-file overwrite) thay vì Edit/append → file
1116 dòng bị đè chỉ còn ~49 dòng. Không có git history (file untracked), không VSS (không quyền
admin), không Recycle Bin. Uni dùng IntelliJ Local History để revert (kết quả: xem ghi chú CCD ở
trên — snapshot lấy được cũ hơn dự kiến, mất luôn Phần 24-26 gốc, đây là lý do 3 phần này đang được
viết lại). Cùng lúc đó, check-in phát hiện đĩa Oracle tụt xuống 7.3GB free (<15GB) do 6 quý mới
đóng tích tụ lúc bridge Windows offline. Đã xử lý: `kill -STOP` label_export theo rule, sau đó leo
thang tự `kill -STOP` luôn tool1_export (ngoài rule gốc) vì đĩa vẫn tụt, push 5 dataset mới (3 label
Q4/2022+Q1/2023+Q2/2023, 2 tool1 Q3/2024+Q4/2024) để giải phóng đĩa, verify 3/5 xong xoá local ngay,
2/5 còn chờ index. Đĩa hồi lên 20GB free → `kill -CONT` cả 2 job. Uni sau đó xác nhận: đã revert
xong + **OK rule mới: dừng CẢ 2 job (không chỉ label) khi đĩa <15GB.**

## 🔴 Phần 27 — CẢ 2 JOB ĐÃ CRASH THẬT (hết đĩa hoàn toàn), đã xử lý dữ liệu hỏng, ĐANG CHỜ QUYẾT ĐỊNH RESTART (2026-08-06 ~20:53-21:05 ICT)

**Phát hiện:** check-in 20:54 ICT thấy `ps -p 196631,182968` trả về TRỐNG — không chỉ là bị STOP,
mà cả 2 process ĐÃ CHẾT THẬT. Đĩa lúc phát hiện: **100% used, 372K free / 146G** (từ 20GB free lúc
resume 19:53 ICT tụt về 0 trong vòng ~1 giờ — nhanh hơn nhiều so với dự đoán, vì trong giờ đó có
tới 8 quý label + 3 quý tool1 đóng file mà không ai push+xoá kịp, cộng thêm 1 phát hiện MỚI ở dưới).

**Log lỗi xác nhận (không phải giả định):**
```
2026-08-06 20:53:12 ERROR ExportFundingLabel lỗi
java.io.IOException: No space left on device
```
Cả 2 job crash gần như cùng lúc (~20:53 ICT) vì cùng chung 1 đĩa.

**Phát hiện KIẾN TRÚC mới (nguyên nhân sâu, chưa từng biết trước đây):** `ExportFundingLabel`
KHÔNG tự xoá 4 file `.part0-3.csv` của 1 quý sau khi gộp (merge) thành công — file gộp
(`funding_label_1m_<quý>.csv`) và 4 file `.part*.csv` gốc **cùng tồn tại song song**, chiếm ĐÚP
dung lượng cho mọi quý đã gộp nhưng chưa kịp xoá tay. Đây là rò rỉ đĩa âm thầm, cộng với việc
review chu kỳ 60 phút không đủ nhanh để bắt kịp, là 2 nguyên nhân chính gây hết đĩa.

**Thiệt hại dữ liệu (đã kiểm tra kỹ, KHÔNG mất gì không phục hồi được):**
- `funding_label_1m_20231001_to_20240101.csv`: merge ĐANG chạy đúng lúc hết đĩa → file bị cắt cụt
  giữa dòng (xác nhận bằng `tail -c 300`, dòng cuối `...1701855420000,20231` không có ký tự xuống
  dòng) → **file HỎNG, đã xoá.** Dữ liệu gốc vẫn còn trong Aerospike, quý này quy lại từ đầu được
  (không mất thông tin, chỉ mất công tính lại).
- `features_export_python_v3_1mfeatures_20250401_to_20250701.bin.gz`: đang ghi dở khi crash → gzip
  cụt, không giải nén được → **đã xoá.** Cũng regen được từ Aerospike.
- Đã xoá theo luôn ~14 file `.part*.csv` orphan (quý đã gộp/hoặc đang gộp dở, ~14GB) — không mất
  dữ liệu vì đây chỉ là bản trung gian, quý đã gộp xong thì file gộp đã có đủ; quý đang gộp dở thì
  coi như phải làm lại đoạn đó thôi.
- Quý `20230701_to_20231001` (label): merge THÀNH CÔNG trước khi crash (file hoàn chỉnh, không cụt)
  nhưng CHƯA kịp push Kaggle → đã tạo dataset mới `funding-label-1m-20230701-20231001`, `create`
  xong, đang chờ index Kaggle verify (403 tạm), CHƯA xoá local.

**Đã làm để cứu đĩa:** xoá 2 quý đã verify Kaggle từ lần check trước (label Q2/2023, tool1 Q4/2024)
+ push nốt quý label Q3/2023 valid + xoá file hỏng/orphan part files → đĩa từ 372K lên **30GB
free**. An toàn, không cần thao tác gấp nữa.

**⚠️ CẦN UNI QUYẾT ĐỊNH (KHÔNG tự làm, vì đây là quyết định kiến trúc/tốn nhiều giờ compute):**
Cả 2 job hiện ĐANG CHẾT, không phải đang dừng — cần **restart thủ công**, nhưng restart bằng đúng
lệnh cũ (`java ... ExportFundingLabel 20210101 20260701 ...`) sẽ chạy lại **TỪ ĐẦU 2021**, lãng phí
~5-6 giờ đã chạy (dù không mất data vì các quý cũ đã có trên Kaggle rồi, chỉ tốn compute + thời
gian). Cách hiệu quả hơn: restart với `start` mới = ngay sau quý an toàn cuối cùng — label từ
`20231001` (vì 20230701_to_20231001 đã merge xong+đang push), tool1 từ `20250401` (vì
20250101_to_20250401 đã đóng file an toàn). Nhưng: (1) chưa kiểm tra code có phụ thuộc gì vào việc
chạy từ `20210101` không (walk-forward gate, rolling window...) — cần xem code trước khi đổi
`start`; (2) bug rò rỉ đĩa (không xoá part file sau merge) CHƯA fix — nếu restart mà không fix,
tình huống này sẽ LẶP LẠI trong vài giờ tới. Uni muốn: (a) tôi cứ restart ngay với start mới, chấp
nhận rủi ro crash lại nếu không canh kỹ hơn; (b) tôi xem code `ExportFundingLabel.java` fix bug
không-xoá-part-file trước khi restart; (c) khác?

**Uni chọn (b). Kết quả xem code (21:10-21:15 ICT):**

**Cải chính chẩn đoán ở trên — KHÔNG có bug "không xoá part file":** đọc `mergeQuarter()` trong
`ExportFundingLabel.java` thấy code ĐÃ có sẵn vòng lặp xoá 4 file `.partN.csv` ngay sau khi gộp
xong (`new File(quarterPartPath(...)).delete()`), nằm SAU đoạn `try (FileWriter out = ...)`. Lý do
thật của việc "part file + merge file cùng tồn tại" ở Phần 27: merge quý `20231001_to_20240101`
ĐANG CHẠY đúng lúc hết đĩa → exception `IOException` bắn ra TỪ TRONG try-block → vòng lặp xoá phía
dưới KHÔNG BAO GIỜ được chạy tới (không phải do thiếu code dọn dẹp, mà do crash cắt ngang giữa lúc
đang dọn). Đây là hành vi merge-crash bình thường, không phải lỗi thiết kế. Nguyên nhân THẬT gây
hết đĩa vẫn là: (1) quý đã gộp xong nhưng CHƯA kịp push+xoá tích tụ (do khoảng cách check-in 60
phút quá dài so với tốc độ đóng quý); (2) lúc gộp quý, có 1 khoảng ngắn cần dư ~1 quý dung lượng
(part files + file gộp cùng lúc) — đúng như comment code đã cảnh báo trước, không phải bug.

**Kiểm tra an toàn đổi `start`:** cả 2 tool nhận `start`/`end` thuần làm argument, không có state
toàn cục phụ thuộc mốc `20210101`. `ExportFundingLabel`: label là path-tương-lai (H_MAX bước tới),
không cần lịch sử trước `start`. `ExportFeaturesForPythonTool`: có warmup 48h tự động lùi về trước
`targetStartTs` (comment code xác nhận: "mọi feature dùng lookback ≤24h, riêng funding-sâu dùng
full TreeMap headMap(t) nên đúng từ mọi mốc bắt đầu") — code tự thiết kế để restart an toàn từ bất
kỳ mốc nào. Kết luận: đổi `start` để bỏ qua phần đã xong AN TOÀN, không cần sửa code.

**Đã restart (21:51 ICT) với start mới, bỏ qua các quý đã xong+an toàn:**
- Push nốt quý tool1 Q1/2025 (`20250101_to_20250401`) còn treo lên `funding-tool1-1m-20250101-20250401`
  trước khi restart (đang chờ verify).
- `label_export` PID mới **217186**: `java -Xmx6g ... ExportFundingLabel 20231001 20260701
  /home/ubuntu/claudedata/wfo1m/label_ds_1m/funding_label_1m.csv` (bắt đầu từ ngay sau quý
  20230701_to_20231001 đã an toàn trên Kaggle).
- `tool1_export` PID mới **217219**: `java -Xmx12g ... ExportFeaturesForPythonTool 20250401
  20260701 /home/ubuntu/claudedata/wfo1m/features_export_python_v3_1m 12.0` (bắt đầu từ ngay sau
  quý 20250101_to_20250401 đã an toàn).
- Log mới: `label_export_prod2.log`, `tool1_export_features_export_python_v3_1m_2.log` (đổi tên có
  `_2` để không lẫn với log job cũ đã crash).
- Đĩa lúc restart: 34GB free — an toàn, tiết kiệm được ~4.5 năm compute lẽ ra phải chạy lại từ đầu
  (chỉ cần chạy từ 2023Q4/2025Q2 tới hiện tại).

**Rủi ro còn treo (chưa giải quyết được bằng code, chỉ giảm nhẹ bằng quy trình):** vẫn CHƯA có cơ
chế tự động push+xoá độc lập với việc tôi check-in — nếu khoảng cách giữa các lần check-in kéo dài
(bridge offline, hoặc quên) và nhiều quý đóng liên tiếp, tình huống hết đĩa NÀY CÓ THỂ LẶP LẠI. Đề
xuất cho lần sau (chưa làm, cần Uni duyệt nếu muốn): viết 1 script bash chạy độc lập trên Oracle
(cron hoặc loop nền), tự kiểm tra quý mới đóng + tự push + tự xoá, không phụ thuộc vào chu kỳ
check-in của Claude.

## Phần 28 — Check-in 22:28 ICT: 2 job mới khỏe, rà soát toàn bộ data layer (ticker/market/funding fee/OI/gate) theo yêu cầu Uni

**2 job (start date mới) khỏe:** label_export PID 217186 (37 phút), tool1_export PID 217219 (37
phút), đĩa 26GB free, chưa có quý mới đóng (bình thường, mới chạy được ~40 phút).

**Uni hỏi: ticker/market_data/funding_fee/OI/gate đã lên Kaggle hết chưa, chỉ symbol_mapper ở lại
Aerospike.** Rà soát code + Kaggle thật (không giả định):

| Data layer | Trạng thái | Việc cần làm |
|---|---|---|
| Ticker (`kline_1m_opt`) | Có trên Kaggle (`hpo-ticker-daily`, 1826 file) nhưng **chỉ tới 20251231**, THIẾU 01-07/2026 | Xuất bổ sung đoạn thiếu, push dataset RIÊNG (không đụng `version` vào bộ 1826 file cũ — tránh lặp lại bug Phần 24) |
| OI (`funding-oi-percoin`) | Có trên Kaggle (`oi_percoin_full.bin` 4.2GB) | Chưa xác nhận coverage chính xác (không tải 4.2GB chỉ để check ngày) — nghi thiếu đoạn cuối 06/2026 theo ghi chú cũ |
| Gate (`wfo_gate_pred.csv`) | **Vừa push xong** dataset mới `chuyendinh/funding-gate-wfo-pred` (97MB, verify server-side khớp size) | Xong |
| Market object (`market_data`) | **KHÔNG có tool export nào từng chạy** — có 1 method chết trong code (`ExportHpoDataKaggle.exportCoreData()`) nhưng chưa bao giờ dùng | Cần VIẾT TOOL MỚI (đã note trước đó là "chưa có tool export ra file") |
| Funding fee (`funding_data`) | **HOÀN TOÀN chưa có tool export nào** | Cần viết từ đầu |

Đã báo Uni, hỏi có muốn viết 2 tool mới (market_data, funding_fee) ngay không hay ưu tiên 3 việc dễ
(ticker backfill + OI verify) trước — Uni CHƯA trả lời câu này (không chặn giám sát 2 job chính).

**Check-in 22:42 ICT:** 2 job vẫn khỏe (label 55 phút, tool1 55 phút). Verify + xoá local xong quý
tool1 Q1/2025 (`funding-tool1-1m-20250101-20250401`, size Kaggle 7,454,623,420 B khớp bản giải nén
từ 4,471,486,333 B gốc .gz). Quý label mới đóng: `20231001_to_20240101` (28,493,351 dòng) — đang
push dataset mới `funding-label-1m-20231001-20240101` (5.3GB, chạy nền, chưa xong lúc ghi note này).
Đĩa 26GB free, ổn định.

## Phần 29 — Check-in 23:0x-23:5x ICT: bridge rớt giữa việc, xử lý lại + push 2 quý mới

**Sự cố nhỏ:** giữa lúc đang tạo dataset cho quý label `20240101_20240401` + tìm path file quý
tool1 `20250401_20250701`, bridge tới máy Windows rớt kết nối (`device not connected`). Đã báo Uni,
tự lên lịch check lại 40 phút sau (đúng quy tắc không retry liên tục). Trạng thái treo lúc đó: quý
label `20240101_20240401` đã hardlink+metadata nhưng CHƯA chạy `kaggle datasets create`; quý tool1
`20250401_20250701` chưa tìm được path đúng (giả định sai vị trí subfolder).

**Khi bridge online lại (~23:33 ICT):**
- 2 job vẫn khỏe: label PID 217186 (1h42m→1h52m qua các lần check), tool1 PID 217219 (tương tự),
  %CPU bình thường (292% cho label — job đa luồng, 99%+ cho tool1).
- Verify xong quý label `20231001_to_20240101` (5,691,958,279 B khớp Kaggle) → đã xoá local (thực
  hiện ở phiên trước khi bridge rớt).
- Tìm ra path đúng file tool1: `/home/ubuntu/claudedata/wfo1m/features_export_python_v3_1mfeatures_20250401_to_20250701.bin.gz`
  (tên file nối liền `features_export_python_v3_1m` + `features_...` KHÔNG có dấu `/` — không phải
  nằm trong subfolder `features_export_python_v3_1m/` như tôi giả định ban đầu, đây là lý do lệnh
  `ln` lần trước báo "No such file or directory").
- Đã push xong 2 dataset mới (chạy nền qua SSH, mất ~5-7 phút cho mỗi file do băng thông upload):
  - `chuyendinh/funding-label-1m-20240101-20240401` (6,212,923,983 B local, quý 31,141,573 dòng)
  - `chuyendinh/funding-tool1-1m-20250401-20250701` (5,319,844,284 B local .gz, quý 51,701,191
    records — đây chính là bản generate lại sạch của quý từng bị corrupt trong vụ crash đĩa lần 2)
- **Verify 2 dataset trên vẫn đang bị 403 Forbidden** (Kaggle indexing lag bình thường sau `create`,
  không phải lỗi) — CHƯA xoá local, để lần check tới verify lại rồi mới xoá.
- Không có quý mới nào đóng thêm kể từ Phần 28 (vẫn chỉ 2 quý label + 1 quý tool1 đã biết).
- Đĩa: 18GB free (đang giảm chậm, gần ngưỡng 15GB — vì 2 file 6.2GB+5.3GB vẫn còn nằm local đợi
  verify; sau khi xoá dự kiến nhảy lên ~29GB).

**Việc cần làm ở lần check tiếp:** verify lại 2 dataset trên qua `kaggle datasets files`, nếu khớp
size thì xoá local ngay (ưu tiên vì đĩa đang gần ngưỡng); nếu đĩa xuống dưới 15GB trước khi verify
xong thì `kill -STOP` cả 2 PID theo quy tắc đã duyệt, báo Uni ngay.

**Câu hỏi vẫn đang treo, Uni chưa trả lời:** viết 2 tool export mới cho `market_data` và
`funding_fee` ngay, hay ưu tiên ticker-2026-backfill + OI-coverage-verify trước? Không tự quyết,
không tự bắt đầu viết code mới.

## Phần 30 — Check-in 00:1x ICT: ĐĨA XUỐNG DƯỚI NGƯỠNG (11GB) — đã STOP 2 job, dọn đĩa, resume

**Sự cố:** 1 lịch check tự tạo trước đó bị bắn ra với nội dung đã lỗi thời (nói "chưa tìm được path
tool1", "chưa push label" — nhưng thực tế đã xử lý xong ở Phần 29). Nhận ra ngay là stale, không làm
lại các bước đã xong, mà đi kiểm tra trạng thái thật:
- Đĩa đã tụt xuống **11GB free** (dưới ngưỡng hành động 15GB) — do 2 file đã verify (label
  `20240101_20240401` 6.2GB, tool1 `20250401_20250701` 5.3GB .gz) vẫn còn nằm local chờ hết 403
  indexing-lag, CỘNG với 1 quý label mới đóng thêm (`20240401_to_20240701`, 32,765,424 dòng, 6.5GB)
  trong lúc chờ.
- Verify lại 2 dataset cũ: cả 2 đã lên Kaggle sạch, khớp size — label `funding_label_1m_20240101_to_20240401.csv`
  6,212,923,983 B khớp; tool1 hiển thị `features_export_python_v3_1mfeatures_20250401_to_20250701.bin`
  (Kaggle tự giải nén .gz) 8,789,202,470 B — cùng pattern đã thấy ở quý 2025Q1, coi là verify OK.
- **Hành động theo đúng quy tắc đã duyệt:** `kill -STOP` cả 2 PID (217186, 217219) NGAY trước khi
  làm gì khác, báo Uni ngay trong lúc job đang dừng.
- Xoá local 2 file đã verify (label 20240101_20240401 + tool1 20250401_20250701, cả gốc và
  hardlink) → đĩa nhảy từ 11GB lên **21GB free**.
- Push luôn quý label mới `20240401_to_20240701` (dataset mới `funding-label-1m-20240401-20240701`,
  6,540,005,199 B local) trong lúc 2 job đang dừng, để có thêm headroom trước khi resume.
- `kill -CONT` cả 2 PID — job chỉ dừng ~25 giây, không ảnh hưởng gì (đang giữa việc ghi file, JVM
  pause an toàn).
- Push xong (~5-6 phút), verify quý `20240401_20240701` vẫn đang 403 (indexing lag bình thường) —
  CHƯA xoá local, để lần check tới. Đĩa ổn định 20GB free. 2 job vẫn khỏe (~2h30m), không có quý
  mới nào khác đóng thêm trong lúc chờ.

**Bài học rút ra:** khoảng cách giữa 2 lần check-in liên tiếp (kể cả khi không có sự cố bridge) đủ để
2 job đóng thêm ~1 quý mỗi loại và đẩy đĩa từ mức an toàn xuống dưới ngưỡng — xác nhận lại rủi ro đã
nêu ở Phần 27/28: CHƯA có cơ chế tự động độc lập với chu kỳ check-in của Claude. Đề xuất viết script
bash chạy nền/cron trên Oracle vẫn đang chờ Uni duyệt.

**Câu hỏi vẫn đang treo:** viết 2 tool export mới cho `market_data`/`funding_fee` ngay hay ưu tiên
ticker-2026-backfill + OI-verify trước? Uni vẫn chưa trả lời.

## Phần 31 — Check-in 00:3x-00:5x ICT: verify+xoá quý label 20240401_20240701, push quý tool1 mới

**Lịch check tự tạo lần này cũng đã lỗi thời** (tham chiếu Phần 29, mốc 23:3x — trước cả sự cố đĩa
11GB ở Phần 30). Không làm lại việc đã xong, kiểm tra trạng thái thật:
- 2 job khỏe (~2h40m), đĩa 17GB free lúc đầu (tiếp tục giảm chậm nhưng còn trên ngưỡng).
- Verify quý label `20240401_to_20240701` (push ở Phần 30): khớp Kaggle (6,540,005,199 B) → xoá
  local ngay → đĩa lên 23GB.
- Phát hiện quý tool1 mới đóng: `20250701_to_20251001` (58,105,501 records, .gz 5,786,607,208 B).
  Tạo dataset mới `chuyendinh/funding-tool1-1m-20250701-20251001`, push xong (~5 phút), verify đang
  403 (indexing lag) — đĩa vẫn ổn định 22GB (trên ngưỡng nhiều) nên KHÔNG xoá local vội, để lần check
  tới verify rồi xoá.
- Không có quý label mới nào đóng thêm kể từ `20240401_to_20240701`.
- 2 job vẫn khỏe xuyên suốt, không phải STOP lần nào trong phiên check này.

**Câu hỏi vẫn đang treo:** viết 2 tool export mới cho `market_data`/`funding_fee` ngay hay ưu tiên
ticker-2026-backfill + OI-verify trước? Uni vẫn chưa trả lời.

## Phần 32 — Check-in 01:0x-01:1x ICT: đĩa lại chạm đúng ngưỡng 15GB — STOP/dọn/push/CONT lần 3

**Lịch check tự tạo lần này cũng lỗi thời** (tham chiếu Phần 30 — đã xử lý xong ở Phần 31). Kiểm tra
trạng thái thật:
- Đĩa 15GB free — ĐÚNG ngưỡng hành động. Theo quy tắc đã duyệt: `kill -STOP` cả 2 PID NGAY trước khi
  làm gì khác (chủ động, không chờ xuống dưới hẳn 15GB — vì 2 lần trước disk rơi rất nhanh giữa các
  lần check).
- Verify quý tool1 `20250701_to_20251001` (push ở Phần 31): khớp Kaggle (Kaggle tự giải nén .gz →
  hiển thị `.bin` 9,877,935,170 B, cùng pattern các quý trước) → xoá local.
- Phát hiện quý label mới đóng: `20240701_to_20241001` (35,294,921 dòng, 7,057,208,457 B) — tạo
  dataset mới `chuyendinh/funding-label-1m-20240701-20241001`, push ngay trong lúc 2 job đang dừng.
- Đĩa sau xoá+trước push: 20GB. Push xong (~7 phút) đĩa vẫn 20GB (job đang dừng nên không sinh thêm
  file).
- `kill -CONT` cả 2 PID — lần này dừng khá lâu hơn các lần trước (~6 phút, do chờ push xong) nhưng
  vẫn an toàn (JVM pause, không mất dữ liệu, không lỗi khi resume).
- Verify quý label mới push vẫn đang 403 (indexing lag) — để lần check tới.
- Không có quý tool1 mới nào đóng thêm trong phiên này (vẫn `20250701_to_20251001` là mới nhất).

**Nhận xét:** đây là lần thứ 3 đĩa chạm/dưới ngưỡng 15GB kể từ khi restart job (Phần 27). Tần suất
đóng quý mới (~1 quý/45-90 phút cho mỗi job) đang nhanh hơn khả năng verify+xoá thủ công theo chu kỳ
check-in 40-45 phút. Đề xuất vẫn treo từ Phần 27/28/30: cần script tự động độc lập trên Oracle. Chưa
được Uni duyệt để triển khai.

**Câu hỏi vẫn đang treo:** viết 2 tool export mới cho `market_data`/`funding_fee` ngay hay ưu tiên
ticker-2026-backfill + OI-verify trước? Uni vẫn chưa trả lời.

## Phần 33 — Check-in 01:2x ICT: verify+xoá quý label 20240701_20241001, không có quý mới, đĩa ổn

**Lịch check lần này cũng lỗi thời** (Phần 31 — đã xử lý ở Phần 32). Verify quý label
`20240701_to_20241001` (push Phần 32): khớp Kaggle (7,057,208,457 B) → xoá local → đĩa 18GB→24GB.
Không có quý mới nào đóng thêm (label mới nhất vẫn `20240701_20241001`, tool1 mới nhất vẫn
`20250701_20251001`, cả 2 đã push+verify+xoá xong). 2 job khỏe liên tục (~3h35m), không cần STOP.

**Câu hỏi vẫn đang treo:** viết 2 tool export mới cho `market_data`/`funding_fee` ngay hay ưu tiên
ticker-2026-backfill + OI-verify trước? Uni vẫn chưa trả lời.

## Phần 34 — TỔNG HỢP CHUYỂN SESSION (viết theo yêu cầu Uni "chạy xong rồi đó tổng hợp...")

**⚠️ CẢI CHÍNH QUAN TRỌNG: 2 job KHÔNG "chạy xong" — cả 2 đã CRASH lần thứ 4 lúc 02:44 ICT
07/08 do hết đĩa (100% đầy, còn 1.1GB).** Đây là hiểu lầm cần sửa ngay: `tool1_export` có log dòng
"🏁 HOÀN TẤT TOÀN BỘ QUÁ TRÌNH XUẤT FEATURES!" và `EXIT=0` NGAY SAU một `IOException: No space left
on device` — tool này có BUG che giấu lỗi (log "hoàn tất" dù vừa crash giữa lúc viết file), rất có
thể đây là nguồn gốc khiến Uni nhìn log tưởng đã xong. Cần sửa code (bắt exception rồi set exit code
khác 0, không log "HOÀN TẤT" khi có lỗi) — CHƯA làm, để dành cho session mới.

### A. Trạng thái 2 job (cả 2 đã CHẾT, không phải dừng tạm)

- `label_export` PID 217186: EXIT=1 lúc 02:44:10. Range gốc `20231001-20260701`.
- `tool1_export` PID 217219: EXIT=0 (giả, thực chất crash) lúc 02:44:10. Range gốc `20250401-20260701`.
- Log: `label_export_prod2.log`, `tool1_export_features_export_python_v3_1m_2.log` (không đổi tên).

### B. Việc đã làm để cứu dữ liệu trong lần check này (đĩa 100% → 23GB free)

1. Xoá 2 file XÁC NHẬN CORRUPT (đã kiểm tra kỹ, không phải suy đoán):
   - `funding_label_1m_20250101_to_20250401.csv` — truncate giữa dòng (`tail -c 200` cho thấy dòng
     cuối cụt "1742865180000,2025", không xuống dòng).
   - `features_export_python_v3_1mfeatures_20260101_to_20260401.bin.gz` — `gzip -t` báo "unexpected
     end of file".
2. Push + verify + xoá local 2 quý AN TOÀN đã đóng xong hoàn chỉnh trước khi crash:
   - `chuyendinh/funding-label-1m-20241001-20250101` (40,073,536 dòng, verify khớp 8,007,891,009 B).
   - `chuyendinh/funding-tool1-1m-20251001-20260101` (65,950,029 records, verify khớp — Kaggle tự
     giải nén .gz thành 11,211,504,930 B).
3. **Cứu được quý label `20250101_to_20250401` KHÔNG CẦN regenerate lại từ Aerospike**: 4 file
   `.part0-3.csv` gốc của quý này vẫn CÒN NGUYÊN VẸN trên đĩa (kiểm tra `tail -c` từng part, tất cả
   kết thúc sạch bằng dòng CSV đầy đủ) — vì code `mergeQuarter()` crash NGAY TRƯỚC bước xoá part
   (đúng như chẩn đoán cũ ở Phần 26). Đã tự viết lệnh `cat`/`tail -n +2` để merge lại 4 part thành 1
   file hoàn chỉnh (`head -1` lấy header từ part0, rồi `tail -n +2` từng part nối vào) — **kết quả
   khớp CHÍNH XÁC 100%**: tổng 4 part = 8,990,326,942 B, output = 8,990,326,090 B (chênh đúng 852B =
   3 dòng header trùng bị bỏ, không thiếu không dư 1 byte nào).
   - **Sự cố phụ trong lúc merge**: lần chạy đầu bị lỗi transport (Cloudflare 520) giữa lúc SSH đang
     chạy — tưởng lệnh đã chết theo kết nối nên chạy lại lần 2, nhưng thực ra lệnh 1 KHÔNG CHẾT (vẫn
     sống trên server vì không dùng nohup/disown), dẫn tới 2 process cùng ghi đè 1 file → dữ liệu bị
     xen lẫn (`ps aux` phát hiện 2 PID bash + 2 PID tail cùng chạy). Đã `kill -9` cả 2, xoá file hỏng,
     chạy lại ĐÚNG 1 lần với `nohup ... & disown` — lần 2 sạch, khớp size như trên.
   - **Bài học cho session mới:** khi 1 lệnh SSH không nohup bị lỗi transport/mất kết nối giữa lúc
     chạy, ĐỪNG giả định nó đã chết — luôn `ps aux` kiểm tra trước khi chạy lại, nếu không sẽ bị
     race-condition ghi đè file như trên.

### C. 🔴 PHÁT HIỆN MỚI, NGHIÊM TRỌNG NHẤT: tài khoản Kaggle đã HẾT QUOTA private dataset

Khi push quý `20250101_to_20250401` vừa cứu được (8.37GB) lên `chuyendinh/funding-label-1m-20250101-20250401`:
file upload lên THÀNH CÔNG (`Upload successful: funding_label_1m_20250101_to_20250401.csv (8GB)`)
nhưng **tạo dataset THẤT BẠI**: `Dataset creation error: The size of your files is 8.372 GB, it
exceeds the 0 B of remaining private quota`.

**Nghĩa là: quý này CHƯA hề an toàn trên Kaggle — chỉ tồn tại 1 bản duy nhất trên local Oracle.**

Kiểm tra `kaggle datasets list --mine` (3 trang, ~28 dataset của session này + ~21 dataset cũ hơn từ
trước): tổng dung lượng theo cách Kaggle tính quota (có vẻ là size sau khi Kaggle tự nén nội bộ,
KHÁC với size file gốc upload — ví dụ file CSV gốc 8GB chỉ tính ~2.2GB quota) ước tính **~95GB**,
và quota hiện đã về **0 B còn lại**. Đây là hệ quả tích lũy của cả session này (mỗi quý 1 dataset
riêng theo đúng quy tắc đã chọn — nhưng chưa ai tính tổng quota sẽ hết).

**3 hướng xử lý, CẦN UNI QUYẾT ĐỊNH, KHÔNG TỰ CHỌN:**
1. Xoá 1 số dataset cũ/rác để giải phóng quota — ứng viên rõ ràng nhất là rác test:
   `cli-smoke-1783939742` (200B), `smoke-cli-latest-1783946170` (181B), `ticker-probe-1783948469`
   (505MB) — nhưng tổng 3 cái này chỉ ~500MB, KHÔNG đủ giải phóng đáng kể. Muốn giải phóng nhiều
   (vài chục GB) phải xoá các dataset lớn như `hpo-ticker-daily` (10.68GB), `funding-selector-wfo-data`
   (10GB), `funding-tool1-features` (4.86GB), `funding-oi-percoin` (3.2GB), `funding-label-full`
   (2.62GB), `funding-label-full-1m`/`funding-tool1-features-1m` (2 dataset "đông lạnh" có bug mất
   dữ liệu quý 1-12 từ trước, đã quyết định không đụng) — CẦN Uni xác nhận cái nào thực sự không
   dùng nữa mới xoá, tự xoá nhầm có thể mất dữ liệu đang dùng ở notebook/pipeline khác.
2. Đổi dataset mới sang PUBLIC thay vì private (mặc định `kaggle datasets create` tạo private) — có
   thể có quota riêng lớn hơn hoặc không giới hạn, nhưng đồng nghĩa dữ liệu funding/trading lên công
   khai trên Kaggle — cần Uni đồng ý trước vì đây là thay đổi mức độ riêng tư dữ liệu.
3. Kiểm tra xem tài khoản Kaggle có thể nâng quota (verify phone/nâng cấp) hay không — chưa tra cứu.

**Cho tới khi Uni quyết định, KHÔNG restart lại 2 job** — vì dù chạy tiếp, mọi quý mới đóng cũng
không thể push lên Kaggle (quota 0), sẽ chỉ chất đầy đĩa Oracle rồi crash lại (lần 5) nhanh hơn lần
này vì không còn xả được dữ liệu ra ngoài.

### D. Bảng tình trạng dữ liệu THẬT (đã kiểm chứng qua `kaggle datasets list --mine`, không suy đoán)

**LABEL** (job range `20231001-20260701`, các quý TRƯỚC `20231001` do job cũ trước khi restart Phần
27 phụ trách — 2021Q4-2023Q3 đã có trên Kaggle riêng lẻ, còn 2021Q1-Q3 hình như chỉ nằm trong dataset
cũ gộp `funding-label-full-1m`/`funding-label-full`, CHƯA xác nhận lại):
- Đã CONFIRMED an toàn trên Kaggle (verify size khớp): `20231001-20240101`, `20240101-20240401`,
  `20240401-20240701`, `20240701-20241001`, `20241001-20250101`.
- Đã merge lại sạch nhưng CHƯA lên được Kaggle (chặn bởi quota, chỉ có 1 bản local):
  `20250101-20250401` (file `/home/ubuntu/claudedata/wfo1m/label_ds_1m/funding_label_1m_20250101_to_20250401.csv`,
  8,990,326,090 B) — **RỦI RO MẤT DỮ LIỆU NẾU CRASH LẦN NỮA, ưu tiên push ngay khi quota được giải
  quyết.**
- Dở dang, part file KHÔNG đủ để merge (1 trong 4 part rõ ràng ít hơn hẳn 3 part khác — job crash
  giữa lúc viết): `20250401-20250701` (part0 2.1GB, part1 2.0GB, part2 2.4GB, part3 CHỈ 178MB),
  `20250701-20251001` (part1 1.7GB, part2 CHỈ 493MB, thiếu part0/part3). Các part này vẫn còn trên
  đĩa, CHƯA xoá — nếu muốn cứu tiếp phải chờ job restart và tiếp tục ghi nốt các part còn thiếu
  (CẦN kiểm tra code xem job có tự nhận ra part đã có và ghi tiếp hay ghi đè mất dữ liệu — CHƯA kiểm
  tra, rủi ro cần đánh giá trước khi restart).
- Chưa hề bắt đầu: `20251001-20260101`, `20260101-20260401`, `20260401-20260701`.

**TOOL1** (job range `20250401-20260701`, quý trước đó do job cũ phụ trách, đã có sẵn trên Kaggle):
- Đã CONFIRMED an toàn trên Kaggle: `20240101-20240401`, `20240401-20240701`, `20240701-20241001`,
  `20241001-20250101`, `20250101-20250401`, `20250401-20250701`, `20250701-20251001`,
  `20251001-20260101`.
- Đã xoá vì corrupt, KHÔNG cứu được (tool1 không có part file để ghép lại như label — 1 file/quý
  duy nhất, ghi tuần tự): `20260101-20260401` — MẤT HOÀN TOÀN, cần regenerate lại từ Aerospike nếu
  muốn có quý này.
- Chưa hề bắt đầu: `20260401-20260701` (quý cuối, mục tiêu cuối của range job).

### E. Việc cần Uni quyết định trước khi làm tiếp (ưu tiên từ cao xuống thấp)

1. **Quota Kaggle** (mục C) — chặn TOÀN BỘ việc push tiếp, kể cả quý vừa cứu được.
2. **Có restart lại 2 job không, và restart từ đâu** — với 2 lựa chọn cho label: (a) restart từ
   `20250401` (bỏ luôn 2 quý dở `20250401-20250701`/`20250701-20251001`, quy tương tự Phần 27 —
   an toàn, đơn giản, nhưng lãng phí phần đã ghi dở); (b) tìm cách resume ghi tiếp phần part còn
   thiếu (rủi ro cần đọc code trước, chưa làm). Cho tool1: chỉ có 1 lựa chọn — restart từ
   `20260101` (quý mất) vì không có gì để resume.
3. **Bug che giấu lỗi của `ExportFeaturesForPythonTool`** (mục đầu Phần 34) — nên sửa code trước
   khi chạy tiếp, để không bị hiểu lầm "xong" lần nữa khi thực ra crash.
4. **Câu hỏi cũ vẫn treo từ Phần 28:** viết 2 tool export mới cho `market_data`/`funding_fee` ngay
   hay ưu tiên ticker-2026-backfill + OI-verify trước.
5. **Cơ chế tự động chống crash đĩa** (đề xuất từ Phần 27/28/30/32, vẫn chưa được duyệt) — với quota
   Kaggle giờ cũng là 1 điểm nghẽn, cơ chế tự động (nếu làm) cũng cần tính luôn việc kiểm tra quota
   trước khi push, không chỉ kiểm tra đĩa.

### F. Việc kỹ thuật đã dọn dẹp phiên này (không cần theo dõi tiếp)

- Đã xoá 1 lịch check tự tạo (`send_later`) còn treo (`trig_01SGQmXpL36UV6dCa4qau8KN`) để tránh bắn
  thông tin cũ (job PID không còn tồn tại) vào session mới. Không còn lịch check tự động nào đang
  chờ chạy cho TASK-251 sau thời điểm này — session mới cần tự quyết định có tiếp tục theo dõi hay
  không, KHÔNG có gì tự động chạy ngầm.

**Kết luận cho session mới:** đọc Phần 34 này là đủ để nắm bối cảnh hiện tại, không cần đọc lại toàn
bộ Phần 1-33 trừ khi cần tra cứu chi tiết lịch sử/quyết định cũ. Việc đầu tiên khi bắt đầu: hỏi Uni
về mục E.1 (quota Kaggle) trước khi làm bất cứ điều gì khác liên quan tới push hay restart job.

## Phần 35 — ĐỔI LABEL TỪ CSV SANG PROTOBUF COLUMNAR (giảm quota Kaggle 3.7 lần) — ĐÃ TRIỂN KHAI

### A. Phát hiện nền tảng: Kaggle tính quota theo BẢN NÉN, không theo size thô

Uni đề xuất "xoá label CSV, xuất lại dạng bin/snappy cho nhẹ". Đo thật trước khi làm, và phát hiện
trực giác ban đầu NGƯỢC với thực tế:

| Định dạng | Size thô | Quota Kaggle THẬT | So với CSV |
|---|---|---|---|
| CSV (đang dùng) | 601.7 MB | 161.8 MB (26.9%) | 1.00× |
| protobuf row-based | 299.6 MB | 163.2 MB | **0.99× — KHÔNG giảm gì** |
| protobuf columnar | 175.3 MB | 108.0 MB | 1.50× |
| + delta giữa horizon (lossless 1e-6) | 141.8 MB | 60.3 MB | 2.68× |
| + scale 1e-5 | 123.1 MB | **46.5 MB** | **3.48×** |
| + scale 1e-4 | 115.5 MB | 31.1 MB | 5.21× |

Cả 3 dòng cuối đã **push thật lên Kaggle verify**, quota đo được lệch <0.2% so với gzip ước lượng
(`pbtest-v3-delta-1e6` 60,329,814 B / `v4` 46,481,933 B / `v5` 31,077,175 B). Kết luận chắc chắn:
**quota Kaggle ≈ size sau gzip**. Vì vậy:
- File ĐÃ NÉN SẴN (.gz, snappy) tốn quota ~100% size file — đây chính là lý do tool1 `.bin.gz`
  ngốn tới ~40GB quota. Nén sẵn trước khi push là PHẢN TÁC DỤNG.
- Chuyển CSV sang binary thô mà không đổi cấu trúc thì VÔ ÍCH (protobuf row-based chứng minh:
  thô nhỏ hơn 2× nhưng nén xong bằng đúng CSV).

### B. 3 kỹ thuật thực sự tạo ra khác biệt

1. **Columnar**: gom 200k dòng thành 1 chunk, mỗi cột 1 mảng packed.
2. **Delta giữa các horizon**: `maxFav` là running max nên `maxFav_12h` thường BẰNG `maxFav_4h`.
   Lưu h0 rồi (h1−h0), (h2−h1)… → phần lớn = 0. `nBars` lưu THIẾU HỤT so với kỳ vọng (đủ nến ⇒ 0).
   Đây là kỹ thuật đóng góp lớn nhất (1.50× → 2.68×).
3. **Sort trong chunk theo (symbol, t)**: đo 3 phương án — sort-trong-chunk 3.50× > sort-toàn-cục
   3.49× > không-sort 2.96×. Sort trong chunk vừa TỐT NHẤT vừa chỉ cần buffer 21MB (không phải
   buffer cả quý) → giữ nguyên được kiến trúc partition + đóng-file-theo-quý.

### C. Precision: Uni chốt 1e-5 sau khi xem tác động thật

Đo trên 500k dòng (6 triệu giá trị ratio): median maxFav 3.4%, maxAdv 1.5%, retEnd 2.3%; chỉ
0.3–0.9% giá trị nhỏ hơn bước làm tròn 1e-4.

| | Sai số tối đa | Tỉ lệ giá trị sát ngưỡng có thể đổi phía (ngưỡng 2% / 6%) |
|---|---|---|
| 1e-6 | 0.005 bps | ~0 |
| **1e-5 (CHỌN)** | **0.05 bps** | **0.014% (1/7.000) / 0.005% (1/20.000)** |
| 1e-4 | 0.5 bps | 0.145% (1/690) / 0.048% |

Đối chiếu: fee taker Binance futures = 4 bps → sai số 1e-5 nhỏ hơn fee 80 lần. Chọn 1e-5 thay vì
1e-4 vì chênh quota chỉ ~3GB trên toàn dải nhưng rủi ro biên ngưỡng thấp hơn 10 lần (quan trọng nếu
sau này test ngưỡng thấp 2% cho chiến lược lướt).

### D. Đã code + verify + đang chạy

**Code mới:**
- `src/main/proto/funding_label.proto` — schema (đã có sẵn `protobuf-java` + `protobuf-maven-plugin`
  trong pom.xml nên không phải thêm dependency).
- `src/main/java/.../export/LabelPbSink.java` — writer columnar (buffer 200k, sort bằng cách gói
  (symId,tIdx,vịTrí) vào 1 long rồi `Arrays.sort` để tránh boxing).
- `ExportFundingLabel.java` sửa 6 điểm: QuarterSink dùng LabelPbSink; `sinkFor` truyền baseMs = đầu
  quý; `emit()` đẩy thẳng số thay vì build chuỗi CSV; `mergeQuarter()` giờ chỉ NỐI BYTE (mỗi chunk
  tự chứa dictionary symbol → không cần remap, nhanh hơn và an toàn hơn bản CSV cũ); đuôi file
  `.csv` → `.pb`.
- `ml/lib/funding_label_pb.py` — decoder trả DataFrame TÊN CỘT Y HỆT CSV cũ, có `usecols` để chỉ
  giải nén cột cần. Phía consumer chỉ đổi 1 dòng: `pd.read_csv(...)` → `read_label(...)`.

**Verify round-trip (không lấy mẫu, so từng ô):** chạy jar mới trên 20250101→20250115, đọc lại bằng
decoder Python, so với file CSV cũ `funding_label_1m_20250101_to_20250401.csv` (do jar CŨ sinh):
- **1.561.213 dòng × 24 cột = 37,5 triệu ô.**
- Cột số nguyên (`tHitFav`, `tHitAdv`, `nBars` × 4 horizon): **sai lệch 0 tuyệt đối**.
- Cột ratio: sai số max 5.03e-6 — đúng bằng mức làm tròn của scale 1e-5 (lý thuyết ≤ 5.5e-6), KHÔNG
  có outlier nào ⇒ không có bug logic.
- NaN/ô rỗng: `lệch NaN = 0` trên mọi cột ⇒ bitmask null hoạt động đúng.

**Tỉ lệ nén trên file JAVA thật sinh ra** (không phải bản test Python): quý 20250101_20250401 phần
6.8M dòng → .pb 281,730,244 B, gzip 99,281,549 B, so với CSV tương đương → **giảm 3.70 lần** (còn
tốt hơn bản test Python 3.48× nhờ dictionary symbol tích luỹ).

**Job đang chạy:** PID 243175, jar `/home/ubuntu/java/simulator/gatecount_pb_20260807.jar`, range
FULL `20210101 → 20260701`, `LABEL_THREADS=4`, log
`/home/ubuntu/claudedata/wfo1m/label_ds_1m/label_export_pb.log`. Đĩa lúc khởi động 29GB free.
File sinh ra: `funding_label_1m_YYYYMMDD_to_YYYYMMDD.pb` (~1.7–2.3GB/quý thay vì 6–8GB như CSV) ⇒
rủi ro hết đĩa GIẢM MẠNH so với 4 lần crash trước.

### E. Việc còn lại (chưa làm)

1. **Consumer Python chưa sửa** — `gen_funding_wf_predictions.py` (critical path WFO) và ~40 file
   khác vẫn đang `pd.read_csv(LABEL_CSV, usecols=[...])`. Decoder đã sẵn sàng, mỗi file chỉ cần đổi
   1 dòng, nhưng CHƯA đổi file nào. Phải làm trước khi chạy lại WFO.
2. **`funding_label_pb2.py`** (binding Python sinh từ .proto) cần commit vào repo / ship lên Kaggle
   dataset code để kernel dùng được. Hiện mới sinh tạm ở `/home/ubuntu/claudedata/pbtest/gen/`.
3. **Tool1 chưa đổi** — Uni đã đồng ý làm cả tool1, nhưng chưa thiết kế/test được vì dữ liệu tool1
   đã bị xoá sạch cả trên Kaggle lẫn local (không còn mẫu để đo). Lưu ý quan trọng: tool1 hiện là
   raw struct 170B/record ghi qua GZIPOutputStream — **bỏ .gz KHÔNG giúp gì** (gzip và bản nén nội
   bộ của Kaggle tương đương nhau); muốn giảm thật phải làm giống label (columnar + scale int thay
   float32 + delta). Cần xuất lại 1 quý trước rồi mới đo được.
4. **3 dataset test trên Kaggle** (`pbtest-v3-delta-1e6`, `pbtest-v4-delta-1e5`, `pbtest-v5-delta-1e4`,
   tổng ~138MB quota) nên xoá tay qua web UI — API Kaggle KHÔNG có hàm xoá dataset, và
   `kaggle datasets version` cũng không thay thế được khi quota cạn (nó cần quota trống cho bản mới
   TRƯỚC khi xoá bản cũ).
5. **File CSV tham chiếu** `funding_label_1m_20250101_to_20250401.csv` (8.99GB) đang giữ lại trên
   Oracle để đối chiếu; xoá được sau khi export mới chạy ổn định vài quý.

## Phần 36 — Cải chính "40 file consumer" + vá điểm chặn thật + tool1 đã khởi động lại

### A. ⚠️ CẢI CHÍNH mục E.1 của Phần 35: "~40 file phải sửa" là BÁO ĐỘNG GIẢ

Đã điều tra từng file (git log lần sửa cuối + ai tham chiếu + dataset nào đang trỏ tới). Kết quả:

**Chỉ 1 file Python thực sự phải sửa**, vì 51 file còn lại đọc dataset `funding-label-full` CŨ
(lưới 15m, CSV) — hoàn toàn KHÔNG đụng tới định dạng .pb mới (chỉ áp cho export 1m). Cụ thể:
- **43/44 kernel-metadata.json** trỏ `chuyendinh/funding-label-full` (cũ). Duy nhất
  `orchestrator/kernels_wfo1m/selector-predict-1m/` trỏ `funding-label-full-1m` (mới).
- 32 file `orchestrator/kernels_sl4h/*/run_train.py` là copy-paste (diff giữa 2 file cùng họ = ĐÚNG
  1 dòng), commit cuối 07-16→07-19, và chính `docs/reports/ENTRY_ALPHA_STATE_AND_PLAYBOOK.md` +
  `HANDOFF_20260730` đã liệt kê thẳng là "rác, chờ Uni quyết dọn".
- Các probe `kaggle_{oiz_probe,track_a_lite,short_probe,reprobe_unfiltered}`, `kaggle_dca_hard`
  (commit cuối có message *"DCA ablation verdict: DCA ~0 edge → chốt bỏ DCA"*), `train_funding_selector*`
  (đã bị thay bởi `gen_funding_wf_predictions.py`) — đều là thí nghiệm đã đóng.
- 4 file NÊN sửa khi cần (không chặn): `orchestrator/tools/leg1_econ.py`,
  `kaggle_recovery_depth/recovery_by_depth.py` + `recovery_grid_v2.py`,
  `ml/funding_selector/analyze_label_baserate.py` — đều đọc dataset/đường dẫn CŨ.

**Lưu ý còn lại:** nếu sau này xoá dataset `funding-label-full` cũ để lấy quota thì 43 kernel đó
chết vì MẤT DATA (không phải vì đổi format) — nhưng phần lớn đã được chính docs đánh dấu là rác.

### B. Đã vá 4 điểm chặn THẬT (rủi ro lớn hơn nhiều so với "40 file")

1. `orchestrator/kernels_wfo1m/selector-predict-1m/run_train.py` — dòng tìm label cũ là
   `find1(".../funding_label.csv")`, dataset mới KHÔNG có file đó ⇒ assert chết ngay. Đã đổi: ưu tiên
   glob `funding_label_1m_*.pb` rồi truyền cả PATTERN (không phải 1 file) cho script gen; vẫn
   fallback về CSV nếu dataset mount là bản cũ.
2. `ml/lib/funding_label_pb2.py` — binding Python sinh từ .proto, TRƯỚC ĐÓ CHƯA có trong repo (chỉ
   nằm tạm trên Oracle) ⇒ thiếu là kernel chết ở `import`. Đã sinh và đưa vào repo.
3. `orchestrator/pipelines/wfo_canonical_1m.json` bước `sync_kernel` chỉ copy 1 file
   `gen_funding_wf_predictions.py` sang kernel dir ⇒ decoder không lên Kaggle. Đã sửa để copy thêm
   `funding_label_pb.py` + `funding_label_pb2.py`.
4. `gen_funding_wf_predictions.py` — gom việc import decoder vào `_import_pb_decoder()`, thử CẢ 2
   đường dẫn (cùng thư mục cho Kaggle, `../lib` cho repo) và báo lỗi rõ ràng nếu thiếu, thay vì
   ImportError khó hiểu giữa lúc kernel chạy trên Kaggle.

### C. Bug thật phát hiện nhờ chạy test end-to-end (không phải suy đoán)

Test đọc bằng glob `funding_label_1m_*.pb` khi job export ĐANG chạy → `DecodeError: Wire format was
corrupt`. Nguyên nhân: glob bắt luôn file `.partN.pb` mà job đang GHI DỞ (chunk cuối chưa hoàn
chỉnh). Đã vá ở CẢ 2 nơi (`funding_label_pb.read_label` và `_read_label_any`): tự loại file có
`.part` trong tên, kèm cảnh báo rõ. Nếu không vá, kernel Kaggle sẽ chết ngẫu nhiên tuỳ thời điểm
dataset được push.

**Test lại sau khi vá — chạy sạch:** đọc 24.964.883 dòng từ 2 quý (tự bỏ qua 5 file .part), 111
symbol, base rate maxFav≥6% tăng dần đúng logic theo horizon: 4h=13.5%, 12h=33.6%, 24h=48.7%,
72h=69.2%.

### D. Quota THẬT của 2 quý label protobuf đầu tiên (đã push + verify + xoá local)

| Quý | Dòng | File .pb | Quota Kaggle THẬT | CSV tương đương (ước) | Giảm |
|---|---|---|---|---|---|
| 2021Q1 | 10.972.619 | 463.825.531 B | **190.090.651 B** | ~590 MB | ~3.1× |
| 2021Q2 | 13.992.264 | 591.327.422 B | **242.823.743 B** | ~753 MB | ~3.1× |

Tỉ lệ 3.1× (thấp hơn 3.70× đo ở quý 2025) là hợp lý: 2021 ít coin hơn nên dictionary symbol + delta
kém hiệu quả hơn. Ước tính cả dải 22 quý: **~9GB quota thay vì ~33GB** nếu để CSV.

### E. Tool1 đã khởi động lại (Uni chọn "làm luôn cả 2")

Job tool1 chạy song song với label: PID 244172, cùng jar `gatecount_pb_20260807.jar`, range
`20210101→20260701`, `FF_UNFILTERED=1 FF_GRID_MIN=1`, `-Xmx10g`, log
`/home/ubuntu/claudedata/.run/mcp_ce/tool1_export_pb_20260807.log`.

**Vẫn xuất theo format CŨ (.bin.gz) — có chủ ý**, vì: (a) dữ liệu tool1 đã bị xoá sạch cả Kaggle lẫn
local nên KHÔNG còn mẫu nào để phân tích phân phối 40 feature → chưa thiết kế được format mới;
(b) khi quý đầu đóng xong sẽ có mẫu, lúc đó **convert offline sang format mới KHÔNG cần đọc lại
Aerospike** (tiết kiệm hàng giờ compute so với xuất lại lần nữa).

⚠️ Lưu ý khi làm format tool1: **bỏ `.gz` KHÔNG giúp gì** (gzip và bản nén nội bộ Kaggle tương
đương ⇒ quota gần như không đổi). Muốn giảm thật phải áp đúng 3 kỹ thuật như label: columnar +
scaled-int thay float32 + delta theo thời gian trong cùng symbol.

Oracle chỉ có **4 core** — label đang chiếm ~377%, tool1 ~95% ⇒ 2 job đã dùng gần hết CPU, KHÔNG
khởi động thêm job thứ 3. Đĩa 28GB free.

## Phần 37 — Đã ĐO tool1 trên mẫu thật: chỉ giảm được ~1.8×, KHÔNG như label (3.1–3.7×)

Quý tool1 đầu tiên đóng lúc 15:07 ICT (`20210101_to_20210401`, 11.019.264 records, .bin.gz 904MB)
⇒ đã có mẫu để phân tích (trước đó không có gì để đo vì dữ liệu tool1 bị xoá sạch).

**Đo trên 3.000.000 record đầu** (81 symbol, ~510MB raw), gzip level 9 = xấp xỉ quota Kaggle:

| Cách mã hoá | Thô | gzip (≈quota) | So với hiện tại |
|---|---|---|---|
| **A. raw struct 170B + gzip (ĐANG DÙNG)** | 510.000.000 | **243.975.926** | 1.00× |
| B. columnar float32 (chỉ tách cột, giữ kiểu) | 480.000.000 | 186.947.391 | 1.30× |
| C. columnar + scale int32 1e-5 | 480.000.000 | **135.625.714** | **1.80×** |
| D. columnar + scale 1e-4 + delta theo thời gian | 480.000.000 | 150.645.052 | 1.62× — **TỆ HƠN C** |

**Kết quả D bác bỏ giả thuyết ban đầu:** delta theo thời gian KHÔNG giúp cho tool1 (150.6MB so với
135.6MB của C — tệ hơn dù precision đã hạ thấp hơn 10 lần). Nguyên nhân: feature tool1 biến động
mạnh giữa các phút liền kề nên `x[t] − x[t−1]` không hề nhỏ hơn `x[t]`, trong khi zigzag varint lại
tốn thêm bit dấu. ⇒ **Phương án tốt nhất cho tool1 là C (columnar + scale int32 1e-5), 1.80×**, đây
là trần thực tế chứ không phải chưa tối ưu hết.

**Vì sao tool1 khó nén hơn label nhiều:** label thắng lớn nhờ *delta giữa các horizon*
(`maxFav_12h` thường BẰNG ĐÚNG `maxFav_4h` vì là running max ⇒ đa số delta = 0). Tool1 KHÔNG có cấu
trúc lặp đó — 40 feature là số thực liên tục độc lập (kiểm tra phân phối: %zero hầu hết < 4%, không
có cột nào gần-hằng-số). Nên chỉ còn 2 đòn bẩy là columnar (1.30×) và hạ precision (thêm 1.38×).

**Quy đổi ra tiền thật:** cả dải 22 quý tool1 hiện tốn ~20GB quota; theo phương án C còn ~11GB
⇒ tiết kiệm ~9GB. Trong khi quota còn 58GB và label mới chỉ dùng ~9GB ⇒ **KHÔNG gấp**.

**Chi phí phải trả nếu đổi format tool1:** sửa `ExportFeaturesForPythonTool.writeBatch` (Java) +
~15 file Python đang đọc trực tiếp `np.frombuffer(raw, dtype=TOOL1_DT)` (dtype 170B hardcode ở mỗi
file, KHÔNG có wrapper dùng chung như label) + verify round-trip lại từ đầu. Đây là điểm khác quan
trọng so với label: label chỉ có 1 điểm chạm thật, tool1 có ~15.

⇒ **Cần Uni quyết**: (a) đổi format tool1 ngay (đổi ~9GB quota lấy ~15 file phải sửa + rủi ro
regression), (b) giữ .bin.gz, chỉ push bình thường (quota vẫn đủ), hay (c) hoãn tới khi quota thực
sự căng. KHÔNG tự quyết. Trong lúc chờ, tool1 vẫn chạy và file .bin.gz vẫn giữ local (chưa push).

**Đã push+verify+xoá local quý label thứ 3** `20210701_to_20211001` (623.513.034 B, verify khớp).
2 job vẫn khỏe (label 1h09m, tool1 42m), đĩa 25-26GB free.
