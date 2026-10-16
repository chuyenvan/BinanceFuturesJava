# RESULT FW tầng 1 — dòng tiền bắt buộc quanh mốc funding (MASTER 2026-10-17)

- **Pre-reg:** `docs/prereg/PREREG_FW.md` (5f500fc6).
- **Code:** `research/fw/fw.py`.
- **Output:** `~/claude_master/fw/` gồm `fw_result.json`, `fw.log` và `fw_events.parquet` (685k sự kiện, 575 coin).
- **Kiểm dữ liệu:**
  - V1: 100 % ts funding rơi đúng giờ chẵn.
  - V2: 99,89 % sự kiện có đủ giá.
  - V3: 10 sự kiện tính tay, sai số 0.

## VERDICT: **NO-GO** — cả 3 luật đều âm sau phí

Các con số dưới đây là trung bình **mỗi lệnh**. Phí taker + slippage là 0,14 % một vòng.

| Luật | Kỳ | n | Gross | Net | t (gom theo T) | DiD so với mốc T−2h | Theo năm (net) |
|---|---|---|---|---|---|---|---|
| L_post (funding dương: mua tại T, bán T+60m) | DEV | 21 927 | +0,042 % | −0,098 % | −1,1 | +0,061 % (t 1,95) | 22/23/24 đều âm |
| | VAL | 5 667 | +0,042 % | −0,098 % | −0,9 | −0,226 % (t −3,3) | |
| L_pre (funding âm: mua T−60m, bán T+1m, nhận funding) | DEV | 10 190 | **+0,124 %** | −0,016 % | −3,0 | +0,047 % (t 2,2) | +0,09 / +0,00 / −0,16 % |
| | VAL | 26 185 | +0,010 % | −0,130 % | −5,5 | +0,017 % | |
| L_cap (funding âm: bắt carry ±5m) | DEV | 10 190 | +0,028 % | −0,112 % | −9,7 | +0,015 % (t 2,7) | âm |
| | VAL | 26 185 | −0,008 % | −0,148 % | −12,4 | +0,035 % (t 3,5) | |

## Kết luận
1. **Cơ chế có thật nhưng rất nhỏ.** DiD dương với t ≈ 2–3: trước mốc thanh toán, coin có funding âm tăng thêm khoảng +0,02 % đến +0,05 % so với đối chứng. Gross thấp hơn phí taker 3–10 lần.
2. **Năm 2025 gross gần 0.** L_pre giảm từ +0,124 % ở DEV xuống +0,010 % ở VAL. Kể cả khớp maker (phí ≈ 0,04 %/vòng) cũng không cứu được VAL.
3. **Bắt carry funding âm (L_cap) không ăn được:** giá giảm quanh mốc đủ để triệt tiêu phần funding nhận được.
4. Theo quintile funding (mô tả, DEV), không quintile nào có pre/post khác 0 quá ±0,1 %.

**Đóng họ #1 (FW).** Ngân sách còn 2 họ. Ledger cộng 3.
