# Apontar esta skill para a sua instância

Índice: [`../SKILL.md`](../SKILL.md).

> 🔴 **Nenhum valor real mora aqui, de propósito.** Este repositório é público. Hostnames internos,
> ids de workflow, ids de projeto/usuário, endereços de conta de serviço e chaves de API são dados
> de infraestrutura: eles pertencem ao `.claude/rules/` do repositório privado que opera aquela
> instância, e os segredos ao `.env.local` gitignored. O que a skill precisa saber é o **contrato**,
> não os valores.

## O contrato: o que a skill espera encontrar

Ao operar uma instância, procure primeiro por uma regra do repositório (`.claude/rules/*n8n*.md` ou
equivalente) que preencha esta tabela. Se ela não existir, **crie-a** — descobrir isso de novo custa
horas, e cada linha abaixo custou pelo menos uma tentativa falha em algum lugar.

| Variável | O que é | Onde costuma viver |
|---|---|---|
| `N8N_SSH` | destino SSH do host do n8n | `.env.local` |
| `N8N_DB_EXEC` | comando que abre o `psql` do banco do n8n no host (com `-i`) | `.env.local` |
| `N8N_API_KEY` | chave da API pública, criada em Settings → n8n API | `.env.local` / ambiente do shell |
| `N8N_PROJECT_ID` | projeto onde os workflows vivem | `.env.local` |
| `N8N_USER_ID` | dono do projeto — **necessário quando o projeto é pessoal** | `.env.local` |
| id de cada workflow vigiado | chave de toda consulta a `execution_entity` | regra do repositório |
| path de cada webhook, por ambiente | o que o cliente chama; produção e treinamento diferem | regra do repositório |
| id da data table de dedup | só se houver vigia com dedup | `.env.local` |

## O que registrar sobre a instância, e por quê

Estas são as perguntas cuja resposta muda o procedimento. Registre-as na regra do repositório
privado, **com a data da medição** ao lado — instância muda, e uma afirmação sem data envelhece sem
avisar.

- **A instância roda em modo regular ou `queue`/`multi-main`?** Decide se `--activeState=fromJson`
  funciona ou faz o import falhar inteiro, e se workflow importado nasce inativo.
- **O projeto alvo é pessoal ou de equipe?** Decide entre `--userId` e `--projectId` no import.
- **`EXECUTIONS_DATA_SAVE_ON_SUCCESS` é `none`?** Se for, quais workflows têm override
  `saveDataSuccessExecution: "all"` — sem isso não há o que diagnosticar nem o que vigiar.
- **Quais módulos o servidor carrega que o CLI não carrega?** É o que inviabiliza `n8n execute` como
  forma de ensaio.
- **Quais workflows são espelho de leitura** (mantidos na UI por gente) e portanto nunca devem ser
  importados por cima.
- **Onde ficam os workflows na hierarquia de pastas**, e se algum nome tem erro de digitação — busca
  por um nome "óbvio" que não bate custa uma busca inteira em vão. Liste pela pasta, nunca por ids
  decorados.
- **Qual a origem que o CORS libera** em cada ambiente, se o cliente é um navegador.

## Higiene ao trazer esse conhecimento para cá

Ao contribuir uma lição desta skill a partir de uma instância real, **generalize antes**: descreva o
mecanismo e o sintoma, não o host. "O projeto pessoal quebra `--projectId`" é a lição; o id do
projeto não acrescenta nada a quem lê e é infraestrutura de terceiro.
