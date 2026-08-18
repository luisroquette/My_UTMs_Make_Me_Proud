# Changelog

All notable changes to this skill are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-08-18

### Added

- Full tracking-link cycle orchestration in `SKILL.md`: Creation → Click → Attribution → Health → Metrics.
- Core references (`references/nucleo/`):
  - `criacao.md` — three creation modes, slug normalization, UTM inference, destination safety, lifecycle, optimistic concurrency, audit trail.
  - `clique.md` — short route behavior, strict counting rules, 30 s dedup, attribution cookie.
  - `atribuicao.md` — first/last click from cookie to lead and purchase.
  - `saude.md` — batch health probe, SSRF guard, systemic datacenter-block detection, worsening-only alerts.
  - `metricas.md` — daily aggregate + granular events, calendar-filled analytics, dashboard contract.
- Integrations (`references/integracoes/`):
  - `lp.md` — landing-page contract (atomic bundle, publication gate, Meta Pixel, documented rename absence).
  - `modelo-nova-integracao.md` — template for plugging the next channel.
- `scripts/validar-tracking-link.py` — deterministic link form validation (no LLM).
- `examples/example-tracking-link.json` — validator example input.
- `references/versionamento.md` — SemVer policy for the skill itself.
- Codex support via `agents/openai.yaml`.
