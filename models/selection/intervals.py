"""Intervals — P50/P90 staffing bands with split-conformal calibration.

A point forecast says the expected load; this adds a safe upper bound (P90) so
operations can hold head-room for the 1-in-10 peak. Quantile regression +
conformal calibration on a recent slice (so bands track demand drift). Uses the
shared trusted dataset and the prescription engine for the lane bands.

Run:  python -m modeling.intervals
"""
import numpy as np
from sklearn.ensemble import GradientBoostingRegressor

from config import SHEET_NAMES
from data_processor.prescription import prescribe_hour
from data_trust.integrate import median_pt
from modeling.dataset import FEATURES, TARGET, trusted_hourly
from training.common import get_clean_data

TEST_FRACTION = 0.15   # last ~15% of days held out for calibration check


def _qmodel(alpha):
    return GradientBoostingRegressor(loss='quantile', alpha=alpha, n_estimators=200,
                                     max_depth=3, learning_rate=0.05, random_state=42)


def fit_predict(tp, data):
    g = trusted_hourly(data, tp)
    days = sorted(g['Date'].unique())
    cut = days[int(len(days) * (1 - TEST_FRACTION))]
    tr, te = g[g['Date'] < cut], g[g['Date'] >= cut]
    if len(te) < 20 or len(tr) < 100:
        return None
    # split train -> fit (older) + calibration (recent) for split-conformal
    tr_days = sorted(tr['Date'].unique())
    cal_cut = tr_days[int(len(tr_days) * 0.85)]
    fit, cal = tr[tr['Date'] < cal_cut], tr[tr['Date'] >= cal_cut]
    if len(cal) < 50:
        fit, cal = tr, tr

    m50 = _qmodel(0.5).fit(fit[FEATURES], fit[TARGET])
    m90 = _qmodel(0.9).fit(fit[FEATURES], fit[TARGET])
    # conformal shift so empirical coverage matches nominal level (tracks drift)
    d50 = float(np.quantile(cal[TARGET].values - m50.predict(cal[FEATURES]), 0.5))
    d90 = float(np.quantile(cal[TARGET].values - m90.predict(cal[FEATURES]), 0.9))

    p50 = m50.predict(te[FEATURES]) + d50
    p90 = np.maximum(m90.predict(te[FEATURES]) + d90, p50)
    return {'actual': te[TARGET].values, 'p50': p50, 'p90': p90, 'hours': te['Hour'].values}


def main():
    data = get_clean_data()
    print("=" * 74)
    print("PREDICTION INTERVALS (P50/P90) — calibration + staffing bands")
    print("=" * 74)
    print("\n1) Calibration — does P90 cover ~90% of real hours? (target: cov90 ~ 0.90)")
    print(f"   {'Touchpoint':<12}{'cov@P50':>9}{'cov@P90':>9}{'band (P90-P50)/P50':>22}")
    covs90, preds = [], {}
    for tp in SHEET_NAMES:
        r = fit_predict(tp, data)
        if r is None:
            continue
        preds[tp] = r
        m = r['actual'] > 0
        cov50 = float((r['actual'][m] <= r['p50'][m]).mean())
        cov90 = float((r['actual'][m] <= r['p90'][m]).mean())
        band = float(np.mean((r['p90'][m] - r['p50'][m]) / np.maximum(r['p50'][m], 1)))
        covs90.append(cov90)
        print(f"   {tp:<12}{cov50:>9.2f}{cov90:>9.2f}{band*100:>20.0f}%")
    print(f"   {'AVERAGE':<12}{'':>9}{np.mean(covs90):>9.2f}")

    print("\n2) Staffing bands — lanes to plan (P50) vs hold for the peak (P90):")
    print(f"   {'Touchpoint':<12}{'peak hr':>8}{'P50 pax':>9}{'P90 pax':>9}"
          f"{'lanes P50':>11}{'lanes P90':>11}")
    for tp, r in preds.items():
        i = int(np.argsort(-r['p50'])[0])
        pt = median_pt(data, tp)
        l50 = prescribe_hour(tp, r['p50'][i], pt)['lanes_needed']
        l90 = prescribe_hour(tp, r['p90'][i], pt)['lanes_needed']
        print(f"   {tp:<12}{int(r['hours'][i]):>8}{r['p50'][i]:>9,.0f}{r['p90'][i]:>9,.0f}"
              f"{l50:>11}{l90:>11}")
    print("\nP90 lanes = head-room to hold so peak demand still meets the wait-time SLA.")


if __name__ == '__main__':
    main()
