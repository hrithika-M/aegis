"""Aegis config — the single place where a user describes their data.

A run is declared in YAML (or JSON, or a plain dict). Example:

    name: airport_run
    target_trust: 97          # aim; achieved score is always reported honestly
    sources:
      - name: scans
        kind: csv                       # csv | excel | database
        path: data/scans.csv            # files: path
        # url: postgresql://user:pass@host:5432/mydb    # database: URL +
        # query: SELECT * FROM eboarding_scans          # query
        columns:                        # map raw columns -> canonical roles
          datetime: scan_time           # OR: date: d / hour: h
          entity: gate                  # optional (single-stream if omitted)
          value: scan_count
        role: data                      # data | reference (ground truth)
        links: [camera]                 # cross-source healing edges (phase 2)
        physical_max: 220               # hard plausibility ceiling (optional)
        params: {z_spike: 4.0}          # detector overrides (optional)

Everything else — the normal bands, correlations, repair ratios — is LEARNED
from the data, never configured.
"""
import json
import os
from dataclasses import dataclass, field

VALID_KINDS = ('csv', 'excel', 'database', 'dataframe')
VALID_ROLES = ('data', 'reference')


@dataclass
class SourceCfg:
    name: str
    kind: str
    columns: dict                     # {'datetime'|'date'/'hour', 'entity'?, 'value'}
    path: str = None                  # for csv/excel
    url: str = None                   # for database (SQLAlchemy URL)
    query: str = None                 # for database
    role: str = 'data'
    links: list = field(default_factory=list)
    physical_max: float = None
    params: dict = field(default_factory=dict)

    def validate(self):
        if self.kind not in VALID_KINDS:
            raise ValueError(f"source '{self.name}': kind must be one of {VALID_KINDS}")
        if self.kind in ('csv', 'excel') and not self.path:
            raise ValueError(f"source '{self.name}': file kind needs `path`")
        if self.kind == 'database' and not (self.url and self.query):
            raise ValueError(f"source '{self.name}': database kind needs `url` and `query`")
        if self.role not in VALID_ROLES:
            raise ValueError(f"source '{self.name}': role must be one of {VALID_ROLES}")
        c = self.columns or {}
        if 'value' not in c:
            raise ValueError(f"source '{self.name}': columns.value is required")
        if 'datetime' not in c and not ('date' in c and 'hour' in c):
            raise ValueError(f"source '{self.name}': give columns.datetime, or BOTH "
                             "columns.date and columns.hour")
        return self


@dataclass
class AegisConfig:
    name: str
    sources: list                     # [SourceCfg]
    target_trust: float = 97.0
    max_iterations: int = 5           # self-heal loop cap (phase 2)

    def validate(self):
        if not self.sources:
            raise ValueError("config needs at least one source")
        names = [s.name for s in self.sources]
        if len(names) != len(set(names)):
            raise ValueError(f"duplicate source names: {names}")
        for s in self.sources:
            s.validate()
            for l in s.links:
                if l not in names:
                    raise ValueError(f"source '{s.name}' links to unknown source '{l}'")
        return self


def load(config) -> AegisConfig:
    """Accept a dict, a .yaml/.yml path, or a .json path."""
    if isinstance(config, AegisConfig):
        return config.validate()
    if isinstance(config, str):
        if not os.path.exists(config):
            raise FileNotFoundError(config)
        with open(config, encoding='utf-8') as f:
            if config.endswith(('.yaml', '.yml')):
                import yaml
                config = yaml.safe_load(f)
            else:
                config = json.load(f)
    if not isinstance(config, dict):
        raise TypeError("config must be a dict or a path to .yaml/.json")
    sources = [SourceCfg(**s) for s in config.get('sources', [])]
    cfg = AegisConfig(name=config.get('name', 'aegis_run'), sources=sources,
                      target_trust=float(config.get('target_trust', 97.0)),
                      max_iterations=int(config.get('max_iterations', 5)))
    return cfg.validate()
