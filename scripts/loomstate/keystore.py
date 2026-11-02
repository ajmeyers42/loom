"""Per-engagement keystore ({engagement_dir}/.env): status, sample, manual set, sibling clone.

Never prints secret values. Private identity (company / opportunity) never lands in .env.
"""

from __future__ import annotations

import json
import re
import ssl
import urllib.error
import urllib.request
from pathlib import Path

from . import solution as space_solution
from .core import LoomError, find_identity_leaks, normalize_tag_id, now_iso, write_text_atomic

REQUIRED_KEYS = ("ELASTICSEARCH_URL", "KIBANA_URL", "ES_API_KEY", "KIBANA_API_KEY")
SECRET_RE = re.compile(r"(_API_KEY|_KEY|_TOKEN|_SECRET|PASSWORD)$")
PRIVATE_IDENTITY_RE = re.compile(r"^(COMPANY|CUSTOMER|OPPORTUNITY|SFDC|CRM|ACCOUNT_NAME)")
# Keys that always describe *this* engagement — never copied from a sibling.
THIS_SLUG_KEYS = ("DEMO_SLUG", "ENGAGEMENT", "KIBANA_SPACE_PATH", "KIBANA_SOLUTION", "INDEX_PREFIX")
# Copied only when the SA opts in (--keep).
CLONE_OPT_IN = ("DEMO_ASSET_TAG", "CLUSTER_NAME", "DEPLOYMENT_ID")

SOLUTION_TO_KIBANA = {"security": "security", "observability": "oblt"}  # everything else → classic
KIBANA_SOLUTIONS = space_solution.KIBANA_SOLUTIONS
MIN_VERSION = (9, 4)


def kibana_solution(solution: str, fallback: str = space_solution.DEFAULT_SOLUTION) -> str:
    """Space solution for an engagement's declared solution: security / oblt when explicit, else classic."""
    return SOLUTION_TO_KIBANA.get(solution, fallback or space_solution.DEFAULT_SOLUTION)


def current_kibana_solution(eng) -> str:
    """This engagement's KIBANA_SOLUTION: recorded value (SA choice or suggestion), else derived from the solution."""
    rec = eng.state.get("kibana_solution") or {}
    if rec.get("value"):
        return rec["value"]
    return kibana_solution(eng.state.get("solution", ""))


def kibana_solution_status(eng) -> dict:
    """Input-settings view: the value in use, whether the SA confirmed it, and the suggestion behind it."""
    rec = eng.state.get("kibana_solution") or {}
    value = current_kibana_solution(eng)
    return {
        "value": value,
        "source": rec.get("source") or "default",
        "confirmed": rec.get("source") == "sa",
        "confidence": rec.get("confidence"),
        "reason": rec.get("reason"),
        "suggested": rec.get("suggested") or (value if rec.get("source") != "sa" else None),
        "options": list(KIBANA_SOLUTIONS),
    }


def refresh_kibana_solution(eng, profile: dict | None = None) -> list[str]:
    """Infer the Kibana space solution from the engagement (notes, discovery, profile) and record it as a suggestion.

    Observability / security only when clear; otherwise classic. Never overrides an SA choice
    (`keys set KIBANA_SOLUTION=…`). Called at create, `listen record` and `qualify record`. Returns messages.
    """
    rec = eng.state.get("kibana_solution") or {}
    if rec.get("source") == "sa":
        return []
    found = space_solution.infer(eng, profile)
    new = {"value": found["value"], "source": "inferred", "confidence": found["confidence"],
           "reason": found["reason"], "signals": found["signals"]}
    eng.state["kibana_solution"] = new
    for name in (".env.example", ".env"):
        p = eng.dir / name
        if p.exists() and parse_env(p).get("KIBANA_SOLUTION") != new["value"]:
            write_env(p, {"KIBANA_SOLUTION": new["value"]})
    if rec.get("value") == new["value"] and rec.get("reason") == new["reason"]:
        return []
    return [f"KIBANA_SOLUTION={new['value']} suggested — {new['reason']}. Override in input settings: "
            f"loom_state keys set {eng.slug} KIBANA_SOLUTION={'|'.join(KIBANA_SOLUTIONS)}"]


def is_set(value: str | None) -> bool:
    v = (value or "").strip()
    return bool(v) and not (v.startswith("<") and v.endswith(">"))


def parse_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for line in path.read_text().splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        key, _, val = s.partition("=")
        key = key.strip().removeprefix("export ").strip()
        val = val.split(" #", 1)[0].strip().strip('"').strip("'")
        values[key] = val
    return values


def write_env(path: Path, updates: dict[str, str], header: str | None = None) -> None:
    """Update keys in place (preserving comments/order); append new keys."""
    lines = path.read_text().splitlines() if path.exists() else []
    if not lines and header:
        lines = header.rstrip("\n").splitlines()
    seen = set()
    out = []
    for line in lines:
        s = line.strip()
        key = s.partition("=")[0].strip().removeprefix("export ").strip() if "=" in s and not s.startswith("#") else None
        if key and key in updates:
            out.append(f"{key}={updates[key]}")
            seen.add(key)
        else:
            out.append(line)
    for key, val in updates.items():
        if key not in seen:
            out.append(f"{key}={val}")
    write_text_atomic(path, "\n".join(out) + "\n", mode=0o600)


def env_template(slug: str, display: str, solution: str, example: bool) -> str:
    """Render .env / .env.example per skills/references/env-reference.md (public identity only)."""
    ph = (lambda s: f"<{s}>") if example else (lambda s: "")
    return f"""# {'.env.example — copy to .env and fill in values' if example else 'Engagement keystore — never commit'}
# See: skills/references/env-reference.md
# Public demo identity only — company / opportunity names live in {slug}-pipeline-state.json, never here.

DEMO_SLUG={slug}
ENGAGEMENT={display}
DEPLOYMENT_TYPE={ph('serverless|ech|self_managed|docker')}
DEPLOY_MODE=terraform

# D-020: must match live cluster version (loom_state keys validate --probe sets it)
ELASTIC_VERSION={ph('e.g.-9.5.0')}

ELASTICSEARCH_URL={ph('https://your-cluster.es.io:443')}
KIBANA_URL={ph('https://your-kibana.kb.io:443')}
# APM_SERVER_URL=
# MANAGED_OTLP_URL=
# FLEET_SERVER_URL=
# FLEET_ENROLLMENT_TOKEN=

ES_API_KEY={ph('your-es-api-key')}
KIBANA_API_KEY={ph('your-kibana-api-key')}

KIBANA_SPACE_PATH=/s/{slug}
# Space solution view: classic | es | oblt | security — loom suggests one from the notes (oblt / security only when
# clear, otherwise classic); change it here or with `loom_state keys set {slug} KIBANA_SOLUTION=…`.
KIBANA_SOLUTION={kibana_solution(solution)}

# Leave blank on a dedicated cluster; required (distinct) when sharing a cluster.
INDEX_PREFIX=
# DEMO_ASSET_TAG=
# INCLUDE_TOKEN_VISIBILITY=true
"""


def compute_status(values: dict[str, str]) -> tuple[str, list[str]]:
    missing = [k for k in REQUIRED_KEYS if not is_set(values.get(k))]
    if len(missing) == len(REQUIRED_KEYS):
        return "empty", missing
    return ("partial" if missing else "complete"), missing


def presence_summary(values: dict[str, str]) -> str:
    if not values:
        return "no .env"
    es_kb = is_set(values.get("ELASTICSEARCH_URL")) and is_set(values.get("KIBANA_URL"))
    keys = is_set(values.get("ES_API_KEY")) and is_set(values.get("KIBANA_API_KEY"))
    status, _ = compute_status(values)
    parts = ["ES+Kibana set" if es_kb else "endpoints missing", "keys set" if keys else "keys missing"]
    return f"{status} · " + " · ".join(parts)


def _norm_url(url: str) -> str:
    return (url or "").strip().rstrip("/").lower()


def default_index_prefix(slug: str) -> str:
    parts = slug.split("-")
    if parts[0] == "acme" and len(parts) > 1:
        base = "a" + parts[1][:2]
    else:
        base = "".join(p[0] for p in parts)[:3] or slug[:3]
    return base + "-"


def siblings(root: Path, slug: str) -> list[dict]:
    out = []
    if not root.exists():
        return out
    for d in sorted(p for p in root.iterdir() if p.is_dir() and not p.name.startswith(".")):
        if d.name == slug:
            continue
        env = d / ".env"
        vals = parse_env(env)
        out.append({
            "slug": d.name,
            "has_env": env.exists(),
            "summary": presence_summary(vals),
            "es_url": vals.get("ELASTICSEARCH_URL", ""),
            "index_prefix": vals.get("INDEX_PREFIX", ""),
            "tag_id": normalize_tag_id(vals.get("DEMO_ASSET_TAG") or vals.get("INDEX_PREFIX") or d.name),
        })
    return out


def _check_values_public(values: dict[str, str], identity: dict) -> None:
    leaks = {}
    for k, v in values.items():
        hits = find_identity_leaks(v or "", identity)
        if hits:
            leaks[k] = hits
    if leaks:
        keys = ", ".join(sorted(leaks))
        raise LoomError(f"Refusing to write private identity into .env (keys: {keys}). "
                        "Use the public Acme display name / slug only.")
    bad = [k for k in values if PRIVATE_IDENTITY_RE.match(k)]
    if bad:
        raise LoomError(f"Private identity variables are not allowed in .env: {', '.join(bad)}")


def _record(eng, values: dict[str, str], source: str | None, cloned_from: str | None = None) -> dict:
    status, missing = compute_status(values)
    ks = eng.state.setdefault("keystore", {})
    ks.update({
        "status": status,
        "missing": missing,
        "updated_at": now_iso(),
        "validated_at": None,
        "deferred": False if status != "empty" else ks.get("deferred", False),
    })
    if source:
        ks["source"] = source
    if cloned_from is not None:
        ks["cloned_from"] = cloned_from
    if values.get("ELASTIC_VERSION") and is_set(values.get("ELASTIC_VERSION")):
        ks["elastic_version"] = values["ELASTIC_VERSION"]
    return ks


def _identity_defaults(eng) -> dict[str, str]:
    ident = eng.state.get("identity", {})
    return {
        "DEMO_SLUG": eng.slug,
        "ENGAGEMENT": ident.get("public_display_name", eng.slug),
        "KIBANA_SPACE_PATH": f"/s/{eng.slug}",
        "KIBANA_SOLUTION": current_kibana_solution(eng),
    }


def env_path(eng) -> Path:
    p = eng.dir / ".env"
    if p.is_symlink():
        target = p.resolve()
        if target.parent.parent == eng.dir.parent and target.parent != eng.dir:
            raise LoomError(f".env is a symlink into another engagement ({target.parent.name}); "
                            "each slug needs its own keystore file. Remove it and clone instead.")
    return p


def init_from_sample(eng) -> dict:
    env = env_path(eng)
    if env.exists() and any(is_set(v) for v in parse_env(env).values()):
        raise LoomError(".env already exists with values; use `keys set` to edit.")
    template = env_template(eng.slug, eng.state["identity"]["public_display_name"], eng.state.get("solution", ""), False)
    write_text_atomic(env, template, mode=0o600)
    write_env(env, {"KIBANA_SOLUTION": current_kibana_solution(eng)})
    values = parse_env(env)
    return _record(eng, values, "sample")


def set_values(eng, updates: dict[str, str]) -> dict:
    env = env_path(eng)
    forbidden = [k for k in updates if k in ("DEMO_SLUG", "KIBANA_SPACE_PATH") and updates[k] not in
                 (eng.slug, f"/s/{eng.slug}")]
    if forbidden:
        raise LoomError(f"{', '.join(forbidden)} must stay bound to this engagement ({eng.slug}).")
    if "KIBANA_SOLUTION" in updates:
        if updates["KIBANA_SOLUTION"] not in KIBANA_SOLUTIONS:
            raise LoomError(f"KIBANA_SOLUTION must be one of {', '.join(KIBANA_SOLUTIONS)}")
        prior = eng.state.get("kibana_solution") or {}
        eng.state["kibana_solution"] = {"value": updates["KIBANA_SOLUTION"], "source": "sa",
                                        "suggested": prior.get("suggested") or (prior.get("value") if prior.get("source") != "sa" else None)}
    _check_values_public(updates, eng.state.get("identity", {}))
    if not env.exists():
        write_text_atomic(env, env_template(eng.slug, eng.state["identity"]["public_display_name"],
                                            eng.state.get("solution", ""), False), mode=0o600)
    write_env(env, {**_identity_defaults(eng), **updates})
    return _record(eng, parse_env(env), "manual")


def defer(eng) -> dict:
    ks = eng.state.setdefault("keystore", {})
    ks["deferred"] = True
    ks["updated_at"] = now_iso()
    return ks


def clone(eng, root: Path, source_slug: str, include_secrets: bool = True, index_prefix: str | None = None,
          keep: tuple[str, ...] = ()) -> dict:
    """Copy values from a sibling keystore into this engagement's .env (by value, never by link)."""
    src_dir = root / source_slug
    src_env = src_dir / ".env"
    if src_dir.resolve().parent != root.resolve():
        raise LoomError("Clone source must be a sibling under the configured engagements root.")
    if source_slug == eng.slug:
        raise LoomError("Cannot clone a keystore into itself.")
    if not src_env.exists():
        raise LoomError(f"Sibling '{source_slug}' has no .env to clone.")
    src = parse_env(src_env)
    bad_keep = [k for k in keep if k not in CLONE_OPT_IN]
    if bad_keep:
        raise LoomError(f"--keep only accepts {', '.join(CLONE_OPT_IN)}")

    copied, skipped = {}, {}
    for k, v in src.items():
        if k in THIS_SLUG_KEYS:
            skipped[k] = "bound to this engagement"
        elif PRIVATE_IDENTITY_RE.match(k):
            skipped[k] = "private identity — never cloned"
        elif k in CLONE_OPT_IN and k not in keep:
            skipped[k] = "opt-in only (--keep)"
        elif SECRET_RE.search(k) and not include_secrets:
            skipped[k] = "secret — excluded (--no-secrets)"
        else:
            copied[k] = v

    updates = {**copied, **_identity_defaults(eng)}

    es_url = _norm_url(copied.get("ELASTICSEARCH_URL", ""))
    shared = bool(es_url) and es_url == _norm_url(src.get("ELASTICSEARCH_URL", ""))
    if shared:
        taken = {s["index_prefix"] for s in siblings(root, eng.slug)
                 if _norm_url(s["es_url"]) == es_url and s["index_prefix"]}
        taken_tags = {s["tag_id"] for s in siblings(root, eng.slug) if _norm_url(s["es_url"]) == es_url}
        prefix = index_prefix or default_index_prefix(eng.slug)
        if not prefix.endswith("-"):
            prefix += "-"
        if index_prefix and (prefix in taken or normalize_tag_id(prefix) in taken_tags):
            raise LoomError(f"INDEX_PREFIX '{prefix}' is already used on this cluster by a sibling.")
        n = 2
        base = prefix[:-1]
        while prefix in taken or normalize_tag_id(prefix) in taken_tags:
            prefix = f"{base}{n}-"
            n += 1
        updates["INDEX_PREFIX"] = prefix
    else:
        updates["INDEX_PREFIX"] = parse_env(eng.dir / ".env").get("INDEX_PREFIX", "")

    _check_values_public(updates, eng.state.get("identity", {}))
    env = env_path(eng)
    if not env.exists():
        write_text_atomic(env, env_template(eng.slug, eng.state["identity"]["public_display_name"],
                                            eng.state.get("solution", ""), False), mode=0o600)
    write_env(env, updates)
    ks = _record(eng, parse_env(env), "clone", source_slug)
    return {
        "keystore": ks,
        "copied": sorted(copied),
        "skipped": skipped,
        "shared_cluster": shared,
        "index_prefix": updates.get("INDEX_PREFIX", ""),
    }


def _get_json(url: str, api_key: str, timeout: float = 10.0) -> dict:
    req = urllib.request.Request(url, headers={"Authorization": f"ApiKey {api_key}", "kbn-xsrf": "loom"})
    with urllib.request.urlopen(req, timeout=timeout, context=ssl.create_default_context()) as resp:
        return json.loads(resp.read().decode())


def _version_tuple(v: str) -> tuple[int, ...]:
    return tuple(int(x) for x in re.findall(r"\d+", v)[:3])


def validate(eng, probe: bool = False) -> dict:
    """Completeness check; with probe=True also read-only GET / and Kibana /api/status (D-020)."""
    env = env_path(eng)
    values = parse_env(env)
    status, missing = compute_status(values)
    result = {"status": status, "missing": missing, "probed": False, "warnings": []}
    if values.get("DEMO_SLUG") and values["DEMO_SLUG"] != eng.slug:
        result["warnings"].append(f"DEMO_SLUG={values['DEMO_SLUG']} does not match {eng.slug}")
    if values.get("KIBANA_SPACE_PATH") and values["KIBANA_SPACE_PATH"] != f"/s/{eng.slug}":
        result["warnings"].append("KIBANA_SPACE_PATH is not this engagement's space")
    if probe:
        if status != "complete":
            raise LoomError(f"Cannot probe: keystore is {status} (missing {', '.join(missing)}).")
        try:
            es = _get_json(values["ELASTICSEARCH_URL"].rstrip("/") + "/", values["ES_API_KEY"])
            kb = _get_json(values["KIBANA_URL"].rstrip("/") + "/api/status", values["KIBANA_API_KEY"])
        except (urllib.error.URLError, TimeoutError, ValueError) as e:
            raise LoomError(f"Read-only probe failed: {e}")
        es_ver = (es.get("version") or {}).get("number", "")
        kb_ver = ((kb.get("version") or {}).get("number")) or ""
        result.update({"probed": True, "elastic_version": es_ver, "kibana_version": kb_ver})
        if es_ver and _version_tuple(es_ver) < MIN_VERSION:
            result["warnings"].append(f"Elasticsearch {es_ver} is below the 9.4 floor (D-033)")
        if es_ver:
            write_env(env, {"ELASTIC_VERSION": es_ver})
        ks = _record(eng, parse_env(env), None)
        ks.update({"status": "validated", "validated_at": now_iso(), "elastic_version": es_ver or None})
        result["status"] = "validated"
    else:
        _record(eng, values, None)
    return result
