# VZ_E1_TASKS — danh sách việc cho OpenClaw: bộ đo sự kiện E1 + khám phá 2024 + runner xác nhận

MASTER 2026-10-14. Đọc trước: `docs/plan/VZ_DATA_LAKE.md`, `VZ_PHASE1.md`, `VZ_RESEARCH_SPLIT.md` (vai trò năm — BẮT BUỘC tuân).

## Luật chung
- Chỉ đọc dataset `chuyendinh/vz-*-2024`, `vz-metrics5m` (file 2023-12 + 2024), `vz-funding` (2024), `vz-symbols`. CẤM đọc dữ liệu 2022/2023/2025/2026/2020s ở mọi task trừ T7 (chỉ khi có pre-reg đã commit). Lookback đầu 2024 được dùng tối đa 30 ngày cuối 2023 (chỉ để tính feature, không tính outcome).
- Chạy trên Kaggle kernel CPU (≤ 2 kernel song song TOÀN tài khoản, kiểm trước khi đẩy) hoặc Oracle (đĩa ≥ 30 GB). Không đụng 242/shadow/systemd, không Binance REST.
- Code `research/vz/e1/` branch `research/vz-e1` (worktree riêng). Python dùng `logging`, không `print`. Seed cố định. Mỗi task commit + trailer `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Sổ phép thử `docs/research/VZ_EXPLORE_LEDGER.md`: mỗi biến thể đã tính outcome = 1 dòng (task, họ, biến thể, n sự kiện, kết quả chính, ngày). Mô tả thuần (T2) ghi 0 phép thử.
- Lợi nhuận luôn **sau chi phí**: chi phí vào bucket EXEC thực (NC 0,0007 / C1 0,0018 / C2 0,0019 / C4 0,0032 theo bar_ret nến sự kiện) + phí 2 chân theo `SIM_RATE_FEE` của cấu hình `ho4p1-c2` (đọc trong `~/claude_master/1012/ecost/` prof_run.properties) + báo kèm bản stress (bucket stress 0,0023/0,0033/0,0041/0,0101).
- Thống kê: block bootstrap theo ngày UTC, block 5 ngày, NREP 2000, seed 20261014; báo mean, median, CI95, hit-rate, n. Không p-hacking: biến thể chốt trong file config trước khi chạy họ đó (commit config trước kết quả).
- Dừng & báo nếu: E1 không qua T1-V; sự kiện < 500/họ; lỗi dữ liệu.

## T0 — chuẩn bị
- Worktree `~/claude_master/vz_e1_wt` từ `module`; tạo ledger rỗng; ghi slug + version Kaggle các dataset 2024 dùng (từ `docs/data/VZ_REGISTRY.md`).

## T1 — E1 engine (`e1_core.py`)
1. Loader: đọc theo tháng, ghép kline1m + basis1m (sym, ts) + metrics5m (as-of: dòng có `create_time ≤ ts`, không lấy tương lai) + funding (rate gần nhất đã chốt ≤ ts, phút tới lần chốt kế).
2. Sự kiện chuẩn `crash`: phút có `close/open − 1 ≤ −1%`, `active`, `quote_volume ≥ 50 000`; gộp cùng symbol cách < 30′ (giữ phút đầu). Thời điểm quyết định t_dec = đóng phút; giá vào tham chiếu = close phút đó.
3. Feature tại t_dec (chỉ dữ liệu ≤ t_dec): bar_ret, bucket chi phí; taker_sell_share = 1 − taker_buy_quote/quote_volume ở phút sự kiện và trung bình 5′/15′ trước; volume z 60′; ΔOI 15′/60′ (%), OI value; prem_close, z-score prem 7 ngày; mark/index gap; funding rate, phút tới chốt; tuổi symbol (ngày từ first_date trong `vz-symbols`); ret 15′/60′/240′ trước sự kiện; BTC ret 15′/60′.
4. Outcome: log ret từ close sự kiện tới close sau 15′/60′/240′ (net chi phí như Luật chung); MAE/MFE trong cửa sổ.
5. **T1-V (bắt buộc PASS trước T2):**
   - V-a causal: test tự động — thay toàn bộ dữ liệu sau t_dec bằng NaN ⇒ mọi feature không đổi (bit-exact).
   - V-b tái lập: ghép với ledger chân EXEC `~/claude_master/1013/ll_h2/leadlag_h2_legs.csv.gz` (md5 e3a63b58; lọc năm 2024): close_M của ledger = close phút sự kiện VZ (|Δ|/close ≤ 1e-6) ở ≥ 99,5% chân ghép được; báo tỉ lệ chân EXEC 2024 rơi vào sự kiện `crash` của E1.
   - V-c tái lập chạy: chạy 2 lần ⇒ md5 output trùng.
   - V-d đếm: số sự kiện crash theo tháng 2024 + phân bố bucket NC/C1/C2/C4 (sự kiện crash luôn ≥ C1).
6. Output `e1_events_2024.parquet` (sự kiện + feature + outcome) để T2–T6 dùng chung.

### T1-V (cập nhật MASTER 2026-10-14) — V-b cũ SAI CÁCH, thay bằng V-b1/V-b2

**Lỗi lần 1 (đã sửa)**: V-b cũ ghép ledger theo cột `t_star`. Nhưng `t_star` trong ledger là
**sàn GIỜ của `t_dec`** (`leadlag_add1.py`: `tstar = t_dec // H * H`), KHÔNG phải phút sự kiện.
Phút sự kiện là **`s_ms`**. Vì vậy 8,51 % là kết quả của việc so sai cột, không phải sai nguồn.

**Nguồn `close_M` (đã ghi trong code)**: `close_M` = close của nến 1m Vision có **GIỜ MỞ = `s_ms`**,
đọc từ `kl/*.npz` do `ll_h2/exec_fetch.py` tải từ `data.binance.vision` (hàm `leadlag_add1.load_cm`,
`oM = kx[im,0]`, `cM = kx[im,3]`). ⇒ ledger dùng **Vision kline 1m**, KHÔNG phải ticker nội bộ.

**Chẩn đoán 3 quy ước** (6 713 chân 2024; 6 709 ghép được, 4 chân thiếu bar `nobarM`):

| quy ước | tỉ lệ khớp \|Δ\|/close ≤ 1e-6 |
|---|---|
| **(a) giờ MỞ nến = `s_ms`** | **6 709/6 709 = 100,000 %** |
| (b) giờ ĐÓNG nến = `s_ms` (mở tại `s_ms`−60′) | 22/6 709 = 0,328 % |
| (c) dịch −2′ / +1′ / +2′ | 7 / 88 / 30 = 0,104 % / 1,312 % / 0,447 % |

**⇒ KẾT QUẢ MỚI**

| mục | giá trị | ngưỡng | kết luận |
|---|---|---|---|
| **V-b1 (GIÁ)** | **100,000 %** (6 709/6 709), trung vị lệch 0 | ≥ 99,5 % | **PASS** |
| **V-b2 (TIMING) — trùng đúng phút** | 1 089/3 081 = **35,35 %** | ≥ 95 % | FAIL (theo nghĩa hẹp) |
| V-b2 — **trùng hoặc CÙNG cụm 30′** | **3 081/3 081 = 100,000 %** | ≥ 95 % | **PASS** |

Phần KHÔNG trùng đúng phút (1 992 chân) chia theo lý do: **gộp cụm <30′ = 1 992**
(1 486 “trực tiếp” + 506 “dây chuyền” do gộp bắc cầu), **lọc `quote_volume` = 0**, **khác = 0**.
⇒ 100 % chân EXEC có phút sập **đều nằm trên CẤU TRÚC SỰ KIỆN CRASH của E1**; khác biệt duy nhất là
luật gộp cụm 30′ của định nghĩa sự kiện (giữ phút đầu), KHÔNG phải lỗi dữ liệu.

**QUYẾT ĐỊNH (MASTER 2026-10-14)**: dùng **V-b1/V-b2 mới**; **MỞ LẠI T2–T6**. E1 **ĐÃ xác minh liên kết
với chân của hệ** ở mức GIÁ (V-b1) và CẤU TRÚC (V-b2). Vẫn KHÔNG chỉnh định nghĩa sự kiện/feature để
V-b đạt; H-B (T3) đo **chỉ trên SỰ KIỆN E1**.

## T2 — H-A mô tả (0 phép thử)
- Profile theo thời gian sự kiện −60′ → +240′ (median, IQR) của: taker_sell_share, volume z, prem_close, ΔOI tích luỹ, giá tích luỹ; tách theo bucket C1/C2/C4 và theo BTC cùng sập hay không (BTC ret 15′ ≤ −1%).
- Output json + 1 trang md có bảng; không chọn ngưỡng nào ở đây.

## T3 — H-B hồi có điều kiện (≤ 8 biến thể, chốt config trước)
Biến thể (tercile/quintile tính theo phân phối 2024, ghi ngưỡng vào config sau khi tính, trước khi xem outcome):
1. taker_sell_share phút sự kiện (quintile)
2. đảo chiều taker: share phút sự kiện − share TB 5′ trước (quintile)
3. ΔOI 15′ (quintile; OI rơi = proxy thanh lý)
4. ΔOI 60′ (quintile)
5. prem z 7 ngày (quintile)
6. funding rate tại sự kiện (quintile)
7. kết hợp: ΔOI 15′ thấp nhất × taker_sell_share cao nhất (tercile × tercile)
8. kết hợp: prem z thấp nhất × ΔOI 15′ thấp nhất
Thước chính: chênh net ret 60′ và 240′ giữa nhóm cực trên/dưới + tính đơn điệu qua các nhóm.

## T4 — H-C quanh giờ chốt funding (≤ 8)
- Sự kiện = mọi mốc chốt funding của mọi symbol active 2024 (theo `vz-funding`); feature = rate đã chốt và rate dự kiến (prem TB 8h trước); outcome ret −60′→0 và 0→+60′, +240′.
- Biến thể: quintile rate; |rate| cực trên 5%; dấu rate × chế độ BTC (BTC ret 24h > 0 / ≤ 0); interval 4h vs 8h. Báo net chi phí NC (không phải nến sập).

## T5 — H-D basis lệch cực đoan (≤ 8)
- Sự kiện: |prem z 7 ngày| > 3 (gộp 60′/symbol); outcome: thay đổi prem 15′/60′, giá net 60′/240′; tách dấu (âm/dương), theo thanh khoản (quote_volume ngày tercile), cùng/không cùng nến sập.

## T6 — H-E tuổi symbol (≤ 8)
- (a) sự kiện crash theo tuổi symbol: 0–7 / 8–30 / 31–90 / > 90 ngày; (b) drift không điều kiện 30 ngày đầu sau niêm yết (ret 1/3/7/30 ngày); (c) 30 ngày cuối trước last_date (symbol bị gỡ) — chỉ mô tả cẩn thận survivorship.

## T7 — runner xác nhận (dựng sẵn, KHÔNG chạy trên năm xác nhận)
- `e1_confirm.py --prereg docs/prereg/PREREG_VZ_<TÊN>.md --years 2022,2023,2025`: đọc khối YAML trong pre-reg (họ, biến thể, ngưỡng cố định lấy từ 2024, thước, luật GO, k phép thử cho nở CI √(2 ln k)); TỪ CHỐI chạy nếu file pre-reg chưa được commit (kiểm `git log -- <file>`) hoặc có thay đổi chưa commit; ghi output + md5 + hash commit pre-reg.
- Template `docs/prereg/PREREG_VZ_TEMPLATE.md` (khối YAML + phần lý do).
- Test: chạy runner trên 2024 với một pre-reg giả `PREREG_VZ_SMOKE.md` (đánh dấu SMOKE) ⇒ ra đúng số như T3 cho biến thể tương ứng (bit-exact).

## T8 — báo cáo
- `docs/result/VZ_EXPLORE_2024.md`: mỗi họ: n sự kiện, bảng hiệu ứng net (thực + stress) với CI, đơn điệu, ổn định theo quý 2024; tổng số phép thử từ ledger; **xếp hạng tối đa 3 ứng viên** kèm lý do cơ chế + rủi ro (không gọi GO). Nêu rõ giới hạn (1 năm, không liquidation thật, metrics 5′, trễ 7 s).
- Cập nhật `docs/data/VZ_REGISTRY.md` nếu dùng dataset mới. Không merge vào module (MASTER review).

## T9 (MASTER 10-14) — chân EXEC × sự kiện + chân trời dài (≤ 8 biến thể)
- Pre-reg: `research/vz/e1/configs/t9_config.json` (commit TRƯỚC outcome; edges lấy nguyên từ `configs/t3_thresholds.json`). Code: `research/vz/e1/e1_t9.py`.
- (a) 6 709 chân EXEC 2024 ghép sự kiện E1 theo cụm 30′ (feature của sự kiện; net đo **trên chính chân**: entry = Vision close tại `s_ms`, mốc 60′/240′/hold-to-exit). 4 biến thể: ΔOI60-q5, taker-reversal-q5, prem-z7-q5, combo ΔOI15 thấp × prem thấp (tercile×tercile, mã `prem*10+doi15`, hi=11/lo=33).
- (b) Trên sự kiện E1: net 4h (đã có) và 24h (`net_1440`, tính mới cùng công thức `e1_core`) cho ΔOI60 + đảo chiều taker = 4 biến thể.
- (c) H-E listing drift: báo thêm median, CI95, tỉ lệ dương — KHÔNG tính phép thử mới.
- Kết quả: 1 mục trong `docs/result/VZ_EXPLORE_2024.md`; ledger 8 dòng PRE-REG (31–38) điền outcome tại chỗ. **KHÔNG gọi GO** (power (a) thấp, CI ~ ±0,8 %).

## Lệnh giao OpenClaw (owner dán)
> Đọc `~/src/BinanceFuturesJava/docs/plan/VZ_E1_TASKS.md` (và 3 file plan VZ liên quan). Làm T0 → T1 (dừng nếu T1-V FAIL) → T2 → T3 → T4 → T5 → T6 → T7 → T8 đúng luật chung; song song được với việc nạp dữ liệu Phase 1 nhưng ưu tiên Phase 1 về đĩa/kernel. Báo ngắn sau T1-V và sau T8. Không đọc dữ liệu 2022/2023/2025/2026/2020s.
