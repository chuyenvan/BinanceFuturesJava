# TASK-128 — Đo chất lượng model WFO (scripts)

Đo IC / decile-lift / hit-rate của gate-market + funding-selector trong dataset WFO leak-free.
**Semantics chốt tại** `docs/reports/model_quality_wfo_20260704.md` (ĐỊNH NGHĨA PRE-REGISTERED — đọc trước).

## Kiến trúc
- Nhãn realized = **Java** (tái dùng đúng code `ValidateOldPredictVsRealized` + `ExportFundingLabel`; ticker file
  là Java-serialized → không đọc được bằng Python). Tool: `com.binance.chuyennd.ai_ml.validation.Task128ModelQuality`.
- `analyze.py` = thuần tiêu thụ 2 CSV Java → IC/decile/hit-rate theo quý (đã test synthetic: chiều đúng).

## Chạy (Kaggle CPU — jar đã sanitize, ở dataset `chuyendinh/t128-model-quality-jar`)
Datasets mount: `t128-model-quality-jar` (jar+config) + `wfo-dataset-wf-leakfree` + `hpo-ticker-daily`.
```bash
# 1. validate-small (2024Q1) — BẮT BUỘC trước full
cd scripts/model_quality/kernel_validate && kaggle kernels push -p .
kaggle kernels status chuyendinh/model-quality-1     # poll tới COMPLETE
kaggle kernels output chuyendinh/model-quality-1 -p /d/claudedata/mq1-out
python scripts/model_quality/analyze.py /d/claudedata/mq1-out/t128_out
# 2. full (toàn kỳ) sau khi validate PASS
cd scripts/model_quality/kernel_full && kaggle kernels push -p .
kaggle kernels status chuyendinh/model-quality-full
```
⚠️ Slot CPU tối đa 5 (KAGGLE_RULES §1). Kiểm `FREE` trước khi push. **KHÔNG** đụng `wfo-worker-*` (job khác).

## Rebuild jar (khi đổi tool)
```bash
mvn -q -DskipTests clean package     # -> target/binance-java-sdk-1.2.4.jar (fat, PrivateConfig SANITIZED)
cp target/binance-java-sdk-1.2.4.jar /d/claudedata/t128-jar-stage/
cd /d/claudedata/t128-jar-stage && kaggle datasets version -p . --dir-mode zip -m "rebuild <sha>"
```

## Fallback Oracle (nếu Kaggle bận + Oracle rảnh RAM)
`java -Duser.timezone=Asia/Ho_Chi_Minh -Xmx2g -cp <jar> ...Task128ModelQuality` với CWD chứa `config.properties`
trỏ Aerospike LOCAL (AEROSPIKE_READ_CLUSTER=226, AEROSPIKE_HOST_226=127.0.0.1). WFO_DATA_DIR + TICKER_DIR = file.
⚠️ nice -n 15, chỉ khi Oracle đủ RAM trống (không đụng WFO vế-C đang chạy).
