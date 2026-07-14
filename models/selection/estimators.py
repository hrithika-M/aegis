"""Estimators — the ONE model zoo for the whole modelling layer.

`zoo()` + `zoo_extra()` are the 20 algorithms the benchmark compares.
`make(name)` returns a single fresh estimator for the production Plan of the Day.
Defaults follow docs/MODEL_SELECTION.md (RandomForest / LightGBM tie for best).

A value of 'naive_seasonal' / 'naive_median' is a baseline handled specially by
evaluate.py (no fit); everything else is a factory returning a fresh estimator.
"""


def zoo():
    """Batch 1 — the core comparison."""
    from sklearn.ensemble import (RandomForestRegressor, ExtraTreesRegressor,
                                  GradientBoostingRegressor,
                                  HistGradientBoostingRegressor)
    from sklearn.linear_model import Ridge
    from sklearn.neighbors import KNeighborsRegressor
    from lightgbm import LGBMRegressor
    from xgboost import XGBRegressor
    return {
        'Naive-seasonal-7d':      'naive_seasonal',
        'Naive-median(dow,hour)': 'naive_median',
        'Ridge (linear floor)':   lambda: Ridge(),
        'kNN-7':                  lambda: KNeighborsRegressor(n_neighbors=7),
        'RandomForest [Naveen]':  lambda: RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1),
        'ExtraTrees':             lambda: ExtraTreesRegressor(n_estimators=100, random_state=42, n_jobs=-1),
        'GradientBoosting':       lambda: GradientBoostingRegressor(random_state=42),
        'HistGradientBoosting':   lambda: HistGradientBoostingRegressor(random_state=42),
        'LightGBM':               lambda: LGBMRegressor(n_estimators=300, learning_rate=0.05, random_state=42, verbose=-1),
        'XGBoost':                lambda: XGBRegressor(n_estimators=300, learning_rate=0.05, random_state=42, verbosity=0),
    }


def zoo_extra():
    """Batch 2 — completeness (count GLMs, neural net, SVR, other ensembles)."""
    from sklearn.tree import DecisionTreeRegressor
    from sklearn.ensemble import AdaBoostRegressor, BaggingRegressor
    from sklearn.linear_model import (Lasso, ElasticNet, HuberRegressor,
                                      PoissonRegressor, TweedieRegressor)
    from sklearn.neural_network import MLPRegressor
    from sklearn.svm import SVR
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    return {
        'DecisionTree (single)':  lambda: DecisionTreeRegressor(random_state=42),
        'AdaBoost':               lambda: AdaBoostRegressor(n_estimators=100, random_state=42),
        'Bagging(trees)':         lambda: BaggingRegressor(n_estimators=50, random_state=42, n_jobs=-1),
        'Lasso':                  lambda: make_pipeline(StandardScaler(), Lasso(alpha=0.5)),
        'ElasticNet':             lambda: make_pipeline(StandardScaler(), ElasticNet(alpha=0.5)),
        'HuberRegressor (robust)':lambda: make_pipeline(StandardScaler(), HuberRegressor(max_iter=500)),
        'PoissonGLM (count)':     lambda: make_pipeline(StandardScaler(), PoissonRegressor(max_iter=500)),
        'TweedieGLM (count)':     lambda: make_pipeline(StandardScaler(), TweedieRegressor(power=1.3, max_iter=500)),
        'MLP neural-net':         lambda: make_pipeline(StandardScaler(), MLPRegressor(hidden_layer_sizes=(64, 32), max_iter=400, random_state=42)),
        'SVR (RBF)':              lambda: make_pipeline(StandardScaler(), SVR(C=100, gamma='scale')),
    }


# short-name -> full model name in the zoos (for per-touchpoint selection)
ALIASES = {
    'randomforest': 'RandomForest [Naveen]', 'lightgbm': 'LightGBM',
    'xgboost': 'XGBoost', 'extratrees': 'ExtraTrees',
    'histgb': 'HistGradientBoosting', 'bagging': 'Bagging(trees)',
    'gradientboosting': 'GradientBoosting', 'knn': 'kNN-7',
}


def make(name='randomforest'):
    """A single production estimator by short name (used by the Plan of the Day)."""
    if name == 'randomforest':
        from sklearn.ensemble import RandomForestRegressor
        return RandomForestRegressor(n_estimators=200, random_state=42, n_jobs=-1)
    if name == 'lightgbm':
        from lightgbm import LGBMRegressor
        return LGBMRegressor(n_estimators=300, learning_rate=0.05, random_state=42, verbose=-1)
    if name == 'xgboost':
        from xgboost import XGBRegressor
        return XGBRegressor(n_estimators=300, learning_rate=0.05, random_state=42, verbosity=0)
    if name == 'extratrees':
        from sklearn.ensemble import ExtraTreesRegressor
        return ExtraTreesRegressor(n_estimators=200, random_state=42, n_jobs=-1)
    if name == 'histgb':
        from sklearn.ensemble import HistGradientBoostingRegressor
        return HistGradientBoostingRegressor(random_state=42)
    if name == 'bagging':
        from sklearn.ensemble import BaggingRegressor
        return BaggingRegressor(n_estimators=50, random_state=42, n_jobs=-1)
    raise ValueError(f"unknown estimator '{name}'")
