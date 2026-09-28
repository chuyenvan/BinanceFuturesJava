# RESULT — CADENCE-SPLIT-V2: PARITY md5 "OFF ⇒ Y NGUYÊN" (CỔNG CUỐI TRƯỚC DEPLOY)

Trạng thái: **PASS — đủ bằng chứng THỰC NGHIỆM** · 2026-09-28 · branch `module` · **KHÔNG push**.
Vòng: `bd7c4cd` (thiết kế lại thực thi nhịp, key `MARKET_SCAN_PRIORITY` mặc định 0 = OFF).

## 0. Kết luận

**CẢ 3 CHÂN md5 KHỚP CHÍNH XÁC.** "OFF ⇒ y nguyên" từ nay có **bằng chứng thực nghiệm**, không chỉ
bằng chứng cấu trúc ⇒ **đủ điều kiện kỹ thuật để deploy** (deploy vẫn cần owner duyệt riêng, thứ tự
shadow → 242 như `PLAN_CADENCE_SPLIT_V2.md` §4).

## 1. Jar kiểm chứng

- Nguồn: HEAD `bd7c4cd` (`bd7c4cda1f7eb017bddf92fc58cd2afa5e8295eb`), **working tree sạch** (không patch rời).
- Build: `mvn -q -DskipTests package` **local** (`arm64`, OpenJDK 11) — **KHÔNG** trên Oracle.
- **sha256 = `4aa42ceb03d34b91090a615260ad7dd1256ff6b22df79e2a083f2b9fb466f80c`** (99.716.708 B).
- Dataset Kaggle: `chuyendinh/sim-jar-cadence-v2` (mới; `sim.jar` + `JAR_PROVENANCE.txt`).
- Kernel log ghi `JAR_SHA256=4aa42ceb…` và `result.json` khớp ⇒ **0 rủi ro "jar cũ dùng âm thầm"**.
- Sanity: class `Configs` trong jar có key mới `MARKET_SCAN_PRIORITY` ⇒ jar đúng là bản có patch.

## 2. Ba chân parity (bundle `sim-x1-2021-bundle`, cửa sổ DEV 2021-07-01..2025-12-31, ticker_min 1826)

| chân | profile | key khai | md5 `printDone.csv` | kỳ vọng | n lệnh | equity | JVM secs |
|---|---|---|---|---|---|---|---|
| `par-kg0` | `x1_gs_t170` | KEEPLEG0 (`DCA_GRID_WEIGHTS=1,1,1,1`+`DCA_GRID_SCALE=6.0`), **KHÔNG** khai key mới | `99e42b75cf1a2142f9cd14dc72e371ba` | `99e42b75…` | 1085 | 103.083 | 819,9 |
| `par-t170` | `x1_gs_t170` | không override | `efb793e2468ca3a7318da0f0ad23d4fc` | `efb793e2…` | 1089 | 111.070 | 1246,5 |
| `par-bb` (belt-and-braces) | `x1_gs_t170` | KEEPLEG0 + **`MARKET_SCAN_MIN=0`** + **`MARKET_SCAN_PRIORITY=0`** (khai RÕ RÀNG) | `99e42b75cf1a2142f9cd14dc72e371ba` | = `par-kg0` | 1085 | 103.083 | 1104,4 |

- `PROFILE_HASH` khác nhau giữa 3 chân (do profile ghi khác key) **KHÔNG** dùng để so parity — dùng md5 `printDone.csv` (đúng quy ước `KAGGLE_SIM.md` §0.3).
- `symbol_mapper = 863` ở cả 3 chân (≥800) ⇒ guard Aerospike không kích hoạt ⇒ kết quả không lệch âm thầm.
- `java_rc=1` không phải fail: tiêu chí là log có `done:` + `printDone.csv` có dòng (như runbook).

## 3. `diff` (số dòng khác) so với baseline local đã ghi trước đó

| so sánh | số dòng khác |
|---|---|
| `par-kg0` vs baseline `cd-par-kg0` | **0** |
| `par-t170` vs baseline `cd-par-t170` | **0** |
| `par-bb` vs baseline `cd-par-kg0` | **0** |

⇒ Byte-identical, không chỉ "cùng số lệnh/equity".

## 4. Ý nghĩa "belt-and-braces" (`par-bb`)

`par-bb` chứng minh **"khai = 0" cũng y nguyên**, không chỉ "không khai": đặt tường minh
`MARKET_SCAN_MIN=0` **và** `MARKET_SCAN_PRIORITY=0` vào profile ⇒ md5 **vẫn** `99e42b75…`.
Phù hợp code: `Configs.java:818-826` chỉ gán khi `> 0` (`if (mm > 0)` / `if (mp > 0)`) ⇒ giá trị `0`
không đổi hành vi mặc định. Đây cũng chính là đường **rollback** (§4 kế hoạch): đặt 2 key = 0.

## 5. Chi phí / thời gian

- Cả 3 chân chạy **song song** trên Kaggle CPU (5 slot/account), **0 đồng**, **0 sim trên Oracle**.
- JVM mỗi chân: **819,9 / 1246,5 / 1104,4 s** (xấp xỉ và nhanh hơn mốc lịch sử ~1.100-1.300 s).
- Wall-clock push → COMPLETE cả 3: **~23 phút** (queue + mount + chạy 3 song song + fetch).

## 6. Giới hạn / không làm

- Không deploy/restart/sửa config production/242/shadow; không chạy gì trên Oracle; không push git.
- Parity này là **md5 trên đường SIM** (Kaggle + `TICKER_SOURCE=file`). Đường LIVE chỉ được chứng minh
  bằng cấu trúc: patch chỉ chạm `Configs.java` + `DetectEntrySignal2TradeNormal.java` (LIVE),
  đường SIM không tham chiếu `MARKET_SCAN_PRIORITY`/`TickGate`/`shouldSubmit`.
- Nhịp MKT ~16-17 lượt/giờ vẫn là **ƯỚC LƯỢNG** (mô hình), không đo live — phải xác minh ở bước A.

## 7. Tái lập

```bash
# 1) build jar từ HEAD (local)
cd /home/ubuntu/src/BinanceFuturesJava
export PATH=/home/ubuntu/tools/apache-maven-3.9.9/bin:$PATH
mvn -q -DskipTests package
sha256sum target/binance-java-sdk-1.2.4.jar   # 4aa42ceb…

# 2) stage + tạo dataset jar  (đã tạo: chuyendinh/sim-jar-cadence-v2)
mkdir -p /home/ubuntu/cadv2_jar && cd /home/ubuntu/cadv2_jar
cp /home/ubuntu/src/BinanceFuturesJava/target/binance-java-sdk-1.2.4.jar sim.jar
/home/ubuntu/.local/bin/kaggle datasets create -p . --dir-mode skip

# 3) chạy 3 chân parity
cd /home/ubuntu/src/BinanceFuturesJava
python3 research/analysis/cadence_v2_parity_run.py all

# 4) so md5
md5sum /home/ubuntu/kaggle_sim/out/cadv2-par-*/storage/printDone.csv
```
