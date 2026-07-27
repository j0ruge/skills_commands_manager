#!/bin/bash
# Tara todos os volumes Docker do host para um diretório de backup.
# Uso: backup-volumes.sh <backup_dir> <backup_date>
#
# Ponto de partida, não código para colar sem ler. Ver
# references/backup-pipeline-e-falha-silenciosa.md §2.3 e §5.

set -euo pipefail

BACKUP_DIR="$1"
BACKUP_DATE="$2"
VOLUMES_DIR="${BACKUP_DIR}/volumes"

mkdir -p "$VOLUMES_DIR"

WARNED=0

# POR QUE ESTA FUNÇÃO EXISTE
#
# O `set -e` acima mata o script quando o tar devolve 1. E o GNU tar devolve 1
# para "file changed as we read it", que é situação NORMAL ao tarar o datadir de
# um banco em execução.
#
# Como os volumes são tarados em ordem alfabética, um banco cedo no alfabeto
# abortava tudo o que vinha depois — os outros volumes E a sincronização final.
# Pior: só acontecia quando o banco escrevia exatamente durante aquela janela, o
# que fazia a falha parecer intermitente e sumir quando alguém ia investigar.
#
# Códigos de saída do GNU tar:
#   0   tudo certo
#   1   "some files differ" — no modo -c, um arquivo mudou enquanto era lido.
#       O tar É gravado; o que está inconsistente é aquele arquivo.
#   >=2 erro de verdade (disco cheio, permissão, caminho inexistente).
#
# Para volume de BANCO isto é seguro: a fonte autoritativa é o dump SQL feito
# antes deste script, não o tar do datadir. Para volume de APLICAÇÃO, um aviso
# merece investigação — por isso ele é contado e aparece no resumo final.
tar_volume() {
  local out="$1"
  shift
  local rc=0
  tar -cf "$out" "$@" || rc=$?

  if (( rc >= 2 )); then
    echo "  ✗ ERRO FATAL ao gerar ${out} (tar rc=${rc})" >&2
    return "$rc"
  fi

  if (( rc == 1 )); then
    echo "  ⚠ ${out}: arquivos mudaram durante a leitura (volume vivo). Tar gravado." >&2
    WARNED=$((WARNED + 1))
  fi

  return 0
}

# Process substitution, não pipe: num pipe o laço roda em subshell e o contador
# WARNED morre antes do resumo final.
while read -r vol; do
  echo "  → Tar: $vol"
  MOUNTPOINT=$(docker volume inspect "$vol" --format '{{.Mountpoint}}')

  # PADRÃO DE EXCLUSÃO — leia §5 antes de acrescentar qualquer linha aqui.
  #
  # Só conteúdo DERIVADO entra: cache de página, thumbnails regeneráveis, perfil
  # de navegador headless, log de aplicação. Se você não sabe dizer o comando
  # que reconstrói aquilo, não é derivado — é dado, e excluí-lo apaga o dado de
  # TODO backup, todo dia, em silêncio.
  #
  # Ancore o caminho (`./caminho/exato`) em vez de um nome solto, que casaria em
  # qualquer profundidade. E justifique por escrito, aqui, ao lado da linha.
  #
  # case "$vol" in
  #   <volume_com_cache_grande>)
  #     # <por que é descartável> / <como se regenera>
  #     tar_volume "${VOLUMES_DIR}/${vol}_${BACKUP_DATE}.tar" \
  #       --exclude='./<caminho/derivado>' \
  #       -C "$MOUNTPOINT" .
  #     ;;
  #   *)
        tar_volume "${VOLUMES_DIR}/${vol}_${BACKUP_DATE}.tar" -C "$MOUNTPOINT" .
  #     ;;
  # esac
done < <(docker volume ls --format '{{.Name}}')

echo "  ✅ $(ls "${VOLUMES_DIR}"/*.tar | wc -l) volumes tarados (${WARNED} com aviso de arquivo vivo)"
