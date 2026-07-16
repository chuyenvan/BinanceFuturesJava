# ROADMAP CHIẾN LƯỢC — Kiến trúc 3 phần (Entry / Success / Fail) + WFO

> **Bổ sung cho `REBUILD_ROADMAP.md`** (cái đó lo DATA + 2 MODEL). File này lo tầng còn thiếu:
> **CHIẾN LƯỢC VẬN HÀNH LỆNH** — cách một hệ thống trading tốt được phân rã thành 3 phần độc lập-
> nhưng-liên-kết, mỗi phần có bộ chỉ tiêu WFO riêng. Mục đích: vẽ đúng đường tổng thể để KHÔNG sa đà
> vào một góc nhỏ (bài học 2 ngày: tối ưu một-tham-số-cắt-ngang → vá bên này thủng bên kia).

## 0. Nguyên lý gốc (vì sao 3 phần)

Một lệnh có 2 số phận: **success** hoặc **fail**. Một luật chung áp cho cả hai luôn xung đột (đã đo:
SL cứng chữa đuôi lỗ nhưng cắt oan lệnh lãi; giveback cao nuôi lãi nhưng vô dụng với lệnh chết). →
Phân rã thành 3 bài toán con, mỗi cái một bộ chỉ tiêu riêng, WFO riêng:

```
        ┌─────────────┐   entry định đoạt tỉ lệ succ/fail + room cho DCA/SL
        │ 1. ENTRY    │──────────────┬──────────────┐
        │ (chọn+size) │              │              │
        └─────────────┘         success           fail
                                     │              │
                            ┌────────▼─────┐ ┌──────▼───────┐
                            │ 2. SUCCESS   │ │ 3. FAIL      │
                            │ (nuôi lãi)   │ │ (DCA/SL)     │
                            └────────┬─────┘ └──────┬───────┘
                                     └──────┬───────┘
                       mỗi action đóng lệnh → giải phóng/co vốn
                       → ĐỔI budget+ngưỡng cho tập entry CÒN LẠI  (vòng phản hồi động)
```

**Ràng buộc chống tối-ưu-cục-bộ:** bộ chỉ tiêu mỗi phần phải PHÁI SINH từ mục tiêu tổng
(20%/năm + ổn định + thanh khoản ≤1 năm), KHÔNG tự đặt rời — nếu không ba phần kéo ba hướng.

## 1. PHẦN 1 — ENTRY (bộ chọn + sizing ban đầu)

**Nhiệm vụ:** quyết định vào coin nào, size bao nhiêu — định đoạt cả tần suất cơ hội lẫn dư địa cho phần 3.

**Bộ chỉ tiêu (WFO):**
- **Tần suất cơ hội** = số quý có kèo (ràng buộc THEN CHỐT đã đo: hệ nằm im 60% thời gian → đây là
  đòn bẩy lớn nhất, không phải sizing).
- Tỉ lệ succ/fail của kèo ở horizon chuẩn.
- Entry-size ban đầu để lại đủ room cho DCA (liên kết Phần 3).

**Kỹ thuật (từ rẻ→mạnh):**
- (đang) `0.01|72h|pump` — label lỏng + horizon dài + feature pump → NHIỀU cơ hội hơn. **§1 đang chạy.**
- **Meta-labeling** (López de Prado): model-2 dự đoán P(success|tín hiệu) → dùng để (a) lọc kèo yếu,
  (b) quyết size động (kèo P cao → size lớn). Thay size cố định.
- Position sizing: vol-target / Kelly-fraction thay vì budget chia đều 50 phần.

**Cổng:** entry mới phải THẮNG entry hiện tại trên tần-suất-cơ-hội VÀ không làm tệ tỉ lệ succ.

## 2. PHẦN 2 — XỬ LÝ SUCCESS (nuôi lãi)

**Nhiệm vụ:** khi lệnh đi đúng, vắt tối đa mà không cắt non.

**Bộ chỉ tiêu (WFO):** % của đỉnh giữ được; PnL trung bình/lệnh thắng; không cắt-non-rate.

**Kỹ thuật:**
- (đang, tối ưu tạm) `TS_GIVEBACK_RATIO=1.0` — "càng giữ càng tốt", đơn điệu dương. Nền cố định mọi test.
- **Scale-out từng phần:** chốt 1/3 ở mốc lãi, nuôi 2/3 bằng trailing lỏng → giảm giveback risk mà vẫn ăn đuôi.
- **Pyramid (anti-martingale):** nhồi thêm vào lệnh ĐANG THẮNG (ngược DCA vào lệnh lỗ) — chuẩn trend-following.
- Cần re-WFO giveback trên horizon 72h (candidate mới) — có thể tối ưu khác 12h.

## 3. PHẦN 3 — XỬ LÝ FAIL (DCA / SL) — CHƯA TỪNG TỐI ƯU RIÊNG

**Nhiệm vụ:** khi lệnh đi sai, hoặc cứu (DCA) hoặc cắt (SL) sao cho tổng danh mục tối ưu + thanh khoản OK.

**Bộ chỉ tiêu (WFO):** max-holding (≤1 năm — thanh khoản); maxDD mỗi cụm; tỉ lệ-cứu (lỗ→hồi thành công);
vốn kẹt trung bình.

**Kỹ thuật (đây là mỏ chưa khai thác):**
- **Thang DCA theo tier + volatility:** Tier-1 bluechip gồng sâu; Tier-2/3 dừng DCA sớm hoặc SL (đúng ý
  tài liệu — coin rác sập vĩnh viễn LUNA/FTT). Spacing DCA theo ATR, không theo % cứng.
- **Stop theo thesis-invalidation:** thoát khi LÝ DO vào lệnh sai (vd pump-setup gãy cấu trúc), KHÔNG
  theo % cứng — vì % cứng đã đo là net âm (cắt ngang mọi loại).
- **Entry-size ↔ DCA room:** entry nhỏ → DCA sâu được (nuôi); entry lớn → SL sớm (không đủ room). Đây là
  liên kết Phần 1 ↔ Phần 3 — tối ưu CẶP, không rời.
- Time-stop mềm (đã đo: 270/360d không kích hoạt ở config hiện tại → thanh khoản tự thỏa; giữ như lưới an toàn).

## 4. Vòng phản hồi động (nâng cao — làm SAU khi 3 phần đứng riêng OK)

Mỗi lệnh đóng (succ hoặc fail) → đổi vốn khả dụng → đổi budget/ngưỡng cho tập entry còn lại. Hệ hiện đã có
mầm (BudgetManager theo vốn, circuit-breaker 50%) nhưng NGẦM + thô. Làm tường minh: bộ chỉ số Phần 1 nhận
tín hiệu từ trạng thái vốn realtime. **Chỉ nối vòng khi 3 phần đo được độc lập** — nếu không sẽ khớp lẫn
nhau, không cô lập được nhân-quả (bài học bug đo lường).

## 5. Thứ tự đi (chống sa đà — validate-small từng phần, WFO riêng)

**Nguyên tắc:** cố định 2 phần ở mức hiện tại, sweep 1 phần, WFO. Chỉ nối vòng khi cả 3 "đủ tốt" riêng.

| Bước | Phần | Việc | Điều kiện |
|---|---|---|---|
| A | 1 | §1 candidate `0.01\|72h\|pump` → Java confirm bậc thang | ĐANG CHẠY |
| B | 1 | Nếu A pass: meta-labeling + sizing động | sau A |
| C | 3 | Thang DCA tier/ATR + thesis-stop (mỏ chưa khai thác) | sau khi A xác nhận entry đủ cơ hội |
| D | 2 | Scale-out + pyramid + re-WFO giveback@72h | song song C được |
| E | 4 | Nối vòng phản hồi động | chỉ khi A-D đều có bộ chỉ số OK |

**ĐIỂM DỪNG (kế thừa `SOLUTION_FRAMEWORK`):** nếu Phần 1 (bước A/B) không phá được trần "thưa cơ hội"
→ Phần 2/3 chỉ vắt kiệt số ít → cần sleeve-2 THẬT (short/majors, §3 framework) hoặc kết luận trần ~5%/năm.
Phần 3 giỏi mấy cũng không tạo cơ hội mới — nó chỉ tối ưu cái Phần 1 đưa ra.

## 6. Ánh xạ sang khung SOLUTION_FRAMEWORK (không mâu thuẫn)

- 3-phần này là cách phân rã BÊN TRONG kiến trúc long-only hiện tại (nhánh §1/§4 của framework).
- Nếu đi hết 3 phần mà chưa đạt 20%/năm → framework §3 (sleeve 2 khác loại) hoặc §6 (dừng/chấp nhận).
- Hai tài liệu bổ sung nhau: framework = cây kiến-trúc (đi rộng); roadmap này = tối ưu SÂU trong 1 kiến trúc.

## 7. Nguyên tắc chống overfit (áp mọi phần)
Mỗi phần WFO riêng (không chỉ tổng); OOS đông lạnh không cho tuning chạm; deflated-Sharpe phạt số lần thử;
model/luật NHỎ thắng rule khiêm tốn hơn cấu hình to đẹp-trên-backtest; pre-register ngưỡng trước khi nhìn số.
