# RUNBOOK CHUẨN — CPCV AUTO-VALIDATION (Pha 2, chống-leak)

> **Trạng thái tài liệu:** CHUẨN THỰC HIỆN (SOP). Cập nhật 2026-08-26.
> **Luật gốc:** `docs/DATA_GOVERNANCE_PROTOCOL.md` · **Recipe:** `docs/PHASE1_RECIPE_FROZEN_v1.md` (sha256 738772ff…)
> **Bản đồ file chi tiết:** `docs/CPCV_PIPELINE_INVENTORY.md`
>
> **Hợp đồng một câu.** Máy chạy validate trên VALIDATION; người + LLM CHỈ nhận `verdict.json`
> (PASS/FAIL + DSR/PBO tổng), KHÔNG BAO GIỜ xem số per-config/per-fold. Nhìn số per-config = leak = tập cháy.

---

## 0. TRẠNG THÁI SẴN SÀNG (đọc trước mỗi lần chạy)

| Mắt xích | Trạng thái |
|---|---|
| Java engine `cpcv.jar` (CpcvBatchRunner) | ✅ built + deploy Oracle `/home/ubuntu/java/cpcv.jar` |
| Python core (`scripts/model_quality/cpcv/`) | ✅ committed, self-test PASS |
| Baseline Oracle K=8 | ✅ đã chạy (b00 SUCCESS 69 lệnh Calmar 1.74) |
| Dataset VALIDATION `/home/ubuntu/wfo_ds_VAL/` | ⚠️ verify tồn tại trước khi chạy (§2) |
| `parity_check.py` | ❌ **THIẾU** — blocker B1 (§7) |
| `run_cpcv_worker.py` (bản shard CpcvBatchRunner) | ❌ **SAI** (đang là WfoWorker/jobstore) — blocker B2 (§7) |
| Scheduled orchestrator | ❌ không còn — chạy tay theo §4 hoặc lập lại (§6) |
| Lớp 3 (`_wfotmp/`) trong git | ⚠️ chưa commit |

**Kết luận: pipeline chạy được BASELINE + verdict tay; nhưng FANOUT Kaggle tự động cần đóng B1+B2 trước.**

---

## 1. VAI TRÒ (bất biến — chống leak bằng tách vai)

- 👤 **Người (Uni):** chốt recipe/ngưỡng TRƯỚC khi chạy (pre-register), nhận verdict, quyết PASS→Pha 3 / FAIL→về DEV.
- 🤖 **Máy:** chạy toàn bộ search + backtest + CPCV + DSR/PBO. Không hỏi người giữa chừng.
- 🧭 **Claude:** viết/soi công cụ, KHÔNG chọn config, KHÔNG nhìn số per-config, KHÔNG tự đổi recipe/ngưỡng.
- **Một chủ thể điều phối tại một thời điểm.** Không để 2 orchestrator (session + scheduled) cùng chạm Oracle/Kaggle.

---

## 2. TIỀN ĐỀ — CHECKLIST TRƯỚC KHI CHẠY (dừng nếu thiếu bất kỳ)

```bash
ssh -i ~/.ssh/id_rsa_chuyennd_openssh ubuntu@161.118.212.3
# [ ] jar có class:   unzip -l /home/ubuntu/java/cpcv.jar | grep -c CpcvBatchRunner   (>0)
# [ ] dataset VAL:    ls /home/ubuntu/wfo_ds_VAL/manifest.txt /home/ubuntu/wfo_ds_VAL/*.bin
# [ ] config file-mode: grep TICKER_SOURCE /home/ubuntu/cpcv/run/config.properties   (=file)
# [ ] ticker daily:   ls /home/ubuntu/java/simulator/kaggle_data_hpo/daily | wc -l    (đủ 2024-07→2025-12)
# [ ] recipe hash khớp: sha256sum docs/PHASE1_RECIPE_FROZEN_v1.md == 738772ff…
```

**3 GUARD BẮT BUỘC mọi lệnh java (thiếu 1 = kết quả SAI recipe, âm thầm):**
1. `SELECTOR_RANK_TOPK=8`  (quên → về -1 rank OFF → 168 lệnh thay vì 69)
2. `-Duser.timezone=Asia/Ho_Chi_Minh`  (thiếu → lệch múi giờ → ZERO_TRADES)
3. `TICKER_SOURCE=file` trong config + CWD có `kaggle_data_hpo/`  (đọc ticker relative)

---

## 3. LỆNH CHẠY 1 BATCH (CpcvBatchRunner) — dạng chuẩn

```bash
cd /home/ubuntu/cpcv/run
env CPCV_CELLS=<shard.jsonl> CPCV_OUT=<out.jsonl> \
    WFO_DATA_DIR=/home/ubuntu/wfo_ds_VAL WFO_SMART_CACHE=1 SELECTOR_RANK_TOPK=8 \
    java -Duser.timezone=Asia/Ho_Chi_Minh -Xmx14g \
    -cp /home/ubuntu/java/cpcv.jar com.binance.chuyennd.ai_ml.wfo.CpcvBatchRunner
# Resume: chạy lại cùng lệnh — bỏ qua cell đã có trong CPCV_OUT (theo seq|block).
```

---

## 4. QUY TRÌNH CHẠY TỰ ĐỘNG ĐẦY ĐỦ (5 bước, không can thiệp giữa chừng)

Master: `_wfotmp/cpcv_fanout.sh STAGE` (STAGE = upload|kernels|parity|fanout|poll|verdict|all).

1. **Baseline** — `bash cpcv_baseline.sh` trên Oracle → `baseline_oracle.jsonl` (16 cell, K=8, tất định).
2. **Upload** — `cpcv_fanout.sh upload` → cpcv.jar + wfo-ds-val + shard cells lên Kaggle (ticker đã có sẵn).
3. **PARITY GATE (chốt chặn)** — `cpcv_fanout.sh kernels && cpcv_fanout.sh parity`:
   Kaggle chạy 16 cell → so với `baseline_oracle.jsonl`. **Tiêu chí: trades KHỚP CHÍNH XÁC, note khớp,
   calmar/pnl reltol ≤ 1e-3.** LỆCH → **DỪNG**, không fanout. (Sim tất định → môi trường lệch = bug hạ tầng.)
4. **Fanout** — parity MATCH → `cpcv_fanout.sh fanout && cpcv_fanout.sh poll` → 1600 cell (200 config × 8 block)
   trên 5 kernel → gộp `results.jsonl`.
5. **Verdict** — `cpcv_fanout.sh verdict` → `run_cpcv_validation.py data_tiers.json wf_full --n 200 --seed 42`
   → CPCV 28 path + DSR/PBO → `verdict.json`.

---

## 5. ĐỌC VERDICT (thứ duy nhất người được xem)

`verdict.json` = `{verdict, O_test_median, pos_path_ratio, pbo, dsr, n_trials}`.

- **PASS** ⇔ `PBO < 0.20` **VÀ** `DSR > 0.95` **VÀ** `pos_path_ratio ≥ 0.80` (objective O = median(Calmar_mtm) − 0.5·std).
- **Luôn ghi kèm:** "VALIDATION 2024-2025 đã bị nhìn quá khứ → DSR là CẬN TRÊN. 2026 mới là trọng tài."
- PASS → mở Pha 3 (HOLDOUT 2026, chạy 1 config thắng đúng 1 lần).
- FAIL → **KHÔNG vặn-rồi-chạy-lại trên VALIDATION.** Về DEV đẻ giả thuyết mới; `trial_ledger` cộng dồn n_trials
  vĩnh viễn → cửa DSR tự cao lên.
- CẤM: mở `results.jsonl`/số per-config để "xem thử vì sao FAIL". Đó là leak.

---

## 6. ĐIỀU KIỆN DỪNG (gặp là dừng, không tự chữa cháy)

- Parity MISMATCH → dừng, ghi log, điều tra hạ tầng (KHÔNG đổi recipe/config cho khớp).
- Thiếu tiền đề §2 → dừng.
- Cần làm gì ngoài scope `/home/ubuntu/cpcv/` + Kaggle của chuyendinh → dừng.
- Muốn sửa recipe đã hash → dừng, pre-register v2 (ngày + lý do), KHÔNG sửa lén.
- Phát hiện người đã lỡ nhìn số per-config → ghi nhận leak vào ledger, không giả vờ chưa thấy.

---

## 7. BLOCKER PHẢI ĐÓNG TRƯỚC LẦN FANOUT THẬT

- **B1 — viết `/home/ubuntu/cpcv/parity_check.py`.** `cpcv_fanout.sh` gọi nó nhưng file chưa có; chỉ có
  `compare_parity.py` (khác tên + **đảo thứ tự tham số**). Cần: `parity_check.py <candidate> <baseline>` in
  MATCH/MISMATCH theo tiêu chí §4.3.
- **B2 — rewrite `run_cpcv_worker.py` sang CpcvBatchRunner + shard file.** Bản hiện tại chạy `WfoWorker` qua
  jobstore Aerospike (`WFO_STATE_HOST`) — SAI theo `ORCH_PARITY.md`; phải chạy CpcvBatchRunner đọc shard,
  KHÔNG jobstore, có đủ 3 guard §2.
- **B3 — commit lớp 3** (`_wfotmp/` → repo) để không mất.

---

## 8. NÂNG CẤP v2 (nếu chuyển objective/label mới)

Pipeline hiện validate **recipe v1**. Quyết định 2026-08-26 (fitness = PnL, maxDD gate 40%; label net_4h ≥ 1.5%)
CHƯA vào pipeline. Muốn chạy v2, làm THEO THỨ TỰ:
1. Pre-register `PHASE1_RECIPE_FROZEN_v2.md` (ngày + lý do) → sha256 mới → reset ledger n_trials.
2. Sửa `run_cpcv_validation.py`: `PASS` dict + `objective_O` theo v2.
3. Sửa fitness Java (`HPOFitnessCalculatorV4`) + label selector (`SEL_LABEL_MODE=net` đã có sẵn).
4. Rebuild jar → deploy → chạy lại từ §2.

---

## 9. HẠ TẦNG (facts + bẫy)

- Oracle 161.118.212.3, ubuntu, key `~/.ssh/id_rsa_chuyennd_openssh` (qua desktop-commander/Git ssh;
  **device_bash Linux VM KHÔNG có egress/key** → không chạm Oracle được).
- Oracle chỉ có java 11, KHÔNG maven → build trên Windows (`mvn.cmd`, JDK 11) rồi scp.
- Kaggle user chuyendinh, ticker sẵn: wfo-ticker-2024h1/h2/2025h1/h2.
- Bẫy PowerShell→ssh: KHÔNG `&&`/`|` (cắt/nuốt lệnh) → dùng `;` + redirect file.
- Bẫy `pkill -f CpcvBatchRunner` tự giết shell → dùng regex bracket `pkill -9 -f 'CpcvBatchRunne[r]'`, launch lệnh khác.


---

## 10. KAGGLE 5-NODE FIXED-SHARD FANOUT (đóng B2 — chạy thật cho v3, 2026-08-28)

**Mục tiêu:** chạy 3200 cell NHANH + DETERMINISTIC. Mỗi kernel Kaggle nhận 1 shard CỐ ĐỊNH và chạy
`CpcvBatchRunner` (KHÔNG jobstore/WfoWorker — cái đó non-deterministic). Kaggle mỗi node ~31GB RAM →
hết OOM (v3 `funding.bin`=2.2GB, cần >6g heap; Oracle 24g chỉ chạy nổi 1 JVM `-Xmx16g`).

**Vì sao Oracle-only không đủ:** 1 JVM serial ~36h; 2 JVM song song = RAM thrash (mất sshd, phải reboot).
Song song thật chỉ có trên Kaggle. Đây là lý do B2.

### 10.1 Tiền đề (bắt buộc)
- `cpcv.jar` PHẢI có `CpcvBatchRunner` → upload thành dataset `chuyendinh/cpcv-jar` (jar Kaggle cũ
  `binance-java-sdk-*-shaded.jar` chỉ có WfoWorker, KHÔNG có CpcvBatchRunner).
- dataset VAL: market.bin/pred.bin/funding.bin/manifest.txt + `config.properties` đã SỬA
  `AEROSPIKE_HOST_226=161.118.212.3` (để kernel Kaggle reach Aerospike Oracle lấy symbol-map qua internet)
  + 5 shard cố định + 1 shard_smoke → dataset `chuyendinh/wfo-ds-val-vX`.
- ticker có sẵn: `chuyendinh/wfo-ticker-2024h1|2024h2|2025h1|2025h2|2026pf`.
- kaggle CLI trên Oracle: `/home/ubuntu/kaggle_latest_venv/bin/kaggle`.

### 10.2 Các bước (script mẫu: build_kag_v3.sh / mk_smoke.sh / mk_fanout.sh / collect_v3.sh)
1. **Split shard:** `split -n l/5 -d --additional-suffix=.shard shard_all shard_vX_` ;
   `head -8 shard_all > shard_smoke.shard`.
2. **Upload** 2 dataset (jar + ds): `kaggle datasets create -p . -r skip` (hoặc `version -m .. -r skip`).
3. **SMOKE 1 kernel** (shard_smoke, 8 cell). run.py: glob jar/ds/config/shard + ticker→symlink vào
   `/kaggle/working/kaggle_data_hpo`; `chdir /kaggle/working`; env `WFO_DATA_DIR=<ds> WFO_SMART_CACHE=1
   SELECTOR_RANK_TOPK=8 CPCV_CELLS=<shard> CPCV_OUT=/kaggle/working/out.jsonl`; chạy
   `java -Duser.timezone=Asia/Ho_Chi_Minh -Xmx20g -cp <jar> ...CpcvBatchRunner`. metadata:
   `enable_internet=true` (BẮT BUỘC — cần Aerospike symbol-map), `dataset_sources=[cpcv-jar, ds, 5 ticker]`.
   → **PARITY GATE:** 8 cell smoke PHẢI khớp Oracle cùng (seq,block). v3 đạt 8/8. Không khớp = DỪNG.
4. **FANOUT 5 kernel** `chuyendinh/cpcv-vX-{0..4}`: copy smoke run.py, đổi `CPCV_CELLS=shard_vX_0i.shard`
   + `CPCV_OUT=out_vX_0i.jsonl`. push cả 5. Thực tế ~40–60 phút/kernel (cell nặng dồn ở đầu shard nên
   smoke ~53s/cell ước SAI thành 9h — đừng tin ước từ smoke).
5. **COLLECT:** `kaggle kernels output` từng kernel → gộp `out_vX_0*.jsonl` → kiểm `uniq(seq,block)=3200`,
   8 block b00..b07, seq 0..399. Thiếu (kernel timeout 12h) → bù từ bản Oracle serial.
6. **VERDICT:** như Mục 5.

### 10.3 Bẫy + luật (đã trả giá)
- **Cross-machine FP:** Kaggle vs Oracle lệch ~0.2–0.7% ở ~40% cell (KHÁC bug jobstore lệch ~50% cả dấu).
  Không đổi kết luận định tính. Cần khớp-byte với baseline (chạy Oracle) → chạy thêm 1 JVM Oracle
  `-Xmx16g` serial làm confirm.
- **RAM Oracle 24g/4cpu:** CHỈ 1 JVM `-Xmx16g`. KHÔNG 2 JVM heap-lớn song song → thrash → reboot.
- **Bridge PowerShell→ssh:** hay rớt DÒNG ĐẦU output → thêm `echo S;` mồi trước lệnh.
- **ĐỪNG `cat`/`tail` log Kaggle thô** (progress bar `%|` ngốn hàng chục nghìn token) → `grep -avE '%\|'`.
- B2 ĐÃ ĐÓNG. B1 (parity_check.py) thay bằng smoke-parity 8 cell ở bước 3. B3: commit `_wfotmp/` vẫn treo.
