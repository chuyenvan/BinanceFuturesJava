# RESULT_SHORT_V3 — SHORT: NỀ FUNDING + TĂNG WINRATE

Prereg: `docs/prereg/PREREG_SHORT_V3.md` (`06b8046d`, commit TRƯỚC đo).
Chấm: 0-sim, **KHÔNG train lại** (bins Kaggle `sm-train-gpu` đã có), DEV ≤ 2025-12-31, không chạm 2026.
Script: `research/analysis/short_v3_score.py` (chấm) · `short_v3_analyze.py` (gộp 3 seed + luật).
Dữ liệu: bins `SHORT{42,7,13}` (nhãn `ndown thr 1,5 %`, 3 seed) · nhãn `.pb` 4/12/24/72h ·
funding **chính xác từng lệnh** từ `/tmp/fund_cache.npz` (Aerospike `test.funding_data`).
OOS: 16 fold, 35.450.551 dòng/arm. CI block-72h, NREP=2000, SEED=20260905, ×1,21.

## 0. VERDICT: **NO-GO/NULL** (theo luật §6 khóa)

Không có cấu hình **tradeable** nào đạt A (net sau funding ngoài CI) **và** B (≥3/4 năm dương)
**và** C (winrate ≥ 55 % & ≥ baseline +5 điểm %).

## 1. Nề funding giúp bao nhiêu (net trước/sau, mean-seed, %/lệnh)

| cấu hình (K8, cắt +30 %, T=72h) | giữ | net TRƯỚC funding | net SAU funding (exact) | Δ | winrate | năm dương |
|---|---|---|---|---|---|---|
| **baseline** (không lọc) | 100 % | +0,409 | **−0,171** | — | 0,558 | 1/4 |
| **N1b** lọc dấu funding **kỳ kế tiếp** (CAUSAL) | 66 % | +0,362 | **+0,374** | **+0,545** | 0,569 | 2/4 |
| **N1a** lọc `f_72h ≥ 0` (LOOKAHEAD) | 63 % | +0,583 | **+0,725** | +0,896 | 0,559 | 4/4 |
| N2a time-stop 4h | 100 % | −0,052 | −0,111 | — | 0,506 | 0/4 |
| N2a time-stop 12h / 24h | 100 % | +0,033 / +0,115 | −0,123 / −0,162 | — | 0,533 / 0,546 | 1/4 |
| N2b vào lệnh tránh mốc settle | 32 % | −0,121 | −0,121 | — | 0,491 | 1/4 |

- **Funding là chi phí thật:** baseline `fund_mean = −0,580 %/72h` — **khớp** `RESULT_SHORT_DEEP`
  (−0,585 %/72h) ⇒ cache + phương pháp đúng.
- **Causal (N1b):** lọc coin có rate kỳ settle kế tiếp ≥ 0 **lật net từ −0,171 % → +0,374 %**
  (+0,545 pp/lệnh) — nhưng CI **chứa 0** (`raw [−0,212, +0,948]`) và **chỉ 2/4 năm dương** ⇒ FAIL A & B.
- **Cận trên (N1a):** nếu biết trước funding **tương lai** thì net +0,725 %, 4/4 năm, ngoài CI.
  Đây là **LỌC LOOKAHEAD** (dùng `f_72h` phát sinh SAU khi vào lệnh) ⇒ **không tradeable, không tính GO**.
  Ý nghĩa: "độ lớn khoản funding" đủ lớn để cứu net, nhưng **tại thời điểm vào lệnh không dự báo đủ**.
- **Giữ ngắn để né funding (N2a/N2b) đều THẤT BẠI** (âm hơn baseline): né được funding nhưng mất alpha
  72h nhiều hơn phần tiết kiệm.

## 2. Winrate tăng được bao nhiêu + bằng cách nào

| đòn | net_pre | net_post | winrate | ghi chú |
|---|---|---|---|---|
| baseline K8 | +0,409 | −0,171 | 0,558 | — |
| **P1 chọn tinh K1 / K2 / K3** | +0,678 / +0,633 / +0,573 | **−0,590 / −0,429 / −0,359** | 0,560 / 0,562 / 0,562 | gross TĂNG nhưng funding **xấu hơn** (`fund_mean` K1 = **−1,268 %** vs K8 −0,580 %) |
| **P2 regime (breadth ≤0,5 tại t−72h)** | +0,298 | −0,370 | 0,546 | 2023 **tệ hơn** (−1,15 %) |
| **P3 cắt cứng +20/+30/+50/no-cut** | +0,420/+0,409/+0,342/+0,338 | −0,160/−0,171/−0,238/−0,242 | 0,542/0,558/0,566/0,569 | winrate nhích khi cắt lỏng |
| tổ hợp tốt nhất (N1b + regime, K3) | +0,236 | +0,174 | 0,570 | yrs+ 1,7; CI chứa 0 |

- **Winrate gần như BẤT BIẾN: 0,542–0,570**, tối đa **+1,1–1,2 điểm %** so baseline — **KHÔNG đòn nào đạt +5 pp**.
- Phát hiện cơ chế: **chọn tinh (K↓) làm gross TĂNG nhưng net GIẢM** — vì coin được chọn mạnh nhất
  lại là coin **funding âm nhất** (short phải TRẢ nhiều nhất). Alpha short và "được nhận funding"
  **ngược chiều nhau**; đây là lý do gốc khiến "nề funding" khó thành công.

## 3. 2023 / 2024 có hết âm không?

| | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|
| baseline | +0,981 | **−0,924** | **−0,241** | −0,479 |
| N1b (causal) | +1,339 | **−0,433** | **−0,053** | +0,671 |
| N1a (lookahead) | +1,281 | +0,070 | +0,161 | +1,422 |
| + regime (P2) | +1,158 | **−1,154** | −0,105 | −1,350 |

- Lọc funding **causal (N1b) kéo 2023/2024 về gần 0** (−0,43 % / −0,05 %) nhưng **chưa dương**.
- Lọc **regime breadth KHÔNG cứu 2023** — còn **tệ hơn** (−1,15 %). Giả thuyết "chỉ chết ở pha TĂNG"
  KHÔNG được xác nhận qua thước đo breadth-backward này.

## 4. Trả lời 4 câu

1. **Nề funding giúp bao nhiêu?** Causal: **−0,171 % → +0,374 %** (+0,545 pp/lệnh), nhưng CI chứa 0,
   2/4 năm dương. Cận trên lookahead: +0,725 %, 4/4 năm — **không tradeable**.
2. **Winrate tăng bao nhiêu?** Tối đa **+1,1–1,2 pp** (0,558 → 0,570). Không đòn nào (P1/P2/P3) đạt +5 pp.
   Đòn hiệu quả nhất: **N1b (lọc dấu funding kỳ kế tiếp) + regime** (winrate 0,570) — nhưng net CI chứa 0.
3. **2023/2024 hết âm?** Với lọc funding causal: **gần hết** (−0,43 % / −0,05 %) nhưng chưa dương;
   lọc regime **không** giúp (2023 tệ hơn).
4. **Kết luận: NO-GO.** Không có cấu hình short BỀN (net>0 ngoài CI & ≥3/4 năm & winrate đạt).
   **Còn thiếu CỤ THỂ:** (a) **dự báo funding của CẢ cửa sổ giữ** tại thời điểm vào lệnh (không chỉ dấu
   kỳ kế tiếp) — cần feature/term-structure funding đủ mạnh; (b) **alpha short TRỰC GIAO funding**
   (hiện chọn tinh lại rơi đúng coin funding âm nhất); (c) **path-aware + nề funding per-lệnh** —
   bins `pa` đã bị kernel Kaggle tự xoá (§5.3) ⇒ cần 1 vòng Kaggle train lại (~4 g GPU).

## 5. Deviations & giới hạn (khai báo)

1. **N1a là lookahead** — khoá trong prereg §2 nhưng chỉ dùng làm **cận trên**, KHÔNG tính GO.
2. **Chân BTC của gate regime (§3 P2) KHÔNG đo được:** universe nhãn `funding_label_*` **không chứa
   BTCUSDT** (kiểm chứng: 198 sym/file, 0 chứa "BTC"). Thay bằng **lợi suất EW thị trường tại t−72h**
   + breadth (đúng phần breadth đã khoá). Chỉ phụ trợ.
3. **Bins PATH-AWARE (`pa`) không còn**: kernel `sm-label2` xoá bins sau khi chấm ⇒ "kết hợp
   path-aware + nề funding" per-lệnh = **BỎ (blocked)**, không đo được vòng này.
4. Với T < 72h, **xếp hạng vẫn dùng head 72h** (bins chỉ có slot 72h) ⇒ N2a là "thoát sớm trên tín
   hiệu 72h", không phải model 4/12/24h.
5. Không mô hình liquidation/borrow (PERP, borrow = 0); chi phí base 0,112 %/vòng.

## 6. Sản phẩm

| File | Nội dung |
|---|---|
| `docs/prereg/PREREG_SHORT_V3.md` | prereg (`06b8046d`, TRƯỚC đo) |
| `research/analysis/short_v3_score.py` | chấm 0-sim 18 cấu hình × 3 seed |
| `research/analysis/short_v3_analyze.py` | gộp seed + áp luật GO |
| `docs/result/RESULT_SHORT_V3.json` | số đầy đủ (net/CI/winrate/by-year per cấu hình) |
