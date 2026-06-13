# TASK-012: Export GATE label (median-alt forward return) + validate RIÊNG

- **status:** DONE — `gate_return.csv` (190 271 dòng, 2021→2026-06) trên 226 + local; 5 validate (a–e) PASS.
- **owner:** Claude Code (CCD) · **updated:** 2026-06-13
- **Spec gốc:** `docs/H1_GATE_SPEC.md` §1 (label đã CHỐT: C1=median-alt, C2=ngưỡng tuyệt đối scale-H). Đọc spec trước.

## Mục tiêu
Export **return thô** `retMktMedian(t,H)` cho gate, mỗi H ∈ {4,12,24h}, **sample mỗi 15m**, 2021→nay. **KHÔNG threshold/3-class** (việc đó ở H2). Validate riêng PASS mới sang features.

## Công thức (H1_GATE_SPEC §1.3)
```
alt = universe USDT-perp TRỪ BTC và ETH (cả 2 là "đầu tàu" → để dành FEATURE, không vào label)
với mỗi t (bước 15m), mỗi H:
  retMktMedian(t,H) = median over {sym ∈ alt : có close(t) VÀ close(t+H)} của [close_sym(t+H)/close_sym(t) − 1]
```
- `close` lấy từ `kline_1m_opt` (close phút `t` và phút `t+H`). **close-to-close, KHÔNG max/min.**
- Xuất mỗi dòng: `t, ret_4h, ret_12h, ret_24h, nCoin_4h, nCoin_12h, nCoin_24h` (số coin tham gia median mỗi H — để biết độ tin).
- ⚠️ **Look-ahead:** chỉ dùng close tại đúng `t` và `t+H`; `t+H` vượt "nay" → bỏ dòng (chưa đủ tương lai). KHÔNG dùng bất kỳ giá > `t+H`.
- "Có close tại t & t+H" tự loại coin chưa sinh / đã delist → **KHÔNG cần lifecycle (010)**.

## Lưu trữ
- File cho train Python H2 đọc: CSV `gate_return.csv` (hoặc `.bin.gz` theo convention export hiện có). Format chốt để khớp loader H2.
- Đọc client: train đọc **226** (xác nhận với read-client của H1/sim). Đọc-only.

## Validate RIÊNG — BẮT BUỘC (H1_GATE_SPEC §1.4), PASS mới sang features
- **(a) Phân bố** return mỗi H: in percentile (p1/p5/p50/p95/p99) + đếm đuôi trái (ret ≤ −15%) — phải có cú sập, không phẳng lì.
- **(b) Recompute-compare:** chọn ~5 mốc t, tính median tay bằng đường code khác → khớp retMktMedian.
- **(c) Look-ahead check:** xác nhận code chỉ chạm close ≤ t+H (đọc lại vòng tính, không lấy giá tương lai xa hơn).
- **(d) Cross-audit cú sập:** t quanh **LUNA 2022-05-09→13**, **FTT 2022-11-08→09** → `ret_24h` âm SÂU (xác nhận label bắt đúng sập). In số.
- **(e) nCoin:** cảnh báo các mốc `nCoin < 50` (universe 2021 đầu mỏng — median ít coin kém tin); báo min/median nCoin theo năm.

## An toàn
- Đọc-only `kline_1m_opt`. KHÔNG đụng live/config/trading. SLF4J.

## Acceptance
- [ ] File `gate_return.csv` (t + ret_4h/12h/24h + nCoin_*) 2021→nay, sample 15m.
- [ ] 5 validate (a–e) PASS, kèm số liệu thật (phân bố, cú sập âm sâu, nCoin theo năm).
- [ ] Look-ahead clean; recompute-compare khớp.

## (Code điền)
Tool: `ai_ml/features/export/ExportGateReturn.java` (đọc-only 226, streaming ring 96 bước-15m; alt = USDT-perp trừ BTC/ETH/USDC/BTCDOM/`_`).
- **Format + #dòng + range:** CSV `outputs/gate_return.csv` (226 + local), cột `tEpochMs,tDate,ret_4h,ret_12h,ret_24h,n_4h,n_12h,n_24h`. **190 271 dòng**, 2021-01-01 07:00 (=UTC 00:00) → ~2026-06 (bỏ 24h cuối vì t+24h>nay). Sample 15m, close-to-close.
- **(a) phân bố** (đuôi trái rộng dần theo H): 4h p1=−6.1%/p50=0/p99=+4.5%, đuôi≤−15%=97(0.05%); 12h p1=−10.1%/p99=+7.5%, đuôi=586(0.31%); 24h p1=−14.6%/p99=+10.1%, đuôi=1759(0.92%). Có cú sập, không phẳng.
- **(b/c) recompute** 7 mốc × 3 H = **21/21 KHỚP** (đọc lại close t & t+H trực tiếp); look-ahead clean (chỉ chạm t, t+H).
- **(d) LUNA/FTT:** FTT 2022-11-08 ret_24h=−13.4%, 11-09=−10.1%; LUNA 2022-05-12 ret_12h=−19.3% (24h=−6.9%, median ALT hồi phần sau). Label bắt đúng sập. Median robust ⇒ 1 coin→0 KHÔNG kéo median −99% (đúng: gate đo timing thị trường, ruin-1-coin do DCA/breaker).
- **(e) nCoin (n_24h) min/median/#(<50) theo năm:** 2021 0/110/6 · 2022 0/134/8 · 2023 0/182/2 · 2024 0/259/14 · 2025 0/432/2 · 2026 471/532/0. Lác đác mốc gap n=0 (ret trống) → H2 loader bỏ dòng trống.
- ⚠️ Ranh giới: H1 chỉ return THÔ; 3-class-hoá bằng ngưỡng X(H)/Y(H) ở **H2** (quét không re-export).
