---
description: Automatically generates release notes from the last release and creates a new GitHub Release via gh CLI.
metadata:
  version: 1.0.0
---

## User Input

```text
$ARGUMENTS
```

Interpret the input:

- **Semantic version** (e.g.: `3.0.0`, `2.1.0`): use as the new release version.
- **Empty**: ask the user which version to use before proceeding.

---

## Objective

Create a complete **GitHub Release** with detailed release notes in **English**, covering all changes since the last existing release tag in the repository.

---

## Constraints

- **DO NOT** modify project files. This command is read-only + release creation.
- **DO NOT** push code or commits.
- **DO NOT** fabricate information — everything must come from git data.

---

## Execution — Step by Step

### 1. Detect the project name

```bash
# Project name (package.json name or directory name)
PROJECT_NAME=$(node -p "try{require('./package.json').name}catch{''}" 2>/dev/null || basename "$(git rev-parse --show-toplevel)")
```

If `PROJECT_NAME` is empty, use `basename "$(git rev-parse --show-toplevel)"` as fallback.

### 2. Detect the last release

```bash
# Last release tag (sorted by semantic version)
git tag -l --sort=-version:refname | head -1
```

If there are no tags, inform the user and abort.

Store the result as `$LAST_TAG`.

### 3. Collect git data

Execute **in parallel**:

```bash
# Commits since the last release (excluding merges)
git log $LAST_TAG..HEAD --format="%h %s%n%b" --no-merges

# Changed file statistics
git diff --stat $LAST_TAG..HEAD

# Merged PRs (merge commits)
git log $LAST_TAG..HEAD --merges --oneline

# Contributors
git log $LAST_TAG..HEAD --format="%aN" --no-merges | sort | uniq

# Total files and lines
git diff --shortstat $LAST_TAG..HEAD
```

### 4. Analyze and categorize commits

Read the body and title of each commit to classify into categories:

| Prefix / Pattern           | Category             |
|----------------------------|----------------------|
| `feat:`                    | ✨ New Features      |
| `fix:`                     | 🐛 Bug Fixes        |
| `refactor:`                | 🏗️ Refactoring      |
| `docs:`                    | 📚 Documentation     |
| `test:`                    | 🧪 Tests             |
| `perf:`                    | ⚡ Performance       |
| `security` / `harden`     | 🔒 Security          |
| `chore:` / `ci:` / `build:` | 📦 Infrastructure  |
| No prefix                  | Analyze content and classify manually |

For each **feature** (`feat:`), group by source PR/branch when possible, creating a subsection with a descriptive title.

### 5. Identify added/removed dependencies

```bash
# Differences in package.json
git diff $LAST_TAG..HEAD -- package.json
```

Analyze the diff to list added, removed, and updated dependencies.

### 6. Compose the Release Note

Use **exactly** this format (adapt sections according to the collected data — omit empty sections):

````markdown
# 🚀 $PROJECT_NAME v$NEW_VERSION

**Release Date:** $TODAY_DATE
**Full Changelog:** $LAST_TAG...v$NEW_VERSION
**$N files changed** — $INSERTIONS insertions(+), $DELETIONS deletions(-)

---

## ✨ New Features

### Descriptive feature title (#PR — `branch-name`)
- Bullet point describing the change with relevant technical details
- Mention endpoints, modules, integrations created
- Use **bold** for important technical terms

---

## 🏗️ Refactoring

- **Short title** — description of the refactoring with context

---

## 🔒 Security

- **Short title** — description of the security improvement

---

## 🐛 Bug Fixes

- **Identifier (if any)** — description of the fix

---

## ⚡ Performance

- **Short title** — description of the improvement

---

## 📚 Documentation

- List added or updated documentation
- Mention specific files when relevant

---

## 🧪 Tests

- **N test files** added/modified
- List test types: integration, unit, e2e
- Mention covered domains/modules

---

## 📦 Dependencies

- **Added:** list new packages
- **Removed:** list removed packages
- **Updated:** list packages with version changes
- Runtime: information about Node.js, TypeScript, etc.

---

## Included Pull Requests

- #N — short PR title/description

---

**Contributors:** @usernames
````

### 7. Create the Release

Immediately after composing the release note, create the GitHub Release **without asking for confirmation**:

```bash
gh release create v$NEW_VERSION --target main --title "v$NEW_VERSION" --notes "$RELEASE_NOTES"
```

### 8. Display result

Display the full release note in the conversation along with the URL of the created release.

---

## Quality Rules

1. **Do not fabricate** — each item in the release note must have a corresponding commit or PR.
2. **English** — all text must be in English.
3. **Technical details** — mention endpoints, modules, files, and specific technologies.
4. **Group by feature** — commits related to the same PR/feature should be grouped, not listed individually.
5. **Omit empty sections** — if there are no bug fixes, do not include the 🐛 section.
6. **Consistent format** — follow the template above exactly, including emojis in headers.
