# RESULT — GATE_VZ: gate p15 + feature VZ cấp thị trường (2026-10-17)

- Pre-reg `docs/prereg/PREREG_GATE_VZ.md` ee97237b; addendum 1 208db28d (MTM nguồn Vision), 2 5a49b97a (VZ-B NaN < 2021-12-02, dung sai D3), 3 2643be92 (owner: chỉ là ứng viên dự phòng). Code `research/gvz/` 7807542f (+ sửa builder trong 5a49b97a).
- **Kết luận: NO-GO cả hai arm (VA, VB).** Không vào mở rộng 16 seed (6.3: mean ΔCAGR_DEV < +1,5pp ở cả hai). Không chạy HO 2026 (mục 7 chỉ áp cho arm GO). Không đổi gì trên 242/shadow.

## Kiểm dữ liệu (PASS)
- D1: G0 train lại từ store Kaggle `bdchain-gate-store` trùng bit `gabl/p15_G0.npy`; pearson vs pred.bin min 0,9919.
- Căn thời gian: momentum1M dòng T ↔ nến open=T (r 0,87); nhãn dùng close nến T ⇒ VZ trễ thêm 1 nến; metrics `ts ≤ T−10m`.
- D2 phủ ≥ 99,9% (VZ-A), ≥ 96,9% (VZ-B); D3 30 dòng tính lại độc lập worst 2,7e-6; D4 trùng biến thể trễ 1 (|Δ| 3e-8).
- MTM: nguồn Vision tái lập cache gqsf-s7/a1 trùng tuyệt đối. Parity 17/17 sim PASS (jar 0944841c, topk24, skipFull ON, pred md5).

## Kết quả (Δ = arm − baseline cùng seed; DEV = 2022–2024)

| Arm | mean ΔCAGR_DEV | CI 97,5% | seed > 0 | ΔCalmar_DEV | ΔmaxDD_DEV | Δ năm 22/23/24 | Δ 2025 (VAL) | C1 | C2 | C3 | C4 | C5 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| VA (VZ-A, 8 cột) | +0,68 | [−1,65; +3,02] | 4/8 | +0,30 | +2,89 (nông hơn) | +3,39 / −1,51 / −1,06 | −2,62 | ✗ | ✗ | ✓ | ✗ | ✗ |
| VB (VZ-A + OI/LS, 13 cột) | +0,39 | [−4,84; +5,62] | 6/8 | +0,29 | +2,73 | −0,53 / −0,77 / +2,66 | +1,33 | ✗ | ✓ | ✓ | ✗ | ✓ |

Từng seed ΔCAGR_DEV:
- VA: 42 +3,06 · 7 +4,06 · 13 −3,39 · 21 +1,61 · 99 −0,24 · 123 +1,07 · 777 −0,20 · 2024 −0,50
- VB: 42 +2,73 · 7 +0,45 · 13 +2,07 · 21 +7,69 · 99 +2,80 · 123 +0,40 · 777 −10,16 · 2024 −2,87

Baseline (CAGR_DEV): B42 38,22 (pred python G0, skipFull 588) · gqsf-s7 35,62 · s13 39,04 · s21 36,45 · s99 39,35 · s123 35,71 · s777 43,61 · s2024 38,13.

## Đọc kết quả (hậu kiểm — KHÔNG dùng để đổi kết luận)
- Cả hai arm làm **maxDD DEV nông hơn** (VA 8/8 seed, VB 6/8; mean ≈ +2,8pp) và Calmar +0,3, nhưng lợi suất không tăng ổn định: lợi/thiệt dồn theo năm và đổi chiều giữa seed. Phút gate-mở gần như không đổi; thay đổi nằm ở *phút nào* được mở trong các đợt sập.
- VB phân tán rất lớn (sd Δ ≈ 5,6; S777 −10,2, S21 +7,7): thêm OI/LS làm model nhạy với seed hơn, không ổn định hơn. Median ΔCAGR_DEV VB ≈ +1,3 nhưng không phải tiêu chí.
- p15 mới vẫn tương quan 0,90–0,98 với p15 gốc; feature VZ chiếm ~8% (VA) / ~12% (VB) gain. IC đơn biến cao nhất là vzNtR15/vzQvR60 (trùng thông tin volume đã có). Giống kết luận 10-04: IC/gain không dự báo tiền.
- Nếu sau này cần hồ sơ DD thấp hơn (khẩu vị owner), VA là manh mối duy nhất đáng ghi nhận — phải pre-reg riêng với tiêu chí DD làm chính + HO 2026, không tái dùng vòng này.

## Hạ tầng tái dùng được
- `research/gvz/gvz_mtm.py`: MTM legacy nguồn kline1m Vision (thay ticker bin đã xoá), thêm cửa sổ DEV.
- `gvz_feat.py` (feature market-level causal), `gvz_train.py` (recipe gate + cột thêm), `gvz_sim.py` (orch Kaggle ghép cặp gqsf), `gvz_score.py` (C1–C5).
- Store gate gốc: Kaggle `chuyendinh/bdchain-gate-store` (bản `.csv.gz` cục bộ đã mất).
