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
