# PREREG_PARITY_V12_DRY — ADDENDUM 9: BỎ seed, không re-seed (2026-11-05, quyết định MASTER)

## 1. Quyết định
- Seed A ∪ C (ADD2–ADD7) **KHÔNG dùng**. Bỏ seed khỏi đường go-live. Không làm re-seed theo ADD6 §2, không restart dry vì seed.
- Cửa sổ ngày sạch **Nhóm H** giữ nguyên: **2026-11-04 → 2026-11-10** (ADD6 §3). **Nhóm K** (KPI dry, T-BOOK, so dải backtest A1)
  không có mốc re-seed, nên đi theo nhánh "seed A không có trước 11-10" của ADD6 §3: MASTER quyết bằng văn bản riêng.
  Từ ADD6 §1 trở đi, KPI/T-BOOK vẫn ghi "không so được".
- Env C11 áp lúc micro_on (MASTER). Việc này nằm ngoài phạm vi chấm parity của file này.

## 2. Lý do: V-OVL (i) TRƯỢT, là lệch THẬT, không phải lỗi đo
- Kết quả `vovl.py` (ADD4 feb32107, chạy 2026-11-05 05:55): n_pairs = 6, i_frac = 0,0 → (i) TRƯỢT. (ii) ĐẠT (median 0,34 %, max 2,09 %).
  Theo ADD4 §1 thì seed dùng được ⇔ (i) VÀ (ii), TRƯỢT ⇒ DỪNG, không nới.
- Chẩn đoán (`gst1030/seed/vdiag.py`, `vdiag2.py`, chỉ đọc):
  - Khoá join đúng. ts hai phía là ms tròn phút (mod 60000 = 0 ở 100 % dòng), cùng trục UTC. Ngày 10-20 trùng 1439/1439 phút ts.
    Dời ±5 phút thì dời 0 cho lệch nhỏ nhất.
  - p15 (1 giá trị/phút): trên 21 156 phút chung 10-17..10-31 chỉ 1 phút bằng nhau, lệch tương đối median 6,3 %, mọi ngày.
    gateValue/sp từng symbol cũng khác. Join (phút, sp float32) ra 1/34 428 cặp.
  - Nguyên nhân: sim A (`gs-x14-s42`) lấy p15/sp từ `pred_s42` (gs-chain-q4, PRED_MD5_USED df1ed6d5…), không phải model live.
    Buffer từ sim vì vậy không cùng phân phối r với live ở mức bit.
- Không sửa `vovl.py`, không viết lại tiêu chí.

## 3. Hệ quả
- `kaggle_priority` đã xoá (05:55). Orchestrator seed dừng. Không push thêm kernel seed.
- Cờ watcher v12 / day_report_v12 không đổi.
