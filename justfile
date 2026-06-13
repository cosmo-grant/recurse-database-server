check:
  uv run ruff format
  uv run ruff check --fix
  ty check
  uv run pytest
