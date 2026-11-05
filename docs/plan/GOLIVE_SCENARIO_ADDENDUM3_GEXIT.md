# GOLIVE_SCENARIO — ADDENDUM 3: tiêu chí trượt THOÁT (G-EXIT) trong G-PILOT (2026-11-05, TRƯỚC micro-live)

Gốc: `GOLIVE_SCENARIO.md` + ADD1 (90cd2e77) + ADD2 (37489f62). Addendum này THÊM một mục vào G-PILOT. Không đổi gì khác.

## 0. Khai báo thứ tự
- Ngưỡng dưới đây do MASTER đề xuất **sau khi** đã thấy số mô tả của exec-probe (ADD2 §0): thoát trailing có trung vị 26,8 bps,
  p90 209 bps, trong khi sim là 0,67 bps.
- Ngưỡng được chốt **trước khi có bất kỳ fill micro-live nào**, vì micro chưa bật.
- Tập chấm điểm chỉ gồm **fill thật của micro-live**. Số exec-probe không dùng để chấm, chỉ đặt cạnh để mô tả.

## 1. G-PILOT mục 7: G-EXIT — ĐẠT khi cả (a) và (b) đúng
- **(a) Trượt thoát:** trung vị `slip_exit_bps` ≤ **30 bps**.
- **(b) PnL ròng/leg sau trượt:**
  - Tính R = Σ ret_live / Σ ret_sim trên các cụm khớp. Đạt khi R ≥ **0,80**.
  - Nếu Σ ret_sim ≤ 0, điều kiện thay bằng Σ ret_live ≥ Σ ret_sim − 0,2·|Σ ret_sim|.
- **Báo kèm, chỉ để mô tả, không làm cổng:**
  - p90 trượt thoát;
  - trượt theo loại thoát (stop / MARKET);
  - đặt cạnh số exec-probe ở ADD2 §0.

## 2. Định nghĩa (chốt trước khi đo)
- **Lệnh thoát:** lệnh SELL của c3 trong kỳ micro có fill thật. Hai loại:
  - `c3s-…`: STOP_MARKET trailing hoặc bảo vệ.
  - `c3x-…`: MARKET reduce-only (flatten, time-stop, đóng ngay khi -2021).
- **Mẫu:** mỗi lệnh thoát là một mẫu, trượt tính trên giá khớp trung bình của lệnh.
- **Nguồn:** sổ c3 và ledger `run/c3live_ledger.csv`, cùng dòng audit `[C3-LIVE-ORDER]`.
- **Trượt thoát:** `slip_exit_bps = (ref − avgFill) / ref × 10 000`. Dương nghĩa là xấu hơn ref.
  - Lệnh `c3s-`: ref = stopPrice của stop đã kích hoạt.
  - Lệnh `c3x-`: ref = giá close nến 1m của phút quyết định đóng.
- **ret của một cụm:**
  - Live: `ret_live = (realized_pnl − commission) / (qty × avg_entry) / số_leg`, lấy từ ledger.
  - Sim: `ret_sim` cùng công thức, lấy từ cụm cùng symbol và cùng `ts_first_leg` trong sổ giấy twin (ShadowBookC3) chạy song song.
  - Chuẩn hoá theo notional, vì size live và size twin khác nhau.
  - Cụm chỉ có ở một phía bị loại khỏi (b). Số cụm bị loại phải báo.
- **Mẫu tối thiểu:** ≥ 20 lệnh thoát **và** ≥ 10 cụm khớp.
  - Thiếu mẫu thì không có verdict. Khi đó owner quyết bằng văn bản (`Q4_OWNER`, ghi commit), như G-EXEC.
  - Thị trường êm không phải lý do bỏ qua cổng.

## 3. Cổng và script
- File `GOLIVE_GATE_PILOT.ok` phải có dòng: `g_exit=<DAT|TRUOT|Q4_OWNER> <median_bps> <R> <n_exit>/<n_cum> <dẫn chứng>`.
- Cách `golive_pilot_on.sh` xử lý dòng này:
  - Thiếu dòng: từ chối.
  - `TRUOT`: từ chối. Chỉ owner viết lại Q4 mới gỡ được.
  - Nhận `DAT` hoặc `Q4_OWNER`.
- Addendum này được commit **TRƯỚC** khi đổi script.
