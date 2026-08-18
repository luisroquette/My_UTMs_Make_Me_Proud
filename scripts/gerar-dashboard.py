#!/usr/bin/env python3
"""Deterministic tracking dashboard generator — no LLM, no dependencies.

Reads the storage-layer export (links + daily aggregates + granular events +
conversions) and renders a single-file HTML dashboard that answers the five
questions of the metrics contract (references/nucleo/metricas.md):

  1. clicks per link, per period       (top links, 7/30/90 columns)
  2. clicks per origin/channel         (UTM snapshot breakdown)
  3. conversions per link              (attribution joined at export time)
  4. link status                       (paused > expired > broken > active)
  5. series over time                  (calendar-filled daily grid, top 5)

Determinism: the report date is the max aggregate day in the input — the same
input always renders the same HTML, on any machine, at any hour. Absence is
never zero: a day with no aggregate row renders "—", a row with clicks 0
renders "0". Origin breakdowns read the UTM snapshot stored on each event,
never the link's current UTM — an edited link must not rewrite history.

The attribution join (click ids -> link slug) happens at EXPORT time, in the
host stack; this dashboard consumes the resolved result.

Usage:
  python3 scripts/gerar-dashboard.py --input dashboard/dados-exemplo.json \
      --output dashboard/index.html
  python3 scripts/gerar-dashboard.py --self-test
"""

import argparse
import base64
import csv
import io
import json
import sys
from datetime import date, timedelta
from html import escape

# ---------------------------------------------------------------------------
# Input contract (see docs/superpowers/specs/2026-08-18-dashboard-skill-design.md)

LINK_FIELDS = ["slug", "name", "destination_url", "utm_source", "utm_medium",
               "utm_campaign", "is_active", "expires_at", "saude"]
AGG_FIELDS = ["slug", "day", "clicks"]
EVENT_FIELDS = ["slug", "clicked_at", "utm_source", "utm_medium", "utm_campaign"]
CONV_FIELDS = ["slug", "type", "converted_at"]
SAUDE_STATES = ("healthy", "warning", "broken")
DEVICE_STATES = ("desktop", "mobile", "tablet", "other")
CONV_TYPES = ("lead", "purchase")
WINDOWS = (7, 30, 90)


def _err(msg):
    raise ValueError(msg)


def validar(dados):
    """Return a list of named errors; [] means the input is well-formed."""
    erros = []
    if not isinstance(dados, dict):
        return ["raiz: esperava objeto JSON"]
    for chave in ("links", "daily_aggregates", "events", "conversions"):
        if chave not in dados:
            erros.append(f"raiz: chave obrigatória ausente: {chave}")
            return erros
        if not isinstance(dados[chave], list):
            erros.append(f"raiz: {chave} deve ser lista")
    if erros:
        return erros

    slugs = set()
    for i, link in enumerate(dados["links"]):
        onde = f"links[{i}]"
        for campo in LINK_FIELDS:
            if campo not in link:
                erros.append(f"{onde}: campo ausente: {campo}")
        if "saude" in link and link["saude"] not in SAUDE_STATES:
            erros.append(f"{onde}: saude inválido: {link['saude']!r}")
        if "is_active" in link and not isinstance(link["is_active"], bool):
            erros.append(f"{onde}: is_active deve ser booleano")
        if "slug" in link and not (isinstance(link["slug"], str) and link["slug"]):
            erros.append(f"{onde}: slug vazio ou não-string")
        elif "slug" in link:
            slugs.add(link["slug"])

    for i, agg in enumerate(dados["daily_aggregates"]):
        onde = f"daily_aggregates[{i}]"
        for campo in AGG_FIELDS:
            if campo not in agg:
                erros.append(f"{onde}: campo ausente: {campo}")
        if "day" in agg:
            try:
                date.fromisoformat(agg["day"])
            except ValueError:
                erros.append(f"{onde}: day inválido (esperado YYYY-MM-DD): {agg['day']!r}")
        if "clicks" in agg and (not isinstance(agg["clicks"], int)
                                or isinstance(agg["clicks"], bool)
                                or agg["clicks"] < 0):
            erros.append(f"{onde}: clicks deve ser inteiro >= 0")

    for i, ev in enumerate(dados["events"]):
        onde = f"events[{i}]"
        for campo in EVENT_FIELDS:
            if campo not in ev:
                erros.append(f"{onde}: campo ausente: {campo}")
        if "device" in ev and ev["device"] not in DEVICE_STATES:
            erros.append(f"{onde}: device inválido: {ev['device']!r}")

    for i, conv in enumerate(dados["conversions"]):
        onde = f"conversions[{i}]"
        for campo in CONV_FIELDS:
            if campo not in conv:
                erros.append(f"{onde}: campo ausente: {campo}")
        if "type" in conv and conv["type"] not in CONV_TYPES:
            erros.append(f"{onde}: type inválido: {conv['type']!r}")

    # Unknown slugs: an aggregate/event/conversion pointing at nothing is
    # export corruption, not silence — named error, never ignored.
    for nome, lista, campo in (("daily_aggregates", dados["daily_aggregates"], "day"),
                               ("events", dados["events"], "clicked_at"),
                               ("conversions", dados["conversions"], "converted_at")):
        for i, item in enumerate(lista):
            slug = item.get("slug")
            if isinstance(slug, str) and slug and slug not in slugs:
                erros.append(f"{nome}[{i}]: slug desconhecido: {slug}")

    return erros


# ---------------------------------------------------------------------------
# Model (pure data — what the self-test asserts)

def status_link(link, report_date):
    """Derived status, deterministic precedence: paused > expired > broken > active."""
    if not link.get("is_active", True):
        return "pausado"
    if link.get("expires_at"):
        try:
            if date.fromisoformat(str(link["expires_at"])[:10]) < report_date:
                return "expirado"
        except ValueError:
            pass  # malformed expiry is an export problem, not a status
    if link.get("saude") == "broken":
        return "quebrado"
    return "ativo"


def construir(dados):
    """Build the dashboard model from validated input."""
    aggs = dados["daily_aggregates"]
    if not aggs:
        _err("daily_aggregates: vazio — sem agregados não há report_date")
    report_date = max(date.fromisoformat(a["day"]) for a in aggs)

    janelas = {n: [report_date - timedelta(days=n - 1 - i) for i in range(n)]
               for n in WINDOWS}

    clicks_por_slug = {}
    for agg in aggs:
        clicks_por_slug.setdefault(agg["slug"], {})[date.fromisoformat(agg["day"])] = agg["clicks"]

    def clicks_janela(slug, n):
        dias = set(janelas[n])
        return sum(v for d, v in clicks_por_slug.get(slug, {}).items() if d in dias)

    links_ordenados = sorted(
        dados["links"],
        key=lambda l: (-clicks_janela(l["slug"], 30), l["slug"]),
    )
    top_links = [{
        "slug": l["slug"], "name": l["name"],
        "status": status_link(l, report_date),
        "saude": l.get("saude", "healthy"),
        "clicks": {n: clicks_janela(l["slug"], n) for n in WINDOWS},
    } for l in links_ordenados]

    # Origin breakdown — event UTM snapshots only (history is immutable).
    eventos = dados["events"]
    def origem_de(ev):
        return (ev["utm_source"], ev["utm_medium"])
    origens = {n: {} for n in WINDOWS}
    for ev in eventos:
        try:
            dia = date.fromisoformat(str(ev["clicked_at"])[:10])
        except ValueError:
            continue
        chave = origem_de(ev)
        for n in WINDOWS:
            if dia in janelas[n]:
                origens[n][chave] = origens[n].get(chave, 0) + 1
    top_origens = {
        n: sorted(origens[n].items(), key=lambda kv: (-kv[1], kv[0]))[:10]
        for n in WINDOWS
    }

    conversoes = {slug: {"lead": 0, "purchase": 0} for slug in clicks_por_slug}
    conversoes.update({l["slug"]: {"lead": 0, "purchase": 0} for l in dados["links"]})
    for conv in dados["conversions"]:
        if conv["slug"] in conversoes:
            conversoes[conv["slug"]][conv["type"]] += 1

    # Calendar-filled series per link — missing day is None ("—"),
    # a row with clicks 0 is a measured zero (0). The 30-day grid renders
    # this per top-5 link; window totals come from the same aggregates.
    serie_top5 = []
    for tl in top_links[:5]:
        por_dia = clicks_por_slug.get(tl["slug"], {})
        serie_top5.append({
            "slug": tl["slug"], "name": tl["name"],
            "dias": [(d, por_dia.get(d)) for d in janelas[30]],
        })

    return {
        "report_date": report_date,
        "top_links": top_links,
        "top_origens": top_origens,
        "conversoes": conversoes,
        "serie_top5": serie_top5,
    }


def csv_links(dados, modelo):
    """Deterministic CSV export of the link rows (reporting rule of Stage 5)."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["slug", "name", "destination_url", "utm_source", "utm_medium",
                     "utm_campaign", "is_active", "expires_at", "saude", "status",
                     "clicks_7d", "clicks_30d", "clicks_90d", "leads", "purchases"])
    por_slug = {tl["slug"]: tl for tl in modelo["top_links"]}
    for link in dados["links"]:
        tl = por_slug[link["slug"]]
        conv = modelo["conversoes"].get(link["slug"], {"lead": 0, "purchase": 0})
        writer.writerow([link["slug"], link["name"], link["destination_url"],
                         link["utm_source"], link["utm_medium"], link["utm_campaign"],
                         link["is_active"], link.get("expires_at") or "",
                         link.get("saude", "healthy"), tl["status"],
                         tl["clicks"][7], tl["clicks"][30], tl["clicks"][90],
                         conv["lead"], conv["purchase"]])
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Render (single-file HTML, zero JavaScript, offline)

CSS = """
:root { --ink:#1A1524; --ink-soft:#4A4458; --lilas:#C9A7FF; --brand:#7B2FBE;
        --brand-soft:#F3ECFB; --ok:#2E7D32; --warn:#D5A62E; --bad:#B3261E; }
* { box-sizing:border-box; margin:0; padding:0; }
body { font-family:Inter,-apple-system,'Segoe UI',system-ui,sans-serif;
       background:#FDFCFE; color:var(--ink); padding:32px 20px 64px; }
.wrap { max-width:960px; margin:0 auto; }
header h1 { font-size:24px; letter-spacing:-0.02em; }
header p { color:var(--ink-soft); margin-top:6px; font-size:14px; }
h2 { font-size:15px; margin:36px 0 12px; text-transform:uppercase;
     letter-spacing:0.08em; color:var(--ink-soft); }
table { width:100%; border-collapse:collapse; background:#fff;
        border:1px solid #E8E4F0; border-radius:10px; overflow:hidden; }
th, td { text-align:left; padding:10px 12px; font-size:13px;
         border-bottom:1px solid #F0EDF6; }
th { background:var(--brand-soft); color:var(--brand); font-weight:600; }
tr:last-child td { border-bottom:none; }
.num { text-align:right; font-variant-numeric:tabular-nums; }
.badge { display:inline-block; padding:2px 8px; border-radius:999px;
         font-size:11px; font-weight:600; }
.badge.ativo { background:#E7F4E8; color:var(--ok); }
.badge.pausado { background:#F3F0E7; color:#8A6D1A; }
.badge.expirado { background:#F3E9EC; color:var(--bad); }
.badge.quebrado { background:#FCEBEA; color:var(--bad); }
.bar { height:8px; border-radius:4px; background:var(--brand);
       min-width:2px; }
.grid { display:grid; gap:2px; }
.grid-row { display:grid; grid-template-columns:150px repeat(30,1fr);
            align-items:center; gap:2px; margin-bottom:4px; }
.grid-label { font-size:12px; color:var(--ink-soft); overflow:hidden;
              text-overflow:ellipsis; white-space:nowrap; }
.cell { height:18px; border-radius:3px; display:flex; align-items:center;
        justify-content:center; font-size:9px; color:transparent; }
.cell.click { background:var(--brand); opacity:0.85; }
.cell.click:hover { color:#fff; }
.cell.zero { background:#EDEAF3; }
.cell.empty { background:#F6F4FA; color:var(--ink-soft); font-size:10px; }
.legend { font-size:12px; color:var(--ink-soft); margin-top:8px; }
.legend .cell { display:inline-flex; width:18px; margin-right:4px;
                vertical-align:middle; }
.export { display:inline-block; margin-top:10px; font-size:13px;
          color:var(--brand); background:var(--brand-soft);
          padding:8px 14px; border-radius:8px; text-decoration:none; }
.alert { color:var(--warn); font-size:12px; }
footer { margin-top:48px; color:var(--ink-soft); font-size:12px; }
"""


def _bar(largura_pct):
    pct = max(1.0, min(100.0, largura_pct))
    return f'<div class="bar" style="width:{pct:.1f}%"></div>'


def render(modelo, csv_data_uri):
    r = modelo["report_date"].isoformat()
    m = modelo

    linhas_top = ""
    max_30 = max((tl["clicks"][30] for tl in m["top_links"]), default=0) or 1
    for i, tl in enumerate(m["top_links"], start=1):
        alerta = ' <span class="alert" title="health warning">&#9888;</span>' \
            if tl["saude"] == "warning" else ""
        linhas_top += (
            f'<tr><td>{i}</td>'
            f'<td>{escape(tl["name"])} <span style="color:var(--ink-soft)">'
            f'/t/{escape(tl["slug"])}</span></td>'
            f'<td><span class="badge {tl["status"]}">{tl["status"]}</span>{alerta}</td>'
            f'<td class="num">{tl["clicks"][7]}</td>'
            f'<td class="num">{tl["clicks"][30]}</td>'
            f'<td class="num">{tl["clicks"][90]}</td>'
            f'<td>{_bar(100.0 * tl["clicks"][30] / max_30)}</td></tr>'
        )

    linhas_origem = ""
    max_origem = max((v for _, v in m["top_origens"][30]), default=0) or 1
    origens_7 = dict(m["top_origens"][7])
    origens_90 = dict(m["top_origens"][90])
    for (fonte, meio), total in m["top_origens"][30]:
        linhas_origem += (
            f'<tr><td>{escape(fonte)}</td><td>{escape(meio)}</td>'
            f'<td class="num">{origens_7.get((fonte, meio), 0)}</td>'
            f'<td class="num">{total}</td>'
            f'<td class="num">{origens_90.get((fonte, meio), 0)}</td>'
            f'<td>{_bar(100.0 * total / max_origem)}</td></tr>'
        )

    linhas_status = ""
    for tl in m["top_links"]:
        linhas_status += (
            f'<tr><td>{escape(tl["name"])}</td>'
            f'<td><span class="badge {tl["status"]}">{tl["status"]}</span></td>'
            f'<td>{escape(tl["saude"])}</td>'
            f'<td class="num">{m["conversoes"].get(tl["slug"], {}).get("lead", 0)}</td>'
            f'<td class="num">{m["conversoes"].get(tl["slug"], {}).get("purchase", 0)}</td>'
            f'<td class="num">{tl["clicks"][30]}</td></tr>'
        )

    linhas_grid = ""
    for serie in m["serie_top5"]:
        celulas = ""
        for dia, valor in serie["dias"]:
            if valor is None:
                celulas += '<div class="cell empty" title="no data">—</div>'
            elif valor == 0:
                celulas += '<div class="cell zero" title="0 clicks">0</div>'
            else:
                celulas += f'<div class="cell click" title="{dia.isoformat()}: {valor}">·</div>'
        linhas_grid += (
            f'<div class="grid-row"><div class="grid-label">'
            f'{escape(serie["name"])}</div>{celulas}</div>'
        )

    def total_janela(n):
        # serie_global covers 90 days ending at report_date; the window totals
        # come from the aggregate sums per link (same source of truth).
        return sum(tl["clicks"][n] for tl in m["top_links"])

    resumo = (
        f'<tr><td><strong>Total de cliques</strong></td>'
        f'<td class="num"><strong>{total_janela(7)}</strong></td>'
        f'<td class="num"><strong>{total_janela(30)}</strong></td>'
        f'<td class="num"><strong>{total_janela(90)}</strong></td><td></td></tr>'
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Tracking dashboard — {r}</title>
<style>{CSS}</style>
</head>
<body>
<div class="wrap">
<header>
  <h1>Tracking dashboard</h1>
  <p>Report date: {r} · generated by scripts/gerar-dashboard.py ·
     My_UTMs_Make_Me_Proud</p>
</header>

<h2>1 · Clicks per link, per period</h2>
<table>
  <tr><th>#</th><th>Link</th><th>Status</th>
      <th class="num">7d</th><th class="num">30d</th><th class="num">90d</th><th></th></tr>
  {linhas_top}
  {resumo}
</table>
<a class="export" href="{csv_data_uri}" download="links.csv">Export links (CSV)</a>

<h2>2 · Clicks per origin / channel</h2>
<p style="font-size:12px;color:var(--ink-soft);margin-bottom:8px">
UTM snapshots from click events — editing a link never rewrites history.</p>
<table>
  <tr><th>Source</th><th>Medium</th><th class="num">7d</th>
      <th class="num">30d</th><th class="num">90d</th><th></th></tr>
  {linhas_origem}
</table>

<h2>3 · Conversions per link</h2>
<p style="font-size:12px;color:var(--ink-soft);margin-bottom:8px">
Attribution ids joined at export time, by conversion point.</p>
<table>
  <tr><th>Link</th><th>Status</th><th>Health</th>
      <th class="num">Leads</th><th class="num">Purchases</th>
      <th class="num">Clicks (30d)</th></tr>
  {linhas_status}
</table>

<h2>4 · Series over time — last 30 days, top 5 links</h2>
<div class="grid">
  {linhas_grid}
</div>
<div class="legend">
  <span class="cell click">·</span> clicks &nbsp;
  <span class="cell zero">0</span> measured zero &nbsp;
  <span class="cell empty">—</span> no data
</div>
<p class="legend" style="margin-top:10px">Absence is never zero: a gap
renders as —, a measured zero as 0.</p>

<footer>My_UTMs_Make_Me_Proud · reference dashboard · MIT</footer>
</div>
</body>
</html>
"""
    return html


def gerar(dados, caminho_saida):
    erros = validar(dados)
    if erros:
        for e in erros:
            print(f"ERRO: {e}", file=sys.stderr)
        raise SystemExit(1)
    modelo = construir(dados)
    csv_texto = csv_links(dados, modelo)
    csv_uri = ("data:text/csv;base64," +
               base64.b64encode(csv_texto.encode("utf-8")).decode("ascii"))
    html = render(modelo, csv_uri)
    with open(caminho_saida, "w", encoding="utf-8") as f:
        f.write(html)
    return modelo


# ---------------------------------------------------------------------------
# Self-test — the ledger of bugs that were real (same philosophy as the validator)

def _fixture():
    return {
        "links": [
            {"slug": "lp-a", "name": "Link A", "destination_url": "https://ex.com/lp/a",
             "utm_source": "cfgauss", "utm_medium": "referral", "utm_campaign": "lp-a",
             "is_active": True, "expires_at": None, "saude": "healthy"},
            {"slug": "lp-b", "name": "Link B", "destination_url": "https://ex.com/lp/b",
             "utm_source": "cfgauss", "utm_medium": "referral", "utm_campaign": "lp-b",
             "is_active": False, "expires_at": None, "saude": "healthy"},
            {"slug": "lp-c", "name": "Link C", "destination_url": "https://ex.com/lp/c",
             "utm_source": "cfgauss", "utm_medium": "referral", "utm_campaign": "lp-c",
             "is_active": True, "expires_at": None, "saude": "broken"},
            {"slug": "lp-d", "name": "Link D", "destination_url": "https://ex.com/lp/d",
             "utm_source": "cfgauss", "utm_medium": "referral", "utm_campaign": "lp-d",
             "is_active": True, "expires_at": "2026-08-01T00:00:00Z", "saude": "healthy"},
            {"slug": "lp-e", "name": "Link E", "destination_url": "https://ex.com/lp/e",
             "utm_source": "cfgauss", "utm_medium": "referral", "utm_campaign": "lp-e",
             "is_active": False, "expires_at": "2026-08-01T00:00:00Z", "saude": "broken"},
        ],
        "daily_aggregates": [
            # Link A: clicks on 08-16 and 08-18, 08-17 deliberately missing.
            {"slug": "lp-a", "day": "2026-08-16", "clicks": 5},
            {"slug": "lp-a", "day": "2026-08-18", "clicks": 2},
            # Link A: an old click outside the 7d window but inside 30d.
            {"slug": "lp-a", "day": "2026-07-25", "clicks": 3},
            # Link B: measured zero on the report date.
            {"slug": "lp-b", "day": "2026-08-18", "clicks": 0},
            # Link C: one click, inside 7d.
            {"slug": "lp-c", "day": "2026-08-15", "clicks": 1},
        ],
        "events": [
            {"slug": "lp-a", "clicked_at": "2026-08-18T10:00:00Z",
             "utm_source": "instagram", "utm_medium": "social",
             "utm_campaign": "lp-a", "referrer_host": "instagram.com",
             "device": "mobile"},
            {"slug": "lp-a", "clicked_at": "2026-08-18T11:00:00Z",
             "utm_source": "cfgauss", "utm_medium": "email",
             "utm_campaign": "lp-a", "referrer_host": "gmail.com",
             "device": "desktop"},
        ],
        "conversions": [
            {"slug": "lp-a", "type": "lead", "converted_at": "2026-08-18T12:00:00Z"},
            {"slug": "lp-a", "type": "lead", "converted_at": "2026-08-18T13:00:00Z"},
            {"slug": "lp-a", "type": "purchase", "converted_at": "2026-08-18T14:00:00Z"},
            {"slug": "lp-c", "type": "lead", "converted_at": "2026-08-18T15:00:00Z"},
        ],
    }


def _sistema_de_teste():
    casos = []

    def caso(nome):
        def decorator(fn):
            def _run():
                fn()
            _run.__name__ = nome
            casos.append((nome, _run))
            return _run
        return decorator

    @caso("dia ausente -> — ; zero medido -> 0")
    def _1():
        dados = _fixture()
        modelo = construir(dados)
        # série do Link A na janela de 30 dias: 08-17 ausente, sem linha zero.
        serie_a = next(s for s in modelo["serie_top5"] if s["slug"] == "lp-a")
        por_dia = dict(serie_a["dias"])
        assert por_dia[date(2026, 8, 17)] is None, "dia sem linha deve ser None"
        assert por_dia[date(2026, 8, 18)] == 2
        serie_b = next(s for s in modelo["serie_top5"] if s["slug"] == "lp-b")
        por_dia_b = dict(serie_b["dias"])
        assert por_dia_b[date(2026, 8, 18)] == 0, "zero medido deve ser 0"
        # Render: ausência vira '—', zero vira célula zero.
        csv_uri = "data:text/csv;base64,"
        html = render(modelo, csv_uri)
        assert '<div class="cell empty" title="no data">—</div>' in html
        assert '<div class="cell zero" title="0 clicks">0</div>' in html

    @caso("calendar-fill: janela de 30 dias sempre tem 30 células")
    def _2():
        modelo = construir(_fixture())
        for serie in modelo["serie_top5"]:
            assert len(serie["dias"]) == 30

    @caso("editar UTM do link não reescreve origem (snapshot vence)")
    def _3():
        dados = _fixture()
        antes = construir(dados)["top_origens"]
        dados["links"][0]["utm_source"] = "alterado"
        dados["links"][0]["utm_medium"] = "alterado"
        depois = construir(dados)["top_origens"]
        assert antes == depois, "origem deve vir do snapshot do evento"

    @caso("filtro 7/30/90 respeitado")
    def _4():
        modelo = construir(_fixture())
        a = next(tl for tl in modelo["top_links"] if tl["slug"] == "lp-a")
        # 08-16 e 08-18 dentro de 7d; 07-25 fora de 7d mas dentro de 30d.
        assert a["clicks"][7] == 7
        assert a["clicks"][30] == 10
        assert a["clicks"][90] == 10

    @caso("conversões por slug; zero é explícito, não ausente")
    def _5():
        modelo = construir(_fixture())
        assert modelo["conversoes"]["lp-a"] == {"lead": 2, "purchase": 1}
        assert modelo["conversoes"]["lp-b"] == {"lead": 0, "purchase": 0}

    @caso("precedência de status: pausado > expirado > quebrado > ativo")
    def _6():
        modelo = construir(_fixture())
        por_slug = {tl["slug"]: tl["status"] for tl in modelo["top_links"]}
        assert por_slug["lp-a"] == "ativo"
        assert por_slug["lp-b"] == "pausado"
        assert por_slug["lp-c"] == "quebrado"
        assert por_slug["lp-d"] == "expirado"
        assert por_slug["lp-e"] == "pausado", "pausado vence expirado/quebrado"

    @caso("input inválido -> erro nomeado, exit 1")
    def _7():
        dados = _fixture()
        del dados["links"][0]["destination_url"]
        assert any("destination_url" in e for e in validar(dados))
        dados2 = _fixture()
        dados2["daily_aggregates"].append(
            {"slug": "lp-fantasma", "day": "2026-08-18", "clicks": 1})
        assert any("slug desconhecido" in e for e in validar(dados2))
        dados3 = _fixture()
        dados3["daily_aggregates"][0]["clicks"] = -1
        assert any("clicks" in e for e in validar(dados3))
        import contextlib
        try:
            with contextlib.redirect_stderr(io.StringIO()):
                gerar(dados, "/tmp/nao-importa.html")
            raise AssertionError("gerar deveria sair com exit 1")
        except SystemExit as exc:
            assert exc.code == 1

    @caso("CSV embutido decodifica para as linhas esperadas")
    def _8():
        dados = _fixture()
        modelo = construir(dados)
        csv_texto = csv_links(dados, modelo)
        linhas = list(csv.reader(io.StringIO(csv_texto)))
        assert linhas[0][0] == "slug"
        por_slug = {l[0]: l for l in linhas[1:]}
        assert len(por_slug) == 5
        assert por_slug["lp-a"][-1] == "1"          # purchases
        assert por_slug["lp-a"][-2] == "2"          # leads
        assert por_slug["lp-b"][-2] == "0"          # explicit zero
        assert por_slug["lp-e"][9] == "pausado"     # derived status column

    return casos


def _self_test():
    falhas = 0
    for nome, fn in _sistema_de_teste():
        try:
            fn()
            print(f"ok  {nome}")
        except Exception as exc:
            falhas += 1
            print(f"FAIL {nome}: {exc}")
    print(f"\n{len(_sistema_de_teste()) - falhas}/{len(_sistema_de_teste())} "
          "casos passaram")
    if falhas:
        raise SystemExit(1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", help="JSON de export das camadas de armazenamento")
    parser.add_argument("--output", default="dashboard/index.html",
                        help="caminho do HTML gerado")
    parser.add_argument("--self-test", action="store_true",
                        help="roda a suíte de regressão")
    args = parser.parse_args()

    if args.self_test:
        _self_test()
        return
    if not args.input:
        parser.error("--input é obrigatório (ou use --self-test)")
    with open(args.input, encoding="utf-8") as f:
        dados = json.load(f)
    modelo = gerar(dados, args.output)
    print(f"OK: {len(modelo['top_links'])} links, report_date "
          f"{modelo['report_date']} -> {args.output}")


if __name__ == "__main__":
    main()
