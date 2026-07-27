# Changelog — `skills/ansible-docker-backup-restore`

Lições incorporadas à skill, datadas. Cada entrada diz **o que** mudou e **por
quê** — o sintoma que ela teria evitado.

## 2026-07-27 — versão inicial (1.0.0)

Origem: três sessões de recuperação de um servidor Linux Dockerizado. A primeira
metade (restore) já existia como documento interno de 10 fases; a segunda
(backup) não existia em lugar nenhum e é o que motivou publicar.

### Por que backup e restore ficaram na mesma skill

Porque o incidente que fecha o ciclo nasceu na costura: o restore renomeou um
container para desfazer uma colisão de alias de rede, o inventário do backup não
acompanhou **no mesmo commit**, e o backup daquele servidor parou de completar —
por dias, sem alerta. Uma skill só de restore não teria onde guardar essa lição;
duas skills irmãs a deixariam cair no vão entre elas.

### As lições que entraram na espinha

Ficam no `SKILL.md` as que mudam comportamento no instante em que ninguém
abriria uma reference:

- **`ignore_errors` + `no_log` na mesma task** — padrão que o modelo *escreve*
  de novo, não só encontra. Um esconde o erro, o outro a mensagem.
- **Toda exclusão de backup apaga dado para sempre** — uma lista escrita uma vez
  remove aqueles caminhos de todo backup, todo dia, sem avisar. Num caso real
  isso apagou por anos o feed de auto-update de uma aplicação instalada em
  clientes, descoberto só quando o servidor foi perdido.
- **Renomear container é mudança de duas pontas** — inventário no mesmo commit.
- **Nenhum `VIRTUAL_HOST` antes de auditar o vhost** — é a única regra cujo raio
  de alcance é *todos* os domínios do host de uma vez, e cujo teste (`nginx -t`)
  passa até o momento exato em que já é tarde.
- **`PLAY RECAP failed=1` não é sucesso** mesmo com `; echo $?` devolvendo 0 —
  o modelo encadeia isso por reflexo.
- **"Não existe em backup" só vale dentro das origens enumeradas por escrito.**

### O que foi deliberadamente demovido

- O detalhe de `while read` alimentado por pipe rodar em subshell virou nota de
  rodapé, não item próprio: é bash comum, não conhecimento de domínio. Está lá
  porque explica por que o contador de avisos funciona.
- O default de 1 MB de corpo de requisição do proxy virou linha de tabela: é o
  único caso do conjunto em que o sintoma (413) aponta direto para a causa. Os
  demais só merecem documentação porque o sintoma aponta para o lugar errado.

### Nota sobre agnosticismo

Nenhum nome de servidor, domínio, container, volume ou endereço de rede de
ambiente específico entrou aqui — nem nos exemplos, nem nos assets. Onde o caso
real importava para o argumento, ele foi contado pelo mecanismo, com
placeholders. Isso não é só higiene de segredo: lição amarrada a um parque só
serve àquele parque, e o lugar dela seria o repositório daquele parque.
