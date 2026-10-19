# BOOK_HEDGE_ALT_CAPACITY — kiểm capacity/impact của hedge ZIL (bổ sung, KHÔNG đổi outcome)

Ngày 2026-10-19. Chạy sau `BOOK_HEDGE_ALT` (kết quả `59fd8ef9`), **cùng dữ liệu, cùng luật GO**;
chỉ **thêm chi phí impact = bps × turnover** để xem kết luận có bền không. Đây là kiểm robustness, **không** phải thử nghiệm mới.

## Turnover thực của hedge (đo từ `N(m)`, 8 seed, book chuẩn 100k)
| h | tổng turnover (1 605 ngày) | /ngày (mean) | p99 ngày | max ngày | lệnh lớn nhất 1 phút | số phút có lệnh |
|---|---|---|---|---|---|---|
| 0,5 | 2,83–3,16 M USD | 1 854 | 31 757 | 102 890 | 23 535 | 3 366–3 473 |
| 1,0 | 5,95 M USD | 3 707 | 63 514 | 205 780 | 47 069 | 3 366–3 473 |

## Mức tham gia so với thanh khoản ZIL (ADV 11,9 M USD/ngày, median 2024)
| h | /ngày trung bình | ngày xấu nhất |
|---|---|---|
| 0,5 | **0,015 %** ADV | **0,854 %** ADV |
| 1,0 | **0,031 %** ADV | **1,708 %** ADV |

## Độ bền của luật GO khi thêm impact (bps trên turnover)
| h | 0 bps | 5 | 10 | 25 | 50 | 100 |
|---|---|---|---|---|---|---|
| **0,5** ΔCalmar / dPnL | +1,209 / −15,2 % | +1,160 / −16,6 % | +1,112 / −17,9 % | +0,967 / −21,9 % | +0,726 / −28,6 % | +0,272 / −42,0 % |
| **0,5** GO | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **1,0** ΔCalmar / dPnL | +1,538 / −30,4 % | +1,373 / −33,1 % | +1,211 / −35,8 % | +0,725 / −43,8 % | −0,018 / −57,2 % | −1,359 / −84,0 % |
| **1,0** GO | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |

## Kết luận
- **Daily capacity rất thoải mái**: trung bình chỉ 0,015–0,031 % ADV; ngày xấu nhất 0,85–1,7 % ADV.
- **Điểm nghẽn là lệnh trong 1 phút**: lệnh lớn nhất **47 069 USD** (h1,0) ≈ **5,7× volume phút trung bình** (11,9 M/1 440 ≈ 8,3 k/phút)
  ⇒ **bắt buộc slice** qua nhiều phút; nếu không, trượt giá đúng vào lúc cần hedge nhất.
- **Ngưỡng sống của GO**: h1,0 bền tới **25 bps** (chết ở 50 bps); h0,5 bền tới **100 bps**.
- **Ước lượng trần quy mô** (giữ ngày xấu nhất ≤ 5 % ADV): book ≈ **0,3 M USD** với h1,0. Vượt mức đó, chi phí impact
  bắt đầu ăn vào ΔCalmar ⇒ phải đo lại trên volume thực của quy mô đó.
- Không đổi bất kỳ số nào của `BOOK_HEDGE_ALT`; kết luận **GO (thăm dò)** giữ nguyên.
