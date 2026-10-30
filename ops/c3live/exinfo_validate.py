# exinfo_validate.py — [V12 R4f MINOR-2] bo kiem DUY NHAT cho raw /fapi/v1/exchangeInfo (UNIVERSE_A1 + R7), dung CHUNG o:
#   - deploy_v12_dry_r4.sh: PRE (nguon doc ra stdout, "-") va buoc chuan bi (file tai ve);
#   - exinfo_refresh_242.sh (cron 242): moi lan lam moi.
# Chay: python3 -I exinfo_validate.py <file_moi|-> <file_hien_tai|""> <min_tradfi> <max_giam_symbol>
# Kiem: JSON; serverTime > 0 (va MOI HON file hien tai neu co); > 100 symbol; MOI symbol co onboardDate + underlyingType;
#   >= min_tradfi hop dong TradFi (contractType chua TRADIFI/TRADFI); so symbol giam <= max_giam so voi file hien tai.
# rc 0 + "symbols=.. TradFi=.. onboardDate=.. underlyingType=.. serverTime=.." ; rc 2 + ly do. Phan loai TF/INDEX KHONG o day.
import json
import sys


def main(a):
    new, cur, mintf, drop = a[1], a[2], int(a[3]), float(a[4])
    try:
        if new == '-':
            d = json.loads(sys.stdin.read())
        else:
            with open(new, encoding='utf-8') as fh:
                d = json.load(fh)
    except Exception as e:
        return 'JSON hong: %s' % str(e)[:120]
    st = d.get('serverTime') if isinstance(d, dict) else None
    sy = d.get('symbols') if isinstance(d, dict) else None
    if not isinstance(st, int) or isinstance(st, bool) or st <= 0:
        return 'thieu serverTime'
    if not isinstance(sy, list) or len(sy) <= 100:
        return 'chi %d symbol (can > 100)' % (len(sy) if isinstance(sy, list) else 0)
    bad = [s.get('symbol') if isinstance(s, dict) else '?' for s in sy
           if not isinstance(s, dict) or not s.get('onboardDate') or not s.get('underlyingType')]
    if bad:
        return '%d symbol thieu onboardDate/underlyingType (vd %s)' % (len(bad), bad[:3])
    tf = sum(1 for s in sy if 'TRADIFI' in str(s.get('contractType', '')).upper()
             or 'TRADFI' in str(s.get('contractType', '')).upper())
    if tf < mintf:
        return 'chi %d hop dong TradFi (< %d)' % (tf, mintf)
    c = None
    if cur:
        try:
            with open(cur, encoding='utf-8') as fh:
                c = json.load(fh)
        except Exception:
            c = None
    if isinstance(c, dict):
        cst = c.get('serverTime') or 0
        if st <= cst:
            return 'serverTime %d KHONG moi hon file hien tai %d' % (st, cst)
        n0 = len(c.get('symbols') or [])
        if n0 and len(sy) < n0 * (1 - drop):
            return 'so symbol giam %d -> %d (> %d %%)' % (n0, len(sy), int(round(drop * 100)))
    print('symbols=%d TradFi=%d onboardDate=%d underlyingType=%d serverTime=%d' % (len(sy), tf, len(sy), len(sy), st))
    return None


if __name__ == '__main__':
    err = main(sys.argv)
    if err:
        print(err)
        sys.exit(2)
