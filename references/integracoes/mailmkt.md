# Integration — Email Marketing

The email engine is the **second integration** of the tracking core. This contract defines how email-produced links are created, reused, and consumed. It mirrors the production binding at CF Gauss (`lib/nurture/marketing/runner.ts` and the generic helper `lib/tracking-links/obter-ou-criar.ts`); where the production system is stricter than the portable skill, the difference is stated.

## Who produces the links

The campaign run produces the link, not the individual send. One campaign occurrence → one tracking link, created (or reused) **before** the per-lead send loop — one database call per campaign run, never per recipient. The production binding is **by slug convention**, not by foreign key: there is no `campaign_id` column on the link. The idempotent upsert by slug is what ties the link to the campaign.

Every email flow in the reference system follows this pattern: marketing campaigns, launch sequences (one link per step), digests (one link per article), checkout abandonment / payment reminders / cross-sell, and class notifications.

## Slug and UTM conventions

- Slug: `mailmkt-<campaign-identifier>` (lowercase, hyphenated — core normalization applies).
- `utm_campaign`: `mailmkt_<campaign-identifier>` — the channel prefix is mandatory; an unprefixed campaign is unreviewable at the origin.
- `utm_source`: `cfgauss` (host default); `utm_medium`: `email`.
- The generic helper `obterOuCriarTrackingLinkDeCanal({ canal, identificador, nome, destinationUrl, utmMedium, expiresAt? })` builds both values from the channel prefix; `mailmkt.ts` is a thin wrapper that pins `canal: "mailmkt"`, `utmMedium: "email"`.

## Destination rules specific to the channel

- **Double tracking.** Email keeps per-recipient click attribution in parallel: the CTA ships as the `/t/<slug>` link wrapped in the nurture click route (`/api/nurture/click`). The tracking_links layer answers "which link was clicked most across every channel"; the nurture layer answers "which recipient clicked". Neither replaces the other.
- **Send-time safety net.** The production gate (`urlsCruasDeDivulgacaoEm`) scans outgoing email text for raw `cfgauss.com.br` URLs and blocks the send — allowlist: `/t/`, `/api/nurture/click`, `/api/checkout/redeem`. A bypass that sneaks past code review dies at the gate instead of shipping an untracked link. In the portable skill this gate is the **recommended standard**, not a mandatory step.
- **Coupon links carry a token.** Abandonment and payment-reminder links embed the coupon token in `destination_url` and set `expires_at` to coupon start + 7 days — expired links stop redirecting by the core lifecycle rules.
- **Deliberate raw exceptions** (approved by the owner, 18/08/2026): unsubscribe links, dynamic wa.me support links, and relative checkout URLs stay raw by design.

## Conversion points

Email has no conversion points of its own. Visitors land on the LP and convert through the LP's points, which read the attribution cookie (Stage 3). Per-recipient open/click events live in the nurture event table and complement — never duplicate — the link ranking.

## Metrics consumed

The dashboard answer "which link was clicked most", broken down by `mailmkt` campaign slug. Per-recipient events answer "who clicked" and are reported by the email engine itself, not by the tracking core.

## Documented absence (do not invent)

**The link is not per-recipient.** All recipients of a campaign share the same `/t/<slug>`. Unique links per lead would make the global ranking meaningless; where per-recipient attribution is needed, the nurture layer provides it. Any implementation that promises per-lead tracked links must build it; this contract documents the real behavior, not the ideal one.

**Failure degrades, never blocks.** If link creation fails (database down), the email ships with the raw URL and an error log. Analytics may go blind for one run; delivery never stops. This is the core principle applied at the producer end.
