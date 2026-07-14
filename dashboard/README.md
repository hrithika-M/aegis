# dashboard — Naveen's POD Plan-of-the-Day UI

The front-end for the POD system: a Flask app serving the operations dashboard
(touchpoints, flight prediction, simulation, data & quality, accuracy & models,
report). This is Naveen's original UI, preserved here with the model work.

> **UI-only.** Per `app.py`, the server renders static templates; the mock data
> lives in the front-end JS (`static/js/mock.js`). It shows the intended
> operator experience — it does not load the trained models in `../models/` at
> runtime. Wiring the real models behind these pages is future work.

## Run
```bash
pip install -r requirements.txt      # Flask
python app.py                        # -> http://localhost:5000
```

## Pages
`dashboard` · `touchpoints` · `flight` (flight prediction) · `simulation` ·
`data` (data & quality) · `accuracy` (accuracy & models) · `settings`, plus a
print-ready `/report`.

## Layout
- `app.py` — Flask routes + sidebar nav.
- `templates/` — one HTML per page (`base.html` is the shell).
- `static/css/`, `static/js/` — styles and the per-page front-end logic
  (`page-*.js`), charts, and the mock data feed.
