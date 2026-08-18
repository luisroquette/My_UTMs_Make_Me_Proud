# Stage 2 — Click

The click path is the only public surface of the system: a short route (`/t/<slug>`) that resolves, records, and redirects — in that order, with counting rules that keep the number honest.

## The route

- `GET /t/<slug>` — resolves and counts (when countable).
- `HEAD /t/<slug>` — resolves, never counts (health probes and link previews must not inflate clicks).

## Counting rules (hard)

1. **Bots never count.** Requests whose User-Agent matches the automated-client pattern are resolved but not recorded.
2. **Prefetch never counts.** Requests with prefetch purpose headers (`purpose: prefetch`, `next-router-prefetch`) are resolved but not recorded.
3. **HEAD never counts.**
4. **Dedup: one click per visitor per slug per 30 s.** A `clicks` cookie scoped to the path `/t/<slug>` with a 30-second max-age carries the server-generated `click_id`. A repeat within the window reuses the same `click_id` instead of creating a second click.

## Flow

1. **Validate** the slug against the slug regex. Invalid → 404.
2. **Resolve** the destination: active, not deleted, not expired. Resolve first, via the service-role resolver, with a direct-table fallback that re-checks expiry. If resolution fails → 404; if the whole mechanism is down → 503 "Tracking unavailable".
3. **Record** the click **in one transaction**: insert the granular event (idempotent on `click_id`) and increment the daily aggregate **only when the insert actually created the row** — detect the insert with `RETURNING (xmax = 0)` (an `ON CONFLICT DO UPDATE` also returns a row on replay). A replay must never re-increment: the granular event and the aggregate are one atomic unit, "both layers or neither".
4. **Redirect** 302 to `tracked_destination_url`.

**Metrics never block the visitor.** If recording fails, log it and redirect anyway. The redirect is the product; the metric is the side effect. This rule is absolute: no metric error may ever stand between a visitor and the destination.

## Redirect headers

Every redirect carries:

- `Cache-Control: no-store` — intermediaries must not cache the hop.
- `X-Robots-Tag: noindex, nofollow` — the tracking hop must not appear in search results.
- `Referrer-Policy: no-referrer` — the destination does not learn the referrer.

## Attribution cookie

After the click is recorded, write (or refresh) the attribution cookie:

- **HMAC-sealed** (HMAC-SHA256) — forged or tampered cookies are detected and rejected at conversion points.
- **90-day lifespan**, refreshed on each counted click.
- Payload: `first` click id (written once, never overwritten), `last` click id (every click), `touchedAt`.

The cookie is the bridge to Stage 3 — it is the only thing that survives the redirect.

## What the click path does NOT do

- **No query-string UTM reading.** UTMs live in `tracked_destination_url`, set at creation. A visitor cannot tamper with attribution by editing the URL.
- **No IP inspection, no geolocation.** Privacy by design; the referrer is reduced to its hostname before storage.
- **No counting of anything but real visitor clicks**, as defined by the rules above.
