.PHONY: format format_check format_fix lint lint_fix

format:
	poetry run ruff format --check --diff

format_fix:
	poetry run ruff format
lint:
	poetry run ruff check

lint_fix:
	poetry run ruff check --fix