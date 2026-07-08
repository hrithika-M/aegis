"""Heal — the confidence-gated self-healing loop. The full Aegis engine.

    scan (detect everything)
      -> LOOP until converged:
           repair every source        (its own history, day-scaled)
           reconcile every source     (its linked sources + references)
           re-score trust
           stop when: target reached, OR no cell improved this pass, OR
                      max_iterations hit
      -> honest result: healed tables + achieved trust (vs target) +
         escalation list of everything NOT confidently fixed

Why iterating matters (the chained-equations idea): sources heal EACH OTHER.
In pass 1, camera may heal the scanner's dark morning; in pass 2 the now-
trusted scanner series can heal the camera's dark evening. Each pass only
applies fixes whose confidence is HIGH, so iteration can only add
well-evidenced repairs — it can never spiral into fabrication.

The trust score counts a bucket as trusted only if it is OK or repaired at
HIGH confidence. MEDIUM/LOW repairs and DRIFT watchlist rows are reported in
the escalation list. The target (e.g. 97%) is an aim; the achieved score is
reported truthfully either way.
"""
import json
import sys
from datetime import datetime

from aegis import __version__
from aegis.config import load
from aegis.connectors import load_source, DATE, TIME, ENTITY
from aegis.detect import detect
from aegis.repair import repair
from aegis.reconcile import reconcile


def trust_score(t):
    """% of buckets that are OK or repaired at HIGH confidence."""
    if len(t) == 0:
        return 0.0
    ok = (t['flag'] == 'OK') | (t.get('confidence', '') == 'HIGH')
    return round(float(ok.mean()) * 100, 2)


def escalations(t, source):
    """Rows a human (or more data) must look at — never silently accepted."""
    e = t[(t['was_corrected'] & (t['confidence'] != 'HIGH')) | (t['flag'] == 'DRIFT')]
    cols = [DATE, TIME, ENTITY, 'flag', 'actual', 'expected', 'value_adj',
            'confidence', 'repair_method']
    out = e[[c for c in cols if c in e.columns]].copy()
    out.insert(0, 'source', source)
    return out


def heal(config, frames=None, verbose=True):
    """Run the full engine. Returns dict with healed tables, scores, iteration
    log, escalation list, and the honest target-vs-achieved verdict."""
    cfg = load(config)
    frames = frames or {}
    refs = [s.name for s in cfg.sources if s.role == 'reference']
    by_name = {s.name: s for s in cfg.sources}

    # ── scan ──
    tables, ingest = {}, {}
    for src in cfg.sources:
        canon, rep = load_source(src, frames.get(src.name))
        tables[src.name] = detect(canon, src.params)
        ingest[src.name] = rep
    initial = {n: trust_score(t) for n, t in tables.items()}

    # ── loop ──
    log = []
    for it in range(1, cfg.max_iterations + 1):
        # repair pass (idempotent: operates on flags, re-grades confidence)
        for src in cfg.sources:
            tables[src.name] = repair(tables[src.name], physical_max=src.physical_max)
        # reconcile pass (uses the freshly repaired helpers)
        upgrades = 0
        for src in cfg.sources:
            if not src.links:
                continue
            healed, rep = reconcile(src.name, tables, links=src.links,
                                    references=[l for l in src.links if l in refs],
                                    physical_max=src.physical_max)
            tables[src.name] = healed
            upgrades += rep['upgraded']
        overall = round(sum(trust_score(t) for t in tables.values()) / len(tables), 2)
        log.append({'iteration': it, 'upgrades': int(upgrades), 'overall_trust': overall})
        if verbose:
            print(f"  iter {it}: upgrades={upgrades:>4}  overall trust={overall}%")
        if overall >= cfg.target_trust or upgrades == 0:
            break

    # ── honest verdict ──
    esc = [escalations(t, n) for n, t in tables.items()]
    esc = __import__('pandas').concat(esc, ignore_index=True) if esc else None
    final = {n: trust_score(t) for n, t in tables.items()}
    overall = round(sum(final.values()) / len(final), 2)
    result = {
        'run': cfg.name, 'aegis': __version__,
        'at': datetime.now().isoformat(timespec='seconds'),
        'tables': tables, 'ingest': ingest,
        'trust_initial': initial, 'trust_final': final,
        'overall_trust': overall,
        'target_trust': cfg.target_trust,
        'target_met': bool(overall >= cfg.target_trust),
        'iterations': log,
        'escalations': esc,
        'n_escalations': int(len(esc)) if esc is not None else 0,
    }
    if verbose:
        verdict = 'TARGET MET' if result['target_met'] else 'TARGET NOT MET — reported honestly'
        print(f"  final: {overall}% vs target {cfg.target_trust}%  [{verdict}]  "
              f"escalations={result['n_escalations']}")
    return result


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("usage: python -m aegis.heal <config.yaml|config.json>")
        sys.exit(1)
    res = heal(sys.argv[1])
    summary = {k: res[k] for k in ('run', 'overall_trust', 'target_trust',
                                   'target_met', 'iterations', 'trust_initial',
                                   'trust_final', 'n_escalations')}
    print(json.dumps(summary, indent=2, default=str))
