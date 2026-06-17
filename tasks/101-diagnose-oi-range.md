---
id: 101
status: TODO
touches_live_process: false
writes_242_data: false
resource: 226+local
---

# TASK-101: Chẩn đoán OI 2023 empty — dump key range per coin

## Bối cảnh
Tool 2 (`ExportFundingOiPerCoin`) báo empty cho năm 2023. Logic trong `writeCoin()`:
```java
TreeMap<Long, Float> oi = getMetricMap226(OiMetricSets.OI.set, ...);
if (oi == null || oi.isEmpty()) return 0;  // bỏ coin nếu không có data
```
Tool đọc **toàn bộ history** OI của coin từ Aerospike rồi filter theo `[start, end)`.
"Empty 2023" có thể do: (A) data OI trong Aerospike không có mốc nào thuộc 2023, hoặc
(B) data có nhưng bị lọc ra (timezone shift làm `start` lệch, key format khác).

**Cần xác định:** data OI trong Aerospike thực tế cover năm nào?

## Việc làm

### Bước 1: Viết tool Java diagnostic (CCD code)

Tạo file mới:
`src/main/java/com/binance/chuyennd/ai_ml/features/export/fundingv2/DiagnoseOiRange.java`

```java
package com.binance.chuyennd.ai_ml.features.export.fundingv2;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.research.oibackfill.OiMetricSets;
import com.binance.chuyennd.tradecore.Configs;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.text.SimpleDateFormat;
import java.util.*;

/**
 * TASK-101: Chẩn đoán range OI trong Aerospike — 5 coin đại diện, đếm record theo năm.
 * Chạy trên 226 (IS_KAGGLE_MODE=true để kết nối đúng), KHÔNG ghi gì.
 * Usage: java DiagnoseOiRange [BTCUSDT ETHUSDT BNBUSDT XRPUSDT SOLUSDT]
 */
public class DiagnoseOiRange {
    private static final Logger LOG = LoggerFactory.getLogger(DiagnoseOiRange.class);

    public static void main(String[] args) throws Exception {
        Configs.IS_HPO_MODE = false;
        Configs.IS_KAGGLE_MODE = true;
        SimpleDateFormat sdf = new SimpleDateFormat("yyyy-MM-dd");
        sdf.setTimeZone(TimeZone.getTimeZone("UTC"));

        // Moc UTC epoch (ms) cho dau nam
        long y2021 = 1609459200000L; // 2021-01-01
        long y2022 = 1640995200000L; // 2022-01-01
        long y2023 = 1672531200000L; // 2023-01-01
        long y2024 = 1704067200000L; // 2024-01-01
        long y2025 = 1735689600000L; // 2025-01-01
        long y2026 = 1767225600000L; // 2026-01-01

        String[] coins = args.length > 0 ? args
                : new String[]{"BTCUSDT", "ETHUSDT", "BNBUSDT", "XRPUSDT", "SOLUSDT"};

        for (String coin : coins) {
            TreeMap<Long, Float> oi = DataManagerAerospikeFloatSim.getMetricMap226(
                    OiMetricSets.OI.set, OiMetricSets.OI.bin, coin);
            if (oi == null || oi.isEmpty()) {
                LOG.info("COIN={} OI=EMPTY", coin);
                continue;
            }
            long minTs = oi.firstKey(), maxTs = oi.lastKey();
            int n2021 = count(oi, y2021, y2022);
            int n2022 = count(oi, y2022, y2023);
            int n2023 = count(oi, y2023, y2024);
            int n2024 = count(oi, y2024, y2025);
            int n2025 = count(oi, y2025, y2026);
            LOG.info("COIN={} total={} range=[{} .. {}] | 2021={} 2022={} 2023={} 2024={} 2025={}",
                    coin, oi.size(), sdf.format(new Date(minTs)), sdf.format(new Date(maxTs)),
                    n2021, n2022, n2023, n2024, n2025);
        }
        LOG.info("DONE");
    }

    private static int count(TreeMap<Long, Float> m, long from, long to) {
        return m.subMap(from, to).size();
    }
}
```

### Bước 2: Compile + chạy trên 226

```bash
# compile (Windows, từ Git Bash)
JAVAC="/c/Users/pc/.jdks/corretto-17.0.9/bin/javac"
JAR="C:/Users/pc/oi-fleet/binance-java-sdk-1.2.4-shaded.jar"
rm -rf /tmp/c101 && mkdir -p /tmp/c101
"$JAVAC" --release 11 -cp "$JAR" -d /tmp/c101 \
  src/main/java/com/binance/chuyennd/ai_ml/features/export/fundingv2/DiagnoseOiRange.java
```

Upload jar (hoặc dùng jar đã deploy trên 226) rồi SSH chạy:
```bash
ssh -i /c/Users/pc/.ssh/id_rsa_chuyennd -p 2222 root@103.157.218.226 \
  "java -Duser.timezone=Asia/Ho_Chi_Minh -Xmx4g -cp /root/java-run/binance-futures-java.jar \
   com.binance.chuyennd.ai_ml.features.export.fundingv2.DiagnoseOiRange 2>&1" \
  | grep -E "COIN=|DONE"
```

> Nếu jar trên 226 cũ (thiếu class mới), build + upload jar mới từ HEAD trước.

### Bước 3: Báo lại kết quả (điền vào đây)

Dán output của DiagnoseOiRange — ví dụ:
```
COIN=BTCUSDT total=105120 range=[2021-01-15 .. 2025-12-31] | 2021=8736 2022=17520 2023=17520 2024=17568 2025=43776
```

Tôi (CDK) sẽ đọc kết quả và quyết định fix (timezone shift / backfill thiếu / range sai).

## An toàn
- KHÔNG ghi gì vào Aerospike, chỉ đọc.
- KHÔNG đụng process live/ingest.
- Nếu jar trên 226 đã có class DiagnoseOiRange (từ lần deploy trước) → chạy luôn, không cần rebuild.
