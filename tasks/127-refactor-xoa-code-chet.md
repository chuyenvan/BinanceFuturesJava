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

## Kết quả
<CCD điền>
