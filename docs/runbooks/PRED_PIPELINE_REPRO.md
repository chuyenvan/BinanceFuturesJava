# PRED_PIPELINE_REPRO — runbook tái lập pipeline dự báo selector (pred map)

Mục đích: lệnh 1-phát build lại **toàn bộ pred map** cho **một cấu hình features/label bất kỳ**
(tham số hoá), trên DEV (≤ 2025-12-31). Kế thừa `research/pipeline/README.md` (10 fold cũ) +
`research/pipeline/x1/` (16 fold 48 tháng) + `docs/experiment/G3_X26_RECOVERY.md` (net015).
Task F0 (2026-09-29) bổ sung generator `CLOSES_1H.bin`.

**Rủi ro trước (đọc kỹ):**
1. 🔴 `CLOSES_1H.bin` **KHÔNG tái lập byte** được — nguồn Binance Vision futures 1h **biến động**
   (delist-extension + xoá 2022-02 + chỉnh close + backfill). Xem `docs/result/RESULT_F0_CLOSES1H.md`.
   ⇒ generator `closes1h_build.py` chỉ dùng để **mở rộng sang 2026**; đoạn DEV dùng **file gốc đã ghim**.
2. 🔴 `predwf_G015x26` (net015) **tái lập tới 1 ULP** (predict từ 18 model gốc), **KHÔNG byte-identical**
   (pipeline gốc `sort_values("ts")` quicksort không ổn định). Trainer gốc 08-14 đã mất; retrain
   `g015_net_train.py` = họ net015 (đúng nhãn), nhưng **CPU không ra byte model GPU**.
3. `pred_s1a2x1` (S1) tái lập **deterministic** trên CPU (seed 42, `n_jobs=4`), G3 cong byte-identical PASS.

---

## 0. Kiểm kê artifact (provenance)

| artifact | đường dẫn | sinh bởi | sha256 (16 fold) | tái lập? |
|---|---|---|---|---|
| `CLOSES_1H.bin` | `/home/ubuntu/java/fsrun/` | **F0**: `research/pipeline/closes1h_build.py` (trước đó KHÔNG có generator) | `24fd3e93…4d94b5` | format ✅ / byte ❌ (Vision biến động) |
| `predwf_G015x26` | `/home/ubuntu/claudedata/predwf_G015x26/` (16 fold) | kernel Kaggle GPU `selector-15mtr-pred15-net015-gpu` 08-14 (trainer đã mất) | `BINS_MANIFEST.md` §G3 | ✅ tới 1 ULP (`g015x26_train.py`) |
| `pred_s1a2x1.parquet` | `/home/ubuntu/ledger/pred_s1a2x1.parquet` | `x1/x1_s1_rank.py 2x1` (16 cutoff) | `2618fe1a…` | ✅ byte (G3 PASS) |
| `predwf_map_s1a2_x1` | `/home/ubuntu/predwf_map_s1a2_x1/` (16 bin) | `x1/x1_build_map.py s1a2x1` | `BINS_MANIFEST.md` §X1 | ✅ nếu S1+G015x26 có |

Chi tiết sha256 từng file: `research/pipeline/BINS_MANIFEST.md` (mục 2, X1, G3).

## 1. Chuỗi build (16 fold, 48 tháng DEV 2022-01..2025-12)

```
CLOSES_1H.bin ─┐
OI percoin ────┼→ [1] x1_feat_v2_build.py → feat_v2_x1.parquet (45+ feat, hourly)
Aerospike funding
wfo_gate_pred.csv ─┐
label_15m/*.pb ────┼→ [2] x1_ledger.py build → cand_dev_x1.parquet (pool + g1lite)
predwf_G015x26 ────┘
feat_v2_x1 + cand_dev_x1 → [3] x1_s1_rank.py 2x1 → pred_s1a2x1.parquet (ts,sym,score)
predwf_G015x26 ─┐
pred_s1a2x1 ────┼→ [4] x1_build_map.py s1a2x1 → predwf_map_s1a2_x1/*.bin (26B/rec)
```

## 2. Lệnh 1-phát (Oracle, chạy tuần tự; mỗi bước có cổng byte-identical G1..G4)

```bash
R=/home/ubuntu/src/BinanceFuturesJava
CUTS16="20220101 20220401 20220701 20221001 20230101 20230401 20230701 20231001 \
        20240101 20240401 20240701 20241001 20250101 20250401 20250701 20251001"

# [1] feature hourly 48 thang (T_END=2026-01-01 UTC = 1767225600000)
cd /home/ubuntu/featv2
env X1_NAME=feat_v2_x1 X1_T_END=1767225600000 \
  python3 $R/research/pipeline/x1/x1_feat_v2_build.py > feat_v2_x1.out 2>&1   # ~4-6 phut, ~23G RAM
grep -q ALL_V3_PASS feat_v2_x1.out || { echo "ABORT feat"; exit 1; }

# [2] candidate ledger (X1_LBGLOB bat buoc 202[1-5] — bay glob nhan)
env X1_T1=2026-01-01 X1_CUTS="$CUTS16" X1_LNAME=cand_dev_x1 X1_LBGLOB='202[1-5]' \
  python3 $R/research/pipeline/x1/x1_ledger.py build > cand_dev_x1.out 2>&1   # ~20s

# [3] S1 ranker 16 fold (seed 42, CPU, n_jobs=4)
env X1_LNAME=cand_dev_x1 X1_FEAT=/home/ubuntu/featv2/feat_v2_x1.parquet X1_ICOUT=pool_rankic_x1 \
  X1_CUTS="$CUTS16" X1_SHUF=0,7,15 \
  python3 $R/research/pipeline/x1/x1_s1_rank.py 2x1 > s1_x1.out 2>&1        # ~6-10 phut

# [4] quantile-map ra bins
env X1_CUTS="$CUTS16" python3 $R/research/pipeline/x1/x1_build_map.py s1a2x1 \
  /home/ubuntu/predwf_map_s1a2_x1 > map_x1.out 2>&1                          # ~45s

# cong byte-identical (G1..G4) — FAIL => DUNG, khong chay sim
python3 $R/research/pipeline/x1/x1_gates.py g1 && \
python3 $R/research/pipeline/x1/x1_gates.py g2 && \
python3 $R/research/pipeline/x1/x1_gates.py g3 && \
python3 $R/research/pipeline/x1/x1_gates.py g4
```

**Tham số hoá (đổi features/label):**
- **features S1**: sửa `KEEP` trong `x1_s1_rank.py` (9 feature hiện tại) + thêm feature vào
  `x1_feat_v2_build.py` trước bước [1].
- **label value net015**: đổi `NET_THR`/`--label-mode` trong `g015_net_train.py` (train mới) rồi
  predict; hoặc `g015x26_train.py` (predict từ model gốc, không đổi nhãn).
- **cutoff/fold**: env `X1_CUTS` (quarter-aligned, train < cutoff − 72h purge).

## 3. Tái lập riêng `predwf_G015x26` (net015, 16 fold)

```bash
# predict tu 18 model goc (KHONG train) — tai lap toi 1 ULP, ~2 phut/fold, peak ~11 GB
R=/home/ubuntu/src/BinanceFuturesJava; OUT=/home/ubuntu/f0_repro/g015x26_regen; mkdir -p $OUT
i=0
for C in 20220101 20220401 20220701 20221001 20230101 20230401 20230701 20231001 \
         20240101 20240401 20240701 20241001 20250101 20250401 20250701 20251001; do
  CUTOFF=$C FOLD_IDX=$i OUT="$OUT/predict_wf_${C}.bin" \
    python3 $R/research/pipeline/g015x26_train.py || exit 1
  i=$((i+1))
done
python3 $R/research/analysis/g015x26_compare.py   # spearman 1.0, max|d| 1.19e-07 (16/16)
# train lai tu dau (doi features/label): python3 $R/research/pipeline/g015_net_train.py --fold all --device cpu --out-dir /duong/dan
```

## 4. Export dataset WFO + sim (Java, sau khi bins sẵn sàng)

```bash
# dataset (1 lan, dung chung N sim)
R=/home/ubuntu/src/BinanceFuturesJava; JAR=$R/target/binance-java-sdk-1.2.4.jar
cd /home/ubuntu/java/devrun && cp -f $R/configs/sim_dev.properties config.properties
env TRADING_PROFILE=$R/profiles/r4_kg0_k16_f015_g155.properties \
  WFO_SET_PRED=ai_pred_market_gate_wfo WFO_SEL_HORIZON_IDX=0 WFO_CODE_SHA=$(cd $R && git rev-parse --short HEAD) \
  java -Duser.timezone=Asia/Ho_Chi_Minh -Xmx14g -cp $JAR \
  com.binance.chuyennd.ai_ml.wfo.framework.ExportWfoDataset /home/ubuntu/wfo_ds_r4
# sim (Kaggle, TICKER_SOURCE=file) — xem docs/runbooks/KAGGLE_SIM.md; KHONG sim Java tren Oracle
```

## 5. Thời gian + tài nguyên (đo 2026-09-29)

| bước | thời gian | RAM peak | ghi chú |
|---|---|---|---|
| `closes1h_build.py` (627 sym, 60 tháng) | **~4 phút** | thấp (mạng) | 20 threads, giai nen trong bộ nhớ |
| `x1_feat_v2_build.py` (48 tháng) | ~4-6 phút | **~23 GB** | `hrs_since_high` O(n²) theo symbol |
| `x1_ledger.py build` | ~20 s | thấp | |
| `x1_s1_rank.py 2x1` (16 fold) | ~6-10 phút | ~6 GB | XGBRanker CPU |
| `g015x26_train.py` (1 fold) | ~2 phút | **~11 GB** | fold 2025 nặng nhất |
| `x1_build_map.py` | ~45 s | thấp | |
| Tổng toàn tuyến (S1 + net015 + map) | **~30-45 phút** | ≤ 23 GB | chạy tuần tự (1 job nặng/lúc, `nice -n 10`) |

## 6. Luật bắt buộc

- DEV ≤ 2025-12-31; **KHÔNG** dùng/kết quả 2026; KHÔNG chạm 242; KHÔNG đọc key/secret.
- KHÔNG ghi đè data dir đang dùng — ghi ra thư mục mới; `CLOSES_1H.bin` gốc là input chuẩn.
- Python `logging` (cấm `print`), Java SLF4J. Sim → Kaggle (KHÔNG Oracle). `nice -n 10`.
- Pre-reg trước khi tính số kết quả; parity G1..G4 PASS trước khi chạm sim.
