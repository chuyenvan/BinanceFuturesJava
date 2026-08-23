# Phân tích chiến lược: lướt vs nuôi, edge có thực không (2026-08-16)

Trả lời trực tiếp 6 câu hỏi trong project. Ghi rõ đâu là **đo được từ data**, đâu là **suy luận thiết kế**, đâu là **cần dump per-trade mới định lượng được**.

## 1. "Model là lướt vì label 6% là lướt phải không?" — Đúng một nửa

Phải **tách SELECTOR và EXIT**, chúng là 2 tầng khác nhau:

- **Selector** học label `maxFav_4h ≥ 0.06` (binary). Nó chỉ dự đoán "coin này có khả năng bật ≥6% trong **4h** tới không." Đây là tín hiệu **SELECTION ngắn hạn**, KHÔNG phải lệnh exit.
- "Lướt" thật sự nằm ở **EXIT config** (moveSL 0.05, TS params trong genome 17-gene). Việc bạn lướt hay nuôi do exit rules quyết, không phải label.

=> Câu "model là lướt" **đúng ở tầng selector objective** (bắt spike 4h/6%). Nhưng maxDD lớn **không phải do label** — do (a) exit không cắt phần thua đủ nhanh, và/hoặc (b) vào coin có left-tail sâu. Label chỉ định hướng "bắt pump", nó không ép bạn phải lướt.

## 2. Edge là gì, có thực không?

**Edge = SELECTION**: nâng P(coin bật ≥6% trong 4h) lên trên **base rate ~4.6%** (đo thật: kernel log 5m `base=0.0457`; 15m tương đương). Nếu selector không nâng được tỉ lệ này trên OOS → không có edge.

"Có thực" theo 3 lớp bằng chứng đã có:
- (a) **Audit giá** (doc 08-12): 15/15 lệnh khớp tuyệt đối close 1m Binance, entry = close nến gate-trigger, **no lookahead**.
- (b) **OOS expanding 2022-2026**, purge 72h leak-free, **16/18 window dương** (posRatio lenient 89%).
- (c) **2026 Q1 (+808) + Q2 (+878) dương độc lập** — regime mới nhất, xác nhận edge còn sống.

=> Edge selection là **thật**. NHƯNG:
- Con số sạch nhất để đóng đinh vẫn **chưa đo trực tiếp**: **OOS lift / AUC** = P(hit +6% | top selector score) / base rate. Nên đo trước go-live (join `predict_wf` với label OOS). **Đây là việc tôi đề xuất làm tiếp.**
- **Cảnh báo lệch PnL**: 2025Q4 (win15) = +5,888, chiếm **~31% tổng**. Edge selection thật, nhưng **độ lớn PnL phụ thuộc regime** — đừng nhầm "edge thật" với "PnL ổn định/lặp lại được." 2026 khiêm tốn hơn nhiều là baseline thực tế hơn.

## 3. "Chọn coin pump nhưng đánh lướt → đuôi lớn (maxDD) mà ăn ít"

Quan sát của bạn **được data ủng hộ**:
- MFE/MAE (`entry_paths.csv`, **caveat: cohort 2021, có survivorship/delist** — minh hoạ chứ chưa đại diện toàn WFO): `maeFinal` tới **−0.82 / −0.89** → coin được chọn có thể dump 80-90% nếu giữ; `mfe` bị chặn thấp hơn nhiều. Đây chính là "pump ngắn, dump dài" định lượng.
- Hệ quả: **giữ (nuôi) mà KHÔNG có SL = tự sát** vì left-tail cực sâu. "Ăn ít" vì lướt thoát sớm phần thắng; "maxDD lớn" vì phần thua không cắt đủ nhanh.

**Cần để định lượng đúng cho 2022-2026**: dump per-trade WFO thật (realized PnL, MFE/MAE intra-4h, duration). File hiện có không đủ. → Chạy backtest với cờ trade-dump.

## 4. "Lướt khi lỗ, nuôi khi lãi — SL/TP ra sao?"

Logic **đúng hướng** cho tài sản skew-phải hiếm + left-tail dày. Cụ thể hoá:

- **Tách 2 vai trò SL** (hiện đang lẫn): (i) **SL cắt lỗ ban đầu** — chặt, đặt theo vol/ATR coin chứ không % cố định (pump coin vol rất khác nhau); (ii) **moveSL bảo vệ lãi** (0.05 hiện tại) — chỉ kích hoạt khi đã có đệm lãi X%, rồi trailing.
- **Time-stop 4h**: edge chỉ "sống" trong horizon label (4h). Coin không bật trong 4h → xác suất dump tăng → **cắt theo thời gian quan trọng ngang cắt theo giá**.
- **"Nuôi"**: chỉ nuôi sau khi move SL lên breakeven+; trailing phải **đủ chặt** vì crypto dump dài sẽ trả lại hết lãi nếu nuôi lơi. Độ rộng trailing nên chọn từ **phân bố mfe intra** (cần dump).
- Không đặt **TP cứng nhỏ** (đó là nguyên nhân "ăn ít") — thay bằng trailing để bắt phần đuôi phải hiếm.

## 5. Nếu chuyển sang "SL chặn lỗ khi có lãi + nuôi lãi" thì selector & gate đổi ra sao?

Đây là điểm quan trọng nhất: **đổi exit không đủ, phải đổi cả objective.**

- **Selector**: label `maxFav_4h≥6%` chỉ tối ưu "có bật ≥6% hay không" — **không phân biệt** coin bật-rồi-đi-tiếp (nuôi được) với coin bật-rồi-dump-ngay (chỉ lướt mới ăn). Nếu nuôi, label phải đổi/bổ sung:
  - dự đoán **mfe/mae ratio** hoặc **follow-through** (còn tăng sau spike), hoặc
  - `maxFav` ở **horizon dài hơn** (12h/24h — 2 horizon này đã có sẵn slot trong code, hiện chỉ dùng idx0=4h), hoặc
  - **multi-label**: spike (4h) + sustained (24h).
- **Gate**: nếu nuôi, entry phải **sớm trong pump** (không đuổi đỉnh) + **lọc coin left-tail sâu** (thêm feature/rule loại high-dump-risk). Gate hiện tối ưu cho "bắt spike."
- Nếu **chỉ đổi exit mà giữ selector spike-4h** → sẽ **nuôi nhầm** nhiều coin spike-rồi-dump → ăn ngược. Đây là bẫy chính.

## 6. "Nên tách 2 chiến lược song song hay không?" — Nên

- Book A "**lướt spike 4h**": giữ nguyên selector+gate+exit hiện tại (đã có edge thật). Tối ưu: cắt lỗ nhanh hơn để giảm maxDD, giữ TP lướt.
- Book B "**nuôi trend**": label + gate MỚI (horizon dài, follow-through, lọc dump-risk), exit trailing.
- **Không ép 1 model làm cả hai** vì objective ngược nhau (spike-catch vs sustained-trend). Chạy song song, phân bổ vốn theo regime.

## Việc đề xuất tiếp (để biến suy luận thành số)
1. **Đo OOS lift/AUC của selector** (join predict_wf × label) — đóng đinh "edge có thực" bằng số. Ưu tiên 1.
2. **Dump per-trade WFO 2022-2026** (PnL, MFE/MAE intra-4h, duration) — để chọn SL/time-stop/trailing width chính xác, và đo "hiện đang ăn ít / eat tail" bao nhiêu.
3. Thử **horizon 12h/24h cho selector** (slot đã có) — kiểm giả thuyết nuôi.

## Trạng thái compute
5m grid (T1C2 fix) đang train GPU (check 14:02 UTC). Chưa đụng 1m.
