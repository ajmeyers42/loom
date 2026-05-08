# Engagement root: `DEMOBUILDER_ENGAGEMENTS_ROOT`

## Why

- **Portable repo:** The loom git tree holds **pipeline skills** (`skills/`, `docs/`) only. Customer-specific files stay **out of version control** under your user profile.
- **Sharable:** You can push the repo without engagement data; each machine uses the same default layout.
- **Cloud-synced option:** Point the root at a cloud-synced folder (Google Drive, OneDrive) so engagements are available on any machine without a separate copy step.

## Convention

| Variable | Meaning |
|----------|---------|
| `DEMOBUILDER_ENGAGEMENTS_ROOT` | Absolute path to a directory that **contains** one folder per engagement |

**Default (when unset):** **`$HOME/engagements`** — a normal folder in your home directory (not a cloud symlink). Agents and scripts should resolve engagement paths as:

`"${DEMOBUILDER_ENGAGEMENTS_ROOT:-$HOME/engagements}/{slug}/"`

Override only if you want engagements somewhere else:

```bash
export DEMOBUILDER_ENGAGEMENTS_ROOT="/custom/path"
```

Engagement workspace for slug `{slug}`:

`$DEMOBUILDER_ENGAGEMENTS_ROOT/{slug}/`

Example: `~/engagements/2026CitizensAI/`

## Setup

1. Create the default root once (optional — tools can create it when needed):

```bash
mkdir -p "$HOME/engagements"
```

2. Optionally pin the variable in `~/.zshrc` / `~/.bashrc` (same default as above, explicit):

```bash
export DEMOBUILDER_ENGAGEMENTS_ROOT="$HOME/engagements"
```

3. Point the agent at **`$DEMOBUILDER_ENGAGEMENTS_ROOT/{slug}`** when running the orchestrator or a single skill.

## Agents

Skills and [`AGENTS.md`](../AGENTS.md): if `DEMOBUILDER_ENGAGEMENTS_ROOT` is unset, use **`$HOME/engagements`** before asking the SA.

## Cloud-synced root (Google Drive / OneDrive)

You can point `DEMOBUILDER_ENGAGEMENTS_ROOT` at a cloud-synced folder for cross-device access. Engagement files are written locally first; the sync client uploads in the background.

### Google Drive for Desktop (macOS)

Google Drive mounts under `~/Library/CloudStorage/`. Find your mount:

```bash
ls ~/Library/CloudStorage/ | grep Google
# e.g. GoogleDrive-you@elastic.co
```

Set the root to **My Drive**:

```bash
# Add to ~/.zshrc
export DEMOBUILDER_ENGAGEMENTS_ROOT="$HOME/Library/CloudStorage/GoogleDrive-you@elastic.co/My Drive/engagements"

# Create the folder
mkdir -p "$DEMOBUILDER_ENGAGEMENTS_ROOT"
```

### OneDrive (macOS)

OneDrive also mounts under `~/Library/CloudStorage/`. The pattern is the same:

```bash
ls ~/Library/CloudStorage/ | grep OneDrive
# e.g. OneDrive-Elastic

export DEMOBUILDER_ENGAGEMENTS_ROOT="$HOME/Library/CloudStorage/OneDrive-Elastic/engagements"
mkdir -p "$DEMOBUILDER_ENGAGEMENTS_ROOT"
```

### Things to know when using a cloud-synced root

| Topic | Detail |
|-------|--------|
| **Spaces in path** | `My Drive` contains a space. Always quote the env var in shell scripts: `"${DEMOBUILDER_ENGAGEMENTS_ROOT}"`. The pipeline skills already quote it correctly. |
| **Credentials (`.env`)** | Each engagement's `.env` holds `ES_API_KEY` and cluster URLs. These **will sync to the cloud provider**. For Elastic-managed Google/OneDrive this is acceptable; for personal accounts or shared drives, consider keeping `.env` local and symlinking it. |
| **Offline / poor connectivity** | Writes land on the local Drive cache immediately; sync resumes when connected. No data loss on a train or spotty connection. |
| **Large files** | `vulcan-data/*.csv` and diagnostic ZIPs can be large. They will count toward cloud storage and sync time. Exclude them from Drive sync if needed. |
| **Python scripts** | `bootstrap.py` and `teardown.py` run fine from paths with spaces as long as you invoke them with the path quoted. |
| **Migrating an existing root** | Copy with `cp -Rp ~/engagements/. "$DEMOBUILDER_ENGAGEMENTS_ROOT/"`, verify in Drive, then `rm -rf ~/engagements`. |

## Decision record

See `docs/decisions.md` **D-019** and **D-023**.
