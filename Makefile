SHELL := /bin/bash
VENV := .venv
BIN := $(VENV)/bin
STAMP := $(VENV)/.installed

.PHONY: help venv test lint format clean

help:
	@printf "Usage:\n"
	@printf "  make venv      Create .venv and install the project with dev tooling into it\n"
	@printf "  make test      Run tests with pytest (ARGS=... passes extra arguments)\n"
	@printf "  make lint      Run ruff to check for lint issues\n"
	@printf "  make format    Run ruff to format code\n"
	@printf "  make clean     Delete .venv and caches\n"

venv: $(STAMP)

$(STAMP): pyproject.toml
	python3 -m venv $(VENV)
	$(BIN)/pip install --upgrade pip
	$(BIN)/pip install -e '.[dev]'
	touch $(STAMP)

test: venv
	$(BIN)/pytest $(ARGS)

lint: venv
	$(BIN)/ruff check .

format: venv
	$(BIN)/ruff format .

clean:
	rm -rf $(VENV) .pytest_cache .ruff_cache build dist *.egg-info src/*.egg-info
