# Rà soát tổng thể LIVE + BACKTEST + WFO và chiến lược DCA — 2026-08-20

Doc này tổng hợp 21 doc synthesis (golive, roadmap, luot_vs_nuoi, maxdd_anatomy, exit_sweep, pathstats, nuoi_safety_oos, fitness_audit, capital_lock, wfo_methodology/canonical/1m_vs_15m/recipe/arm_sweep, live30_audit, over_entry, gate_24h, kgrid K5/K8, dead_param, live_vs_wfo_reconcile) để trả lời: (1) logic live/backtest có sạch không, (2) WFO có đáng tin không, (3) edge có thực không, (4) chiến lược DCA nên thế nào. **Viết flaws-first: rủi ro trước, khuyến nghị sau.**

---

## PHẦN 0 — KẾT LUẬN 5 DÒNG

1. **Edge SELECTION là thật** (lift 11.7× ở 4h, 99% lệnh pump thật, 16/18 window OOS dương, 2026 Q1+Q2 dương độc lập). Nhưng **độ lớn PnL phụ thuộc regime** — dồn vào 2–3 quý pump (win8 2024Q1, win15 2025Q4 ≈ 31% tổng). Edge thật ≠ PnL lặp lại được.
2. **Logic live↔backtest phần lớn ĐÃ sạch** (giá entry ~0% slippage, OI 45/45 feature, gate khớp). Lệch còn lại là **tham số vận hành**, không phải bug logic.
3. **WFO đáng tin ở vai trò EVAL, KHÔNG phải OPTIMIZE.** Phát hiện lớn: HPO trong WFO đang degenerate (mọi gene đứng default vì capital-lock) → WFO thực chất chỉ là walk-forward-eval của 1 config frozen. Điều này **tốt** (không overfit knob) nhưng nghĩa là chưa từng có param nào được tối ưu thật.
4. **Đòn bẩy P&L còn lại KHÔNG nằm ở gate (đã hết dư địa) cũng KHÔNG ở exit-trailing (đã ở đỉnh 0.05).** Nó nằm ở: (a) chặn đuôi sập-đơn-coin bằng disaster-exit, (b) lọc chất lượng coin, (c) kiểm soát/khai thác việc vào-thêm-lệnh (DCA).
5. **Cảnh báo DCA quan trọng nhất:** DCA-down ngây thơ (nhồi lệnh khi lỗ) sẽ **KHUẾCH ĐẠI đúng cái đuôi maxdd** (sập đơn-coin Terra/meme). DCA chỉ an toàn khi: bounded legs + lọc tail-coin + giới hạn cửa sổ dip + BẮT BUỘC đi kèm hard catastrophic-stop trên vị thế gộp.

---

## PHẦN 1 — RÀ LOGIC LIVE

### 1.1 Cái đã sạch (đã verify, tin được)
- **Giá entry:** = close nến 1m tại phút tín hiệu, slippage median ~0.000%, không "lấy high". (live30_audit; báo cáo +9.7%/+44% trước đó là **bug tz double-trừ 7h**, đã sửa.)
- **OI feature:** ComputeOiFeat2Live242 chạy thành thread trong ingestor, push 691/vòng, tươi ~40' << tol 2h → selector live chạy **45/45 feature**, không NaN. ("8924 NaN" trước đó là false-positive khớp chuỗi "biNANce"/"baNANa".)
- **Gate:** pred live khớp WFO fold RAW; ngưỡng Min15M 0.008 khớp canonical.
- **Entry flow:** cùng luồng DetectEntrySignal2TradeNormal → gate AIRejectFilter → selector topK → dedup coin-đang-giữ (có ở cả live + sim).

### 1.2 Lệch thật còn lại (đều là tham số/hành vi vận hành, không phải bug logic)
- **⚠️ #1 — Live thiếu cap TOP-K ở leg selector (over-entry).** Backtest cap 5 coin/tick (rank-based); live vào MỌI coin qua ngưỡng per-symbol → 72–75 vị thế đồng thời, stacking dày. Edge backtest được validate VỚI cap 5 → live uncapped = **chạy ngoài phân phối đã test**. (Đã cap về K5 qua env, nhưng xem #2.)
- **⚠️ #2 — Pyramiding vô ý (DCA-up ngoài ý muốn).** dedup chỉ khóa khi đang giữ; TP thấp → coin pump chạm TP đóng nhanh → tick sau mở khóa → vào lại → leo từng nấc: **BTW×7 +46%, HEMI +44%, STAR×7, GPS×7**. Lệnh cuối gần đỉnh không kịp TP trước dump = "kẹt". Đây chính là "vào nhiều + leo đỉnh rồi kẹt" user cảm nhận. **Đây là DCA-UP không kiểm soát — nguy hiểm nhất, phải chặn trước khi bàn thêm DCA.**
- **Cẫy config.properties:** nhiều key kinh tế hardcode literal trong Configs.java (RATE_FEE, RATE_PROFIT_STOP_MARKET, NUMBER_ENTRY_EACH_SIGNAL, LEVERAGE) → config.properties(242) **bị bỏ qua**. Muốn biết param live thật phải đọc Configs default + env SIM_*. (live_vs_wfo_reconcile: chỉ 1 divergence thật là moveSL, đã bump 0.03→0.05.)
- NUMBER_ENTRY_EACH_SIGNAL=4 trong config.properties **không có hiệu lực** (Configs literal=2); chỉ dùng cho leg bigdown (DCA), selector không dùng.

### 1.3 Trạng thái go-live (2026-08-21 06:14)
Đã BẬT lệnh thật (hết shadow), đồng thời 3 thay đổi: arm 26%→15% + pred-gap lần đầu + lệnh thật. **⚠️ 3 thay đổi cùng lúc → nếu lệch rất khó tách nguyên nhân.** Rollback path đã có đầy đủ (env backup + jar backup).

---

## PHẦN 2 — RÀ LOGIC BACKTEST / STRATEGY

### 2.1 Fitness đáng tin (đã audit 5/5 PASS)
Công thức + thứ tự constraint + đơn vị đúng. Verdict FAIL/capital-lock là **chẩn đoán thật của config**, không phải lỗi thước đo. Không cần "làm mịn fitness" để sửa đúng-sai; chỉ cần nếu sau này bật HPO-search thật.

### 2.2 Bản chất chiến lược hiện tại (tách 2 tầng — điểm dễ nhầm nhất)
- **SELECTOR** học label `maxFav_4h ≥ 6%` (binary) = dự đoán "coin có bật ≥6% trong 4h" → đây là **SELECTION**, KHÔNG phải lệnh exit.
- **EXIT** (moveSL 0.05 + trailing genome) mới quyết định lướt hay nuôi.
- ⇒ Câu "model là lướt vì label 6%" **đúng ở tầng objective selector** (bắt spike 4h), nhưng maxdd KHÔNG do label — do exit không cắt đuôi + vào coin left-tail sâu.

### 2.3 Giải phẫu maxdd (đã đóng) — SỬA lại giả thuyết user
- Edge selector CÓ THẬT: 99% lệnh pump (median mfe1d +21%).
- "Ăn ít" = **exit không gặt** (+21% có sẵn nhưng lướt thoát sớm), KHÔNG do chọn coin.
- "Đuôi lớn" = **SẬP ĐƠN-COIN fat-tail** (LUNA/Terra death spiral + meme mới list pump-rồi-chết: BANANAS31, AIOT, HIPPO, MELANIA, OM... pump thật rồi sập 90–98%). **KHÔNG phải "cả rổ mua đỉnh rồi dump"** (bác giả thuyết: burst KHÔNG tệ hơn, lệnh cuối AN TOÀN hơn lệnh đầu).
- **Timing (cực quan trọng cho DCA):** 66.7% lệnh **dip TRƯỚC pump SAU** — median chạm đáy 3.5h, chạm đỉnh 12h. ⇒ cú dip ngay sau entry là BÌNH THƯỜNG, không phải tín hiệu thất bại. **SL chặt sẽ cắt ngay trước cú pump → phá edge.**

### 2.4 Lướt vs Nuôi — ĐÃ ĐÓNG bằng 3 dòng bằng chứng hội tụ
Có một **mâu thuẫn biểu kiến** trong docs, đã được giải quyết:
- **pathstats (raw excursion):** gợi ý "nuôi mạnh, giữ 24–72h, bỏ TP nhỏ" (pure-hold +9.4% >> TP/SL chặt +0.9%). NHƯNG đây là **raw price, KHÔNG fee/funding**, universe g008 ≠ canonical → chỉ là **hình dạng cơ hội**, doc tự ghi "phải validate WFO sim".
- **exit_sweep (WFO sim THẬT, có fee+funding):** khi validate thật, **RATE_PROFIT=0.05 là ĐỈNH** (+19,676); nuôi lỏng 0.10 → **SỤP −4,587** (giữ 4.3 ngày → ăn trọn dump dài). Đường inverted-U có vách.
- **nuoi_safety_oos:** không dự đoán được OOS coin nào sustain vs reverse (AUC ~0.45–0.58, đảo dấu qua năm). **Không time được nuôi.**

⇒ **VERDICT đã chốt:** raw-path phóng đại nuôi. Thực tế **exit moderate (trailing 0.05, arm nay 15%) là tối ưu** — không chặt hơn, không lỏng hơn. Phần "ăn ít" chấp nhận đánh đổi để tránh "ăn trọn dump".

### 2.5 Trả lời trực tiếp câu hỏi chiến lược trong project
- **"Lướt khi lỗ" (cắt nhanh khi lỗ): SAI ở thị trường này.** Vì dip-trước-pump 66.7%, cắt nhanh = cắt ngay trước pump. SL phải **RỘNG** (chỉ chặn thảm hoạ), không chặt.
- **"Nuôi khi lãi": đúng hướng nhưng BOUNDED.** Nuôi = trailing moderate (arm 15%, giveback vừa), KHÔNG phải giữ vô hạn (giữ lỏng = sụp trong sim thật).
- ⇒ Cấu hình đúng = **SL rộng chặn thảm hoạ (−15/−18% trên vị thế) + trailing moderate phía lãi.**
- **Nếu chuyển hẳn sang "SL-chặn-lỗ + nuôi-lãi" thì selector/gate đổi ra sao?** → **Gate: KHÔNG đổi** (hết dư địa, gate 15m để lọc điểm-vào chứ không dự báo trend dài — label 24h thua đều). **Selector: KHÔNG relabel horizon dài** (nuoi_safety_oos đã chứng minh không dự đoán được sustain; selector 4h vốn đã ngầm bắt trend — 4h-pickers chạy tới +27%@72h). **Thay đổi nằm ở EXIT + DCA, không phải selector/gate.**

---

## PHẦN 3 — RÀ KỸ WFO

### 3.1 Phát hiện lớn nhất: WFO KHÔNG optimize
Report K-grid cho thấy cả 17 gene **min==max** (đứng đúng default) qua mọi window. Nguyên nhân: mọi window `IS_fit ≈ −100000` (TOO_MUCH_CAPITAL_LOCK/BURN) → fitness in-sample phẳng → HPO không phân biệt được candidate → trả seed=default.
- **Hệ quả tốt:** mọi kết luận WFO lâu nay = walk-forward EVAL của config frozen (arm 26% = live), **không có per-window tuning → không overfit knob trên OOS.**
- **Hệ quả xấu:** chưa từng có param nào được tối ưu thật (arm chưa từng thử giá trị khác trong WFO). Muốn tối ưu phải fix capital-lock trước.

### 3.2 Nguồn gốc capital-lock: THIẾU disaster-exit
`HARD_STOP_LOSS_RATE=0, HARD_SL_PCT=0, TIME_STOP_HOURS=0` → exit duy nhất là trailing; trailing chỉ arm khi lãi ≥ arm (26%, 84% entry không chạm) → lệnh không pump đủ **ride vô hạn** tới hết window → 17–38% lệnh giữ >7 ngày (mức khoẻ 0.31%) → trip constraint pctHeldOver7d>2% → reject. **Losers KHÔNG fix được bằng arm** (arm chỉ trigger phía lãi). Fix = bật TIME_STOP_HOURS / SIM_HARD_SL_PCT (đều env, không rebuild).

### 3.3 Methodology: từng trộn HPO vào WFO (đã nhận diện + có quy trình sửa)
Việc đọc "ô tốt nhất theo total gộp trên toàn OOS" = chọn hyperparameter bằng chính OOS → selection bias. **Quy trình chọn đã CHỐT (áp cho mọi trục):** không đọc max-total → tính t-stat/worst-window/%dương → khử multiplicity → 1-SE rule (hoà thì chọn ít rủi ro đuôi nhất) → xác nhận 1 phát trên **2026 holdout sạch** (KHÔNG re-tune trên 2026, nếu không đốt holdout duy nhất).

### 3.4 Config canonical (frozen 2026-08-15)
Lưới **15m** / thr **0.015** / moveSL **0.05** / **K5** / 1x / fee 0.1% / funding ON. Kết quả G015-K5: total 18,528 (+53%/35k/4yr), 14/16 quý dương, worst DD 19.1% vốn, margin-call 0/16.
- **K5 vs K8:** K8 total cao hơn (20,247 vs 18,748) NHƯNG sau khử multiplicity ×5 + 1-SE rule, **cả K5–K15 nằm trong 1 SE của nhau** → khác biệt là nhiễu. K5 trội risk-adjusted (t=3.25, p=0.006, worst window −787 vs K8 −2,450). → **giữ K5** (đã revert live K8→K5).
- **Lưu ý tên project "model 1m" vs canonical 15m:** verdict 1m_vs_15m cho thấy **1m trơ với ngưỡng + t<2 (không có edge chắc)**; 15m@0.008 đều nhất (t=3.65, DD 0). Canonical dùng 15m@0.015 (mạnh ở 2025H2). **1m KHÔNG nên là lưới sản xuất.**

### 3.5 Rủi ro lớn nhất của WFO (chưa giải quyết)
**Edge dồn 2–3 quý pump → là kỹ năng chọn coin hay chỉ beta mùa pump?** Regime/outlier analysis (tách PnL theo mùa BTC, bỏ win8/win15) vẫn là ưu tiên #1 chưa làm. Cho tới khi làm, phải coi độ lớn PnL là **regime-dependent**, size theo kịch bản xấu nhất.

### 3.6 Data gap 2026
market_data + funding từng dừng ~2026-06-07 → 2026Q2 window chưa sinh trong WFO batch. Fix = rebuild market_data_object (ExportMarketData2File) → 2026-08 rồi re-fanout. (Cần lệnh/args từ user.) Live vẫn chạy realtime nên không chặn go-live, chỉ chặn việc đóng đinh holdout 2026 trong WFO.

---

## PHẦN 4 — CHIẾN LƯỢC DCA (đề xuất)

> **Định nghĩa dùng ở đây:** "DCA" = chiến lược vào-thêm-lệnh trên cùng một coin/portfolio. Có 3 biến thể khác nhau về bản chất — phải tách rõ vì rủi ro ngược nhau:
> - **DCA-DOWN** (nhồi khi lỗ, hạ giá vốn TB)
> - **DCA-UP / pyramid** (thêm khi lãi — hiện đang xảy ra vô ý ở live)
> - **DCA-portfolio** (lịch giải ngân vốn theo regime)

### 4.0 Nguyên tắc nền (rút từ toàn bộ evidence)
1. Edge = selection thật nhưng magnitude regime-dependent → **không all-in, size fractional + cap theo regime xấu nhất.**
2. Không time được sustain/reverse (OOS null) → **DCA phải theo LUẬT CỨNG, không theo dự báo.**
3. Đuôi = sập đơn-coin → **mọi DCA phải lọc tail-coin + có hard-stop gộp.** Đây là ràng buộc không thương lượng.
4. WFO chưa optimize + capital-lock → **fix capital-lock TRƯỚC, mọi A/B DCA sau đó mới không bị confound.**

### 4.1 ƯU TIÊN 0 — Chặn DCA-UP vô ý ở live (làm TRƯỚC, không phải "thêm DCA")
Đây là việc cấp thiết nhất và ngược đời: **thứ giống DCA nhất đang chạy ở live lại là thứ có hại nhất.** Trước khi thêm bất kỳ DCA có chủ đích nào:
- **Cap top-K ở leg selector live** (mirror sim rank-mode: lấy K coin score tốt nhất chưa-giữ, break tại K). Đã cap K5 nhưng cần đảm bảo per-coin re-entry sau TP không rò.
- **Cooldown re-entry per-coin** sau khi TP đóng (vd ≥ 1 chu kỳ label / vài giờ) — chặn recycle mỗi tick.
- **Chống đuổi đỉnh:** cấm re-entry nếu giá hiện tại > giá-entry-đầu-của-run × (1 + chase_limit). chase_limit ~ 5–8%. Cắt đúng cơ chế "lệnh cuối leo đỉnh rồi kẹt".
- **Verify bằng shadow:** nhịp would-BUY/tick ≤ K, số lệnh/ngày về gần backtest (~1.2/ngày).

### 4.2 ƯU TIÊN 1 — Disaster-exit (điều kiện cần cho MỌI thứ, kể cả DCA)
- Bật **SIM_HARD_SL_PCT** (hard catastrophic-stop theo giá entry, vd thử {0.15, 0.18, 0.20}) và/hoặc **TIME_STOP_HOURS** ({72, 120, 168}h).
- **Ngưỡng phải > cú dip thường** (median mae1d ~−9%, p05 −19%) để KHÔNG cắt winner ở cú dip 3.5h. → hard-stop ~−15/−18% là vùng hợp lý (dưới nhiễu dip, trên vùng "đang sập").
- Mục tiêu đo: pctHeldOver7d < 2% (thoát capital-lock) + IS_fit thoát −100000 → WFO bắt đầu optimize thật.

### 4.3 DCA-DOWN "dip-fill" — CHỈ bản bounded, tail-filtered (đề xuất chính, cần A/B)
Cơ sở duy nhất ủng hộ DCA-down: **66.7% dip-trước-pump, dip ~3.5h.** Nghĩa là một lần vào-thêm trong cửa sổ dip có thể hạ giá vốn ngay trước cú pump. NHƯNG rủi ro chí mạng: nhồi vào coin đang sập-đơn-coin = khuếch đại maxdd. Vì vậy chỉ chấp nhận bản **có 5 khoá an toàn cùng lúc**:

| Khoá | Luật | Lý do (evidence) |
|---|---|---|
| **Bounded legs** | Tối đa **1 leg thêm** (2 legs tổng). KHÔNG martingale grid. Size leg-2 ≤ leg-1 (w 1,1), **KHÔNG dùng w1,1,3,8** (escalating = tự sát khi sập). | Grid escalating chính là thứ blow-up trên collapse |
| **Cửa sổ thời gian** | Chỉ fill trong **~4–6h đầu** kể từ entry-1 (cửa sổ dip). Sau đó không nhồi. | dip median 3.5h; quá cửa sổ = không còn là "dip trước pump" |
| **Dải giá dip** | Fill khi giá về **−6% đến −8%** so entry-1 (trong dải dip thường). **KHÔNG fill sâu hơn** −ngưỡng hard-stop. | −6..−8% nằm giữa dip thường (−9% median... thực ra fill NÔNG hơn median để chừa biên) và catastrophic |
| **Lọc tail-coin** | **CẤM DCA** cho coin mới list < N ngày, thanh khoản thấp, trong DIED_SYMBOLS-risk. | Đuôi = đúng nhóm coin này (Terra/meme) |
| **Hard-stop gộp** | Vị thế gộp (sau leg-2) vẫn chịu hard catastrophic-stop −15/−18% theo giá vốn TB. | Không có cái này thì DCA-down = tăng thẳng exposure vào coin chết |

**Kỳ vọng thành thật:** modest. Đây KHÔNG phải đòn bẩy lớn; nó cải thiện giá vốn trên nhóm winner dip-trước-pump, đổi lại tăng nhẹ rủi ro nếu lọc tail không hoàn hảo. **Phải đo net trong WFO sim (fee+funding), không tin raw-path.**

### 4.4 DCA-portfolio — sizing theo regime (đơn giản, không dự báo)
- Vì magnitude regime-dependent + không time được regime OOS → **KHÔNG dùng model dự báo regime để tăng/giảm size.** Thay bằng luật cứng:
  - Fractional sizing cố định + **cap notional theo kịch bản xấu nhất** (size từ worst-window DD, không từ mean).
  - Có thể giảm size khi số vị thế đồng thời cao (chống over-deploy như live 72 vị thế).
- Kill-switch cluster-DD (breaker hiện OFF) — cân nhắc bật ở mức bảo thủ cho tail-risk hệ thống.

### 4.5 Cái KHÔNG nên làm (flaws-first)
- ❌ **DCA-down open-ended / martingale** (grid w1,1,3,8): khuếch đại đuôi sập-đơn-coin. Từ chối.
- ❌ **Relabel selector horizon 24h/72h để "nuôi an toàn"**: nuoi_safety_oos đã chứng minh không generalize. Prior thấp.
- ❌ **Tune DCA params bằng cách đọc max-total trên WFO**: lặp bẫy selection-bias K8. Dùng deflated-t/1SE/worst-window + 2026 holdout.
- ❌ **Chạy A/B DCA khi capital-lock chưa fix**: fitness degenerate → kết quả confound, vô nghĩa.

---

## PHẦN 5 — THỨ TỰ THỰC THI ĐỀ XUẤT

1. **Ổn định go-live** (đang 3 thay đổi cùng lúc): theo dõi arm-15% + pred-gap vài ngày, tách tác động, sẵn sàng rollback.
2. **Chặn DCA-up vô ý** (§4.1): cap K + cooldown + chống-đuổi-đỉnh; verify shadow. → thu hẹp divergence live↔backtest lớn nhất.
3. **Fix capital-lock** (§4.2): bật hard-SL/time-stop, đo pctHeldOver7d<2%, unlock WFO optimize. → điều kiện cần cho mọi A/B sau.
4. **A/B disaster-exit** trên WFO full-range (deflated-t/1SE/worst-window), confirm 2026 holdout.
5. **A/B DCA-down bounded** (§4.3) chỉ sau khi (3)(4) xong — đo net PnL + maxdd, so baseline no-DCA.
6. **Regime/outlier analysis** (ưu tiên #1 tồn đọng): tách PnL theo mùa BTC, bỏ win8/win15 → biết edge là skill hay pump-beta → quyết định sizing thật.
7. (Nền) rebuild market_data 2026 để đóng đinh holdout WFO.

**Nguyên tắc:** Live = tiền thật, mọi thay đổi qua env + backup + shadow verify; mở rộng push CHỈ sau A/B dương. Đòn bẩy P&L thật đã được chứng minh KHÔNG ở gate/exit-trailing mà ở **disaster-exit + lọc coin + kiểm soát DCA**.
