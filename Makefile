# Process-Tools — workshop-wide make targets.
#
# Usage:
#     make test-all       # run every tool's test suite
#     make install-hooks  # install the truncation-hazard pre-commit hook
#     make help           # show available targets

PYTHON ?= python3

.PHONY: help test-all install-hooks

help:
	@echo "Process-Tools workshop targets:"
	@echo "  make test-all       Run every tool's tests; print a single summary."
	@echo "  make install-hooks  Install the git pre-commit hook."

test-all:
	@bash scripts/test_all.sh

install-hooks:
	@bash scripts/install-hooks.sh
