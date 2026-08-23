# Phân tích số liệu coin-sập + luật exit KHÔNG dùng SL-giá — 2026-08-21

Chạy trên Oracle (`/tmp/cs.py`) join 3 file thật: entry_paths.csv (2975 lệnh THẬT trade 2021-04→2025-12, kèm outcome 180d + recoverDay + delisted) × entry_pathstats_g008 (path 4h→72h) × entry_universe (age niêm yết). Mục tiêu: tìm chiến lược xử lý đuôi sập-đơn-coin **bằng số liệu**, với ràng buộc user: **KHÔNG dùng hard-SL giá** (đã fail thực tế, MM quét SL).

> Caveat: retEnd là raw (chưa fee/funding); "collapse" định nghĩa (recoverDay==0 & maeFinal<−50%) | delisted → hơi rộng (recoverDay semantics chưa chắc). Các kết luận chính dựa trên maeFinal/retEnd (không phụ thuộc cờ collapse) nên vẫn vững.

## KẾT QUẢ CHÍNH (4 phát hiện, có cái đảo kết luận cũ)

### PH1 — Đuôi KHÔNG tách được sớm. Coin pump +15%, đã "arm", vẫn sập.
Luật "đã chạm +15% favorable trong T giờ" KHÔNG phân biệt winner vs rot:
| T | %armed | ARMED: maeFinal / collapse | NOTarmed: maeFinal / collapse |
|---|---|---|---|
| 4h | 12% | −0.585 / 0.43 | −0.566 / 0.28 |
| 24h | 37% | −0.538 / 0.30 | −0.582 / 0.30 |
| 72h | 55% | −0.545 / 0.28 | −0.586 / 0.31 |

**maeFinal của ARMED ≈ NOTarmed (≈ −0.55).** Coin pump rồi arm vẫn sập tới −55% median. VD LUNA 20211204: retEnd72 **+28%** (winner ở 72h) → maeFinal **−100%** (chết tháng sau, Terra). ⇒ **Không có tín hiệu excursion sớm nào cắt được đuôi.** Đây là kết quả âm quan trọng nhất.

### PH2 — Luật "cắt khi đang lỗ sớm" (give-up 12h/24h) là NET-LOSER (xác nhận user #2 rộng hơn cả hard-SL)
Overlay: exit nếu chưa arm & đang lỗ tại T (đây là exit theo TIME+STATE, KHÔNG phải SL-giá, MM không quét được):
| Policy | sum PnL | mean | p01 | min |
|---|---|---|---|---|
| HOLD tới 72h | 205.3 | +6.95% | −43% | −89.8% |
| give-up @12h | 168.0 (**−18%**) | +5.68% | −38.8% | −67% |
| give-up @24h | 184.4 (**−10%**) | +6.24% | −38.6% | −67% |

Cắt sớm khi lỗ **mất tổng nhiều hơn cứu được đuôi** (đuôi chỉ cải thiện chút), false-cut 11–14% winner. Lý do: 66.7% dip-trước-pump → cắt lúc lỗ = cắt ngay trước pump. **Không chỉ hard-SL giá fail — MỌI luật cắt-sớm-khi-lỗ ở 12–24h đều fail.**

### PH3 — Đuôi thảm hoạ nằm ở GIỮ DÀI, không ở 72h đầu → đòn bẩy là MAX-HOLD time-stop
- retEnd_72h: min **−67%**. maeFinal (180d): min **−100%**. Chênh lệch −67% vs −100% = phần đuôi tích luỹ SAU 72h (ride coin chết hàng tuần/tháng — đúng cơ chế capital-lock).
- NOT-armed-by-72h: median retEnd_72h **−3.7%**, nhưng nhóm này ride tới maeFinal **−58.6%**. ⇒ Chốt nhóm này quanh mốc vài ngày = khoá −vài% thay vì −59%.
- Khác PH2: cắt ở 12–24h (quá sớm, giết dip-winner) SAI; nhưng **max-hold ở 72h–168h** (sau khi pump median 12h đã xong) chốt đúng nhóm chết mà không đụng winner. **Time-stop DÀI (3–7 ngày), không phải cắt-lỗ-sớm.**
- Khớp WFO exit_sweep độc lập: giữ lỏng/dài (RATE_PROFIT 0.10, hold 4.3d) = −4587 thảm hoạ. Cả 2 nguồn hội tụ: giữ vô hạn = chết.

### PH4 — Coin mới niêm yết rủi ro cao hơn → SIZE-DOWN, không loại bỏ
| Age tại entry | n | collapse | retEnd72 mean |
|---|---|---|---|
| <7d | 438 | 0.40 | +6.0% |
| 7–30d | 337 | 0.38 | +6.2% |
| 30–90d | 793 | 0.24 | +7.8% |
| >90d | 1407 | 0.28 | +7.0% |

Coin <30d: collapse cao hơn rõ (0.38–0.40 vs 0.24) NHƯNG mean vẫn dương (+6%). ⇒ **Loại hẳn = bỏ ~26% lệnh còn có lãi.** Đúng hơn là **giảm size theo tuổi** (risk-adjusted tốt hơn: cùng $ nhưng đóng góp đuôi ít hơn).

## VỀ "DCA" — số liệu KHÔNG ủng hộ DCA-down
- Coin sập giảm đơn điệu tới −55%..−100% (LUNA/ACE/UNFI/meme, xem chi tiết §5 script). Nhồi thêm khi lỗ = tăng exposure đúng lúc 30% số đó đang chết. Vì đuôi KHÔNG tách sớm được (PH1), DCA-down **khuếch đại** đuôi.
- Xác nhận user #1: re-entry live KHÔNG phải DCA-up một vị thế — đó là các lệnh ĐỘC LẬP trên cùng symbol ở các thời điểm cách nhau tuần/tháng (dedup khi đang giữ). VD UNFI vào 22 lần rải 2021→2024.
- **Rủi ro over-entry THẬT = 4 leg CÙNG TICK trên 1 coin** (ACE/SXP/FLM có 4 dòng trùng entry cùng ngày = NUMBER_ENTRY/topK) → 4× exposure vào 1 coin sập. Đây mới là chỗ cần cap.

## KHUYẾN NGHỊ #3 (bám số liệu, tôn trọng "no hard-SL")
1. **Disaster-exit = MAX-HOLD time-stop (KHÔNG phải SL giá).** Force-close sau N ngày bất kể lỗ/lãi. MM không quét được (không có lệnh stop treo). A/B `TIME_STOP_HOURS ∈ {72,120,168}` trong WFO. Path-data ủng hộ đầu DÀI (72h+), KHÔNG phải 12–24h. Đây cũng chính là fix capital-lock.
2. **Cap 1 leg / coin / tick** — giết cú 4× cùng tick vào 1 coin (over-concentration thật).
3. **Size theo tuổi niêm yết** — coin <30d giảm size (vd ×0.5), không loại.
4. **KHÔNG thêm DCA-down.** Nếu muốn "DCA" thì chỉ ở tầng portfolio (rải vốn nhiều coin/thời điểm), không nhồi 1 vị thế.
5. Hard-SL giá: note lại, chỉ dùng khi hết cách khác (theo user) — và số liệu cũng cho thấy nó kém time-stop.

## Việc còn thiếu để đóng đinh (cần WFO sim, không làm từ path-data được)
- retEnd tại horizon >72h không có trong file → không đo trực tiếp được total của max-hold {5,7}d. Phải A/B `TIME_STOP_HOURS` trong WFO sim thật (có fee/funding) — đo total + maxdd, đánh giá bằng deflated-t/1SE/worst-window + confirm 2026 holdout. Điều kiện: fix capital-lock trước (đã bàn).
- File: `/tmp/cs.py` (Oracle), nguồn `/home/ubuntu/claudedata/entry_{paths,pathstats_g008,universe_g008}.csv`.
