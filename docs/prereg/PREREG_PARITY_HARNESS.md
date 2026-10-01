# PREREG — PARITY HARNESS shadow/242 ↔ BACKTEST (`research/parity/parity_check.py`)

> **Chốt TRƯỚC khi chạy.** Ngày chốt: **2026-10-01** (GMT+7). Sau khi đã thấy số ⇒ **KHÔNG đổi** nguồn dữ liệu,
> cửa sổ, symbol, ngưỡng PASS, hay cách xử lý thiếu dữ liệu. Mọi thay đổi sau đó phải là **amend riêng**, ghi rõ.

- **Bối cảnh:** owner yêu cầu 1 harness parity để so **shadow (242, PAPER)** với **backtest**, **validate INPUT/OUTPUT
  chặt chẽ**, **deterministic**, và **LUÔN in ra PASS/FAIL/MISSING + exit code** — tuyệt đối không "chạy test fail rồi
  không có kết quả". Tiêu chí đích: **khớp 100 %**.
- **Ràng buộc giữ nguyên:** Python là chính (không Java trên Oracle); **KHÔNG** sửa/ghi trên 242 (READ-ONLY);
  **KHÔNG** chạm ONNX/LIVE secret; **KHÔNG** in secret; **KHÔNG** push file dữ liệu (`*.csv`,`*.gz`,`*.log` bị `.gitignore`);
  `df -h` nhẹ; output tool nhỏ.
- **Holdout:** 2026 là HOLDOUT — cửa sổ parity dưới đây **chỉ dùng để ĐO/ĐỐI CHIẾU (audit-only)**, **KHÔNG** dùng để
  chọn/hiệu chuẩn tham số. Harness là **đo lường thuần**, không bao giờ chọn tham số.

---

## 0. MỘT ENTRY POINT, 7 SUBCOMMAND

`python3 research/parity/parity_check.py {config|features|gate|marketparams|selector|entry|exit|all|selftest|fetch}`

Mỗi subcommand in 1 bảng (tầng · LIVE · BACKTEST · lệch · ngưỡng · PASS/FAIL) và trả **exit code**:
`0` = mọi tầng PASS · `2` = có ≥1 FAIL · `3` = không FAIL nhưng có ≥1 MISSING.

Quy tắc trạng thái 1 tầng: **FAIL > MISSING > PASS** (nếu 1 tầng có cả FAIL và MISSING ⇒ tầng = FAIL).

---

## 1. NGUỒN DỮ LIỆU (chốt cứng)

| ký hiệu | nguồn | đường dẫn mặc định | ghi chú |
|---|---|---|---|
| BASELINE | profile mốc | `profiles/g2_flat3.properties` | = G2 gate rolling + FLAT3 exit + R4 sizing |
| LIVE-CFG | config 242 (non-secret) | `research/parity/data/live_242_config.snapshot` | lấy READ-ONLY từ 242 bằng `fetch`; **chỉ key non-secret** |
| LIVE-LOG | tóm tắt log 242 (non-secret) | `research/parity/data/live_242_log_summary.json` | đếm `[GATE]`, `n_pass`, `AI PASS`, ledger |
| LIVE-FEAT | feat_dump 242 (BTCUSDT) | `~/claudedata/devexport_202609/live_242/*.csv.gz` + `~/shadow_c3/app/feat_dump/feat_dump_20260928_*.csv.gz` | 33 feature + `p15_out` |
| BACKTEST | export DEV | `~/claudedata/devexport_202609/devexport_20260701_20260928_FULL.csv.gz` | 1 dòng/phút, market-level 33 feature |

**Cửa sổ parity:** các phút cùng tồn tại ở LIVE-FEAT và BACKTEST (**ghép cặp CHÍNH XÁC theo `ts`**, như
`RESULT_FEATDIFF_PASS2`). Không nội suy, không ghép gần.

**Symbol:** LIVE-FEAT chỉ có `BTCUSDT`; BACKTEST là market-level (1 dòng/phút) ⇒ khoá ghép = `ts` (BTCUSDT ≡ dòng market).

---

## 2. NGƯỠNG PASS TỪNG TẦNG (chốt cứng)

| tầng | chỉ số | ngưỡng PASS | nguồn LIVE | nguồn BACKTEST |
|---|---|---|---|---|
| **config** | từng key | giá trị LIVE khai báo == profile (hoặc unset nhưng default Java == profile) | LIVE-CFG | BASELINE |
| **features** | `max|Δ|` từng feature trên cùng `ts` | `≤ 1e-8` **và** 0 NaN bất thường | LIVE-FEAT | BACKTEST |
| **gate** | (a) tái lập quyết định cổng; (b) chế độ cổng | (a) `n_pass` tái lập == `n_pass` log; (b) LIVE mode == BASELINE mode | LIVE-FEAT + LIVE-LOG | BASELINE |
| **selector** | score/rank cùng tick | khớp (==) | LIVE (serialized) | BACKTEST selector |
| **entry** | số quyết định vào lệnh trong cửa sổ | LIVE == BACKTEST | LIVE-LOG | BASELINE (G2 tự hiệu chuẩn) |
| **exit** | lệnh đóng đối chiếu | khớp == | LIVE ledger | BACKTEST printDone |

`max|Δ| ≤ 1e-8` = mức "khớp máy" (byte/float parity). Bất kỳ feature nào vượt ⇒ feature đó **FAIL** (kể cả khi tương
quan cao) — vì tiêu chí owner là **khớp 100 %**, không phải "tương quan tốt".

---

## 3. CÁCH XỬ LÝ THIẾU DỮ LIỆU (chốt cứng — KHÔNG im lặng)

1. File thiếu / không đọc được / thiếu cột / sai dtype / sai symbol / rỗng ⇒ tầng đó = **FAIL** kèm **lý do cụ thể**
   (tên file, cột thiếu, số dòng). **Không** crash, **không** "0 kết quả".
2. Artifact bị **cắt cụt** (gz thiếu end-of-stream) ⇒ đọc **các dòng hoàn chỉnh** (zlib partial), ghi cảnh báo
   `truncated=true`; nếu 0 dòng hoàn chỉnh ⇒ FAIL.
3. Không đo được 1 tầng vì **thiếu nguồn đối ứng** (vd selector live là Java-serialized, không có artifact score
   cùng tick phía backtest) ⇒ ghi **MISSING + lý do + đề xuất cách đo**. **KHÔNG** tính là PASS.
4. **Exit** khi gate đóng ⇒ không có lệnh ⇒ **MISSING + lý do**, KHÔNG tính PASS.
5. **Luôn** ghi `docs/result/parity_report.json` + `.md` dù bất kỳ tầng nào FAIL/MISSING.

---

## 4. TỰ KIỂM HARNESS (bắt buộc, chốt trước)

| # | phép thử | kỳ vọng |
|---|---|---|
| (a) | cố ý **tiêm lệch** vào 1 feature (BACKTEST += 1.0) | tầng features **FAIL đúng chỗ** (feature đó) |
| (b) | chạy so sánh **2 lần** | output **byte-identical** (deterministic) |
| (c) | **xoá 1 cột** input bắt buộc | **FAIL kèm lý do** (không crash, không exception) |

Ba kết quả này ghi vào `parity_report.json` mục `selftests` (mỗi phép PASS/FAIL riêng).

**Deterministic:** báo cáo **không** chứa đồng hồ thời gian / thứ tự ngẫu nhiên; JSON `sort_keys=True`; mọi tập hợp
được sort trước khi ghi.

---

## 5. MỤC BỎ / KHÔNG LÀM (khai rõ)

- **KHÔNG** chạy Java/sim/WFO trên Oracle (ràng buộc cứng). Nếu buộc phải chạy sim ⇒ **chỉ Kaggle**; Kaggle không
  chạy được ⇒ **DỪNG + báo rõ**.
- **KHÔNG** gọi ONNX inference (tránh chạm ONNX); nếu cần p15 phía DEV ⇒ ghi **MISSING + đề xuất**.
- **KHÔNG** ghi/sửa/restart/kill trên 242.
- **KHÔNG** push file dữ liệu; chỉ commit code + doc + JSON nhỏ + snapshot config non-secret.
- **KHÔNG** dùng 2026 để chọn tham số; chỉ audit/đối chiếu.

---

## 6. AMEND — STEER owner 2026-10-01 10:45: audit tham số MARKET `rateDown15MAvg`

> **Steer owner:** *"dau vao cua features co DownAvg15M no la tham so market gi do can audit ca cai nay. no lech la rat nhieu noi lech"*.
> Amend này **chốt TRƯỚC khi chạy tầng `marketparams`** (chưa xem số).

**Vì sao:** `rateDown15MAvg` chạy vào **4 nơi** (file:line): `MarketBigChangeDetector.java:174-186` `getMarketStatus1M`
→ **BIG_DOWN** (`MS_DOWN_BIG_AVG=-0.03157`) · `:188-191` `isDcaAlt` → **DCA** (`MS_DOWN_BIG_AVG_DCA=-0.03157`) ·
`TickWeakBlock.java:135` (`MODE=DROP15M`) · `BdSizeAdapt.java:90` (`thr=MS_DOWN_BIG_AVG`). Lệch field ⇒ lệch 4 nơi.

**Ánh xạ (đã xác minh, `ComprehensiveMarketFeatureExtractor.java:93-94`):** `momentum1M = rateDownAvg`,
`momentum15M = rateDown15MAvg` ⇒ 2 field đọc được từ feat_dump/export; **`rateUpAvg`/`rateUp15MAvg`**
không có trong CSV ⇒ **MISSING + lý do**.

**Ngưỡng (chốt):** so `MS_DOWN_BIG_AVG`, `MS_DOWN_BIG_AVG_DCA`, `MS_UP_BIG_THRES` (alias `SIM_MS_DOWN_BIG_AVG*`)
giữa **242 snapshot** vs `g2_flat3.properties`; **unset cả 2 bên ⇒ MATCH-DEFAULT** (default Java
`-0.03157 / -0.03157 / 0.02046`, `Configs.java:465-470`).

**Đo tác động (chốt):** trên cùng cửa sổ ghép, đếm **số phút quyết định BIG_DOWN / DCA ĐỔI TRẠNG THÁI**
giữa LIVE và BACKTEST (không chỉ `max|Δ|`), **+** số phút mà field BACKTEST = 0 (chết) khiến BIG_DOWN/DCA
**không thể kích hoạt**.

**Ngưỡng PASS tầng `marketparams`:** field `max|Δ| ≤ 1e-8` · ngưỡng khớp (==, hoặc cùng default) ·
impact flip = 0 **và** dead-minutes = 0. Bất kỳ feature/field nào thiếu ⇒ **MISSING + lý do + đề xuất**, không tính PASS.
