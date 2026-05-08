---
name: weave-fleet
description: >
  Resolves, configures, and registers Elastic Fleet integration packages (EPM) for a
  loom engagement. Reads discovery and data model to determine which packages to
  install, performs an asset catalog review to surface use-as-is / clone-and-modify /
  storyline-enhancement opportunities, generates deploy/{slug}-integrations-manifest.json
  and demo/{slug}-integration-assets.md, and injects an idempotent install step into
  bootstrap.py. Supports ECH (full Fleet) and Serverless (asset-only mode).

  ALWAYS use this skill when the data model includes any logs-* or metrics-* data streams.
  This skill decides whether each stream should be backed by a real integration package
  (Path A) or managed-template fallback naming (Path B). Also trigger when the SA says
  trigger when the SA says "install the kubernetes integration", "use Fleet for log
  collection", "EPM package install", "I want the out-of-the-box dashboards", "set up the
  integration", or "install integration packages for the demo".
---

# Demo Fleet Integrations

You are selecting, cataloging, and registering Elastic integration packages (EPM) for a
pre-sales demo environment. This is a **planning stage** — you produce a manifest and an
asset guide that `bolt-launch` consumes when generating `deploy/bootstrap.py`. You do not
install packages directly unless the SA explicitly asks for a live cluster operation and
a `.env` is present.

**Deployability (D-025):** Every API path and body you reference must be valid for the
resolved target stack version (baseline 9.4+, D-033). Do not reference Fleet APIs that
are unavailable on Serverless.

---

## Step 0: Resolve deployment type and stack version

Read `{engagement_dir}/.env` for `DEPLOYMENT_TYPE` (`ech` | `serverless`) and
`ELASTIC_VERSION`. If `.env` is absent, check `demo/{slug}-platform-audit.json` for
`platform.version` and `platform.deployment_type`.

**ECH mode** — full Fleet: package install + agent policy creation + enrollment token.

**Serverless mode** — asset-only: package install is valid (creates dashboards, ingest
pipelines, index templates). Fleet Server enrollment is not supported on Serverless.
Set `"mode": "asset-only"` in the manifest; omit agent policy creation from bootstrap.

If neither source is available, default to `"mode": "asset-only"` and flag as unverified.

---

## Step 0.5: Validate data stream strategy (Path A / Path B contract)

Read `data/{slug}-data-model.json` and inspect every `logs-*` / `metrics-*` stream.

For each stream, classify it:

1. **Path A — Fleet package backed**
   - Stream matches `logs-<integration>.<dataset>-<namespace>` or
     `metrics-<integration>.<dataset>-<namespace>`
   - `<integration>` resolves to a known package in this skill's catalog

2. **Path B — Managed-template fallback**
   - Stream matches `logs-demo.<dataset>-<namespace>` or `metrics-demo.<dataset>-<namespace>`
   - No package install required for that stream

If a stream matches neither path (e.g. `security-events-*`, `metrics-gpu.*`, uppercase naming),
stop and return a `schema_contract_error` with the exact stream name and expected replacement.

---

## Step 1: Select packages from data model and discovery

Read `data/{slug}-data-model.json` and `demo/{slug}-discovery.json`. Derive the candidate
package list from three sources, in priority order:

**1a. Integration-grounded Vulcan output** — if `data/{slug}-vulcan-queries.json` exists
and `integration_grounded: true`, use the `index_name_map` keys to identify integration
patterns (e.g. `logs-kubernetes.container_logs-*` → `kubernetes` package).

**1b. Data model index patterns** — for each index or data stream whose name follows
`logs-<integration>.*` or `metrics-<integration>.*`, the integration package is required.
Extract the integration name from the pattern and add to the candidate list.

**1c. Discovery profile** — scan `demo/{slug}-discovery.json` for named technologies in
`current_tools`, `data_sources`, `infrastructure`, and `pain_points`. Map to packages:

| Technology mention | Package name |
|---|---|
| Kubernetes / K8s / containers | `kubernetes` |
| Linux / Windows host metrics | `system` |
| NVIDIA GPU / DCGM / GPU utilization | `nvidia_gpu` |
| Generic custom logs stream | `custom_logs` (optional Path B scaffolding) |
| Generic custom metrics stream | `custom_metrics` (optional Path B scaffolding) |
| APM / traces / OpenTelemetry | `apm` |
| Synthetic monitoring / uptime / availability | `synthetics` |
| Nginx / Apache | `nginx` |
| AWS CloudWatch / EC2 | `aws` |

For any candidate not derivable from the above, ask the SA before adding it.

---

## Step 2: Resolve package versions

For each candidate package:

**If a live cluster is available** (`.env` present with valid credentials):
```
GET {KIBANA_URL}/api/fleet/epm/packages/{name}
```
Read `item.latestVersion` from the response. Use that version. Log a warning if the
package is unavailable (`404`) or version-incompatible.

**If no live cluster** — use `references/package-versions.md` to look up the
recommended version for the target stack version range. Never hardcode a version without
this reference.

Do not proceed with a package whose version cannot be resolved. Ask the SA to confirm
or skip the package.

---

## Step 3: Asset catalog review and storyline enhancement check

After packages are selected, inspect each package's known assets against the demo script.
Read `references/package-asset-catalog.md` for the offline catalog (or query the live EPM
API: `GET /api/fleet/epm/packages/{name}/{version}` and inspect `response.item.assets`).

**For each selected package, catalog:**
- Shipped dashboards (name, Kibana path, what it visualizes)
- ML modules (job names, what anomaly they detect)
- Saved searches and visualizations
- Detection rules (Security packages)
- Ingest pipelines and transforms

**Cross-reference against `demo/{slug}-demo-script.md` using the shared asset taxonomy:**

| Class | Definition | Action |
|---|---|---|
| `use_as_is` | Asset directly supports an existing demo scene with no structural changes | Reference in script; import via bootstrap step 1c |
| `clone_and_modify` | Asset is structurally close; needs field remapping, branding, or minor query edits | Note fields to remap; add clone step to bootstrap |
| `storyline_enhancement` | Asset surfaces a capability not currently scripted; high-value addition | Prompt SA to consider adding a scene |

**Write `demo/{slug}-integration-assets.md`** — SA-facing guide organized by package.
Use this entry format for every asset (shared format with future `thread-audit`
asset discovery pass):

```
- [use_as_is | clone_and_modify | storyline_enhancement] {asset_name} ({asset_type})
  Source: {package_name}
  Kibana path: {path or "n/a"}
  Action: {one specific sentence — what to do with this asset}
```

Example output:
```markdown
## kubernetes

- [use_as_is] Kubernetes Pod Health (dashboard)
  Source: kubernetes
  Kibana path: /app/dashboards#/view/kubernetes-f4dc26db-1b53-4ea2-a4b7-1f5a1db4b9b0
  Action: Import via bootstrap step 1c; reference in Scene 2 (K8s infrastructure visibility)

- [clone_and_modify] Kubernetes Node Metrics (dashboard)
  Source: kubernetes
  Kibana path: /app/dashboards#/view/kubernetes-nodeinfo-...
  Action: Clone and remap `kubernetes.node.name` to customer node naming convention before import

- [storyline_enhancement] kubernetes.apiserver.request.count anomaly detection (ML module)
  Source: kubernetes
  Kibana path: n/a
  Action: Not in current script — strong add for Scene 3; enables "API server saturation" moment
```

**Human gate — storyline enhancements found:**
After writing `demo/{slug}-integration-assets.md`, if any assets are classified
`storyline_enhancement`, surface this prompt to the SA:

> "`demo/{slug}-integration-assets.md` lists integration assets that could strengthen
> the demo script. Would you like to re-run `weave-script` with this context
> before finalizing the data model?"

If the SA accepts, stop here and run `weave-script` again with
`demo/{slug}-integration-assets.md` added to its input context. If the SA declines,
proceed to Step 3b.

---

## Step 3b: Conflict detection

Cross-reference `managed_index_patterns` from each package against the index patterns
defined in `data/{slug}-data-model.json`. If a custom component template or index template
targets the same pattern as a package template:

1. Flag it as a `schema_overlap_warning` in the manifest
2. Recommend resolution: remove the custom template and rely on the integration's template,
   OR use a higher-priority custom template that explicitly extends the integration's mappings
3. Surface the conflict in the output so the data modeler can be updated if needed

---

## Step 3c: Generate `deploy/{slug}-integrations-manifest.json`

Write the manifest to `{engagement_dir}/deploy/{slug}-integrations-manifest.json`:

```json
{
  "slug": "{slug}",
  "deployment_type": "ech|serverless",
  "mode": "full|asset-only",
  "generated_at": "<ISO8601>",
  "packages": [
    {
      "name": "kubernetes",
      "version": "1.62.0",
      "install_reason": "K8s pod logs — logs-kubernetes.container_logs-* index pattern in data model",
      "managed_index_patterns": ["logs-kubernetes.*", "metrics-kubernetes.*"],
      "managed_dashboards": true,
      "conflicts_with": [],
      "asset_catalog": {
        "use_as_is": ["Kubernetes Pod Health", "Kubernetes Cluster Overview"],
        "clone_and_modify": ["Kubernetes Node Metrics"],
        "storyline_enhancements": ["ML module: kubernetes.apiserver.request.count anomaly detection"]
      }
    }
  ],
  "agent_policy": {
    "create": true,
    "name": "{slug}-demo-policy",
    "description": "Demo agent policy — {slug}",
    "namespace": "default",
    "enrollment_token_note": "Policy created for completeness; no agents enrolled in bootstrap"
  },
  "conflict_warnings": [],
  "schema_overlap_warnings": []
}
```

Set `"agent_policy": { "create": false }` when `mode` is `"asset-only"` (Serverless).

---

## Step 4: Generate bootstrap step 1c

Produce the Python function to embed in `deploy/bootstrap.py` as **step 1c** — inserted
after step 1b (Kibana Space creation) and before step 2 (ILM policies). Fleet packages
must be installed before custom index templates because packages register their own
templates; installing after causes name-collision errors.

```python
# ── Step 1c: Fleet integration packages ─────────────────────────────────────
def step_1c_fleet_integrations():
    """Install EPM packages idempotently. Must run before ILM/templates (step 2)."""
    from pathlib import Path
    manifest_path = SCRIPT_DIR / "{slug}-integrations-manifest.json"
    if not manifest_path.exists():
        print("  step 1c: No integrations manifest — skipping Fleet packages")
        return
    manifest = json.loads(manifest_path.read_text())
    mode = manifest.get("mode", "asset-only")
    for pkg in manifest.get("packages", []):
        name, version = pkg["name"], pkg["version"]
        url = f"{KB_URL}{SPACE_PATH}/api/fleet/epm/packages/{name}/{version}"
        try:
            _kb_post(url, {"force": True})
            print(f"  ✅ {name} {version} installed")
        except Exception as e:
            if "already_installed" in str(e).lower() or "already installed" in str(e).lower():
                print(f"  ✅ {name} {version} already installed")
            else:
                print(f"  ⚠️  {name} {version} install warning: {e}")
                raise
    if mode == "full" and manifest.get("agent_policy", {}).get("create"):
        policy = manifest["agent_policy"]
        _kb_post(f"{KB_URL}{SPACE_PATH}/api/fleet/agent_policies", {
            "name": policy["name"],
            "description": policy.get("description", ""),
            "namespace": policy.get("namespace", "default"),
            "monitoring_enabled": []
        })
        print(f"  ✅ Agent policy '{policy['name']}' created")
```

Include this function in the `STEPS` dict at step `"1c"`:
```python
STEPS = {
    "1":  step_1_connectivity,
    "1b": step_1b_kibana_space,
    "1c": step_1c_fleet_integrations,   # ← new
    "2":  step_2_ilm_policies,
    ...
}
```

---

## Step 5: Generate teardown block

Produce the teardown section for `deploy/teardown.py`. This reads from the cluster-resident
manifest (`loom-manifests` index, D-031) and falls back to the local manifest:

```python
# ── Fleet integrations teardown ──────────────────────────────────────────────
def teardown_fleet_integrations(manifest):
    pkgs = manifest.get("assets", {}).get("fleet_integrations", {}).get("packages", [])
    policy_ids = manifest.get("assets", {}).get("fleet_integrations", {}).get("agent_policy_ids", [])
    for pkg in pkgs:
        name, version = pkg["name"], pkg["version"]
        try:
            _kb_delete(f"{KB_URL}/api/fleet/epm/packages/{name}/{version}")
            print(f"  ✅ Uninstalled {name} {version}")
        except Exception as e:
            print(f"  ⚠️  Could not uninstall {name}: {e}")
    for policy_id in policy_ids:
        try:
            _kb_delete(f"{KB_URL}/api/fleet/agent_policies/{policy_id}")
            print(f"  ✅ Deleted agent policy {policy_id}")
        except Exception as e:
            print(f"  ⚠️  Could not delete agent policy {policy_id}: {e}")
```

---

## Outputs

| File | Location | Purpose |
|---|---|---|
| `{slug}-integrations-manifest.json` | `deploy/` | Machine-readable: packages, versions, policies, asset catalog, warnings — consumed by `bootstrap.py` and `teardown.py` |
| `{slug}-integration-assets.md` | `demo/` | SA-facing: use-as-is / clone-modify / storyline enhancements per package; shared taxonomy with future platform-audit asset discovery |

---

## Asset catalog pattern note

This skill implements the **package-scoped** instance of a broader asset discovery pattern.
The `thread-audit` skill will implement the **cluster-resident** instance (existing
Agent Builder agents, deployed ML jobs, detection rules, etc.) using the same taxonomy and
entry format. See `docs/decisions.md` D-037 note on shared asset taxonomy.

When the platform-audit asset discovery pass is implemented, `weave-script` will
consume both outputs — giving the SA a unified view before the script is finalized.

---

## References

- `references/package-versions.md` — offline version compatibility table (use when no live cluster)
- `references/package-asset-catalog.md` — offline asset catalog per package (use in Step 3 when no live EPM API)
- `skills/bolt-launch/references/asset-manifest.md` — manifest schema including `fleet_integrations` key
- `docs/decisions.md` D-025 (deployable API shapes), D-033 (9.4+ baseline)

---

## Acceptance criteria

- [ ] `python3 deploy/bootstrap.py --step 1c` installs all scoped packages idempotently
- [ ] Re-run does not reinstall already-installed packages (checks version match)
- [ ] `deploy/{slug}-integrations-manifest.json` records all installed package names, versions, managed index patterns, and asset catalog classification
- [ ] `demo/{slug}-integration-assets.md` is written with at least one entry per installed package, classified using the shared taxonomy
- [ ] `deploy/teardown.py` successfully removes all fleet integration assets and agent policies
- [ ] Works on ECH 9.x (full mode) and Serverless Elasticsearch (asset-only mode)
- [ ] Warns clearly when a package is unavailable or version-incompatible
