# PREREG_CROWDED_LONG — crowded-long bằng **QUANTILE TRƯỢT** như luật **RỦI RO/SIZE**

Ngày chốt: 2026-09-24. **Chốt TRƯỚC khi đo** (mọi số ở `RESULT_CROWDED_LONG.md`).
Ràng buộc: **thuần Python offline** · **KHÔNG** Java/sim · **KHÔNG** `claude-run`/Claude Code ·
**KHÔNG push** · **DEV only** (ma trận dừng ở `2025-12-31 23:00`, không đọc 2026). Trung gian `/tmp/crowded/`.

---

## 0. Vì sao vòng này tồn tại (khác vòng trước)

Vòng `RESULT_LS_TAKER` (commit `19b4c02`) để lại **đúng một** hint chưa bị phủ định: **regime crowded-long
cấp THỊ TRƯỜNG** — tercile `median(log ls_global)` cao ⇒ EW 24h `−0,6044%` vs ter0 `−0,0556%`
(Δ `−0,5487%`), CI72h_x1.21 `[−1,2278, +0,1303]` **chứa 0**, **chỉ 1 quý OOS** ⇒ **UNCONFIRMED**.
⚠ Vòng đó chia tercile **THEO THỜI GIAN** (khối thời gian liền mạch) ⇒ **lẫn "thời kỳ" với "regime"**,
nên không phân biệt được "crowded-long là trạng thái" với "2025 là một năm xấu".

**Vòng này thay định nghĩa bằng QUANTILE TRƯỢT (causal)** và **đổi câu hỏi**:

> **KHÔNG phải alpha.** Câu hỏi là **RỦI RO/SIZE**: *"khi thị trường crowded-long thì giảm
> size/exposure"* có **giảm ĐUÔI** (intraday maxDD / worst-window drop của sách) với **chi phí chấp
> nhận được** không? Tức **luật rủi ro có điều kiện**, không phải tín hiệu vào lệnh, không phải lọc coin.

Đối chứng nội bộ: `RESULT_TAIL_LEVER` đã chứng minh **trần tỉnh (unconditional cap) KHÔNG đáng**
⇒ vòng này chỉ có cửa nếu luật **có điều kiện** thắng được **chi phí bỏ lỡ lợi nhuận**.

---

## 1. Tín hiệu — crowded-long BẰNG QUANTILE TRƯỢT

- `ls_global` = cột thứ 3 (0-based: cột 2) của `oi_percoin_full.bin`, đã xác định schema ở vòng trước:
  **ratio long/short**, `p50 ≈ 2` ⇒ dùng `log()`.
- **Tín hiệu thị trường** tại mốc giờ `t`:
  `x_t = median_{u ∈ U_t} log(ls_global_{u,t})` với `U_t = {u : ls_global_{u,t} > 0, close_{u,t} > 0}`;
  yêu cầu `|U_t| ≥ MIN_SYM = 50` (nếu không ⇒ `NaN`, không tính).
- **Ngưỡng trượt, CAUSAL** (không dùng dữ liệu tương lai, **và không dùng chính `t`**):
  `thr_t(N) = quantile_{0.80}( x_s : s ∈ [t − N·24, t − 1] )`
  — chỉ trên các mốc giờ có `x_s` hữu hạn; **yêu cầu ≥ 90% số mốc hợp lệ** trong cửa sổ, nếu không ⇒ `NaN`.
- **BẬT:** `ON_t = (x_t > thr_t(N))`. Nếu `x_t` hoặc `thr_t` là `NaN` ⇒ trạng thái **KHÔNG XÁC ĐỊNH**
  (loại khỏi mọi bảng ON/OFF, đếm riêng theo `n_undef`).
- **N ∈ {30, 90} ngày** = **2 giả thuyết chính** (`k = 2`). Ngưỡng `p = 0,80` và `MIN_SYM = 50` cố định,
  **không quét thêm** (chống multiplicity).
- Báo cáo bắt buộc: **% thời gian BẬT**, **số lần kích hoạt** (số đoạn ON liên tục + số lần chuyển
  OFF→ON), **phân bố theo năm/quý**, và **độ dài trung vị của một đoạn ON** (giờ).
- **Đối chứng định nghĩa (KHÔNG tính vào k):** tercile **THEO THỜI GIAN** như vòng trước — chạy lại
  cùng khung đo để chứng minh sự khác biệt giữa "thời kỳ" và "regime trượt".

---

## 2. Lợi nhuận khi BẬT vs TẮT (chi phí của luật)

Panel giờ, `T0 = 2021-12-31 00:00Z`, **W1 = 2023-01-01 → 2025-12-31 23:00** (cửa sổ chính; `ls_global`
có coverage 100% từ 2023). `IS = 2023-2024`, **`OOS = 2025`**. Lưới **1 mốc/giờ** (không chồng lấn).

- **Book proxy EW (universe):**
  `net(t,H) = mean_u [ c5_u(t+H)/c5_u(t) − 1 ] − FEE_RT − slip − fund`
  với `FEE_RT = 0,0010` (harness, 0,10% round-trip), `slip = 0,5·rg_u(t)/c5_u(t)` (nửa range),
  `fund = f5_u(t+H) − f5_u(t)` (funding tích luỹ, funding dương ⇒ long trả).
  `H ∈ {1h, 4h, 24h}`.
- **Neo MOM15** (`/tmp/funding_factor/pools.npz`, `m_valid` bit `j`): `net24 = m_raw[1] − m_slip − m_fund[1] − FEE_RT`,
  `net4h = m_raw[0] − m_slip − m_fund[0] − FEE_RT`; trạng thái ON lấy tại **giờ chứa mốc fire**
  (`floor(m_min/60)`). MOM15 **không có horizon 1h** trong `pools.npz` ⇒ chỉ 4h/24h (ghi rõ).
- **Neo cổng G3 (bắt buộc tái lập trước khi đọc bất kỳ số nào):** `n_DEV = 7128` và
  `net@0,10% = +1,6690% ± 0,05pp` trên 24h. Nếu lệch ⇒ **dừng, không kết luận**.
- **Chỉ số:** `mean`, `median`, `win%`, **`p05`**, **`p01`**, **`CVaR5`** (mean của 5% xấu nhất),
  `CVaR1`; **CI block-72h bootstrap ×1,21** (2000 rep, seed `20260905`); **`CI_adj = CI72h_x1.21 × √k`**;
  **MDE(p80 nửa-độ-rộng ×1,21)** trên 500 chuỗi null sign-flip 72h; `OOS` = 2025; `%quý OOS dương`;
  `ICC72`/`N_eff`.
- **Tương phản chính:** `ON − OFF`, dự đoán **< 0** (ON ⇒ forward xấu hơn). Đăng ký **6 ô** (2N × 3H)
  cho EW; neo MOM15 đăng ký **2N × {4h,24h} = 4 ô**, tất cả thuộc `k = 2`; báo cáo thêm mức toàn cục `√6`.

---

## 3. ĐUÔI intraday trên SÁCH THẬT (biến thiên (b) của câu hỏi)

**Chỉ đọc lại** chuỗi equity MTM mốc phút **đã tái tạo & đã nghiệm thu** ở `RESULT_INTRADAY_DD`
(cache `/home/ubuntu/intradaydd/series.npz`: `c_<run>` = mark `close`, `l_<run>` = mark `bar.low`,
`r_<run>` = realized; trục `2021-07-01..2025-12-30`, 1440 phút/ngày, 4 nền
`T170 / KEEPLEG0 / T100 / GD92`). **KHÔNG chạy lại sim, KHÔNG sửa code.**

> ⚠ Giới hạn đã biết (`RESULT_INTRADAY_DD` §7): không mô hình margin call; `c_` bỏ đường đi trong nến 1m.
> Vòng này **không** dùng cache để kết luận PASS/FAIL rủi ro nào của sim — chỉ để đo **phân bố đuôi**.

Với mỗi mốc giờ `t` trong W1 (ánh xạ sang chỉ số phút trên trục chung), trên `E = c_<run>`:

- `r24(t) = E(t+24h)/E(t) − 1`;
- **`drop24(t) = min_{m ∈ (t, t+24h]} E(m)/E(t) − 1`** (drop tính từ mốc đầu cửa sổ — metric CHÍNH của đuôi);
- `dd24(t)` = **maxDD trong cửa sổ** (cummax reset tại `t`, rồi `min(E/cummax − 1)`) — báo cáo phụ,
  **không có CI** (như `RESULT_INTRADAY_DD` §0 đã ghi: không bootstrap được cho metric cummax);
- biến thể `l_<run>` (mark `bar.low`) cho `drop24` = **cận dưới** của đuôi.

So **ON vs OFF** (`N = 30` và `90`): `mean/median/p05/p01/CVaR5` của `drop24`; **tỷ lệ cửa sổ ON trong
10 cửa sổ `drop24` tệ nhất** (so với **tần suất ON nền** ⇒ dùng "lift"); và **tỷ trọng đóng góp** của
các cửa sổ ON vào tổng `drop24` ÂM. CI block-72h ×1,21 cho tương phản `mean(drop24)` trên **KEEPLEG0**
(nền production) là chính; `T170/T100/GD92` là phụ.

---

## 4. Chi phí vs lợi ích của LUẬT (trả lời câu hỏi (2))

Luật đăng ký: `s_t = 1` khi OFF, **`s_t = 0,5` khi ON** (giảm nửa size). Biến thể phụ: `s_t = 0` (đứng ngoài).

- **Trên proxy EW 24h (một số DUY NHẤT phán quyết):** `r_rule(t) = s_t·net(t,24h)` trên toàn W1 ⇒
  `mean`, `t_iid`, `CVaR5`, `p01`, **maxDD của chuỗi luỹ kế 24h-step** — so trực tiếp với baseline `s ≡ 1`.
  Ngưỡng: luật **"đáng"** iff `Δ mean` (chi phí) **nhỏ hơn** `Δ CVaR5` (lợi ích đuôi) **theo tỷ lệ
  ≥ 1,5×** và `Δ mean > −1×MDE` của nhánh EW.
- **Trên sách thật (chỉ mô tả, KHÔNG mô phỏng):** báo cáo **lift** ở §3 và tỷ trọng đóng góp đuôi của
  cửa sổ ON. **Không** suy ra PnL có luật cho sách thật (không chạy sim) — nếu có đề xuất thì chỉ là
  **cấu hình để đưa vào SIM thật**.

---

## 5. KIỂM CHÉO BẮT BUỘC — tín hiệu có phải chỉ là proxy?

1. **Biến động cao:** `vol_t` = **SD cross-section** của log-return 1h tại `t` (universe như `U_t`).
   Đo: Spearman(`x_t`, `vol_t`); **Jaccard** giữa `ON_t` và tercile cao của `vol_t`;
   **tương phản ON−OFF bên trong TỪNG tercile vol** (2×2). Nếu hiệu ứng ON−OFF biến mất trong mọi
   tercile ⇒ **crowded-long chỉ là proxy biến động**.
2. **Downtrend BTC:** `btc24_t` = return 24h của `BTCUSDT`; `btcma_t` = `close/MA30(close) − 1`.
   Đo: Jaccard giữa `ON_t` và `{btc24 < 0}`; Jaccard giữa `ON_t` và `{btcma < 0}`;
   **tương phản ON−OFF bên trong `{btc24 > 0}`** (cửa sổ BTC đi lên) — nếu crowded-long chỉ là
   "BTC đang giảm" thì hiệu ứng phải **biến mất** khi BTC tăng.
3. Nếu trùng nhau nhiều ⇒ **phải nói rõ** và **ưu tiên cái đơn giản hơn** (vol hoặc trend) làm luật.

---

## 6. Tác động lên SỐ LỆNH (nếu dùng như filter)

- `% giờ ON` trong W1 = **% thời gian phải giảm size** (= tỷ lệ "mất lệnh" nếu `s = 0`);
- `% event MOM15` (n = **7128**, DEV 2022-2025; và subset trong W1) rơi vào **giờ ON**;
- số **đoạn ON** và **độ dài trung vị** ⇒ tần suất can thiệp vận hành.

---

## 7. Phán quyết định trước (viết trước khi đo)

- **(1) "Crowded-long là tín hiệu RỦI RO thật"** iff **cả ba**:
  (i) ít nhất **1 trong 2 N** cho `ON−OFF` của `net(24h)` EW **hoặc** của `drop24` (KEEPLEG0) có
  **`CI72h_x1.21 × √2` NGOÀI 0`** theo hướng **xấu hơn** khi ON;
  (ii) **OOS 2025 cùng dấu** ở ô đó;
  (iii) hiệu ứng **không biến mất** ở kiểm chéo §5 (còn trong ít nhất cửa sổ BTC-tăng **hoặc** trong
  một tercile biến động).
- **(2) "Giảm size có lợi > chi phí"** iff §4 đạt **và** §3 cho `lift ≥ 3×` (hoặc tỷ trọng đuôi của ON
  ≥ 2× tần suất nền).
- **(3) Nếu cả (1) và (2) đạt** ⇒ **1 cấu hình đề xuất cho SIM thật** (ghi rõ tham số, KHÔNG tự chạy).
  **Nếu không** ⇒ **ĐÓNG nốt**, không mở lại trục crowded-long/positioning.

---

## 8. Danh mục ô đo & multiplicity (chống "thử đến khi ra")

| nhóm | ô | k |
|---|---|---|
| Lợi nhuận EW | 2N × 3H = **6** | 2 |
| Neo MOM15 | 2N × 2H = **4** | 2 |
| Đuôi sách thật (`drop24`) | 2N × 1 nền chính = **2** (+3 nền phụ, không phán quyết) | 2 |
| Kiểm chéo | vol 2×2 + BTC-tăng = **3** (diễn giải, không tính k) | — |

`k = 2` (N = 30 vs 90 là hai giả thuyết); `CI_adj = CI72h_x1.21 × √2`; mức toàn cục `√6` báo cáo thêm.

## 9. Bỏ ngoài phạm vi

- **Không** chạy Java/sim/agent coding; **không** chạm 2026; **không** dùng `claude-run`.
- **Không** quét thêm `N`, `p`, hay horizon ngoài đăng ký; **không** thêm biến thể để "cứu" kết quả âm.
- **Không** dùng cho lọc cấp-coin (đã chứng minh VÔ HIỆU ở các vòng trước) và **không** đưa vào cổng AI.
- **Không** suy diễn PnL có luật trên sách thật (không chạy sim) — §4 chỉ là xấp xỉ trên proxy.
