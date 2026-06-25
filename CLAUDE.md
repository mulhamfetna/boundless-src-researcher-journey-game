# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this directory is

This is a **content-only directory**, not a code project. It holds Arabic-language
educational PDFs about academic/scientific research methodology — there is no source
code, build system, package manifest, or git repository here.

Current contents (all `.pdf`):

- `أسس البحث العلمي واختيار الفجوة البحثية.pdf` — Foundations of scientific research and choosing the research gap
- `أنواع الأوراق البحثية العلمية.pdf` — Types of scientific research papers
- `اجزاء الورقة البحثية.pdf` — Parts of a research paper
- `المحور الثاني -تصنيف المجلات العلمية.pdf` — (Module 2) Classifying scientific journals

## Working here

- There are **no build/test/lint commands** — nothing is executable.
- This directory sits under the larger `/mnt/data/projects` multi-project workspace; see
  that workspace's root `CLAUDE.md`/`AGENTS.md` for cross-project conventions.
- Treat the PDFs as reference material. To read one, use the file-reading tools (PDFs can
  be read page-by-page). Filenames are in Arabic and contain spaces — quote paths in shell
  commands.
- If this directory later gains actual code (a manifest like `package.json`,
  `pyproject.toml`, etc.), update this file with the real build/test/run commands and
  architecture notes at that point.
