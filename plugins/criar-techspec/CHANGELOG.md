# Changelog

## [0.1.0] — 2026-09-04

- Initial release: packaged the personal `/criar-techspec` command as a marketplace plugin.
- Ships its own `templates/techspec-template.md`, resolved via `${CLAUDE_PLUGIN_ROOT}`, with
  a project-local template taking precedence. The missing-template hard stop is gone; a
  missing PRD still stops the command, since there is nothing to specify without one.
- Decoupled from the origin project: the fixed `.agents/rules/*.md` list, the `graphify`
  CLI, `docs/stack_tec.md` and the Vite-specific env rule became a discovery step over
  whatever conventions the target project actually has.
- Feature slug validated as a single kebab-case segment before it reaches any path.
