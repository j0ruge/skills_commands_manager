# Changelog — codereview

Formato: [Semantic Versioning](https://semver.org/)

## [1.0.0] - 2026-03-13

### Adicionado

- Skill de code review automatizado pré-PR inspirado no Zen of Python (PEP 20)
- Análise de diffs com severidades CRITICO/ALTO/MEDIO/BAIXO
- 5 princípios Zen como lentes de análise (readability, explicit, simple, flat, error handling)
- Passes de detecção: bugs, segurança, performance, type safety
- Avaliação de cobertura de testes (COM_TESTE / TESTE_DESATUALIZADO / SEM_TESTE)
- Nota final por letra (A-F) com critérios por categoria
- Stack-agnostic com defaults TypeScript/React configuráveis
- `references/report-template.md` — template completo do relatório
- `references/configuration.md` — valores default e sintaxe de override

---

## Histórico Pré-Marketplace

A skill existia como v2.0.0 informal no repositório `digital_service_report_frontend` (sem disciplina semver). O histórico abaixo documenta a evolução antes da publicação no marketplace.

- **v2.0.0** (2026-03-10): Reescrita completa — classificação de arquivos por categoria, progressive disclosure via references, override de configuração stack-agnostic, grading scale A-F, cap de 50 findings
- **v1.0.0** (2026-03): Versão inicial com análise básica de diffs e relatório estruturado
