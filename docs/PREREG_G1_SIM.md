# PREREG_G1_SIM — giai đoạn 2 của G1: thay thang giá trị gate bằng `G72`

**Chốt trước khi chạy sim. Viết TRƯỚC khi thấy bất kỳ số nào của giai đoạn 1.**
Chỉ chạy nếu **cổng GO/NO-GO của `docs/PREREG_G1.md` §6 PASS**. Cổng FAIL ⇒ file này không
được thực thi và `docs/G1_HORIZON.md` phải ghi rõ là đã không chạy.

Ngày: 2026-09-05 (Oracle). Phạm vi **DEV** `2022-01-01 → 2024-06-30`. Không VAL. Không push.

## 1. Đổi đúng một thứ

- Bins gate: `predwf_G015x26` → **`G72`** (bins mới, 10 fold DEV).
- `build_map.py` chạy với **đúng thứ tự S1 của C2b** — `pred_s1a2.parquet`, **S1 KHÔNG ĐỔI**.
  Chỉ tham số hoá thư mục bins nguồn qua env `G015_BINS_DIR` (mặc định = đường dẫn cũ ⇒
  hành vi cũ không đổi).
- Profile: copy `profiles/c2b_min.properties` → `profiles/c2b_g72.properties`, sửa **đúng 1 dòng**
  `WFO_FUNDING_PRED_DIR`. Không đổi bất kỳ param exit/gate/sizing nào
  (`AGENT_RUNBOOK` bẫy 2: đã có `TRADING_PROFILE` thì không được đặt env tiền tố `SIM_`).

## 2. ĐÚNG 2 sim run — không hơn

| tag | profile | bins | vai trò |
|---|---|---|---|
| `G1_parity` | `c2b_min.properties` | `predwf_map_s1a2` (cũ) | **cổng**: phải byte-identical C2b |
| `G1_g72` | `c2b_g72.properties` | `predwf_map_g72` (mới) | run đo |

**Cổng parity:** `printDone.csv` (bỏ header) byte-identical với `devrun/C2b`;
md5 `8f7afdfb27b15f5b6d4c886700def93c`, `b:60390`, **970 lệnh**.
**Parity FAIL ⇒ DỪNG**, không đọc kết quả `G1_g72`.

Chạy bằng `tools/run_c2b_dev.sh <profile> <tag> <ds_dir>`; 1 slot JVM, `pgrep java` rỗng,
`df -h /` ≥ 5G trước mỗi build, `rm -rf $DS` sau mỗi run.

## 3. PRIMARY — rate, không phải equity

Chấm bằng `research/analysis/qret_ladder.py` + `/home/ubuntu/java/fsrun/qret.py`
+ `/home/ubuntu/java/fsrun/ev.sh`, so `G1_g72` với `C2b`:

| # | chỉ tiêu | yêu cầu |
|---|---|---|
| P1 | `TSloss%` | **GIẢM** |
| P2 | `win%` | **TĂNG** |
| P3 | `mean(profit \| STOP_MARKET_DONE)` | **không giảm quá 0.3pp** |

## 4. Ràng buộc CỨNG — vi phạm bất kỳ cái nào ⇒ loại

| # | ràng buộc |
|---|---|
| H1 | `maxDD` ≤ **15%** |
| H2 | underwater ≤ **120 ngày** |
| H3 | **không năm âm** |
| H4 | **không quý < −5%** |
| H5 | số lệnh ≥ **600** |

## 5. Quy tắc quyết định

`G72` **được chấp nhận** ⟺ P1 ∧ P2 ∧ P3 ∧ H1..H5. Thiếu một điều kiện ⇒ **null**.

**Equity báo cáo riêng, dán nhãn "KHÔNG PHẢI TIÊU CHÍ"**: `sd(ΔCAGR)` = 2.57pp,
`E[max nhiễu]` N=50 = +7.2pp, DEV đã ~125 run (`AGENT_RUNBOOK §0.3`, `docs/NBETS_RESULT.md`).
Equity cao hơn **không** được dùng để cứu một run trượt PRIMARY, và equity thấp hơn **không**
được dùng để loại một run đạt PRIMARY.

## 6. Giá trị hạ tầng — kết luận RIÊNG

Ghi trước: kể cả null ở rate lẫn equity, `G72` vẫn reproduce được và train được trên 2021,
trong khi `predwf_G015x26` thì không (`docs/G015X26_PROVENANCE.md §1`). Đây là **kết luận
riêng**, viết ở mục riêng của `docs/G1_HORIZON.md`, **không được trộn** với phán quyết PRIMARY
và không được dùng để biện minh cho việc nhận `G72` vào baseline.
