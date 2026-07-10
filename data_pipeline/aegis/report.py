"""Report — turn a heal() result into deliverables a human can act on.

Outputs (write_outputs -> out_dir):
  <source>_healed.csv   the trusted series (canonical + value_adj + confidence)
  audit.csv             EVERY changed cell: old -> new, method, confidence,
                        which sources healed it (full provenance)
  escalations.csv       what still needs a human / more data
  report.json           machine-readable summary
  report.html           self-contained one-page report: verdict, trust
                        before -> after, fixes by confidence, iteration log,
                        biggest repairs, escalations. No external assets.

CLI:  python -m aegis.report run.yaml [out_dir]     (runs heal, writes all)
"""
import json
import os
import sys
from datetime import datetime

import pandas as pd

from aegis import __version__
from aegis.connectors import DATE, TIME, ENTITY
from aegis.heal import heal

NAVY, BLUE, GREEN, AMBER, RED = '#1F3864', '#2E75B6', '#2E7D32', '#B9770E', '#C0392B'


def audit_trail(tables):
    """Every cell any stage changed, across all sources — the full ledger."""
    rows = []
    for name, t in tables.items():
        ch = t[t['was_corrected']].copy()
        ch.insert(0, 'source', name)
        cols = ['source', DATE, TIME, ENTITY, 'flag', 'actual', 'expected',
                'value_adj', 'repair_method', 'confidence', 'healed_by']
        rows.append(ch[[c for c in cols if c in ch.columns]])
    if not rows:
        return pd.DataFrame()
    a = pd.concat(rows, ignore_index=True)
    return a.sort_values(['source', DATE, TIME]).reset_index(drop=True)


def write_outputs(result, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    tables = result['tables']

    for name, t in tables.items():
        keep = [DATE, TIME, ENTITY, 'actual', 'value_adj', 'flag', 'confidence']
        t[[c for c in keep if c in t.columns]].to_csv(
            os.path.join(out_dir, f'{name}_healed.csv'), index=False)

    audit = audit_trail(tables)
    audit.to_csv(os.path.join(out_dir, 'audit.csv'), index=False)
    if result['escalations'] is not None and len(result['escalations']):
        result['escalations'].to_csv(os.path.join(out_dir, 'escalations.csv'), index=False)

    summary = {k: result[k] for k in ('run', 'aegis', 'at', 'trust_initial',
                                      'trust_final', 'overall_trust', 'target_trust',
                                      'target_met', 'iterations', 'n_escalations')}
    summary['ingestion'] = result['ingest']
    with open(os.path.join(out_dir, 'report.json'), 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, default=str)

    html = build_html(result, audit)
    path = os.path.join(out_dir, 'report.html')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(html)
    return path


def _table(df, max_rows=15):
    if df is None or len(df) == 0:
        return '<p class="sub">none</p>'
    d = df.head(max_rows)
    head = ''.join(f'<th>{c}</th>' for c in d.columns)
    body = ''.join('<tr>' + ''.join(f'<td>{v}</td>' for v in r) + '</tr>'
                   for r in d.itertuples(index=False))
    more = (f'<p class="sub">… and {len(df) - max_rows:,} more (see CSV)</p>'
            if len(df) > max_rows else '')
    return f'<table><tr>{head}</tr>{body}</table>{more}'


def build_html(result, audit):
    ok = result['target_met']
    badge = (f'<span class="badge good">TARGET MET — {result["overall_trust"]}%'
             f' ≥ {result["target_trust"]}%</span>' if ok else
             f'<span class="badge bad">TARGET NOT MET — {result["overall_trust"]}%'
             f' &lt; {result["target_trust"]}% (reported honestly)</span>')

    src_rows = ''.join(
        f"<tr><td>{n}</td><td>{result['ingest'][n]['rows_used']:,}</td>"
        f"<td>{result['trust_initial'][n]}%</td><td><b>{result['trust_final'][n]}%</b></td></tr>"
        for n in result['trust_final'])
    iter_rows = ''.join(
        f"<tr><td>{i['iteration']}</td><td>{i['upgrades']}</td>"
        f"<td>{i['overall_trust']}%</td></tr>" for i in result['iterations'])

    conf_counts = (audit['confidence'].value_counts().to_dict() if len(audit) else {})
    top = (audit.assign(delta=(audit['value_adj'] - audit['actual']).abs())
           .nlargest(10, 'delta').drop(columns='delta') if len(audit) else audit)

    return f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<title>Aegis Report — {result['run']}</title><style>
 body{{font-family:'Segoe UI',Arial,sans-serif;margin:0;background:#F4F6FA;color:#222}}
 header{{background:{NAVY};color:#fff;padding:20px 40px}}
 header h1{{margin:0;font-size:22px}} header p{{margin:5px 0 0;opacity:.85;font-size:13px}}
 .wrap{{max-width:960px;margin:22px auto;padding:0 20px}}
 .badge{{display:inline-block;border-radius:14px;padding:6px 16px;font-weight:700;font-size:14px}}
 .good{{background:#E8F0E3;color:{GREEN}}} .bad{{background:#FBEAEA;color:{RED}}}
 .cards{{display:flex;gap:12px;flex-wrap:wrap;margin:18px 0}}
 .card{{flex:1;min-width:150px;background:#fff;border-radius:10px;padding:14px 16px;
        box-shadow:0 1px 4px rgba(0,0,0,.08);border-top:4px solid {BLUE}}}
 .card .n{{font-size:22px;font-weight:700;color:{NAVY}}} .card .l{{font-size:11.5px;color:#666;margin-top:3px}}
 section{{background:#fff;border-radius:10px;padding:18px 22px;margin-bottom:18px;
          box-shadow:0 1px 4px rgba(0,0,0,.08)}}
 h2{{color:{NAVY};font-size:16px;margin:0 0 10px}} .sub{{font-size:12px;color:#777}}
 table{{border-collapse:collapse;width:100%;font-size:12.5px;overflow-x:auto;display:block}}
 th{{background:{NAVY};color:#fff;padding:6px 9px;text-align:left;white-space:nowrap}}
 td{{padding:6px 9px;border-bottom:1px solid #e4e7ee;white-space:nowrap}}
 footer{{text-align:center;color:#999;font-size:12px;margin:26px 0}}
</style></head><body>
<header><h1>Aegis — Self-Healing Report</h1>
<p>run: {result['run']} · v{result['aegis']} · {result['at']}</p></header>
<div class="wrap">
<p style="margin-top:18px">{badge}</p>
<div class="cards">
 <div class="card"><div class="n">{len(result['tables'])}</div><div class="l">sources</div></div>
 <div class="card"><div class="n">{sum(len(t) for t in result['tables'].values()):,}</div><div class="l">buckets judged</div></div>
 <div class="card"><div class="n">{len(audit):,}</div><div class="l">cells healed (audited)</div></div>
 <div class="card"><div class="n">{conf_counts.get('HIGH', 0):,}</div><div class="l">HIGH-confidence fixes</div></div>
 <div class="card"><div class="n">{result['n_escalations']:,}</div><div class="l">escalated to a human</div></div>
</div>

<section><h2>Trust per source (before → after)</h2>
<table><tr><th>source</th><th>rows used</th><th>initial trust</th><th>final trust</th></tr>
{src_rows}</table></section>

<section><h2>Self-healing iterations</h2>
<table><tr><th>iteration</th><th>cells upgraded</th><th>overall trust</th></tr>
{iter_rows}</table>
<p class="sub">The loop stops when the target is met, nothing more can be
confidently improved, or the iteration cap is reached.</p></section>

<section><h2>Biggest repairs (full ledger in audit.csv)</h2>
{_table(top)}</section>

<section><h2>Escalations — needs a human or more data (escalations.csv)</h2>
{_table(result['escalations'])}
<p class="sub">Aegis never fabricates: cells without confident evidence are
listed here instead of being silently filled.</p></section>

<footer>Aegis v{__version__} · github.com/hrithika-M/aegis</footer>
</div></body></html>"""


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("usage: python -m aegis.report <config.yaml|json> [out_dir]")
        sys.exit(1)
    out = sys.argv[2] if len(sys.argv) > 2 else 'aegis_out'
    res = heal(sys.argv[1])
    path = write_outputs(res, out)
    print(f"report written: {path}")
