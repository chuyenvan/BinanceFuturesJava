# BOOK_HEDGE_BIGCOIN — hard-pick coin TO (SOL/BNB/XRP/DOGE/ADA/LINK), h ∈ {0,5; 1,0}

Ngày 2026-10-19. Trả lời câu hỏi của owner: *"nếu chọn cứng thì phải chọn coin thật to như BTC/ETH chứ ZIL
không đảm bảo ổn định"*. Chạy **cùng harness, cùng 8 seed, cùng luật GO**; dùng cache `dyn_minute.npz`.
**Đây là lần thử thứ 5 trong họ ⇒ THĂM DÒ** (6 arm mới, chọn sau khi đã thấy ZIL/DYN).

## Kết quả (base: CAGR22 37,95 · DD22 −22,55 · Calmar 1,69 · ΣPnL 110 047)
| Coin | ADV 2024 ($/ngày) | corr_ew | h | ≥5pp | ΔDD | ΔCalmar CI99 | PnL | GO |
|---|---|---|---|---|---|---|---|---|
| **LINK** | **219 M** | 0,762 | 0,5 | **8/8** | **+11,31** | **+0,968 [+0,75; +1,19]** | −27,4 % | **GO** |
| **ADA** | **208 M** | 0,795 | 0,5 | **8/8** | **+9,45** | **+0,724 [+0,57; +0,88]** | −28,4 % | **GO** |
| **DOGE** | **655 M** | 0,715 | 0,5 | **8/8** | **+9,40** | **+0,541 [+0,33; +0,76]** | −30,8 % | **GO** |
| **XRP** | **514 M** | 0,562 | 0,5 | **7/8** | **+8,12** | **+0,327 [+0,00; +0,66]** | −33,4 % | **GO** (sát biên) |
| BNB | 446 M | 0,686 | 0,5 | 6/8 | +4,99 | +0,225 [−0,07; +0,52] | −17,8 % | NO |
| SOL | **2 704 M** | 0,775 | 0,5 | 1/8 | +3,08 | −0,025 [−0,28; +0,23] | −37,0 % | NO |
| BTC | 16 239 M | 0,750 | 0,5 | 4/8 | +4,74 | +0,261 [+0,06; +0,47] | −9,2 % | NO |
| ETH | 7 492 M | 0,829 | 0,5 | 5/8 | +4,53 | +0,271 [+0,04; +0,50] | −11,3 % | NO |
| ZIL (tham chiếu) | 11,9 M | 0,908 | 0,5 | 8/8 | +10,93 | +1,209 [+0,78; +1,64] | −15,2 % | GO |

**h1,0: TOÀN BỘ NO-GO** — LINK 1/8 (−0,643), DOGE 0/8 (−1,117), ADA 0/8 (−0,884), XRP 0/8 (−0,887),
BNB 5/8 (−0,132), SOL 0/8 (−0,974), PnL −54…−74 %. ⇒ **chỉ dùng h0,5**.

## Đọc
1. **Owner đúng ở chỗ quan trọng**: hard-pick phải là coin lớn, thanh khoản cao. Và **đúng là có coin lớn làm được**:
   **LINK (219 M/ngày) và ADA (208 M/ngày) pass 8/8**, ΔCalmar +0,97 / +0,72, PnL −27/−28 %.
2. **Nhưng "to" KHÔNG phải tiêu chí quyết định**: **SOL to nhất trong nhóm alt (2,7 tỷ/ngày) lại FAIL nặng** (1/8, ΔCalmar −0,025);
   **BTC/ETH to nhất thị trường cũng FAIL** (4/8, 5/8, ΔCalmar +0,26). Lý do: book **97 % alt**, nên công cụ phải
   **bám nhân tố alt**, không phải "to".
3. **Thứ tự đúng theo (hiệu quả hedge × thanh khoản)**: **LINK ≈ ADA > DOGE > XRP ≫ BNB > SOL**;
   ZIL nhỉnh hơn về ΔCalmar (+1,21 vs +0,97) nhưng **ADV nhỏ hơn LINK 18×** ⇒ rủi ro thanh khoản/duy trì.
4. **Độ bền**: 4/6 coin lớn pass ở h0,5 với 7–8/8 seed ⇒ hiệu ứng **không phải đặc thù một coin**, mà là
   "short alt-beta ở đòn ~0,5". Đây là bằng chứng ủng hộ cách hiểu cơ học, không phải "tìm được coin thần".
5. **Cảnh báo kiểm định bội**: 6 arm mới sau khi đã thấy ZIL/DYN ⇒ kết quả **thăm dò**; muốn dùng thật phải
   pre-reg **1 lần** trên HO4 2026 với **một** coin đã chốt (đề xuất **LINK**, h0,5) — không chọn lại sau khi xem.

## Đề xuất (chờ owner/MASTER)
- Nếu đi tiếp: **LINK h0,5** làm công cụ hard-pick chính thức (thanh khoản 219 M/ngày ⇒ capacity tốt hơn ZIL ~18×,
  có thể tái dùng khung capacity đã làm, kỳ vọng trần quy mô cao hơn nhiều so với 0,3 M USD của ZIL).
- Hoặc **DYN h0,5** (7/8, ΔCalmar +1,268) nếu muốn tự thích ứng — nhưng phải đo capacity cho basket 5 leg.
- Không dùng h1,0 với bất kỳ công cụ nào đã thử.

## Nguồn
`~/claude_master/bookhedge_dyn/book_hedge_bigcoin.py`, `book_hedge_bigcoin.json`; cache `dyn_minute.npz`.
