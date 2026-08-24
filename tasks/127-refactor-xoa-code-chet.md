# TASK-127: Refactor — xoá file/func/class không còn dùng (CCD opus, branch riêng)

- **status:** doing (giao CCD 2026-07-04 tối)
- **resource:** local · **branch:** `cleanup-dead-code` (tạo từ `module`; TUYỆT ĐỐI không commit lên module — merge là quyết định của Uni sau review)

## ⛔ HÀNG RÀO CỨNG — đọc kỹ trước khi xoá bất kỳ thứ gì
1. **KHÔNG BAO GIỜ xoá** các loại sau dù "không có reference tĩnh":
   - Class có `public static void main` (entry-point tool chạy qua `java -cp jar <tên class>` — hệ này vận hành bằng chúng:
     WfoWorker, WfoCoordinator, LoadWfoGatePredTool, ExportHpoDataKaggle, ExportFeaturesForPythonTool, DumpSymbolMapper,
     GoldenBacktest, BinanceDataIngestor, BinanceOrderTradingManager, các Run*/Export*/Load*/Dump* khác...)
   - Class/tên xuất hiện dưới dạng CHUỖI trong bất kỳ file nào: *.md, *.sh, *.py, *.properties, *.xml, tasks/, docs/, scripts/
     (reflection, config, lệnh vận hành) — grep tên class (không package) toàn repo trước khi kết luận.
   - Code trong package live trading/ingestor đang chạy trên 242 (mọi thứ dưới `trading`, `ingestor`, `order` — chỉ liệt kê nghi vấn, không đụng).
2. Mỗi ứng viên xoá phải có BẰNG CHỨNG trong Kết quả: lệnh grep tên class toàn repo trả 0 hit ngoài chính nó + không main + không test đang tham chiếu.
3. Func/method không dùng trong class ĐANG dùng: chỉ xoá private/package-private không được gọi; public method giữ nguyên trừ khi chứng minh 0 caller toàn repo (cẩn thận reflection/serialization: giữ getter/setter của DTO, giữ method Gson/Jackson đọc).
4. Gate BẮT BUỘC sau MỖI cụm commit: `JAVA_HOME=/c/Users/pc/.jdks/corretto-17.0.9 /c/Users/pc/bin/mvn -q -DskipTests package` PASS; cuối cùng chạy thêm unit: `mvn -q test` — nếu test nào fail do xoá → khôi phục phần liên quan.
5. Commit CỤM NHỎ theo nhóm liên quan (vd: "xoa nhom simulator cu v1", "xoa util khong dung") — mỗi commit revert được độc lập. Trailer Co-Authored-By như quy ước. KHÔNG git add .
6. Nghi ngờ = KHÔNG XOÁ, đưa vào mục "Nghi vấn cần Uni quyết" trong Kết quả.

## Việc làm
1. `git checkout -b cleanup-dead-code` từ module (xác nhận tree sạch trước).
2. Quét ứng viên: class không được import/reference ở đâu + không thuộc whitelist mục 1. Gợi ý bắt đầu từ các vùng đã biết có xác cũ: simulator phiên bản cũ, HPO đời đầu, các *Test/*Demo/*Backup/*Old/*V1 bỏ hoang, code IS_KAGGLE_MODE còn sót (TASK-112 đã gỡ chính, có thể còn vụn), util không caller.
3. Xoá theo cụm + gate build từng cụm (mục 4).
4. Chạy full `mvn -q test` cuối; ghi số test pass.
5. Kết quả: bảng {file/class xoá | lý do | bằng chứng} + bảng "Nghi vấn cần Uni quyết" + tổng LOC giảm + danh sách commit. Marker /d/claudedata/CCD127_DONE. KHÔNG merge, KHÔNG checkout lại module ở cuối (để nguyên branch cleanup cho master review).

## Kết quả (CCD opus — 2026-07-04)

**Branch:** `cleanup-dead-code` (từ `module`, tree sạch trước khi tạo). KHÔNG commit lên module. KHÔNG merge. Để nguyên branch cho Uni review.

### Phương pháp (bằng chứng lặp lại được)
- `scripts_tmp/reach.py`: dựng đồ thị reachability toàn bộ 366 class. Roots = 177 class có `public static void main` ∪ mọi class-name xuất hiện dạng **chuỗi** trong `*.md/*.sh/*.py/*.properties/*.xml/*.txt/*.json/*.yaml` (docs, tasks, scripts). BFS: class được coi "sống" nếu tên nó xuất hiện trong file của một class đã reachable. → tìm ra tập **unreachable** (bắt được cả cụm chết tự tham chiếu lẫn nhau).
- Mỗi ứng viên trước khi xoá: `grep -rw <tên-class>` toàn repo (trừ `.git/target/scripts_tmp/luna_csv`) = **0 hit ngoài chính file**, không main, không chuỗi trong md/sh/py/properties/xml.
- `scripts_tmp/deadmethods.py` + grep tay: dò private/private-static method 0 caller trong class đang dùng; đã loại false-positive (call dạng `obj.method()`).
- Gate `mvn -q -DskipTests package` PASS sau **mỗi** cụm commit; `mvn -q test` cuối = **EXIT 0** (repo không có JUnit/surefire — `test` chỉ compile; các `*Test` là tool main ad-hoc, đã giữ nguyên vì có main).

### Đã xoá (3 commit, tổng **-317 LOC**, 0 dòng thêm)

| File / method xoá | Loại | Lý do | Bằng chứng |
|---|---|---|---|
| `ai_ml/hpo/BackTestEngineAIMarket.java` | class (42) | HPO đời đầu, không caller | grep -rw = 0 ngoài; no main; unreachable |
| `ai_ml/hpo/HPOEvaluator.java` | class (32) | HPO đời đầu, không caller | grep -rw = 0 ngoài; no main; unreachable |
| `aerospike/CheckFundingDataInDB.java` | class (2) | Stub rỗng (chỉ khai báo, không body) | grep -rw = 0 ngoài; no main |
| `utils/DoubleArrayUtils.java` | class (111) | Util 0 caller | grep -rw = 0 ngoài; no main |
| `ai_ml/onnx/FixedSymbolMapper.java` | class (96) | Onnx orphan (thay bởi SimpleSymbolMapper/DumpSymbolMapper) | grep -rw = 0 ngoài; no main |
| `ComprehensiveMarketFeatureExtractor.validateAndCleanFeatures` | private method | 0 call trong file | grep = chỉ dòng khai báo |
| `FundingDataCollectionManager.calculateDistFromLow24H` | private method | 0 call | grep = chỉ dòng khai báo |
| `BackfillTickerPilot.shortOf` | private static | 0 call | grep = chỉ dòng khai báo |
| `DataManager.readObjectFromFile` + `writeObjectToFile` | 2 private static | 0 call | grep = chỉ dòng khai báo |

**Commit (revert độc lập từng cụm):**
- `3a5a4d2` xoa nhom HPO doi dau khong caller (BackTestEngineAIMarket, HPOEvaluator)
- `be070ae` xoa stub rong + util/onnx orphan (CheckFundingDataInDB, DoubleArrayUtils, FixedSymbolMapper)
- `ea6077d` xoa private method 0 caller (rule 3)

### Nghi vấn cần Uni quyết — KHÔNG đụng
1. **SDK vendored `com/binance/client/**` — 34 class unreachable** (REST-impl + enum không dùng nội bộ): `RestApiRequestImpl`, `ChannelParser`, `ApiSignature`, `InternalUtils`, `ResponseCallback` + ~29 enum (`OrderStatus`, `TradeDirection`, `TransferType`, `AccountState`, ...). App live dùng client khác (`BinanceFuturesClientSingleton`/`ClientSingleton`), nên cả nhánh REST-impl này chết nội bộ. **Nhưng** đây là code thư viện fork (groupId `binance-java-sdk`) → có thể là **API surface published** và/hoặc bị nạp qua **Gson/reflection**. Rủi ro cao, giá trị thấp → để Uni quyết có xoá cả `com/binance/client/impl` + enum thừa không. (Danh sách đầy đủ: chạy `python scripts_tmp/reach.py`.)
2. **`initData` / `run` KHÔNG phải dead** — analyzer flag nhầm vì bỏ qua call `obj.method()`; đã giữ nguyên. Ghi lại để lần sau không hiểu lầm.

### Không tìm thấy (đã quét, sạch)
- `IS_KAGGLE_MODE`/`KAGGLE_MODE` remnant: 0 hit (TASK-112 gỡ sạch).
- File `*Old/*Backup/*Demo/*V1` bỏ hoang: các match chỉ là substring ("Gold"→Old, "BackTest"→Back) của tool hợp lệ có main.
- Class chết trong `com/binance/chuyennd/**` ngoài 5 cái trên: 0 (re-run reachability sau xoá không sinh cascade app-code).

> `scripts_tmp/` (reach.py, deadmethods.py, *.txt) là script phân tích, **không commit** (đang untracked). Marker: `/d/claudedata/CCD127_DONE`.
