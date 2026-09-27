# PREREG_GROSS_ASYMMAP — Đối chiếu định nghĩa `gross` + re-score artifact theo bộ thước mới (0 sim)

**Ngày chốt:** 2026-09-27 (trước khi đọc số mới) · **Nhánh:** `module` · **KHÔNG push**
**Loại việc:** chỉ ĐỌC artifact (`printDone.csv` + `sim.out`). **KHÔNG** train, **KHÔNG** chạy Java/sim, **KHÔNG** chạy sim mới, **KHÔNG** chạm production/242/ONNX/LIVE. DEV only ≤ 2025-12-31.

---

## 0. BỐI CẢNH — vì sao phải chốt trước

Hai lần đo `gross` gần đây cho ra số **lệch nhau ~25–50×**:

| vòng | artifact | `gross` TB | `gross` MAX | nguồn |
|---|---|---|---|---|
| MỚI (`87a9f5c`, `RESULT_SIZE_COUNT`) | ledger `cd-sel15`/`sc-b*` | **1,0–2,0 %** | **34,4–53,5 %** | hậu kiểm từ ledger + equity ngày |
| CŨ (`844ca68`, `RESULT_CAP70_FEE06`) | pool `label_b_pnl.parquet` | **48,8 %** | **84,0 %** | neo post-hoc `2,0 %/lệnh` × `d_mean(K)` |

Hệ quả: kết luận cũ *"`K=12` phá trần ⇒ size phải co **0,83×**"* dựa trên `gross_max(K=8)=84 % > 70 %`.
Nếu định nghĩa MỚI đúng thì trần 70 % **không bind** và kết luận cũ sai. Việc này **được chốt TRƯỚC** bằng số.

Đồng thời: **chưa ai chấm lại ~artifact cũ** bằng RÀO MỚI (a)/(b′) + 4 THƯỚC CHUẨN, nên chưa có BẢN ĐỒ `asym`.

---

## 1. CHỐT CÁCH ĐO `asym` (không đổi sau khi thấy số)

- `asym := mean(|pnl| của leg LỖ) / mean(pnl của leg LÃI)`, tính trên **pnl USDT của từng lệnh** trong ledger (`printDone.csv`), **KHÔNG** mô phỏng lại.
  - Leg LỖ: `pnl < 0`; leg LÃI: `pnl > 0`; loại `NaN`.
  - `wl_ratio := 1 / asym`.
  - Trùng công thức `research/analysis/size_count_score.py::tail()` (commit `b1b77d6`).
- `sign% := 100 × tỉ lệ leg có pnl > 0`.
- **Thiếu dữ liệu ⇒ KHAI RÕTHIẾU**, không suy diễn. Không có `printDone.csv` hoặc không có `pnl` ⇒ loại run khỏi bảng, ghi vào danh sách MISSING.

## 2. HAI CÔNG THỨC `gross` SẼ SO SÁNH (chốt)

Gọi `m_leg` = `margin` của một leg (USDT); `E(t)` = equity ngày (từ `sim.out`); `open(t)` = tập leg đang mở tại `t` (theo `start`→`end`).

- **`G_new` (MỚI)** = trung bình theo thời gian của `100 × Σ_{open(t)} m_leg / E(t)`.
  - `G_new_max` = max theo thời gian của cùng biểu thức. (đúng `size_count_score.gross()`).
- **`G_old` (CŨ)** = `100 × S0 × d`, với **`S0 = 0,02` (neo post-hoc "2,0 %/lệnh")** và
  - `d_mean` = TB theo thời gian của số **coin phân biệt** đang mở; `d_max` = max.
  - (đúng `cap70_fee06.py` dòng ~14–16, 129).
- **Đo `G_old` HAI NGUỒN để tách nguyên nhân lệch:**
  - `G_old[ledger]`: `d` lấy từ **chính ledger `cd-sel15`** (cùng dữ liệu với `G_new`).
  - `G_old[pool]`: `d` lấy từ pool `label_b_pnl.parquet` top-K (như `844ca68`).
- **Bảng đối chiếu trên CÙNG 1 artifact `cd-sel15`** là bằng chứng phán xử: nếu `G_old[ledger] ≈ G_new` thì **2 công thức CÙNG DẠNG**, chênh số do **INPUT `d`** (pool vs ledger), không phải do công thức.

## 3. TIÊU CHÍ "gần < 1"

- `asym < 1,00` ⇒ **PASS (đạt đối xứng)**.
- `1,00 ≤ asym < 1,30` ⇒ **GẦN** (đáng đào thêm).
- `asym ≥ 1,30` ⇒ **XA**.
- `asym` thấp nhất đạt được = min trên tập artifact; nếu min ≥ 1,00 thì kết luận **"chưa tồn tại cấu hình `asym<1`"** (không được nói "chưa thử").

## 4. RÀO + THƯỚC (chốt, theo owner 27/09 05:22)

- **RÀO (a)**: `%PnL từ top-1 % leg ≤ 15 %` (`top1_share`).
- **RÀO (b′)**: bỏ **top-50 %** leg (theo pnl giảm dần) ⇒ **Σ pnl còn lại > 0** (`TF50 > 0`). Ghi thêm `TF30`, `TF40`.
- **`q*`** = % leg (từ lớn nhất) phải bỏ để Σ còn lại ≤ 0.
- **4 THƯỚC CHUẨN**: `wl_ratio · tf_5 · loss_mean · conc_5` (+ dự bị `median`).
  - `tf_5` = mean pnl của 95 % leg đuôi (bỏ top-5 %); `conc_5` = `100 × Σ(top-5 %)/Σall`.
- **RÀO CŨ**: `--appetite latest` = `maxDD ≤ 40 · UW ≤ 250 · qmin ≥ −20 · 0 năm âm · conc 1 coin ≤ 15 · gross ≤ 70`.
- **Bộ rate**: `{TSloss% · mP|SM · mP|SL · mMargin}` + luật siết.

## 5. THAM SỐ THỐNG KÊ (chốt)

- Block bootstrap `BLOCK_H = 72 h`, `NREP = 2000`, `SEED = 20260905`, neo `2021-07-01`.
- `k = 4`, `inflate(k) = 1,6651` (như `size_count_score.py`).
- Không đổi seed/k sau khi đọc số.

## 6. BẢN ĐỒ `asym` — nhóm theo CẤU TRÚC (chốt trục nhóm)

Nhóm theo metadata run (`prof_run.properties` + `result.json`):
1. **time-stop**: có/không (`SIM_LOSER_TIME_STOP_HOURS`).
2. **DCA**: grid (`DCA_GRID_ENABLED=true`) vs reactive/không grid.
3. **nhịp entry**: `SIM_ENTRY_SAMPLE_MIN` 15 phút vs 1 phút vs khác.
4. **K**: `SELECTOR_RANK_TOPK`.
5. **profile/thuật toán** (`profile` trong `result.json`) khi các trục trên giống nhau.

Kết luận: cấu trúc nào cho `asym` **thấp nhất**, và nó có `< 1` không.

## 7. GIỚI HẠN KHAI TRƯỚC

- Artifact do **nhiều vòng/nhiều agent khác nhau** sinh, khác window/universe/phiên bản code ⇒ **không phải so sánh nhân–quả**; chỉ là **bản đồ**.
- Nếu thiếu `entry`/`exit`/`pnl` để tính một chỉ tiêu ⇒ **ghi rõ THIẾU**, không suy diễn.
- `G_new` bỏ qua equity **nội ngày** (chỉ dùng equity ngày) ⇒ là **cận**; đã khai trong `RESULT_SIZE_COUNT`.
