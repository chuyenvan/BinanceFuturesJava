---
id: 106b
status: TODO
owner: —
updated: 2026-06-20
touches_live_process: false
writes_242_data: false
resource: kaggle + 226 (read-only Aerospike)
require_review: false
depends_on: []
---

# TASK-106b: Xuất lại feature Tool1 (60G → ~5G) bằng EntrySignalFilter — CHẠY ĐẦU-CUỐI, TỰ QUYẾT

> ⚠️ Bạn là CCD headless chạy ĐỘC LẬP, TỰ QUYẾT, KHÔNG hỏi người dùng. Đọc CLAUDE.md + KAGGLE_RULES.md trước.
> Chỉ 1 CCD làm task này. Nếu thấy CCD khác đang chạy 106/106b → DỪNG, báo, không song song.
> Ghi tiến trình liên tục (mỗi bước 1 dòng có timestamp) vào `/d/claudedata/agent106b.log`.
> Cuối cùng ghi report `docs/reports/106.md` + commit + push.

## MỤC TIÊU DUY NHẤT
Xuất lại dataset feature Tool1 (40 cột) cho 2021→2026, ĐỦ + ĐÚNG, kích thước nhỏ (~5G thay vì 60G)
nhờ `EntrySignalFilter` (đã wire vào Tool1). Đủ để train funding selector 039. Không làm gì ngoài việc này.

## QUY TẮC SỐNG CÒN (vi phạm = hỏng việc / lộ secret / crash máy)
1. **Ổ C đã full 3 lần gây crash.** MỌI log/output/file tải về → `/d/claudedata`. TUYỆT ĐỐI không ghi `/tmp`, `~/`, AppData (đều ổ C). `kaggle kernels output -p /d/claudedata/...` — KHÔNG BAO GIỜ `-p /tmp`.
2. **Sanitize trước khi upload Kaggle.** `src/main/java/com/binance/chuyennd/config/PrivateConfig.java` PHẢI ở placeholder (`API_KEY="SANITIZED_FOR_KAGGLE_UPLOAD"`, không phải secret thật) trước khi `mvn package`. Sau build, verify: `unzip -p target/binance-java-sdk-1.2.4-shaded.jar com/binance/chuyennd/config/PrivateConfig.class | grep -a SANITIZED` phải có match. Nếu jar chứa secret thật → DỪNG, KHÔNG upload.
3. **226 Aerospike READ-ONLY.** Không đụng live trading (BinanceOrderTradingManager), ingest (BinanceDataIngestor), Aerospike-write, Redis, 242. Chỉ kill PID do session này spawn theo PID cụ thể, KHÔNG pkill/killall java.
4. **Filter tham số KHÓA CỨNG** (`EntrySignalFilter`: vol-avg-30m≥2k + top-10% |rate30m| cross-sectional). Đã validate đa-giai-đoạn. KHÔNG tự sửa tham số. Validate FAIL vì filter → DỪNG báo, không sửa.
5. **TEST TRƯỚC, FULL SAU.** Tuyệt đối KHÔNG push cả 8 kernel rồi mới phát hiện lỗi. Push 1 kernel test, validate xong mới push phần còn lại. (Bài học: đã từng chạy vài tiếng mới lòi lỗi nhỏ.)
6. SLF4J/Log4j2, không System.out.

## ĐIỂM BẮT ĐẦU (trạng thái đã biết — cập nhật 2026-06-20)

### Commits cần có (HEAD hiện tại ✅)
- `532e0b8` — **fix(Tool1): chot minutesToRead=1440 lam CHUAN DUY NHAT** ← COMMIT CUỐI CÙNG, chuẩn
- `a3a1e31` — (quay lại 10080, bị reverted bởi 532e0b8)
- `1e8c2f2` — retry batch read + log lỗi cụ thể

### ⚠️ JAR STAGED ĐÃ STALE — PHẢI REBUILD
- Jar tại `/c/Users/pc/java-run-lc-stage/binance-java-sdk-1.2.4-shaded.jar`: Jun 19 20:34 (98876658 bytes)
- Commit `532e0b8` (chốt 1440): Jun 19 21:24 → **jar build TRƯỚC commit cuối → jar có minutesToRead=10080, sai**
- **Phải rebuild từ HEAD trước khi upload dataset và push kernels**

### Trạng thái còn lại
- `PrivateConfig.java`: đã SANITIZED ✅ (`API_KEY="SANITIZED_FOR_KAGGLE_UPLOAD"`)
- `validate_106.py`: có tại `/d/claudedata/validate_106.py` ✅
- Kernel folders: `/c/Users/pc/ff40-{2021,2022,2023,2024h1,2024h2,2025h1,2025h2x,2026x}` ✅ (mỗi cái có kernel-metadata.json + ff40.py)
- Dataset staging: `/c/Users/pc/java-run-lc-stage/` → `chuyendinh/java-run-lc`
- Output cũ tại `/d/claudedata/oi-ff40-2021/` (từ run trước, stale — xóa trước validate)
- ⚠️ Lỗi đã gặp: `Batch max requests exceeded` → push **≤4 kernel cùng lúc** (KHÔNG 5+)

## CÁC BƯỚC

### B1. Build jar mới từ HEAD (532e0b8, minutesToRead=1440)
```bash
cd /e/educa/source/github/20260415/BinanceFuturesJava
git pull origin module
git log --oneline -3   # phai thay 532e0b8 dau tien
# xac nhan source co 1440
grep "minutesToRead = " src/main/java/com/binance/chuyennd/ai_ml/features/export/fundingv2/ExportFeaturesForPythonTool.java | head -1  # phai = 1440
# verify PrivateConfig sanitized
grep -E 'API_KEY|SECRET_KEY' src/main/java/com/binance/chuyennd/config/PrivateConfig.java  # phai = SANITIZED_FOR_KAGGLE_UPLOAD
mvn package -DskipTests -q > /d/claudedata/106b-build.log 2>&1; echo "BUILD EXIT=$?"
# verify jar co 2 class + sanitized (KHONG dung /tmp)
unzip -l target/binance-java-sdk-1.2.4-shaded.jar | grep -E "EntrySignalFilter.class|DataManagerAerospikeFloatSim.class"
unzip -p target/binance-java-sdk-1.2.4-shaded.jar com/binance/chuyennd/config/PrivateConfig.class > /d/claudedata/pc.class
grep -a SANITIZED /d/claudedata/pc.class && echo "JAR SACH" || { echo "STOP: JAR CO SECRET"; exit 1; }
```
Nếu jar thiếu class hoặc không sanitized → DỪNG, báo.

### B2. Upload jar lên Kaggle dataset
```bash
cp target/binance-java-sdk-1.2.4-shaded.jar /c/Users/pc/java-run-lc-stage/binance-java-sdk-1.2.4-shaded.jar
cd /c/Users/pc/java-run-lc-stage && kaggle datasets version -p . -m "106b: EntrySignalFilter + retry batch"
# cho ready
while [ "$(kaggle datasets status chuyendinh/java-run-lc 2>&1 | tr -d '[:space:]')" != "ready" ]; do sleep 15; done
kaggle datasets files chuyendinh/java-run-lc | grep shaded.jar   # xac nhan size jar moi
```

### B3. Xóa Tool1 cũ local (giữ OI)
```bash
rm -rf /d/claudedata/oi-ff40-*/features_export_python_v3   # CHI Tool1, GIU features_oi_percoin_v1
df -h /c | tail -1   # xac nhan khong cham o C
```

### B4. TEST 1 KERNEL (ff40-2021) — cổng quyết định, BẮT BUỘC trước khi push phần còn lại
```bash
cd /c/Users/pc/ff40-2021 && kaggle kernels push -p .
# cho COMPLETE (poll moi 60s)
while ! kaggle kernels status chuyendinh/ff40-2021 2>&1 | grep -qiE "complete|error"; do sleep 60; done
kaggle kernels status chuyendinh/ff40-2021
# tai output + validate
rm -rf /d/claudedata/ff40-2021-out && kaggle kernels output chuyendinh/ff40-2021 -p /d/claudedata/ff40-2021-out
python /d/claudedata/validate_106.py /d/claudedata/ff40-2021-out/features_export_python_v3
grep -c "AEROSPIKE-FAIL" /d/claudedata/ff40-2021-out/*.log   # phai = 0 (khong mat data)
```
**Tiêu chí TEST PASS (pre-register):**
- (a) Tool1 2021 size << bản cũ (~vài MB→vài trăm MB, KHÔNG phải GB). Nếu vẫn GB → filter không áp → DỪNG.
- (b) `AEROSPIKE-FAIL` = 0 trong log (retry đã cứu hết; nếu >0 → data mất, DỪNG báo).
- (c) Format đúng (size chia hết 170), cột hợp lý (coinFunding∈[-0.01,0.01], rsi1H∈[0,100], rangePos24H∈[0,1]).
- (d) Cross-sectional: #coin tại 1 mốc ≈ 10% số coin có volume (không phải toàn bộ ~780).
  TEST FAIL bất kỳ điểm nào → DỪNG, ghi rõ vào `docs/reports/106.md` + `/d/claudedata/agent106b.log`, KHÔNG push tiếp.

### B5. Push 7 kernel còn lại (SO LE để tránh quá tải 226)
Chỉ làm nếu B4 PASS. Push theo đợt ≤4 kernel cùng lúc (không dồn 5+ vì 226 + 2 VPS ngoài cũng đọc):
- Đợt 1: ff40-2022, ff40-2023, ff40-2024h1, ff40-2024h2
- Chờ ≥2 cái COMPLETE rồi đợt 2: ff40-2025h1, ff40-2025h2x, ff40-2026x
```bash
for k in ff40-2022 ff40-2023 ff40-2024h1 ff40-2024h2; do (cd /c/Users/pc/$k && kaggle kernels push -p .); sleep 20; done
# cho bot slot... rồi push 3 cai con lai tuong tu
```
Poll tới khi cả 8 COMPLETE. Tải log mỗi kernel về `/d/claudedata`, grep `AEROSPIKE-FAIL` mỗi cái (phải = 0).

### B6. VALIDATE TỔNG 5 tiêu chí
```bash
# tai het output 8 kernel ve /d/claudedata/oi-ff40-*/
# chay validate tong
python /d/claudedata/validate_106.py /d/claudedata/oi-ff40-*/features_export_python_v3
```
Tiêu chí: (1) size tổng ~3-7G (>15G→filter sai, DỪNG); (2) %giữ 6-12%; (3) phân bố cột hợp lý;
(4) cross-sectional ≈10%/mốc; (5) regime coverage — 2022 (crash) + 2024 (bull) đều có record; (6) tổng `AEROSPIKE-FAIL` = 0.

### B7. Đóng task
Ghi `docs/reports/106.md`: size trước/sau từng năm, %giữ, kết quả 6 tiêu chí PASS/FAIL, số AEROSPIKE-FAIL.
Set 106/106b = DONE nếu PASS. `git add` report + commit (`Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>`) + push origin module.
Báo: data Tool1 mới sẵn sàng cho merge 039.

## CÔNG CỤ
- mvn: `/c/Users/pc/bin/mvn` (có sẵn). Build: `mvn package -DskipTests -q`.
- SSH 226: `ssh -i /c/Users/pc/.ssh/id_rsa_chuyennd -p 2222 -o BatchMode=yes -o ConnectTimeout=10 root@103.157.218.226` (lọc noise: `| grep -vE "post-quantum|store now|upgraded|openssh"`). Aerospike 226 port 3222 ns ticker.
- kaggle CLI: trong PATH, gọi `kaggle ...` trực tiếp.
- Compile-on-226 KHÔNG được (javac Java 8 vs jar Java 11) — chỉ build local bằng mvn.

## (CCD điền khi xong)
- B1: build exit, jar có class? sanitized? (y/n)
- B4: ff40-2021 size, AEROSPIKE-FAIL count, TEST PASS/FAIL
- B5: kernel nào push, size mỗi năm
- B6: size tổng, %giữ, 6 tiêu chí, tổng AEROSPIKE-FAIL
- B7: commit + report hash