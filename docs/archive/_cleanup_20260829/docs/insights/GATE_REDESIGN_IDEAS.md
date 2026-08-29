# GATE_REDESIGN_IDEAS — ý tưởng thiết kế lại gate (GÁC LẠI, quay lại sau khi 039 xong)

> Trạng thái: **PARKED 2026-06-18.** Đây là ghi chú để không mất tư duy. KHÔNG làm bây giờ.
> Lý do gác: nền dữ liệu train (037/039) chưa xong — bàn kiến trúc lớn lúc này là đi ngang.
> Quay lại khi: model funding (039) đã train được trên data sạch.

---

## Bối cảnh — vì sao bàn lại gate

- Gate 12h (026b): đo sạch (non-overlap) → **không edge thật** (IC trùm 0, Newey-West t=0.49). Đã gác.
- Market model 15m: IC OOS = **0.52 THẬT, không leak** (bỏ momentum vẫn giữ 0.532).
  Nhưng IC cao chủ yếu do label = max-high (đỉnh look-forward) + market-level smoothing.
  Model chỉ hơn rule-base **×1.21** (giá trị AI khiêm tốn nhưng thật).
- FINDINGS chốt: **entry CÓ edge** (payoff>1 mọi năm) nhưng **DCA martingale + maxDD mật độ ăn sạch lãi**.
  `worstLoss −768.6 GIỐNG HỆT qua cả 4 mode filter` → filter (ML) KHÔNG đụng được đuôi.

---

## Nguyên tắc cốt lõi rút ra

> **Gate ML chỉ giỏi 1 việc: chọn thời điểm/coin vào lệnh tốt hơn (tăng PnL/win-rate).
> Nó KHÔNG chặn được đuôi. Đuôi phải chặn bằng RULE cứng, không phải model.**

---

## Kiến trúc đề xuất — gate 2 tầng

**Tầng 1 — GATE ENTRY (ML), chỉ áp cho LEG ĐẦU:**
- 15m timing (khi nào sắp nảy) × funding selector 039 (coin nào đáng vào).
- 15m là "chân ái" cho khung ngắn / đánh nhanh; 4h+ loãng vì trộn chế độ thị trường.
- Nhánh EARLY (15M ∧ funding bắt tay) hiện gánh 96.5% reject — lá chắn chất lượng entry thật.

**Tầng 2 — GATE DCA (RULE cứng), áp cho LEG DCA:**
- TẮT gate 15m ở leg DCA (hỏi "có nên vào" khi đang tụt là vô nghĩa — 15m luôn nói không).
- Quyết định nhồi/dừng = bài toán quản trị rủi ro: `BREAKER_CLUSTER_DD_MAX=−0.30`,
  giới hạn DCA depth, margin cap toàn danh mục (chặn nguồn maxDD mật độ ~325 cụm).

**Khoảng trống code hiện tại:** `AIRejectFilter` KHÔNG phân biệt leg đầu vs leg DCA — áp cùng logic
mọi lần gọi. Muốn làm tầng 2 phải thêm context "lệnh đang ở leg nào" vào filter.

---

## Quyết định lớn của user (2026-06-18)

> **Gate 15m chọn coin sắp nảy → vào → CHỐT LÃI/CẮT NHANH, KHÔNG DCA.**

Đây là **đổi hệ**, không phải tinh chỉnh. Hệ quả phải thành thật:
1. **Xóa nguồn rủi ro #1 + #2** (DCA khuếch đại −61/leg + maxDD mật độ) — giải đúng gốc.
2. **Mất lưới an toàn martingale** → mỗi entry phải tự đứng được → gate 15m + exit là tuyến
   phòng thủ DUY NHẤT ở entry. IC 0.52 và ×1.21 giờ trở nên cực kỳ quan trọng.
3. **Phí giao dịch thành đối thủ chính** (đánh nhanh = nhiều lệnh = phí 2 chân ăn mòn).
   realized 15M: p50=0.85%, %>1%=30.4% → biên mỏng, exit rule quyết định sống chết.
4. **Bài toán dịch** từ "quản trị DCA" sang "exit (TP/SL) + sizing". "No hard stop" cũ KHÔNG còn
   hợp lệ — phải có SL vì không còn DCA đỡ.
5. **Label phải đổi:** max-high (đỉnh) → forward-return THỰC chốt được, hoặc P(chạm +X% trước −Y%)
   = triple-barrier. IC sẽ thấp hơn 0.52 nhiều nhưng THẬT hơn (khớp túi tiền, không lạc quan đỉnh).

**Câu CHƯA chốt (hỏi khi quay lại):** hệ chốt-nhanh-không-DCA này **THAY THẾ** hệ DCA cũ,
hay **CHẠY SONG SONG** (2 kèo ngược pha trên cùng vốn)?
- Thay thế = thiết kế lại bot từ đầu (entry+sizing+exit+risk), đơn giản hơn, dễ kiểm soát đuôi. Sạch.
- Song song = 2 chiến lược ngược pha bù trừ rủi ro, nhưng phải chia vốn/margin + kế toán riêng. Phức tạp.

---

## Khi quay lại — thứ tự gợi ý

1. Chốt thay-thế vs song-song (định hình toàn bộ thiết kế).
2. Nếu giữ ý chốt-nhanh: thiết kế lại label (triple-barrier / forward-return thực) TRƯỚC khi train.
3. Đo bằng tiền (A/B trên golden — TASK-104 framework đã có mode E/F/OFF) chứ không chỉ IC.
4. Tách `AIRejectFilter` theo leg đầu vs DCA nếu vẫn giữ DCA ở đâu đó.

## Liên quan
- `docs/FINDINGS.md` (số gốc), `tasks/104-ab-test-gate-15m-golden.md` (A/B framework),
  `tasks/026b-train-gate-production-12h.md` (gate 12h đã gác), `docs/AUDIT_filter_ablation.md`.
