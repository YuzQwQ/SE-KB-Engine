# Obsidian integration ownership model

SE-KB treats an Obsidian Vault as a projection and user interface, not as the canonical corpus.

| Layer | Owner | Mutability | Recovery |
| --- | --- | --- | --- |
| Versioned artifacts and manifests | SE-KB | Published through existing artifact contracts | Authoritative source |
| Vector index | SE-KB | Rebuildable derived data | Re-index artifacts |
| Managed Vault directory (`SE-KB/` by default) | SE-KB exporter | Updated only when the last published hash still matches | Re-export artifacts |
| Notes outside the managed directory | User | Never rewritten or deleted by the exporter | User backups/Vault history |
| Semantic suggestions | SE-KB retrieval projection | Approximate and rebuildable | Recompute from the selected index |

The integration is disabled until a Vault root is explicitly configured. A preview never writes files. Publication must preserve modified, unknown, conflicted, and stale files by default. Bidirectional body synchronization and automatic cleanup are outside the first delivery.

## Configure and prepare a Vault

1. Create or choose an existing Obsidian Vault and back it up according to your normal policy.
2. Set `OBSIDIAN_VAULT_ROOT` to its absolute local path. Optionally set `OBSIDIAN_VAULT_NAME`; otherwise the directory name is used for deep links.
3. Keep `OBSIDIAN_MANAGED_DIRECTORY=SE-KB` unless a different relative namespace is required. Do not point it at an existing user-authored folder.
4. Start the Web console, enter an admin service key, open **知识图谱**, and check that status is `ready`.
5. Run **生成预览** before the first publication. Review every conflict, skipped item, and stale item.
6. Use **导出到 Vault** only after the preview matches the intended source and entity filters.

The exporter creates the managed directory on first publication. Obsidian does not need to be running. Network access, community plugins, embedding calls, and paid model calls are not required for explicit-link export or the default test suite.

## Preview and publication behavior

- `create`: no managed file exists at the deterministic destination.
- `update`: the existing file still matches the last exporter-owned hash and rendered content changed.
- `rename`: a stable identity changed display path; the owned prior file is removed only after the new file verifies.
- `unchanged`: bytes already match and are not rewritten.
- `conflict`: a user changed the generated file, the destination is unowned, or expected state is missing. The file is preserved.
- `skipped`: the destination or input cannot be safely projected.
- `stale`: the source is no longer selected. The file is retained by default.

Writes use temporary files, hash verification, and atomic replacement where the host filesystem supports it. Export state is committed last. A failed or cancelled run never records a partial projection as successful.

## Conflict recovery

Do not delete or overwrite a conflict blindly. Compare the generated source artifact, the current Vault note, and any user changes. Move valuable human content to a user-owned note outside the managed directory, restore the generated file to its last exporter-owned contents if appropriate, then preview again. If exporter state is corrupt or from a newer version, the integration enters read-only protection until an operator resolves it.

## Privacy and security

Generated notes can expose source URLs, document titles, extracted text, quality/trace metadata, explicit links, and approximate semantic associations. Treat the Vault as a copy of the underlying corpus when applying access control, backup, synchronization, and sharing policies. Semantic suggestions are labeled approximations, not asserted facts. Service credentials are never written to notes.

All destinations are resolved beneath the managed root. Traversal, absolute children, control characters, and symlink/reparse-point escapes are rejected. The Web API returns logical Vault paths instead of unrelated host filesystem paths.

## Rollback

Unset `OBSIDIAN_VAULT_ROOT` or stop using the export endpoints to disable the integration. Existing Vault output remains readable and is not automatically deleted. If the projection is no longer needed, review and back up the exact managed directory before removing it manually; source artifacts and vector indexes are unaffected and can rebuild the projection later.

## Offline verification

The default checks use temporary Vault fixtures only:

```powershell
uv run pytest tests/test_obsidian_foundations.py tests/test_obsidian_projection.py tests/test_obsidian_relationships.py tests/test_obsidian_export.py tests/test_obsidian_service.py tests/test_obsidian_api.py tests/test_obsidian_canvas.py -q
uv run python scripts/quality.py
```

These commands do not launch Obsidian or access external services.

## JSON Canvas compatibility

Optional Canvas output follows JSON Canvas 1.0 and is disabled by default. The exporter uses only the portable top-level `nodes` and `edges` arrays, file nodes (`id`, `type`, `file`, `x`, `y`, `width`, `height`, optional `color`), and directed edges (`id`, `fromNode`, `toNode`, optional sides, arrow, color, and label). File paths are Vault-relative. Node and edge IDs and the grid layout are deterministic so unchanged inputs remain byte-stable.

Reference: <https://jsoncanvas.org/spec/1.0/>. Obsidian deep links use the encoded `obsidian://open?vault=...&file=...` form documented at <https://help.obsidian.md/Extending%2BObsidian/Obsidian%2BURI>.
