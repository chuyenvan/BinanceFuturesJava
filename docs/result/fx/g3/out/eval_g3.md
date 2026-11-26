# G3 eval (TRAIN numbers tagged [in-sample])

## LevFunds_TFF: direction H_ND (TRAIN mean daily -0.0000 [in-sample]); selected W156_H4; conclusion KHONG DAT
| config | TRAIN Sharpe [in-sample] | TRAIN ann_ret [in-sample] | WFO Sharpe | WFO ann_ret | WFO maxDD | WFO trades |
|---|---|---|---|---|---|---|
| W52_H1 | -0.1616 [in-sample] | -0.0059 [in-sample] | -0.2806 | -0.0053 | 0.0741 | 594 |
| W52_H4 | 0.0050 [in-sample] | 0.0002 [in-sample] | -0.3071 | -0.0052 | 0.0689 | 594 |
| W156_H1 | 0.2175 [in-sample] | 0.0025 [in-sample] | -0.0866 | -0.0017 | 0.0473 | 441 |
| W156_H4 | 0.2986 [in-sample] | 0.0030 [in-sample] | -0.3789 | -0.0061 | 0.0781 | 441 |
random p=0.0040; cost x2 WFO ann_ret=-0.0084; criteria {'D1': False, 'D2': True, 'D3': True, 'D4': False, 'D6': False, 'D7': False, 'D8': False, 'D9': True}

## AssetMgr_TFF: direction H_TD (TRAIN mean daily 0.0000 [in-sample]); selected W52_H4; conclusion KHONG DAT
| config | TRAIN Sharpe [in-sample] | TRAIN ann_ret [in-sample] | WFO Sharpe | WFO ann_ret | WFO maxDD | WFO trades |
|---|---|---|---|---|---|---|
| W52_H1 | 0.1789 [in-sample] | 0.0053 [in-sample] | -0.5289 | -0.0116 | 0.1129 | 743 |
| W52_H4 | 0.2945 [in-sample] | 0.0072 [in-sample] | -0.2706 | -0.0053 | 0.0708 | 743 |
| W156_H1 | -0.2256 [in-sample] | -0.0028 [in-sample] | -0.5493 | -0.0105 | 0.0988 | 752 |
| W156_H4 | 0.0627 [in-sample] | 0.0007 [in-sample] | -0.6962 | -0.0132 | 0.1160 | 752 |
random p=0.8982; cost x2 WFO ann_ret=-0.0092; criteria {'D1': False, 'D2': False, 'D3': True, 'D4': False, 'D6': False, 'D7': False, 'D8': False, 'D9': True}

## NonComm_LEG: direction H_ND (TRAIN mean daily -0.0000 [in-sample]); selected W52_H4; conclusion KHONG DAT
| config | TRAIN Sharpe [in-sample] | TRAIN ann_ret [in-sample] | WFO Sharpe | WFO ann_ret | WFO maxDD | WFO trades |
|---|---|---|---|---|---|---|
| W52_H1 | -0.0847 [in-sample] | -0.0017 [in-sample] | -0.2543 | -0.0081 | 0.1688 | 1269 |
| W52_H4 | 0.0143 [in-sample] | 0.0002 [in-sample] | -0.2348 | -0.0070 | 0.1580 | 1269 |
| W156_H1 | -0.1900 [in-sample] | -0.0033 [in-sample] | -0.3563 | -0.0108 | 0.1829 | 971 |
| W156_H4 | -0.3075 [in-sample] | -0.0048 [in-sample] | -0.2172 | -0.0063 | 0.1327 | 971 |
random p=0.0020; cost x2 WFO ann_ret=-0.0104; criteria {'D1': False, 'D2': True, 'D3': True, 'D4': False, 'D6': False, 'D7': False, 'D8': False, 'D9': True}

## combined 2013-01-01..2019-12-31: Sharpe -0.6038 ann_ret -0.0058 maxDD 0.0480 p 0.0140 trades 1788; criteria {'D1': False, 'D2': True, 'D3': True, 'D4': False, 'D6': False, 'D7': False, 'D8': False, 'D9': True}; conclusion KHONG DAT
