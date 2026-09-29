# RESULT_F0_G015X26 — tái lập `predwf_G015x26` + độ nhạy bins map (item 3 + 4a)

Ngày: 2026-09-29. Task: **F0** (item 3 + 4a). Pre-reg: `docs/prereg/PREREG_F0_REPRO.md` (`f675e5ec`).

---

## 1. Tái lập `predwf_G015x26` (16 fold DEV) — PASS

Phương pháp: **predict từ 18 model gốc đã lưu** (`claudedata/predwf_G015/model_f{0..17}_4h.json`)
bằng `research/pipeline/g015x26_train.py` (KHÔNG train). Nhãn `retEnd_4h > 0.015` (net015), 45
feature (f0..f39 + 5 OI), XGB 400/depth 5/seed 42/hist, WFO expanding purge 72h, 16 cutoff
`20220101..20251001`. Output: `/home/ubuntu/f0_repro/g015x26_regen/` (16 file).

| chỉ số | kết quả (16/16 fold) |
|---|---|
| khoá `(ts,symId)` | **trùng tuyệt đối** |
| spearman (rank-IC) | **1.00000000** |
| `max\|d\|` | **1.192e-07** = 1 ULP float32 |
| **% giá trị float32 bit-identical** | **82,98 % – 88,55 %** (min 0.8298) |
| sha256 byte-identical | **KHÔNG** (thứ tự dòng trong cùng `ts` khác — pipeline gốc `sort_values("ts")` quicksort không ổn định) |

⇒ **PASS ngưỡng pre-reg** (spearman ≥ 0.999 VÀ max|d| ≤ 1 ULP). ~14 % giá trị lệch đúng 1 ULP
(cuối nổi float32), ~86 % bit-identical. Đây là **khiếm khuyết determinism của pipeline gốc**,
không phải mất input — khớp G3 (`docs/experiment/G3_X26_RECOVERY.md`), bổ sung % bit-identical mà G3 chưa báo.

## 2. Tái lập bins map `predwf_map_s1a2_x1` (item 4a) — khác bản cũ

Rebuild `x1_build_map.py s1a2x1` với `pred_s1a2x1.parquet` (S1, đã byte-reproducible — cổng G3
PASS) + `predwf_G015x26` **tái lập** → `/home/ubuntu/f0_repro/predwf_map_s1a2_x1/` (16 bin).

So với bản đang dùng (`/home/ubuntu/predwf_map_s1a2_x1/`):

| chỉ số | kết quả |
|---|---|
| khoá `(ts,symId)` | **trùng 16/16 fold** (không mất/thêm dòng nào) |
| giá trị `p0` khác | **4 796 414 / 35 806 379 = 13,40 %** |
| % bit-identical | 82,97 % – 88,23 % |
| sha256 | KHÁC 16/16 |

Cơ chế: 1 ULP của `G015x26` + thứ tự `sort_values` → `build_map.py` `rank(method="first")` pha
thế các coin có `p` gần bằng nhau trong tick → gán lại giá trị `P(win)` cho coin khác. **Multiset
`P(win)` mỗi tick gần như giữ nguyên** (chỉ lệch 1 ULP) ⇒ **gate không đổi**.

## 3. Độ nhạy sim R4 (item 4b) — CHƯA CHẠY SIM, dùng tiền lệ G4

**Chưa chạy sim Kaggle** (xem §4 — lý do). Nhưng tiền lệ `docs/experiment/G4_RECIPE_C4.md` §4 đã đo
cùng loại lệch này trên C3/X1: sai số 1 ULP bị khuyếch đại thành 0.3715 ở map, và sim chỉ lệch
**khoá `(sym,start)` 99,90 %** (0,1 % entry đổi), `win%`/`TSloss%`/`mP|SL` **= 0 tuyệt đối**, chỉ
`mean(margin)` +0,18 % — **md5 `printDone` KHÁC**.

⇒ **Dự báo [SUY LUẬN] cho R4**: md5 `printDone` khác `06fd6e9a…`, `n` lệch ~0,1 % (≈ 2 lệnh),
rate chất lượng không đổi. **Độ nhạy NHỎ** — việc tái lập KHÔNG đổi kết luận của R4. Cần chạy sim
thật để xác nhận (lệnh ở §5).

## 4. Vì sao chưa chạy sim Kaggle (blocker tài nguyên, không phải logic)

1. **Đĩa Oracle 95 % đầy (11 GB trống).** Chạy sim R4 với bins tái lập đòi rebuild dataset WFO
   (`ExportWfoDataset` → `funding.bin` 4,14 GB) + stage lại bundle 5,3 GB + upload Kaggle —
   cần ~10 GB, sát giới hạn, rủi ro đầy đĩa giữa chừng (vi phạm "KHÔNG xoá dữ liệu").
2. `funding.bin` **embed bins lúc build dataset** ⇒ phải rebuild dataset, KHÔNG thể chỉ swap bins
   (`KAGGLE_SIM_48M` §2). Đổi bins trong bundle không đổi kết quả sim.

## 5. Lệnh chạy sim R4 với bins tái lập (khi có đĩa/duyệt)

```bash
# (a) copy profile R4, doi WFO_FUNDING_PRED_DIR -> bins tai lap
cp profiles/r4_kg0_k16_f015_g155.properties /tmp/r4_repro.properties
sed -i 's#/home/ubuntu/predwf_map_s1a2_x1#/home/ubuntu/f0_repro/predwf_map_s1a2_x1#' /tmp/r4_repro.properties
# (b) rebuild dataset (Oracle)
R=/home/ubuntu/src/BinanceFuturesJava; JAR=$R/target/binance-java-sdk-1.2.4.jar
cd /home/ubuntu/java/devrun && cp -f $R/configs/sim_dev.properties config.properties
env TRADING_PROFILE=/tmp/r4_repro.properties WFO_SET_PRED=ai_pred_market_gate_wfo \
  WFO_SEL_HORIZON_IDX=0 WFO_CODE_SHA=$(cd $R && git rev-parse --short HEAD) \
  java -Duser.timezone=Asia/Ho_Chi_Minh -Xmx14g -cp $JAR \
  com.binance.chuyennd.ai_ml.wfo.framework.ExportWfoDataset /home/ubuntu/f0_repro/wfo_ds_r4_repro
# (c) stage bundle + upload + sim (Kaggle) — dung kaggle_sim.py, bundle_ds moi
# (d) doi chieu: md5 printDone vs 06fd6e9aa9c916945b2cf12310b337ff; n=2027; eq=104489
```

## 6. Tuân thủ

0 train/0 sim Java trên Oracle (chỉ predict + build map + doc). 0 chạm 242. 0 đọc key/secret.
Ghi ra `/home/ubuntu/f0_repro/` (thư mục mới), KHÔNG ghi đè bins/data đang dùng. Python `logging`.
