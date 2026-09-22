"""
Pure fantasy-football power ranking helpers.

No Yahoo I/O. ``YahooLeagueFetcher.power_rankings`` / ``fetch_all_for_week``
call :func:`compute_power_rankings` after loading last week's ranks and
prior-week matchups from recap_history / weekdata files.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

APP_ROOT = Path(__file__).resolve().parent.parent

# Weeks 1–3: win% is too noisy; lean on points.
EARLY_WEIGHTS: Tuple[float, float, float] = (0.20, 0.70, 0.10)
# Week 4+: win% matters, PF stays primary, shrink differential (it double-counts PF).
LATE_WEIGHTS: Tuple[float, float, float] = (0.45, 0.50, 0.05)

L3_BLEND_WEEK = 4
SEASON_BLEND = 0.60
L3_BLEND = 0.40
HEAT_RANK_DELTA = 2


def weights_for_week(week: int) -> Tuple[float, float, float]:
    """Return (win%, PF, differential) weights for ``week``."""
    if int(week) < L3_BLEND_WEEK:
        return EARLY_WEIGHTS
    return LATE_WEIGHTS


def format_movement(current_rank: int, previous_rank: Optional[int]) -> str:
    """``▲2`` / ``▼1`` / ``—`` from current vs previous rank (1 = best)."""
    if previous_rank is None:
        return "—"
    try:
        delta = int(previous_rank) - int(current_rank)
    except (TypeError, ValueError):
        return "—"
    if delta > 0:
        return f"▲{delta}"
    if delta < 0:
        return f"▼{abs(delta)}"
    return "—"


def heat_from_ranks(
    season_rank: Optional[int],
    l3_rank: Optional[int],
    *,
    threshold: int = HEAT_RANK_DELTA,
) -> str:
    """
    One-liner heat check for the recap writer — not a second ranking.

    L3 rank better than season rank by ``threshold`` spots → ``surging``.
    Worse by ``threshold`` → ``sliding``. Otherwise ``steady``.
    """
    if season_rank is None or l3_rank is None:
        return "steady"
    try:
        delta = int(season_rank) - int(l3_rank)
    except (TypeError, ValueError):
        return "steady"
    if delta >= threshold:
        return "surging"
    if delta <= -threshold:
        return "sliding"
    return "steady"


def team_id_or_none(row: Dict[str, Any]) -> Optional[int]:
    raw = row.get("team_id")
    try:
        tid = int(raw)
    except (TypeError, ValueError):
        return None
    return tid or None


def team_name_key(row: Dict[str, Any]) -> str:
    return (row.get("team_name") or "").strip().lower()


def points_for(row: Dict[str, Any]) -> float:
    raw = row.get("points_for", row.get("pf", 0)) or 0
    try:
        return float(raw)
    except (TypeError, ValueError):
        return 0.0


def point_differential(row: Dict[str, Any]) -> float:
    raw = row.get("point_differential")
    if raw is not None:
        try:
            return float(raw)
        except (TypeError, ValueError):
            pass
    pa = row.get("points_against", 0) or 0
    try:
        return points_for(row) - float(pa)
    except (TypeError, ValueError):
        return points_for(row)


def composite_score(
    team: Dict[str, Any],
    *,
    max_pf: float,
    max_abs_diff: float,
    weights: Tuple[float, float, float],
) -> float:
    w_pct, w_pf, w_diff = weights
    wins = int(team.get("wins", 0) or 0)
    losses = int(team.get("losses", 0) or 0)
    ties = int(team.get("ties", 0) or 0)
    gp = wins + losses + ties
    wpct = (wins / gp) if gp else 0.0
    pf_norm = points_for(team) / max_pf if max_pf else 0.0
    if max_abs_diff:
        diff_norm = (point_differential(team) / max_abs_diff + 1) / 2
    else:
        diff_norm = 0.5
    return w_pct * wpct + w_pf * pf_norm + w_diff * diff_norm


def _norm_params(teams: Sequence[Dict[str, Any]]) -> Tuple[float, float]:
    if not teams:
        return 1.0, 1.0
    max_pf = max((points_for(t) for t in teams), default=0.0) or 1.0
    max_abs_diff = max(
        (abs(point_differential(t)) for t in teams),
        default=0.0,
    )
    return max_pf, max(1.0, max_abs_diff)


def score_teams(
    teams: Sequence[Dict[str, Any]],
    weights: Tuple[float, float, float],
) -> List[Dict[str, Any]]:
    """Attach a ``score`` to each team using ``weights``. Does not sort."""
    max_pf, max_abs_diff = _norm_params(teams)
    scored = []
    for t in teams:
        scored.append({
            **t,
            "score": composite_score(
                t, max_pf=max_pf, max_abs_diff=max_abs_diff, weights=weights
            ),
        })
    return scored


def rank_order(scored: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Sort by composite desc, then PF desc, then name. Assign 1-based ``rank``."""
    ordered = sorted(
        scored,
        key=lambda t: (
            -float(t.get("score") or 0),
            -points_for(t),
            team_name_key(t),
        ),
    )
    out = []
    for i, t in enumerate(ordered, 1):
        row = dict(t)
        row["rank"] = i
        out.append(row)
    return out


def lookup_prior_rank(
    team: Dict[str, Any],
    prior_rankings: Optional[Sequence[Dict[str, Any]]],
) -> Optional[int]:
    """Match ``team_id`` first, then ``team_name``."""
    if not prior_rankings:
        return None
    tid = team_id_or_none(team)
    name = team_name_key(team)
    by_id: Dict[int, int] = {}
    by_name: Dict[str, int] = {}
    for row in prior_rankings:
        rank = row.get("rank")
        try:
            rank_i = int(rank)
        except (TypeError, ValueError):
            continue
        pid = team_id_or_none(row)
        if pid:
            by_id[pid] = rank_i
        pname = team_name_key(row)
        if pname:
            by_name[pname] = rank_i
    if tid and tid in by_id:
        return by_id[tid]
    if name and name in by_name:
        return by_name[name]
    return None


def extract_week_results(matchups_payload: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """One result row per team from a ``week_matchups``-shaped payload."""
    if not matchups_payload:
        return []
    results: List[Dict[str, Any]] = []
    for m in matchups_payload.get("matchups") or []:
        home = m.get("home_team") or {}
        away = m.get("away_team") or {}
        try:
            hs = float(home.get("score") or 0)
        except (TypeError, ValueError):
            hs = 0.0
        try:
            aws = float(away.get("score") or 0)
        except (TypeError, ValueError):
            aws = 0.0
        if hs > aws:
            home_res, away_res = "W", "L"
        elif aws > hs:
            home_res, away_res = "L", "W"
        else:
            home_res, away_res = "T", "T"
        for team, score, opp, res in (
            (home, hs, aws, home_res),
            (away, aws, hs, away_res),
        ):
            if not team_id_or_none(team) and not team_name_key(team):
                continue
            results.append({
                "team_id": team.get("team_id"),
                "team_name": team.get("team_name"),
                "owner": team.get("owner"),
                "score": score,
                "points_against": opp,
                "result": res,
            })
    return results


def _result_identity(row: Dict[str, Any]) -> Tuple[str, Any]:
    tid = team_id_or_none(row)
    if tid:
        return ("id", tid)
    return ("name", team_name_key(row))


def aggregate_week_results(
    weeks_of_results: Iterable[Sequence[Dict[str, Any]]],
) -> List[Dict[str, Any]]:
    """Roll weekly result rows into standings-shaped records."""
    by_team: Dict[Tuple[str, Any], Dict[str, Any]] = {}
    for week_results in weeks_of_results:
        for r in week_results:
            key = _result_identity(r)
            if key not in by_team:
                by_team[key] = {
                    "team_id": r.get("team_id"),
                    "team_name": r.get("team_name"),
                    "owner": r.get("owner"),
                    "wins": 0,
                    "losses": 0,
                    "ties": 0,
                    "points_for": 0.0,
                    "points_against": 0.0,
                }
            t = by_team[key]
            result = r.get("result")
            if result == "W":
                t["wins"] += 1
            elif result == "L":
                t["losses"] += 1
            else:
                t["ties"] += 1
            t["points_for"] += float(r.get("score") or 0)
            t["points_against"] += float(r.get("points_against") or 0)
            if r.get("team_name") and not t.get("team_name"):
                t["team_name"] = r.get("team_name")
            if r.get("owner") and not t.get("owner"):
                t["owner"] = r.get("owner")
            if team_id_or_none(r) and not team_id_or_none(t):
                t["team_id"] = r.get("team_id")
    out = []
    for t in by_team.values():
        t["points_for"] = round(t["points_for"], 2)
        t["points_against"] = round(t["points_against"], 2)
        t["point_differential"] = round(t["points_for"] - t["points_against"], 2)
        out.append(t)
    return out


def _index_by_identity(rows: Sequence[Dict[str, Any]]) -> Dict[Tuple[str, Any], Dict[str, Any]]:
    indexed: Dict[Tuple[str, Any], Dict[str, Any]] = {}
    for row in rows:
        tid = team_id_or_none(row)
        if tid:
            indexed[("id", tid)] = row
        name = team_name_key(row)
        if name:
            indexed[("name", name)] = row
    return indexed


def _lookup_indexed(
    team: Dict[str, Any],
    indexed: Dict[Tuple[str, Any], Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    tid = team_id_or_none(team)
    if tid and ("id", tid) in indexed:
        return indexed[("id", tid)]
    name = team_name_key(team)
    if name and ("name", name) in indexed:
        return indexed[("name", name)]
    return None


def compute_power_rankings(
    week: int,
    standings: Sequence[Dict[str, Any]],
    *,
    current_matchups: Optional[Dict[str, Any]] = None,
    prior_rankings: Optional[Sequence[Dict[str, Any]]] = None,
    historical_matchups: Optional[Sequence[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Build the ``power_rankings`` payload consumed by context / canvas.

    Season composite uses Yahoo standings (W%, PF, differential). After
    week 3, blend 60% season / 40% last-3-weeks when prior-week matchups
    exist. Movement is vs ``prior_rankings`` (last week's list).
    """
    teams = list(standings or [])
    if not teams:
        return {"week": week, "rankings": []}

    weights = weights_for_week(week)
    season_scored = rank_order(score_teams(teams, weights))
    season_by_id = _index_by_identity(season_scored)

    l3_ranked: List[Dict[str, Any]] = []
    prior_bags = [
        extract_week_results(payload)
        for payload in (historical_matchups or [])
    ]
    prior_bags = [bag for bag in prior_bags if bag]
    use_l3 = int(week) >= L3_BLEND_WEEK and bool(prior_bags)
    if use_l3:
        week_bags: List[List[Dict[str, Any]]] = []
        if current_matchups:
            current_results = extract_week_results(current_matchups)
            if current_results:
                week_bags.append(current_results)
        week_bags.extend(prior_bags)
        l3_standings = aggregate_week_results(week_bags)
        if l3_standings:
            l3_ranked = rank_order(score_teams(l3_standings, weights))

    l3_by_id = _index_by_identity(l3_ranked) if l3_ranked else {}

    blended: List[Dict[str, Any]] = []
    for row in season_scored:
        season_score = float(row.get("score") or 0)
        final = season_score
        if l3_ranked:
            l3_row = _lookup_indexed(row, l3_by_id)
            if l3_row is not None:
                final = SEASON_BLEND * season_score + L3_BLEND * float(
                    l3_row.get("score") or 0
                )
        blended.append({**row, "score": final})

    final_ranked = rank_order(blended)

    rankings = []
    for t in final_ranked:
        previous_rank = lookup_prior_rank(t, prior_rankings)
        season_row = _lookup_indexed(t, season_by_id)
        l3_row = _lookup_indexed(t, l3_by_id) if l3_ranked else None
        season_rank = season_row.get("rank") if season_row else t["rank"]
        l3_rank = l3_row.get("rank") if l3_row else None
        rankings.append({
            "rank": t["rank"],
            "team_id": t.get("team_id"),
            "team_name": t.get("team_name"),
            "owner": t.get("owner"),
            "wins": t.get("wins", 0),
            "losses": t.get("losses", 0),
            "ties": t.get("ties", 0),
            "pf": round(points_for(t), 2),
            "movement": format_movement(t["rank"], previous_rank),
            "previous_rank": previous_rank,
            "heat": heat_from_ranks(season_rank, l3_rank),
        })
    return {"week": week, "rankings": rankings}


# ---------------------------------------------------------------------------
# History / weekdata loaders (filesystem, still no Yahoo)
# ---------------------------------------------------------------------------


def _as_int(value: Any) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError, TypeError):
        return None


def week_data_from_history_entry(entry: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    data = (entry.get("context") or {}).get("data")
    return data if isinstance(data, dict) else None


def week_data_from_history(
    history: Sequence[Dict[str, Any]], week: int
) -> Optional[Dict[str, Any]]:
    target = _as_int(week)
    if target is None:
        return None
    for entry in history:
        if _as_int(entry.get("week")) == target:
            data = week_data_from_history_entry(entry)
            if data:
                return data
    return None


def weekdata_path(output_dir: Path, week: int) -> Path:
    return Path(output_dir) / f"week-{week}-weekdata.json"


def load_weekdata_file(output_dir: Optional[Path], week: int) -> Optional[Dict[str, Any]]:
    if output_dir is None:
        return None
    path = weekdata_path(output_dir, week)
    if not path.exists():
        return None
    data = _load_json(path)
    return data if isinstance(data, dict) else None


def rankings_from_week_data(week_data: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not week_data:
        return []
    rankings = (week_data.get("power_rankings") or {}).get("rankings") or []
    return list(rankings) if isinstance(rankings, list) else []


def prior_rankings_reliable(rankings: Optional[Sequence[Dict[str, Any]]]) -> bool:
    """
    True when stored prior-week ranks reflect real games (W/L or PF).

    Week 1 recaps often saved 0-0 / PF 0 from a stale Yahoo standings parse;
    movement vs that list is noise.
    """
    if not rankings:
        return False
    for row in rankings:
        wins = int(row.get("wins", 0) or 0)
        losses = int(row.get("losses", 0) or 0)
        ties = int(row.get("ties", 0) or 0)
        if wins + losses + ties > 0:
            return True
        if points_for(row) > 0:
            return True
    return False


def derive_cumulative_standings(
    through_week: int,
    *,
    history: Optional[Sequence[Dict[str, Any]]] = None,
    output_dir: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """Build W/L and PF through ``through_week`` from stored matchup payloads."""
    target = _as_int(through_week)
    if target is None or target < 1:
        return []
    hist = load_history_list(history)
    week_bags: List[List[Dict[str, Any]]] = []
    for w in range(1, target + 1):
        data = week_data_from_history(hist, w)
        if data is None and output_dir is not None:
            data = load_weekdata_file(output_dir, w)
        if data is None and output_dir is None:
            for directory in default_output_dirs():
                data = load_weekdata_file(directory, w)
                if data:
                    break
        if not data:
            continue
        matchups = data.get("matchups") or {}
        if not isinstance(matchups, dict):
            continue
        results = extract_week_results(matchups)
        if results:
            week_bags.append(results)
    return aggregate_week_results(week_bags)


def reconcile_prior_rankings(
    week: int,
    prior_rankings: List[Dict[str, Any]],
    *,
    history: Optional[Sequence[Dict[str, Any]]] = None,
    output_dir: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """
    Use stored prior-week ranks when trustworthy; otherwise recompute from matchups.
    """
    if prior_rankings_reliable(prior_rankings):
        return prior_rankings
    derived = derive_cumulative_standings(
        week - 1, history=history, output_dir=output_dir
    )
    if not derived:
        return []
    payload = compute_power_rankings(week - 1, derived, prior_rankings=None)
    return list(payload.get("rankings") or [])


def default_history_candidates(explicit: Optional[Path] = None) -> List[Path]:
    out: List[Path] = []
    if explicit is not None:
        out.append(Path(explicit))
    out.append(Path.cwd() / "recap_history.json")
    out.append(APP_ROOT / "recap_history.json")
    # Deduplicate while preserving order.
    seen = set()
    unique: List[Path] = []
    for p in out:
        resolved = p.resolve() if p.exists() else p
        key = str(resolved)
        if key not in seen:
            seen.add(key)
            unique.append(p)
    return unique


def default_output_dirs(explicit: Optional[Path] = None) -> List[Path]:
    out: List[Path] = []
    if explicit is not None:
        out.append(Path(explicit))
    out.append(Path.cwd() / "output")
    out.append(APP_ROOT / "output")
    seen = set()
    unique: List[Path] = []
    for p in out:
        key = str(p.resolve()) if p.exists() else str(p)
        if key not in seen:
            seen.add(key)
            unique.append(p)
    return unique


def load_history_list(
    history: Optional[Sequence[Dict[str, Any]]] = None,
    history_path: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    if history is not None:
        return list(history)
    for path in default_history_candidates(history_path):
        if path.exists():
            data = _load_json(path)
            if isinstance(data, list):
                return data
    return []


def resolve_week_data(
    week: int,
    *,
    history: Optional[Sequence[Dict[str, Any]]] = None,
    output_dir: Optional[Path] = None,
) -> Optional[Dict[str, Any]]:
    """Prefer recap_history ``context.data``, then ``output/week-N-weekdata.json``."""
    hist = load_history_list(history)
    data = week_data_from_history(hist, week)
    if data:
        return data
    for directory in default_output_dirs(output_dir):
        data = load_weekdata_file(directory, week)
        if data:
            return data
    return None


def load_ranking_inputs(
    week: int,
    *,
    history: Optional[Sequence[Dict[str, Any]]] = None,
    output_dir: Optional[Path] = None,
    history_path: Optional[Path] = None,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Prior-week rankings + prior-week matchup payloads for L3.

    History is preferred over weekdata files. Prior matchups are weeks
    ``week-2`` and ``week-1`` when present (current week is passed separately).
    """
    hist = load_history_list(history, history_path=history_path)
    prior_data = resolve_week_data(week - 1, history=hist, output_dir=output_dir)
    prior_rankings = reconcile_prior_rankings(
        week,
        rankings_from_week_data(prior_data),
        history=hist,
        output_dir=output_dir,
    )

    historical_matchups: List[Dict[str, Any]] = []
    for prior_week in range(max(1, week - 2), week):
        data = week_data_from_history(hist, prior_week)
        if data is None and output_dir is not None:
            data = load_weekdata_file(output_dir, prior_week)
        elif data is None:
            data = resolve_week_data(prior_week, history=hist, output_dir=output_dir)
        if not data:
            continue
        matchups = data.get("matchups") or {}
        if not isinstance(matchups, dict):
            continue
        games = matchups.get("matchups") or []
        if games:
            payload = dict(matchups)
            payload.setdefault("week", prior_week)
            historical_matchups.append(payload)
    return prior_rankings, historical_matchups
