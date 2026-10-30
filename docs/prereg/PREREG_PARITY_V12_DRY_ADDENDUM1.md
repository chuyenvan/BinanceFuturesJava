# PREREG_PARITY_V12_DRY — ADDENDUM 1 (2026-10-30, viết TRƯỚC deploy dry và trước mọi phép đo)

- **Gốc:** `docs/prereg/PREREG_PARITY_V12_DRY.md` (`3c7dae05`). Mọi điều không nhắc ở đây giữ nguyên.
- **Thời điểm:** chưa deploy dry, chưa có số nào của cửa sổ ⇒ không phải sửa sau khi thấy số.

## 1. Lý do (ghi trung thực)
1. Bản gốc §2.6 viết "LEGACY = ∅ (dry không có LEGACY) — khác ∅ ⇒ DỪNG". **SAI về thực tế 242:** process strategy trên 242 vẫn quản
   lý vị thế thật cũ của tài khoản 242 — log `[LEGACY] managed 44: …` (10-30 22:53 +07). Câu "dry không có LEGACY" chỉ đúng cho
   **sổ c3 dry** (DryGateway, tài khoản giả lập). Giữ nguyên như bản gốc ⇒ cửa sổ DỪNG ngay ngày đầu vì lý do sai.
2. Round 4h (v1.2/c3-live, ROUND4H §1) đổi lọc ứng viên TRƯỚC gate theo quy ước sim: coin đang giữ (dry: sổ giấy twin)
   **đếm hạng nhưng không qua gate, không nạp r**; LEGACY **đếm hạng + qua gate (nạp r) nhưng không vào**; A1 loại ⇒ bỏ hẳn.
   Jar r4f (trước đó): LEGACY bị bỏ trước khi đếm hạng; coin giữ trong sổ giấy vẫn nạp r.

## 2. Thay đổi
- **§2.6 (thay):** tập LEGACY theo phút = dòng `[LEGACY] managed N: …` gần nhất của log trading (không còn điều kiện "= ∅").
  - jar dry **≥ r4h** (log có `[GATE-PRE]`): S1-I = thứ tự top-24 `sel_dump` == sort(score↑, symbol↑) của `s1_dump` **sau khi chỉ
    bỏ symbol A1 loại** (LEGACY và coin đang giữ VẪN chiếm hạng, quy ước sim cap-then-skip). GV-I/P2 chỉ chấm cặp (phút, symbol)
    **không** thuộc coin đang giữ (dòng `[GATE-PRE] … bo_dang_giu=`); LEGACY được chấm như ứng viên thường (đã nạp r).
  - jar dry **r4f**: giữ luật v1.1 (bỏ LEGACY trước hạng). Ghi rõ jar ở D1.
- **§4 (làm rõ):** "dry không LEGACY ⇒ KPI lạc quan" áp cho **sổ c3 dry**; ứng viên selector vẫn bị 44 LEGACY chiếm hạng (r4h) hoặc
  bị bỏ (r4f) — khác sim (sim không có LEGACY). Ghi số phút có LEGACY trong top-24 mỗi ngày (mô tả).
- **P3 (làm rõ):** q replay causal dùng chính buffer đọc từ 242 (cat) — nếu deploy dùng `GATE_BUFFER_SEED` thì ghi md5 seed ở D1;
  buffer = seed (≤ bản ghi cuối seed) + r live sau đó (log `[GATE-SEED]`).
- Ngưỡng, nhãn, định nghĩa ngày sạch, ngày sập: **không đổi**.
