# rules/build-env — Build Maven & môi trường dev (nạp khi build/đóng jar)

> Đọc cùng [CORE](../CORE.md).

## Maven (no wrapper)
```bash
mvn install     # compile + protobuf codegen + shade fat jar
mvn package     # build shaded jar trong target/ (không install)
mvn -o package  # offline (deps đã cache)
```
- `maven-shade-plugin` → một fat jar (launch theo main-class). Tên artifact (`binance-java-sdk-1.2.4`) là legacy/upstream — đây là app PRIVATE, không phải SDK published.
- `protobuf-maven-plugin` gen Java từ `src/main/proto/*.proto` lúc build bằng `protoc` tải về (cần mạng lần đầu). `os-maven-plugin` resolve platform classifier.

## ⚙️ mvn trên máy dev (Windows) — wrapper đã cắm
- System Maven `D:\java\apache-maven-3.5.2` trong PATH **cài hỏng** (thiếu `bin/mvn`) → terminal mới báo `mvn: command not found`.
- Đã cắm wrapper `C:\Users\pc\bin\{mvn,mvn.cmd}` (User PATH, đứng đầu) trỏ Maven bundled trong IntelliJ (`...\plugins\maven\lib\maven3`, hiện 3.9.9) + `JAVA_HOME=jdk-11.0.17`. **Terminal mới gọi `mvn` chạy luôn** (bash + PowerShell).
- Bash tự chọn IntelliJ mới nhất; nếu IntelliJ đổi version mà PowerShell lỗi → sửa path hardcode trong `mvn.cmd`.
