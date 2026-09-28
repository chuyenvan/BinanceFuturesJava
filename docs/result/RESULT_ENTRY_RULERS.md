# RESULT_ENTRY_RULERS — BỘ THƯỚC "TẦNG ENTRY" (vi mô) + LÀM MỊN LẠI

Pre-reg: `docs/prereg/PREREG_ENTRY_RULERS.md` (commit `c24c908`). Code: `research/analysis/entry_rulers.py`.
JSON: `docs/result/entry_rulers.json`. Thuần Python offline, **KHÔNG** train/sim, **KHÔNG** chạm
242/ONNX/LIVE. DEV only (**<= 2025-12-31**; pool `P32` kết thúc 2025-09-27). `sha256` pool `1d42b7f6…`.

**Mẫu:** pool `P32` = **9.651 tick dùng chung** (nhịp 15') × 32 coin = **308.832 leg** (bỏ 6 tick thiếu điểm;
mọi đối tượng ghép cặp trên **cùng tập tick**). CI: **block-72h (362 khối), 2000 rep, seed `20260905`**,
paired; `inflate(k_ruler=6)=1,8926` · `inflate(k_obj=10)=2,146`. `f=0,006`.

## 1. ĐỊNH NGHĨA 4 THƯỚC (1 dòng/thước)

| thước | 1 dòng |
|---|---|
| `rank_ic` | trung bình theo tick của `Spearman(score_t, gross_t)` trên **cả 32 coin** (rank-based, bất trị đuôi). |
| `top_decile_lift` | trung bình của `mean(gross \| top-4 theo score_t) − mean(gross \| cả tick)`. |
| `winrate` | tỉ lệ leg `net>0` trên **tập chọn CỐ ĐỊNH top-8/tick** (không cắt đuôi) — vũ trụ cố định. |
| `pnl_vol_norm` | `mean_leg( net / sigma_sym )` trên tập chọn top-8 (`sigma_sym` = std `gross` của coin đó). |

Phụ: `edge5` (lift top-5), `med_lift` (bản median của lift top-4). **Bỏ:** turnover-adjusted (turnover hằng
32 leg/tick ⇒ hằng số nhân, vô nghĩa — pre-reg §4).

## 2. BẢNG: đối tượng × 4 thước chính (điểm [CI thô] · `width_rel` · `out`=ngoài CI thô&nới)

| đối tượng | `rank_ic` | `top_decile_lift` | `winrate` | `pnl_vol_norm` |
|---|---|---|---|---|
| 45deploy | +0,0274 [+0,0164,+0,0383] w0,80 **out** | +0,00230 [−0,0006,+0,0053] w2,54 | +0,7997 [+0,7798,+0,8187] w0,05 **out** | +0,1213 [+0,0630,+0,1767] w0,94 **out** |
| A44 | +0,0262 [+0,0154,+0,0374] w0,84 **out** | +0,00085 [−0,0021,+0,0037] w6,86 | +0,7976 [+0,7768,+0,8170] w0,05 **out** | +0,1209 [+0,0611,+0,1780] w0,97 **out** |
| A45 | **+0,0324** [+0,0213,+0,0432] w0,68 **out** | +0,00180 [−0,0008,+0,0044] w2,90 | **+0,8005** [+0,7802,+0,8196] w0,05 **out** | +0,1265 [+0,0685,+0,1812] w0,89 **out** |
| V1 | +0,0268 [+0,0156,+0,0385] w0,85 **out** | +0,00178 [−0,0009,+0,0045] w3,05 | +0,7981 [+0,7769,+0,8174] w0,05 **out** | +0,1235 [+0,0646,+0,1795] w0,93 **out** |
| V5 | +0,0243 [+0,0128,+0,0357] w0,94 **out** | +0,00025 [−0,0027,+0,0032] w23,2 | +0,7975 [+0,7769,+0,8170] w0,05 **out** | +0,1226 [+0,0626,+0,1779] w0,94 **out** |
| MRA4 | +0,0177 [+0,0071,+0,0285] w1,21 | +0,00239 [−0,0007,+0,0052] w2,50 | **+0,7808** [+0,7583,+0,8015] w0,06 **out** | **+0,1423** [+0,0793,+0,2006] w0,85 **out** |
| S1 | +0,0212 [+0,0073,+0,0349] w1,30 | −0,00328 [−0,0105,+0,0033] w4,22 | +0,7925 [+0,7715,+0,8129] w0,05 **out** | +0,1067 [+0,0513,+0,1616] w1,03 **out** |
| ofi_candidate | +0,0225 [+0,0083,+0,0370] w1,28 | −0,00235 [−0,0088,+0,0037] w5,33 | +0,7944 [+0,7744,+0,8147] w0,05 **out** | +0,1131 [+0,0584,+0,1679] w0,97 **out** |
| ofi_baseline_fresh | +0,0212 [+0,0075,+0,0349] w1,29 | −0,00318 [−0,0107,+0,0034] w4,42 | +0,7912 [+0,7700,+0,8124] w0,05 **out** | +0,1030 [+0,0463,+0,1576] w1,08 |
| ofi_noise | +0,0211 [+0,0071,+0,0355] w1,35 | −0,00374 [−0,0103,+0,0022] w3,35 | +0,7921 [+0,7718,+0,8129] w0,05 **out** | +0,1075 [+0,0528,+0,1616] w1,01 **out** |

Phụ: `edge5` chỉ 45deploy(+0,0017,+MRA4 +0,0024) dương còn S1/OFI **âm** (−0,0022…−0,0032), nhưng **mọi CI
chứa 0** (w 2,2–12,5) ⇒ **không phân giải**. `med_lift` **ÂM ở cả 10 đối tượng** (w 1,3–2,8): bởi
`gross` rời rạc tại các mức TP (`0,04/0,045/0,05/0,055/0,06…`, trung vị tick ≈0,0506) ⇒ **artifact của
nhãn rời rạc**, không phải tín hiệu.

## 3. TRẢ LỜI (4 câu bắt buộc)

**(1) 4 thước cho gì + có ai THẮNG ngoài CI vs CẢ 2 đối chứng?**
`rank_ic`: dương ở **cả 10** đối tượng, CI (nới) ngoài 0 cho **5/10** (`45deploy`/`A44`/`A45`/`V1`/`V5`;
`MRA4` cũng là bins nhưng CI chứa 0); **A45 cao nhất**
(+0,0324). `winrate`: **CI cực hẹp** (w≈0,05) và ngoài 0 ở **cả 10**; A45 cao nhất (+0,8005), **MRA4
thấp nhất** (+0,7808). `pnl_vol_norm`: ngoài 0 ở 9/10, **MRA4 cao nhất** (+0,1423).
`top_decile_lift`: **KHÔNG ô nào ngoài CI** (w 2,2–23) ⇒ **vô dụng**. (Phụ `edge5` cũng vậy; `med_lift` artifact.)
⇒ **KHÔNG đối tượng nào THẮNG**: không ai có Δ>0 ngoài CI (thô&nới) vs **cả** `45deploy` **và** `V1`
trên **>=2** thước chính. Tín hiệu "ngoài CI" DUY NHẤT: **MRA4** có `winrate` **THẤP hơn** cả 2 đối chứng
(Δ −0,0189 vs 45deploy; −0,0173 vs V1; **out**) và `pnl_vol_norm` **cao hơn** V1 (+0,0188, **out**);
`A45` hơn `45deploy` ở `rank_ic` (Δ +0,0050, CI thô ngoài 0, **nới thì chứa 0**); `ofi_noise` thấp hơn ở
`top_decile_lift` (Δ −0,0060, out). ⇒ chưa có "đối tượng thắng" nào; nhưng bộ thước **đã phân giải** (khác
hẳn tầng tiền).

**(2) Có đổi thứ tự xếp hạng so với tầng TIỀN không? CÓ — rõ.**
Tầng tiền `net_tick` (f=0,006): `MRA4` **#1**. Nhưng `rank_ic`/`winrate`/`med_lift` đặt **MRA4 #10 (bét)**
và `A45` **#1**. Spearman(entry-rank vs money-rank): `rank_ic +0,39` · `winrate +0,42` · `med_lift +0,78`
(khác) so với `top_decile_lift +0,90` · `edge5 +0,95` · `pnl_vol_norm **+0,99**` (gần như ĐỒNG NHẤT với tiền).
⇒ **tầng tiền `net_tick` đang xếp theo "độ tập trung đuôi", KHÔNG theo chất lượng xếp hạng entry**;
"MRA4 #1" là nhờ **vài big winner** (winrate thấp nhất) — bị bộ thước entry phát hiện.
(`money_sized_A_mean` thậm chí xếp OFI/S1 lên đầu ⇒ tham số trần/size lật ngược hoàn toàn.)

**(3) Thước nào PHÂN GIẢI được / KHÔNG + bộ chuẩn ENTRY (không trùng).**
- Phân giải (nhỏ = tốt): `winrate` **w≈0,05** (mạnh nhất) · `pnl_vol_norm` w≈0,85–1,08 · `rank_ic` w≈0,68–1,35.
- KHÔNG phân giải: `top_decile_lift` (w 2,2–23, **0/10 ngoài CI**) · `edge5` (w 2,2–12) · `med_lift` (w 1,3–2,8).
- **Trùng lặp** (10 đối tượng): `top_decile_lift ↔ edge5` **ρ_Pearson 0,99** (trùng) · `rank_ic ↔ winrate`
  ρ_P 0,88 / **ρ_S 0,99** (trùng thứ tự) · `pnl_vol_norm ↔ edge5` 0,91 · `pnl_vol_norm ↔ money_net_tick` **0,99**
  (⇒ `pnl_vol_norm` là **proxy của tầng tiền**, không phải thước entry độc lập).
  Hai **trục gần trực giao**: [rank-quality: `rank_ic`≈`winrate`] ⟂ [tail/money: `pnl_vol_norm`≈`edge5`≈tiền]
  (`rank_ic ↔ pnl_vol_norm`: ρ_P 0,15 / ρ_S 0,36; `winrate ↔ pnl_vol_norm`: ρ_P **−0,20**).
- **BỘ CHUẨN ENTRY đề xuất (2 thước, không trùng):** **(a) `winrate@top-8`** (trục rank-quality, đuôi-miễn,
  CI hẹp nhất, "đại diện" cho `rank_ic` vì ρ_S 0,99) + **(b) `pnl_vol_norm@top-8`** (trục tail/PnL, gần trực
  giao với (a)). Nếu muốn đủ 3–4: thêm **`rank_ic`** (quét cả 32 coin, độc lập với tiền) nhưng **ghi rõ nó
  trùng thứ tự với `winrate`**; **KHÔNG** thêm `top_decile_lift`/`edge5`/`med_lift`.

**(4) Tận dụng ngay + vòng xác nhận (kèm chi phí).**
- Tận dụng ngay (offline, ~0đ): tầng tiền bỏ sót rằng **S1/OFI có `top_decile_lift` ÂM** (−0,002…−0,004)
  trong khi **mọi bins-object DƯƠNG** ⇒ phần **thập phân vị TRÊN của S1/OFI phản dự báo** (score cao nhất =
  gross thấp hơn trung bình tick). Tiền không thấy vì chỉ cộng PnL top-8.
- **Vòng E1 (offline, ~0đ, vài phút):** "cắt thập phân vị trên" — chọn từ decile 2–3 thay vì decile 1 cho
  S1/OFI, đo lại `winrate`/`pnl_vol_norm` + tầng tiền `net_tick`. Quyết: nếu top-decile âm là thật ⇒ bỏ
  đuôi-trên ⇒ cải thiện tiền **mà không cần sim**.
- **Vòng E2 (1 chặn Kaggle/sim):** xác nhận `winrate@top-8` dẫn tầng tiền: sim **A45 vs 45deploy** đọc
  `dCAGR` — kỳ vọng dương nhỏ; **chi phí 1 chặn Kaggle (~1 giờ, 0 tiền mặt)**; chỉ chạy nếu cần "nối" thước
  entry ↔ tiền.

## 4. MỤC BỎ + LÝ DO

- **BỎ `turnover-adjusted`** (chốt trước): turnover **hằng** giữa mọi đối tượng ở tầng pool ⇒ hằng số nhân.
- **BỎ `top_decile_lift` + `edge5`** khỏi bộ chuẩn: **0 ngoài CI** (không phân giải) **và** trùng nhau (ρ 0,99).
- **BỎ `med_lift`**: âm cả 10 đối tượng do **nhãn rời rạc tại mức TP** (artifact), không phải tín hiệu.
- **KHÔNG dùng `pnl_vol_norm` như thước entry ĐỘC LẬP**: ρ 0,99 với `money_net_tick` (proxy tiền).
- **KHÔNG đọc/kết luận 2026**, KHÔNG chạm 242/ONNX/LIVE, KHÔNG push file dữ liệu.
