# Changelog

## [0.1.0] — 2026-09-04

- Initial release: packaged the personal `/criar-prd` command as a marketplace plugin.
- Ships its own `templates/prd-template.md`, resolved via `${CLAUDE_PLUGIN_ROOT}` — a
  project-local `templates/prd-template.md` still wins when present. Without this the
  command referenced a template no consumer had.
- Feature slug validated as a single kebab-case segment before it reaches any path.
