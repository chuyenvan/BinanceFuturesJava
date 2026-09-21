# TƯỜNG POWER — tầng equity đã chết, quyết định chuyển hẳn về tầng xếp hạng (2026-09-03)

**Đây là kết luận quan trọng nhất của ngày 2026-09-03. Đọc trước khi đề xuất bất kỳ thí nghiệm mới nào.**
Nguồn: `docs/NBETS_RESULT.md` (kết luận cuối), `docs/CI_REAUDIT.md`, `docs/DATA_EXTENT_SURVEY.md`,
`docs/TICKLOG_RESULT.md`, `docs/FS_RESULT.md`, `docs/G015CUT_RESULT.md`, `docs/GS_WAVE1_RESULT.md`,
`docs/B4_RESULT.md`.

> **PORT 2026-09-20 (executor TASK C)**: file này trước đó chỉ tồn tại trong project memory của
> MASTER, CHƯA từng được commit vào repo (`git log --all -- docs/power_wall.md` rỗng trước commit
> này). Nội dung dưới đây port NGUYÊN VĂN từ project memory `power_wall.md` (đã có banner đính
> chính C2b/T170 từ trước) — không sửa nội dung ngoài việc thêm chính dòng port này.

🔴 **ĐÍNH CHÍNH 2026-09-20 (đọc trước khi dùng bất kỳ con số ICC nào dưới đây)**: mọi số ICC=0.247 /
trần 1/ICC=4.05 cược trong file này được đo trên **C2b** (baseline cũ, đã SUPERSEDED). Đo lại bằng
đúng `icc_anova()` của `nbets_step3_crosssec.py` trên incumbent hiện tại **T170** cho **ICC=0.0516**
(bền theo cohort 72h/tuần), **trần 1/ICC=19.4 cược**, KHÔNG phải 4. `n_eff` thực của T170 (3.13) bị
chặn bởi **k̄=3.55 vị thế đồng thời** + chỉ **105/1644 ngày có lệnh vào** (77% giờ trống), KHÔNG phải
bởi tương quan trong-ngày. TASK2 (hedge BTC nhắm vào ICC=0.247) đã chạy Phương án A (overlay
counterfactual) và ra **NULL**: hedge triệt được beta (r² 0.031→0.0015) nhưng ICC lại TĂNG 4.3 lần
(0.0516→0.2208, do beta rolling causal tự nó là một cú sốc chung mới, nhiễu hơn beta nó thay thế) —
xem `round_2026-09-20_beta_decomp_and_data_survey.md` mục TASK2 để biết đầy đủ. Kết luận: đòn bẩy
power ĐÚNG cho T170 không phải "giảm ICC bằng hedge" mà là **tăng k̄ (số vị thế đồng thời) / tần suất
vào lệnh** — chưa có PREREG cho hướng này, để ngỏ cho vòng sau.

## KẾT LUẬN CUỐI (NBETS, đã qua cổng kiểm phủ): KHÔNG có cấu hình nào đo được 3pp ở tầng equity

MDE80 **sàn khả thi = 3.78pp**, và ô đó đòi 6.31 năm dữ liệu (gồm cả VAL) + vô hạn vị thế. Thực tế
nhất (6 năm, bỏ OI, train lại) = **4.94pp**. Cặp đổi selector cách 3pp thì cần **10–16 năm**. Gộp
mọi lever còn lại (thời gian + ngang + time-stop) = 2.02×, cần 2.55× ⇒ **vẫn thiếu 1.6 lần**.
⇒ **Tầng equity từ nay chỉ dùng cho ràng buộc cứng (maxDD) + sanity. Mọi quyết định chuyển hẳn về
tầng XẾP HẠNG** (rank-IC S1−G015 = +0.0973 CI [+0.0711,+0.1152]; gate edge +0.0182 — hai thứ duy
nhất đo được với n_eff 39–52).

## SỬA LẬP LUẬN CŨ CỦA CHÍNH FILE NÀY (NBETS bác 2 điểm)

- **SAI**: "nút cổ là số khối độc lập (304)". Số khối 72h là đơn vị resample, **không phải cỡ mẫu
  hiệu dụng**. ESS variance-ratio thật của C2b = **1089–1826 ngày iid tương đương, LỚN hơn 911**;
  số cược hiệu dụng trên ROI từng lệnh = 251–298. Nút cổ thật là **tỉ số tín/nhiễu**: biên độ
  nhiễu ngày 0.187%/ngày so với hiệu ứng 3pp ⇒ tín/nhiễu trên 1 năm = 0.84 ⇒ cần ~11 năm. Không
  cần khái niệm "số khối".
- **SAI**: "thêm symbol tăng số cược độc lập" (viết ở dưới, và trong `CI_REAUDIT` mục 5 + `PREREG_GS`
  §12.4). Đo được: 4.88→30 vị thế (6.1×) chỉ mua 1.48× số cược ⇒ sd giảm 1.22× ⇒ MDE80 7.66→6.31pp;
  vô hạn vị thế 1.275×. **Không bao giờ là √N** vì ICC(ROI, cohort ngày) = +0.247 ⇒ trần 1/ICC =
  **4.05 cược độc lập** dù giữ bao nhiêu vị thế (⚠️ số 0.247 này là của **C2b**; T170 = 0.0516/trần
  19.4 — xem đính chính đầu file). Crypto đi theo BTC, đúng như nghi ngờ (nhưng với T170, TASK2 đã
  đo trực tiếp và bác bỏ: hedge triệt beta nhưng KHÔNG giảm ICC).
- **Phụ thuộc chuỗi lợi nhuận ngày là ÂM** (φ₁ = −0.04…−0.34) ⇒ rút ngắn khối là **tự trừng phạt**
  (CI rộng ra), không phải nới. Politis–White: khối hợp lệ = 3 ngày (exit-param) / 10 ngày
  (selector). Cổng kiểm phủ (coverage) xác nhận khối 21 ngày cũ **vẫn hợp lệ** (.932–.954), chỉ
  hơi hẹp quá 4–7% ⇒ **không mở lại verdict nào**.
- ⚠️ Lỗ hổng NBETS tự khai: **chưa kiểm phủ cho nhóm tick/xếp hạng**; nhãn cửa sổ 72h ở đó là phụ
  thuộc DƯƠNG ⇒ CI của rank-IC #7/#8 **có thể đang hẹp quá**. Cần kiểm trước khi dựa nặng vào chúng.

## Time-stop KHÔNG mua power (đo trực tiếp, cùng L=7)

D1 (96/168/336h): MDE80 26.42/27.29/27.84pp — giảm tối đa 5.1% < ngưỡng 25%. `L_PW` **giảm** khi
time-stop tăng (ngược giả thiết); median giờ giữ thật chỉ **4–20h**, time-stop chỉ là trần của đuôi.

## Lever KHÔNG ai nêu mà số liệu chỉ ra: 62.5% thời gian vốn KHÔNG làm gì

C2b giữ **1.83 vị thế trung bình**, 62.5% số giờ không giữ gì (max 29), `NO_BUDGET = 0`. Ràng buộc
binding là **gate MOM15** (`GATE_REJECT` 94.5% phút-ứng-viên — `TICKLOG_RESULT`). Đây là chỗ đáng
động nhất theo bằng chứng, NHƯNG đo nó ở tầng equity thì vô vọng (trên) ⇒ phải đo ở tầng xếp hạng.
(Lưu ý 09-20: T170 còn cực đoan hơn — chỉ 105/1644 ngày có lệnh vào, k̄=3.55 — cùng họ hiện tượng.)

## Đường 1 — THÊM DỮ LIỆU: đã đo, KHÔNG đủ

metrics (6 cột OI) chỉ có từ **2021-12-01** (2020-09 riêng BTC); kline/funding từ 2019-12/2020-01.
Giữ OI thì chỉ lùi thêm 31 ngày. Tối đa mọi byte (6 năm): MDE80 4.64pp (exit) — không đạt 3pp.

## Đường 2 — LOG QUYẾT ĐỊNH TỪNG TICK: đã cài, KHÔNG mua được power

`TickDecisionLog` (`4074f8c`), 2/2 cổng byte-identity PASS, 97 MiB/run, sim +56%. MDE80 tầng tick
3.400 vs equity cùng khối 72h 4.023 ⇒ 0.845 = không cải thiện. Giá trị còn lại: **chẩn đoán** (phát
hiện gate binding 94.5% ở trên). §12.4 đường "xuất log từng tick" **ĐÃ CHẾT**.

## Feature: đã sàng có kỷ luật, KHÔNG có thông tin mới (case c)

`PREREG_FS` N=16 (15 thật + 1 nhiễu), 5 nhóm chưa từng có trong S1, tất cả chỉ cần kline 1h+funding.
**0/16 vượt ngưỡng** `sqrt(2 ln 16)=2.3548 × sd_boot`. Đối chứng nhiễu PASS. 3 ứng viên **có hại đo
được**. Lead duy nhất `fs_wick_up_7d` (46% ngưỡng, đổi dấu trên 2024H1). ⇒ khoảng trống 80% tới trần
oracle **không nằm** ở feature suy từ giá/volume/funding lưới giờ; ở order book / trade-by-trade /
cross-exchange, hoặc ở cách đặt bài toán (timing/exit, không phải selection).

## Ba quy tắc hạ tầng mới, bắt buộc

1. **Đo rankIC/rho phải CPU, KHÔNG GPU.** `XGBRanker(device="cuda")` không tái lập CPU (spearman
   0.9855); nhiễu rank-IC theo tick 0.0184 lớn hơn mọi hiệu ứng đang tìm; trên GPU có 2 ứng viên
   vượt ngưỡng GIẢ.
2. **Kaggle CPU ≠ Oracle CPU** (cùng xgboost 3.2.0): 0.17040 vs 0.1723. Phép so ghép cặp phải cùng
   một môi trường.
3. **Tập ~51 khối 72h (2024H1) KHÔNG có sức phân biệt**: đối chứng seed vô thông tin cũng vượt
   ngưỡng. Đừng dùng làm tập xác nhận cho phép so train-lại.

## GS wave-1: phán quyết (b), giả thuyết HPO bị BÁC

Neo `id=-1` = **60395** ⇒ không VOID. 115/256 điểm hợp lệ. argmax NS (id=149, 21.13%) ≠ argmax CAGR
(id=127, 53.61%, hạng NS 11) ⇒ cơ chế lấy tâm plateau đúng. 0/5 finalist vượt ngưỡng đã siết ⇒ (b),
**không** đọc thành "C2b tốt nhất". Wave 1 không lấy mẫu lân cận C2b (cách 0.733 > bán kính 1.002).
Phân rã phương sai (CV R² 0.373): 3 chiều mạnh nhất `SIM_F_BASE` 0.50 · `RATE_PROFIT_STOP_MARKET`
0.45 · `DCA_GRID_SCALE` 0.28 **đều là trục đòn đẩy/size**, `SELECTOR_RANK_TOPK` hạng 6/15 ⇒ **không
chiều tín hiệu nào bị HPO che** ⇒ giả thuyết HPO **bị bác**. Không gian tham số chỉ có 1 đòn bẩy
mạnh là size, và nó đổi maxDD lấy CAGR (điểm CAGR cao nhất đều maxDD −22..−23%).

## G015: bins đang deploy KHÔNG tái lập được, train lại thì TỐT HƠN

Tái lập `full45` FAIL: rho **0.18900** vs mốc **0.1675**; d ghép cặp −0.02147 CI [−0.0383,−0.0047]
loại 0 ⇒ **bins deploy kém hơn bản train lại**. Nguyên nhân đo được: file Tool1 2021 mtime 2026-08-16
SAU khi bins sinh 2026-08-14 ⇒ bins train trên bản export không còn tồn tại. **Mốc 0.1675 không tái
lập được.** Bỏ OI: **không kết luận được** theo pre-reg, nhưng đọc không-pre-reg thì bỏ không mất gì
(`no_oi` 0.18934, đơn điệu 20/20); không nhóm nào trong 4 nhóm là cần ⇒ 45 feature đặc tả thừa nặng.
Cắt từng feature rất có thể đo được (k·sd 0.0014–0.0060 hẹp hơn CI hai-model-độc-lập 4.5–20 lần).
⚠️ Train lại G015 đổi admit-rate 3–3.7× ⇒ thay đổi cả hệ, phải hiệu chuẩn lại ngưỡng + sinh lại bins.
⚠️ **G015 KHÔNG phải model của C2b.** C2b dùng **S1** (`predwf_map_s1a2`) làm selector+gate
(`profiles/c2b.properties:23`); G015 chỉ ở tầng phân tích ledger. Provenance byte-identical đã ghim
cho **đúng model của C2b là S1** — mục kế.

⚠️ **PHÂN BIỆT G015x26 vs G015_v2/p_g015 (BẢO TỒN 2026-09-04):** câu "G015 chỉ ở tầng ledger" ở trên
nói về **G015_v2 / p_g015** (bản tái lập rho 0.18991, file đầu `aed0732c...`, dùng phân tích/tương
lai). KHÁC hẳn **`predwf_G015x26/`** (file đầu `199ad42e...`, 16 file, ~888 MiB): đó là **phân phối
gate P(win) THẬT của C2b**. `build_map.py:28` lấy G015x26 làm INPUT và **GIỮ NGUYÊN multiset P(win)
per-tick** khi sinh S1 bins ⇒ S1 quyết **thứ hạng**, G015x26 quyết **giá trị gate**. G015x26 **KHÔNG
tái lập được** (export Tool1 2021 mất, bins mtime 2026-08-14 trước export 2021 sinh lại 2026-08-16)
nhưng đã **ĐÓNG BĂNG + backup**: manifest 16 file co-located + Kaggle PRIVATE
**`chuyendinh/predwf-g015x26-gate`** (v1), verify tải-lại-so-hash **PASS**. Provenance:
`docs/G015X26_PROVENANCE.md` + trio `docs/C2B_PROVENANCE.md`. **KHÔNG được xoá `predwf_G015x26/`** —
mất nó (cả deploy lẫn backup) = mất gate C2b vĩnh viễn. ⇒ C2b bảo tồn+verify được toàn bộ nhưng
**không dựng lại 100% từ source** vì thành phần gate này.

## S1 (đúng model của C2b): provenance BYTE-IDENTICAL đã ghim (2026-09-04)

Điều phối từng cho một agent ghim provenance NHẦM sang G015; đã sửa. S1 = `predwf_map_s1a2` là
selector+gate thật của C2b. Rebuild 2 lần CPU độc lập từ input ghim (`s1_rank.py`→`build_map.py`,
PREREG `docs/PREREG_S1PROV.md` @ `020be5b`, kết quả `docs/S1_PROVENANCE.md` @ `1f7a1bf`):
**bins byte-identical 10/10 fold giữa r1==r2==deploy==backup Kaggle** (`chuyendinh/predwf-map-s1a2-bins`);
aggregate `bins.sha256=0f8721558fbd87ef...` khớp bản ghi cũ; edge5 +6.8043%; spearman(pred, deploy)=1.0,
0 lệch thứ hạng. **Lỗ `cand_dev` (build lại 09-03) ĐÃ ĐÓNG bằng bằng chứng** — cand_dev hiện tại sinh
bins trùng byte deploy nên đồng nhất thứ hạng với bản 09-02 (bins chỉ phụ thuộc thứ hạng). Input ghim
sha256, digest `ca1d262d...`; OI sạch `e3887f63...` KHÔNG rebuild; đo trên CPU (GPU cấm cho rankIC).
Lý do cắt 40→9 KHÔNG tái lập được (`PROCESS_LOG.md` chưa vào git) — 9 feature là dữ kiện; forward-test
`FS_RESULT` 0/16 thay cho văn bản đã mất. Đây là NỀN cho việc cắt feature / thêm nguồn dữ liệu sau.

## B4 rolling gate: đóng theo cách đọc (b)

Cổng byte-identity PASS. 3/3 đạt maxDD và **không tệ hơn C2b** ⇒ nhãn "EV âm" cũ **rút**. Nhưng 0/3
vượt ngưỡng, cả 3 điểm ước lượng âm; RG97 ở tầng từng-lệnh còn kém hơn C2b. Bear 2022 cả 3 âm ⇒
"thích nghi chế độ" không được ủng hộ. Cơ chế 149 dòng giờ là cờ trơ — Uni chốt giữ hay revert.

## HỆ QUẢ CHO KẾ HOẠCH (Uni đã chọn: đo số cược độc lập trước — ĐÃ XONG, ra KHÔNG)

1. **Ngừng quét tham số** (không gian chỉ có đòn bẩy size), **ngừng tìm feature giá/volume/funding
   lưới giờ** (0/16), **ngừng mọi thí nghiệm quyết-định-ở-tầng-equity** (NBETS: không đo được 3pp).
2. Tầng equity chỉ còn giữ **maxDD làm ràng buộc cứng**.
3. Quyết định chuyển hẳn về **tầng xếp hạng**. Chỗ đáng động nhất: **gate** (binding 94.5%) và
   **G015** (không tái lập + kém hơn bản train lại + đặc tả thừa nặng) — nhưng cải thiện rho KHÔNG
   tự chứng minh thành cải thiện equity, và train lại đổi admit-rate 3–3.7× = thay đổi cả hệ ⇒ để
   Uni quyết trước khi đụng.
4. Ngoài dữ liệu hiện có: order book / trade-by-trade / cross-exchange là nguồn thông tin duy nhất
   chưa thử; hoặc tích cược thật qua shadow live theo thời gian thực (chậm nhưng là cách duy nhất
   số cược độc lập tăng thật).
5. **09-20 (T170)**: hướng "tăng số cược độc lập bằng hedge BTC" đã đo trực tiếp trên incumbent thật
   và NULL (xem đính chính đầu file + `round_2026-09-20...md`). Hướng còn sống cho T170 cụ thể:
   **tăng k̄ vị thế đồng thời / tần suất vào lệnh** (105/1644 ngày có lệnh, k̄=3.55) — chưa PREREG.

## 🔵 BỔ SUNG 2026-09-20 (TASK C close-out) — trạng thái vòng bigdown/pacing kế tiếp

Sau round 09-20 (xem `round_2026-09-20_beta_decomp_and_data_survey.md` đầy đủ): TASK1
(`ANALYSIS_BETA_DECOMP_T170.md`) kết luận **T170 chủ yếu ALPHA** (%beta=3.9%, |t(α)|=4.372).
TASK2 Phương án A (`RESULT_HEDGE_OVERLAY_A.md`) = **NULL** (đã tóm tắt ở đính chính đầu file);
Phương án B hedge Java **KHÔNG làm** (chi phí/rủi ro quá cao so với thông tin thu được, r²=0.031
đã đủ để đóng hướng). TASK5 vol-target (`RESULT_VOL_TARGET.md`) COIN/PORTFOLIO đều **NULL** ở rate
chất lượng; COIN cải thiện rủi ro thật, PORTFOLIO làm xấu đi (do chọn target-vol cao hơn vol tự
nhiên — lỗi tham số, không phải bug). Uni redirect sang trục **bigdown = nhân tố đồng-thua** +
**pacing động thay gate fix cứng** (xem `TASKS_2026-09-20b_bet_structure_and_closeout.md`,
copy tại `tasks/` trong repo) — TASK A/A-recon/B ở vòng đó là hướng power tiếp theo cho T170, đo
tần suất vào lệnh / k̄ vị thế đồng thời chứ không phải hedge-beta. Shadow-c3 production DOWN
09-20 06:13 (jar cũ mang STUB API key) → **ĐÃ KHÔI PHỤC 09-20 22:06** (rebuild+redeploy, không
sửa file repo).

## 🔴 HƯỚNG BREADTH (hạ gate lấy breadth) — ĐÓNG 2026-09-21 sau 5 round

Thực hiện đúng hướng "tăng k̄/tần suất" đề ra ở mục 5 ngay trên (hạ `SIM_GATE_DYN_SCALE` từ 1.70 để
lấy thêm breadth), nhưng theo 5 round độc lập đều NULL/NO-GO:

1. **TASK B (pacing-size P0/P3 trên gate 1.0, `0ca2c62`, PREREG `aa3c4aa`)**: giảm size khi bigdown
   đạt breadth dễ dàng (n_eff ×1.74-1.80) nhưng KHÔNG kéo được UW về khẩu vị (cả hai vỡ 2025,
   UW>200) — pacing theo kích thước chỉ sửa maxDD, không sửa UW (tần suất/thời gian dưới nước).
2. **B2 Bước 2 (regime-adaptive gate MA200-trailing, `54d9cdb`, PREREG `9c5b74d`)**: cơ chế sửa
   ĐÚNG UW-nguồn-2022 (khớp T170 gần tuyệt đối năm đó) nhưng vỡ khẩu vị vì 2025 — tồn tại nguồn UW
   dài thứ hai, độc lập với xu hướng BTC, mà regime macro không bắt được.
3. **B2 Bước 3 (drawdown-throttle nội tại, `50f7ff0`, PREREG `0d3eb51`)**: giảm đúng maxDD như dự
   báo nhưng UW **TĂNG 34%** (248→332 ngày) so với chính nền nó chạy trên — xác nhận đúng dự báo
   MASTER: giảm phơi nhiễm lúc dưới nước = phục hồi chậm hơn = UW không giảm.
4. **B2 Bước 4 (up-gate chặt hơn: RA12 khoá, `dccba82`, PREREG `ba3d7ba`)**: chỉ đạt 1/5 tiêu chí;
   RA14 (sweep mô tả, không phải ứng viên) là biến thể DUY NHẤT PASS khẩu vị 5/5 năm nhưng bị
   luật chống overfit khoá trước khi chạy (cấm mở biến thể quanh winner sau khi thấy kết quả) —
   không được dùng để thay RA12 làm quyết định.
5. **B2 Bước 5.1 (trend-detector SMA7/100, `64285c1`, PREREG `3e3aa88`)**: NO-GO ở khâu coverage
   (chỉ phân loại được 19.8% ngày, dưới ngưỡng tối thiểu 60% để tin số liệu) — không tới được
   bước đo hiệu năng.

**Kết luận cơ chế**: breadth CÓ alpha thật (CAGR round breadth-improvement dao động 31-34%, cao hơn
T170 29.27%) nhưng UW (thời gian dưới nước) là nút thắt NỘI TẠI của hướng long-only-breadth trên
crypto — không phải lỗi thiết kế phòng thủ có thể vá. Ba thiết kế phòng thủ ĐỘC LẬP về cơ chế
(giảm-đều theo bigdown / theo-regime BTC-macro / theo-drawdown-nội-tại) đều thất bại CÙNG MỘT LÝ DO:
giảm phơi nhiễm khi đang thua = phục hồi chậm hơn = UW không giảm (hoặc tăng). Không cơ chế phơi
nhiễm nào đo được phá vỡ trade-off breadth↔UW trong 5 round độc lập này.

RA14 (up=1.4, PASS khẩu vị 5/5 năm ở B2 Bước 4) là ứng viên "đẹp" nhất về số nhưng **KHÔNG được
chọn thẳng từ số DEV** theo đúng luật chống overfit — nếu muốn theo đuổi lại, phải chờ một
round PREREG riêng, có shadow-forward/holdout xác nhận trước, không được suy ra ngược từ kết quả
đã thấy.

**Hạ tầng để lại (dùng lại được, cổng OFF byte-identical PASS, md5 `efb793e2468ca3a7318da0f0ad23d4fc`
xuyên suốt cả 5 round)**: `GATE_REGIME_ADAPTIVE`/`RegimeSchedule`/`SIM_REGIME_SCALE_UP` (regime
BTC-vs-MA200-trailing, đọc CSV ngoài, causal), `PacingSizing.java` (mode `OFF|P0|P3|DT`, cắm được
thêm mode mới không đổi đường OFF), script sinh CSV regime MA200. Không xoá, không revert — có thể
tái sử dụng cho hướng khác (ví dụ sizing/risk-management) dù hướng breadth đã đóng.

**Chuyển sang TASK D (alpha event-trigger mới, độc lập cơ chế với breadth/MOM15)**: Bước 1 recon
(`docs/RECON_EVENT_ALPHA.md`, `5b97a07`) đã xong — nguồn listing/delisting (Binance Announcement
Archive + `claudedata/universe_birth_death.csv` nội bộ), verdict **GO** cho nhánh listing (causal-safe,
648 event/4.5 năm, độc lập MOM15 đo thật 0/709 cặp (symbol,tháng) trùng T170 entry). Quyết định của
Uni, 2026-09-21.
