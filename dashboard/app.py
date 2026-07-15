"""POD — Plan of the Day. Flask ops console.

The HYD pages are UI-only (mock data in the front-end). The Bhogapuram page is
wired to the REAL digital-twin outputs in ../bhogapuram_digital_twin/ — so our work
shows up inside the dashboard with the same look and feel.
"""
import csv
import json
import os

from flask import Flask, render_template, abort

app = Flask(__name__)
TWIN = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'bhogapuram_digital_twin')

# (route, label, icon-key) — order defines sidebar
PAGES = [
    ('dashboard',   'Dashboard',          'grid'),
    ('touchpoints', 'Touchpoints',        'layers'),
    ('flight',      'Flight Prediction',  'plane'),
    ('simulation',  'Simulation',         'sliders'),
    ('data',        'Data & Quality',     'server'),
    ('accuracy',    'Accuracy & Models',  'report'),
    ('bhogapuram',  'Bhogapuram Twin',    'plane'),
    ('settings',    'Settings',           'gear'),
]
VALID = {p[0] for p in PAGES}


def _csv(rel):
    p = os.path.join(TWIN, rel)
    return list(csv.DictReader(open(p, encoding='utf-8'))) if os.path.exists(p) else []


def twin_data():
    """Load the REAL Bhogapuram digital-twin outputs for the dashboard."""
    ms = _csv('analytics/model_selection_twin.csv')
    champ = {}
    for r in ms:
        tp = r['Touchpoint']
        try:
            acc = float(r['Accuracy'])
        except (ValueError, KeyError):
            continue
        if r['Model'] == 'Naive-7d':
            continue
        if tp not in champ or acc > champ[tp]['acc']:
            champ[tp] = {'model': r['Model'], 'acc': acc, 'rmse': r['RMSE'],
                         'recall': r.get('PeakRecall', ''), 'r2': r.get('R2', '')}
    ver = {}
    vp = os.path.join(TWIN, 'version.json')
    if os.path.exists(vp):
        ver = json.load(open(vp, encoding='utf-8'))
    return {
        'kpis': _csv('analytics/kpis.csv'),
        'peak_hours': _csv('analytics/peak_hours.csv'),
        'ci': _csv('analytics/confidence_intervals.csv'),
        'scenarios': _csv('analytics/scenarios.csv'),
        'events': _csv('analytics/events.csv'),
        'champions': champ,
        'validation': _csv('analytics/synthetic_validation.csv'),
        'version': ver.get('simulator_version', '0.4.0'),
    }


@app.route('/')
def home():
    return render_template('dashboard.html', active='dashboard', pages=PAGES)


@app.route('/report')
def report():
    """Print-ready Plan-of-the-Day report (full day or one touchpoint via ?tp=)."""
    return render_template('report.html')


@app.route('/bhogapuram')
def bhogapuram():
    return render_template('bhogapuram.html', active='bhogapuram', pages=PAGES, data=twin_data())


@app.route('/<page>')
def page(page):
    if page not in VALID:
        abort(404)
    return render_template(f'{page}.html', active=page, pages=PAGES)


if __name__ == '__main__':
    app.run(debug=True, port=5000)
