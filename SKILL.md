---
name: my-utms-make-me-proud
description: Full tracking-link cycle — create links (individual, bulk, or all pages of a campaign), route clicks with strict counting rules, attribute first/last click to leads and purchases, monitor link health, and measure clicks. Channel-agnostic core; landing pages are the first integration. Use when creating, validating, or monitoring marketing tracking links, UTM parameters, click attribution, or link health for any channel (landing pages, email, workshops, ads, WhatsApp).
---

# Tracking-link cycle

Orchestrates the five stages of a tracking link: Creation → Click → Attribution → Health → Metrics. Each stage has its own reference and an output contract. The core is channel-agnostic: any marketing system (landing pages, email, workshops, ads, WhatsApp) produces links this skill creates, routes, attributes, watches, and measures.

Load only the references of the stage being executed.

## Modes

- **Full cycle** — default when asked to set up or operate tracking for a marketing initiative.
- **Single stage** — when asked only to create a link, check health, or read metrics, execute that stage alone.

## Integrations

Integrations are pluggable contracts in `references/integracoes/`. Each defines how one marketing system (landing pages first) produces links and consumes metrics. Adding an integration never rewrites the core — follow `references/integracoes/modelo-nova-integracao.md`.

## Global hard rules (apply to every stage)

1. **Metrics never block the visitor.** Counting, attribution, or analytics failures are logged; the redirect always proceeds.
2. **Bots, prefetch, and HEAD never count.**
3. **No `/t/` loops.** A destination must never point to another tracking link.
4. **UTMs are mandatory.** source, medium, and campaign always present.
5. **Absence is never zero.** A day without clicks is an explicit empty day in reports — never a silent 0 that reads as failure.
6. **Admin access only.** Link data is owner-only (deny-all RLS; service-role RPCs only). Never expose link rows to anonymous visitors.
7. **Never invent a destination.** A link is created only for a destination the requester stated or that exists in the system.

## Stage 1 — Creation

Load `references/nucleo/criacao.md`.

**Output contract:**
- A link draft with slug, destination, tracked destination (destination + UTMs), and lifecycle fields — valid under `python3 scripts/validar-tracking-link.py  # rode da RAIZ da skill
- The three creation modes applied when applicable: individual, bulk (up to 25), all pages of a campaign (up to 250, atomic batch).
- Optimistic concurrency and audit-trail requirements stated.
- The draft is delivered for human review. **Creation never activates a link on its own.**

## Stage 2 — Click

Load `references/nucleo/clique.md`.

**Output contract:**
- The short route `/t/<slug>` behavior: what counts (real visitor clicks), what never counts (bots, prefetch, HEAD), the 30-second per-slug cookie dedup, the resolve → record → redirect order, and the redirect headers (`no-store`, `noindex, nofollow`, `no-referrer`).
- The attribution cookie contract: HMAC-sealed, 90 days, first/last click.

## Stage 3 — Attribution

Load `references/nucleo/atribuicao.md`.

**Output contract:**
- Every conversion point (lead form, checkout) reads the attribution cookie and records first/last click ids.
- The join click → link → campaign resolves first/last touch from link to purchase.

## Stage 4 — Health

Load `references/nucleo/saude.md`.

**Output contract:**
- A health-check run: batch of up to 100 links, double probe (HEAD + confirmation), states `unchecked|healthy|warning|broken`.
- SSRF guard active; systemic failure detection applied (≥5 suspects across ≥3 hostnames → preserve prior state, count as datacenter-blocked, do not fail the run).
- Alerts only on state worsening or operational failure (`failures>0 || conflicts>0 || truncated`).

## Stage 5 — Metrics

Load `references/nucleo/metricas.md`.

**Output contract:**
- Daily aggregate + granular events (device, referrer hostname, UTM snapshot).
- Analytics over 7/30/90 days: calendar-filled daily series (absence is never zero), top links, sources, devices, referrers.
- What the tracking system exposes for a dashboard: clicks per link, origin/channel, period, conversions.

## Versioning

This skill is versioned with SemVer — see `references/versionamento.md` and `CHANGELOG.md`. Report which version you are executing when starting a session that loads this skill.
