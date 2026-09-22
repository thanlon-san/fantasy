#!/usr/bin/env python3
"""
Yahoo Fantasy Football data fetcher.

Replaces the ESPN espn_api + local FastAPI pattern with in-process Yahoo
Fantasy API calls. Produces the exact dict shapes that ``context_builder``
and ``recap_generator`` consume, so no HTTP self-calls are required.

OAuth token loading order (whichever is present wins):
  1. ``config/oauth2.json`` in the football-recap app dir
  2. ``../baseball-engine/config/oauth2.json`` (share the baseball token —
     one Yahoo OAuth token covers all fantasy games for a user)
  3. ``$YAHOO_OAUTH_JSON`` env var (same JSON body, used in CI)
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from shared.logger import get_logger
from shared.yahoo import YahooFantasyClient, YahooOAuth2

from src.constants import resolve_owner
from src.power_rankings import compute_power_rankings, load_ranking_inputs

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# OAuth loading
# ---------------------------------------------------------------------------

APP_ROOT = Path(__file__).resolve().parent.parent
WORKSPACE_ROOT = APP_ROOT.parent.parent

DEFAULT_TOKEN_LOCATIONS = (
    APP_ROOT / "config" / "oauth2.json",
    WORKSPACE_ROOT / "apps" / "baseball-engine" / "config" / "oauth2.json",
)


def load_yahoo_oauth(explicit_path: Optional[Path] = None) -> YahooOAuth2:
    """
    Load a ``YahooOAuth2`` client, refreshing its access token as a side effect.

    Search order matches the module docstring. Raises ``RuntimeError`` with a
    clear message if no token source is available.
    """
    env_blob = os.environ.get("YAHOO_OAUTH_JSON")

    if explicit_path is not None:
        candidates: List[Path] = [Path(explicit_path)]
    else:
        candidates = [p for p in DEFAULT_TOKEN_LOCATIONS]

    chosen_path: Optional[Path] = None
    for candidate in candidates:
        if candidate.exists():
            chosen_path = candidate
            break

    if chosen_path is None and env_blob:
        # Materialize env blob into a temp file for save-back on refresh.
        chosen_path = APP_ROOT / "config" / "oauth2.json"
        chosen_path.parent.mkdir(parents=True, exist_ok=True)
        chosen_path.write_text(env_blob)
        logger.info("Materialized YAHOO_OAUTH_JSON env var to %s", chosen_path)

    if chosen_path is None:
        raise RuntimeError(
            "No Yahoo OAuth token found. Either place oauth2.json at "
            f"{DEFAULT_TOKEN_LOCATIONS[0]} (or the baseball-engine equivalent) "
            "or set the YAHOO_OAUTH_JSON environment variable."
        )

    oauth = YahooOAuth2.load_from_file(str(chosen_path))
    if not oauth.refresh_access_token():
        raise RuntimeError(
            f"Yahoo OAuth token refresh failed. Re-run the OAuth flow "
            f"(apps/baseball-engine/scripts/setup_yahoo.py) and update {chosen_path}."
        )
    oauth.save_to_file(str(chosen_path))
    return oauth


# ---------------------------------------------------------------------------
# Small helpers for parsing Yahoo's array-of-property-dicts responses
# ---------------------------------------------------------------------------


def _flatten_props(props: Any) -> Dict[str, Any]:
    """
    Yahoo often returns a "list of property dicts" for a single entity, e.g.
    ``[{"team_key": "..."}, {"name": "..."}]``. Flatten to one dict.
    """
    out: Dict[str, Any] = {}
    if not isinstance(props, list):
        return out
    for entry in props:
        if isinstance(entry, dict):
            for k, v in entry.items():
                out[k] = v
    return out


def _split_team_payload(team_payload: Any) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Yahoo team entries are a list: property dicts, then one or more stat dicts.

    Recent API responses split ``team_points`` and ``team_standings`` across
    separate dict blocks (index 1 and 2). Merge all stat dicts after the props.
    """
    props: Dict[str, Any] = {}
    stats_wrapper: Dict[str, Any] = {}
    if not isinstance(team_payload, list):
        return props, stats_wrapper
    if team_payload and isinstance(team_payload[0], list):
        props = _flatten_props(team_payload[0])
    for block in team_payload[1:]:
        if isinstance(block, dict):
            stats_wrapper.update(block)
    return props, stats_wrapper


def _numbered_children(collection: Any, child_key: str) -> List[Any]:
    """
    Yahoo collection responses use numbered keys plus a ``count`` field:
    ``{"count": 2, "0": {"team": [...]}, "1": {"team": [...]}}``.
    Return the raw ``child_key`` payload for each numbered entry.
    """
    if not isinstance(collection, dict):
        return []
    out = []
    for k, v in collection.items():
        if k == "count" or not isinstance(v, dict):
            continue
        if child_key in v:
            out.append(v[child_key])
    return out


# ---------------------------------------------------------------------------
# Main fetcher
# ---------------------------------------------------------------------------


class YahooLeagueFetcher:
    """
    In-process Yahoo Fantasy fetcher tailored to the football-recap pipeline.

    Usage::

        fetcher = YahooLeagueFetcher.from_config(config)
        week_data = fetcher.fetch_all_for_week(week=5)
    """

    def __init__(
        self,
        oauth: YahooOAuth2,
        league_id: int,
        year: int,
        sport: str = "nfl",
    ):
        self.oauth = oauth
        self.client = YahooFantasyClient(oauth)
        self.league_id = int(league_id)
        self.year = int(year)
        self.sport = sport
        self._league_key: Optional[str] = None
        self._league_meta: Optional[Dict[str, Any]] = None
        self._teams_cache: Optional[List[Dict[str, Any]]] = None
        self._fantasy_api_forbidden: bool = False
        # Yahoo returns roster slots that map to positions
        self._flex_slots = {"W/R/T", "W/T", "W/R", "Q/W/R/T", "FLEX"}

    # ---- config wiring -----------------------------------------------------

    @classmethod
    def from_config(
        cls,
        config: Dict[str, Any],
        oauth_path: Optional[Path] = None,
    ) -> "YahooLeagueFetcher":
        league_id = config.get("league_id")
        year = config.get("year")
        sport = config.get("sport", "nfl")
        if not league_id or not year:
            raise ValueError(
                "config.json is missing required 'league_id' or 'year' fields."
            )
        oauth = load_yahoo_oauth(oauth_path)
        return cls(oauth=oauth, league_id=league_id, year=year, sport=sport)

    # ---- league key resolution --------------------------------------------

    def _resolve_league_key(self) -> str:
        """Resolve the fully-qualified Yahoo league key (e.g. ``461.l.1324751``)."""
        if self._league_key:
            return self._league_key

        # Try the requested year first, then walk back a year if Yahoo hasn't
        # published the new season's game key yet (common in preseason).
        for candidate_year in (self.year, self.year - 1):
            game_key = self._lookup_game_key(candidate_year)
            if game_key:
                key = f"{game_key}.l.{self.league_id}"
                # Confirm the league is actually accessible before caching.
                if self._league_settings_ok(key):
                    self._league_key = key
                    if candidate_year != self.year:
                        logger.warning(
                            "Using %s game key for year %s (year %s not yet available).",
                            game_key, candidate_year, self.year,
                        )
                    return key

        if self._fantasy_api_forbidden:
            raise RuntimeError(
                "Yahoo Fantasy API returned 403 (application not authorized). "
                "OAuth refresh succeeded, but this Yahoo developer app still "
                "cannot call Fantasy endpoints. After Yahoo confirms API "
                "access, re-run apps/baseball-engine/scripts/setup_yahoo.py "
                "to re-authorize, update oauth2.json / YAHOO_OAUTH_JSON, "
                "then retry."
            )

        raise RuntimeError(
            f"Could not resolve Yahoo league key for league_id={self.league_id}, "
            f"year={self.year}, sport={self.sport}. Check the Yahoo login has "
            "access to this league."
        )

    def _lookup_game_key(self, year: int) -> Optional[str]:
        url = (
            f"{YahooFantasyClient.BASE_URL}"
            f"/users;use_login=1/games?format=json"
        )
        resp = self.client.session.get(url)
        if resp.status_code == 403:
            self._fantasy_api_forbidden = True
            logger.error(
                "Yahoo Fantasy API 403 on %s — application not authorized.",
                url,
            )
            return None
        if resp.status_code != 200:
            return None
        try:
            games = (
                resp.json()
                .get("fantasy_content", {})
                .get("users", {})
                .get("0", {})
                .get("user", [{}, {}])[1]
                .get("games", {})
            )
        except Exception:
            return None
        for key, value in games.items():
            if key == "count" or not isinstance(value, dict):
                continue
            game = value.get("game", [])
            if isinstance(game, list) and game:
                info = game[0] if isinstance(game[0], dict) else {}
                if (
                    info.get("code") == self.sport
                    and str(info.get("season")) == str(year)
                ):
                    return info.get("game_key")
        return None

    def _league_settings_ok(self, league_key: str) -> bool:
        url = f"{YahooFantasyClient.BASE_URL}/league/{league_key}/settings?format=json"
        resp = self.client.session.get(url)
        if resp.status_code == 403:
            self._fantasy_api_forbidden = True
        return resp.status_code == 200

    # ---- league / teams / standings ---------------------------------------

    def league_info(self) -> Dict[str, Any]:
        if self._league_meta is not None:
            return self._league_meta
        key = self._resolve_league_key()
        url = f"{YahooFantasyClient.BASE_URL}/league/{key}?format=json"
        resp = self.client.session.get(url)
        resp.raise_for_status()
        raw = (
            resp.json()
            .get("fantasy_content", {})
            .get("league", [])
        )
        league_props: Dict[str, Any] = {}
        if isinstance(raw, list) and raw and isinstance(raw[0], dict):
            league_props = raw[0]
        elif isinstance(raw, dict):
            league_props = raw

        info = {
            "league_id": self.league_id,
            "year": self.year,
            "season_year": self.year,
            "league_name": league_props.get("name", "Unknown League"),
            "current_week": int(league_props.get("current_week", 1)),
            "total_teams": int(league_props.get("num_teams", 0)),
            "start_week": int(league_props.get("start_week", 1)),
            "end_week": int(league_props.get("end_week", 17)),
            "league_key": key,
        }
        self._league_meta = info
        return info

    def _load_teams(self) -> List[Dict[str, Any]]:
        if self._teams_cache is not None:
            return self._teams_cache
        key = self._resolve_league_key()
        url = f"{YahooFantasyClient.BASE_URL}/league/{key}/standings?format=json"
        resp = self.client.session.get(url)
        resp.raise_for_status()
        payload = resp.json().get("fantasy_content", {}).get("league", [])
        teams_collection: Dict[str, Any] = {}
        # Yahoo returns [league_dict, {"standings": [{"teams": {...}}]}]
        if isinstance(payload, list) and len(payload) >= 2:
            standings_wrapper = payload[1]
            if isinstance(standings_wrapper, dict):
                standings_list = standings_wrapper.get("standings", [])
                if isinstance(standings_list, list) and standings_list:
                    first = standings_list[0]
                    if isinstance(first, dict):
                        teams_collection = first.get("teams", {}) or {}

        teams: List[Dict[str, Any]] = []
        for team_payload in _numbered_children(teams_collection, "team"):
            teams.append(self._parse_team_entry(team_payload))
        # Sort by standings rank ascending; teams with no rank sink to the end.
        teams.sort(key=lambda t: (t.get("standing") or 999, -t.get("points_for", 0)))
        self._teams_cache = teams
        return teams

    def _parse_team_entry(self, team_payload: Any) -> Dict[str, Any]:
        """
        Yahoo team entries under ``standings`` look roughly like::

            [ [ {team_key}, {team_id}, {name}, {managers}, ... ],
              {"team_points": {...}},
              {"team_standings": {...}} ]

        Older payloads combined ``team_points`` and ``team_standings`` in one dict.
        """
        props, stats_wrapper = _split_team_payload(team_payload)

        # Manager nickname
        manager_nickname = ""
        managers = props.get("managers")
        if isinstance(managers, list) and managers:
            mgr_wrapper = managers[0]
            if isinstance(mgr_wrapper, dict):
                mgr = mgr_wrapper.get("manager", {})
                if isinstance(mgr, dict):
                    manager_nickname = mgr.get("nickname", "") or ""

        team_name = props.get("name", "Unknown")
        owner = resolve_owner(team_name, manager_nickname)

        standings = stats_wrapper.get("team_standings", {}) or {}
        outcome = standings.get("outcome_totals", {}) or {}
        streak_obj = standings.get("streak", {}) or {}
        team_points = stats_wrapper.get("team_points", {}) or {}
        # Yahoo H2H standings puts points_against under team_points_against or points_against
        pa_value = (
            standings.get("points_against")
            or stats_wrapper.get("points_against", {}).get("total")
            if isinstance(stats_wrapper.get("points_against"), dict)
            else standings.get("points_against", 0)
        )

        try:
            points_for = float(team_points.get("total", 0))
        except (TypeError, ValueError):
            points_for = 0.0
        try:
            points_against_num = float(pa_value or 0)
        except (TypeError, ValueError):
            points_against_num = 0.0

        return {
            "team_id": int(props.get("team_id", 0) or 0),
            "team_key": props.get("team_key", ""),
            "team_name": team_name,
            "owner": owner,
            "manager_nickname": manager_nickname,
            "wins": int(outcome.get("wins", 0) or 0),
            "losses": int(outcome.get("losses", 0) or 0),
            "ties": int(outcome.get("ties", 0) or 0),
            "points_for": round(points_for, 2),
            "points_against": round(points_against_num, 2),
            "streak_type": (streak_obj.get("type") or "NONE").upper()[:1] or "N",
            "streak_length": int(streak_obj.get("value", 0) or 0),
            "standing": int(standings.get("rank", 0) or 0),
            # Yahoo doesn't expose these in this feed — leave as None so
            # downstream code falls back to safe defaults via .get(..., 0).
            "acquisitions": None,
            "drops": None,
            "trades": None,
            "faab_spent": None,
        }

    def teams(self) -> Dict[str, Any]:
        teams = self._load_teams()
        return {"total_teams": len(teams), "teams": teams}

    def draft_results(self) -> Dict[str, Any]:
        """
        Fetch the league's draft results.

        **Untested against live Yahoo** as of this writing (API access is
        currently pending re-approval — see docs/AUTOMATION_SPEC.md). Shape
        mirrors the endpoint pattern already proven in
        ``apps/baseball-engine/scripts/get_draft_results.py``:
        ``league/{key}/draftresults`` returns numbered ``draft_result``
        entries with ``pick``, ``round``, ``team_key``, ``player_key``.

        Returns ``{"picks": [...]}`` where each pick is
        ``{round, pick, team_key, team_name, owner, player_key, player_name,
        position}``. Player name/position require a follow-up lookup since
        the draft results endpoint only returns ``player_key`` — resolved
        best-effort via the league's player endpoint in batches.
        """
        key = self._resolve_league_key()
        url = f"{YahooFantasyClient.BASE_URL}/league/{key}/draftresults?format=json"
        resp = self.client.session.get(url)
        resp.raise_for_status()
        payload = resp.json().get("fantasy_content", {}).get("league", [])

        draft_collection: Dict[str, Any] = {}
        if isinstance(payload, list) and len(payload) >= 2:
            wrapper = payload[1]
            if isinstance(wrapper, dict):
                draft_collection = wrapper.get("draft_results", {}) or {}

        teams_by_key = {t["team_key"]: t for t in self._load_teams()}

        picks: List[Dict[str, Any]] = []
        player_keys: List[str] = []
        for raw in _numbered_children(draft_collection, "draft_result"):
            props = _flatten_props(raw) if isinstance(raw, list) else (raw or {})
            team_key = props.get("team_key")
            team = teams_by_key.get(team_key, {})
            player_key = props.get("player_key")
            if player_key:
                player_keys.append(player_key)
            picks.append({
                "round": props.get("round"),
                "pick": props.get("pick"),
                "team_key": team_key,
                "team_name": team.get("team_name", ""),
                "owner": team.get("owner", ""),
                "player_key": player_key,
                "player_name": None,  # filled below, best-effort
                "position": None,
            })

        if player_keys:
            self._enrich_picks_with_player_info(picks, player_keys)

        picks.sort(key=lambda p: (p.get("round") or 999, p.get("pick") or 999))
        return {"picks": picks, "total_picks": len(picks)}

    def _enrich_picks_with_player_info(
        self, picks: List[Dict[str, Any]], player_keys: List[str]
    ) -> None:
        """Best-effort player name/position lookup for draft picks, batched."""
        batch_size = 25
        info_by_key: Dict[str, Dict[str, Any]] = {}
        for i in range(0, len(player_keys), batch_size):
            batch = player_keys[i:i + batch_size]
            keys_str = ",".join(batch)
            url = f"{YahooFantasyClient.BASE_URL}/players;player_keys={keys_str}?format=json"
            try:
                resp = self.client.session.get(url)
                resp.raise_for_status()
                players_collection = (
                    resp.json().get("fantasy_content", {}).get("players", {}) or {}
                )
            except Exception as exc:
                logger.warning("Draft pick player lookup failed for batch: %s", exc)
                continue
            for raw in _numbered_children(players_collection, "player"):
                props = _flatten_props(raw[0]) if isinstance(raw, list) and raw else {}
                pkey = props.get("player_key")
                if pkey:
                    info_by_key[pkey] = {
                        "name": (props.get("name") or {}).get("full", "Unknown Player"),
                        "position": props.get("display_position", ""),
                    }

        for pick in picks:
            info = info_by_key.get(pick.get("player_key"))
            if info:
                pick["player_name"] = info["name"]
                pick["position"] = info["position"]

    def standings(self) -> Dict[str, Any]:
        teams = self._load_teams()
        ranked = []
        for i, t in enumerate(teams, 1):
            gp = t["wins"] + t["losses"]
            pct = (t["wins"] / gp) if gp > 0 else 0.0
            ranked.append({
                "rank": t.get("standing") or i,
                "team_id": t["team_id"],
                "team_name": t["team_name"],
                "owner": t["owner"],
                "wins": t["wins"],
                "losses": t["losses"],
                "ties": t["ties"],
                "win_pct": round(pct, 3),
                "points_for": t["points_for"],
                "points_against": t["points_against"],
                "point_differential": round(t["points_for"] - t["points_against"], 2),
                "streak": f"{t['streak_type']}{t['streak_length']}",
            })
        leaders = {}
        if ranked:
            leaders = {
                "most_points": max(ranked, key=lambda x: x["points_for"]),
                "fewest_points_against": min(ranked, key=lambda x: x["points_against"]),
                "best_differential": max(ranked, key=lambda x: x["point_differential"]),
            }
        return {"standings": ranked, "leaders": leaders}

    # ---- matchups ----------------------------------------------------------

    def week_matchups(self, week: int) -> Dict[str, Any]:
        key = self._resolve_league_key()
        url = (
            f"{YahooFantasyClient.BASE_URL}/league/{key}/scoreboard;week={week}"
            "?format=json"
        )
        resp = self.client.session.get(url)
        resp.raise_for_status()
        payload = resp.json().get("fantasy_content", {}).get("league", [])
        matchups_collection: Dict[str, Any] = {}
        if isinstance(payload, list) and len(payload) >= 2:
            sb_wrapper = payload[1]
            if isinstance(sb_wrapper, dict):
                sb = sb_wrapper.get("scoreboard", {}) or {}
                # ``scoreboard`` is sometimes a dict, sometimes a list.
                if isinstance(sb, dict):
                    matchups_collection = sb.get("0", {}).get("matchups", {}) or {}
                elif isinstance(sb, list):
                    for item in sb:
                        if isinstance(item, dict) and "matchups" in item:
                            matchups_collection = item["matchups"] or {}
                            break

        teams_by_key = {t["team_key"]: t for t in self._load_teams()}
        matchups: List[Dict[str, Any]] = []
        for idx, raw_matchup in enumerate(
            _numbered_children(matchups_collection, "matchup"), 1
        ):
            parsed = self._parse_matchup(raw_matchup, week, idx, teams_by_key)
            if parsed:
                matchups.append(parsed)

        return {"week": week, "total_matchups": len(matchups), "matchups": matchups}

    def _parse_matchup(
        self,
        raw: Any,
        week: int,
        idx: int,
        teams_by_key: Dict[str, Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        # Yahoo matchup shape: dict with "teams" collection (2 teams) plus flat
        # metadata like "week", "is_playoffs", "winner_team_key".
        if not isinstance(raw, dict):
            return None
        winner_key = raw.get("winner_team_key") or ""
        teams_coll = raw.get("0", {}).get("teams") if isinstance(raw.get("0"), dict) else None
        if not teams_coll:
            teams_coll = raw.get("teams", {})

        team_entries = _numbered_children(teams_coll or {}, "team")
        if len(team_entries) < 2:
            return None

        parsed_teams: List[Dict[str, Any]] = []
        for entry in team_entries[:2]:
            parsed_teams.append(
                self._parse_matchup_team(entry, week, teams_by_key)
            )
        home = parsed_teams[0]
        away = parsed_teams[1]

        winner_name = ""
        if winner_key:
            for t in parsed_teams:
                if t.get("team_key") == winner_key:
                    winner_name = t["team_name"]
                    break
        if not winner_name:
            # Yahoo may not set winner_team_key for in-progress or tied games.
            winner_name = (
                home["team_name"] if home["score"] >= away["score"] else away["team_name"]
            )

        return {
            "matchup_id": idx,
            "home_team": home,
            "away_team": away,
            "winner": winner_name,
            "margin": round(abs(home["score"] - away["score"]), 2),
            "is_playoffs": str(raw.get("is_playoffs", "0")) == "1",
        }

    def _parse_matchup_team(
        self,
        raw: Any,
        week: int,
        teams_by_key: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Any]:
        team_props, stats_wrapper = _split_team_payload(raw)

        team_key = team_props.get("team_key", "")
        team_name = team_props.get("name", "Unknown")
        team_meta = teams_by_key.get(team_key, {})
        owner = team_meta.get("owner") or resolve_owner(team_name)

        team_points = stats_wrapper.get("team_points", {}) or {}
        try:
            score = float(team_points.get("total", 0))
        except (TypeError, ValueError):
            score = 0.0

        # Roster for this week (starters + bench)
        starters, bench = self._fetch_week_roster(team_key, week)

        # Derived analytics
        aggregates = _position_aggregates(starters)
        optimal = _optimal_lineup(starters + bench)
        management_gap = round(max(0.0, optimal["optimal_score"] - score), 2)

        record = ""
        if team_meta:
            record = (
                f"{team_meta.get('wins', 0)}-{team_meta.get('losses', 0)}-{team_meta.get('ties', 0)}"
            )

        return {
            "team_id": team_meta.get("team_id") or int(team_props.get("team_id", 0) or 0),
            "team_key": team_key,
            "team_name": team_name,
            "owner": owner,
            "score": round(score, 2),
            "record": record,
            "starters": starters,
            "bench": bench,
            "position_aggregates": aggregates,
            "optimal_lineup": optimal,
            "management_gap": management_gap,
        }

    def _fetch_week_roster(
        self, team_key: str, week: int
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Fetch roster for a given team/week and split into starters + bench."""
        if not team_key:
            return [], []
        url = (
            f"{YahooFantasyClient.BASE_URL}/team/{team_key}/roster;week={week}"
            "/players/stats;type=week;week=" + str(week) + "?format=json"
        )
        resp = self.client.session.get(url)
        if resp.status_code != 200:
            logger.warning(
                "Failed to fetch roster for %s week %s (HTTP %s)",
                team_key, week, resp.status_code,
            )
            return [], []
        try:
            team_data = resp.json().get("fantasy_content", {}).get("team", [])
        except Exception:
            return [], []

        # team_data shape: [ [propdicts], {"roster": {"0": {"players": {...}}}} ]
        players_collection: Dict[str, Any] = {}
        if isinstance(team_data, list) and len(team_data) >= 2:
            wrapper = team_data[1]
            if isinstance(wrapper, dict):
                roster = wrapper.get("roster", {})
                if isinstance(roster, dict):
                    zero = roster.get("0", {})
                    if isinstance(zero, dict):
                        players_collection = zero.get("players", {}) or {}

        starters: List[Dict[str, Any]] = []
        bench: List[Dict[str, Any]] = []
        for raw_player in _numbered_children(players_collection, "player"):
            player = self._parse_player(raw_player)
            if not player:
                continue
            if player["slot"] in ("BN", "IR"):
                bench.append(player)
            else:
                starters.append(player)
        return starters, bench

    def _parse_player(self, raw: Any) -> Optional[Dict[str, Any]]:
        if not isinstance(raw, list):
            return None
        props: Dict[str, Any] = {}
        selected_position: Dict[str, Any] = {}
        player_points: Dict[str, Any] = {}
        # ``raw`` is an array of ~4-5 blocks: [propdicts, {selected_position:...},
        # {player_points:...}, ...]
        for block in raw:
            if isinstance(block, list):
                props.update(_flatten_props(block))
            elif isinstance(block, dict):
                if "selected_position" in block:
                    sp = block["selected_position"]
                    if isinstance(sp, list):
                        selected_position = _flatten_props(sp)
                    elif isinstance(sp, dict):
                        selected_position = sp
                if "player_points" in block:
                    player_points = block["player_points"] or {}

        name_field = props.get("name", {})
        name = ""
        if isinstance(name_field, dict):
            name = name_field.get("full", "") or ""
        if not name:
            return None

        position = props.get("display_position") or props.get("primary_position") or ""
        pro_team = props.get("editorial_team_abbr", "FA")
        slot = selected_position.get("position", "BN")

        try:
            actual = float(player_points.get("total", 0))
        except (TypeError, ValueError):
            actual = 0.0

        # Yahoo doesn't return projections on the same payload; leave 0.
        return {
            "name": name,
            "position": position,
            "slot": slot,
            "projected_points": 0.0,
            "actual_points": round(actual, 2),
            "pro_team": pro_team,
            # ESPN-only signal; -1 tells context_builder "unavailable, skip roasts".
            "percent_started": -1,
            # Detailed passing/rushing/receiving splits require per-player
            # calls; leave empty so _format_player_stats returns "".
            "stats": {},
        }

    # ---- derived / bundled -------------------------------------------------

    def week_stats(self, matchups_payload: Dict[str, Any]) -> Dict[str, Any]:
        """Compute headline weekly stats from an already-fetched matchups payload."""
        stats: Dict[str, Any] = {
            "highest_score": None,
            "lowest_score": None,
            "biggest_blowout": None,
            "closest_game": None,
            "most_bench_points": None,
        }
        biggest = -1.0
        closest = float("inf")
        all_scores: List[Tuple[str, float]] = []
        best_bench: Optional[Dict[str, Any]] = None

        for m in matchups_payload.get("matchups", []):
            home, away = m["home_team"], m["away_team"]
            diff = abs(home["score"] - away["score"])

            if diff > biggest:
                biggest = diff
                winner = home if home["score"] > away["score"] else away
                loser = away if home["score"] > away["score"] else home
                stats["biggest_blowout"] = {
                    "winner": winner["team_name"],
                    "loser": loser["team_name"],
                    "margin": round(diff, 2),
                }
            if diff < closest:
                closest = diff
                stats["closest_game"] = {
                    "team1": home["team_name"],
                    "team2": away["team_name"],
                    "margin": round(diff, 2),
                }

            all_scores.append((home["team_name"], home["score"]))
            all_scores.append((away["team_name"], away["score"]))

            for side in (home, away):
                bench_points = sum(p["actual_points"] for p in side["bench"])
                if best_bench is None or bench_points > best_bench["points"]:
                    best_bench = {
                        "team": side["team_name"],
                        "points": round(bench_points, 2),
                    }

        if all_scores:
            hi = max(all_scores, key=lambda x: x[1])
            lo = min(all_scores, key=lambda x: x[1])
            stats["highest_score"] = {"team": hi[0], "points": round(hi[1], 2)}
            stats["lowest_score"] = {"team": lo[0], "points": round(lo[1], 2)}
        stats["most_bench_points"] = best_bench
        return stats

    def power_rankings(
        self,
        week: int,
        standings_payload: Dict[str, Any],
        matchups_payload: Optional[Dict[str, Any]] = None,
        prior_rankings: Optional[List[Dict[str, Any]]] = None,
        historical_matchups: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Power rankings: season composite, last-3-weeks blend after week 3,
        movement vs last week's list, heat check for the recap writer.

        Shape mirrors what ``context_builder._add_power_rankings`` expects.
        Pure math lives in ``src.power_rankings`` so tests don't need Yahoo.
        """
        return compute_power_rankings(
            week,
            list(standings_payload.get("standings", [])),
            current_matchups=matchups_payload,
            prior_rankings=prior_rankings,
            historical_matchups=historical_matchups,
        )

    def fetch_all_for_week(
        self,
        week: int,
        *,
        history: Optional[List[Dict[str, Any]]] = None,
        output_dir: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """
        Return the exact ``week_data`` dict expected by ``ContextBuilder``.

        Keys: league, teams, standings, matchups, week_stats, power_rankings,
        next_week_matchups, superlatives, gif_of_the_week.

        Team names are live Yahoo ``team_name`` values. Recaps and League HQ
        should use these, not ``PRESEASON_MANAGERS_2026``. ``TEAM_OWNERS`` is
        only a display-name override via ``resolve_owner``.
        """
        # Local imports keep the top-level of this module free of engagement
        # feature deps — the fetcher stays usable if callers only want raw
        # Yahoo data.
        from src.gif_bank import pick_gif
        from src.superlatives import compute_superlatives

        league = self.league_info()
        teams = self.teams()
        standings = self.standings()
        matchups = self.week_matchups(week)
        stats = self.week_stats(matchups)
        prior_rankings, historical_matchups = load_ranking_inputs(
            week, history=history, output_dir=output_dir
        )
        rankings = self.power_rankings(
            week,
            standings,
            matchups_payload=matchups,
            prior_rankings=prior_rankings,
            historical_matchups=historical_matchups,
        )

        # Next week matchups (best-effort; may be empty in preseason/final week)
        next_week = week + 1
        next_matchups: Dict[str, Any] = {"matchups": []}
        try:
            next_matchups = self.week_matchups(next_week)
        except Exception as exc:
            logger.warning("Could not fetch next-week matchups: %s", exc)

        data = {
            "league": league,
            "teams": teams,
            "standings": standings,
            "matchups": matchups,
            "week_stats": stats,
            "power_rankings": rankings,
            "next_week_matchups": next_matchups,
        }
        # Engagement features (superlatives + GIF) are derived, not fetched.
        superlatives = compute_superlatives(data)
        data["superlatives"] = superlatives
        data["gif_of_the_week"] = pick_gif(data, week, superlatives=superlatives)
        return data


# ---------------------------------------------------------------------------
# Analytics helpers (pure functions)
# ---------------------------------------------------------------------------

_POSITION_KEYS = ("QB", "RB", "WR", "TE", "K", "DEF", "D/ST", "FLEX")


def _position_aggregates(starters: List[Dict[str, Any]]) -> Dict[str, float]:
    """Sum actual points per position among starters."""
    agg = {k: 0.0 for k in _POSITION_KEYS}
    for p in starters:
        pos = (p.get("position") or "").upper()
        # Yahoo uses "DEF" for team defense; keep both keys populated.
        if pos in agg:
            agg[pos] += p.get("actual_points", 0.0)
        if pos == "DEF":
            agg["D/ST"] += p.get("actual_points", 0.0)
    return {k: round(v, 2) for k, v in agg.items()}


def _optimal_lineup(all_players: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Compute the best legal 9-player Yahoo lineup given a full roster.

    Assumes a standard lineup: 1 QB, 2 RB, 2 WR, 1 TE, 1 W/R/T FLEX, 1 K, 1 DEF.
    """
    def pool(pos: str) -> List[Dict[str, Any]]:
        return sorted(
            [p for p in all_players if (p.get("position") or "").upper() == pos],
            key=lambda x: x.get("actual_points", 0.0),
            reverse=True,
        )

    qbs = pool("QB")
    rbs = pool("RB")
    wrs = pool("WR")
    tes = pool("TE")
    ks = pool("K")
    defs = pool("DEF") + pool("D/ST")

    chosen: List[Dict[str, Any]] = []
    total = 0.0

    def take(pool_list: List[Dict[str, Any]], n: int, label: str):
        nonlocal total
        for p in pool_list[:n]:
            total += p.get("actual_points", 0.0)
            chosen.append({
                "name": p["name"],
                "position": label,
                "points": p.get("actual_points", 0.0),
            })

    take(qbs, 1, "QB")
    take(rbs, 2, "RB")
    take(wrs, 2, "WR")
    take(tes, 1, "TE")

    # FLEX = best remaining RB/WR/TE
    flex_pool = rbs[2:] + wrs[2:] + tes[1:]
    flex_pool.sort(key=lambda x: x.get("actual_points", 0.0), reverse=True)
    take(flex_pool, 1, "FLEX")

    take(ks, 1, "K")
    take(defs, 1, "DEF")

    return {
        "optimal_score": round(total, 2),
        "optimal_players": chosen,
    }
