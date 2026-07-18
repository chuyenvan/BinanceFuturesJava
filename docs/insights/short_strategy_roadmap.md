# SHORT STRATEGY ROADMAP — selector BÁN KHỐNG (short) riêng, không đối xứng long

> Chốt: chiến lược hiện **long-only**, edge **regime-gated** (BULL dương, CHOP breakeven, BEAR không tham gia).
> Roadmap này chỉ lo phần SHORT. Sequencing: **xác nhận EDGE trước, xây sim sau** (đừng xây khi chưa có số).
> Đo cuối cùng bằng **Java WFO** với `APPLY_FUNDING_FEE=true` (BẮT BUỘC cho short).

## 1. Vì sao thêm short
- **Lấp regime long chết:** long chỉ dương ở BULL, breakeven ở CHOP, im ở BEAR. Short kiếm tiền khi giá GIẢM
  → phủ đúng CHOP/BEAR mà long bỏ trống.
- **Tăng tần suất kèo:** thêm 1 hướng vào cùng universe alt → nhiều cơ hội/quý hơn, giảm phụ thuộc 1 regime.
- **Giả thuyết kiểm định (kernel `short-selector`):** `net_CHOP > net_BULL` (NGƯỢC long). Đúng ⇒ short bổ khuyết đúng chỗ.

## 2. KHÁC long ở đâu (đối xứng SAI = cháy tài khoản)
| Yếu tố | LONG | SHORT |
|---|---|---|
| Rủi ro đuôi | lỗ tối đa −100% (giá về 0) | **lỗ VÔ HẠN** (giá tăng không trần) |
| Hard-SL | tuỳ chọn | **BẮT BUỘC** hard-SL cứng X% (5/8/10 sweep, default 8) |
| DCA / martingale | có thể cân nhắc | **CẤM TUYỆT ĐỐI** (nhồi lệnh khi giá tăng = nuôi lỗ vô hạn) |
| Funding | thu funding khi funding dương (đa số bull) | **TRẢ funding khi funding dương** = chi phí thật, phải trừ |
| Regime tốt | BULL | CHOP / BEAR |

- **Mandatory hard-SL X%:** không có SL cứng = một cú pump thổi bay account. SL cắt bằng LỆNH thật, không "SL mềm".
- **CẤM DCA/martingale:** mọi cơ chế trung bình giá khi lỗ đều tắt cho short.
- **Funding BẬT:** short trả funding qua các kỳ 8h khi funding dương (đa số thời gian bull). Kernel dùng xấp xỉ
  `FUNDING_BPS_PER_TRADE=0.3%`; Java WFO dùng funding THẬT per-kỳ.

## 3. Short label (từ cột SẴN CÓ trong `funding_label.csv`, KHÔNG re-export)
Cột path-thô per-coin đã có: `maxFav_H, maxAdv_H, tHitFav_H, tHitAdv_H, retEnd_H, nBars_H` (tHit* = phút).
- `drop = -maxAdv_H*100` (độ sâu giảm, dương — short LỜI khi giảm).
- `rise =  maxFav_H*100` (độ tăng, bất lợi — chạm rise = hard-SL).
- `N_PCT=6`: short THẮNG khi giá giảm 6%.
- **HIT_short (path-aware):** chạm −N% TRƯỚC khi chạm +X_SL:
  `(maxAdv_H ≤ −N/100) AND (tHitAdv_H < tHitFav_H OR tHitFav_H ≤ 0)`, với `nBars_H` đủ.
  → KHÔNG phụ thuộc X_SL ⇒ classifier train MỘT lần, kế toán quét X_SL sau.

## 4. Exit riêng cho short (không mượn exit long)
- **Hard-SL cứng X%** (chân stop): giá tăng ≥ X% ⇒ cắt lỗ −X% ngay. Không đàm phán, không nới.
- **Chốt lời N%:** giá giảm N% ⇒ chốt +N.
- **Trailing riêng cho short:** *arm khi ĐÃ lời* (giá đã giảm đủ, vd ≥ 2–3%), sau đó **nuôi khi giá GIẢM tiếp**
  (trail theo đáy mới), siết dần khi giá hồi lên. Đối xứng-gương của trailing long nhưng THEO CHIỀU GIẢM.
- **Kế toán mỗi kèo (đã cài trong kernel):**
  - `rise≥X_SL và tHitFav<tHitAdv` → **−X_SL** (stopped, hard-SL);
  - elif HIT_short → **+N**;
  - else → **−retEnd_H*100** (short pnl = âm biến động; giá cuối giảm ⇒ dương);
  - `net = pnl_gross − 0.2%(phí) − FUNDING_BPS`.

## 5. Sequencing (GATE — không nhảy cóc)
1. **[ĐANG] Kernel `short-selector`** đo EDGE OOS: mỗi (horizon 4h/12h × P* 0.30–0.90 × X_SL 5/8/10) →
   `tpq, gross, net, net_bull, net_chop, hit_rate, auc`, tách regime BULL(<2025-01-01) vs CHOP(≥).
2. **Quyết định:**
   - `net_chop > 0` ở ≥1 (P*, X_SL) với `tpq` đủ (≥~30/quý) ⇒ **GO** xây short sim.
   - `net_chop ≤ 0` mọi cấu hình ⇒ **STOP**, short không có edge, không xây.
3. Nếu GO: xây short exit/sim (hard-SL + trailing chiều giảm) trong Java, đối chứng golden như long.
4. **KHÔNG** động WFO Oracle / prod cho tới khi short sim có số nội bộ sạch.

## 6. Đo cuối bằng Java WFO
- `APPLY_FUNDING_FEE=true` **BẮT BUỘC** (short trả funding — tắt = lãi ảo).
- Fee + slippage 2 chân LUÔN bật (CORE.md). Đi qua `BacktestIntegrityGuard.assertProductionGrade()`.
- Bump `CONFIG_VERSION` khi thêm nhánh short (đổi logic PnL ngoài genome) — tránh cache HPO trả điểm cũ.
- Funding trong kernel chỉ là XẤP XỈ (`FUNDING_BPS`); con số THẬT chốt ở WFO với funding per-kỳ 8h thực tế.
