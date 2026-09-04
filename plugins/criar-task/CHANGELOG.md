# Changelog

## [0.1.0] — 2026-09-04

- Initial release: packaged the personal `/criar-task` command as a marketplace plugin.
- Ships `templates/tasks-template.md` and `templates/task-template.md`, resolved via
  `${CLAUDE_PLUGIN_ROOT}`, with project-local templates taking precedence.
- Feature slug validated as a single kebab-case segment before it reaches any path.
