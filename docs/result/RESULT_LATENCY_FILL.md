# RESULT_LATENCY_FILL — ĐỘ TRỄ + GIÁ KHỚP vs NẾN QUYẾT ĐỊNH ⇒ (a) LỆCH MỐC ĐO, KHÔNG BIAS

Ngày: **2026-09-29** (D6, `AUDIT_OPENCLAW_RESET_20260929` §1.1). Pre-reg: **`docs/prereg/PREREG_LATENCY_FILL.md`**
(commit **`c6749bf`**, chốt **TRƯỚC**; sau đó **không sửa thiết kế**). Script: `research/analysis/latency_fill.py`
(+ helper deserialize `research/live_fills_audit/OrderIntentDump.java`). JSON: `docs/result/latency_fill.json`.

**Tuân thủ:** **0 sim** · **đọc 242 READ-ONLY** (`ssh -p 2222 -i ~/.ssh/id_rsa_chuyennd root@103.157.218.242`) —
chỉ `logs/` + `storage/data/order/`, KHÔNG ghi/sửa/restart/kill, KHÔNG đọc key/secret, copy về Oracle rồi xử lý ·
thuần Python + 1 helper Java deserialize (KHÔNG phải sim) · **KHÔNG push dữ liệu** · `nice -n 10`.

---

## 0. KẾT LUẬN (một dòng)

> **`+1,675 %/chân` (n=37) của `RESULT_COST_TRUTH` là LỆCH MỐC ĐO (a), KHÔNG có bias**: nó so fill với **close của NẾN
> CHỨA FILL** (nến đỏ, sập xảy ra **SAU khi vào**), trong khi mốc đúng là **close của NẾN QUYẾT ĐỊNH** (nến sim dùng).
> Đo lại đúng mốc: `slip_dec` nhóm sập **+0,693 %/chân, CI95 `[−0,187, +1,497]` CHỨA 0** (n=27). Đối chiếu trực tiếp
> 37 chân "fill-candle-crash": `s_close = +1,680 %` (tái lập +1,675) nhưng **`slip_dec = −0,208 %` ≈ 0**, và nến quyết
> định của chúng **+0,34 % (không đỏ)**. **Latency thật median ~7 s (max 37 s) ≠ 228 s.** ⇒ **(a)**; **KHÔNG rescore**,
> **KHÔNG có chi phí latency/look-ahead cần cộng thêm** vào base `0,112 %/vòng`.

---

## 1. DỮ LIỆU + KHỚP (đúng pre-reg §1–§3)

- **224 lệnh BUY-entry** (side=BUY, reduceOnly=False) → khớp **218** intent `OrderTargetInfo` (6 UNMATCHED: fill sau
  20260912 khi hết file intent, hoặc ngoài cửa sổ 1 h).
- **`level` thật** (từ `OrderTargetInfo.marketLevel`, deserialize Snappy+Java-serialization): **`PREDICT_SYMBOL_TRADE 197` ·
  `DCA_LEVEL1 21` · `BIG_DOWN 0`** (live giai đoạn này KHÔNG phát lệnh BIG_DOWN — không có nhóm để đo).
- Đơn vị = **lệnh** (1 lệnh = 1 chân VÀO), gom fill theo `orderId` lấy giá bình quân (khác `RESULT_COST_TRUTH` đếm theo fill).
- `slip_dec = (fill − close(nến quyết định))/close` (BUY, dương = bất lợi); `latency = t_fill − (close nến quyết định)`.

## 2. SỐ CHÍNH — `slip_dec` theo ĐỘ SẬP NẾN QUYẾT ĐỊNH

CI = block-72h · 2000 rep · seed `20260905` · `inflate(k=2)=1,1774` (%/chân):

| nhóm (nến quyết định) | n | mean % | median % | CI95 (infl2) % | latency mean/med (s) | bar_ret % |
|---|---|---|---|---|---|---|
| **sập** (`bar_ret ≤ −1 %`) | 27 | **+0,693** | +0,337 | **[−0,187, +1,497]** | 12,2 / 7,2 | −1,77 |
| không sập (`bar_ret > −1 %`) | 191 | +0,081 | +0,024 | [−0,023, +0,175] | 14,0 / 7,1 | +0,30 |

- **Nhóm sập: CI CHỨA 0** (mean +0,69 %, nhưng CI `[−0,19, +1,50]` bao 0) ⇒ **theo LUẬT KẾT LUẬN ⇒ (a) lệch mốc đo**.
- Độ nhạy `inflate(5)=1,7941` (đối chiếu convention `RESULT_COST_TRUTH`): CI `[−0,648, +1,919]` — càng chứa 0.
- Latency hai nhóm **gần như nhau** (med ~7 s) ⇒ không phải latency tạo ra chênh lệch; chênh mean còn lại là nhiễu.
- `ρ_spearman(latency, slip_dec)` nhóm sập = **+0,248** (pearson +0,332) — dưới ngưỡng "tăng theo latency" (0,3) đã chốt;
  binned theo median latency: `≤med +0,319 %` vs `>med +1,095 %` — xu hướng yếu, không đủ để lật (a).

## 3. ĐỐI CHIẾU TRỰC TIẾP VỚI `RESULT_COST_TRUTH` (bằng chứng quyết định)

Lấy đúng tập **37 fill "fill-candle-crash"** (định nghĩa `BIG_DOWN proxy` của `RESULT_COST_TRUTH`: nến CHỨA fill có
`bar_ret ≤ −1 %`), đo lại 3 thước:

| thước | ý nghĩa | giá trị |
|---|---|---|
| `s_close` | (fill − close **nến chứa fill**)/close | **+1,680 %** — tái lập đúng `+1,675 %` của `RESULT_COST_TRUTH` |
| `slip_dec` | (fill − close **nến QUYẾT ĐỊNH**)/close | **−0,208 % ≈ 0** (đúng mốc sim) |
| `dec_bar` | độ sập của **nến QUYẾT ĐỊNH** (trung bình) | **+0,34 %** — nến quyết định **KHÔNG đỏ** |

**Đọc:** với 37 chân này, nến quyết định **trung bình xanh nhẹ** (+0,34 %); chỉ **9/37** có nến quyết định đỏ ≤ −1 %.
Fill khớp tại **open của nến kế tiếp** (sau nến quyết định), rồi **nến kế tiếp mới sập** (bar_ret ≤ −1 %). So fill với
**close nến đỏ kế tiếp** ⇒ +1,68 % (đo nhầm cú sập xảy ra **SAU khi vào**); so fill với **close nến quyết định** ⇒
**−0,21 % ≈ 0**. ⇒ **+1,675 % là artifact mốc đo, không phải chi phí entry.**

## 4. LATENCY THẬT — KHÔNG CÓ "~228 s"

`latency = t_fill − (close nến quyết định)` (mốc sim): **min 6,6 · p25 6,9 · median 7,2 · p75 25,3 · p90 27,8 · max 37 s**.
**0 chân > 60 s**; chỉ **12/218** > 30 s. Scan selector chạy tại mốc lưới 15' (log `Market level:` :14/:29/:44/:59),
đọc nến 1m vừa đóng, fill ngay trong ~7 s (queue + market order). ⇒ giả thuyết "một lượt quét ~228 s làm khớp muộn"
**(b) KHÔNG được dữ liệu xác nhận** — latency thực tế nhỏ hơn ~30×.

## 5. THEO `level` THẬT (mô tả, CI `inflate(3)=1,4823`)

| level | n | mean slip_dec % | CI95 (infl3) % | ghi chú |
|---|---|---|---|---|
| `PREDICT_SYMBOL_TRADE` | 197 | +0,040 | [−0,056, +0,142] | ≈ 0 |
| `DCA_LEVEL1` | 21 | **+1,254** | **[+1,254, +1,254]** (thoái hoá) | **21/21 trong 1 block 72h** (một cú sập 2026-08-22 05:14–05:45) ⇒ **1 episode**, CI không xác định, chỉ mô tả |
| `BIG_DOWN` | **0** | — | — | live không phát BIG_DOWN trong cửa sổ |

- **DCA +1,254 % là NHIỄU 1-episode** (n=21 gom hết trong một cú sập thị trường 2026-08-22), không phải hiệu ứng bền;
  không dùng làm phạt.

## 6. TRẢ LỜI CÂU HỎI (bắt buộc)

1. **`+1,675 %` là gì?** **(a) lệch mốc đo.** So fill với close nến CHỨA fill (đỏ) thay vì close nến QUYẾT ĐỊNH.
   Đo lại đúng mốc: **−0,21 %** (tập 37) / **+0,69 % CI chứa 0** (tập 27 theo nến quyết định).
2. **Có latency thật không?** **KHÔNG đáng kể.** median ~7 s (max 37 s), ≠ 228 s; `ρ(latency, slip_dec)` +0,25 (yếu),
   và nhóm sập CI chứa 0.
3. **Có look-ahead thật của sim không?** **KHÔNG.** nến quyết định của các chân "sập" trung bình **xanh nhẹ (+0,34 %)**,
   fill khớp ngay sau close ⇒ sim vào ở close nến quyết định là **đúng mốc khả thi**, không lạc quan có hệ thống.
4. **Cần rescore R0/R4 với phạt slip?** **KHÔNG** (luật: chỉ khi (b) hoặc (c)). **Giữ nguyên `base 0,112 %/vòng`** —
   không cộng thêm chi phí latency/look-ahead vào leg sập.

## 7. HẠN CHẾ (khai rõ)

1. `BIG_DOWN` **vắng mặt** trong intent live (0 lệnh) ⇒ không đo được slip_dec riêng cho BIG_DOWN; kết luận (a) dựa trên
   trục "độ sập nến quyết định" (đúng pre-reg §4).
2. `DCA_LEVEL1` n=21 **gom trong 1 block 72h** (một cú sập 2026-08-22) ⇒ CI thoái hoá, chỉ mô tả.
3. 6/224 lệnh UNMATCHED (fill sau 20260912 hết file intent, hoặc ngoài cửa sổ 1 h) — loại khỏi CI, báo n.
4. `latency` đo từ `t_fill − (close nến quyết định)` (mốc sim), bỏ ~3–10 s hằng số giữa close và "Push redis" (không đổi
   kết luận tương đối).
5. `slip_dec` dùng giá bình quân (weighted), không mô phỏng spread/impact nội phút; 119/2850 file intent (20260424–0505)
   trước cửa sổ fill, không ảnh hưởng.
6. Mọi số mô tả quá khứ (live 2026-06→09, sim DEV ≤ 2025-12-31), không cam kết forward.

## 8. TÁI LẬP

```bash
cd /home/ubuntu/src/BinanceFuturesJava
# 1) copy intent từ 242 (đọc-only) về Oracle, deserialize:
#    java -cp ".:target/binance-java-sdk-1.2.4.jar:$HOME/.m2/repository/org/xerial/snappy/snappy-java/1.1.10.1/snappy-java-1.1.10.1.jar" \
#      research/live_fills_audit/OrderIntentDump.java  # (javac trước) -> orders_dump.csv
# 2) phân tích (0 sim):
python3 research/analysis/latency_fill.py --orders /home/ubuntu/latency_fill/orders_dump.csv --json docs/result/latency_fill.json
```

## 9. COMMIT

- Pre-reg: **`c6749bf`** (`docs/prereg/PREREG_LATENCY_FILL.md`).
- Kết quả: commit này (`RESULT_LATENCY_FILL.md` + `latency_fill.json` + `latency_fill.py` + `OrderIntentDump.java`).
