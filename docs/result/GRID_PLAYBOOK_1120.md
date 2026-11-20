# Sổ tay kinh nghiệm grid — tổng hợp từ internet (truy cập 2026-11-20)

Nhãn: [TH] người thực hành có mô tả cụ thể · [SP] tài liệu sàn / người bán bot (có động cơ bán hàng) · [KC] có dữ liệu kiểm chứng độc lập · [SL] suy luận của agent tổng hợp. Mã nguồn [S..] xem cuối file.

## Kết luận chính

Gần như không có nguồn thực hành nào công bố PnL tổng thật, nhiều tháng, có phương pháp rõ. Phần lớn "kinh nghiệm" là bài của người bán bot, và ngưỡng hầu như luôn để trống. Hai nguồn có kiểm chứng mạnh nhất ([S14], [S5]) đều chỉ ra lợi thế hồi quy ngắn hạn nhỏ hơn phí maker — khớp với 7 phép thử nội bộ đã âm. Không có nguồn [KC] nào ủng hộ grid hai chiều có lãi sau phí trên futures.

## 1. Grid hai chiều (neutral)

- Chọn coin: các nguồn nói chung chung "đủ biến động + đủ thanh khoản + dao động quanh vùng, không trend đều" [S2][S19][S31][S11]; không nguồn nào cho ngưỡng số. Bảng xếp hạng ROI của Binance là hậu nghiệm, dính survivorship [S9].
- Vùng giá: Binance "AI" đặt MA ± 3σ (nến ngày, n = 7/30/180), độ rộng kẹp trong [1 %; 15 %]·n^(1/3) [S1]. Người thực hành nhận lỗi đặt vùng quá hẹp, giá văng khỏi vùng, bot nằm im hàng tuần [S4][S10].
- Số lưới: Binance 1,3·(U−L)/ATR khung ngắn [S1]; KuCoin (U−L)/ATR 15 phút [S2] ⇒ bước rất nhỏ.
- Bước lưới so với phí: lãi mỗi bước = bước − 2×phí [S18]; nên > 2× phí khứ hồi [S32]; Pionex 0,5–2 %/lưới [S16]. Một người chuyển 1,5 % → 2,5 % để tránh giao dịch quá nhiều [S13]; một người dùng bước = clamp(0,6×ATR%(1h,14); 1 %; 4 %) nhưng không báo PnL [S12].
- Đòn bẩy: chạy 5x rồi giảm về 2x vì −20 % trên tồn kho đã tích là thanh lý [S4]; Bitsgap khuyên 1x [S6].
- Tắt / dừng lỗ: công cụ có sẵn (stop ngoài biên, trailing theo đỉnh equity, giới hạn thời gian) nhưng không nguồn nào có ngưỡng được kiểm chứng [S3][S19].
- Kỳ vọng thực tế: 6 tháng BTC perp "gần hòa tới lãi khiêm tốn sau phí", không công bố số [S4]. Dữ liệu nền tảng Bitsgap H1 2026: tỉ lệ bot grid có lãi 35,1 %, lãi trung bình 2,34 %, trung vị 0,51 % [S7].

## 2. Grid một chiều theo xu hướng

- Định nghĩa "đang lên / đang xuống" của các sàn chỉ định tính: Long khi "đáy sau cao hơn + đủ dao động", Short khi "đỉnh sau thấp hơn + có nhịp hồi" [S19][S2]. Không nguồn nào cho MA cụ thể, độ dốc hay sức mạnh so với BTC.
- Trailing: Bitget kích hoạt khi MA 720 phút tăng vượt X % (X do người dùng chọn 1–50 %) [S22]; script 3Commas dời cả lưới lên 50 % độ rộng vùng khi close > High×1,03 [S34]; Binance có trailing up/down kèm giá giới hạn [S23].
- Sai lầm hay gặp: long grid trong downtrend thành "ôm lỗ" và còn trả funding [S4]; bật cả trailing lên và xuống, bot đảo chiều, báo lỗ lớn [S24] (giai thoại).
- "Bắt đầu sau cú giảm lớn / tại hỗ trợ" [S17][S10] thực chất là mua đáy (beta), không phải lợi thế của grid [SL].

## 3. Lọc trước (làm mịn tập đầu vào)

- Coin mới niêm yết: chờ giá giữ giữa hai mức "ít nhất vài ngày" và chạm mỗi biên hơn 1 lần; funding perp mới dao động bất thường [S20][S31].
- Funding: kiểm trước khi vào cỡ lệnh [S4].
- Thanh khoản: [S14] cho thấy độ đảo chiều 15 phút không tập trung ở cặp mỏng ⇒ lọc thanh khoản để giảm rủi ro thực thi, không để tăng lợi thế.
- Không thấy nguồn grid nào dùng bộ lọc giờ trong ngày / ngày trong tuần.

## 4. Tinh chỉnh và rủi ro

- Người dùng cho là có ích (chưa kiểm chứng): giảm đòn bẩy; cảnh báo margin ratio < 10 %, dừng < 5 %; chỉ đặt lệnh trong ±0,5 % quanh giá để giới hạn vốn lộ khi sập [S3]; chia vốn ~10 phần, mở dần [S10].
- Bằng chứng mạnh nhất về thứ KHÔNG hiệu quả (một người làm FX, có bán EA): grid đổi "xác suất nhỏ lỗ lớn" lấy "xác suất lớn lãi nhỏ"; equity stop 5–35 % đều vẫn lỗ; 3 840 tổ hợp tham số qua kiểm ngoài mẫu vẫn −23,2 %; tỉ lệ thắng 92–98 % đi kèm tài khoản −86 % [S8].
- Đánh giá bot: tổng PnL = lãi lưới + lãi/lỗ chưa thực hiện (+ funding). APR hiển thị của bot bỏ qua phần chưa thực hiện ⇒ APR ảo [S25]. Ví dụ: lãi lưới +197 USDT nhưng ROI −33 % [S26].

## 5. Nhiều bot / phân bổ

- Không bot nào > ~15 % tài khoản; đa dạng hóa đo bằng việc các bot có lỗ cùng lúc không, không bằng số lượng bot; nhiều bot long trên BTC/ETH/SOL thực chất là một vị thế [S21][S36]. Mỗi bot ≤ 20–30 % danh mục [S32].
- Nhận diện regime: chỉ thấy ADX (< 16 đi ngang, > 22 xu hướng) trong bài quảng bá; không có quy tắc "giảm toàn bộ" nào được kiểm chứng.

## 6. Bằng chứng phản biện

- [KC] arXiv 2608.21888 [S14]: đảo chiều giá 15 phút có ở 90 % trong 183 cặp spot Binance, mọi năm 2021–2026; yếu ở 1 h, mất ở 4 h. Lợi thế gross ≤ 1,3 bp/lệnh, không cặp nào vượt ngưỡng maker 5 bp; holdout 6 tháng hiệu ứng giảm ~1/3.
- [KC] Ledger [S15]: tự tương quan âm 1h/2h/4h trên BTC (dữ liệu ≤ 2021), không báo PnL.
- [KC] arXiv 2506.11921 [S5]: kỳ vọng grid = 0 dưới random walk; grid cố định BTC/ETH 2021–07/2024 ≈ 0 trước phí, âm sau phí; grid động reset dương nhờ uptrend.
- [SP] Bitsgap "futures thắng spot 72 %" [S6]: không công bố đòn bẩy/phí, chỉ long, 1 giai đoạn ⇒ không dùng làm bằng chứng.

## 7. Quy tắc đo được (R01–R30)

| Mã | Bước | Kinh nghiệm | Công thức ex-ante | Kỳ vọng | Nguồn | Mâu thuẫn |
|---|---|---|---|---|---|---|
| R01 | khung-vùng | Vùng theo dải thống kê | U/L = MA_n ± 3σ_n (nến 1d, n ∈ {7,30,180}); độ rộng kẹp [1 %; 15 %]·n^(1/3) | + neutral nếu giá ở lại vùng | SP [S1] | — |
| R02 | tham số | Số lưới theo ATR | N = 1,3·(U−L)/ATR khung ngắn | bước nhỏ, nhiều khớp, dễ âm sau phí | SP [S1][S2] | R03 |
| R03 | tham số | Bước phải trội phí | bước − 2·phí maker ≥ k·2·phí; nguồn nói "> 2×" hoặc 0,5–2 %; [SL] bước ≥ max(0,5 %; 10×0,04 %) | + mọi loại grid | SP ×5 | R02 |
| R04 | tham số | Bước co giãn theo ATR | bước = clamp(0,6·ATR%(1h,14); 1 %; 4 %) | chưa có PnL | TH [S12] | — |
| R05 | khung-vùng | Vùng đủ rộng cho thời gian chạy | (U−L)/P ≥ c·σ_ngày·√T; [SL] c = 2–3 | − tỉ lệ văng khỏi vùng | TH [S4][S10]; SP | — |
| R06 | chọn coin | Coin "dao động", không trend đều | [SL] Efficiency Ratio ER(30 ngày, nến 1h) thấp; hoặc chạm cả hai biên ≥ 2 lần | + neutral | TH [S11][S10]; SP | nội bộ: nhãn đi ngang mất tác dụng 2024–25 |
| R07 | chọn coin | Biến động vừa phải | [SL] xếp hạng ATR%_1d 30 ngày; loại 10 % thấp nhất và 10 % cao nhất | ± | SP ×4 | Bitget "vol cao tốt" ↔ nguồn khác "tránh" |
| R08 | bộ lọc | Thanh khoản tối thiểu | [SL] quoteVolume trung vị 30 ngày ≥ ngưỡng / top-N | − rủi ro thực thi | SP ×3 | [S14]: lợi thế không phụ thuộc thanh khoản |
| R09 | bộ lọc | Tránh coin mới niêm yết | tuổi ≥ D; [SL] D = 30–90 ngày | − rủi ro gãy vùng | SP [S20][S31]; KC [S14] | — |
| R10 | bộ lọc | Funding cực đoan | [SL] bỏ short grid nếu funding TB 3 ngày < −0,01 %/8h; bỏ long grid nếu > +0,05 %/8h | − squeeze / − chi phí | TH [S4] | khớp nội bộ |
| R11 | chọn chiều | Long khi đáy sau cao hơn, short khi đỉnh sau thấp hơn | [SL] dấu độ dốc EMA + đếm swing trên 4h–1d | + long/short grid nếu xu hướng tiếp diễn | SP [S19][S2] | **mâu thuẫn nội bộ: trend/momentum 6/6 NO-GO** |
| R12 | bật-tắt | Trailing lên theo MA | dời lưới khi MA(720 phút) tăng ≥ X % hoặc close > U×1,03 ⇒ dời 50 %·(U−L) | + long grid trong uptrend | SP [S22][S34][S23] | giai thoại lỗ lớn [S24] |
| R13 | bật-tắt | Mở long grid sau cú giảm lớn | [SL] giảm so với đỉnh 90 ngày ≥ 30–40 % | beta mua đáy | SP [S17]; TH [S10] | — |
| R14 | bật-tắt | Chỉ chạy khi ADX thấp | ADX14 (4h/1d) < 16–20 | + neutral? | TH quảng bá | bộ lọc ADX không bền ở thị trường khác [S30] |
| R15 | bật-tắt | Stop ngoài biên | đóng khi close < L·(1 − x); [SL] x = 1–2·ATR_1d% | cắt đuôi, cũng cắt lãi | SP [S3][S19] | [S8]: stop 5–35 % vẫn lỗ |
| R16 | bật-tắt | Reset vùng khi vỡ | vỡ trên: tái tâm; vỡ dưới: giữ hàng | thành thiên long | KC [S5] | thắng nhờ uptrend 2021–24 |
| R17 | rủi ro | Đòn bẩy thấp | lev ≤ 2; khoảng cách thanh lý dưới L ≥ max(50 %; 5·ATR_1d%) | − thanh lý | TH [S4]; SP | — |
| R18 | rủi ro | Guard margin | margin ratio < 10 % cảnh báo, < 5 % dừng | − thanh lý | TH [S4] | — |
| R19 | rủi ro | Chỉ đặt lệnh gần giá | chỉ đặt trong ±a quanh giá (a = 0,5 %) | − vốn lộ khi sập | SP [S3] | — |
| R20 | rủi ro | Kẹt hàng: ngừng thêm / cắt / hedge | [SL] trần tồn kho abs(net) ≤ m·vốn | cắt đuôi, giảm lãi | TH [S29][S11] | [S8] |
| R21 | phân bổ | Trần mỗi bot | mỗi bot ≤ 15 % (≤ 20–30 %) vốn; dự trữ 15 % | − tập trung | SP ×3 | — |
| R22 | phân bổ | Đa dạng theo tương quan / chiều | [SL] Σ(delta_i·β_i,BTC) ≤ X | − lỗ đồng thời | SP [S21][S36] | — |
| R23 | phân bổ | Chia vốn ~10 phần, mở dần | mở 1 phần khi lỗ ≥ y % hoặc mỗi tháng | DCA trá hình | TH [S10] | — |
| R24 | đánh giá | Tổng PnL, không APR | lãi lưới + chưa thực hiện + funding − phí; lỗ lớn nhất trên đường equity liên tục | lộ APR ảo | SP; TH | — |
| R25 | đánh giá | Phân phối lệch | báo trung vị và tỉ lệ cửa sổ 1/3/12 tháng có lãi | — | SP [S7]; TH [S8] | — |
| R26 | tham số | Thời gian một lần cắt mức phải nằm trong vùng có hồi quy | [SL] τ ≈ (bước/σ_1phút)² phút; hồi quy chỉ có ở 15 phút–1 giờ ⇒ bước ≈ 0,1–0,3 % cho BTC, nhưng lợi thế ≤ 1,3 bp < 4 bp phí maker khứ hồi | âm sau phí | KC [S14][S15] | R03 |
| R27 | tham số | Mọi lệnh post-only maker | lệnh limit-maker; đo tỉ lệ khớp bị chọn ngược | bắt buộc | SP [S3][S19] | nội bộ: maker bị chọn ngược |
| R28 | tham số | Số mức bị chặn bởi lệnh tối thiểu | N_max = vốn / min_notional | — | SP; TH | — |
| R29 | chọn coin | Short grid perp sắp hủy niêm yết | cần thông báo hủy niêm yết | + short | TH [S33] | không đo được (thiếu tin) |
| R30 | chọn coin | Grid cặp alt/BTC vùng hẹp hơn | log(P_alt) − β·log(P_BTC) | ? | TH [S11][S10] | 2 chân ⇒ phí ×2 |

**Nên kiểm trước** (cơ chế rõ, nhiều nguồn, đo được): R26 + R03 cùng lúc (quét bước × khung để tìm điểm cân bằng giữa hồi quy và phí — câu hỏi gốc); R24/R25 (chuẩn hóa thước đo); R17 + R19 + R20 (cắt đuôi rủi ro, đo đánh đổi); R09 (tuổi coin); R10 (funding cực đoan theo chiều); R06 (ER thấp); R05 (độ rộng vùng); R07 (dải biến động giữa); R22 (trần beta tổng); R12 (trailing cho long grid, sau khi chốt chiều).

**Huyền thoại / quảng cáo:** "crypto đi ngang 70 % thời gian"; bot "AI" và bảng xếp hạng ROI; "futures thắng spot 72 %"; APR hiển thị trên bot; tỉ lệ thắng 90 %+; "grid không cần đoán hướng"; script TradingView chọn giai đoạn đẹp.

**Mâu thuẫn trực tiếp với bằng chứng đã có:** R11/R12/R13 (grid theo chiều, mua sau cú giảm) ↔ trend/momentum nội bộ 6/6 NO-GO, lợi nhuận các nguồn này thực chất là beta; R02 (bước ≈ ATR khung ngắn) ↔ phí maker + thí nghiệm 400 nghìn lệnh maker bị chọn ngược; R06/R14 (lọc đi ngang) ↔ nhãn đi ngang nội bộ mất hiệu ứng 2024–25.

## Nguồn (truy cập 2026-11-20)

S1 binance.com/en/support/faq/647b0dba72d145219688b04aa51405fc · S2 kucoin.com/support/31130050642329 · S3 hummingbot.org/blog/strategy-guide-grid-strike/ · S4 dev.to/joe_hans_6c082d6c1caf189f/i-ran-a-gateio-btc-grid-bot-for-6-months-real-returns-and-3-fatal-mistakes-2i1p · S5 arxiv.org/pdf/2506.11921 · S6 bitsgap.com/blog/spot-vs-futures-grid-bot-what-backtests-show · S7 bitsgap.com/blog/what-actually-worked-in-2026 · S8 mql5.com/en/blogs/post/776032 · S9 binance.com/en/blog/futures/how-to-identify-and-replicate-futures-grid-trading-strategy-on-binance-futures-4391049088293774616 · S10 mirror Reddit r/Pionex (08/2022) · S11 coda.io/@tjuh1/recovery-grids · S12 dev.to/jmolinasoler/dynamic-grid-spacing-with-atr-letting-volatility-set-the-parameters-4jo0 · S13 dev.to/jmolinasoler/running-automated-crypto-grid-trading-bots-across-multiple-l2s-a-month-in-production-579c · S14 arxiv.org/pdf/2608.21888 · S15 ledger.pitt.edu/ojs/ledger/article/view/213 · S16 medium.com/pionex/faq-for-grid-trading-bot-on-pionex-150cf1b9ae23 · S17 medium.com/pionex/the-5-tips-for-trading-bot-which-may-help-you-make-more-profit-42b843f4dc08 · S18 dev.to/guardlabs_team/grid-bot-roi-the-first-principles-math-most-calculators-ignore-43le · S19 bybit.com/en/learn/bybit-trading-bot/make-profits-with-bybit-futures-grid-bot · S20 bitsgap.com/blog/new-listing-empty-order-book-what-your-bot-sees-on-day-one · S21 bitsgap.com/blog/how-much-per-bot · S22 bitget.com/support/articles/12560603800614 · S23 binance.com/en/support/faq/7a7bb22420404385991dee3a0930207d · S24 sikayetvar.com (khiếu nại Binance futures grid) · S25 medium.com/pionex/faq-for-infinity-grids-bot-on-pionex-8306c3e932f1 · S26 binance.com/square/hashtag/gridbot · S27 tradingview.com/scripts/gridbot/ · S28 myfxbook.com (fallacy martingale/grid systems) · S29 mql5.com/en/forum/491887 · S30 algolab.co.kr/blog/adx-filter-trend-breakout-backtest-2026 · S31 bitget.com/blog/articles/bot-crash-course-grid-bots · S32 dextools.io/tutorials/how-to-use-grid-trading-bots-crypto-2026-ja · S33 dev.to/quant001/shorting-binance-delisted-perpetuals-a-grid-strategy-from-monitoring-to-auto-execution-27bb · S34 tradingview.com/script/8N8DT3Pv-Geometric-Grid-Machine-3Commas/ · S35 cryptohopper.com/blog/grid-bot-p-l-why-red-doesn-t-mean-losing-13430 · S36 bitsgap.com/blog/one-bot-is-easy-five-bots-need-a-plan

Không tìm thấy: nguồn tiếng Việt có số liệu thực hành cụ thể; backtest công khai đa coin có phương pháp rõ cho futures grid; ngưỡng định lượng có kiểm chứng cho chọn coin / độ dốc MA / funding.
