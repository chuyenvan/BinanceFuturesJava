package com.binance.chuyennd.c3live.canary;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;

import java.io.File;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.StandardCopyOption;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * [V12 3] Trang thai phien canary ({@code run/canary/canary_state.json}, ghi atomic): 2 symbol do luat chon (+ du lieu tho
 * luc chon), tmb moc, ket qua tung buoc K, co da dung tiem timeout (MO-5, 1 lan), ly do dung phien (tran lo), anh chup cum
 * K6. KHONG chua bi mat.
 */
public final class CanaryState {

    private static final Gson GSON = new GsonBuilder().setPrettyPrinting()
            .disableHtmlEscaping().create();
    public static final String FILE_NAME = "canary_state.json";

    /** Ket qua 1 buoc. */
    public static final class StepRecord {
        public String result;
        public long ms;
        public List<String> fails = new ArrayList<>();
        public Map<String, Object> data = new LinkedHashMap<>();
    }

    public String symMain;
    public String symAux;
    public long pickedAtMs;
    public List<Map<String, Object>> pickTop = new ArrayList<>();
    /** tmb moc (K0 DAT); null = chua co. */
    public Double tmb0;
    public long tmb0Ms;
    public boolean injectTimeoutUsed;
    public String aborted;
    public Map<String, StepRecord> steps = new LinkedHashMap<>();
    public Map<String, Object> k6Snapshot = new LinkedHashMap<>();
    public String k6SnapshotSymbol;
    /** So cai doc lap (tu su kien stream ORDER_TRADE_UPDATE / ACCOUNT_UPDATE FUNDING_FEE) — K8 + tran lo. */
    public double cumRealized;
    public double cumFeeStable;
    public double cumFunding;
    public Map<String, Double> feeOther = new LinkedHashMap<>();
    public int fills;
    /** Phut cuoi cung co cid (c3-/c3x-/c3s-) cua symbol — mo cum moi phai sang phut khac (cid khong trung qua cac cum). */
    public Map<String, Long> lastCidMinute = new LinkedHashMap<>();
    /** Phut gui lenh dong gan nhat cua symbol (cid c3x- khong trung qua cac cum). */
    public Map<String, Long> lastCloseMinute = new LinkedHashMap<>();
    /** [3f §ADD-4] ledger: so luong canary theo symbol (+ BUY c3-, - SELL c3x- theo khop; co lai theo san khi nho hon 2 lan doc). */
    public Map<String, String> canaryQty = new LinkedHashMap<>();
    /** [3f] khoi luong da tinh theo cid (response / queryOrder / stream — khong tinh 2 lan, ca qua JVM). */
    public Map<String, String> canaryCidQty = new LinkedHashMap<>();
    /** [3f §ADD-4 C] symbol TRUOT-DO (vi the ngoai canary / cong don LEGACY): KHONG dong, KHONG dat lenh — MASTER quyet. */
    public Map<String, String> red = new LinkedHashMap<>();
    /** [3f §ADD-4 D] anh chup LEGACY luc K0: vi the "qty@entry", lenh / algo "SYMBOL|cid|type|side". */
    public Map<String, String> legacyK0Positions = new LinkedHashMap<>();
    public List<String> legacyK0Orders = new ArrayList<>();
    public List<String> legacyK0Algos = new ArrayList<>();
    public Long legacyK0Ms;
    /** [3g MIN-4] phi tra bang tai san ngoai stable (vd BNB) quy ra USDT theo gia luc tinh lo gan nhat. */
    public Double feeOtherUsd;

    public static CanaryState load(File dir) throws IOException {
        File f = new File(dir, FILE_NAME);
        if (!f.exists()) return new CanaryState();
        String s = new String(Files.readAllBytes(f.toPath()), StandardCharsets.UTF_8);
        CanaryState st = GSON.fromJson(s, CanaryState.class);
        if (st == null) throw new IOException("file trang thai rong: " + f.getPath());
        if (st.steps == null) st.steps = new LinkedHashMap<>();
        if (st.pickTop == null) st.pickTop = new ArrayList<>();
        if (st.k6Snapshot == null) st.k6Snapshot = new LinkedHashMap<>();
        if (st.feeOther == null) st.feeOther = new LinkedHashMap<>();
        if (st.lastCidMinute == null) st.lastCidMinute = new LinkedHashMap<>();
        if (st.lastCloseMinute == null) st.lastCloseMinute = new LinkedHashMap<>();
        if (st.canaryQty == null) st.canaryQty = new LinkedHashMap<>();
        if (st.canaryCidQty == null) st.canaryCidQty = new LinkedHashMap<>();
        if (st.red == null) st.red = new LinkedHashMap<>();
        if (st.legacyK0Positions == null) st.legacyK0Positions = new LinkedHashMap<>();
        if (st.legacyK0Orders == null) st.legacyK0Orders = new ArrayList<>();
        if (st.legacyK0Algos == null) st.legacyK0Algos = new ArrayList<>();
        return st;
    }

    public void save(File dir) throws IOException {
        if (!dir.exists() && !dir.mkdirs()) throw new IOException("mkdirs " + dir);
        File f = new File(dir, FILE_NAME);
        File tmp = new File(dir, FILE_NAME + ".tmp");
        Files.write(tmp.toPath(), GSON.toJson(this).getBytes(StandardCharsets.UTF_8));
        Files.move(tmp.toPath(), f.toPath(), StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE);
    }

    public boolean symbolsChosen() {
        return symMain != null && symAux != null;
    }

    public String toJson() {
        return GSON.toJson(this);
    }
}
