# LSDMU Bibliography Agent Instructions

This repository contains the machine-readable bibliography and citation registry for Bache Archive LSDMU-related sources.

## Codex Startup From This Repo

- These instructions must be sufficient when Codex CLI is started from this repository instead of `/Users/howardrhee/projects/bache-archive`.
- Also read `../AGENTS.md` and `../CODEX_WORKSPACE.md` when they are available; they contain cross-repo policy and current workspace priorities.
- Use `AGENTS.md` for durable Codex instructions. Do not create `CODEX.md` unless a separate non-Codex tool explicitly requires it.
- For GitHub CLI commands, set `GH_CONFIG_DIR="$HOME/.config/gh-bache"` so archive auth does not overwrite or use personal GitHub accounts.
- Start broad archive work from `/Users/howardrhee/projects/bache-archive`; keep bibliography/citation registry work in this repo.
- Corpus/transcript/fixity work belongs in `../chris-bache-archive`.
- Web/frontend/domain work belongs in `../bache-archive-web`.
- RAG/API/chat-answer work belongs in `../bache-rag-api`.

## GitHub Issue Ownership

When taking on a GitHub issue, always mark it as in progress before starting local work so other agents can see it is claimed.

1. Read recent issue comments first. If another agent already owns the issue and there is no clear handoff or completion note, do not duplicate the work.
2. Before any code change, branch creation, or dependency install, post a claim comment on the issue using this exact format:

```text
🤖 In progress — branch agent/issue-{N}-{short-slug}
```

3. After posting the claim comment, try to add the GitHub label:

```bash
GH_CONFIG_DIR="$HOME/.config/gh-bache" gh issue edit {N} --add-label "in-progress"
```

If the label does not exist or permissions do not allow it, do not block on that step. The claim comment is still required.

4. Then create the branch and start implementation.
5. When the work is done, blocked, or handed off, comment again with the outcome. If the issue was labeled `in-progress`, remove that label when appropriate.

## Identity Boundary

- Remote must be `git@github-bache:bache-archive/lsdmu-bibliography.git`.
- Local Git identity must be `Bache Archive <bache-archive@tuta.com>`.
- Do not use personal GitHub CLI auth, default `github.com` SSH remotes, or HTTPS GitHub remotes for archive work.
- Never commit `.env*`, API keys, tokens, raw email exports, downloaded media, or private material.

## Verification

- Run any repo-local CSL, JSON, DOI, Wikidata, or schema validation scripts that apply to changed bibliography data.
- Before commits or pushes, confirm `git remote -v`, `git config --local user.name`, and `git config --local user.email` match the archive identity boundary.
