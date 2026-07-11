#!/usr/bin/env python3
"""
OpenCode Maintenance Script
- Fetches OpenCode model catalogs (Zen free + Go paid)
- Fetches LiveBench leaderboard data
- Classifies workflows by task type
- Scores and recommends optimal models per task type
- Updates README.md with recommendation tables
- Audits workflows for model optimality
"""

import csv
import io
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import yaml

# ─── Paths ───────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
CONFIG_DIR = ROOT / "config"
DATA_DIR = ROOT / "data"
WORKFLOWS_DIR = ROOT / ".github" / "workflows"
README_PATH = ROOT / "README.md"

TASK_TYPES_PATH = CONFIG_DIR / "task-types.yaml"
WORKFLOW_MAP_PATH = CONFIG_DIR / "workflow-task-map.yaml"

# Data files
ZEN_MODELS_PATH = DATA_DIR / "zen_models.json"
GO_MODELS_PATH = DATA_DIR / "go_models.json"
LIVEBENCH_PATH = DATA_DIR / "livebench.json"
WORKFLOW_SCAN_PATH = DATA_DIR / "workflow_scan.json"
AUDIT_RESULTS_PATH = DATA_DIR / "audit_results.json"
COVERAGE_ISSUES_PATH = DATA_DIR / "coverage_issues.json"

# ─── Constants ────────────────────────────────────────────────────────────────
ZEN_URL = "https://opencode.ai/zen/v1/models"
GO_URL = "https://opencode.ai/zen/go/v1/models"
LIVEBENCH_BASE = "https://livebench.ai"
LIVEBENCH_CHANGELOG_URL = (
    "https://raw.githubusercontent.com/LiveBench/LiveBench/main/changelog.md"
)
LIVEBENCH_JSON_URLS = [
    "https://raw.githubusercontent.com/LiveBench/LiveBench/main/livebench/leaderboard/data/all_models_df.json",
    "https://raw.githubusercontent.com/LiveBench/LiveBench/main/livebench/leaderboard/data/leaderboard.json",
]

FREE_FIRST_THRESHOLD_PCT = 5  # % within best paid to prefer free

# Map LiveBench fine-grained task columns to subscore categories
LIVEBENCH_COLUMN_CATEGORIES = {
    "coding": [
        "code_completion",
        "code_generation",
        "javascript",
        "python",
        "typescript",
    ],
    "reasoning": [
        "AMPS_Hard",
        "math_comp",
        "olympiad",
        "integrals_with_game",
        "simplify",
        "logic_with_navigation",
        "consecutive_events",
        "zebra_puzzle",
        "theory_of_mind",
        "connections",
        "spatial",
    ],
    "vision": [
        "plot_unscrambling",
    ],
    "instruction_following": [
        "paraphrase",
        "summarize",
        "story_generation",
        "typos",
        "tablejoin",
        "tablereformat",
    ],
}

# Static fallback scores cache (loaded from config/model-scores.yaml)
_FALLBACK_CACHE = None


def _get_fallback_scores() -> dict:
    """Load static fallback scores for models not on LiveBench.
    Returns a normalized lookup: strips the '-free' suffix so
    that both "mimo-v2.5-free" and "mimo-v2.5" resolve correctly.
    If both foo-free and foo exist, foo-free values take priority."""
    global _FALLBACK_CACHE
    if _FALLBACK_CACHE is not None:
        return _FALLBACK_CACHE
    path = CONFIG_DIR / "model-scores.yaml"
    if path.exists():
        data = load_yaml(path)
        raw = data.get("model_scores") or {}
    else:
        raw = {}
    _FALLBACK_CACHE = {}
    SFX = "-free"
    for name, scores in raw.items():
        norm = name.strip().lower()
        if norm.endswith(SFX):
            wf = norm[: -len(SFX)]
            _FALLBACK_CACHE[norm] = scores
            if wf not in _FALLBACK_CACHE:
                _FALLBACK_CACHE[wf] = scores
        else:
            _FALLBACK_CACHE[norm] = scores
            nsfx = norm + SFX
            if nsfx not in _FALLBACK_CACHE:
                _FALLBACK_CACHE[nsfx] = scores
    return _FALLBACK_CACHE


# ─── Utils ────────────────────────────────────────────────────────────────────
def fetch_json(url: str, timeout: int = 15) -> Optional[dict]:
    """Fetch JSON from URL with timeout."""
    try:
        req = Request(url, headers={"User-Agent": "opencode-maintenance/1.0"})
        with urlopen(req, timeout=timeout) as resp:
            return json.load(resp)
    except (URLError, HTTPError, json.JSONDecodeError, TimeoutError) as e:
        print(f"  ✗ Failed to fetch {url}: {e}")
        return None


def fetch_text(url: str, timeout: int = 15) -> Optional[str]:
    """Fetch text from URL with timeout."""
    try:
        req = Request(url, headers={"User-Agent": "opencode-maintenance/1.0"})
        with urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8")
    except (URLError, HTTPError, TimeoutError) as e:
        print(f"  ✗ Failed to fetch {url}: {e}")
        return None


def fetch_livebench_csv(date_str: str) -> Optional[str]:
    """Try to fetch LiveBench CSV for a specific date."""
    url = f"{LIVEBENCH_BASE}/table_{date_str}.csv"
    return fetch_text(url)


def _to_float(v):
    try:
        return float(v) if v is not None and v != "" else None
    except (ValueError, TypeError):
        return None


def parse_livebench_csv(csv_text: str) -> dict:
    """Parse LiveBench CSV into model_name -> {overall, coding, reasoning, vision, instruction_following}.

    LiveBench CSV columns are fine-grained per-task scores (e.g. `code_completion`,
    `python`, `math_comp`). We aggregate them into subscore categories using
    `LIVEBENCH_COLUMN_CATEGORIES`.
    """
    result = {}
    try:
        reader = csv.DictReader(io.StringIO(csv_text))
        # Normalise column names to lowercase for lookup
        for row in reader:
            row_lc = {k.lower(): v for k, v in row.items() if k}
            model = row_lc.get("model") or row_lc.get("name")
            if not model:
                continue

            subscores = {}
            all_values = []
            for category, cols in LIVEBENCH_COLUMN_CATEGORIES.items():
                vals = []
                for col in cols:
                    v = _to_float(row_lc.get(col.lower()))
                    if v is not None:
                        vals.append(v)
                if vals:
                    subscores[category] = round(sum(vals) / len(vals), 1)
                    all_values.extend(vals)

            # Overall = mean of all numeric task scores (excluding model column)
            if all_values:
                subscores["overall"] = round(sum(all_values) / len(all_values), 1)
                result[model] = subscores
    except Exception as e:
        print(f"  ✗ CSV parse error: {e}")
    return result


def load_yaml(path: Path) -> dict:
    with open(path) as f:
        return yaml.safe_load(f) or {}


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def load_json(path: Path) -> Any:
    with open(path) as f:
        return json.load(f)


# ─── Model Fetching ──────────────────────────────────────────────────────────
def fetch_opencode_models() -> tuple:
    """Fetch Zen (free) and Go (paid) model catalogs."""
    print("→ Fetching OpenCode model catalogs...")

    # Fetch Zen models (all), filter free
    zen_data = fetch_json(ZEN_URL)
    if not zen_data:
        print("  ✗ Failed to fetch Zen models")
        return [], []

    all_zen = zen_data.get("data", [])
    free_models = [m for m in all_zen if m.get("id", "").endswith("-free")]
    save_json(ZEN_MODELS_PATH, {"all": all_zen, "free": free_models})
    print(f"  ✓ Zen: {len(all_zen)} total, {len(free_models)} free")

    # Fetch Go models (paid)
    go_data = fetch_json(GO_URL)
    if not go_data:
        print("  ✗ Failed to fetch Go models")
        go_models = []
    else:
        go_models = go_data.get("data", [])
        save_json(GO_MODELS_PATH, {"data": go_models})
        print(f"  ✓ Go: {len(go_models)} paid models")

    return free_models, go_models


def get_latest_livebench_date() -> Optional[str]:
    """Parse the latest snapshot date from the LiveBench changelog.

    The changelog uses `### YYYY-MM-DD` headers; the first one is the most recent.
    Returns the date in `YYYY_MM_DD` format (for use in the CSV URL), or None.
    """
    text = fetch_text(LIVEBENCH_CHANGELOG_URL)
    if not text:
        return None
    # Find all `### YYYY-MM-DD` headers in order
    matches = re.findall(r"^###\s+(\d{4}-\d{2}-\d{2})\s*$", text, re.MULTILINE)
    if not matches:
        return None
    # Changelog is ordered newest-first, so matches[0] is the latest
    return matches[0].replace("-", "_")


def fetch_livebench() -> dict:
    """Fetch and parse LiveBench leaderboard data.

    The latest snapshot date is read from the official LiveBench changelog
    (https://github.com/LiveBench/LiveBench/blob/main/changelog.md), then the
    corresponding `https://livebench.ai/table_YYYY_MM_DD.csv` is fetched.
    """
    print("→ Fetching LiveBench leaderboard...")

    date_str = get_latest_livebench_date()
    if date_str:
        print(f"  ✓ Latest LiveBench snapshot from changelog: {date_str}")
        csv_text = fetch_livebench_csv(date_str)
        if csv_text:
            scores = parse_livebench_csv(csv_text)
            if scores:
                result = {
                    "_snapshot_date": date_str,
                    "_source": f"{LIVEBENCH_BASE}/table_{date_str}.csv",
                    "models": scores,
                }
                save_json(LIVEBENCH_PATH, result)
                print(f"  ✓ LiveBench CSV ({date_str}): {len(scores)} models parsed")
                return result

    # Fallback to JSON endpoints (older format, may not exist)
    print("  ⚠ CSV fetch failed, trying JSON fallbacks...")
    for url in LIVEBENCH_JSON_URLS:
        data = fetch_json(url)
        if data:
            scores = {}
            if isinstance(data, list):
                for entry in data:
                    if isinstance(entry, dict):
                        name = (
                            entry.get("model") or entry.get("name") or entry.get("id")
                        )
                        if name:
                            scores[name] = {
                                "overall": entry.get("overall") or entry.get("Overall"),
                                "coding": entry.get("coding") or entry.get("Coding"),
                                "reasoning": entry.get("reasoning")
                                or entry.get("Reasoning"),
                                "vision": entry.get("vision") or entry.get("Vision"),
                                "instruction_following": entry.get(
                                    "instruction_following"
                                )
                                or entry.get("Instruction Following"),
                            }
            elif isinstance(data, dict):
                for name, entry in data.items():
                    if isinstance(entry, dict):
                        scores[name] = {
                            "overall": entry.get("overall") or entry.get("Overall"),
                            "coding": entry.get("coding") or entry.get("Coding"),
                            "reasoning": entry.get("reasoning")
                            or entry.get("Reasoning"),
                            "vision": entry.get("vision") or entry.get("Vision"),
                            "instruction_following": entry.get("instruction_following")
                            or entry.get("Instruction Following"),
                        }

            # Clean up scores
            cleaned = {}
            for name, s in scores.items():

                def clean(v):
                    try:
                        return round(float(v), 1) if v is not None else None
                    except (ValueError, TypeError):
                        return None

                ov = clean(s.get("overall"))
                cd = clean(s.get("coding"))
                re_s = clean(s.get("reasoning"))
                vs = clean(s.get("vision"))
                if_ = clean(s.get("instruction_following"))
                if ov is not None:
                    cleaned[name] = {
                        "overall": ov,
                        "coding": cd,
                        "reasoning": re_s,
                        "vision": vs,
                        "instruction_following": if_,
                    }

            if cleaned:
                save_json(LIVEBENCH_PATH, {"_source": url, "models": cleaned})
                print(f"  ✓ LiveBench JSON: {len(cleaned)} models parsed")
                return {"_source": url, "models": cleaned}

    print("  ⚠ No LiveBench data available, using empty scores")
    save_json(LIVEBENCH_PATH, {"models": {}})
    return {"models": {}}


# ─── Workflow Scanning ───────────────────────────────────────────────────────
def scan_workflows() -> list:
    """Scan all workflows for anomalyco/opencode usage."""
    print("→ Scanning workflows for OpenCode usage...")

    results = []
    if not WORKFLOWS_DIR.exists():
        save_json(WORKFLOW_SCAN_PATH, [])
        return []

    workflow_map = load_yaml(WORKFLOW_MAP_PATH).get("workflow_task_map") or {}
    task_types = load_yaml(TASK_TYPES_PATH).get("task_types") or []

    for wf_file in sorted(
        list(WORKFLOWS_DIR.glob("*.yml")) + list(WORKFLOWS_DIR.glob("*.yaml"))
    ):
        stem = wf_file.stem
        if stem in ("opencode-maintenance", "opencode-maintence"):
            continue  # skip self (handles both spellings)

        try:
            content = wf_file.read_text(encoding="utf-8")
            if "anomalyco/opencode" not in content:
                continue

            wf = yaml.safe_load(content) or {}
            wf_name = wf.get("name", wf_file.name)

            # Determine task type from workflow map or auto-classify
            mapped_task = workflow_map.get(stem)

            for job_id, job in (wf.get("jobs") or {}).items():
                steps = job.get("steps") or []
                for idx, step in enumerate(steps):
                    uses = step.get("uses") or ""
                    if "anomalyco/opencode" not in uses:
                        continue

                    with_block = step.get("with") or {}
                    model = str(with_block.get("model") or "NOT_SET")
                    agent = str(with_block.get("agent") or "")
                    prompt = str(with_block.get("prompt") or "")[:500]

                    # Auto-classify if not mapped
                    if mapped_task:
                        task_type = mapped_task
                    else:
                        task_type = classify_task_type(
                            wf_name,
                            job.get("name") or job_id,
                            step.get("name") or f"step-{idx}",
                            prompt,
                            task_types,
                        )

                    results.append(
                        {
                            "file": str(wf_file.relative_to(ROOT)),
                            "workflow_name": wf_name,
                            "job_id": job_id,
                            "job_name": job.get("name") or job_id,
                            "step_index": idx,
                            "step_name": step.get("name") or f"step-{idx}",
                            "action_ref": uses,
                            "model": model,
                            "agent": agent,
                            "prompt_preview": prompt,
                            "task_type": task_type,
                            "mapped": bool(mapped_task),
                        }
                    )

        except Exception as e:
            results.append(
                {
                    "file": str(wf_file.relative_to(ROOT)),
                    "workflow_name": wf_file.name,
                    "error": str(e),
                    "task_type": "other",
                }
            )

    save_json(WORKFLOW_SCAN_PATH, results)
    print(f"  ✓ Found {len(results)} OpenCode step(s) across workflows")
    return results


def classify_task_type(
    wf_name: str, job_name: str, step_name: str, prompt: str, task_types: list
) -> str:
    """Classify workflow step into task type based on signals."""
    text = " ".join([wf_name, job_name, step_name, prompt]).lower()

    for tt in task_types:
        for signal in tt.get("signals", []):
            if signal.lower() in text:
                return tt["name"]

    return "other"


# ─── Scoring & Recommendations ───────────────────────────────────────────────
# LiveBench data is stored as {"models": {name: {subscores...}}, "_source": ...}
# This helper unwraps it for the scoring functions.
def _lb_models(livebench: dict) -> dict:
    if not isinstance(livebench, dict):
        return {}
    if "models" in livebench and isinstance(livebench["models"], dict):
        return livebench["models"]
    # Backwards-compat: treat dict itself as the model map
    return {k: v for k, v in livebench.items() if not k.startswith("_")}


def _normalise_model_for_lookup(model_name: str) -> str:
    """Normalise a model name for LiveBench lookup.

    OpenCode free models carry a `-free` suffix that LiveBench doesn't use, so we
    strip it. Also normalise case and trim whitespace.
    """
    name = model_name.strip().lower()
    if name.endswith("-free"):
        name = name[:-5]
    return name


def get_model_score(model_name: str, livebench: dict, subscore: str) -> Optional[float]:
    """Get a model's subscore from LiveBench data or static fallback (case-insensitive, suffix-stripped)."""
    s = _get_model_score_and_source(model_name, livebench, subscore)
    return s[0] if s else None


def _get_model_score_and_source(
    model_name: str, livebench: dict, subscore: str
) -> Optional[tuple]:
    """Like get_model_score but returns (score, source) where source is 'livebench' or 'fallback'."""
    models = _lb_models(livebench)
    target = _normalise_model_for_lookup(model_name)

    # 1. Try LiveBench data
    for k, v in models.items():
        if _normalise_model_for_lookup(k) == target:
            return (v.get(subscore), "livebench")
    for k, v in models.items():
        k_norm = _normalise_model_for_lookup(k)
        if target and (target in k_norm or k_norm in target):
            return (v.get(subscore), "livebench")

    # 2. Try static fallback config
    fallback = _get_fallback_scores()
    name_lc = model_name.strip().lower()
    if name_lc in fallback:
        return (fallback[name_lc].get(subscore), "fallback")
    for name, scores in fallback.items():
        if _normalise_model_for_lookup(name) == target:
            return (scores.get(subscore), "fallback")
    for name, scores in fallback.items():
        k_norm = _normalise_model_for_lookup(name)
        if target and (target in k_norm or k_norm in target):
            return (scores.get(subscore), "fallback")
    return None


def get_model_source(model_name: str, livebench: dict) -> str:
    """Determine the data source for a model: 'livebench', 'fallback', or 'missing'."""
    s = _get_model_score_and_source(model_name, livebench, "overall")
    if s:
        return s[1]
    return "missing"


def get_best_models_for_task(
    task_type: str,
    free_models: list,
    go_models: list,
    livebench: dict,
    task_types: list,
) -> tuple:
    """Find best free and best paid model for a task type."""
    tt = next((t for t in task_types if t["name"] == task_type), None)
    if not tt:
        return None, None

    priority = tt.get("priority", "overall")

    # Filter models by tier
    free_ids = [m["id"] for m in free_models]
    go_ids = [m["id"] for m in go_models]

    # Score all models
    scored = []
    for model_id in free_ids + go_ids:
        score = get_model_score(model_id, livebench, priority)
        if score is not None:
            tier = "free" if model_id in free_ids else "go"
            scored.append((model_id, tier, score))

    # Fallback to config defaults if no scores
    defaults = {
        "issue-triage": ("deepseek-v4-flash-free", "deepseek-v4-flash"),
        "issue-implementation": ("north-mini-code-free", "kimi-k2.7-code"),
        "pr-review": ("nemotron-3-ultra-free", "deepseek-v4-pro"),
        "code-implementation": ("north-mini-code-free", "kimi-k2.7-code"),
        "frontend-design": ("mimo-v2.5-free", "mimo-v2-omni"),
        "frontend-testing": ("north-mini-code-free", "kimi-k2.7-code"),
        "api-testing": ("deepseek-v4-flash-free", "deepseek-v4-flash"),
    }

    if not scored:
        return defaults.get(task_type, (None, None))

    # Sort by score descending
    scored.sort(key=lambda x: x[2], reverse=True)

    best_free = next((m for m, t, s in scored if t == "free"), None)
    best_go = next((m for m, t, s in scored if t == "go"), None)

    # If no scored free/go found, try config defaults
    if not best_free and not best_go:
        return defaults.get(task_type, (None, None))

    return best_free, best_go


def get_best_zen_model_for_task(
    task_type: str,
    zen_models: list,
    livebench: dict,
    task_types: list,
) -> tuple:
    """Find best model across ALL Zen models (free + paid) for a task type.

    Returns (model_id, score, subscore_used) or (None, None, None).
    This is the overall best model regardless of tier, used as the
    benchmark reference in recommendation and audit tables.
    """
    tt = next((t for t in task_types if t["name"] == task_type), None)
    if not tt:
        return None, None, None

    priority = tt.get("priority", "overall")

    zen_ids = [m["id"] for m in zen_models]
    scored = []
    for model_id in zen_ids:
        score = get_model_score(model_id, livebench, priority)
        if score is not None:
            scored.append((model_id, score))

    if not scored:
        return None, None, None

    scored.sort(key=lambda x: x[1], reverse=True)
    best_id, best_score = scored[0]
    return best_id, best_score, priority


def score_all_zen_models(
    zen_models: list,
    livebench: dict,
    task_types: list,
) -> dict:
    """Score every Zen model across all task types.

    Returns: {
        task_type_name: [
            {"model": id, "score": float, "source": str, "rank": int},
            ...
        ]
    }
    """
    zen_ids = [m["id"] for m in zen_models]
    result = {}
    for tt in task_types:
        name = tt["name"]
        priority = tt.get("priority", "overall")
        scored = []
        for model_id in zen_ids:
            score = get_model_score(model_id, livebench, priority)
            source = get_model_source(model_id, livebench)
            if score is not None:
                scored.append({
                    "model": model_id,
                    "score": score,
                    "source": source,
                })
        scored.sort(key=lambda x: x["score"], reverse=True)
        for i, entry in enumerate(scored, 1):
            entry["rank"] = i
        result[name] = scored
    return result


def get_benchmark_summary(
    zen_models: list,
    go_models: list,
    livebench: dict,
    task_types: list,
) -> dict:
    """Generate a benchmark summary with best models per task type.

    This creates the data for data/benchmark_results.json:
    - best_zen_per_task: best overall Zen model for each task type
    - best_go_per_task: best Go (paid) model for each task type (= benchmark ceiling)
    - all_zen_ranked: full ranking of all Zen models per task type
    """
    go_ids = {m["id"] for m in go_models}

    best_zen_per_task = {}
    best_go_per_task = {}
    for tt in task_types:
        name = tt["name"]
        priority = tt.get("priority", "overall")

        # Best Zen
        zid, zscore, _ = get_best_zen_model_for_task(
            name, zen_models, livebench, task_types
        )
        best_zen_per_task[name] = {
            "model": zid,
            "score": zscore,
            "subscore": priority,
        }

        # Best Go (paid) = benchmark ceiling
        zen_ids = [m["id"] for m in zen_models]
        go_scored = []
        for model_id in zen_ids:
            if model_id not in go_ids:
                continue
            score = get_model_score(model_id, livebench, priority)
            if score is not None:
                go_scored.append((model_id, score))
        if go_scored:
            go_scored.sort(key=lambda x: x[1], reverse=True)
            gid, gscore = go_scored[0]
            best_go_per_task[name] = {
                "model": gid,
                "score": gscore,
                "subscore": priority,
            }
        else:
            best_go_per_task[name] = {
                "model": None,
                "score": None,
                "subscore": priority,
            }

    all_zen_ranked = score_all_zen_models(zen_models, livebench, task_types)

    return {
        "best_zen_per_task": best_zen_per_task,
        "best_go_per_task": best_go_per_task,
        "all_zen_ranked": all_zen_ranked,
    }


def apply_free_first_rule(
    best_free: str,
    best_go: str,
    livebench: dict,
    priority: str,
    threshold_pct: float = 5.0,
) -> tuple:
    """Apply free-first policy: if free within threshold% of paid, prefer free."""
    if not best_free or not best_go:
        return best_free, best_go

    free_score = get_model_score(best_free, livebench, priority)
    go_score = get_model_score(best_go, livebench, priority)

    if free_score is not None and go_score is not None and go_score > 0:
        pct_diff = ((go_score - free_score) / go_score) * 100
        if pct_diff <= threshold_pct:
            return best_free, best_free  # Free is close enough, use it for both

    return best_free, best_go


def _strip_model_prefix(model: str) -> str:
    """Strip common prefixes like `opencode/` from model names for comparison."""
    if not model:
        return model
    name = model.strip()
    # Strip `opencode/` or any other provider prefix
    if "/" in name and not name.startswith("http"):
        name = name.rsplit("/", 1)[-1]
    return name


def classify_model_status(
    current: str, recommended_free: str, recommended_go: str
) -> str:
    """Classify model status: ✅ Optimal, ⚠️ Suboptimal, ❌ Wrong."""
    if not current or current == "NOT_SET":
        return "❌"

    # Normalize model names for comparison (strip opencode/ prefix, lowercase)
    curr = _strip_model_prefix(current).lower().strip()
    rec_free = (
        _strip_model_prefix(recommended_free).lower().strip()
        if recommended_free
        else ""
    )
    rec_go = (
        _strip_model_prefix(recommended_go).lower().strip() if recommended_go else ""
    )

    if curr == rec_free or curr == rec_go:
        return "✅"

    # Check if current is a paid model when free equivalent exists
    is_paid = not curr.endswith("-free")
    if is_paid and rec_free and rec_free != rec_go:
        return "❌"  # Paying when free is recommended

    return "⚠️"  # Suboptimal but not wrong


# ─── README Generation ───────────────────────────────────────────────────────


# ─── Coverage Checks ──────────────────────────────────────────────────────────
def detect_coverage_issues(free_models: list, go_models: list, livebench: dict) -> dict:
    """Detect stale fallback entries and models missing scores entirely.

    Returns: {
        "stale_fallback": [{"model": str, "livebench_scores": {...}}],
        "missing_scores": [{"model": str, "tier": str}],
    }
    """
    issues = {"stale_fallback": [], "missing_scores": []}
    lb_models = _lb_models(livebench)
    fallback = _get_fallback_scores()

    # Normalise LiveBench model names for quick lookup
    lb_set = set()
    for k in lb_models:
        lb_set.add(_normalise_model_for_lookup(k))

    # Check fallback entries that are now in LiveBench
    for name in fallback:
        norm = _normalise_model_for_lookup(name)
        if norm in lb_set:
            lb_scores = {
                k: v
                for k, v in lb_models.items()
                if _normalise_model_for_lookup(k) == norm
            }
            issues["stale_fallback"].append(
                {
                    "model": name,
                    "livebench_scores": lb_scores.get(
                        norm, next(iter(lb_scores.values()), {})
                    ),
                }
            )

    # Check all OpenCode models for missing scores
    all_ids = [m["id"] for m in free_models] + [m["id"] for m in go_models]
    for model_id in sorted(all_ids):
        source = get_model_source(model_id, livebench)
        if source == "missing":
            tier = "Free" if model_id.endswith("-free") else "Go (Paid)"
            issues["missing_scores"].append({"model": model_id, "tier": tier})

    return issues


def generate_model_recommendation_table(
    task_types: list,
    free_models: list,
    go_models: list,
    livebench: dict,
    threshold_pct: float,
    zen_models: list = None,
) -> str:
    """Generate the task-type model recommendation table.

    Columns: Task Type | Description | Best Zen Model | Zen Score | Best Free Model | Free Score | Best Go Model | Go Score
    """
    models = _lb_models(livebench)
    snapshot_date = (
        livebench.get("_snapshot_date") if isinstance(livebench, dict) else None
    )
    source = livebench.get("_source") if isinstance(livebench, dict) else None

    header_lines = [
        "## Model Recommendations by Task Type",
        "",
        f"> Automatically updated by `opencode-maintenance` workflow.",
        f"> Last updated: **{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}**.",
        f"> LiveBench data: **{len(models)} models scored**.",
    ]
    if snapshot_date:
        header_lines.append(f"> LiveBench snapshot: **{snapshot_date}**.")
    if source:
        header_lines.append(f"> Source: {source}")
    header_lines.extend(
        [
            f"> Free-first threshold: **{threshold_pct}%**.",
            "",
            "| Task Type | Description | Best Zen Model | Zen Score | Best Free Model | Free Score | Best Go Model | Go Score |",
            "|-----------|-------------|----------------|-----------|-----------------|------------|---------------|----------|",
        ]
    )
    lines = header_lines

    all_zen = zen_models if zen_models else []

    for tt in task_types:
        name = tt["name"]
        desc = tt.get("description", "")
        priority = tt.get("priority", "overall")

        best_free, best_go = get_best_models_for_task(
            name, free_models, go_models, livebench, task_types
        )
        best_free, best_go = apply_free_first_rule(
            best_free, best_go, livebench, priority, threshold_pct
        )

        # Best Zen model (overall best from all Zen models)
        zen_id, zen_score, _ = get_best_zen_model_for_task(
            name, all_zen, livebench, task_types
        )

        free_score = (
            get_model_score(best_free, livebench, priority) if best_free else None
        )
        go_score = get_model_score(best_go, livebench, priority) if best_go else None

        zen_score_str = str(zen_score) if zen_score is not None else "—"
        free_score_str = str(free_score) if free_score is not None else "—"
        go_score_str = str(go_score) if go_score is not None else "—"
        zen_model_str = f"`{zen_id}`" if zen_id else "—"
        free_model_str = f"`{best_free}`" if best_free else "—"
        go_model_str = f"`{best_go}`" if best_go else "—"

        lines.append(
            f"| `{name}` | {desc} | {zen_model_str} | {zen_score_str} | {free_model_str} | {free_score_str} | {go_model_str} | {go_score_str} |"
        )

    return "\n".join(lines)


def generate_score_reference_table(
    livebench: dict,
    free_models: list,
    go_models: list,
    zen_models: list = None,
    task_types: list = None,
) -> str:
    """Generate the detailed score reference table with source indicators.

    Adds a "Best For" column that shows which task type each model is
    best suited for, based on its highest-scoring subscore relative to
    task-type priorities. Uses emoji badges for visual distinction.
    """
    models = _lb_models(livebench)
    all_model_ids = [m["id"] for m in free_models] + [m["id"] for m in go_models]

    # Build a reverse map: model -> list of task types it's best suited for.
    # For each model, find the task type whose priority subscore the
    # model scores highest on, so the "Best For" column is useful even
    # when a model isn't the absolute #1 overall.
    best_for_map = {}
    if task_types:
        for model_id in all_model_ids:
            best_task = None
            best_score = -1
            for tt in task_types:
                priority = tt.get("priority", "overall")
                score = get_model_score(model_id, livebench, priority)
                if score is not None and score > best_score:
                    best_score = score
                    best_task = tt["name"]
            if best_task:
                best_for_map.setdefault(model_id, []).append(best_task)

    # Short labels for task types in badges
    TASK_BADGES = {
        "issue-triage": "Triage",
        "issue-implementation": "Impl",
        "pr-review": "Review",
        "code-implementation": "Code",
        "frontend-design": "Design",
        "frontend-testing": "FTest",
        "api-testing": "ATest",
        "other": "Other",
    }

    lines = [
        "",
        "### LiveBench Score Reference",
        "",
        "| Model | Tier | Source | Best For | Overall | Coding | Reasoning | Vision | Instruction Following |",
        "|-------|------|--------|----------|---------|--------|-----------|--------|----------------------|",
    ]

    for model_id in sorted(all_model_ids):
        tier = "Free" if model_id.endswith("-free") else "Go (Paid)"
        source = get_model_source(model_id, livebench)
        if source == "livebench":
            src_icon = "✅ LiveBench"
        elif source == "fallback":
            src_icon = "📋 Fallback"
        else:
            src_icon = "❌ Missing"

        # Best-for badges
        tasks = best_for_map.get(model_id, [])
        if tasks:
            badges = " ".join(TASK_BADGES.get(t, t) for t in tasks)
            best_for_cell = badges
        else:
            best_for_cell = "—"

        ov = get_model_score(model_id, livebench, "overall")
        cd = get_model_score(model_id, livebench, "coding")
        re_s = get_model_score(model_id, livebench, "reasoning")
        vs = get_model_score(model_id, livebench, "vision")
        if_ = get_model_score(model_id, livebench, "instruction_following")
        lines.append(
            f"| `{model_id}` | {tier} | {src_icon} | {best_for_cell} | "
            f"{ov if ov is not None else '—'} | {cd if cd is not None else '—'} | "
            f"{re_s if re_s is not None else '—'} | {vs if vs is not None else '—'} | "
            f"{if_ if if_ is not None else '—'} |"
        )

    return "\n".join(lines)


def generate_workflow_audit_table(
    scan_results: list,
    free_models: list,
    go_models: list,
    livebench: dict,
    task_types: list,
    threshold_pct: float,
    zen_models: list = None,
) -> str:
    """Generate the workflow audit table with status icons.

    Columns: Workflow | Job | Step | Task Type | Current Model | Recommended Zen | Zen vs Current | Recommended Free | Recommended Go | Status
    The "Zen vs Current" column shows the percentage difference between the
    recommended Zen model and the current model's score.
    """
    if not scan_results:
        return "\n## Workflow Model Audit\n\n> No OpenCode workflows found (excluding maintenance workflow).\n"

    all_zen = zen_models if zen_models else []

    lines = [
        "",
        "## Workflow Model Audit",
        "",
        f"> Audited: **{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}**",
        f"> Workflows checked: **{len(set(r['file'] for r in scan_results))}**",
        f"> OpenCode steps found: **{len(scan_results)}**",
        "",
        "| Workflow | Job | Step | Task Type | Current Model | Recommended Zen | Zen vs Current | Recommended Free | Recommended Go | Status |",
        "|----------|-----|------|-----------|---------------|-----------------|----------------|------------------|----------------|--------|",
    ]

    for r in scan_results:
        if "error" in r:
            lines.append(
                f"| `{r['file']}` | — | — | `parse-error` | — | — | — | — | — | ❌ Parse Error |"
            )
            continue

        task_type = r.get("task_type", "other")
        current = r.get("model", "NOT_SET")

        best_free, best_go = get_best_models_for_task(
            task_type, free_models, go_models, livebench, task_types
        )
        best_free, best_go = apply_free_first_rule(
            best_free,
            best_go,
            livebench,
            next(
                (t["priority"] for t in task_types if t["name"] == task_type), "overall"
            ),
            threshold_pct,
        )

        # Best Zen model and % diff vs current
        zen_id, zen_score, _ = get_best_zen_model_for_task(
            task_type, all_zen, livebench, task_types
        )
        priority = next(
            (t["priority"] for t in task_types if t["name"] == task_type), "overall"
        )
        current_score = get_model_score(
            _strip_model_prefix(current), livebench, priority
        )

        zen_diff_str = "—"
        if zen_id and zen_score is not None and current_score is not None and current_score > 0:
            zen_pct = ((zen_score - current_score) / current_score) * 100
            if abs(zen_pct) >= 0.5:
                zen_diff_str = f"+{zen_pct:.0f}%" if zen_pct > 0 else f"{zen_pct:.0f}%"
            else:
                zen_diff_str = "≈0%"
        zen_display = f"`{zen_id}`" if zen_id else "—"

        status = classify_model_status(current, best_free, best_go)

        # Compute percentage diff and trophy display
        free_score = (
            get_model_score(best_free, livebench, priority) if best_free else None
        )
        go_score = (
            get_model_score(best_go, livebench, priority) if best_go else None
        )

        diff_str = ""
        if (
            best_free
            and best_go
            and best_free != best_go
            and free_score is not None
            and go_score is not None
            and free_score > 0
        ):
            pct = ((go_score - free_score) / free_score) * 100
            if abs(pct) >= 1:
                diff_str = f" (+{pct:.0f}%)" if pct > 0 else f" ({pct:.0f}%)"

        # Add trophy icon to the recommended model that is preferred
        if best_free and best_go and best_free == best_go:
            free_display = f"\U0001f3c6 `{best_free}`"
            go_display = "\u2014"
        elif best_go and best_free:
            free_display = f"`{best_free}`"
            go_display = f"\U0001f3c6 `{best_go}`{diff_str}"
        elif best_go:
            free_display = "\u2014"
            go_display = f"\U0001f3c6 `{best_go}`{diff_str}"
        elif best_free:
            free_display = f"\U0001f3c6 `{best_free}`"
            go_display = "\u2014"
        else:
            free_display = "\u2014"
            go_display = "\u2014"

        workflow = r.get("workflow_name", r["file"])
        job = r.get("job_name", r["job_id"])
        step = r.get("step_name", f"step-{r['step_index']}")

        lines.append(
            f"| `{workflow}` | `{job}` | `{step}` | `{task_type}` | "
            f"`{current}` | {zen_display} | {zen_diff_str} | {free_display} | {go_display} | {status} |"
        )

    lines.append("")
    lines.append(
        "_Legend: ✅ Optimal · ⚠️ Suboptimal · ❌ Wrong (paying when free equivalent exists). "
        "\U0001f3c6 marks the preferred model after free-first policy (free within 5% of best Go \u2192 prefer free). "
        "Zen vs Current: +X% means the best Zen model scores X% higher than the current model._"
    )

    return "\n".join(lines)


def update_readme(model_table: str, score_table: str, audit_table: str) -> bool:
    """Update README.md with the new tables."""
    print("→ Updating README.md...")

    if README_PATH.exists():
        content = README_PATH.read_text(encoding="utf-8")
    else:
        content = "# opencode-actions\n\n"

    # Define markers for sections to replace
    sections = {
        "## Model Recommendations by Task Type": model_table,
        "### LiveBench Score Reference": score_table,
        "## Workflow Model Audit": audit_table,
    }

    for marker, new_content in sections.items():
        if marker in content:
            # Replace from marker to next ## or ### or end
            parts = content.split(marker)
            before = parts[0]
            after_marker = parts[1] if len(parts) > 1 else ""
            # Find next section header
            next_header = re.search(r"\n(?=## |### )", after_marker)
            if next_header:
                after = after_marker[next_header.start() :]
            else:
                after = ""
            content = before + new_content + after
        else:
            # Append at end
            content = content.rstrip() + "\n\n" + new_content

    README_PATH.write_text(content, encoding="utf-8")
    print("  ✓ README.md updated")
    return True


# ─── Main ────────────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("OpenCode Maintenance - Model Audit & README Update")
    print("=" * 60)

    # Load config
    task_types = load_yaml(TASK_TYPES_PATH).get("task_types") or []
    threshold_pct = load_yaml(TASK_TYPES_PATH).get("free_first_threshold_pct") or 5

    # 1. Fetch model catalogs
    free_models, go_models = fetch_opencode_models()

    # 2. Fetch LiveBench scores
    livebench = fetch_livebench()

    # 3. Scan workflows
    scan_results = scan_workflows()

    # 4. Generate recommendations & audit
    print("→ Computing recommendations...")

    # All Zen models (free + paid) for benchmark scoring
    zen_data_obj = load_json(ZEN_MODELS_PATH) if ZEN_MODELS_PATH.exists() else {}
    all_zen_models = zen_data_obj.get("all", [])

    model_table = generate_model_recommendation_table(
        task_types, free_models, go_models, livebench, threshold_pct,
        zen_models=all_zen_models,
    )
    score_table = generate_score_reference_table(
        livebench, free_models, go_models,
        zen_models=all_zen_models, task_types=task_types,
    )
    audit_table = generate_workflow_audit_table(
        scan_results, free_models, go_models, livebench, task_types, threshold_pct,
        zen_models=all_zen_models,
    )

    # 5. Generate and save benchmark data
    print("→ Generating benchmark data...")
    benchmark = get_benchmark_summary(
        all_zen_models, go_models, livebench, task_types
    )
    benchmark_path = DATA_DIR / "benchmark_results.json"
    save_json(
        benchmark_path,
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "livebench_snapshot": livebench.get("_snapshot_date")
            if isinstance(livebench, dict)
            else None,
            "livebench_source": livebench.get("_source")
            if isinstance(livebench, dict)
            else None,
            "zen_models_count": len(all_zen_models),
            "go_models_count": len(go_models),
            **benchmark,
        },
    )
    print(f"  ✓ Benchmark data saved to {benchmark_path}")

    # 6. Update README
    update_readme(model_table, score_table, audit_table)

    # 7. Save audit results for CI
    audit_results = []
    for r in scan_results:
        if "error" in r:
            audit_results.append(
                {
                    "file": r["file"],
                    "workflow": r["workflow_name"],
                    "status": "parse_error",
                    "error": r["error"],
                }
            )
            continue

        task_type = r.get("task_type", "other")
        current = r.get("model", "NOT_SET")

        best_free, best_go = get_best_models_for_task(
            task_type, free_models, go_models, livebench, task_types
        )
        best_free, best_go = apply_free_first_rule(
            best_free,
            best_go,
            livebench,
            next(
                (t["priority"] for t in task_types if t["name"] == task_type), "overall"
            ),
            threshold_pct,
        )

        status = classify_model_status(current, best_free, best_go)

        # Determine preferred tier and compute % diff
        if best_free and best_go and best_free == best_go:
            preferred_tier = "free"
        elif best_go:
            preferred_tier = "go"
        elif best_free:
            preferred_tier = "free"
        else:
            preferred_tier = None

        priority = next(
            (t["priority"] for t in task_types if t["name"] == task_type), "overall"
        )
        free_score = (
            get_model_score(best_free, livebench, priority) if best_free else None
        )
        go_score = get_model_score(best_go, livebench, priority) if best_go else None

        preferred_diff = None
        if (
            best_free
            and best_go
            and best_free != best_go
            and free_score is not None
            and go_score is not None
            and free_score > 0
        ):
            pct = ((go_score - free_score) / free_score) * 100
            if abs(pct) >= 1:
                preferred_diff = round(pct)

        audit_results.append(
            {
                "file": r["file"],
                "workflow": r["workflow_name"],
                "job": r["job_name"],
                "step": r["step_name"],
                "task_type": task_type,
                "current_model": current,
                "recommended_free": best_free,
                "recommended_go": best_go,
                "preferred_tier": preferred_tier,
                "preferred_diff": preferred_diff,
                "status": status,
            }
        )

    save_json(
        AUDIT_RESULTS_PATH,
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "livebench_snapshot": livebench.get("_snapshot_date")
            if isinstance(livebench, dict)
            else None,
            "livebench_source": livebench.get("_source")
            if isinstance(livebench, dict)
            else None,
            "livebench_models": len(_lb_models(livebench)),
            "free_models": len(free_models),
            "go_models": len(go_models),
            "workflows_audited": len(set(r["file"] for r in scan_results)),
            "steps_audited": len(scan_results),
            "results": audit_results,
        },
    )

    # 8. Detect coverage issues (stale fallback, missing scores)
    print("→ Checking model coverage...")
    coverage = detect_coverage_issues(free_models, go_models, livebench)
    save_json(COVERAGE_ISSUES_PATH, coverage)
    if coverage.get("stale_fallback"):
        for m in coverage["stale_fallback"]:
            print(f"  ⚠ Stale fallback: {m['model']} is now in LiveBench")
    if coverage.get("missing_scores"):
        for m in coverage["missing_scores"]:
            print(f"  ❌ Missing scores: {m['model']} ({m['tier']})")
    if not coverage.get("stale_fallback") and not coverage.get("missing_scores"):
        print("  ✓ All models have scores, no stale fallback entries")

    stale = len(coverage.get("stale_fallback", []))
    missing = len(coverage.get("missing_scores", []))

    print("=" * 60)
    print("✅ Maintenance complete")
    print(f"  Workflows audited: {len(set(r['file'] for r in scan_results))}")
    print(f"  Steps checked: {len(scan_results)}")
    print(f"  LiveBench models: {len(_lb_models(livebench))}")
    if isinstance(livebench, dict) and livebench.get("_snapshot_date"):
        print(f"  LiveBench snapshot: {livebench['_snapshot_date']}")
    print(f"  README updated: {README_PATH}")
    print(f"  Audit data: {AUDIT_RESULTS_PATH}")
    print("=" * 60)

    # Exit with error code if any ❌ found (for CI) or coverage issues
    has_errors = any(r.get("status") == "❌" for r in audit_results)
    has_coverage = bool(
        coverage.get("stale_fallback") or coverage.get("missing_scores")
    )
    sys.exit(1 if (has_errors or has_coverage) else 0)


if __name__ == "__main__":
    main()
