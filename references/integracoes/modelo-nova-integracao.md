# New integration template

The tracking core is channel-agnostic. Plugging a new channel (email, workshops, ads, WhatsApp, anything that sends visitors somewhere) means writing **one file** in `references/integracoes/` — the core never changes.

Copy this structure, fill each section, and follow the versioning rule: a new integration is a MINOR bump.

## Sections

### 1. Who produces the links

Which system creates tracking links and under what lifecycle (e.g. one link per email campaign, one per ad variant). Name the binding: what foreign key or identifier ties the link to the producer's entity.

### 2. Slug and UTM conventions

- Slug convention for this channel (prefix or pattern), if any — the reference email convention (see `mailmkt.md`) is `mailmkt-`-prefixed, idempotent per campaign, created once per campaign run.
- Default `utm_source` / `utm_medium` for the channel (or the inference rule when the creator does not state them).

### 3. Destination rules specific to the channel

Anything the channel adds beyond the core rules (no credentials, no `/t/` loops). Empty when the core rules suffice.

### 4. Conversion points

Where this channel's visitors become leads or customers, and that each such point reads the attribution cookie (Stage 3). If the channel has no own conversion points, state that conversions flow through the LP's points.

### 5. Metrics consumed

Which of the five dashboard answers this channel reads, and any channel-specific breakdown it needs (e.g. email: clicks per `mailmkt` campaign slug).

### 6. Documented absences

What the channel's production system does **not** do automatically (like the LP slug-rename absence). Honest absences prevent fabricated features.

## What an integration must NOT do

- Rewrite or contradict the core references — the core is the source of truth for counting, attribution, health, and metrics.
- Invent bindings that do not exist in the producer's system.
- Make its conventions mandatory for other integrations.

## After writing

1. Add the file to `README.md` (integrations section) and `CHANGELOG.md` (`### Added`).
2. Version bump: **MINOR**.
