# Stage 4 — Health

Health is a scheduled probe that keeps every tracking link honest: a broken link is a lost click and a broken promise. The probe must be strict about what it measures and honest about what it cannot.

## The run

- **Batch**: up to 100 links per run, limited concurrency (6 in the reference implementation). A run must fit its time budget; overflow is reported (`truncated`), never silently dropped.
- **Double probe**: a primary HEAD request, confirmed by a second check (browser-level confirmation in the reference). One probe alone mislabels transient failures.
- **States** per link: `unchecked` → `healthy` | `warning` | `broken`, plus recorded `health_http_status`, `health_checked_at`, and `health_error_code`.

## SSRF guard (mandatory before any probe)

The probe fetches destinations **it does not control**. Before resolving a host:

1. Block private/loopback/link-local/multicast IPv4 and IPv6 ranges (RFC1918, etc.).
2. Intercept DNS resolution and reject any hostname resolving to a blocked IP — error `private_host`.
3. **Redirects: either follow with the guard re-run on EVERY hop, or do not follow at all.** A destination that 302-redirects to `http://169.254.169.254/` (or any RFC1918 host) bypasses the guard entirely if only the initial host is checked. The reference implementation does not follow redirects.

A probe without this guard is a server-side request forgery vector pointed at your own infrastructure.

## Systemic failure detection (the datacenter lesson)

**Real failure mode, measured 2026-08-16:** Instagram, LinkedIn, and Skool actively block the egress IP ranges of known datacenters (Vercel, AWS, GCP). The same links were 100% healthy from a residential network and intermittently failed from the datacenter — fast connections refused in under 250 ms, not timeouts.

Rules derived from that incident:

1. **Detect the pattern, not the individual link.** When ≥5 links across ≥3 hostnames fail in the same run with the same systemic signature, the hostnames are flagged as blocked-by-datacenter suspects.
2. **Isolate, don't destroy.** Suspected links are skipped with their prior state preserved and counted separately (`datacenterBlocked`). The run does not fail, and the links do not get marked broken — a false `broken` would alarm on links that are healthy for real visitors.
3. **Timeouts must be generous** (12 s primary / 25 s total in the reference). A short timeout mislabels slow-but-alive destinations.

## Alerts

- **Only on worsening.** An email fires when a link's state degrades (e.g. `healthy` → `warning`), not on every run. Alert fatigue is the fastest way to make real failures invisible.
- **Operational failure** alert when the run itself is unhealthy: `failures>0 || conflicts>0 || truncated`.
- The health report always includes the datacenter-blocked count so a spike there is never confused with broken links.

## Output contract

Per link: state, HTTP status, error code, checked-at. Per run: counts by state, datacenter-blocked count, truncated flag, alert sent or not. Health never mutates link data except the health columns themselves.
