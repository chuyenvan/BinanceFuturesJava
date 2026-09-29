# AUDIT — DEPLOY R4 LÊN SHADOW (PAPER) NHỊP 1' — 2026-09-29 — **FAIL → ROLLBACK**

Phạm vi được duyệt (owner 09-29): *"cứ test 1 phút"* + cho phép OpenClaw triển khai. Chỉ **shadow-c3**
(Oracle, paper). **KHÔNG** chạm 242 · **KHÔNG** đổi `SHADOW_NO_PUSH=true`.

## KẾT LUẬN: **FAIL → ĐÃ ROLLBACK** (shadow về nguyên trạng 28/09)

Bản deploy R4 (nhịp 1') **KHÔNG đạt tiêu chí B3** và đã **rollback** trong ~7 phút. Nguyên nhân gốc là
**xung đột CODE cấp thiết kế** giữa `SELECTOR_RANK_TOPK=16` (K của R4) và ngưỡng tối thiểu **20 coin** của
`S1RankerLive` — qua cơ chế cap trong `cascadeUniverse`. Chi tiết §4.

---

## 1. PARITY (B2 — cổng bắt buộc) — **PASS**

Jar build từ commit **`dd8d063`**, **sha256 `8d93dad97fb4e2b8cd7b54d4e2448dc413af4c5731826d7d53088f7f5b45160d`**
(`mvn -o -DskipTests package`, arm64, java 11.0.32.1). Dataset jar `chuyendinh/sim-jar-r4-1m`.

| chân | profile | md5 `printDone.csv` | yêu cầu | khớp |
|---|---|---|---|---|
| `r4-par-kg0` (KEEPLEG0) | `x1_gs_t170` + WEIGHTS 1,1,1,1 + SCALE 6.0 | `99e42b75cf1a2142f9cd14dc72e371ba` | `99e42b75…` (n1085/103083) | ✅ |
| `r4-par-t170` (T170) | `x1_gs_t170` | `efb793e2468ca3a7318da0f0ad23d4fc` | `efb793e2…` (n1089/111070) | ✅ |

⇒ "OFF ⇒ y nguyên" có bằng chứng thực nghiệm trên jar mới. **Code B1 không gây hồi quy sim.**

## 2. CODE (B1) — đã commit `dd8d063`, test PASS

- Key `LIVE_ENTRY_GRID_MIN` (mặc định 15) thay hằng `ENTRY_GRID_MIN=15L`. ✅
- Wire `CONC_CAP_PERCOIN` vào đường LIVE (từ trước chỉ sim đọc), gated mặc định false. ✅
- Kiểm knob R4: `F_BASE`/`SELECTOR_RANK_TOPK`/`SIM_GATE_DYN_SCALE` **đọc bởi live**; `CONC_CAP_PERCOIN`
  **trước đây không** ⇒ đã wire (§2). `CONC_CAP_AGG_DCA`/`BD_RATE` vốn đọc bởi live.
- **Full suite: 174 test / 0 fail / 0 error** (gồm `EntryGrid1MTest` 5 mới + re-run 3 test cadence/cascade).

## 3. DEPLOY (B4) — diễn biến

| mốc | hành động | kết quả |
|---|---|---|
| 07:33:52 | deploy jar `8d93dad9` + env (`ENTRY_CASCADE=16`) → restart | lên active; `[R4-1M] LIVE_ENTRY_GRID_MIN=1` ✓; `[CASCADE] keep=16 topK=16` |
| 07:34–07:40 | verify | **FAIL**: `[S1] warm-up CHUA DU … 16 coin … 16 coin du >= 336 moc` mỗi tick; **0 `[GATE]`**; S1 `scoreAll` trả `null` ⇒ `[S1] skip tick` |
| 07:38:54 | thử sửa `ENTRY_CASCADE=32` → restart | **vẫn FAIL** (`keep=16 topK=16` — cap ở `SELECTOR_RANK_TOPK`) |
| 07:41:04 | **rollback** (jar `78387f30` + env `6cc24a57`) → restart | active; SELECTOR về 15'; universe đầy đủ 620 symbols; hết `[R4-1M]`/`[CASCADE]` |

**Tiêu chí B3:** (i) scan nhanh ~7 s PASS · (ii) `[GATE]`/phút **FAIL (0 dòng)** · (iii) 0 ERROR mới
**FAIL (`[S1] warm-up CHUA DU` mỗi tick)** · (iv)/(v) chưa đo (dừng sớm do ii/iii FAIL).

## 4. NGUYÊN NHÂN GỐC (xung đột CODE, không phải lỗi config)

`DetectEntrySignal2TradeNormal.cascadeUniverse`:
```java
int topK = Configs.ENTRY_CASCADE;
if (Configs.SELECTOR_RANK_TOPK > 0 && topK > Configs.SELECTOR_RANK_TOPK) {
    topK = Configs.SELECTOR_RANK_TOPK;      // ← CAP
}
Set<String> keep = cascadeGateFirst(universe, held, predictData.return15M, topK);
```
⇒ cascade **luôn giữ ≤ `SELECTOR_RANK_TOPK` coin**. R4 đặt `SELECTOR_RANK_TOPK=16` ⇒ `keep=16`.

`S1RankerLive.scoreAll` yêu cầu **≥ 20 coin** (`closes.size() < 20 || ready < 20` ⇒ `return null`).

Trước deploy: SELECTOR chạy 15', **không cascade** ⇒ S1 nhận toàn universe (600–711 coin) ⇒ score bình
thường (`[S1] score 658 coin`). Sau deploy: cascade lọc còn 16 (< 20) ⇒ S1 warm-up fail ⇒ skip tick ⇒
không `[GATE]`, không entry selector, ERROR mỗi tick.

**⇒ R4's `SELECTOR_RANK_TOPK=16` < ngưỡng 20 của S1 ⇒ mâu thuẫn cấp thiết kế, cần sửa CODE.**

## 5. ĐỀ XUẤT FIX (chờ owner/MASTER chốt — chưa làm)

1. **(Khuyến nghị)** Bỏ/đổi cap trong `cascadeUniverse`: cho cascade giữ `max(ENTRY_CASCADE, 20)`
   (đủ cho S1 rank), rồi `SELECTOR_RANK_TOPK=16` chọn top-16 như ý R4. Sửa ~2 dòng + unit test.
   Lưu ý: predict trên ~24–32 coin vẫn rẻ (≈ 8–10 s/tick, đủ cho nhịp 1').
2. Hoặc **`SELECTOR_RANK_TOPK >= 20`** — nhưng đổi K của R4 (không còn là R4).
3. Hoặc hạ ngưỡng S1 (20 → nhỏ hơn) — rủi ro S1 rank kém tin cậy, cần đánh giá riêng.

**Cần MASTER/owner quyết hướng fix trước khi deploy lại.** Code B1 (LIVE_ENTRY_GRID_MIN + CONC_CAP_PERCOIN
live) **vẫn đúng, parity PASS**, giữ nguyên.

## 6. ROLLBACK (đã chạy, thành công)

```sh
cd /home/ubuntu/shadow_c3/app
cp -p target/binance-java-sdk-1.2.4.jar.bak_20260929_r4 target/binance-java-sdk-1.2.4.jar
cp -p conf/env.sh.bak_20260929_r4 conf/env.sh
sudo systemctl restart shadow-c3
```
Verify: jar `78387f30…` · env `6cc24a57…` · `is-active=active` (MainPID 2093361, 07:41:04) · SELECTOR 15' ·
universe 620 symbols · hết `[R4-1M]`/`[CASCADE]`. **242 không đụng.**
