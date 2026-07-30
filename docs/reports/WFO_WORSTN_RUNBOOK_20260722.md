# WFO WORST-N SWEEP — RUNBOOK ĐÃ SỬA (đối chiếu CE thực tế, 2026-07-22)

> ⚠️ File này THAY THẾ phần lệnh trong `wfo-worst-n-sweep-roadmap.md` (bản notebooklm).
> Roadmap notebooklm có 4 lỗi khiến sweep chạy SAI ÂM THẦM. Chi tiết + fix ở dưới.
> Chưa build/deploy/bắn fleet — chờ Uni chốt (mục "QUYẾT ĐỊNH CẦN UNI").

---

## 0. TÓM TẮT LỖI ROADMAP vs CODE THỰC (đã verify bằng đọc source)

| # | Roadmap notebooklm | Code thực tế | Hậu quả nếu chạy y roadmap |
|---|---|---|---|
| 1 | `SELECTOR_INVERT=true` | `Configs.SELECTOR_INVERT = "1".equals(getenv)` (chỉ nhận `"1"`) | `true` != `1` → **INVERT TẮT → chạy BEST-N (hệ cũ thua -2589%)**, không phải Worst-N |
| 2 | `WFO_DISABLE_DCA=true` | `"1".equals(getenv)` | `true` → DCA **KHÔNG tắt** dù roadmap tưởng đã tắt |
| 3 | `NUMBER_ENTRY_EACH_SIGNAL=3/5/8` điều khiển "Worst-N" | Configs không đọc env cho biến này; **static = 2**. Và khối selector-invert lấy **TẤT CẢ** candidate qua gate (không cap N) | N-sweep **vô hiệu** — không đổi gì; "Worst-N breadth" không có lever |
| 4 | 1 lệnh fan-out áp cho cả Oracle + 5 Kaggle | `extra_env` trong `wfo_fanout` **chỉ áp Oracle worker**; Kaggle kernel dùng env **bake trong notebook/dataset** | Oracle chạy config A, Kaggle chạy config bake sẵn (khác) → **cùng đổ vào 1 jobstore `strategy_window` → kết quả TRỘN, hỏng** |
| — | "17 cửa sổ" (Phần 3) rồi "16 cửa sổ" (Bước 4) | `buildWindows()` + `WFO_MAX_OOS_DATE=20260101` → **16 window**. "17" là số GENE (docstring StrategyWfoTask), không phải window | Điều kiện gom báo cáo dùng 16 là đúng |

**Kết luận:** chạy đúng nguyên văn roadmap = chạy Best-N (thua), N không tác dụng, kết quả Oracle/Kaggle trộn. Phải sửa trước.

---

## 1. FIX CODE ĐÃ LÀM (branch code, OFF-by-default, byte-identical khi không set)

Thêm knob mới, KHÔNG đụng `NUMBER_ENTRY_EACH_SIGNAL` (biến này dùng chung cả path LIVE — tránh rủi ro).

**`Configs.java`** — thêm:
```java
public static final int SELECTOR_TOPN = System.getenv("SELECTOR_TOPN") != null
        ? Integer.parseInt(System.getenv("SELECTOR_TOPN").trim()) : -1;   // -1 = OFF = uncapped
```

**`SimulatorMarketLevelTicker1MStopLoss.java`** (khối selector `symbol2Pred`) — cap số candidate:
```java
int nSel = (Configs.SELECTOR_TOPN > 0) ? Math.min(nPass, Configs.SELECTOR_TOPN) : nPass;
// INVERT=1: lấy nSel coin TỆ-nhất (oversold); INVERT=0: nSel coin TỐT-nhất. TOPN=-1 -> nSel=nPass -> cũ.
```
+ log 1 dòng đầu mỗi backtest: `[SELECTOR-CFG] INVERT=.. TOPN=.. SCORE_MAX=..` để verify config đã ăn.

> `SELECTOR_TOPN` = lever "Worst-N breadth" đúng nghĩa (số coin bị-ghét mở đồng thời tại mỗi mốc tín hiệu).
> Đây là DIỄN GIẢI của tôi về ý "Worst-3/5/8". **Cần Uni xác nhận** (xem mục QUYẾT ĐỊNH).

---

## 2. LỆNH SWEEP ĐÃ SỬA (chạy TUẦN TỰ, KHÔNG song song 3 config)

Vì cả 3 config dùng chung strategy `strategy_window` + chung jobstore 226, mỗi `wfo_fanout` **reset** coordinator → **không chạy đồng thời 3 config**. Chạy lần lượt: fanout → chờ 16 DONE → report → fanout tiếp.

### Điều kiện tiên quyết (một lần)
1. `ce build_deploy preflight-v42.jar` — build jar Corretto-17 (đã có fix SELECTOR_TOPN) → scp Oracle → verify md5.
2. **Bake env vào 5 Kaggle kernel** (vì extra_env KHÔNG tới Kaggle): trong `WFO_KERNELS_DIR` mỗi kernel phải set `SELECTOR_INVERT=1` và `SELECTOR_TOPN=<N>` cho đúng config đang chạy. → nếu chưa làm được: **chạy Oracle-only** (`kaggle_kernels=0`) để đảm bảo đúng, chịu chậm hơn.

### Config Worst-3
```bash
ce wfo_fanout wfo_ds_oiz2022_75 preflight-v42.jar 30 42 2 5 long_invsel_N3 \
  "SELECTOR_INVERT=1,SELECTOR_TOPN=3,WFO_DISABLE_DCA=1,TIME_STOP_HOURS=24,ABLATION_MODE=A"
# chờ 16/16 DONE:  ce wfo_status   (lặp tới DONE=16)
ce wfo_report long_invsel_N3
```
### Config Worst-5 (baseline)
```bash
ce wfo_fanout wfo_ds_oiz2022_75 preflight-v42.jar 30 42 2 5 long_invsel_N5 \
  "SELECTOR_INVERT=1,SELECTOR_TOPN=5,WFO_DISABLE_DCA=1,TIME_STOP_HOURS=24,ABLATION_MODE=A"
ce wfo_report long_invsel_N5
```
### Config Worst-8
```bash
ce wfo_fanout wfo_ds_oiz2022_75 preflight-v42.jar 30 42 2 5 long_invsel_N8 \
  "SELECTOR_INVERT=1,SELECTOR_TOPN=8,WFO_DISABLE_DCA=1,TIME_STOP_HOURS=24,ABLATION_MODE=A"
ce wfo_report long_invsel_N8
```

> Đã bỏ `SIZE_MULT=1` (mặc định đã =1) và `NUMBER_ENTRY_EACH_SIGNAL` (không có tác dụng).
> `wfo_ds_oiz2022_75` = giá trị positional roadmap dùng; **cần xác nhận** đây là path dataset `_ff` thật trên Oracle (roadmap phần 1 lại ghi tên dataset `wfo-ds-ret2-4h-ff`). Nếu sai → `ce wfo_fanout` sẽ chạy nhưng dataset load sai.

Thứ tự positional (verify từ code): `wfo_fanout <ds> <jar> <n=samples> <seed> <oracle_workers> <kaggle_kernels> <tag> <extra_env>`. `30 42 2 5` = 30 samples HPO / seed 42 / 2 Oracle worker / 5 Kaggle kernel. ✅ đúng như roadmap.

---

## 3. GIÁM SÁT + NGHIỆM THU
```bash
ce wfo_status      # total/PENDING/RUNNING/DONE/FAILED + window FAILED
ce kaggle_slots    # trạng thái 5 kernel Kaggle
```
Report tự parse (ngưỡng pre-registered trong `StrategyWfoTask`, KHÔNG đổi):
- WFE trung vị ≥ **0.5** (chỉ tính trên window `oosNote=SUCCESS`)
- % window OOS dương ≥ **70%**
- maxDD OOS xấu nhất ≤ **50%** vốn (dùng `ddPct`, không phải abs USD)

**Verify config đã ăn:** grep log worker dòng `[SELECTOR-CFG] INVERT=true TOPN=3` — nếu thấy `INVERT=false` hoặc `TOPN=-1` là env chưa vào → DỪNG.

---

## 4. RỦI RO CÒN LẠI / GHI CHÚ
- Kết quả +712% (Worst-5 IS) trong roadmap **không có artifact tái lập trong repo** — coi là giả thuyết, để số OOS của WFO tự phán.
- `SELECTOR_TOPN`: nhánh INVERT=1 lấy N coin tệ nhất **bỏ gate nPass** (khớp proxy Kaggle); nhánh INVERT=0 cap trong nPass qua gate. Byte-identical khi TOPN=-1.
- Nhánh entry `levelChange` (getTopSymbolArray, dùng `NUMBER_ENTRY_EACH_SIGNAL=2`) **không bị** SELECTOR_TOPN đụng — path best-2 FOMO riêng, vẫn chạy song song → nghi phạm pha loãng edge nếu OOS xấu (ablation: thêm cờ tắt path này).
- (Ban đầu định không tự bắn; sau Uni uỷ quyền qua Desktop Commander → đã chạy, xem mục 5.)

---

## 5. TRẠNG THÁI THỰC THI (2026-07-22 ~23:05)

- `ce build_deploy /home/ubuntu/java/simulator/preflight-v42.jar` → **DEPLOY_OK** md5=1746068765005cf441f3bef1b6299b97 (compile pass, jar có SELECTOR_TOPN).
- Snapshot campaign cũ trước reset: `wfo_report_snapshot_before_worstn_20260722.md`.
- **Đã bắn Worst-5** (Oracle-only, full path): `ce wfo_fanout /home/ubuntu/claudedata/wfo_ds_oiz2022_75 /home/ubuntu/java/simulator/preflight-v42.jar 30 42 2 0 long_invsel_N5 SELECTOR_INVERT=1,SELECTOR_TOPN=5,WFO_DISABLE_DCA=1,TIME_STOP_HOURS=24,ABLATION_MODE=A` → 2 Oracle worker RUNNING.
- **VERIFIED** log: `[SELECTOR-CFG] INVERT=true TOPN=5 SCORE_MAX=-1.0` (config ăn đúng — chứng minh bug `=true` của roadmap sẽ thành Best-N).
- **Auto-advance:** scheduled task `wfo-worstn-sweep-advance` (mỗi giờ, phút 19) chờ DONE=16 → `wfo_report` → bắn N3 → N8 tuần tự, idempotent theo `wfo_worstn_sweep_state.json`.
- ⚠️ Scheduled task chỉ chạy khi app Cowork mở; đóng app thì chạy lại khi mở. Nên bấm "Run now" 1 lần để pre-approve Desktop Commander.
- Ước lượng ~4h/config, 3 config tuần tự ~12h.
