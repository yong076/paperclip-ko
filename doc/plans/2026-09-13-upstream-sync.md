# Korean fork upstream update and synchronization

Target: upstream master `c9e3bb7ca40160b2ff80958ec1a8c0254638ad42`.
Starting local master: `0a51ba53d989347f93239f2b3684fc09e0387b8d`.
Starting origin master: `8749127bc0dd78512b1b108576fd3a7f1fa21d3e`.

The local checkout was missing 1,175 upstream commits; origin was missing 2,012.
A normal merge preserves the Korean fork history and the previous local fixes.
Linux sandbox test gating and source-only Vitest collection now use upstream's
equivalent implementations. The onboarding launcher retains Korean copy while
using upstream's current agent step and cloud creation rules.

## Verification and upgrade requirements

- Node.js 24.11+ and Rust/rustfmt are required for the complete source build.
- Run `pnpm typecheck`, `pnpm test:run`, `pnpm build`, and
  `pnpm check:token-gates` with the correct toolchain on PATH.
- Run `python3 scripts/test_sync_upstream.py` for synchronization behavior.
- The fetched upstream lockfile does not match its patched dependency settings.
  Resolve locally with `pnpm install --no-frozen-lockfile`; follow the repository's
  lockfile policy for CI-generated lockfile changes.
- Before deployment, retain the previous Git revision, local changes, launch
  configuration, instance configuration, encryption key, uploads, and a native
  PostgreSQL logical backup outside this repository.
- Use PostgreSQL 18 `pg_dump` and `psql`. The older JavaScript backup omitted
  CHECK constraints: restoring that backup caused migration 0255 to fail while
  dropping `tool_connections_transport_check`. The live database had the
  constraint. Do not treat a successful gzip check as proof of a complete backup.
- Native backup restore and all 94 pending migrations were tested in a separate
  embedded PostgreSQL instance. Counts remained: 1 organization, 14 agents,
  127 issues, 61 comments, and 0 approvals. Migration inspection reported
  `upToDate`. This proves restoration and migration of that snapshot; it does
  not replace application smoke testing.
- Keep `PAPERCLIP_PG_DUMP_PATH` and `PAPERCLIP_PSQL_PATH` pointed at compatible
  PostgreSQL tools for future backups and restores.

## Recurring upstream checks

`scripts/sync-upstream.py` clones the fork into a temporary directory and fetches
upstream master. It does not read or modify the running instance or live checkout.
The default mode checks whether a clean merge is possible:

```sh
python3 scripts/sync-upstream.py
```

The scheduled operator command is:

```sh
python3 scripts/sync-upstream.py --publish \
  --status-file "$HOME/.local/state/paperclip-upstream-sync/status.json"
```

Mac Studio runs this weekly on Monday at 09:00 local time via the user launch
agent `com.trappist.paperclip-upstream-sync`. Its installed script is copied from
the reviewed commit into `~/.local/share/paperclip-upstream-sync/`; changes to the
repository script require reinstalling that copy. Logs and the latest structured
result are under `~/.local/state/paperclip-upstream-sync/`.

The scheduler uses the operator's existing GitHub SSH and `gh` authentication.
It creates only `upstream-sync/<commit>` branches and draft PRs. It never force
pushes, changes master, merges PRs, or restarts the app. Conflicts return a nonzero
exit and list affected files in the status record; resolve them in a normal
reviewed update. A prior PR is reused rather than duplicated. PR creation errors
are reported and retried on the next run.

The old GitHub weekly schedule failed because `GITHUB_TOKEN` could not push
upstream workflow changes, then GitHub disabled it for inactivity. The GitHub
workflow is now a manual alternative using the same script. It requires a
separate `UPSTREAM_SYNC_TOKEN` with repository and workflow write permissions;
without it the workflow fails explicitly. The Mac Studio schedule does not
require this secret or upload local credentials to GitHub.

## Rollback

Stop only the Paperclip launch agent. Restore the saved checkout/revision and
the previous Node/launch configuration. If migrations have run, restore the
pre-upgrade native backup to a clean database together with its matching
encryption key and uploads before starting the old server. Do not run the old
server against the migrated database as a rollback shortcut.
