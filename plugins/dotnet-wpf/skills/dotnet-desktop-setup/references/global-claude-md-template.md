# Template: CLAUDE.md Global (~/.claude/CLAUDE.md)

Este template e usado no Passo 3 do workflow. Copie e adapte as secoes relevantes.
O CLAUDE.md global se aplica a TODOS os projetos C#/.NET do usuario.

---

## Template

```markdown
# Convencoes Globais C#/.NET

Estas regras se aplicam a todos os projetos C#/.NET nesta maquina.

## Linguagem C# Moderna

- Usar file-scoped namespaces (C# 10+): `namespace MyApp;` em vez de bloco `namespace MyApp { }`
- Usar primary constructors para DI (C# 12+): `public class MyService(ILogger logger)`
- Preferir pattern matching sobre type checks: `if (obj is string s)` em vez de `if (obj is string)`
- Usar collection expressions (C# 12+): `int[] nums = [1, 2, 3];`
- Preferir `var` quando o tipo e obvio; tipo explicito quando nao e
- Sempre usar chaves em if/else/for/while, mesmo para uma linha
- Records para DTOs e value objects: `public record OrderDto(int Id, string Name);`

## Naming Conventions

| Elemento | Estilo | Exemplo |
|----------|--------|---------|
| Public members | PascalCase | `public string ShipName` |
| Private fields | _camelCase | `private readonly ILogger _logger` |
| Local variables | camelCase | `var shipName = "..."` |
| Constants | PascalCase | `public const int MaxRetries = 3` |
| Interfaces | IPascalCase | `public interface IVdrParser` |
| Type parameters | TPascalCase | `Result<TValue>` |
| Async methods | PascalCase + Async | `public async Task<Ship> GetShipAsync()` |
| Test methods | Method_Scenario_Expected | `Validar_ArquivoVazio_RetornaErro` |

## .NET CLI Patterns

```bash
# Build rapido (apos primeiro restore)
dotnet build --no-restore -v q

# Testes com filtro
dotnet test --filter "FullyQualifiedName~MinhaClasse"

# Testes de uma categoria
dotnet test --filter "Category=UnitTest"

# Build em modo quiet para CI
dotnet build -v q -c Release --no-restore
```

## Convencoes de Teste (xUnit)

- Padrao Arrange/Act/Assert com comentarios de secao:
  ```csharp
  [Fact]
  public void Calcular_ValorPositivo_RetornaCorreto()
  {
      // Arrange
      var service = new CalculadoraService();

      // Act
      var resultado = service.Calcular(10, 5);

      // Assert
      Assert.Equal(15, resultado);
  }
  ```
- `[Fact]` para caso unico, `[Theory]` + `[InlineData]` para multiplos inputs
- `[Trait("Category", "...")]` para agrupar testes
- Um conceito logico por teste (multiplos Assert OK se testam a mesma coisa)
- Nomes de metodo em ingles OU portugues — siga a convencao do projeto

## Anti-padroes Universais

### NUNCA faca isto em classes que NAO sao Form/UI:
- `MessageBox.Show()` — retorne Result<T> ou lance excecao
- `OpenFileDialog` / `SaveFileDialog` — receba path como parametro
- `System.Windows.Forms` no using — classes de dominio/service nao devem ter esta referencia

### NUNCA faca isto em qualquer classe:
- `public static` mutavel como service locator (padrao Global.cs) — use DI
- `catch { }` vazio — no minimo faca log
- `Thread.Sleep()` em testes — use async/await ou fakes de tempo
- `new HttpClient()` dentro de metodos — use IHttpClientFactory ou injetar HttpClient
- Strings magicas para caminhos de arquivo — use Path.Combine()

## Dependency Injection

- Preferir constructor injection sobre property injection
- Registrar services no composition root (Program.cs)
- Uma interface por service (ISomethingService → SomethingService)
- Ciclo de vida: Singleton para stateless, Scoped para per-request, Transient para leve e stateless

## Error Handling

- Result<T> pattern para erros de negocio esperados (validacao, not found)
- Exceptions para erros inesperados (IO, rede, bug)
- Nunca use exceptions para controle de fluxo
- Valide na fronteira do sistema (input do usuario, API externa), confie em codigo interno

## Commit Messages

- Formato: `<tipo>(<escopo>): <descricao>`
- Tipos: feat, fix, refactor, test, docs, chore
- Idioma: siga a convencao do projeto (portugues ou ingles)
- Exemplo: `refactor(licenca): extrair LicenseValidationService de Licenca.cs`
```

---

## Notas de Adaptacao

- Se o usuario trabalha com .NET 6 ou anterior, remova as secoes sobre primary constructors e collection expressions
- Se o usuario nao usa xUnit, adapte a secao de testes para NUnit ou MSTest
- A secao de anti-padroes e propositalmente opinada — o usuario pode relaxar regras conforme necessidade
