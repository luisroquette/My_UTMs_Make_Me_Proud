# Versioning

This skill is versioned with [Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html): `MAJOR.MINOR.PATCH`.

## What each bump means for this skill

| Bump | Meaning | Examples |
|---|---|---|
| **MAJOR** | The skill's contract changes: stages are added or removed, the required output format changes, or existing behavior changes in a way that breaks prior usage. | Adding a stage that becomes mandatory. Removing a core reference. |
| **MINOR** | A new compatible capability: a new optional stage, a new reference file, a new integration in `references/integracoes/`, a new optional field. | Adding `integracoes/email.md`. |
| **PATCH** | Corrections with no behavior change: typo fixes, clarified wording, script bug fixes, dependency of nothing downstream. | Fixing `validar-tracking-link.py` regex escaping. |

## Release procedure

1. Update `CHANGELOG.md` — move the `[Unreleased]` section to the new version, following Keep a Changelog.
2. Commit on the release branch with a message naming the version.
3. Tag the final commit with `vX.Y.Z` (e.g. `git tag v1.0.0`).
4. Push the tag and create a GitHub Release with release notes matching the changelog entry.

## Rules

- Never reuse a tag. If a release is broken, bump PATCH.
- Never change released content in place — a fix to a released file is a new version.
- Integrations never rewrite the core. A new channel is a MINOR that adds a file under `references/integracoes/`.
- `docs/` (specs and plans) is an audit trail only. The skill never loads it during execution; only `references/` and `scripts/` are loaded.
