# RUNBOOK — Chạy Data Preflight FULL trên Oracle / Kaggle (2026-07-11)

> Theo luật CORE "validate-theo-nơi-chạy": validate chạy TẠI nơi dataset ở (Oracle gốc; Kaggle bản sao).
> Entrypoint: `com.binance.chuyennd.ai_ml.validation.preflight.RunPreflightFull` (env-driven, 21 validator, đóng stamp).
> Máy dev CHỈ build jar; KHÔNG chạy validate ở dev.

## 0. Build jar (máy dev — đã có toolchain)
```bash
cd /e/educa/source/github/20260415/BinanceFuturesJava
mvn -o package                       # ra target/binance-java-sdk-1.2.4-shaded.jar (fat jar)
```

## 1. Oracle (NGUỒN GỐC dataset — chạy đầu tiên)
Điều kiện: Oracle có bin dataset (`/home/ubuntu/claudedata/wfo_dataset/`), Aerospike ns=test @127.0.0.1:3222,
selector pred (`/home/ubuntu/selector_pred_out/`). config.properties tại CWD có `AEROSPIKE_NAMESPACE=test`.
```bash
scp target/binance-java-sdk-1.2.4-shaded.jar <user>@<oracle>:/home/ubuntu/java/preflight.jar
ssh <user>@<oracle>
  cd /home/ubuntu/java
  FP=$(md5sum claudedata/wfo_dataset/manifest.txt | cut -d' ' -f1)   # fingerprint dataset
  PREFLIGHT_ENV=oracle \
  PREFLIGHT_FINGERPRINT=$FP \
  WFO_DATA_DIR=/home/ubuntu/claudedata/wfo_dataset \
  WFO_FUNDING_PRED_DIR=/home/ubuntu/selector_pred_out \
  WFO_SMART_CACHE=1 \
  PREFLIGHT_AS_HOST=127.0.0.1 PREFLIGHT_AS_PORT=3222 \
  java -Xmx11g -cp preflight.jar com.binance.chuyennd.ai_ml.validation.preflight.RunPreflightFull \
       claudedata/preflight_full_oracle.md
  # PASS => ghi claudedata/wfo_dataset/validation_stamp.properties (env=oracle, fingerprint=$FP)
```
Đọc report `preflight_full_oracle.md`: verdict + bảng 21 check + số đo. BLOCK-fail nào → xử (backfill/fix) → chạy lại tới PASS.

## 2. Kaggle (bản sao sync từ Oracle — re-validate theo baseline)
Trong kernel (dataset đã giải nén .bin), sau khi sync dataset từ Oracle:
```python
# fingerprint PHẢI khớp cái Oracle đã stamp (cùng dataset). Nếu Kaggle giải nén đổi byte → md5 khác → re-validate là ĐÚNG.
!FP=$(md5sum /kaggle/working/wfo_dataset/manifest.txt | cut -d' ' -f1); \
 PREFLIGHT_ENV=kaggle PREFLIGHT_FINGERPRINT=$FP \
 WFO_DATA_DIR=/kaggle/working/wfo_dataset WFO_FUNDING_PRED_DIR=/kaggle/working/selector_pred \
 WFO_SMART_CACHE=1 PREFLIGHT_AS_HOST=127.0.0.1 PREFLIGHT_AS_PORT=3222 \
 java -cp /kaggle/working/preflight.jar \
   com.binance.chuyennd.ai_ml.validation.preflight.RunPreflightFull /kaggle/working/preflight_full_kaggle.md
```
> Nếu Kaggle không có Aerospike: các validator Aerospike sẽ báo lỗi hạ tầng (NEEDS_HUMAN) tới khi làm task 207
> (SKIP-semantics) — khi đó Kaggle chỉ chạy nhóm bin (A2/E/B/C1/C4), Oracle chạy nhóm Aerospike, gộp stamp.

## 3. Cổng WFO (sau khi PASS)
Chỉ khi có stamp hợp lệ (fingerprint+env), mới cho WFO chạy — hook `WfoCoordinator` (task 206, CHƯA cắm để
không chặn WFO đang chạy). Kiểm tay:
```bash
java -cp preflight.jar com.binance.chuyennd.ai_ml.validation.preflight.PreflightValidators   # đăng ký 21
cat claudedata/wfo_dataset/validation_stamp.properties                                        # xem stamp
```

## 4. Layer nguồn (Aerospike raw 226/242) — validate riêng
Chạy đọc 226 (đã thử từ dev): `RunPreflight226` (A5/A4/D1/D3/F2 nhẹ). Nhóm nặng (A3 ghost, C2/C3 kline 2.8M,
D2 gap) nên chạy TẠI 226/Oracle, không qua mạng từ dev.
