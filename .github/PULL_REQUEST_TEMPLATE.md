name: Pull Request
description: Submit a pull request
title: "[PR]: "
labels: ["pr"]
body:
  - type: markdown
    attributes:
      value: |
        Thanks for the PR! Please ensure:
        - Tests pass (`make test` or `python -m pytest tests/ -q`)
        - Lint passes (`make lint` or `ruff check optmem/ tests/`)
        - Code follows the project style (type hints on public functions, stdlib only)
  - type: checkboxes
    id: checks
    attributes:
      label: Checklist
      options:
        - label: Tests added/updated for the change
          required: true
        - label: `make check` passes (lint + tests)
          required: true
        - label: CHANGELOG.md updated (if user-facing change)
          required: true
        - label: No breaking changes to on-disk format (LOG.txt/TREE/)
          required: true
        - label: Byte-compatible with upstream `memo` CLI maintained
          required: true
  - type: textarea
    id: description
    attributes:
      label: Description
      description: What does this PR do? Why is it needed?
    validations:
      required: true
  - type: textarea
    id: testing
    attributes:
      label: Testing Done
      description: How did you test this? (unit tests, manual, retro-compat harness)
    validations:
      required: true
  - type: dropdown
    id: type
    attributes:
      label: Type of Change
      options:
        - Bug fix
        - Feature
        - Refactor
        - Documentation
        - CI/CD
        - Tests
    validations:
      required: true