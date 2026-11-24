# Fleet Integration Package Versions — Offline Reference

Used by `weave-fleet` Step 2 when no live cluster is available.
Maps Elastic stack version ranges to tested, compatible package versions for the
initial supported packages. Update this table after each stack release cycle.

*Last updated: 2026-11-24 | Default stack: Elastic 9.6*

---

## Version compatibility table

| Package | Stack 8.17.x | Stack 9.0–9.3 | Stack 9.4–9.5 | Stack 9.6 (default) |
|---|---|---|---|---|
| `kubernetes` | 1.57.x | 1.60.x | 1.62.0 | Resolve live from EPM |
| `system` | 1.54.x | 1.57.x | 1.58.4 | Resolve live from EPM |
| `nvidia_gpu` | 1.14.x | 1.16.x | 1.17.0 | Resolve live from EPM |
| `custom_logs` | 1.1.x | 1.2.x | 1.3.0 | Resolve live from EPM |
| `custom_metrics` | 1.1.x | 1.2.x | 1.3.0 | Resolve live from EPM |
| `apm` | 8.17.x | 9.0.x | 9.4.0 | Resolve live from EPM |
| `synthetics` | 1.4.x | 1.5.x | 1.6.2 | Resolve live from EPM |
| `nginx` | 1.18.x | 1.20.x | 1.20.3 | Resolve live from EPM |
| `aws` | 2.26.x | 2.29.x | 2.31.0 | Resolve live from EPM |

> **Note:** Always prefer resolving versions live via `GET /api/fleet/epm/packages/{name}`
> when a cluster is available. Use this table only as a planning fallback.
> 9.6 was just released, so this offline reference intentionally does not pin 9.6
> package versions yet; `weave-fleet` must resolve the live EPM catalog before locking
> package versions for a 9.6 demo.

---

## Version resolution rules

1. **Use the latest patch in the row** for the target stack version range.
2. **Major version bumps** (e.g. `apm` 8.x → 9.x) require verifying the index pattern
   and field changes — do not assume backward compatibility.
3. **`nvidia_gpu`** is not guaranteed to exist on all Serverless regions. Check availability
   before including in Serverless manifests.
4. **`apm`** on ECH: the APM integration ships with the stack; do not install separately
   unless the engagement specifically needs a standalone Fleet-managed APM server config.
5. For packages not listed here, query the live catalog or ask the SA for confirmation
   before adding to the manifest.

---

## How to update this table

After a stack release:
1. Spin up a test cluster on the new version.
2. Run `GET /api/fleet/epm/packages?category=observability&prerelease=false` to list
   available packages and their latest versions.
3. Update the table above and note the date.
