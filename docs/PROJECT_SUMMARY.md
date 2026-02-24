# Project Summary

## What KCP is
Keyframe Consistency Pack (KCP) is a standalone ComfyUI custom node pack for consistent story keyframe generation.

## v1 architecture overview
- `kcp/db`: SQLite pathing, migration, and CRUD repositories.
- `kcp/nodes`: ComfyUI node classes for init/assets/stacks/composition/policies/status/keyframe set persistence.
- `kcp/policies`: Built-in variant policy templates and engine.
- `kcp/util`: JSON/path/hash/time helpers and optional image thumbnail tooling.
- `kcp/schemas`: JSON schema files for asset/stack/variant list/shotlist payloads.

## Repo map
- `tools/context.py`: environment preflight summary.
- `tools/verify.py`: compile/test oracle runner + receipt writer.
- `tickets/`: small execution tickets.
- `docs/DECISIONS.md`: append-only ADR-lite history.
- `docs/OPEN_DECISIONS.md`: append-only unresolved choices and assumptions.
