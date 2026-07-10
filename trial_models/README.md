# trial_models — forecasting model experiments

Trial-and-error testing of forecasting models for the POD demand problem, on the
real EWS data (in `../data/`). Each model gets its **own folder named after the
model**, with its code and a `README.md` recording its results.

## Convention
```
trial_models/
  <model_name>/
    <model_name>_benchmark.py   # the experiment (runnable)
    README.md                   # what it is + results table + honest notes
```

## Models tried

| Model | Type | Headline result (EWS Entry, walk-forward) | Folder |
|---|---|---|---|
| **Chronos-Bolt** (Amazon) | foundation model, zero-shot | **89.8%** — beat our RandomForest (88.3%) with NO training | [chronos/](chronos/) |
| Moirai (Salesforce) | foundation model, multi-stream | *planned* — transport-trained, takes weather/flights as covariates | (next) |

## Baselines for reference (from the POD project)
- RandomForest / LightGBM (our ML): ~81.8% average across touchpoints (walk-forward).
- The bottleneck is data quality, not the model — see the POD model-selection work.

## The open question these trials probe
Foundation models forecast our demand *zero-shot* as well as our trained models.
The genuinely new value would come from the **multi-stream** angle — feeding
weather and (when available) flight data as covariates — which is what the
Moirai trial will test next.
