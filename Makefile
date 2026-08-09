# OptMem Hermes Plugin - Makefile
# Common development tasks

.PHONY: test lint fmt install dev-install clean build release check

# Run tests (Linux/macOS/Windows)
test:
	python -m pytest tests/ -q

# Run tests with coverage
test-cov:
	python -m pytest tests/ --cov=optmem --cov-report=term-missing

# Lint with ruff
lint:
	ruff check optmem/ tests/

# Format with ruff
fmt:
	ruff check --fix optmem/ tests/
	ruff format optmem/ tests/

# Install in editable mode with dev deps
dev-install:
	pip install -e .[dev]

# Install in editable mode (production deps only)
install:
	pip install -e .

# Build distribution packages
build:
	python -m build

# Clean build artifacts
clean:
	rm -rf build/ dist/ *.egg-info/ .pytest_cache/ .ruff_cache/ optmem/__pycache__/ tests/__pycache__/

# Full check before commit
check: lint test

# Run Windows-specific test (locking)
test-windows:
	python -m pytest tests/ -q -k "lock or windows"

# Verify byte-compat with memo CLI (requires memo in PATH)
test-byte-compat:
	@echo "Run the retro-compat harness manually: scripts/sync_upstream.sh"
	@echo "Then: bash /tmp/optmem_retro_test.sh"

# Show help
help:
	@echo "Available targets:"
	@echo "  test           - Run tests"
	@echo "  test-cov       - Run tests with coverage"
	@echo "  lint           - Lint with ruff"
	@echo "  fmt            - Auto-fix lint issues"
	@echo "  dev-install    - Install in editable mode with dev deps"
	@echo "  install        - Install in editable mode (prod only)"
	@echo "  build          - Build dist packages"
	@echo "  clean          - Clean build artifacts"
	@echo "  check          - Run lint + test (pre-commit)"
	@echo "  test-windows   - Run Windows-specific tests"
	@echo "  help           - Show this help"