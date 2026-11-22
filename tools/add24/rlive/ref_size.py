"""ADD24 REF numpy DOC LAP (KHONG import Java, V7) - bao size s9.3 + ham budget dac ta (= ref_v12.budget, float32 nhu sim).
Hang so lay tu banner live (V8/P7): F_BASE, DCA_GRID_SCALE, weights, sizeCap; U_MAX: banner KHONG in => tham so (mac dinh 0.6 = Configs.U_MAX
rig cfg_effective; ERRATA_PROPOSED_A E-A2 xin owner xac nhan SIM_U_MAX).
Cong thuc (ERRATA_PROPOSED_A E-A1): b = min(sizeCap*C ; C*F_BASE*(1-U/U_MAX)/sum(w) * w[leg]*SCALE)  (leg0, w=1x4, SCALE 6 => 0.0225*C*(1-U/0.6)).
"""
import numpy as np

F = np.float32


def budget(C, U, leg, F_BASE=0.015, U_MAX=0.6, W=(1.0, 1.0, 1.0, 1.0), SCALE=6.0, SIZE_CAP=0.045):
    """float32 nhu ref_v12.budget / sim. U = ty le da dung (U_before). None neu U >= U_MAX."""
    C = F(C)
    u = F(U)
    if u >= F(U_MAX):
        return None
    b = F(F(F(C * F(F_BASE)) * F(F(1) - F(u / F(U_MAX)))) / F(sum(W)))
    if leg >= len(W):
        return F(0)
    b = F(b * F(F(W[leg]) * F(SCALE)))
    cap = F(F(SIZE_CAP) * C)
    return cap if b > cap else b


def bao(C3, E_lo, E_hi, U, leg, **k):
    """[b_lo, b_hi] voi C_eff = min(C3, E) chay tren [E_lo, E_hi] (budget don dieu tang theo C khi U co dinh)."""
    c_lo, c_hi = min(C3, E_lo), min(C3, E_hi)
    b1, b2 = budget(c_lo, U, leg, **k), budget(c_hi, U, leg, **k)
    if b1 is None or b2 is None:
        return None
    return float(min(b1, b2)), float(max(b1, b2))


def floor_to(x, step):
    from decimal import Decimal, ROUND_FLOOR
    d = Decimal(repr(x)) / Decimal(repr(step))
    return float(d.to_integral_value(rounding=ROUND_FLOOR) * Decimal(repr(step)))


def selftest():
    # prereg hand values (C=10000, 3 leg lien tiep, bo lam tron qty): 225,00 / 216,56 / 208,44
    used, out = 0.0, []
    for _ in range(3):
        b = float(budget(10000.0, used / 10000.0, 0))
        out.append(round(b, 2)); used += b
    assert out == [225.0, 216.56, 208.44], out
    assert abs(float(budget(1000.0, 0.0, 0)) - 22.5) < 1e-6
    lo, hi = bao(1000.0, 990.0, 1010.0, 0.1, 0)
    assert lo < hi and abs(hi - float(budget(1000.0, 0.1, 0))) < 1e-9
    return out


if __name__ == '__main__':
    print('selftest', selftest())
