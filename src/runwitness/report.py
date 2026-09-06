import html
import json


def render_report(manifest, decision):
    rows = []
    for gate in decision["gates"]:
        cells = [gate["metric"], gate["op"], gate.get("expected"), gate.get("actual"), gate["status"]]
        rows.append("<tr>" + "".join(f"<td>{html.escape(str(v))}</td>" for v in cells) + "</tr>")
    payload = html.escape(json.dumps(manifest, indent=2, sort_keys=True))
    return f"""<!doctype html><html><head><meta charset='utf-8'><title>RunWitness report</title>
<style>body{{font:16px system-ui;max-width:1050px;margin:48px auto;padding:0 24px;color:#17211c}}h1{{font-size:42px}}.status{{display:inline-block;padding:7px 12px;border:1px solid;border-radius:999px;text-transform:uppercase}}table{{width:100%;border-collapse:collapse;margin:24px 0}}th,td{{text-align:left;padding:10px;border-bottom:1px solid #ccd3ce}}pre{{background:#f3f5f3;padding:20px;overflow:auto}}</style></head>
<body><p>RUNWITNESS / DEPLOYMENT EVIDENCE</p><h1>{html.escape(manifest['benchmark']['name'])}</h1>
<p class='status'>{html.escape(decision['overall'])}</p><p>Run {html.escape(manifest['run_id'])}</p>
<h2>Deployment gates</h2><table><thead><tr><th>Metric</th><th>Operator</th><th>Expected</th><th>Actual</th><th>Status</th></tr></thead><tbody>{''.join(rows)}</tbody></table>
<h2>Evidence manifest</h2><pre>{payload}</pre></body></html>"""
