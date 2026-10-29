# PREREG_HO2026_NOTF — ADDENDUM TECH (2026-10-28)

Prereg gốc: `docs/prereg/PREREG_HO2026_NOTF.md` (96164b72). Addendum này KHÔNG đổi X, cấu hình, seed, thước hay luật D1–D5. Nó chỉ ghi cách hiện thực và những chỗ phải diễn giải. Viết và commit TRƯỚC khi đẩy kernel đầu tiên. Chưa có số nào.

## T1. Jar
- **Exporter (STUB):** build từ `git archive 0594986e`, chép `PrivateConfig.java` STUB (3 hằng, đều rỗng) vào, rồi `mvn -o -DskipTests package`. Kết quả sha256 `a485880cf329ae043b03608faa827f39f1a1baf5c6043308bf526b0735c65167`.
  - `jar_sec_check` ok=true: other 0, max run 44, com/binance 0.
  - Upload thành dataset mới `ho2026-notf-jar-exp`. Orchestrator chạy lại sec check ngay trước upload và assert ok.
- **So với jar 99c5f040** (bản sao dataset `ho4p1-jar-exp`, sec check FAIL, KHÔNG dùng): 7 572/7 572 class. Có 3 class khác md5:
  - `PrivateConfig`;
  - `client/BinanceFuturesClientSingleton` và `client/ClientSingleton`. Lý do là javac inline hằng `static final String` của PrivateConfig vào hai class này.
  - `javap -c -p` sau khi che hằng chuỗi: hai class chỉ khác ở các dòng `ldc … // String` (rỗng so với có giá trị) và độ rộng cột. Không khác lệnh nào.
  - Đây là **lệch chữ** so với prereg §4 ("chỉ PrivateConfig*.class"). Kết luận: tương đương về hành vi, vì hai class client chỉ dùng cho REST và exporter không gọi. Cổng A0'(a) kiểm trực tiếp trên đầu ra.
- **Sim:** dataset `sim-jar-tsx`, sha256 `cc0f9d11…`, sec check ok=true. Dùng cho cả k24-s, k24-b, x14.

## T2. Kernel (tài khoản chuyendinh, tối đa 5 kernel song song toàn tài khoản)
- **Cổng A0':**
  - `a0p-x26-q1`: cfg = `cfg_ho4p1-x26-q1.json`, chỉ đổi tag và jar. So `MANIFEST.json` với `ho4p1-x26-q1` (137 file).
  - `a0p-k24-s-s42`, `a0p-k24-b-s42`, `a0p-x14-s42`: artefact gốc (`ho4p1-chain-y26`, `ho4p1-tk26`, bundle, pred), cờ X14 gốc 15 ngày. md5 printDone phải khớp ba giá trị ở prereg §4.
- **Dữ liệu A1:**
  - `nt-x26-q{1,2,3}`: cfg gốc từng quý + `exclude` (X, assert md5 trong kernel); `in_uni` thêm `s not in EXCL`.
  - `nt-tk26`: copy 273 ngày, như `ho4p1_stage.tk26`.
  - `nt-chain-y26`: `ho4p1_chain.py` (md5 5ec798f7) có chèn sau `DUP_IDS`: id mapper của X được hợp vào tập id loại. Kernel assert không id nào của X dùng chung với crypto. OI nguồn `ho4p1-oi-a`.
  - `nt-v1` (V1): kiểm trên 12 ngày (01-15, 02-05, 02-28, 03-15, 04-20, 05-10, 06-02, 06-20, 07-10, 08-05, 09-01, 09-30), xem T3.
- **Diễn giải "kernel A1" ở prereg §4** = 24 kernel sim `nt-*`, đúng như lệnh MASTER: "only if it passes, launch the 24 A1 kernels". Kernel dựng dữ liệu (`nt-x26-*`, `nt-tk26`, `nt-chain-y26`, `nt-v1`) chạy song song với cổng vì không sinh số chiến lược nào. Sim `nt-*` chỉ được đẩy khi đủ ba điều kiện: cổng (a) và (b) PASS, V1 PASS, `arts_nt.json` có.
- **Sim A1:** 24 kernel `nt-{k24-s,k24-b,x14}-s<seed>` qua `ho4p1_queue.push`, tức template, override, guard và FUND giữ nguyên. Thay CHAIN/TKK/ARTS bằng `nt-chain-y26`/`nt-tk26`/`arts_nt.json` và `bins_md5` mới.
  - Cờ x14 A1: `20260205-20260214,20260216-20260217,20260224-20260225,20260606-20260607,20260610-20260611`.
- **Chạy lại:** đúng như prereg, một lần khi lỗi hạ tầng, cfg y hệt.
- **Orchestrator:** `research/ho2026_notf/notf_orch.py`; state `~/claude_master/ho_tradfi_wk/notf_state.json`; log `orch.log`.

## T3. Hiện thực validate
- **V1:**
  - (i) `universe_by_month.json` của 3 kernel `nt-x26` ∩ X = ∅ ở mọi tháng;
  - (ii) md5 raw ticker `nt-tk26` = exporter, 273/273;
  - (iii) kernel `nt-v1` trên 12 ngày: 0 ô X; tập phút bằng nhau; mọi ô (sym, phút) ngoài X bằng nhau với `ho4p1-tk26`.
- **V2:** chuỗi cờ trong cfg = ranges tính từ `a2v2` noTFIDX (ALT_EW tái dựng, khớp `ew_2026.npz` 4,9e-17 khi không loại gì).
- **V3:** 0 leg ∈ X trong printDone A1.
- **V5:** `ho4p1_queue.check` (jar tsx, override, pred md5 A1, `TICKER_HO4P1 ok=273…`, FUND, mapper, penalty, UNSEAL). x14 có `[TSX] extHours=336`; k24 không có. Thêm: các dòng printDone có start < 20251224 trùng với run gốc cùng seed và phí (đoạn DEV không đổi).
- **V4:** self-check của scorer gốc.

## T4. ADDENDUM_TECH-2 (2026-10-28 08:45, TRƯỚC khi đẩy kernel sim A1 nào) — sửa hạ tầng jar sim

- **Kết quả cổng A0'(b), lần chạy 1** (tất cả dùng jar tsx):
  - `a0p-k24-b-s42`: md5 `7cc8864c` = ho4-k24-b-s42 ✔.
  - `a0p-x14-s42`: md5 `bb609455` = tsx-ho-x14-s42 ✔.
  - `a0p-k24-s-s42`: md5 `7cc8864c`, tức chính là kết quả **k24-b**, và parity `pen=False`. Nguyên nhân: jar tsx cc0f9d11 **không có** key `SIM_CRASH_ENTRY_PENALTY` (`Configs.class` không chứa chuỗi này), nên bản stress chạy như phí gốc.
  - Kết luận: đây là **lỗi hạ tầng (sai jar), không phải bất định**. Giả định của T1 ("jar tsx dùng được cho cả 3 cấu hình") SAI với k24-s.
- **Sửa:**
  - Jar gốc b7c89f09 của ho4-* có bản sao local (`~/src_wt_nsel/target`, `~/kaggle_sim/push_jar_nsel/sim.jar`, sha khớp), nhưng **FAIL sec check** (other 3, max run 65, 3 class com/binance) ⇒ KHÔNG upload. Đã báo MASTER (giống ho4p1-jar-exp).
  - Build lại từ đúng nguồn của b7c89f09 (`df021437`, NSEL_IMPL_JOINTS §1): `git archive df021437`, PrivateConfig STUB, `mvn -o -DskipTests package`. Kết quả sha256 `877d9ffade1daac377cb6aea1f070f57de23e5b44b03cd39e024f13ae8baf883`, sec check ok=true.
  - So 7 572/7 572 class với b7c89f09: chỉ khác `PrivateConfig`, `BinanceFuturesClientSingleton`, `ClientSingleton` (hằng inline), giống T1.
  - Dataset mới `ho2026-notf-sim-jar`: sim.jar + `prof_r4_kg0_k16_f015_g155.properties` (bản copy từ push_jar_nsel). Orchestrator kiểm lại sec check và kiểm prof không có chuỗi ≥ 40 ký tự alnum trước khi upload.
- **Gán jar:** k24-s, k24-b (A0' và A1) dùng `ho2026-notf-sim-jar` (= nguồn jar gốc ho4-*); x14 dùng `sim-jar-tsx` (= jar gốc tsx-ho-x14).
- **Cổng A0'(b) làm lại:** `a0p2-k24-s-s42` phải ra `6989a312…`, `a0p2-k24-b-s42` phải ra `7cc8864c…`, cùng `a0p-x14-s42` đã PASS. Ba kernel `a0p-*` lần 1 giữ làm hồ sơ.
- Không đổi cấu hình, seed, X, luật hay thước.

## T5. ADDENDUM_TECH-3 (2026-10-29, TRƯỚC khi chấm bất kỳ số A1 nào)

Không đổi X, cấu hình, seed, thước hay D1–D5. Ghi lại hạ tầng thực tế và một chỗ phải diễn giải.

- **Trạng thái:** 34/34 job COMPLETE: cổng (a) 1, cổng (b) 4 kernel (1 bản tsx-jar làm hồ sơ + 3 bản đúng), dữ liệu 7 (`nt-x26-q1..3`, `nt-tk26`, `nt-chain-y26`, `nt-v1`), sim 24.
- **Cổng A0'(a):** `a0p-x26-q1` MANIFEST 137/137 file trùng md5 với `ho4p1-x26-q1`.
- **Cổng A0'(b)** (md5 printDone, so run gốc cùng seed 42):
  - `a0p2-k24-s-s42` = `6989a3128daa249372be802fb06a8c27` = `ho4-k24-s-s42` ✔ (jar STUB 877d9ffa)
  - `a0p2-k24-b-s42` = `7cc8864ca12bdd69f0165c9c9d5c74c5` = `ho4-k24-b-s42` ✔ (jar STUB 877d9ffa)
  - `a0p-x14-s42` = `bb609455e02aaf30ed8afc31342329e2` = `tsx-ho-x14-s42` ✔ (jar tsx cc0f9d11)
  - `a0p-k24-s-s42` (jar tsx, lần 1) = md5 của k24-b, `pen=False` → đúng như T4, giữ làm hồ sơ, không dùng.
- **Chạy lại hạ tầng (1 lần, cfg y hệt):** `nt-k24-b-s123` lần 1 COMPLETE nhưng file `result.json` tải về không parse được (`Expecting value: line 2 column 1`) ⇒ đẩy lại 1 lần (`pushes=2`), md5 cuối `7da38ae5e24774416ee47a8adf2ccd91`, pass. Không đổi tham số nào.
- **Bảo mật (kiểm lại trên bản tải từ Kaggle, không chỉ local):**
  - `ho2026-notf-jar-exp/sim.jar` sha256 `a485880c…`, sec ok=true;
  - `ho2026-notf-sim-jar/sim.jar` sha256 `877d9ffa…`, sec ok=true;
  - `sim-jar-tsx/sim.jar` sha256 `cc0f9d11…`, sec ok=true (7 568 class).
- **Kiểm độc lập 24 kernel A1** (metadata Kaggle + source CFG + result.json + log + printDone, script `verify_nt.py`): tất cả PASS — jar sha256 đúng theo cấu hình (k24-s/k24-b: 877d9ffa; x14: cc0f9d11), `pred_md5_used` đúng theo seed, `pred_md5_base=22f69456…`, tk `nt-tk26` md5 273/273 = exporter, chain `nt-chain-y26`, override đúng từng key (penalty 0,01675 chỉ k24-s; extHours 336 + 18 ngày chỉ x14), mapper 863, `TICKER_HO4P1 ok=273 bad=0 miss=0 extra=0 other=0`, `FUND_HO4_OK` + selfcheck, `HOLDOUT_UNSEAL DUNG`, `[CRASH-PENALTY]` đúng, `[TSX] extHours=336 extDays=18` cho x14 và không có cho k24.
- **Diễn giải V3 (nêu rõ để MASTER biết, không đổi luật):** V3 "0 leg ∈ X trong printDone A1" được đọc là **trong cửa sổ chấm A1 (2026)**. Lý do: §2 bắt buộc đoạn ≤ 2025-12-31 giữ NGUYÊN byte như chuỗi gốc, mà chuỗi gốc có leg trên DEFIUSDT/BTCDOMUSDT (INDEX, 2021–2024). Vì vậy đọc V3 theo nghĩa toàn bộ printDone sẽ mâu thuẫn với §2 và không thể đạt. Số liệu: 24/24 kernel có **0 leg X trong 2026**; leg X ngoài cửa sổ (2021–2024, DEFI/BTCDOM) giống hệt A0 cùng seed/phí (đã so từng dòng `start < 20251224`).
- **V1:** `nt-v1` ok=true, 12/12 ngày: 0 ô X trong A1, cùng tập phút, 0 ô lệch, số ô = số ô tham chiếu ngoài X; universe_by_month q1/q2/q3 ∩ X = ∅; `tk_raw_md5` 273/273 khớp exporter.
- **V2:** tái dựng độc lập ALT_EW "all" từ `a2v2` khớp `ew_2026.npz` 437 750/437 750 phút, max|Δ| 4,86e-17; noTFIDX (chỉ n_cr) cho đúng 18 ngày §2; chuỗi `SIM_LOSER_TS_EXT_DAYS` trong 8 kernel x14 = đúng 18 ngày đó.
- **Chưa chấm số A1 nào trước commit này.**
