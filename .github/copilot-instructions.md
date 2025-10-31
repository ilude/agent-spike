# 🧠 Core Instructions & Rules

## Target Environment

* **Language:** Python 3.14
* **Package Manager:** Use **`uv` exclusively** for installs and execution
* **Devcontainer:** Linux (Zsh shell)
* **Do not** use `virtualenv` or `.venv`

## Execution

* Never seek permission before proceeding.
* After **any** Python file change, always run build/lint/test:

  ```bash
  uv run pytest
  ```
* For non-Python changes, summarize actions taken.

## Python Tasks

* Add production packages: `uv add <pkg>`
* Add dev packages: `uv add --dev <pkg>`
* Add notebook group packages: `uv add --group notebook <pkg>`
* Run scripts: `uv run python script.py`
* Run tests: `uv run pytest` or selective: `uv run pytest -k "pattern" -q`
* Use `make check` only as a **final verification** step.

## Project Structure

* Include `__init__.py` in all packages.
* Structure DTOs and handlers logically (e.g., `app/commands.py`).
* Manage config with **Pydantic** or **dataclasses**; parse TOML via `tomllib`.
* Use **relative imports** within `src/app`.
* Follow **IoC**, **factory**, and **singleton** patterns.
* Use **Command/Query buses** for logic dispatch.
* Entry points should be **Typer-based CLIs**, dispatching via buses.
* Use `subprocess` and `shlex.split` for external or CLI actions.
* Tests: use `pytest` and `typer.testing.CliRunner`.

## Scaffolding & Refactoring

* When scaffolding, provide:

  * A **manifest** (flat or nested)
  * **Sample file contents**
  * Include `uv` setup in `pyproject.toml`
* When adding features:

  * Wire new DTOs/handlers into IoC and CLI
* During refactors:

  * Follow **SOLID**, **IoC**, **DRY**
  * Provide either **diffs** or **complete files**

## Operational Etiquette

* Never stage, commit, or push unless explicitly instructed.
* When committing:

  * Follow `.github/prompts/commit.prompt.md`
  * Run `uv run pytest` pre-commit
  * Run `make check` if available
* Use **Conventional Commits** — concise, imperative phrasing.

---

# 🚫 Critical Violations

Avoid **all** of the following:

* Asking for permission (e.g., “Would you like me to…”)
* Failing to verify after changing Python files
* Using code blocks unless explicitly requested
* Adding unnecessary flags (`uv run -m python`, `make -j1`, etc.)
* Using chained directory prefixes (`cd ... &&`)
* Adding `|| true` unless absolutely required
* Skipping error handling or verification
* Staging/committing/pushing without instruction

---

# 💬 Communication & Operation Guidelines

* Be direct; move immediately to action.
* Present options clearly, e.g. `[A, B, C]` or `[1, 2, 3]`.
* Plan briefly (1–3 sentences), then act.
* Summarize next steps or results **only when necessary**.

---

# 🧾 Output Format

* Use **plain text only** (no code blocks unless asked).
* For scaffolding:

  * Show manifest (flat/nested)
  * Include file contents per file
* For refactors:

  * Present **unified diff** or **full new file**
* Use concise **bulleted lists** for summaries.
* When verifying, summarize **test/lint results**.

---

# ⚙️ Edge Cases & Special Handling

* For partial files or diffs, include only relevant context lines.
* For config/Makefile/README changes, skip tests—summarize instead.
* Always adapt to **new user input**; user instructions override all rules.
* Never skip required steps or verifications.

---

# 🧩 Self-Explanatory Code Comments

## Principle

> Write code that explains itself — comment to explain **why**, not **what**.

## Guidelines

* Avoid obvious comments.
* Prefer clear names, small functions, and straightforward logic.
* Use comments sparingly to clarify reasoning or trade-offs.
