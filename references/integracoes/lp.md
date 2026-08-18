# Integration — Landing Pages

The landing-page system is the **first integration** of the tracking core. This contract defines how LP-produced links are created, kept consistent, and consumed. It mirrors the production binding at CF Gauss; where the production system is stricter than the portable skill, the difference is stated.

## Who produces the links

A landing page publishes a campaign, and the campaign owns the tracking link. One published LP → one campaign → one tracking link (plus its thank-you page's tracking if the LP defines one).

## The binding

- The link row carries a `landing_page_id` foreign key to the LP row (`on delete restrict` — a link cannot be orphaned silently).
- The destination is detected from the URL shape: only an exact `https://<host>/lp/<slug>` destination binds the link to that LP (strict https — near-misses must not bind).
- Saving a link resolves `slug → LP id` from the destination and stores the binding.

## Atomic bundle (the core guarantee)

LP main page, thank-you page, offer, campaign, and tracking link are written **in one transaction** — "the LP, its campaign, and its tracking link are a single write". No intermediate state exists where the LP is published but its link is missing.

Bundle rules:

- The campaign slug is deterministic from the LP slug and the campaign name (the reference derives `slugTrackingCampanhaLp(campaignName, lpSlug)`).
- `destination_url` must be exactly `https://<host>/lp/<lpSlug>` and `tracked_destination_url` must equal destination + UTMs (`utm_source=cfgauss`, `utm_medium=referral` in the reference) — mismatches are rejected.
- The thank-you page is optional but, when present, must be complete.
- Collisions are named errors, never silent overwrites: `campaign_slug_collision` (same campaign slug, different LP) and `tracking_slug_collision` (existing link slug pointing at a different LP or campaign).
- Re-saving is idempotent: the link is upserted by slug.

## Publication gate

**Production (CF Gauss):** publishing an LP requires an active tracking link with a campaign — a deferred trigger rejects publication with `published_landing_page_requires_tracking_campaign` when the link is missing, and reactivates link + campaign + offer when they exist but are paused.

**Portable skill:** the gate is the **recommended standard**, not a mandatory step — an LP implementation without a tracking system still publishes. When both systems exist, apply the production behavior: no LP goes live untracked.

## Meta Pixel

The LP's Meta Pixel resolves through the binding: link → campaign → `meta_pixel_id`. When the chain is missing, the pixel degrades to null and the LP renders without it — a missing pixel never breaks the page.

## Documented absence (do not invent)

**Slug rename does not propagate.** Renaming an LP's slug does **not** automatically update its tracking links' `destination_url`, `tracked_destination_url`, or binding. The production system re-establishes consistency on the next bundle save (which revalidates and upserts). Any implementation that promises automatic propagation must build it; this contract documents the real behavior, not the ideal one.

## What the LP consumes from the core

- Stage 2 (click) — the short URL for every campaign link.
- Stage 3 (attribution) — first/last click recorded on lead events and purchases.
- Stage 5 (metrics) — the dashboard contract for issued LPs.
