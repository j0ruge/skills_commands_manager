#!/bin/bash
# Prova que o backup de hoje existe e está completo. SOMENTE LEITURA — não
# escreve, não apaga, não altera nada em nenhum dos dois hosts.
#
# Uso:
#   check-backup-freshness.sh <backup_host> <backup_root>/<servidor> [<servidor_ssh>]
#
# Exemplo:
#   check-backup-freshness.sh root@10.0.0.9 /opt/backups/app01 admin@app01
#
# O terceiro argumento é opcional: com ele, o script também compara a contagem
# de volumes do backup com a do servidor de origem.
#
# Existe porque um backup ficou dias sem completar sem que nada avisasse. O
# sinal mais barato — buracos na sequência de datas — teria pego no primeiro
# dia. Ver references/backup-pipeline-e-falha-silenciosa.md §1.

set -uo pipefail

BACKUP_HOST="${1:?uso: $0 <backup_host> <backup_path> [<servidor_ssh>]}"
BACKUP_PATH="${2:?uso: $0 <backup_host> <backup_path> [<servidor_ssh>]}"
SOURCE_HOST="${3:-}"

FAIL=0
note()  { printf '  %s\n' "$*"; }
bad()   { printf '  ✗ %s\n' "$*"; FAIL=1; }
good()  { printf '  ✓ %s\n' "$*"; }

echo "== Datas presentes em ${BACKUP_HOST}:${BACKUP_PATH}"
DATES=$(ssh "$BACKUP_HOST" "ls -1 '${BACKUP_PATH}' 2>/dev/null | grep -E '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' | sort")
if [ -z "$DATES" ]; then
  bad "nenhuma pasta de data encontrada — o backup nunca completou aqui"
  exit 1
fi
echo "$DATES" | sed 's/^/    /'

TODAY=$(date +%F)
LATEST=$(echo "$DATES" | tail -1)
[ "$LATEST" = "$TODAY" ] && good "backup de hoje (${TODAY}) presente" \
                         || bad "o mais recente é ${LATEST}, não hoje (${TODAY})"

# Buracos na sequência: o sinal mais barato de um backup que morreu calado.
echo "== Continuidade da sequência"
GAPS=$(echo "$DATES" | awk -v last="$LATEST" '
  function d2e(s,   a){split(s,a,"-"); return mktime(a[1]" "a[2]" "a[3]" 12 0 0")}
  NR>1 { gap = int((d2e($0) - d2e(prev)) / 86400); if (gap > 1) print prev " -> " $0 " (" gap-1 " dia(s) sem backup)" }
  { prev = $0 }')
[ -z "$GAPS" ] && good "sem buracos" || { echo "$GAPS" | sed 's/^/    /'; bad "há buracos na sequência acima"; }

echo "== Conteúdo de ${LATEST}"
for sub in databases volumes containers configs; do
  N=$(ssh "$BACKUP_HOST" "ls -1 '${BACKUP_PATH}/${LATEST}/${sub}' 2>/dev/null | wc -l")
  [ "${N:-0}" -gt 0 ] && good "${sub}: ${N} arquivo(s)" || bad "${sub}: VAZIO"
done

# Um dump que é só a mensagem de erro do comando tem poucos bytes.
echo "== Dumps suspeitos de tamanho (< 1 KB)"
SMALL=$(ssh "$BACKUP_HOST" "find '${BACKUP_PATH}/${LATEST}/databases' -type f -size -1k 2>/dev/null")
[ -z "$SMALL" ] && good "nenhum dump minúsculo" || { echo "$SMALL" | sed 's/^/    /'; bad "dump(s) pequenos demais — provável erro gravado no lugar do dado"; }

if [ -n "$SOURCE_HOST" ]; then
  echo "== Cobertura de volumes"
  SRC=$(ssh "$SOURCE_HOST" "sudo docker volume ls -q 2>/dev/null | wc -l")
  DST=$(ssh "$BACKUP_HOST" "ls -1 '${BACKUP_PATH}/${LATEST}/volumes' 2>/dev/null | wc -l")
  [ "${SRC:-0}" -eq "${DST:-0}" ] && good "volumes: ${DST}/${SRC}" \
                                  || bad "volumes: backup tem ${DST}, servidor tem ${SRC}"
fi

echo "== Espaço e aritmética da retenção"
ssh "$BACKUP_HOST" "df -h '${BACKUP_PATH}' | tail -1" | sed 's/^/    /'
LAST_SIZE=$(ssh "$BACKUP_HOST" "du -sk '${BACKUP_PATH}/${LATEST}' 2>/dev/null | cut -f1")
AVAIL=$(ssh "$BACKUP_HOST" "df -k '${BACKUP_PATH}' | tail -1 | awk '{print \$4}'")
if [ -n "${LAST_SIZE:-}" ] && [ -n "${AVAIL:-}" ] && [ "$LAST_SIZE" -gt 0 ]; then
  note "diário ≈ $((LAST_SIZE/1024/1024)) GB · livre ≈ $((AVAIL/1024/1024)) GB · cabem ≈ $((AVAIL/LAST_SIZE)) dia(s)"
  note "compare com a retenção configurada: se ela for maior que isso, é ficção."
fi

echo
[ "$FAIL" -eq 0 ] && echo "RESULTADO: backup íntegro." || echo "RESULTADO: PROBLEMAS ACIMA."
exit "$FAIL"
