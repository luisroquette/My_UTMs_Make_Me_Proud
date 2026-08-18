# Stage 3 — Attribution

Attribution answers one question: **which link brought the customer?** The answer comes from the sealed cookie written at click time, read at every conversion point.

## The conversion points

Every place where a visitor becomes a lead or a customer reads the attribution cookie:

| Conversion point | What it records |
|---|---|
| Lead form / lead event | `first_tracking_click_id`, `last_tracking_click_id` on the lead event row |
| Checkout / purchase (any product) | `first_marketing_click_id`, `last_marketing_click_id` on the purchase row |

The same cookie serves both: a click can produce a lead and, later, a purchase, and both carry the same first/last pair.

## The join

First/last touch resolves through a fixed join chain:

```
click id → tracking link → campaign
```

From a purchase, the join answers: which link was the first touch, which was the last, and which campaign owned each. That is the complete first-touch / last-touch attribution the dashboard consumes.

## Integrity rules

1. **The cookie is sealed.** Conversion points verify the HMAC before trusting it; a forged or corrupted cookie is treated as "no attribution" — never as data.
2. **First is first.** The `first` id is written once and never overwritten by later clicks; the `last` id is the most recent counted click.
3. **Absence is explicit.** A conversion with no attribution cookie records null attribution ids — it is "not attributable", never attributed to a random link and never silently dropped.
4. **Clicks and conversions live in different tables.** A conversion never mutates click data; the join is read-only.

## What attribution must NOT do

- Attribute a conversion to a link the visitor never clicked (no last-click-wins by proximity in time — only by the cookie's actual `last` id).
- Fabricate attribution when the cookie is absent (see rule 3).

## Contract

**The click is traceable from the link to the purchase.** Any implementation that cannot answer "which link produced this purchase" from stored data has not implemented this stage.
