# AGENTS.md

## Scope
These instructions apply to the full repository.

## Repo purpose
This repository contains the standalone ComfyUI custom node pack **Keyframe Consistency Pack (KCP)**.

## Guardrails
- Keep changes surgical and ticket-oriented.
- Avoid broad refactors and incidental formatting changes.
- Runtime dependencies are limited to Python stdlib and optional Pillow.
- Use `pathlib` for all paths.
- New tickets must follow `tickets/TEMPLATE.md` exactly; all sections are required (use `NONE` when not applicable).

## Verify workflow
Run:
1. `python tools/context.py`
2. `python tools/verify.py --receipt "<BATCH label>"`

## Pillow requirements
- Text-only asset workflows can run without Pillow.
- Pillow is required for node paths that write images/thumbs.
- Install dependencies with ComfyUI embedded python:
  - Portable Windows: `python_embeded\python.exe -m pip install -r requirements.txt`
  - Other installs: `python -m pip install -r requirements.txt`
- Install Pillow:
  - `python -m pip install Pillow`

## Local ComfyUI install (manual)
1. Copy this folder into `ComfyUI/custom_nodes/ComfyUI_Keyframe_Consistency_Pack`.
2. Restart ComfyUI.
3. Confirm KCP nodes appear in the node menu.

## Skills
A skill is a set of local instructions to follow that is stored in a `SKILL.md` file. Below is the list of skills that can be used. Each entry includes a name, description, and file path so you can open the source for full instructions when using a specific skill.
### Available skills
- skill-creator: Guide for creating effective skills. This skill should be used when users want to create a new skill (or update an existing skill) that extends Codex's capabilities with specialized knowledge, workflows, or tool integrations. (file: /opt/codex/skills/.system/skill-creator/SKILL.md)
- skill-installer: Install Codex skills into $CODEX_HOME/skills from a curated list or a GitHub repo path. Use when a user asks to list installable skills, install a curated skill, or install a skill from another repo (including private repos). (file: /opt/codex/skills/.system/skill-installer/SKILL.md)
### How to use skills
- Discovery: The list above is the skills available in this session (name + description + file path). Skill bodies live on disk at the listed paths.
- Trigger rules: If the user names a skill (with `$SkillName` or plain text) OR the task clearly matches a skill's description shown above, you must use that skill for that turn. Multiple mentions mean use them all. Do not carry skills across turns unless re-mentioned.
- Missing/blocked: If a named skill isn't in the list or the path can't be read, say so briefly and continue with the best fallback.
- How to use a skill (progressive disclosure):
  1) After deciding to use a skill, open its `SKILL.md`. Read only enough to follow the workflow.
  2) If `SKILL.md` points to extra folders such as `references/`, load only the specific files needed for the request; don't bulk-load everything.
  3) If `scripts/` exist, prefer running or patching them instead of retyping large code blocks.
  4) If `assets/` or templates exist, reuse them instead of recreating from scratch.
- Coordination and sequencing:
  - If multiple skills apply, choose the minimal set that covers the request and state the order you'll use them.
  - Announce which skill(s) you're using and why (one short line). If you skip an obvious skill, say why.
- Context hygiene:
  - Keep context small: summarize long sections instead of pasting them; only load extra files when needed.
  - Avoid deep reference-chasing: prefer opening only files directly linked from `SKILL.md` unless you're blocked.
  - When variants exist (frameworks, providers, domains), pick only the relevant reference file(s) and note that choice.
- Safety and fallback: If a skill can't be applied cleanly (missing files, unclear instructions), state the issue, pick the next-best approach, and continue.
