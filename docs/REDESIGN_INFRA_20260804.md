# REDESIGN_INFRA (2026-08-04) — Thiết kế lại hạ tầng 1 lượt

> Chốt với Uni 2026-08-04. **Thay thế** phần topology cũ ở `SESSION_START §1` + `db/index` khi
> mâu thuẫn (nhánh này thắng). Mục tiêu: dẹp cảnh "data/model/vận hành/nghiên cứu rối loạn" bằng
> cách cho mỗi thứ MỘT chỗ ở cố định. Phần chiến lược (label 6%, SL/TP, selector/gate) KHÔNG thuộc
> file này — đây thuần hạ tầng.

## 0. Quyết định gốc (Uni chốt — không xét lại trừ khi Uni đổi)
1. **Bỏ 226.** Decommission sau khi Oracle-bridge + Oracle:3222-public đã proven.
2. **Oracle = hub duy nhất**, thay trọn vai 226. Mở **Aerospike 3222 ra public** (như 226 đang mở cả năm).
3. **Kaggle = fleet worker**, mặc định **self-contained trên file dataset**; chỉ đọc Oracle:3222 cho phần data nhỏ/live.
4. **242 = source of truth**, off-limits, không đổi. Chỉ Oracle sync TỪ 242.
5. **DR stance:** Oracle hỏng → reboot / reset sạch / cài lại Aerospike → resync từ 242. ⇒ mất mát vĩnh viễn = 0.
6. **symbol_mapper giữ LIVE** (sync từ 242), KHÔNG freeze cứng; mode-file dùng snapshot bake-vào-dataset.

## 1. Vai từng node (target)

| Node | Vai | Ràng buộc phải nhớ |
|---|---|---|
| **242** `103.157.218.242:2222` (aero :3222) | SoT mọi market data (live+lịch sử). Live procs (`BinanceDataIngestor`, `BinanceOrderTradingManager`) ghi thẳng đây. | **OFF-LIMITS.** Chỉ Oracle sync từ nó. Kaggle/dev KHÔNG bao giờ chạm. |
| **Oracle VPS** `ubuntu@161.118.212.3` 4-core/24GB | **HUB.** (a) Aerospike ns=test **public 3222** = kho compute/data-test + node internet-open cho Kaggle; (b) bridge 242→local; (c) compute nặng (WFO/HPO/export) — **1 job nặng/lần**; (d) scheduler always-on + dataset builder. | Disk **89% (~17G free)** — dọn jar cũ trước job ghi nhiều. KHÔNG 2 WFO nặng cùng lúc. |
| **Kaggle** account `chuyendinh`, 5 kernel CPU | Batch fleet. Mặc định **file-self-contained** (parity đã verify). Đọc Oracle:3222 chỉ cho data nhỏ/live. | 12h hard-kill, 5 slot. Không inject env động (hardcode flag vào `run_worker.py`). Đọc live Oracle:3222 ≤2 kernel đồng thời. |
| **226** | ❌ RETIRE. | Không dùng cho việc mới. Gỡ sau khi migration proven. |
| **redis** | Order queue live + messaging (mặt trading). | Không đụng trong redesign này. |

**Nhớ nhanh:** *242 = gốc thị trường · Oracle = hub compute + bridge + kho-Kaggle-đọc · Kaggle = batch trên file · 226 = chết.*

## 2. Ba tầng dữ liệu (source of truth rõ ràng)

1. **Market SoT = 242.** Mọi thứ downstream là dẫn xuất.
2. **Oracle Aerospike (ns=test, public 3222)** = bản làm việc: (a) set sync-từ-242 theo setname on-demand, (b) artifact compute dẫn xuất (`market_data_object`, features, preds, `symbol_mapper` live, jobstore WFO).
3. **Kaggle dataset** = snapshot ĐÓNG BĂNG cho batch tái lập: ticker file, market.bin, gate/selector/funding pred, OI — **có version + manifest provenance** (code SHA + nguồn + ngày). Build theo cadence 3 tháng.

**symbol_mapper (gỡ mâu thuẫn):** bản LIVE trên Oracle là canonical (đọc trực tiếp qua Oracle:3222 cho job light + lúc build). Cho fanout file nặng, bake snapshot `core_symbol_mapper` vào dataset lúc build — nhánh `KaggleDataLoader.loadSymbolMapperFile()` đã có (TASK-112c, 2026-08-04). Snapshot đóng dấu theo version dataset ⇒ luôn truy nguyên về đúng thời điểm sync.

## 3. Nơi chạy job (spine vận hành)

| Job đụng tới | Chạy ở đâu | Đường data |
|---|---|---|
| WFO/HPO/backtest fanout nặng (5 kernel) | **Kaggle** | file dataset, **zero live-dep** |
| Job light cần data tươi hơn chu kỳ build | Kaggle (≤2) hoặc Oracle | **Oracle:3222 public** |
| Build/export dataset | **Oracle** | đọc Aerospike-local + file → .bin/.tar → push Kaggle |
| Sync 242 → bản làm việc | **Oracle** | `Copy*242To226`/`ReplicateSet242To226` chạy TRÊN Oracle (getClient242=242, getClient226=127.0.0.1) |
| GHI 242 (realtime/historical market) | **242** (live procs) | không đụng |
| Sửa code thuần | máy nào cũng được | — |

> ⚠️ Bẫy cũ vẫn đúng: fanout nặng PHẢI file-mode. Đừng để 5 kernel cùng đọc live Oracle:3222 (lặp lại sự cố 226: 15GB RAM drop connection, 9/17 FAIL). Oracle vừa serve Kaggle vừa compute local = tranh tài nguyên.

## 4. Migration — gỡ 226 AN TOÀN (thứ tự, không kill 226 tới bước cuối)

1. **Mở Oracle:3222 public**: security-list Oracle Cloud (ingress 3222) + `aerospike.conf` `network.service.address any` (hoặc access-address = public IP). Verify TỪ Kaggle: TCP tới `161.118.212.3:3222` OK + đọc thử 1 set.
2. **Bridge 242→Oracle-local**: chạy `CopyTicker242To226` / `CopyAuxSets242To226` **trên Oracle** (đã tự write local vì AEROSPIKE_HOST_226=127.0.0.1). Verify record count khớp 242.
3. **Repoint Kaggle-side host**: mọi kernel/config đang trỏ `103.157.218.226:3222` → **đổi giá trị `AEROSPIKE_HOST_226` = IP public Oracle** (`161.118.212.3`). (Tên hằng "226" giữ nguyên — xem Nợ kỹ thuật.)
4. **Jobstore**: nếu muốn master/worker mạng thật, set `WFO_STATE_HOST` = Oracle public 3222 (Kaggle poll được). Nếu chỉ fanout file self-contained (VerifyOneWindow pattern) thì bỏ qua.
5. **Proof run**: 1 fanout WFO file-mode + 1 job light đọc Oracle:3222 live → cả hai PASS.
6. **Decommission 226** (chỉ sau bước 5 xanh).

## 5. Rủi ro còn mở (giữ hiển thị, đã chấp nhận có điều kiện)
- **Concentration:** Oracle là single hub trên box yếu, disk 89%. Build dataset lớn (ticker tar ~10G→31G) cần scratch — dọn jar cũ (`INFRA_FACTS`: ~40 jar × 99MB) trước. Cân nhắc build tar trên máy local (E:/D:) rồi push, tránh ép disk Oracle.
- **Public 3222 = Aerospike KHÔNG auth** (Community): ai scan cũng read/write/wipe. Chấp nhận vì 242=SoT + DR resync ⇒ thiệt hại = downtime + bị nghịch data, KHÔNG mất vĩnh viễn. Coi Oracle Aerospike là **disposable**.
- **Env-flag tax của Kaggle:** mỗi flag mới PHẢI hardcode vào launcher trước khi push (đã cắn vụ `TS_RATCHET_DECOUPLED`). Giữ checklist grep tên flag trong `run_worker.py`.

## 6. Nợ kỹ thuật tạo ra bởi redesign này
- Hằng `AEROSPIKE_HOST_226` / `getClient226()` giờ trỏ Oracle chứ không phải box 226 → **tên gây hiểu nhầm** (~40 file tham chiếu). KHÔNG rename ngay (churn lớn); ghi nợ, rename gộp 1 lượt sau. Chừng nào chưa rename: đọc "226" = "Oracle-local-hoặc-Oracle-public tùy chỗ chạy".
- `db/index` nguyên lý #2 ("242 chỉ 226 tới được") lỗi thời — Oracle tới 242 được. Cập nhật `db/index` sau khi migration xong.
