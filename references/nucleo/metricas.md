# Stage 5 — Metrics

Metrics turn counted clicks into decisions. Two layers store, one layer reports, and one contract feeds the dashboard.

## Storage layers

1. **Daily aggregate** — one row per link per day: `clicks` (non-negative), `last_clicked_at`. Day boundaries in the business timezone (America/Sao_Paulo in the reference). This is the fast-answer layer for totals.
2. **Granular events** — one row per counted click: timestamp, destination snapshot, UTM snapshot (source/medium/campaign), referrer hostname only, device type (`desktop|mobile|tablet|other`). This is the truth layer for breakdowns.

Every counted click lands in both layers or in neither — never in one only.

## Analytics (7 / 30 / 90 days)

- **Daily series with calendar fill.** Every day in the window appears — a day without clicks is an explicit zero-shaped empty day, not a gap. **Absence is never zero**: "no data" and "zero clicks" are distinct states and must stay distinct in the report (a gap renders as `—`, a measured zero as `0`).
- **Top links** — by clicks in the window.
- **Top sources** — from the UTM source snapshot stored at click time (the snapshot, not the link's current UTM — an edited link must not rewrite history).
- **Devices** and **referrers** — from the granular events.

## Funnel view (per destination)

When the destination is a landing page, the funnel joins per-page events: views, CTA clicks, submits, conversions — plus tracking clicks and conversion rate, with sources from the events' metadata. This is what connects Stage 3 attribution to visible performance.

## The dashboard contract (what the tracking system EXPOSES)

A dashboard consumes exactly these five answers — nothing more is required of the tracking system:

| Question | Source |
|---|---|
| Clicks per link, per period | daily aggregate + events |
| Clicks per origin/channel | UTM snapshot on events |
| Conversions per link | attribution ids joined at conversion points |
| Link status (active/paused/expired/broken) | link row + health columns |
| Series over time | calendar-filled daily series |

## Reporting rules

- **History is immutable.** A UTM edit changes future attribution, never past snapshots.
- **Exports**: links export to CSV/XML. Individual click events are not bulk-exported (privacy).
- **A dashboard that cannot answer the five questions from stored data has not implemented this stage.**
