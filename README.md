# My_UTMs_Make_Me_Proud

**The full tracking-link cycle: create, click, attribute, health, and metrics — channel-agnostic and rules-first at every stage.**

Create tracking links in three modes (individual, bulk, all pages of a campaign), route clicks with strict counting rules, attribute first/last click to leads and purchases, watch link health with a datacenter-aware probe, and measure clicks with calendar-filled analytics.

[Download the skill](https://github.com/luisroquette/My_UTMs_Make_Me_Proud/archive/refs/heads/main.zip) · [Install for Codex](#install) · [Integrations](references/integracoes/) · [Changelog](CHANGELOG.md)

> Independent open-source implementation of the tracking-link system built at CF Gauss. This project is not affiliated with any analytics or advertising vendor.

## The cycle

| Stage | What it does | Reference |
|---|---|---|
| 1. Creation | Individual, bulk (≤25), or all pages of a campaign (≤250, atomic batch); slug normalization, UTM inference, destination safety | `references/nucleo/criacao.md` |
| 2. Click | Short route `/t/<slug>`; bots/prefetch/HEAD excluded, 30 s dedup; metrics never block the redirect | `references/nucleo/clique.md` |
| 3. Attribution | HMAC-sealed 90-day cookie; first/last click recorded at lead forms and checkouts | `references/nucleo/atribuicao.md` |
| 4. Health | Batch probe (double check), SSRF guard, systemic datacenter-block detection, alerts on worsening only | `references/nucleo/saude.md` |
| 5. Metrics | Daily aggregate + granular events; calendar-filled 7/30/90 analytics; the contract a dashboard consumes | `references/nucleo/metricas.md` |

Landing pages are the first integration (`references/integracoes/lp.md`) — the same pattern plugs any future channel: email, workshops, ads, WhatsApp.

## Why it holds up

- **Metrics never block the visitor** — a failed counter never breaks the redirect.
- **Strict counting** — bots, prefetch, and HEAD never inflate clicks; 30 s dedup per slug.
- **No `/t/` loops** — a destination can never point to another tracking link.
- **Absence is never zero** — a clickless day is an explicit empty day, not a silent failure.
- **Health that tells the truth** — a datacenter-wide block (Instagram, LinkedIn, Skool) is detected and isolated instead of failing the whole run.

## Install

### Codex

```bash
git clone https://github.com/luisroquette/My_UTMs_Make_Me_Proud.git ~/.codex/skills/my-utms-make-me-proud
```

Then ask:

```text
Use $my-utms-make-me-proud to create a tracking link for this campaign and report its metrics.
```

### Claude Code

```bash
git clone https://github.com/luisroquette/My_UTMs_Make_Me_Proud.git ~/.claude/skills/my-utms-make-me-proud
```

Claude Code ignores the Codex-specific `agents/openai.yaml` file.

### Manual download

Download the [ZIP archive](https://github.com/luisroquette/My_UTMs_Make_Me_Proud/archive/refs/heads/main.zip), extract it, rename the folder to `my-utms-make-me-proud`, and move it into your agent's skills directory.

## Files

```text
SKILL.md                          Cycle orchestrator and output contracts
references/nucleo/                Stages 1-5: creation, click, attribution, health, metrics
references/integracoes/           Channel contracts (LP first) + new-integration template
references/versionamento.md       SemVer policy for the skill
scripts/validar-tracking-link.py  Deterministic link form validator (no LLM)
examples/                         Example inputs for the validator
CHANGELOG.md                      Keep a Changelog
```

The skill loads only `references/` and `scripts/` during execution. `docs/` holds internal specs and plans as an audit trail.

## The suite vision

This skill is the **tracking layer** of a marketing suite. [My_LP_Makes_Neil_Proud](https://github.com/luisroquette/My_LP_Makes_Neil_Proud) (landing pages) plugs into it as its first integration, and the issued-LP dashboard consumes its metrics contract. Future marketing features join the suite through `references/integracoes/` — the core never rewrites.

## Versioning

Versioned with [Semantic Versioning 2.0.0](https://semver.org/): MAJOR when the skill's contract changes, MINOR for new compatible stages or integrations, PATCH for corrections. Current release: **1.0.0**. See `references/versionamento.md` and `CHANGELOG.md`.

## Safe by default

The skill never activates a link, changes a destination, or alerts on data it has not verified. A failed metric write is logged and the redirect proceeds. Missing data is an explicit empty day, never a silent zero.

## License

MIT. Use it, adapt it, and make marketing measurable.
