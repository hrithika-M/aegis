"""Scan — Phase-1 orchestrator: connect -> profile -> detect -> quality report.

For every source in the config: read it (file or database), canonicalise +
validate, learn its normal, flag every bucket, and score its trust. This is the
"understand the data" half of Aegis; the self-healing loop (Phase 2) builds on
the trust tables produced here.

Usage:
    from aegis.scan import scan
    result = scan('run.yaml')                 # or a dict, or AegisConfig
    result['sources']['scans']['trust']       # the per-bucket trust table
    result['report']                          # machine-readable summary

CLI:
    python -m aegis.scan run.yaml
"""
import json
import sys
from datetime import datetime

from aegis import __version__
from aegis.config import load
from aegis.connectors import load_source
from aegis.detect import detect, trust_score


def scan(config, frames=None, verbose=True):
    """Run the understanding pipeline for every source.
    `frames`: {source_name: DataFrame} for kind=dataframe sources."""
    cfg = load(config)
    frames = frames or {}
    out = {'config': cfg, 'sources': {}, 'report': {
        'run': cfg.name, 'aegis': __version__,
        'at': datetime.now().isoformat(timespec='seconds'), 'sources': {}}}
    for src in cfg.sources:
        canon, ingest = load_source(src, frames.get(src.name))
        trust = detect(canon, src.params)
        score = trust_score(trust)
        out['sources'][src.name] = {'canon': canon, 'trust': trust,
                                    'ingest': ingest, 'score': score}
        out['report']['sources'][src.name] = {
            'ingestion': ingest,
            'buckets': int(len(trust)),
            'flags': trust['flag'].value_counts().to_dict(),
            'trust_score': score,
            'role': src.role,
        }
        if verbose:
            f = out['report']['sources'][src.name]['flags']
            print(f"  {src.name:<14} rows={ingest['rows_used']:>9,}  "
                  f"buckets={len(trust):>8,}  trust={score:>6}%  flags={f}")
    scores = [s['score'] for s in out['sources'].values()]
    out['report']['overall_trust'] = round(sum(scores) / len(scores), 2) if scores else 0.0
    if verbose:
        print(f"  {'OVERALL':<14} trust = {out['report']['overall_trust']}%")
    return out


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("usage: python -m aegis.scan <config.yaml|config.json>")
        sys.exit(1)
    res = scan(sys.argv[1])
    print(json.dumps(res['report'], indent=2, default=str))
