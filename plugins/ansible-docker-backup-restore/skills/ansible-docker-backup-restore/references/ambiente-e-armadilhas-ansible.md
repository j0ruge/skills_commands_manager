# Ambiente Ansible e armadilhas que causaram incidentes

Leia antes de escrever ou rodar o primeiro playbook da sessão.

## 1. Instalação — a armadilha do `uv`

```bash
uv tool install "ansible==11.*" --with-executables-from ansible-core --force
```

**Sem `--with-executables-from ansible-core`, o `uv` linka apenas
`ansible-community` e o `ansible-playbook` nunca aparece no PATH.** O sintoma
parece problema de PATH, e `uv tool update-shell` não resolve — o executável
simplesmente não foi linkado.

Escolha a versão pela versão do Python no nó **gerenciado**, não no seu:

| Python no alvo | Use |
|---|---|
| 3.8 | `ansible==11.*` (core 2.18) — core 2.19+ largou 3.8 |
| 3.9+ | a mais recente |

## 2. Validação obrigatória

```bash
ansible --version                            # confirme o core na série esperada
ansible <servidor>,<backup_host> -m ping     # ambos precisam responder pong
```

O `backup_host` responder importa tanto quanto o alvo: metade do procedimento lê
ou escreve lá.

## 3. O SDK Python do Docker provavelmente não está instalado

```bash
ssh <user>@<servidor> 'sudo python3 -c "import docker; print(docker.__version__)"'
```

Se falhar com `ModuleNotFoundError`:

| Pode usar | Não pode usar |
|---|---|
| `community.docker.docker_compose_v2` (opera pela CLI) | `docker_container`, `docker_image` |
| `ansible.builtin.command` com `docker` | `docker_volume`, `docker_volume_info`, `docker_network` |

Prefira **não instalar** o SDK: `docker_compose_v2` faz o trabalho pesado sem
ele, e meia dúzia de comandos `docker` cobre o resto.

> Sinal revelador: se existem playbooks no repositório usando os módulos
> proibidos e o SDK não está instalado, **esses playbooks nunca rodaram**. O que
> está no ar foi subido à mão. Trate-os como documentação de intenção, não como
> descrição do que existe.

Note que a disponibilidade pode ser **parcial** — alguns módulos da coleção
funcionam sem o SDK e outros não. Teste o módulo específico antes de confiar
numa regra geral sobre "a coleção não funciona aqui".

## 4. `roles_path`

Se houver playbook de teste em subdiretório (`tests/`), o Ansible resolve roles
relativo a ele e não encontra nada. Acrescente ao `ansible.cfg`:

```ini
roles_path = roles
```

## 5. Arquitetura: uma role, playbooks finos

Uma role parametrizada e um playbook de ~15 linhas por serviço. O contrato de
variáveis está em `assets/restore-defaults.yml`.

```
roles/restore/
├── defaults/main.yml         # contrato de variáveis
├── tasks/main.yml            # preflight → network → volumes → compose → dbdump → verify
├── tasks/volume.yml          # UM volume, com a guarda
├── tasks/dump.yml            # UM dump SQL, com a guarda
├── tasks/assert_mountpoint.yml
└── files/<servico>/          # composes reconstruídos, versionados
```

## 6. Armadilhas do Ansible que causaram incidentes reais

| Armadilha | Sintoma | Solução |
|---|---|---|
| **`--tags` em `include_role`** | Roda **zero** tasks internas, **sem erro nenhum** — mostra "included:" e termina com `ok=1`. Derrubou um banco de produção que já tinha sido removido e que nada recriou | Não use tags com `include_role` dinâmico. Audite playbooks existentes que dependam disso |
| **`--start-at-task` com `include_role`** | Não funciona, mesma causa (include dinâmico) | Playbook por serviço, ou re-rodar o playbook idempotente inteiro |
| **`blockinfile` com `block: \|`** | O literal YAML zera a indentação da primeira linha → chaves caem na raiz do documento → compose silenciosamente inválido | String com `\n` explícito, e validar com `docker compose config` |
| **Defaults de role não atravessam plays** | Uma task de `pre_tasks` ou de outra play não enxerga os defaults | Redeclare em `vars:` da play com o mesmo valor, ou `include_vars` do `defaults/main.yml` |
| **`default('x')` não pega string vazia** | O placeholder não aparece quando o valor é `""` | Forma de dois argumentos: `default('x', true)` |
| **`docker volume create` não diz "already exists"** | `changed_when` baseado na saída reporta mudança sempre | Padrão check-then-create com `docker volume inspect` |
| **`delegate_to` no mesmo arquivo, de hosts em paralelo** | Vários hosts com `delegate_to: <host_de_backup>` editando o **mesmo** `authorized_keys` correm: leitura-modificação-escrita simultânea, um sobrescreve a inserção do outro. Ambos reportam `changed`, só a última sobrevive — e o host perdido falha depois no rsync com `Permission denied`, longe da causa | `throttle: 1` na task delegada para serializar a escrita no arquivo compartilhado |
| **`PLAY RECAP` com `failed=1` encadeado** | `ansible-playbook … ; echo $?` devolve 0 e parece sucesso | O `$?` é do último comando da cadeia. Leia o RECAP, não o `$?` |

## 7. Sobre copiar regras de harness

Regras que descrevem o comportamento da ferramenta que executa o agente (e não
do domínio) envelhecem rápido — timeouts, execução em segundo plano, limites de
contexto. Antes de seguir uma delas, **confirme o comportamento atual** em vez
de assumir. O que vale para sempre é o de baixo: verificar por observação.
