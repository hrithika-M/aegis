"""POD — Plan of the Day. UI-only Flask server (mock data lives in the front-end).
No models or data are loaded; every page is a static template rendered with the nav.
"""
from flask import Flask, render_template, abort

app = Flask(__name__)

# (route, label, icon-key) — order defines sidebar
PAGES = [
    ('dashboard',   'Dashboard',          'grid'),
    ('touchpoints', 'Touchpoints',        'layers'),
    ('flight',      'Flight Prediction',  'plane'),
    ('simulation',  'Simulation',         'sliders'),
    ('data',        'Data & Quality',     'server'),
    ('accuracy',    'Accuracy & Models',  'report'),
    ('settings',    'Settings',           'gear'),
]
VALID = {p[0] for p in PAGES}


@app.route('/')
def home():
    return render_template('dashboard.html', active='dashboard', pages=PAGES)


@app.route('/report')
def report():
    """Print-ready Plan-of-the-Day report (full day or one touchpoint via ?tp=)."""
    return render_template('report.html')


@app.route('/<page>')
def page(page):
    if page not in VALID:
        abort(404)
    return render_template(f'{page}.html', active=page, pages=PAGES)


if __name__ == '__main__':
    app.run(debug=True, port=5000)
