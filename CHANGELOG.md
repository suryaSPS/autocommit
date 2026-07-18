# Changelog

## v0.3.0 (2026-07-18)

### Features

- initial autocommit CLI — AI-powered git commit message generator
- **secrets:** add regex-based secret scanner
- **llm:** add ollama provider and shared completion dispatch
- **review:** add staged-diff code review module
- **pr:** add PR description writer and branch helpers
- **cli:** wire scan, review, and pr commands with secret commit gate
- **git:** add history, tag, and staging helpers
- **split:** cluster staged changes into atomic commits
- **changelog:** generate changelogs from conventional commits
- **explain:** plain-language explanation of the staged diff
- **cli:** wire split, explain, and changelog commands

### Refactoring

- **llm:** extract pluggable provider registry

### Documentation

- add README
- add repository guidelines
- rewrite README for secret scanning, review, pr, and ollama
- document split, explain, changelog, and custom providers

### Tests

- add pytest suite for scanner, review, pr, config, git, and CLI

### CI

- add GitHub Actions workflow for lint and tests

### Chores

- add .gitignore and LICENSE, untrack compiled artifacts
- bump version to 0.2.0 and fix project URLs
- add mypy and pre-commit tooling
- rename package to commitpilot, add PyPI publish workflow
