#!/bin/bash
# =============================================================================
# audit-environment.sh — Auditoria do ambiente .NET para Claude Code
# Uso: bash scripts/audit-environment.sh [caminho-do-projeto]
# Requer: Git Bash no Windows, .NET SDK instalado
# Este script e READ-ONLY — nao modifica nenhum arquivo.
# =============================================================================

PROJECT_DIR="${1:-.}"
cd "$PROJECT_DIR" || { echo "ERRO: Diretorio '$PROJECT_DIR' nao encontrado"; exit 1; }

echo "=== .NET Desktop Setup — Auditoria do Ambiente ==="
echo "Data: $(date '+%Y-%m-%d %H:%M')"
echo "Diretorio: $(pwd)"
echo ""

# --- 1. SDKs .NET ---
echo "--- SDKs .NET Instalados ---"
if command -v dotnet &>/dev/null; then
    dotnet --list-sdks 2>/dev/null
    echo ""
    echo "SDK ativo: $(dotnet --version 2>/dev/null)"
else
    echo "ERRO: dotnet CLI nao encontrado no PATH"
fi
echo ""

# --- 2. Arquivos de Configuracao ---
echo "--- Arquivos de Configuracao ---"
configs=("CLAUDE.md" ".editorconfig" "Directory.Build.props" "Directory.Build.targets" "global.json" "nuget.config" ".claude/rules")
for cfg in "${configs[@]}"; do
    if [ -e "$cfg" ]; then
        echo "[EXISTE]  $cfg"
    else
        echo "[FALTA]   $cfg"
    fi
done

# Verificar CLAUDE.md global
if [ -f "$HOME/.claude/CLAUDE.md" ]; then
    echo "[EXISTE]  ~/.claude/CLAUDE.md (global)"
else
    echo "[FALTA]   ~/.claude/CLAUDE.md (global)"
fi

# Verificar regras escopadas
if [ -d ".claude/rules" ]; then
    echo ""
    echo "Regras escopadas encontradas:"
    ls -1 .claude/rules/*.md 2>/dev/null || echo "  (nenhuma regra .md encontrada)"
fi
echo ""

# --- 3. Estrutura da Solution ---
echo "--- Estrutura da Solution ---"
SLN_FILE=$(ls *.sln 2>/dev/null | head -1)
if [ -n "$SLN_FILE" ]; then
    echo "Solution: $SLN_FILE"
    echo ""
    echo "Projetos e Frameworks:"
    # Encontrar todos os .csproj referenciados
    grep -oP 'Project\("[^"]*"\) = "[^"]*", "([^"]*\.csproj)"' "$SLN_FILE" 2>/dev/null | \
        grep -oP '"[^"]*\.csproj"' | tr -d '"' | while read -r csproj; do
        if [ -f "$csproj" ]; then
            fw=$(grep -oP '<TargetFramework[s]?>\K[^<]+' "$csproj" 2>/dev/null | head -1)
            output_type=$(grep -oP '<OutputType>\K[^<]+' "$csproj" 2>/dev/null | head -1)
            printf "  %-45s %-25s %s\n" "$csproj" "${fw:-N/A}" "${output_type:-Library}"
        fi
    done
    # Fallback: buscar todos os csproj se o parse do sln falhar
    if [ $? -ne 0 ]; then
        find . -name "*.csproj" -not -path "*/bin/*" -not -path "*/obj/*" | while read -r csproj; do
            fw=$(grep -oP '<TargetFramework[s]?>\K[^<]+' "$csproj" 2>/dev/null | head -1)
            printf "  %-45s %s\n" "$csproj" "${fw:-N/A}"
        done
    fi
else
    echo "AVISO: Nenhum arquivo .sln encontrado"
    echo "Buscando .csproj diretamente..."
    find . -name "*.csproj" -not -path "*/bin/*" -not -path "*/obj/*" | while read -r csproj; do
        fw=$(grep -oP '<TargetFramework[s]?>\K[^<]+' "$csproj" 2>/dev/null | head -1)
        printf "  %-45s %s\n" "$csproj" "${fw:-N/A}"
    done
fi
echo ""

# --- 4. Indicadores de Acoplamento UI ---
echo "--- Indicadores de Acoplamento UI ---"

# MessageBox fora de Forms
echo ""
echo "MessageBox.Show() em arquivos que NAO sao Form*.cs:"
grep -rn "MessageBox\.Show" --include="*.cs" . 2>/dev/null | \
    grep -v "/bin/" | grep -v "/obj/" | grep -v "Form.*\.cs:" | grep -v "Designer\.cs:" || \
    echo "  (nenhum encontrado — bom!)"

# System.Windows.Forms em classes nao-UI
echo ""
echo "System.Windows.Forms em classes fora de UI (Form*, Control*, Program.cs):"
grep -rn "using System\.Windows\.Forms" --include="*.cs" . 2>/dev/null | \
    grep -v "/bin/" | grep -v "/obj/" | \
    grep -v "Form.*\.cs:" | grep -v "Control.*\.cs:" | \
    grep -v "Program\.cs:" | grep -v "Designer\.cs:" | \
    grep -v "UserControl.*\.cs:" || \
    echo "  (nenhum encontrado — bom!)"

# Estado estatico mutavel
echo ""
echo "Campos 'public static' mutaveis (potencial Global.cs pattern):"
grep -rn "public static [^c]" --include="*.cs" . 2>/dev/null | \
    grep -v "/bin/" | grep -v "/obj/" | \
    grep -v "const " | grep -v "readonly " | \
    grep -v "class " | grep -v "void " | grep -v "enum " || \
    echo "  (nenhum encontrado — bom!)"
echo ""

# --- 5. Cobertura de Testes ---
echo "--- Cobertura de Testes ---"

test_projects=$(find . -name "*Test*.csproj" -not -path "*/bin/*" -not -path "*/obj/*" 2>/dev/null)
if [ -n "$test_projects" ]; then
    echo "Projetos de teste encontrados:"
    echo "$test_projects" | while read -r tp; do echo "  $tp"; done
    echo ""

    fact_count=$(grep -r "\[Fact\]" --include="*.cs" . 2>/dev/null | grep -v "/bin/" | grep -v "/obj/" | wc -l)
    theory_count=$(grep -r "\[Theory\]" --include="*.cs" . 2>/dev/null | grep -v "/bin/" | grep -v "/obj/" | wc -l)
    test_files=$(find . -name "*Test*.cs" -not -path "*/bin/*" -not -path "*/obj/*" -not -name "*.Designer.cs" 2>/dev/null | wc -l)

    echo "Arquivos de teste: $test_files"
    echo "Total [Fact]: $fact_count"
    echo "Total [Theory]: $theory_count"
    echo "Total estimado de testes: $((fact_count + theory_count))"
else
    echo "AVISO: Nenhum projeto de teste encontrado"
fi
echo ""

# --- Resumo ---
echo "=== Resumo ==="
echo "Execute os passos do workflow dotnet-desktop-setup para resolver as lacunas encontradas."
echo "============================================"
