# RESULT MK — sleeve maker BTC với khớp maker bảo thủ (họ #2) (MASTER 2026-10-17)

- **Pre-reg:** `docs/prereg/PREREG_MK.md` (dadb4cd5).
- **Code:** `research/mk/mk.py`.
- **Output:** `~/claude_master/mk/`.

## VERDICT: **NO-GO** cả hai sleeve
| Sleeve | Taker | Maker luôn khớp | **Maker bảo thủ** | Tỷ lệ khớp | Lãi theo năm (bảo thủ) 21/22/23/24/25/26 |
|---|---|---|---|---|---|
| S1M (21–23 UTC) | Sh −1,84 | +0,42 | **−0,09**, maxDD −35 % | 95,7 % | +23 / −31 / −3 / +16 / +1 / −14 % |
| S7M (cuối tuần) | +0,26 | +0,44 | **+0,38**, maxDD −43 % | 98,3 % | +36 / −41 / +29 / +19 / +2 / +17 % |

**Bài học về adverse selection (S1):**
- Các phiên KHÔNG khớp được có lợi suất thô trung bình +0,30 %; các phiên khớp được chỉ +0,05 %.
- Lý do: limit mua chỉ khớp khi giá đi xuống, nên phiên giá chạy lên ngay sẽ bị lỡ.
- Hệ quả: con số "maker luôn khớp" của SCREEN_WIDE lạc quan. Khớp thực tế làm mất gần hết edge.

**S7:** phần lớn chỉ là beta cuối tuần của BTC.
- Năm 2022 −41 %, maxDD −43 %. Trượt G1 (Sharpe 0,38 < 0,5) và G4 (maxDD).

Đóng họ #2. Ledger cộng 2.
