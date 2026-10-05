# AUDIT_SHORT_V3_R3 — Auditor đối kháng độc lập (2026-10-02)

Đối tượng: RESULT_SHORT_V3_R3 @ `0e7aee0b` (pre-reg `8b3e6202`, program `a8eff3fb` §R3). Script audit (chỉ đọc, không sửa
file gốc): `research/analysis/audit_short_v3_r3.py`, `research/analysis/audit_short_v3_r3_cluster.py`. Số chi tiết:
`docs/audit/AUDIT_SHORT_V3_R3_20261002.json`. Chạy trên Oracle (RSS 1,3 GB, ~20 s/lần), không Java, không 242, không đọc 2026.

## Kết luận audit
**Verdict NO-GO: GIỮ NGUYÊN, vững.** G4 (excess_short) và G5 (pSQ10) FAIL ở MỌI cách đo thử (pooled, bỏ 2 ngày sập,
trọng số theo ngày, cap 20 lệnh/ngày, SL khớp ở close thực). **Nhưng DIỄN GIẢI chính của result SAI một phần (mức trung bình,
không đổi verdict):** "BRK = capitulation → hồi +2,03%/7d" và "NO-GO đến từ điểm ước lượng ÂM, không do CI" là do **2 ngày sập**
(2025-10-10: 362 lệnh, 2024-08-05: 178 lệnh = 24,8% số lệnh). Bỏ 2 ngày này BRK rơi tiếp nhẹ (bleed_7d −0,47%), netproxy_7d +0,93%;
trọng số theo ngày netproxy_7d +2,00% (CI block [+0,57;+3,55], 4/4 năm) — tức G1–G3 sẽ QUA nếu đo theo ngày. Lý do NO-GO đúng:
**không tách khỏi rổ ALL cùng ngày (G4) và squeeze không thấp hơn (G5)**, cộng với phần dương theo-ngày là SL-convexity trên 1h
close (noSL theo ngày −0,81%) — lạc quan.

## 1. Định nghĩa BRK có đúng pre-reg + causal? — ĐÚNG
- Code: `lo30 = close.shift(1).rolling(30, min_periods=30).min()` (đủ 30/30), `r1 = close/close.shift(1) − 1`,
  `mqv = qv>0 .shift(1).rolling(30, min_periods=20).median()`, `rawB = E ∧ close ≤ lo30 ∧ r1 ≤ −0,05 ∧ qv ≥ 2·mqv`; cooldown
  `(i − last) > 7` ⇒ d+8 được phép, chuỗi bắt đầu DEV0. Khớp §3 pre-reg từng điểm.
- Tái hiện ĐỘC LẬP bằng numpy (cửa sổ cắt tay [i−30, i), không rolling, cooldown tham lam theo coin): E 354 241, raw_BRK 2 804,
  BRK 2 178, raw_BNV 18 096, BNV 9 721 — **lệch 0 ô** ở cả 5 mặt nạ. Vì cách tính chỉ dùng slice ≤ i ⇒ causal theo cấu trúc
  (bổ sung cho S-b của agent, cũng PASS).
- Dữ liệu vào: 0/2 178 BRK có ngày Aerospike thiếu phút (nrec<1440), 0 coin nmin<1380, 0 BRK có median nrec 30 ngày trước
  <1380 ⇒ tỉ lệ volume không bị thổi bởi ngày thiếu dữ liệu. Close panel (CLOSES_1H) = lastc Aerospike trên 100% BRK (lệch 0).
  Funding cache phủ tới 2025-12-31 23:00.
- Nhỏ: 2 BRK có close_d = lo30 đúng bằng (dấu ≤ cho phép, đúng pre-reg). Entry tại đúng close dùng để trigger (độ trễ 0, cần
  quoteVol cả ngày) — quy ước P0A, đã chốt; ảnh hưởng không đáng kể với verdict.

## 2. excess_short — dấu và cách tính ĐÚNG
- `excess = ret − mean(ret ALL cùng T, cùng ngày)`, `excess_short = −mean(excess)` ⇒ dương = BRK rơi mạnh hơn rổ. Tính lại độc lập
  (mean ALL khớp ngày − ret BRK): T3 −0,021%, T7 −0,150% = script tới 1e-9.
- ALL gồm cả chính các BRK; leave-out (bỏ BRK khỏi rổ ngày đó): T7 −0,12%, T3 −0,08% — không đổi kết luận.
- Theo ngày: T7 −0,28%, T3 +0,002%. So median ALL thay mean: T7 −1,69% (lệch do skew; pre-reg dùng mean — đúng).
- Trừ biến thể median (âm sâu hơn), mọi biến thể |excess_short| ≤ 0,42%; không biến thể nào > +0,3% cho BRK ⇒ G4 FAIL vững. CI raw excess_short T7 [−1,40;+0,85].

## 3. Inflate ×1,18 — lệch quy ước P0A nhưng ĐÃ CHỐT TRƯỚC, không ảnh hưởng verdict
- P0A: `INFL = z_k/1,96`, z_k = √(2 ln k): k=13 ⇒ 1,156 (nới). Áp k=2 ⇒ 0,60 (THU HẸP CI — vô lý). Agent ghi rõ ở pre-reg §5
  (commit trước khi đo) và dùng ×√(2 ln 2) = 1,18 nhân trực tiếp nửa-độ-rộng — nhất quán với R1 (×1,89 = √(2 ln 6)) và R2 (1,18)
  trong cùng PROGRAM_SHORT_V3. Không phải tune sau.
- So sánh cận dưới netproxy (T7): ×0,60 −3,37% · raw −4,50% · Bonferroni k=2 (2,241/1,96 = 1,143) −4,91% · ×1,156 −4,94% ·
  **×1,18 −5,01%** · ×1,89 −7,04%. T3 tương tự. G1 đã FAIL (điểm ước lượng −1,66% / −2,42%) ⇒ verdict BẤT BIẾN theo hệ số.
- Ghi chú phương pháp (cho chương trình, không phải lỗi vòng này): √(2 ln k) không phải lượng tử hiệu chuẩn khi k nhỏ (k=2 cho
  1,18 < 1,96); nên thống nhất một quy ước, ví dụ Bonferroni z_{1−0,025/k}/1,96 nhân nửa-độ-rộng. Chương trình nói "CI block (72h)"
  còn R3 dùng block 7 ngày (harness P0A, đã chốt ở pre-reg) — bảo thủ hơn với dữ liệu ngày; không đổi verdict.

## 4. SL trên 1h close lạc quan — có noSL; kiểm thêm SL khớp ở close thực
- Giờ chạm SL thực tế (close 1h đầu tiên ≥ +10%): mean +11,8%, p95 +15,6%, max +82% (agent giả định khớp đúng +10,2%).
- netproxy SL khớp tại close giờ chạm: T7 **−2,50%** (CI raw [−5,44;+1,15]), T3 −3,10%; noSL T7 −2,42%, T3 −4,77% (tái lập).
  Pooled: mọi biến thể âm ⇒ NO-GO không phụ thuộc giả định SL (agent đúng ở điểm này).
- Nhưng: SL 1h còn bỏ qua wick nội giờ ⇒ SL-rate thực cao hơn. Trong phân tích theo-ngày (mục 5) phần dương +2,00% đến từ
  SL-convexity (noSL theo ngày −0,81%) ⇒ không được đọc là edge.

## 5. Tập trung theo ngày — PHÁT HIỆN CHÍNH (đổi diễn giải, không đổi verdict)
| BRK T=7 | n | bleed | netproxy | noSL | CI raw | năm>0 | excess_short | pSQ10 (tỉ lệ ALL) | G1–G5 |
|---|---|---|---|---|---|---|---|---|---|
| pooled (= result) | 2175 | +2,03% | −1,66% | −2,42% | [−4,50;+1,75] | 2/4 | −0,15% | 52,2% (1,42×) | F F F F F |
| bỏ 2025-10-10 & 2024-08-05 | 1635 | −0,47% | +0,93% | +0,07% | [−1,17;+2,94] | 3/4 | −0,13% | 38,0% (1,03×) | T F T F F |
| trọng số theo ngày (360 ngày) | — | +0,11% | +2,00% | −0,81% | [+0,57;+3,55] | 4/4 | −0,28% | 38,2% (1,04×) | T T T F F |
| cap 20 lệnh/ngày | 1229 | +0,53% | +0,60% | −1,00% | [−0,98;+2,15] | 3/4 | −0,42% | 41,9% (1,14×) | T F T F F |

- Ngày 2025-10-10: 362 lệnh, bleed_7d +5,6%, SL 93,6%, pnl −9,1%; 2024-08-05: 178 lệnh, bleed +17,8%, SL 98%, pnl −10,2%.
  Top-10 ngày = 48,7% số lệnh. Bootstrap theo cụm ngày (pooled) T7 [−4,27;+1,89] ≈ block-7d.
- T=3 tương tự: bỏ 2 ngày bleed_3d −0,62%, netproxy +0,10%; theo ngày bleed −0,05%, netproxy +1,34% (CI [+0,14;+2,49], 4/4 năm)
  nhưng G4 (≈0) và G5 (27,2% vs 20,0% ALL = 1,36×) FAIL.
- Hệ quả cho các câu trong result phải sửa:
  (a) "BRK là điểm HỒI (capitulation) +2,03%/7d, +4,51%/3d" → chỉ đúng cho 2 ngày sập toàn thị trường; ngoài 2 ngày đó BRK
      rơi tiếp nhẹ (≈ rổ cùng ngày).
  (b) "NO-GO đến từ điểm ước lượng ÂM, không do CI" → sai về cơ chế; NO-GO vững vì G4/G5 (không tách ALL, squeeze ≈ rổ ngày).
  (c) "Hồi mạnh nhất 3 ngày đầu (bleed T3 > T7)" → artifact của 2 ngày (theo ngày bleed T3 −0,05% vs T7 +0,11%).
  (d) "Volume làm tệ hơn": pooled chênh BRK−BNV +3,0pp, theo ngày chỉ +0,8pp (BNV −0,70% vs BRK +0,11%) — hướng giữ, độ lớn bị thổi.
- Quy tắc GO pre-reg dùng pooled (Σpnl/Σn) — agent áp đúng; điểm trên là về diễn giải và về thiết kế CI/thống kê khi sự kiện
  cụm mạnh (n hiệu dụng ≈ số ngày, không phải số lệnh).

## 6. bull/¬bull — post-hoc, bị dùng làm "đề xuất amend" — CẦN RÚT
- Bảng C được pre-reg cho phép "CHỈ báo cáo"; mục G.2 ghi "không chọn" — OK. Nhưng "Đề xuất amend" viết "BRK∧bull (n 403) là
  lát dương duy nhất" — đây là hạt giống chọn-sau-khi-thấy và còn là ARTIFACT: cả 2 ngày sập đều ¬bull. Theo ngày: bull +2,14%
  vs ¬bull +1,98% (không khác); ¬bull bỏ 2 ngày sập +0,34%. ⇒ tương phản bull/¬bull gần như hoàn toàn là hiệu ứng 2 ngày, không
  nên mở pre-reg BRK∧bull trên cơ sở này.

## 7. Tái lập
- Chạy lại `short_v3_r3_breakdown.py` (HEAD = 0e7aee0b cho cả script và harness P0A, worktree sạch), so JSON với file commit:
  **0 khác biệt** (tol 1e-9) — mọi bảng A–E, sanity, verdict. 14 s.
- Outcome BRK (ret, pnl, pnl_noSL) tính lại độc lập cho 4 352 dòng (T3+T7): khớp 100% dòng, max |lệch| 1,2e-7 (float32).
- pSQ10 ALL khớp ngày, cover, n theo năm, max BRK/ngày (362), số ngày có BRK: khớp result.

## Mức độ phát hiện
| # | Phát hiện | Mức | Đổi verdict? |
|---|---|---|---|
| 1 | Câu chuyện "capitulation → hồi" + "NO-GO do điểm ước lượng âm" do 2 ngày sập (24,8% lệnh); theo ngày netproxy_7d +2,00% (G1–G3 qua) | TRUNG BÌNH | Không (G4/G5 FAIL mọi cách) |
| 2 | Đề xuất amend BRK∧bull = artifact 2 ngày ¬bull, post-hoc | TRUNG BÌNH | Không — rút đề xuất |
| 3 | Inflate ×1,18 lệch quy ước P0A (z_k/1,96) — đã chốt trước, hợp lý, nhất quán V3 | THẤP | Không |
| 4 | SL khớp +10,2% lạc quan: khớp close thực T7 −2,50% | THẤP | Không |
| 5 | Định nghĩa BRK, cooldown, causal, excess_short, funding, dữ liệu vào | — (đúng) | — |

## Đề xuất cho MASTER (không chạy)
- Sửa đoạn kết luận/G của RESULT_SHORT_V3_R3 theo mục 5 (a–d) và rút đề xuất BRK∧bull; giữ NO-GO.
- Các vòng sự kiện tiếp theo (R1/R2/…) có cụm ngày: pre-reg nên báo kèm thống kê theo-ngày (mỗi ngày trọng số 1) + "bỏ top-k
  ngày" làm sanity bắt buộc, và nêu rõ n hiệu dụng = số ngày.
