package com.binance.chuyennd.ops;

/**
 * [V12 SAFE 2026-10-25] Nguon equity THAT cho kill-switch A40 (quyet dinh owner Q1b 10-25: drawdown kill-switch tinh
 * tren totalMarginBalance THAT cua tai khoan con c3_live, gom BFUSD / Multi-Assets, so voi dinh).
 *
 * <p>Diem noi cho vong 2: cai bang client tai khoan con ({@code GET /fapi/v2|v3/account} -> {@code totalMarginBalance}),
 * co cache (khong goi REST moi 15 s neu rate guard khong cho) — {@link KillSwitchEngine#periodic} goi ham nay moi ~15 s
 * tren thread rieng. Tra {@code null} khi khong co so (loi API, chua co cache): engine giu trang thai A40 cu va WARN
 * (loi API nen bao them qua {@code OpsHooks.onApiResult} de C3 bat). KHONG nem exception (neu nem, engine coi nhu null).
 */
@FunctionalInterface
public interface EquitySource {
    /** totalMarginBalance (USD) tai khoan con; null = khong co so lieu. */
    Double totalMarginBalance();
}
