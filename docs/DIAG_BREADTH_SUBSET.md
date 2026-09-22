# DIAG_BREADTH_SUBSET.md — TASK B2 Bước 8: RECON 0-sim breadth theo SUBSET (majors/alts), cổng GO/NO-GO

Thực thi 2026-09-22, executor (session `session_01UoVRjusfNM2USSVNKQrm7z`), branch `module`, repo
`/home/ubuntu/src/BinanceFuturesJava`. Design: `TASK_B2_step8_breadth_subset_split.md` (MASTER).
Tiền đề: BRC (Bước 7, `RESULT_BREADTH_CONT.md`) = NULL.

**VERDICT RECON: NO-GO (áp máy móc §1.3, không nới). KHÔNG sim.** Lý do gọn: book T170 ~98% alts ⇒
relevant-breadth = alt-only; nhưng alt chiếm 612/627 symId của all-coin ⇒ alt-breadth ≈ all-breadth
(chênh gate mọi năm < 0.032, dưới ngưỡng 0.10). Subset-breadth KHÔNG tách được năm tốt/xấu hơn all-coin.

## 0. Cổng an toàn
- **0-sim**: chỉ chạy `research/analysis/breadth_subset_recon.py` (Python, đọc CLOSES_1H.bin +
  map_kaggle.csv + printDone.csv). KHÔNG chạy Java, KHÔNG build, KHÔNG sửa .java, KHÔNG sim Kaggle.
- **shadow-c3 KHÔNG bị đụng**: executor không stop/kill/systemctl bất cứ tiến trình nào; chỉ đọc file.
- **HOLDOUT 2026**: load_closes lọc ts<2026-01-01 (nguyên văn `trend_rank_ic`); cửa sổ 2021-07-01..2025-12-31.
- **git**: không push, không checkout đổi tree. index.lock không gặp (tree sạch, HEAD `13064b3`).

## 1. Phương pháp (tái dùng hạ tầng Bước 5-7, 0 dòng mới về cơ chế breadth)
- Nguồn giá: `trend_rank_ic.load_closes()` → `/home/ubuntu/java/fsrun/CLOSES_1H.bin` (close 1h/symId,
  ts<2026-01-01). Daily close cuối ngày UTC.
- Breadth(D) = % coin "song" có `close[D-1] ≥ MA200_causal(D)` (MA200 min_periods=30, shift(1) —
  nguyên văn `breadth_regime.up_matrix`/`breadth_from_up_matrix`). Score = breadth/100.
- Gate = `continuous_gate(score) = 1.0 + 0.7×clip((0.5 − score)/0.5, 0, 1)` (nguyên văn
  `breadth_robust.continuous_gate`, gate_up=1.0/gate_down=1.7/thr=0.50 — KHOÁ y BRC).
- **Universe** (symId theo `/home/ubuntu/map_kaggle.csv`): `all` = mọi symId có close (627 symId toàn
  kỳ); `top50`/`top30` = symId ≤ N (PROXY thứ tự niêm yết Binance Futures, giống B5/6/7, KHÔNG phải
  volume rolling thực); `major` = danh sách majors KHOÁ TRƯỚC; `alt` = all − major.
- **Majors KHOÁ TRƯỚC** (KHÔNG đổi sau khi thấy kết quả): BTC ETH BNB SOL XRP ADA DOGE AVAX DOT LINK
  TRX MATIC POL LTC BCH → symId {1,2,3,49,58,14,27,33,62,44,29,35,285,57,16} (15/15 có trong CLOSES).
- **Sanity check machinery**: gate all-coin 2025 = **1.423** — TRÙNG BRC (`RESULT_BREADTH_CONT.md`
  ghi mean 2025 = 1.423). Xác nhận script tái lập đúng cơ chế BRC.
- 2021 = H2 only (day_range bắt đầu 2021-07-01).

## 2. §1.1 Book-composition T170 (printDone.csv, level=PREDICT_SYMBOL_TRADE, phân loại theo symbol)
Tổng 821 vị thế / 321 symbol phân biệt. Phân theo năm mở lệnh (field `start`).

| kỳ | tổng vị thế | majors | % majors | % alts |
|---|---:|---:|---:|---:|
| Toàn kỳ | 821 | 18 | **2.19%** | **97.81%** |
| 2021 (H2) | 117 | 3 | 2.56% | 97.44% |
| 2022 | 170 | 9 | 5.29% | 94.71% |
| 2023 | 76 | 2 | 2.63% | 97.37% |
| 2024 | 211 | 3 | 1.42% | 98.58% |
| 2025 | 247 | 1 | 0.40% | 99.60% |

- Chi tiết 18 vị thế majors: ADA×1, AVAX×4, BCH×1, BNB×1, DOGE×4, LTC×1, SOL×5, TRX×1.
- **KHÔNG có** vị thế BTC, ETH, XRP, DOT, LINK, MATIC, POL nào (0 lệnh).
- ⇒ **T170 alt-heavy tuyệt đối** (≈98% alts, mọi năm ≥94.7%). relevant-breadth = **alt-only**
  (rẽ nhánh §1.3: major < 40% ⇒ alt), KHÔNG mập mờ, KHÔNG cần composite.

## 3. §1.2 Gate-profile per-year × 5 định nghĩa breadth (DESCRIPTIVE — trả lời câu top30/all của Uni)
`gate_mean` = trung bình gate ngày trong năm (gate = continuous_gate, MA200/thr50, causal).

| universe | 2021(H2) | 2022 | 2023 | 2024 | 2025 |
|---|---:|---:|---:|---:|---:|
| **all-coin** (627) | 1.199 | 1.607 | 1.274 | 1.250 | **1.423** |
| top50-vol (proxy) | 1.193 | 1.604 | 1.247 | 1.225 | 1.314 |
| top30-vol (proxy) | 1.170 | 1.590 | 1.257 | 1.203 | 1.275 |
| major-only (15) | 1.050 | 1.562 | 1.105 | 1.127 | 1.215 |
| **alt-only** (612) | 1.230 | 1.612 | 1.293 | 1.259 | **1.435** |

Breadth-score trung bình năm (phần, để đối chiếu): all 2025=0.204, alt 2025=0.194, major 2025=0.492;
all 2023=0.394/2024=0.459, alt 2023=0.377/2024=0.450, major 2023=0.585/2024=0.622.

**Câu phán quyết recon §1.2** ("có định nghĩa nào cho gate-2025 ≥ 1.60 VÀ giữ gate-2023 & 2024 ≤ 1.20?"):
**KHÔNG.** Không universe nào đạt. Chi tiết:
- Không universe nào có gate-2025 ≥ 1.60 (cao nhất là alt 1.435). Nguyên nhân cấu trúc: gate_mean năm
  chỉ ≥1.60 khi score-năm ≲ 0.071 (giải `1.0+0.7×(0.5−s)/0.5 ≥ 1.60`). Chỉ 2022 (bear gần toàn phần,
  score ~0.06) đạt. 2025 alt-score trung bình 0.194 (alt crash tập trung + MA200 chậm) ⇒ gate-2025
  ĐÓNG TRẦN ~1.44, KHÔNG thể chạm 1.60/1.7 trên bình quân năm.
- Định nghĩa hẹp hơn (top30/top50) **NỚI** 2025 (gate 1.275/1.314 < all 1.423) chứ không siết —
  vì top-niêm-yết gồm majors + alt mạnh giữ giá tốt 2025 ⇒ đọc 2025 "khoẻ hơn" (đúng chiều SAI mà
  MASTER cảnh báo). major-only nới mạnh nhất (2025=1.215). ⇒ **thu hẹp universe làm 2025 phòng thủ
  KÉM hơn, không tốt hơn**. Trả lời trực tiếp Uni: top30/all đều không cứu được 2025.

## 4. §1.3 Cổng GO/NO-GO (áp máy móc, KHOÁ TRƯỚC — không nới)
relevant-breadth = **alt-only** (book §2 alt-heavy). So sánh alt vs all-coin:

| năm | gate alt (rel) | gate all | chênh rel−all |
|---|---:|---:|---:|
| 2021(H2) | 1.2303 | 1.1992 | +0.0311 |
| 2022 | 1.6120 | 1.6071 | +0.0049 |
| 2023 | 1.2925 | 1.2739 | +0.0186 |
| 2024 | 1.2589 | 1.2502 | +0.0087 |
| 2025 | 1.4355 | 1.4228 | +0.0127 |

**Điều kiện GO** (tất cả phải đạt):
- gate-2025 ≥ 1.60 → **1.436 FAIL**
- gate-2023 ≤ 1.20 → **1.293 FAIL**
- gate-2024 ≤ 1.20 → **1.259 FAIL**
- gate-2022 ≥ 1.55 → 1.612 PASS
- chênh ≥ 0.10 so all ở ≥1 năm → **max |chênh| = 0.031 (2021) FAIL**
⇒ GO = **FALSE**.

**Trigger NO-GO** (bất kỳ điều nào):
- relevant-breadth ~ trùng all-coin (chênh MỌI năm < 0.10) → **TRUE** (max 0.031) kích hoạt.
- siết cả 2023&2024 (gate>1.30) → False (1.29/1.26).
- major-heavy & major-2025 khoẻ → không áp (book alt-heavy).

**VERDICT: NO-GO (rõ).** Không borderline: book alt-heavy dứt khoát (rel=alt không mập mờ), và
alt-breadth ≈ all-breadth theo cấu trúc (alt = 612/627 symId ⇒ 15 majors không dịch được bình quân
all-coin). Đúng y dự báo MASTER: "NO-GO nếu relevant-breadth ~ trùng all-coin".

## 5. Kết luận & khuyến nghị
- **NO-GO máy móc ⇒ DỪNG, KHÔNG sim** (đúng luật §1.3 + "Xử lý sau recon"). Subset-breadth (mọi định
  nghĩa) KHÔNG tách được năm tốt/xấu hơn all-coin cho chiến lược T170.
- **Lý do gốc (2 tầng)**:
  1. **Book alt-heavy** (98%) ⇒ nhóm "relevant" là alts, mà alts CHÍNH LÀ đại đa số all-coin (612/627)
     ⇒ đổi định nghĩa breadth sang alt-only gần như không đổi tín hiệu (chênh gate ≤ 0.031/năm).
  2. **Chiều siết-2025 bất khả**: điều T170 cần là gate-2025 → ~1.7 (siết như flat 1.7). Nhưng breadth
     bình quân năm 2025 của alts = 0.194 (không phải ~0 như 2022) ⇒ gate liên tục đóng trần ~1.44.
     Muốn siết mạnh hơn phải rời breadth-mean sang cơ chế khác (không thuộc phạm vi lever breadth).
- **Đóng lever breadth-subset**: cùng với BR (Bước 6, NULL) và BRC (Bước 7, NULL), đây là bằng chứng
  thứ 3 rằng breadth-gate không phá được trade-off breadth↔UW-2025 cho T170. Ghi `docs/power_wall.md`.
  T170 (flat 1.7) vẫn là incumbent tốt nhất trên khẩu vị + giữ 2025.
- **Không mở biến thể mới** (thr/gate_up/down khác, universe khác) trong round này (luật chống dredging).
  Hướng chính theo roadmap: TASK D (event-alpha listing/delisting, độc lập MOM15).

## 6. Đối chiếu dự báo MASTER (design-doc, khoá trước)
| Dự báo MASTER | Thực tế | KQ |
|---|---|---|
| "NO-GO nếu relevant-breadth ~ trùng all-coin (chênh mọi năm <0.10)" | max chênh 0.031 | ĐÚNG |
| "sửa chiều agent: thu hẹp/major đọc 2025 khoẻ ⇒ nới ⇒ thảm" | top30/50/major đều nới 2025 (1.28/1.31/1.22<1.42) | ĐÚNG |
| "trần cấu trúc, subset-breadth khó phá" | gate-2025 đóng trần ~1.44 mọi universe | ĐÚNG |

## 7. Artifacts & thay đổi (0 dòng Java, 0-sim)
- Mới: `research/analysis/breadth_subset_recon.py` (script recon), `research/analysis/out/breadth_subset_recon.json`.
- Tái dùng (không sửa): `trend_rank_ic.load_closes`, `breadth_regime.up_matrix`/`breadth_from_up_matrix`,
  `breadth_robust.continuous_gate`, `/home/ubuntu/map_kaggle.csv`, printDone T170.
- KHÔNG đụng: Java, jar, Kaggle, shadow-c3, HOLDOUT, git push.

---
Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01UoVRjusfNM2USSVNKQrm7z
