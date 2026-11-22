"""ADD24 P1: luot CHINH THUC R-LIVE + moi doc du lieu van hanh / thi truong >= 2026-10-01 cho OW2 CHI sau khi owner duyet van ban
(commit OWNER_DECISION_* trong vz_e1_wt). Gate: env ADD24_P1_APPROVED=<commit>; commit phai ton tai, them/sua file docs/**/OWNER_DECISION_*
co chuoi 'ADD24' va 'R-LIVE' (hoac 'U5'). Khong co => TU CHOI (exit 2)."""
import os, subprocess, sys

REPO = os.path.expanduser('~/claude_master/vz_e1_wt')


def p1_approved(log=None):
    c = os.environ.get('ADD24_P1_APPROVED', '').strip()
    if not c:
        return False, 'thieu ADD24_P1_APPROVED=<commit OWNER_DECISION duyet R-LIVE>'
    try:
        files = subprocess.run(['git', '-C', REPO, 'show', '--name-only', '--format=', c], capture_output=True, text=True, check=True).stdout.split()
    except Exception as e:
        return False, 'commit %s khong ton tai: %s' % (c, e)
    od = [f for f in files if os.path.basename(f).startswith('OWNER_DECISION')]
    for f in od:
        try:
            txt = subprocess.run(['git', '-C', REPO, 'show', '%s:%s' % (c, f)], capture_output=True, text=True, check=True).stdout
        except Exception:
            continue
        if 'ADD24' in txt and ('R-LIVE' in txt or 'U5' in txt):
            return True, '%s:%s' % (c, f)
    return False, 'commit %s khong co OWNER_DECISION_* nhac ADD24 + R-LIVE/U5' % c


def require_p1():
    ok, why = p1_approved()
    if not ok:
        sys.stderr.write('TU CHOI (P1): %s\n' % why)
        sys.exit(2)
    return why
