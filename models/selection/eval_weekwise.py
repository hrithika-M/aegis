"""Week-wise rollup of the day-wise walk-forward results — real HYD data.

Reads docs/daywise_accuracy.csv (already computed by eval_daywise.py — one row
per touchpoint/model/test-day) and rolls it up by ISO week instead of by month,
per Naveen's ask (week-wise + day-wise per touchpoint, not month-wise).

Outputs:
  docs/weekwise_accuracy.csv   one row per (touchpoint, model, iso_year_week)
  docs/weekwise_winners.csv    one row per (touchpoint, iso_year_week): winner,
                                its accuracy, runner-up, gap

Run:  python -m modeling.eval_weekwise   (after eval_daywise.py has run)
"""
import os

import pandas as pd

DOC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'docs')


def main():
    daily = pd.read_csv(os.path.join(DOC, 'daywise_accuracy.csv'), parse_dates=['test_date'])
    iso = daily['test_date'].dt.isocalendar()
    daily['iso_year_week'] = iso['year'].astype(str) + '-W' + iso['week'].astype(str).str.zfill(2)

    weekly = (daily.groupby(['touchpoint', 'model', 'iso_year_week'])
              .agg(mean_accuracy=('accuracy', 'mean'), std_accuracy=('accuracy', 'std'),
                   mean_rmse=('rmse', 'mean'), n_days=('accuracy', 'count'))
              .reset_index())
    weekly['mean_accuracy'] = weekly['mean_accuracy'].round(1)
    weekly['std_accuracy'] = weekly['std_accuracy'].fillna(0).round(1)
    weekly['mean_rmse'] = weekly['mean_rmse'].round(1)
    weekly.to_csv(os.path.join(DOC, 'weekwise_accuracy.csv'), index=False)

    winners = []
    for (tp, wk), g in weekly.groupby(['touchpoint', 'iso_year_week']):
        g = g.sort_values('mean_accuracy', ascending=False)
        best = g.iloc[0]
        second = g.iloc[1] if len(g) > 1 else g.iloc[0]
        winners.append({'touchpoint': tp, 'iso_year_week': wk, 'winner': best['model'],
                         'winner_accuracy': best['mean_accuracy'], 'runner_up': second['model'],
                         'runner_up_accuracy': second['mean_accuracy'],
                         'gap': round(best['mean_accuracy'] - second['mean_accuracy'], 1)})
    win_df = pd.DataFrame(winners).sort_values(['touchpoint', 'iso_year_week'])
    win_df.to_csv(os.path.join(DOC, 'weekwise_winners.csv'), index=False)

    print(f"wrote docs/weekwise_accuracy.csv  ({len(weekly):,} rows)")
    print(f"wrote docs/weekwise_winners.csv   ({len(win_df):,} rows)")
    print()
    print("=== winner-count per touchpoint (how many weeks each model won) ===")
    for tp in win_df['touchpoint'].unique():
        sub = win_df[win_df['touchpoint'] == tp]
        counts = sub['winner'].value_counts()
        print(f"  {tp:<22}" + "  ".join(f"{m}={c}" for m, c in counts.items()))


if __name__ == '__main__':
    main()
