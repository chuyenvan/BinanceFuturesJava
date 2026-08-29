# DCA-OFF ABLATION — kế hoạch + đề xuất diff Java (chờ master áp)

> Mục tiêu: đo đóng góp DCA (pipeline `dca_ablation`) và đo edge model khi DCA cứng
> (pipeline `edge_dca_hard`). Cả hai cần **ép DCA không trigger** — mà hệ hiện tại
> KHÔNG làm được qua env. Tài liệu này ghi rõ gap + diff nhỏ để master áp trước khi chạy.

## 1. Vì sao KHÔNG ép được DCA-off qua env hiện tại (grep thực tế 2026-07-16)

- **Genome luôn có DCA trigger.** `StrategyWfoTask.java` (dòng 66-67):
  ```java
  put("DCA_LOSS_BIG_DOWN", -0.22, -0.08, false);
  put("DCA_TIME_BIG_DOWN", 3, 7, true);
  ```
  Mọi trial WFO đều tối ưu 2 gene này trong vùng KÍCH HOẠT DCA. Không có giá trị
  "vô hiệu" trong range.
- **Không có env SIM_DCA_\*.** `Configs.java` block `static { ... SIM_* }` (dòng ~296-305)
  chỉ có: `SIM_OFF_FLAT_HARD, SIM_MIN_MOMENTUM_15M, SIM_AI_DYNAMIC_MIN,
  SIM_PREDICT_SYMBOL_RATE_MAX, SIM_RATE_PROFIT_STOP_MARKET, SIM_BREAKER_MODE,
  SIM_BREAKER_MARGIN_HALT, SIM_MS_DOWN_BIG_AVG`. **KHÔNG có cờ tắt DCA.**
- `BREAKER_MODE=DCA` chỉ *ngừng nhồi khi cụm lỗ sâu* (không tắt hẳn DCA), và WfoWorker
  đã ép `Configs.BREAKER_MODE="OFF"`. Không dùng để tắt DCA sạch được.

**Kết luận:** cần thêm 1 env `WFO_DISABLE_DCA` + guard ở entrypoint DCA. Nút `wfo_fanout`
đã hỗ trợ truyền env này qua `extra_env` (áp cho Oracle worker); chỉ chờ Java đọc nó.

## 2. Đề xuất diff Java NHỎ (không đổi logic khi tắt = false → hành vi cũ 100%)

### 2a. `Configs.java` — thêm cờ đọc từ env (đặt cạnh block ABLATION_MODE, ~dòng 226)

```java
// WFO ABLATION: tat cung DCA de do dong gop DCA (chi backtest). Mac dinh false = giu nguyen.
public static boolean WFO_DISABLE_DCA = "1".equals(System.getenv("WFO_DISABLE_DCA"))
        || "true".equalsIgnoreCase(String.valueOf(System.getenv("WFO_DISABLE_DCA")));
```

### 2b. `DcaProcessor.java` — guard đầu 2 entrypoint, return rỗng khi tắt

```java
public static <K> List<K> getDCA(MarketLevelChange levelChange, Long time, Float budget,
                                 Map<K, OrderTargetInfoTest> symbol2OrderRunning) {
    if (Configs.WFO_DISABLE_DCA) return java.util.Collections.emptyList();   // <-- THEM
    return symbol2OrderRunning.entrySet().stream()
            ...
}

public static List<String> getDCAProduction(MarketLevelChange levelChange, Long time, Float budget,
                                             Map<String, PositionRisk> symbol2OrderRunning) {
    if (Configs.WFO_DISABLE_DCA) return java.util.Collections.emptyList();   // <-- THEM (an toan, prod khong set env nay)
    return symbol2OrderRunning.entrySet().stream()
            ...
}
```

> Chỉ 1 dòng guard mỗi hàm, đặt NGAY ĐẦU. `getDCA` là entrypoint backtest (được
> `BackTestEngine`/simulator gọi). Khi `WFO_DISABLE_DCA` không set → `false` → không đổi gì.
> (Nếu muốn chặt hơn có thể thêm guard tương tự ở `DcaUtils.shouldDca(...)` return `false`,
> nhưng chặn ở `getDCA` đã đủ vì mọi quyết định nhồi đi qua đó.)

### 2c. Rebuild + verify

1. `mvn -q -DskipTests package` → tạo jar mới (đặt tên rõ, ví dụ `preflight-v42-dcaoff.jar`
   hoặc giữ tên `preflight-v42.jar` nếu backward-compatible — guard mặc định OFF nên an toàn).
2. Verify 1 window: `WFO_DISABLE_DCA=1 java -cp <jar> ...VerifyOneWindow` → log phải cho thấy
   0 lệnh DCA (số leg = 1 trên mọi cụm). So với `WFO_DISABLE_DCA=0` cùng window → có nhồi.
3. Bump kernel dataset Kaggle (nếu muốn fan-out đồng bộ): jar mới + đảm bảo notebook
   truyền `WFO_DISABLE_DCA=1` (và `ABLATION_MODE` cho `edge_dca_hard`) — xem mục 3.

## 3. Lưu ý fan-out Kaggle (env baked, KHÔNG nhận extra_env runtime)

`wfo_fanout` truyền `extra_env` (WFO_DISABLE_DCA / ABLATION_MODE) **chỉ cho Oracle worker**.
Kaggle kernel chạy từ notebook + dataset đã đóng gói → env phải **baked** trong notebook.
Vì cả 2 tầng dùng CHUNG jobstore 226, nếu Kaggle không cùng env sẽ **nhiễm bẩn** phép đo.

Hai lựa chọn khi chạy ablation:
- **(A) Đồng bộ:** bump kernel dataset + sửa notebook template để set các env này, rồi fan-out đủ 6 node.
- **(B) Oracle-only (an toàn, chậm hơn):** chạy pipeline với `KAGGLE_KERNELS=0`
  (`pipe_run dca_ablation KAGGLE_KERNELS=0`) → chỉ 2 Oracle worker cùng env, không nhiễm.

Gate đầu mỗi pipeline (`gate_java` / `gate_setup`) hỏi rõ lựa chọn này trước khi chạy.

## 4. Sau khi áp xong

- Cập nhật `orchestrator/profiles/wfo-fanout.json` → `verified: <ngày>` sau run đầu sạch.
- Chạy: `pipe_run dca_ablation` và `pipe_run edge_dca_hard` (tuần tự, cùng jobstore).
- `ce --sync bg_selftest` phải PASS trước khi dùng (đã sửa mcp_tools-v3.py).
