# RESULT_BD_CHAIN — đổi `rateDown15MAvg` theo tỷ lệ universe `f` (G2 + FLAT3)

Chạy 2026-10-01 (vòng 2 · subagent "CHO SLOT"), nhánh `module`. Pre-reg: `docs/prereg/PREREG_BD_CHAIN.md`
(chốt **TRƯỚC** khi đo). Nền: `profiles/g2_flat3.properties` (md5 FILE `c6d4ef57…`; parity `printDone.csv`
md5 `650c386f0d0dfea334af9d55ca2f21d4`, equity 131908, n 2517).

---

## 0. KẾT QUẢ CHỐT (đọc trước)

> ### ⛔ VIỆC 2/3 VẪN **KHÔNG CHẠY ĐƯỢC**. Có **2 blocker ĐỘC LẬP** — cái thứ hai là cái thật sự chặn:
>
> **(A) Slot Kaggle bận.** `chuyendinh/sm-pathexit` = `running` suốt cửa sổ theo dõi (poll §1).
> Theo ràng buộc CỨNG #1/#6 ⇒ không giành slot.
>
> **(B) KHÔNG có harness Kaggle cho các bước upstream của dây chuyền** (quan trọng hơn):
> đổi `f` phải **sinh lại `market.bin`** + **sinh lại gate store rồi retrain/pred** + **S1/bins**.
> Cả 3 khối upstream này hiện **không có đường chạy trên Kaggle**: chúng đều là job Java đọc
> **Aerospike 226** (replay nhiều giờ → nhiều ngày), còn `market.bin`/`pred.bin`/`predict_wf_*.bin`
> trong bundle là **snapshot tĩnh** (xem §3). Vì vậy **dù slot có rảnh, VIỆC 2/3 vẫn không tự chạy được** —
> phải **xây kernel/harness mới** (không phải "chạy lại lệnh cũ").

**VIỆC 0 + VIỆC 1 (code) đã xong ở vòng trước** ⇒ xem §1 vòng trước (`commit 08beda05`); vòng này chỉ
cập nhật trạng thái slot + chẩn đoán blocker hạ tầng.

---

## 1. VIỆC 1 — CHỜ SLOT (bắt buộc, không tranh)

Poll `kaggle kernels status chuyendinh/sm-pathexit` định kỳ (~5 phút/lần), log thô: `/home/ubuntu/bd_chain_poll.log`.

| mốc | trạng thái `sm-pathexit` | ghi chú |
|---|---|---|
| 2026-10-01 05:48 (lastRunTime) | running | vòng trước đã thấy |
| 2026-10-01 13:05:39 | **running** | [1] |
| 2026-10-01 13:10:39 | **running** | [2] |
| 2026-10-01 13:10:47 | **running** | kiểm lại trước khi kết thúc vòng |

- **DỪNG vòng này** không phải vì hết hạn chờ, mà vì **blocker (B)** (§3): dây chuyền upstream không có harness
  Kaggle ⇒ **dù slot rảnh, VIỆC 2/3 vẫn không chạy được**. Poll (`/home/ubuntu/bd_chain_poll.sh`) đã ghi log;
  vòng sau chỉ cần đọc lại.

- **Slot theo API list = 0 running / 5** (⚠️ KHÔNG tin được: CLI 1.6.17 `kernels_list` **không** trả
  trường `status` ⇒ lọc `status in (running,queued)` ra 0 một cách SAI). Nguồn sự thật là
  `kaggle kernels status <ref>` (endpoint riêng) ⇒ **`sm-pathexit` = running thật**.
- ⇒ Theo luật §6 pre-reg ("Kaggle bận ⇒ DỪNG + báo RÕ"): **DỪNG**, không push kernel nào.

---

## 2. VIỆC 2 — PARITY `f=0` (xác nhận) + 4 ARM (KHÔNG chạy được)

### 2.1 Parity `f=0` — md5 MỤC TIÊU ĐÃ CÓ BẰNG CHỨNG (từ run nền)

Run nền `chuyendinh/sim-g2flat3-val` (Kaggle, 2026-09-29, `TICKER_SOURCE=file`, profile `g2_flat3`,
bundle `sim-x1-2021-bundle`, jar `sim-jar-gdv2`) **đã** cho:

| chỉ số | giá trị |
|---|---|
| md5 `printDone.csv` | **`650c386f0d0dfea334af9d55ca2f21d4`** = ĐÚNG mục tiêu pre-reg ✅ |
| equity cuối | 131908 · `n_trades` 2517 · cửa sổ 20210701→20251230 |
| `PROFILE_HASH` | c47b73f3133521a1 · `symbol_mapper` 863 · jar_sha256 `7368be46…` |

- **CHƯA re-run trong vòng này**: luật §6 (còn job `running`) ⇒ không push. Do đó chưa xác nhận
  byte-identity của **JAR HEAD** (có key `SIM_BD_FRACTION`, default 0) — đây là việc **còn nợ** (§4).
- Về lý thuyết `f=0` ⇒ `BD_FRACTION=0` ⇒ không chạm `period` ⇒ kỳ vọng **byte-identical**; nhưng
  pre-reg đòi **tái lập bằng số**, nên vẫn phải chạy lại trên Kaggle khi có slot.

### 2.2 Bốn arm `f ∈ {0.10, 0.30, 0.50, 1.00}` — **NOT-RUN** (blocker hạ tầng, KHÔNG phải "kém")

Không có arm nào chạy ⇒ theo luật "arm không ra lệnh ⇒ ghi **NO-CALL**", ở đây mạnh hơn: **NOT-RUN**.
Không có số ⇒ **không bịa**.

---

## 3. BLOCKER HẠ TẦNG — vì sao dây chuyền KHÔNG tự chạy được (bằng chứng file:line)

Pre-reg §2 định nghĩa 6 bước. Trạng thái **đường chạy trên Kaggle** của từng bước:

| bước | cần gì | hiện trạng | file:line |
|---|---|---|---|
| 1. market.bin (rule path) | sinh lại market-rate từ ticker 1m với `N_f`, rồi export | **THIẾU**. `market.bin` = snapshot đọc từ Aerospike set `market_data`; sim **đọc tĩnh** | `WfoDataset.java:45,66` · `SimulatorMarketLevelTicker1MStopLoss.java:921` |
| 2. gate store (33 feat) | replay Aerospike toàn dải rồi ghi CSV | **THIẾU**. Là job Java replay Aerospike **~30–45 s/ngày** (cả dải 2021→2026 = **nhiều giờ**); gate store cũng **không có** dataset trên Kaggle | `ExportGateDataset.java:36,78` |
| 3. gate retrain + pred → `pred.bin` | `WFOGateRunner` (Java gọi Python train/fold) → set `ai_pred_market_gate_wfo` → `LoadWfoGatePredTool` | **THIẾU** trên Kaggle | `WFOGateRunner.java:60-70` · `LoadWfoGatePredTool.java:15,44` |
| 4. ledger/pool | `research/pipeline/ledger.py` | cần feature store mới (từ bước 2) | — |
| 5. S1 retrain + bins | `research/pipeline/s1_rank.py` + `build_map.py` | cần gate p15 mới (bước 3) | — |
| 6. sim | kernel `tools/kaggle_sim.py` | **CÓ** ✅ | `tools/kaggle_sim.py` |

⇒ **Bước 1–3 đều phụ thuộc Aerospike 226 + Java, không có kernel Kaggle nào làm**; bundle sim chỉ là
**snapshot tĩnh** (`market.bin` 49MB · `pred.bin` 38MB · `predict_wf_*.bin` ×19). Đổi `f` ⇒ **phải xây mới**
các kernel upstream này trước; đây là công trình **giờ→ngày**, không phải một lệnh "chạy lại".

**Hệ quả:** kết luận ở §5 là **BLOCKED**, KHÔNG phải kết luận khoa học. `f` đang giữ = **0** (N=100).

---

## 4. BẢNG `f` × chỉ số — **KHÔNG CÓ SỐ (BLOCKED)**

| `f` | parity md5 | ON-rate BD/DCA | n | T3 (win%/TSloss%) | UW | maxDD | q* | conc | Calmar | 4 tầng |
|---|---|---|---|---|---|---|---|---|---|---|
| 0.00 (parity) | `650c386f…` ✅ (run nền; **chưa** re-run JAR HEAD) | — | — | — | — | — | — | — | — | — |
| 0.10 | NOT-RUN | — | — | — | — | — | — | — | — | — |
| 0.30 | NOT-RUN | — | — | — | — | — | — | — | — | — |
| 0.50 | NOT-RUN | — | — | — | — | — | — | — | — | — |
| 1.00 | NOT-RUN | — | — | — | — | — | — | — | — | — |

- **`f` nào qua 4 tầng:** chưa đo (không arm nào chạy).
- **Trôi theo năm (ON-rate 2023 vs 2025):** chưa đo trong bài này; bằng chứng cũ (0-sim) ở
  `RESULT_BD_DEEP §3.4` (non-stationarity 3× theo năm).

---

## 5. TRẢ LỜI (theo thực tế đã làm)

1. **`rateDown15MAvg` là input model hay rule?** → **INPUT MODEL + rule** (đã chốt vòng trước, `08beda05`).
2. **Mỗi `f` (ON-rate/n/T3/UW/maxDD/q*/conc/Calmar) so G2?** → **KHÔNG CÓ SỐ** — blocker §3.
3. **Có `f` nào qua 4 tầng?** → **Chưa đo.**
4. **Trôi theo năm hết chưa?** → **Chưa đo trong bài này.**
5. **Kết luận dứt khoát:** → **NO-GO (tạm thời, do BLOCKED) — giữ `f=0` (N=100).** Đây **không** phải
   kết luận khoa học "biến thể kém"; là **chưa đo được** vì (A) slot bận **và** (B) thiếu harness upstream.

---

## 6. MỤC BỎ + LÝ DO

- **Bỏ:** VIỆC 2 (4 arm Kaggle) + VIỆC 3 (chấm 4 tầng + theo năm + CI).
- **Lý do:** (A) `chuyendinh/sm-pathexit` **`running`** (ràng buộc #1/#6); (B) bước 1–3 của dây chuyền
  **không có harness Kaggle** (§3) ⇒ không thể "chạy nhanh, gọn" kể cả khi slot rảnh.
- **KHÔNG bỏ:** VIỆC 0 (input-vs-rule), VIỆC 1 (pre-reg + code gated default byte-identical), commit+push.

---

## 7. VIỆC CẦN LÀM ĐỂ MỞ KHOÁ (kế hoạch cụ thể, cho vòng sau)

1. **Kernel A — sinh `market.bin` mới**: stream ticker 1m (dataset `wfo-ticker-*`) → `MarketDataInlineGenerator.update()`
   (đã ăn `BD_FRACTION`) → ghi `market.bin` format `[count][ts][down,up,down15m]`. Chạy 1 lần/`f`. Kiểm cổng:
   `f=0` phải **byte-identical** `market.bin` gốc.
2. **Kernel B — gate store**: replay Aerospike 226→CSV (job dài), hoặc chấp nhận **chỉ đổi cột rate-derived**
   (`momentum1M/5M/15M`, `momentumAcceleration`, `basketMomentum15M`) từ Kernel A rồi ghép vào store tĩnh.
3. **Kernel C — gate retrain + pred** → `pred.bin` mới (build lại set). **Kernel D — S1 + bins** → `predict_wf_*.bin` mới.
4. **Kernel E — sim** (`tools/kaggle_sim.py`) với bundle mới (`market.bin`+`pred.bin`+bins của `f`).
5. Chấm `research/analysis/reset_rule_score.py` theo §9 + theo năm; CI block-72h ×1,21.
