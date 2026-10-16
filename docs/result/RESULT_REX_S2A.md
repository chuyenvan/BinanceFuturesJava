# RESULT REX Bước 2a — regime cho long top-20 (P3) (MASTER 2026-10-17)

- **Pre-reg:** `docs/prereg/PREREG_REX_S2A.md` (008ec857).
- **Code:** `research/rex/rex_s2a.py`.
- **Output:** `~/claude_master/rex/s2a_result.json` và `s2a.log`.

## VERDICT: **NO-GO** — R5 (luật thắng) trượt cả 6 gate

Bảng dưới là số DEV 2022–2024. "Lãi 22 / 23 / 24" là tổng lợi suất ngày trong từng năm; "BTC cùng luật" là BTC giao dịch theo đúng luật regime đó.

| Luật | Sharpe | Lãi/năm | maxDD | Lãi 22 / 23 / 24 | % thời gian trong thị trường | Chi phí ×2 | BTC cùng luật: Sharpe / maxDD |
|---|---|---|---|---|---|---|---|
| R0 luôn trong thị trường | 0,19 | +14 % | −73 % | −0,91 / +0,82 / +0,47 | 100 % | 0,12 | 0,54 / −68 % |
| R1 BTC > MA50 | 0,37 | +18 % | −63 % | −0,41 / +0,97 / −0,00 | 52 % | 0,28 | 0,71 / −52 % |
| R2 breadth > 0,5 | 0,40 | +16 % | −40 % | −0,25 / +0,55 / +0,18 | 36 % | 0,31 | 0,51 / −36 % |
| R3 BTC mom28 > 0 | 0,36 | +18 % | −61 % | −0,39 / +0,95 / −0,01 | 54 % | 0,25 | **0,87** / −41 % |
| R4 R1 VÀ R2 | 0,37 | +15 % | −43 % | −0,29 / +0,53 / +0,20 | 35 % | 0,28 | 0,47 / −40 % |
| **R5** chỉ số alt > MA50 | **0,43** | +18 % | −43 % | −0,26 / +0,53 / +0,27 | 39 % | 0,35 | 0,72 / −39 % |

**VAL 2025, luật R5:**
- Danh mục: Sharpe −0,53, lãi −16 %/năm.
- BTC cùng luật: Sharpe −0,18.

## Kết luận
1. Long-only danh mục alt chọn bằng selector có Sharpe dưới 0,45 ở mọi luật regime.
   - Năm 2022 âm ở mọi luật: không luật nào tránh được cú sập alt.
   - **BTC áp cùng luật tốt hơn danh mục ở cả 6 luật.** Chọn alt không thêm giá trị so với cầm BTC.
2. Chính "BTC + regime" cũng yếu: Sharpe DEV 0,5–0,87, maxDD −36 % đến −68 %. VAL 2025 âm.
   - Không đủ điều kiện làm ứng viên riêng.
3. Bước 2b/3 (vào và thoát theo 1m) không còn nền là danh mục có edge, nên không làm tiếp theo nhánh này.

Ledger cộng 6.
