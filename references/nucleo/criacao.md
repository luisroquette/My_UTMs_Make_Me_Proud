# Stage 1 — Creation

Creating tracking links follows one contract in three modes. Everything below is a hard constraint; the agent applies it in any stack.

## Reference schema

The portable contract is the reference table shape. Field names here are the canonical names — an implementation may rename, but the constraints carry over unchanged.

| Field | Constraint |
|---|---|
| `id` | UUID, primary key |
| `name` | 1–100 chars, required |
| `slug` | Required, unique, `^[a-z0-9]+(-[a-z0-9]+)*$`, 1–80 chars |
| `destination_url` | Required, `^https?://`, ≤2048, no credentials, never another tracking link |
| `tracked_destination_url` | Required, `^https?://`, ≤4096 — the destination plus UTMs |
| `utm_source` / `utm_medium` / `utm_campaign` | Required, ≤120 each |
| `utm_content` / `utm_term` | Optional, ≤120 each |
| `is_active` | Boolean, default true |
| `expires_at` | Optional timestamp — expiry blocks resolution and counting |
| `deleted_at` | Soft delete timestamp |
| `created_at` / `updated_at` | Timestamps — `updated_at` is the concurrency token |

## Three creation modes

1. **Individual** — one link from two required inputs: campaign name + destination URL. Slug and UTMs are derived, not typed.
2. **Bulk** — up to 25 rows (name + URL each). Slugs derived from names; duplicates inside the batch are rejected before insert; an existing slug (unique violation) surfaces as "slug already exists", never silently overwrites.
3. **All pages of a campaign** — up to 250 targets from a known set (e.g. published landing pages of a campaign). One atomic batch: either every link is created or none is. Duplicate slugs inside the batch are rejected; per-target validation failure aborts the whole batch.

## Slug rules

- Normalize automatically: strip accents, lowercase, non-alphanumerics become hyphens, collapse repeated hyphens.
- When the normalized slug exceeds 80 chars, truncate it to `80 - len(hash)` and append a short deterministic hash (FNV-1a) — never truncate without the hash, plain truncation creates collisions between similar names. The final slug must stay within 1-80 chars.
- The hostname → utm_source inference map lives **per integration** (`integracoes/<canal>/`), not in the nucleus — each channel owns its mapping.
- Destination URLs must be **query-free**: the tracked URL is `destination_url + "?" + utm params`, so a destination that already carries a query string can never validate. Reject query strings on creation.
- The slug is the public identity (`/t/<slug>`). Renaming a slug changes a public URL: treat it as a destructive edit.

## UTM rules

- `utm_source`, `utm_medium`, `utm_campaign` are mandatory — a tracking link without them is not measurable per channel.
- When the creator does not state UTMs, infer: `utm_source` from the destination hostname (a maintained map hostname → source), `utm_medium` from the source (e.g. `referral`).
- `tracked_destination_url` = `destination_url` + `?utm_source=…&utm_medium=…&utm_campaign=…` (+ optional content/term). The visitor is sent to the tracked URL; the destination alone is never what gets tracked.

## Destination rules

- `^https?://` only, ≤2048 chars.
- No credentials embedded in the URL (`https://user:pass@…` rejected).
- Never point at another tracking link — a `/t/`-to-`/t/` chain is a loop and a metric black hole.

## Lifecycle

- A link is `active` or `paused` (`is_active`); deletion is soft (`deleted_at`) and reversible; `expires_at` blocks resolution and counting when passed.
- Pausing, deleting, restoring, duplicating (slug `-copia`, `-2`, … up to 99) and changing expiry are all mutations — same concurrency and audit rules.

## Optimistic concurrency

Every mutation carries the `updated_at` it read. If the stored value differs, the mutation is rejected — the link changed in another tab or process. Never blind-overwrite.

## Audit trail

Every mutation (create, update, duplicate, pause, activate, delete, restore, expiry change, export) records an audit event with actor, action, and target. A link whose history cannot be told is a link that cannot be trusted.

## Output contract

A draft link object with every field above — validated with `python3 scripts/validar-tracking-link.py --input <draft>.json` — delivered for human review. **Creation never activates a link on its own.**
