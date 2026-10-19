# TS_MKT_EXT — kết quả (2026-10-20)

Prereg: `docs/prereg/PREREG_TS_MKT_EXT.md` (commit `1e138619`), flags `ts_mkt_ext_flags.json` sha `c79ef302…` (214 ngày / 42 range).
Code: `feat/ts-mkt-ext` @ `a8690d46` (src_wt_bcd), jar sha256 `cc0f9d11…1b1dfe`. Driver `~/claude_master/tsx/tsx_driver.py`, raw `~/claude_master/tsx/ts_mkt_ext.json`.

Arm X14: loser time-stop 168h được gia hạn tối đa +336h (tổng ≤ 504h) CHỈ khi ngày hiện tại thuộc flag
(ALT_EW cuối ngày d−1 thấp hơn ≥30 % so với max 30 ngày trước). Ra khỏi ngày flag ⇒ cắt ngay như cũ.

## Validation
- P0 tsx-p0 (jar mới, không key TSX): md5 `ad26fd55…` = gqsf-a1, n=3541, eq=146078 ⇒ PASS (code path OFF không đổi).
- GPU check tsx-gpuchk-s7: md5 = gqsf-s7 ⇒ PASS.
- Parity 8/8 PASS (jar, ok, topk24, skipfull, key, `[TSX]` log, b0ov).
- MTM: `R._work is MT._work_vision` assert OK; `missing == 0` assert OK cho cả 8 seed. OFF tái dùng `iso/mtm_vision.json` (md5 khớp); AGG OFF = ISO_RISK OFF (37.0 / −22.5 / 110k / 742) ⇒ nhất quán.

## Kết quả (TB 8 seed)
| Arm | CAGR22 | DD22 | Calmar22 | UW22 (ngày) | ΣPnL | Legs/yr |
|---|---|---|---|---|---|---|
| OFF | 36.98 | −22.55 | 1.65 | 116 | 110.0k | 741.6 |
| X14 | 39.49 | −22.55 | 1.76 | 120 | 122.2k | 737.0 |

Per seed (OFF→X14):
| Seed | CAGR22 | DD22 | Calmar | UW | ΔPnL | defer clusters / cut sau defer |
|---|---|---|---|---|---|---|
| A1 | 36.90→39.28 | −22.21→−22.20 | 1.662→1.769 | 117→136 | +11.6k | 174 / 149 |
| S7 | 35.64→37.90 | −22.75→−22.74 | 1.566→1.666 | 116→108 | +10.8k | 172 / 153 |
| S13 | 37.67→40.24 | −22.92→−22.92 | 1.644→1.755 | 106→107 | +12.6k | 165 / 143 |
| S21 | 35.88→37.80 | −24.67→−24.66 | 1.454→1.533 | 136→136 | +9.4k | 173 / 155 |
| S99 | 38.36→41.16 | −21.41→−21.43 | 1.792→1.921 | 117→108 | +13.9k | 179 / 153 |
| S123 | 35.61→37.81 | −23.17→−23.18 | 1.537→1.631 | 117→107 | +10.4k | 174 / 153 |
| S777 | 39.34→42.89 | −20.05→−20.05 | 1.962→2.140 | 101→153 | +17.6k | 162 / 132 |
| S2024 | 36.48→38.84 | −23.19→−23.19 | 1.573→1.675 | 117→107 | +11.2k | 165 / 145 |

Lệnh giữ quá 168h (TB/seed): 197 leg, PnL −23.3k, 51 win (đây là PnL thực hiện của các leg gia hạn, không phải Δ so với cắt 168h).

## Rule (pre-reg)
- G1 ΔCAGR22 = +2.51pp, CI99 [1.89, 3.12] > 0 ⇒ PASS
- G2 ΔDD22 = −0.0005pp, worst seed −24.66 ⇒ PASS
- G3 ΔPnL/năm: 2022 +1.8k · 2023 +2.4k · 2024 +3.4k · 2025 +4.3k (4/4) ⇒ PASS
- G4 legs/yr −0.6 % ⇒ PASS
- **GO (theo prereg)**

## Rủi ro / giới hạn (đọc trước khi dùng)
1. **In-sample confirmation, không phải OOS.** Ngưỡng 30 %/30 ngày đến từ diagnostic TS_AFTER (T1 subset) trên CÙNG dữ liệu 2021–25. GO ở đây xác nhận rằng simulator tái hiện được hiệu ứng đã thấy, chưa chứng minh nó tồn tại ngoài mẫu.
2. **CI của G1 là CI theo seed** (seed = model noise, corr ngày 0.975) ⇒ hẹp giả tạo; không đo được bất định đường đi thị trường. Effect +12k/seed vẫn dưới DEV MDE ~16–19k.
3. Hiệu ứng tập trung vào vài đợt sập (2022 LUNA/FTX, 2024, 2025). 2023 chỉ có 4 ngày flag mà vẫn +2.4k ⇒ một phần Δ là path divergence (vốn/slot thay đổi), không thuần do giữ lệnh.
4. UW xấu đi rõ ở A1 (+19 ngày) và S777 (+52 ngày); TB +4 ngày.
5. Tail: giữ loser tới 21 ngày trong đợt sập kéo dài hơn mẫu (kiểu sập 2 nhịp > 3 tuần) chưa có trong DEV.
6. Live cần ALT_EW cuối ngày từ Vision (KHÔNG Binance REST từ Oracle); độ trễ publish của Vision phải được kiểm.
7. Owner 10-17: không sửa logic hệ cũ/shadow ⇒ GO chỉ là ứng viên cho v1.1.

## Bước tiếp đề xuất
Xác nhận OOS trên 2026 (chỉ chạy, KHÔNG tune; flag rule y nguyên) — cần owner đồng ý vì đụng dữ liệu 2026; kiểm số ngày flag 2026 trước (nếu ~0 thì 2026 không có sức thống kê).
