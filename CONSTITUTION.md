# KCP Constitution

## Scope boundaries
- Implement KCP v1 only.
- v2/v3 are backlog and placeholder-only.

## Change policy
- No refactors without explicit ticket scope.
- No incidental renames/reformatting.
- Prefer additive, backwards-safe schema and API changes.

## Data safety
- Never delete user data in `output/kcp`.
- Prefer archive flags over destructive operations.
- Use additive migrations.

## Evidence policy
- For each batch, provide commands run and outputs.
- Include touched symbols and limited high-risk before/after snippets.
