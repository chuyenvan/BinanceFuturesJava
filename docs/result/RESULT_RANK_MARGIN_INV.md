# RESULT — RANK-MARGIN-INV (thêm margin cho rank thấp)

- Pre-reg: `docs/prereg/PREREG_RANK_MARGIN_INV.md` · commit `7ba6a39e` · branch `feat/rank-margin`
- Jar: `sim-jar-rm2` · sha256 `9fc7171395b5e1037217c09cb84fa8e27d341e5cea82b06c5828545ff26a3caa`
- Raw: `docs/result/rank_margin_inv.json`
- Baseline: `gqsf-a1` (α không đặt) · window 2022–2025 · equity_start 35000

## Giả thuyết (owner)

> "Rank cao rủi ro cao → cắt rank thấp; rank thấp rủi ro ít → **thêm** margin mới đúng. Thêm margin cho rank thấp có nâng Calmar không?"

Cơ chế kiểm: `SIM_RANK_MARGIN_ALPHA < 0` ⇒ đảo dấu, **cộng** margin cho rank thấp (thay vì cắt rank cuối như α>0).

## Parity (bắt buộc trước khi tin số)

| Kiểm | Kết quả |
|---|---|
| P0 vs baseline | **PASS** — md5 `ad26fd55f0bb5db32038ec8b357cf8e7`, n=3541, eq=146078 |
| rm-inv-300 / 500 / 700 | **PASS** cả 3 (jar, mapper, topk24, skipfull, alpha, b0ov, pred = true) |

## Kết quả (baseline → arm)

| α | tag | CAGR22 | maxDD22 | **Calmar22** | UW22 | n/yr | ΣPnL 22-25 |
|---|---|---|---|---|---|---|---|
| 0 (base) | gqsf-a1 | 36.90 | -22.21 | **1.662** | 117.3 | 736.0 | 104461 |
| +0.3 | rm-inv-300 | 38.10 (+1.20) | -23.50 (-1.29) | **1.622 (-0.040)** | 117.5 | 736.5 | 110635 (+6174) |
| +0.5 | rm-inv-500 | 39.21 (+2.30) | -24.00 (-1.79) | **1.634 (-0.028)** | 117.5 | 738.3 | 116241 (+11780) |
| +0.7 | rm-inv-700 | 40.02 (+3.12) | -24.68 (-2.47) | **1.622 (-0.040)** | 117.0 | 740.0 | 120482 (+16021) |

## Kết luận

**Không. Thêm margin cho rank thấp KHÔNG nâng Calmar — nó hạ nhẹ ở mọi mức α.**

- **ΣPnL và CAGR tăng đơn điệu** theo |α| (ΣPnL +6.2k → +12k → +16k; CAGR22 +1.2 → +2.3 → +3.1), nhưng **maxDD22 cũng nới rộng** (-1.29 → -1.79 → -2.47).
- DD nới nhanh hơn mức bù của return ⇒ **Calmar22 giảm** ở cả 3 mức: 1.622 / 1.634 / 1.622 vs baseline 1.662 (≈ -1.7% đến -2.4%). Không đơn điệu — α=0.5 ít tệ nhất.
- UW22 gần như không đổi (117.0–117.5); n/yr tăng nhẹ (thêm lệnh, không thêm chất lượng).

**Đọc đúng:** cơ chế "thêm margin rank thấp" chỉ là **đòn bẩy vào phần đuôi dài** — khuếch đại cả lãi lẫn lỗ, không phải cải thiện risk-adjusted. Muốn tăng Calmar thì phải **cắt/cải thiện** phía đuôi rủi ro, không phải bơm thêm vốn vào đó.

## Trạng thái

- α>0 (cắt rank cuối, pre-reg cũ) — đã có kết quả riêng.
- α<0 (đảo dấu, thêm rank thấp) — **kết quả này: không thắng baseline Calmar.** Không đề xuất promote.
