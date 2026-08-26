# Kaizen Log — skills_commands_manager

Registro de melhorias: o que mudou, por quê, e onde o aprendizado foi padronizado
para não se perder. Complementa os `CHANGELOG.md` de cada plugin — eles contam o
**o quê** por versão; aqui fica o **porquê de processo**.

---

## 2026-08-26 — Descriptions acima do cap: da dívida ao gate

**Problema:** 7 dos 16 plugins tinham `description` acima do cap de 500 chars do
`CLAUDE.md` — o pior com **871**. A `description` é a única superfície de
triggering: é por ela que o Claude decide invocar a skill. Texto longo dilui o
sinal e pode ser **cortado em silêncio** na lista `/skills`, piorando exatamente
o que deveria melhorar.

**Métrica de sucesso:** `scripts/validate-versions.py` com zero erros e zero
warnings.

### Gemba

Não foi suposição. `git log` no `plugin.json` de cada plugin mostrou o padrão:
**`codereview` tem 21 commits** no arquivo, `zitadel-idp` 12, `wsl-windows-onboarding` 6.
Cada retrofit acrescentava sua lição ao texto existente.

### 5 Porquês

1. Por que 7 descriptions passaram do cap? Cada retrofit **somou** a lição nova.
2. Por que somar em vez de reescrever? É mais barato acrescentar uma cláusula do
   que reequilibrar o texto inteiro.
3. Por que nada barrou? O cap era **warning**, não erro — não reprovava o gate.
4. Por que warning? Quando o cap foi criado, as descriptions **já** estavam acima;
   torná-lo erro reprovaria o repositório inteiro de imediato.
5. **Causa raiz (processo, não pessoa):** o padrão nasceu depois da deriva e foi
   aplicado como aviso. Aviso que nunca reprova vira ruído de fundo — todo mundo
   aprende a rolar a tela. **O padrão só se sustenta quando a dívida é zerada
   primeiro e o gate é fechado logo em seguida.**

### Antes → Depois

| Plugin                          | Antes | Depois |
| ------------------------------- | ----- | ------ |
| `wsl-windows-onboarding`        | 871   | 468    |
| `codereview`                    | 686   | 489    |
| `zitadel-idp`                   | 670   | 476    |
| `ansible-docker-backup-restore` | 593   | 473    |
| `dev-script`                    | 578   | 434    |
| `whisper-preprocess`            | 578   | 406    |
| `cicd` (divergente + acima)     | 756   | 473    |

Todos os **16** plugins agora cabem no cap. O corte foi **encurtar, não resumir
mecanicamente**: saiu enumeração de detalhe (mensagens de erro literais, nomes de
ferramentas alternativas, exemplos), que continua no corpo da skill; ficaram o que
a skill faz e os diferenciais que a distinguem das vizinhas.

### Muda eliminado

Aplicar a mesma mudança em 6 plugins × 4 arquivos à mão é **retrabalho**. Virou
`aplica_desc.py`: recebe plugin + arquivo de descrição, aplica nos três arquivos,
faz bump de patch, atualiza o README e **recusa** texto acima do cap. Foi esse
poka-yoke que barrou a primeira tentativa do `wsl-windows-onboarding`, com 511
chars — o erro morreu antes de virar commit.

### Act — padronização

**Padronizado em `scripts/validate-versions.py`:** o cap deixou de ser warning e
virou **erro**. Verificado por injeção — 400 chars a mais num plugin e o gate
reprovou; teste revertido em seguida.

Agora que a dívida está zerada, o custo de manter o padrão é encurtar no ato de
cada retrofit, que é barato. Deixar acumular custou este mutirão.

**Oportunidade registrada (fora do escopo desta rodada):** o `retrofit-skill`
poderia lembrar de rodar o validador antes do commit — nesta sessão o erro do
`cicd` só apareceu porque um retrofit anterior alterou 2 dos 3 arquivos.
