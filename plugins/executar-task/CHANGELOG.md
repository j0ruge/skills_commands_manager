# Changelog

## [0.1.0] — 2026-09-04

- Initial release: packaged the personal `/executar-task` command as a marketplace plugin.
- Decoupled from the origin project: the fixed `.agents/rules/*.md` list, the `graphify`
  CLI, the hardcoded `yarn test` / `npx playwright test` / `yarn qa` commands, the
  `docs/notas/…` and `docs/stack_tec.md` paths, the JSDoc-in-pt-BR requirement and the
  Vite env rule now resolve against whatever the target project actually uses — the test
  command is discovered from the build manifest instead of assumed.
- Feature slug validated as a single kebab-case segment, and the task number as an integer,
  before either reaches a path.
