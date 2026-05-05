# Fleet Integration Package Asset Catalog — Offline Reference

Used by `demo-fleet-integrations` Step 3 (asset catalog review) when no live EPM API is
available. Lists known shipped assets per package for the baseline stack version (9.4+).

Asset entry format (shared taxonomy — also used by future `demo-platform-audit` asset discovery):
```
- [use_as_is | clone_and_modify | storyline_enhancement] {asset_name} ({asset_type})
  Source: {package_name}
  Kibana path: {path or "n/a"}
  Action: {one specific sentence}
```

*Last updated: 2026-05-01 | Stack baseline: 9.4+*

---

## kubernetes

### Dashboards
| Asset | Type | Kibana object ID (partial) | What it shows |
|---|---|---|---|
| Kubernetes / Pods | Dashboard | `kubernetes-f4dc26db-...` | Pod status, restarts, CPU/memory per pod |
| Kubernetes / Nodes | Dashboard | `kubernetes-nodeinfo-...` | Node-level CPU, memory, disk, network |
| Kubernetes / Cluster Overview | Dashboard | `kubernetes-cluster-...` | Cluster-wide resource utilization |
| Kubernetes / DaemonSets | Dashboard | `kubernetes-daemonsets-...` | DaemonSet health and scheduling |
| Kubernetes / Deployments | Dashboard | `kubernetes-deployments-...` | Rollout status, available replicas |
| Kubernetes / Namespaces | Dashboard | `kubernetes-namespaces-...` | Resource usage by namespace |

### ML modules
| Asset | Type | What it detects |
|---|---|---|
| `kubernetes.apiserver.request.count` | Anomaly detection | API server request rate anomalies |
| `kubernetes.pod.memory.usage.limit.pct` | Anomaly detection | Pod memory approaching limit |
| `kubernetes.node.cpu.usage.pct` | Anomaly detection | Node CPU saturation |

### Ingest pipelines
| Asset | Type | Purpose |
|---|---|---|
| `logs-kubernetes.audit_logs-*` | Ingest pipeline | Parses kube-audit JSON logs |
| `logs-kubernetes.container_logs-*` | Ingest pipeline | Container stdout/stderr normalization |
| `metrics-kubernetes.state_pod-*` | Ingest pipeline | kube-state-metrics normalization |

### Demo classification guidance
- Pods / Cluster Overview dashboards → `use_as_is` for infrastructure visibility scenes
- Node Metrics dashboard → `clone_and_modify` if customer has custom node naming
- ML modules → `storyline_enhancement` unless anomaly detection is already in script

---

## system

### Dashboards
| Asset | Type | What it shows |
|---|---|---|
| System / Host Overview | Dashboard | CPU, memory, disk, network per host |
| System / Overview | Dashboard | Fleet of hosts summary |
| System / SSH login attempts | Dashboard | Failed/successful login events |
| System / Sudo commands | Dashboard | Privilege escalation events |

### ML modules
| Asset | Type | What it detects |
|---|---|---|
| `hosts.network.out.bytes` | Anomaly detection | Unusual outbound network volume (exfil pattern) |
| `process.cpu.pct` | Anomaly detection | CPU spike by process |

### Demo classification guidance
- Host Overview → `use_as_is` for ops/infrastructure scenes
- SSH login / Sudo dashboards → `storyline_enhancement` for Security-adjacent demos
- Network ML module → `storyline_enhancement` for data exfil storylines

---

## nvidia_gpu

### Dashboards
| Asset | Type | What it shows |
|---|---|---|
| NVIDIA GPU Overview | Dashboard | GPU utilization, memory, temperature, power draw per GPU |
| NVIDIA GPU / Cluster | Dashboard | Aggregate GPU utilization across all nodes |

### Metrics provided
- `nvidia_gpu.activity.gpu.pct` — GPU core utilization %
- `nvidia_gpu.memory.used.bytes` / `nvidia_gpu.memory.total.bytes` — VRAM usage
- `nvidia_gpu.power.draw.watts` — power consumption
- `nvidia_gpu.temperature.core.celsius` — thermal state

### Demo classification guidance
- GPU Overview → `use_as_is` for GPU infrastructure visibility scenes (AI/ML workload demos)
- Cluster dashboard → `use_as_is` for fleet-level GPU utilization
- All metrics → cross-reference against `data/{slug}-data-model.json`; if custom TSDB
  template already maps the same fields, flag as `schema_overlap_warning`

---

## apm

### Dashboards
| Asset | Type | What it shows |
|---|---|---|
| APM / Service Overview | Dashboard | Latency, throughput, error rate per service |
| APM / Dependencies | Dashboard | Downstream service dependencies and latency |
| APM / Transactions | Dashboard | Transaction breakdown by type |

### Other assets
- Service maps (auto-generated from trace data — not a shipped dashboard)
- Latency SLO alert templates
- ML modules: `transaction.duration.us` anomaly detection per service

### Demo classification guidance
- Service Overview → `use_as_is` if APM scenes are in the script
- Dependencies → `use_as_is` for microservices / distributed tracing scenes
- ML transaction duration → `storyline_enhancement` if anomaly detection not in scope yet

---

## synthetics

### Dashboards
| Asset | Type | What it shows |
|---|---|---|
| Synthetics / Overview | Dashboard | Monitor status, uptime %, SLA compliance |
| Synthetics / Monitor Detail | Dashboard | Single monitor latency, cert expiry, step waterfall |

### Demo classification guidance
- Overview → `use_as_is` for availability / SRE storylines
- Monitor Detail → `clone_and_modify` to highlight customer-specific endpoints
- Both → `storyline_enhancement` if endpoint health checking is not yet in the script

---

## nginx

### Dashboards
| Asset | Type | What it shows |
|---|---|---|
| Nginx / Overview | Dashboard | Request rate, error rate, active connections |
| Nginx / Logs | Dashboard | Access log breakdown by status code and URL |

### Demo classification guidance
- Overview → `use_as_is` for web tier observability scenes
- Logs → `clone_and_modify` to apply customer URL patterns

---

## aws

### Dashboards (representative — package ships 20+ dashboards)
| Asset | Type | What it shows |
|---|---|---|
| AWS / EC2 | Dashboard | Instance CPU, network, disk by region |
| AWS / S3 | Dashboard | Bucket request rates, error rates, data transferred |
| AWS / RDS | Dashboard | Database connections, query latency, I/O |
| AWS / ELB | Dashboard | Load balancer request counts, latency, 5xx rate |
| AWS / CloudTrail | Dashboard | API call volume, failed auth attempts |

### Demo classification guidance
- EC2 / ELB → `use_as_is` for AWS infrastructure visibility
- CloudTrail → `storyline_enhancement` for Security-adjacent demos (API abuse detection)
- RDS → `clone_and_modify` if demo uses a specific database identifier

---

## custom_logs

### Purpose
- Generic Fleet package for arbitrary log payloads when no domain-specific package exists.
- Best fit for `logs-demo.<dataset>-<namespace>` fallback streams.

### Notes
- Provides package scaffolding and a valid logs data stream shape.
- Does not replace domain-specific packages (`kubernetes`, `system`, `nginx`, etc.) when those fit.

### Demo classification guidance
- Use as `use_as_is` only for fallback path where no canonical package is available.
- Prefer package-native datasets first; use `custom_logs` to keep conventions without inventing index names.

---

## custom_metrics

### Purpose
- Generic Fleet package for arbitrary metric payloads when no domain-specific package exists.
- Best fit for `metrics-demo.<dataset>-<namespace>` fallback streams.

### Notes
- Keeps stream naming and ECS compatibility aligned for Metrics Explorer / Infrastructure UI baselines.
- Does not replace domain-specific metrics packages (`nvidia_gpu`, `kubernetes`, `system`, etc.) when those fit.

### Demo classification guidance
- Use as `use_as_is` only when no real package maps to the demo dataset.
- Prefer integration-native package datasets when available.

---

## Maintenance notes

- Dashboard Kibana object IDs are partial; resolve full IDs via
  `GET /api/saved_objects/_find?type=dashboard&search_fields=title&search={name}` on a
  live cluster with the package installed.
- ML module names correspond to `job_id` prefixes — exact IDs are
  `{package}-{metric}-{anomaly_type}`.
- This catalog covers assets shipped in the package; custom assets created by the SA
  (cloned dashboards, modified queries) are not tracked here — they belong in the
  engagement's `deploy/kibana-objects/` directory.
