# TASK-006: Chạy circuit breaker 4 mode trên FULL — DCA có phải thủ phạm ruin không

- **status:** done — 4 mode chạy xong (FULL, commit sạch f1f32a3). KL: MARGIN giảm DD −58%→−43% (đổi ~10% PnL) đáng áp; DCA cap gần vô dụng (nhưng KHÔNG kết được vì thiếu coin chết). Bảng + phân tích ở Kết quả.
- **Milestone:** ROADMAP bước 3 (ruin). Vấn đề TRỌNG TÂM (FINDINGS §1/§5: entry có edge nhưng DCA-không-giới-hạn phá hết qua chu kỳ).
- **Thực thi bởi:** Claude Code (**Java**). Tool ĐÃ CÓ: `ai_ml/validation/ablation/market/RunBreakerBacktest.java`. Chạy FULL 2021→2026 (đọc cluster 242). ~4× thời lượng FULL.
- **Quyết định nền:** ADR-0006 (golden/đo) · FINDINGS §5 (3 nguồn đuôi) · §8 (câu hỏi breaker).

## Mục tiêu (1 câu)
Chạy 4 mode OFF/MARGIN/DCA/BOTH → trả lời: breaker có **lật PnL 5 năm âm→dương** + giảm maxDD không, và **MARGIN hay DCA** gánh chính.

## Cơ chế breaker (đã code)
- `BREAKER_MARGIN_HALT` (FINDINGS: 0.70) — chặn MỞ MỚI khi margin/vốn ≥ ngưỡng (nguồn 1: mật độ 325 cụm).
- `BREAKER_CLUSTER_DD_MAX` (FINDINGS: −0.30) — ngừng NHỒI cụm khi tụt ≥ ngưỡng (nguồn 2: DCA khuếch đại).
- KHÔNG force-close (giữ long-only). Phanh chỉ DỪNG MỞ / DỪNG NHỒI.

## Luồng (tuần tự, tự cập nhật trạng thái; fail thì retry đúng bước)
- [ ] **B1 — Dọn + sync:** dọn job java cũ của mình (CLAUDE.md), `git pull`.
- [ ] **B2 — Commit sạch:** `git add -A && commit` (docs/tasks đang uncommitted). `git status` sạch.
- [ ] **B3 — Chạy `RunBreakerBacktest`** (4 mode, 1 lần). Pre-flight PHẢI pass (lookahead_block + slippage_apply + fee>0); nếu tool tự DỪNG vì cấu hình ảo → sửa rồi chạy lại. Dọn job trước khi chạy.
- [ ] **B4 — Ghi bảng vào (Code điền):** mỗi mode: totalPnl, PnL/năm (2021–2026), maxDD cũ + THẬT (+ /năm), halt count, dcaCap count, maxMarginRatio. + xác nhận **gate liêm chính**: totalPnl mode OFF khớp lần chạy nền trước (field đo mới không được đổi PnL).

## Câu hỏi quyết định (đọc bảng)
1. **OFF ra âm hay dương?** ⚠️ Data đang THIẾU coin chết (backfill hoãn, ADR-0007) + funding fee TẮT → PnL tuyệt đối **lạc quan**. Nếu OFF đã dương, rất có thể do survivorship, KHÔNG phải hệ tốt. Chỉ đọc **tương đối giữa các mode**.
2. **MARGIN/DCA/BOTH có lật PnL hay chỉ giảm maxDD?** MARGIN vs DCA — cơ chế nào gánh chính?
3. Kết luận theo FINDINGS §8:
   - Lật âm→dương → **DCA-không-giới-hạn đúng là thủ phạm, breaker sửa được** (bước ngoặt).
   - Giảm maxDD mà PnL ~giữ → đáng áp (an toàn hơn).
   - Giảm maxDD mà PnL xấu đi → **vấn đề sâu hơn DCA**, phải xem lại chiến lược (không cứu bằng phanh).

## Acceptance criteria
- [ ] 4 mode chạy cùng commit sạch (dirty=false), cùng data/tham số, chỉ khác `BREAKER_MODE`.
- [ ] Bảng đầy đủ PnL/năm + maxDD (cũ+thật) + counts; gate liêm chính OFF khớp.
- [ ] Kết luận rõ vào 1 trong 3 nhánh câu hỏi 3, có ghi lưu ý survivorship/funding-fee.
- [ ] Java, SLF4J, KHÔNG System.out.

---
## (Code điền) Kết quả

Chạy `RunBreakerBacktest` (FULL 20210101→20260601, 4 mode, 1 JVM, jar `71de547`, commit sạch `f1f32a3`, qua `BacktestIntegrityGuard`). Pre-flight PASS (lookahead+slippage+fee=0.002). Ngưỡng: MARGIN_HALT=0.70, CLUSTER_DD_MAX=−0.30.

| Mode | totalPnl | maxDD cũ | maxDD THẬT | balEnd | halt | dcaCap | maxMargR |
|---|--:|--:|--:|--:|--:|--:|--:|
| **OFF** | **68513** | −20406 (−58.3%) | −20406 | 103513 | 0 | 0 | 0.99 |
| **MARGIN** | 61529 | −14986 (−42.8%) | −14986 | 96529 | 710432 | 0 | 0.71 |
| **DCA** | 68355 | −19677 (−56.2%) | −19677 | 103355 | 0 | 13179 | 0.99 |
| **BOTH** | 58255 | −14790 (−42.3%) | −14790 | 93255 | 711299 | 8109 | 0.71 |

PnL/năm:
| Mode | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|--:|--:|--:|--:|--:|--:|
| OFF | 21517 | 7085 | 9678 | 17948 | 11816 | 469 |
| MARGIN | 19981 | 6842 | 9284 | 13785 | 12294 | −656 |
| DCA | 20595 | 6911 | 9512 | 17847 | 12532 | 959 |
| BOTH | 19695 | 6492 | 8853 | 13115 | 11972 | −1871 |

maxDD THẬT/năm (đáy sâu nhất = **2025**): OFF 2025=−20406; MARGIN 2025=−14986. (maxDD_cũ ≈ THẬT trong run này — gần như trùng mọi mode.)

### Trả lời 3 câu hỏi
1. **OFF dương mạnh** (+68513, MỌI năm dương kể cả bear 2022 + sập 2025). ⚠️ KHÔNG phải hệ tốt: data thiếu coin chết + funding fee tắt ⇒ lạc quan (khớp baseline CRASH 003.1: 2022 lãi giả). Chỉ đọc TƯƠNG ĐỐI giữa mode.
2. **MARGIN gánh chính; DCA gần như vô dụng.**
   - MARGIN: maxDD −58%→**−43%** (giảm ~15pp thật), PnL −10% (68.5k→61.5k), margin trần đúng 0.71. halt nổ 710k lần.
   - DCA cap: dcaCap nổ 13179 lần nhưng **PnL ~y nguyên (68.4k) và maxDD ~y nguyên (−56% vs −58%)** → gần như KHÔNG tác dụng.
   - BOTH ≈ MARGIN (DD −42%) PnL thấp hơn chút (58.3k) → DD do MARGIN quyết, DCA cap thêm chỉ bào PnL.
3. **Nhánh kết luận: "giảm maxDD mà PnL ~giữ (giảm nhẹ)" → MARGIN ĐÁNG ÁP** (an toàn hơn rõ: −58%→−43% DD, đổi ~10% PnL). KHÔNG phải nhánh "lật âm→dương" (OFF đã dương).

## (Code điền) Phát hiện ngoài scope

- 🚩 **Không thể kết luận "DCA không phải thủ phạm ruin"** từ run này: DCA-không-giới-hạn gây ruin nặng nhất ở coin **về 0** (LUNA/FTT) — mà chúng KHÔNG có trong data (survivorship, backfill hoãn). DCA cap nhìn vô dụng ở đây CHÍNH VÌ thiếu kịch bản kích hoạt nó. Giả thuyết DCA-ruin vẫn **CHƯA được kiểm** một cách công bằng — chỉ kết được sau backfill [B] (ADR-0007).
- **Gate liêm chính chưa verify được tuyệt đối:** không có số FULL-OFF run-trước để so totalPnl (chỉ có baseline FAST khác range). maxDD_cũ ≈ THẬT mọi mode (trùng) — field đo mới nhất quán, nhưng cần 1 lần FULL-OFF mốc để khoá gate về sau.

## (Code điền) Quyết định phát sinh

- MARGIN halt (≥0.70 vốn) đáng cân nhắc áp như guardrail (giảm DD ~15pp, đổi ~10% PnL) — NHƯNG đọc trong bối cảnh survivorship/funding-fee-tắt làm PnL lạc quan; quyết định áp/không nên chờ đánh giá lại sau backfill. DCA cap (−0.30/cụm) hiện chưa cho thấy giá trị — chưa nên áp.
