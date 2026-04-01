# Template: .editorconfig para C#/.NET Desktop

Este template e usado no Passo 6 do workflow. Adapte severity levels conforme a maturidade do projeto.

---

## Template

```ini
# EditorConfig — https://editorconfig.org
root = true

# =============================================================================
# Defaults para todos os arquivos
# =============================================================================
[*]
indent_style = space
indent_size = 4
end_of_line = crlf
charset = utf-8-bom
trim_trailing_whitespace = true
insert_final_newline = true

# =============================================================================
# XML / MSBuild (csproj, props, targets, resx)
# =============================================================================
[*.{csproj,props,targets,resx,xml,config}]
indent_size = 2

# =============================================================================
# JSON
# =============================================================================
[*.json]
indent_size = 2

# =============================================================================
# YAML
# =============================================================================
[*.{yml,yaml}]
indent_size = 2

# =============================================================================
# Markdown
# =============================================================================
[*.md]
trim_trailing_whitespace = false

# =============================================================================
# C# — Estilo de Codigo
# =============================================================================
[*.cs]

# --- Organizacao de usings ---
dotnet_sort_system_directives_first = true
dotnet_separate_import_directive_groups = false
csharp_using_directive_placement = outside_namespace:warning

# --- Namespace ---
csharp_style_namespace_declarations = file_scoped:suggestion

# --- var preferences ---
csharp_style_var_for_built_in_types = true:suggestion
csharp_style_var_when_type_is_apparent = true:suggestion
csharp_style_var_elsewhere = true:silent

# --- Expression-bodied members ---
csharp_style_expression_bodied_methods = when_on_single_line:suggestion
csharp_style_expression_bodied_constructors = false:suggestion
csharp_style_expression_bodied_properties = true:suggestion
csharp_style_expression_bodied_accessors = true:suggestion

# --- Pattern matching ---
csharp_style_pattern_matching_over_is_with_cast_check = true:suggestion
csharp_style_pattern_matching_over_as_with_null_check = true:suggestion
csharp_style_prefer_switch_expression = true:suggestion
csharp_style_prefer_pattern_matching = true:suggestion

# --- Null checking ---
csharp_style_throw_expression = true:suggestion
csharp_style_conditional_delegate_call = true:suggestion
dotnet_style_coalesce_expression = true:suggestion
dotnet_style_null_propagation = true:suggestion

# --- Braces ---
csharp_prefer_braces = true:warning

# --- Outros ---
csharp_style_prefer_local_over_anonymous_function = true:suggestion
csharp_style_prefer_index_operator = true:suggestion
csharp_style_prefer_range_operator = true:suggestion
csharp_style_deconstructed_variable_declaration = true:suggestion
csharp_prefer_simple_using_statement = true:suggestion
csharp_style_prefer_utf8_string_literals = true:suggestion

# =============================================================================
# C# — Formatting
# =============================================================================
[*.cs]

# --- Indentation ---
csharp_indent_case_contents = true
csharp_indent_switch_labels = true
csharp_indent_block_contents = true

# --- New lines ---
csharp_new_line_before_open_brace = all
csharp_new_line_before_catch = true
csharp_new_line_before_else = true
csharp_new_line_before_finally = true
csharp_new_line_before_members_in_object_initializers = true

# --- Spacing ---
csharp_space_after_cast = false
csharp_space_after_keywords_in_control_flow_statements = true
csharp_space_between_method_call_parameter_list_parentheses = false
csharp_space_between_method_declaration_parameter_list_parentheses = false

# =============================================================================
# C# — Naming Conventions
# =============================================================================
[*.cs]

# --- Symbols ---
dotnet_naming_symbols.public_members.applicable_kinds = property, method, field, event, delegate
dotnet_naming_symbols.public_members.applicable_accessibilities = public, internal, protected, protected_internal

dotnet_naming_symbols.private_fields.applicable_kinds = field
dotnet_naming_symbols.private_fields.applicable_accessibilities = private, private_protected

dotnet_naming_symbols.interfaces.applicable_kinds = interface

dotnet_naming_symbols.types.applicable_kinds = class, struct, interface, enum, delegate
dotnet_naming_symbols.types.applicable_accessibilities = *

dotnet_naming_symbols.const_fields.applicable_kinds = field
dotnet_naming_symbols.const_fields.required_modifiers = const

# --- Styles ---
dotnet_naming_style.pascal_case.capitalization = pascal_case

dotnet_naming_style.camel_case_underscore_prefix.capitalization = camel_case
dotnet_naming_style.camel_case_underscore_prefix.required_prefix = _

dotnet_naming_style.interface_prefix.capitalization = pascal_case
dotnet_naming_style.interface_prefix.required_prefix = I

# --- Rules ---
dotnet_naming_rule.interfaces_should_begin_with_i.symbols = interfaces
dotnet_naming_rule.interfaces_should_begin_with_i.style = interface_prefix
dotnet_naming_rule.interfaces_should_begin_with_i.severity = warning

dotnet_naming_rule.types_should_be_pascal_case.symbols = types
dotnet_naming_rule.types_should_be_pascal_case.style = pascal_case
dotnet_naming_rule.types_should_be_pascal_case.severity = warning

dotnet_naming_rule.public_members_should_be_pascal_case.symbols = public_members
dotnet_naming_rule.public_members_should_be_pascal_case.style = pascal_case
dotnet_naming_rule.public_members_should_be_pascal_case.severity = warning

dotnet_naming_rule.private_fields_should_be_camel_case.symbols = private_fields
dotnet_naming_rule.private_fields_should_be_camel_case.style = camel_case_underscore_prefix
dotnet_naming_rule.private_fields_should_be_camel_case.severity = warning

dotnet_naming_rule.const_fields_should_be_pascal_case.symbols = const_fields
dotnet_naming_rule.const_fields_should_be_pascal_case.style = pascal_case
dotnet_naming_rule.const_fields_should_be_pascal_case.severity = warning

# =============================================================================
# C# — Analyzer Rules
# =============================================================================
[*.cs]

# Code quality
dotnet_diagnostic.CA1822.severity = suggestion   # Mark members as static when possible
dotnet_diagnostic.CA1062.severity = warning       # Validate arguments of public methods
dotnet_diagnostic.CA1031.severity = suggestion    # Do not catch general exception types
dotnet_diagnostic.CA1304.severity = suggestion    # Specify CultureInfo
dotnet_diagnostic.CA1305.severity = suggestion    # Specify IFormatProvider

# Not relevant for desktop apps
dotnet_diagnostic.CA2007.severity = none          # Consider calling ConfigureAwait (ASP.NET only)

# Nullable
dotnet_diagnostic.CS8600.severity = warning       # Converting null literal
dotnet_diagnostic.CS8601.severity = warning       # Possible null reference assignment
dotnet_diagnostic.CS8602.severity = warning       # Dereference of a possibly null reference
dotnet_diagnostic.CS8603.severity = warning       # Possible null reference return
dotnet_diagnostic.CS8604.severity = warning       # Possible null reference argument

# Style (IDE analyzers)
dotnet_diagnostic.IDE0003.severity = suggestion   # Remove unnecessary this/Me qualification
dotnet_diagnostic.IDE0044.severity = suggestion   # Add readonly modifier
dotnet_diagnostic.IDE0055.severity = warning      # Fix formatting
dotnet_diagnostic.IDE0060.severity = suggestion   # Remove unused parameter
dotnet_diagnostic.IDE0090.severity = suggestion   # Use 'new(...)'
```

---

## Notas de Adaptacao

### Severity levels por maturidade do projeto

| Maturidade | Naming | Formatting | Analyzers |
|-----------|--------|------------|-----------|
| Projeto legado (migrando) | `suggestion` | `suggestion` | `suggestion` |
| Projeto ativo (padrao) | `warning` | `warning` | `suggestion` |
| Projeto maduro (CI enforced) | `error` | `error` | `warning` |

### charset utf-8-bom

O `utf-8-bom` e necessario para projetos em portugues ou com caracteres especiais.
Se o projeto usa apenas ASCII, pode ser simplificado para `utf-8`.

### Regras que podem conflitar

- Se o projeto usa `this.` por convencao, desabilite IDE0003
- Se o projeto tem muitos parametros legados nao utilizados, comece com IDE0060 em `silent`
- Se nullable ainda nao esta habilitado, coloque CS860x em `none` ate ativar
