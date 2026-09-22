"""Yahoo Fantasy NFL client.

Fetches a week of league data from the Yahoo Fantasy v2 REST API and normalizes
it into the ``week_data`` dict the recap pipeline consumes.

Yahoo's JSON is awkward: collections arrive as dicts keyed by stringified
indices plus a ``count`` key, and objects arrive as lists of single-key dicts.
``flatten`` and ``iter_collection`` below absorb that so the rest of the module
can treat everything as plain dicts.

Credentials come from the ``YAHOO_OAUTH_JSON`` env var (cloud secret) or, when
that is unset, from a local ``oauth2.json``. Either way the blob is the shape
``yahoo_oauth_manual.YahooOAuth2`` writes.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, Iterator, List, Optional

import requests

from src.constants import (
    YAHOO_API_BASE,
    YAHOO_LEAGUE_KEY,
    YAHOO_OAUTH_ENV_VAR,
    YAHOO_OAUTH_FILE_CANDIDATES,
    YAHOO_TOKEN_URL,
)

REQUEST_TIMEOUT = 30


class YahooError(RuntimeError):
    """Base class for Yahoo failures the pipeline knows how to report."""

    #: Short machine-readable tag used in the meta sidecar and Slack draft.
    code = "yahoo_error"


class YahooCredentialsError(YahooError):
    """The credential blob is missing or malformed."""

    code = "missing_credentials"


class YahooAuthError(YahooError):
    """Token refresh failed -- the refresh token is dead or revoked."""

    code = "auth_failed"


class YahooForbiddenError(YahooError):
    """Yahoo returned 403.

    In practice this means the Yahoo developer app has not been granted Fantasy
    Sports API access, so it applies to every endpoint rather than one league.
    Refreshing credentials does not help.
    """

    code = "forbidden"


class YahooNotFoundError(YahooError):
    """The league does not exist yet, or is not visible to this account."""

    code = "not_found"


# ---------------------------------------------------------------------------
# Yahoo JSON shape helpers
# ---------------------------------------------------------------------------


def flatten(node: Any) -> Dict[str, Any]:
    """Collapse Yahoo's list-of-single-key-dicts into one flat dict.

    Yahoo represents an object as e.g.
    ``[{"team_key": "..."}, {"team_id": "3"}, [], {"name": "..."}]``.
    Nested lists are flattened recursively; non-dict scalars are skipped.
    """
    out: Dict[str, Any] = {}

    def walk(item: Any) -> None:
        if isinstance(item, dict):
            for key, value in item.items():
                # Numeric keys are collection indices, not real fields.
                if key.isdigit():
                    walk(value)
                else:
                    out.setdefault(key, value)
        elif isinstance(item, list):
            for sub in item:
                walk(sub)

    walk(node)
    return out


def iter_collection(node: Any) -> Iterator[Any]:
    """Yield members of a Yahoo collection.

    Collections look like ``{"0": {...}, "1": {...}, "count": 2}``. Plain lists
    are passed through so callers do not have to care which they got.
    """
    if isinstance(node, list):
        yield from node
        return
    if not isinstance(node, dict):
        return
    for key in sorted((k for k in node if k.isdigit()), key=int):
        yield node[key]


def _num(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _int(value: Any, default: int = 0) -> int:
    return int(_num(value, default))


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


def _parse_credential_blob(raw: str, source: str) -> Dict[str, str]:
    try:
        creds = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise YahooCredentialsError(
            f"Yahoo credentials from {source} are not valid JSON: {exc}"
        ) from exc

    missing = [
        key
        for key in ("consumer_key", "consumer_secret", "refresh_token")
        if not creds.get(key)
    ]
    if missing:
        raise YahooCredentialsError(
            f"Yahoo credentials from {source} are missing: {', '.join(missing)}"
        )
    return creds


def _refresh_token_works(creds: Dict[str, str]) -> bool:
    """True when Yahoo accepts the stored refresh_token (no token values logged)."""
    try:
        response = requests.post(
            YAHOO_TOKEN_URL,
            data={
                "client_id": creds["consumer_key"],
                "client_secret": creds["consumer_secret"],
                "refresh_token": creds["refresh_token"],
                "grant_type": "refresh_token",
                "redirect_uri": "oob",
            },
            timeout=REQUEST_TIMEOUT,
        )
        return response.status_code == 200
    except requests.RequestException:
        return False


def load_credentials() -> Dict[str, str]:
    """Load Yahoo OAuth credentials from the env var and/or local oauth2.json files.

    ``YAHOO_OAUTH_JSON`` wins when its refresh token is valid. If the cloud secret
    is stale (common after re-auth on disk only), we fall back to the first local
    oauth2.json whose refresh token Yahoo still accepts.
    """
    sources: list[tuple[str, str]] = []

    env_raw = os.environ.get(YAHOO_OAUTH_ENV_VAR, "").strip()
    if env_raw:
        sources.append((YAHOO_OAUTH_ENV_VAR, env_raw))

    for candidate in YAHOO_OAUTH_FILE_CANDIDATES:
        if not os.path.exists(candidate):
            continue
        with open(candidate, "r", encoding="utf-8") as handle:
            file_raw = handle.read().strip()
        if not file_raw:
            continue
        if env_raw and file_raw == env_raw:
            continue
        sources.append((candidate, file_raw))

    if not sources:
        raise YahooCredentialsError(
            f"No Yahoo credentials. Set the {YAHOO_OAUTH_ENV_VAR} secret or add "
            f"one of: {', '.join(YAHOO_OAUTH_FILE_CANDIDATES)}"
        )

    stale_env = False
    for source, raw in sources:
        creds = _parse_credential_blob(raw, source)
        if _refresh_token_works(creds):
            if source != YAHOO_OAUTH_ENV_VAR and env_raw:
                print(
                    f"Warning: {YAHOO_OAUTH_ENV_VAR} has a stale refresh token; "
                    f"using {source} instead. Re-copy apps/baseball-engine/"
                    "config/oauth2.json into the Cursor secret (full JSON, "
                    "including refresh_token), then start a new agent.",
                    file=sys.stderr,
                )
            return creds
        if source == YAHOO_OAUTH_ENV_VAR:
            stale_env = True

    if stale_env:
        raise YahooAuthError(
            f"{YAHOO_OAUTH_ENV_VAR} refresh token is invalid and no local "
            "oauth2.json accepted a refresh. Re-authorize Yahoo, then paste the "
            f"full oauth2.json into the {YAHOO_OAUTH_ENV_VAR} cloud secret."
        )
    raise YahooCredentialsError(
        "No Yahoo credential source could refresh its token."
    )


class YahooNFLClient:
    """Minimal authenticated reader for the Yahoo Fantasy NFL API."""

    def __init__(
        self,
        credentials: Optional[Dict[str, str]] = None,
        league_key: str = YAHOO_LEAGUE_KEY,
    ):
        self.credentials = credentials or load_credentials()
        self.league_key = league_key
        self.access_token: Optional[str] = self.credentials.get("access_token")
        self._session = requests.Session()
        self._refreshed = False

    # -- auth ---------------------------------------------------------------

    def refresh_access_token(self) -> str:
        """Trade the refresh token for a fresh access token."""
        response = requests.post(
            YAHOO_TOKEN_URL,
            data={
                "client_id": self.credentials["consumer_key"],
                "client_secret": self.credentials["consumer_secret"],
                "refresh_token": self.credentials["refresh_token"],
                "grant_type": "refresh_token",
                "redirect_uri": "oob",
            },
            timeout=REQUEST_TIMEOUT,
        )
        if response.status_code != 200:
            raise YahooAuthError(
                "Yahoo token refresh failed "
                f"({response.status_code}). Re-authorize Yahoo and update the "
                f"{YAHOO_OAUTH_ENV_VAR} secret."
            )
        token = response.json().get("access_token")
        if not token:
            raise YahooAuthError("Yahoo token refresh returned no access_token.")
        self.access_token = token
        self._refreshed = True
        return token

    # -- transport ----------------------------------------------------------

    def get(self, path: str) -> Dict[str, Any]:
        """GET a Fantasy v2 path, refreshing the token once on a 401."""
        if not self.access_token:
            self.refresh_access_token()

        for attempt in (1, 2):
            url = f"{YAHOO_API_BASE}/{path}"
            url += ("&" if "?" in url else "?") + "format=json"
            response = self._session.get(
                url,
                headers={"Authorization": f"Bearer {self.access_token}"},
                timeout=REQUEST_TIMEOUT,
            )

            if response.status_code == 401 and attempt == 1 and not self._refreshed:
                self.refresh_access_token()
                continue
            if response.status_code == 401:
                raise YahooAuthError(
                    "Yahoo rejected the access token even after a refresh."
                )
            if response.status_code == 403:
                raise YahooForbiddenError(
                    "Yahoo returned 403 'not authorized'. The Yahoo developer "
                    "app does not have Fantasy Sports API access approved, so "
                    "every endpoint is blocked -- refreshing the token will not "
                    "help. This needs to be granted in the Yahoo app settings."
                )
            if response.status_code == 404:
                raise YahooNotFoundError(
                    f"Yahoo returned 404 for {path}. The league is probably not "
                    "published for this season yet."
                )
            if response.status_code != 200:
                raise YahooError(
                    f"Yahoo returned {response.status_code} for {path}: "
                    f"{response.text[:200]}"
                )

            payload = response.json()
            return payload.get("fantasy_content", payload)

        raise YahooError(f"Unreachable: exhausted retries for {path}")

    # -- domain reads -------------------------------------------------------

    def fetch_league_meta(self) -> Dict[str, Any]:
        content = self.get(f"league/{self.league_key}")
        league = flatten(content.get("league"))
        return {
            "league_id": league.get("league_id"),
            "league_key": league.get("league_key", self.league_key),
            "league_name": league.get("name", "Unknown League"),
            "season": league.get("season"),
            "current_week": _int(league.get("current_week"), 1),
            "start_week": _int(league.get("start_week"), 1),
            "end_week": _int(league.get("end_week"), 17),
            "total_teams": _int(league.get("num_teams")),
            "url": league.get("url", ""),
        }

    def fetch_standings(self) -> List[Dict[str, Any]]:
        content = self.get(f"league/{self.league_key}/standings")
        league = content.get("league")
        standings_node = flatten(league).get("standings")
        teams_node = flatten(standings_node).get("teams") if standings_node else None

        rows: List[Dict[str, Any]] = []
        for raw_team in iter_collection(teams_node):
            team = _parse_team(raw_team)
            if team:
                rows.append(team)

        rows.sort(key=lambda t: (t.get("rank") or 999, -t.get("points_for", 0.0)))
        for index, row in enumerate(rows, 1):
            row.setdefault("rank", index)
        return rows

    def fetch_scoreboard(self, week: int) -> List[Dict[str, Any]]:
        content = self.get(f"league/{self.league_key}/scoreboard;week={week}")
        league = flatten(content.get("league"))
        scoreboard = flatten(league.get("scoreboard"))
        matchups_node = scoreboard.get("matchups")

        matchups: List[Dict[str, Any]] = []
        for index, raw_matchup in enumerate(iter_collection(matchups_node)):
            parsed = _parse_matchup(raw_matchup, index)
            if parsed:
                matchups.append(parsed)
        return matchups

    def fetch_team_roster(self, team_key: str, week: int) -> List[Dict[str, Any]]:
        """Fetch one team's Week N roster with per-player scoring and slot.

        Returns a flat list of ``{name, selected_position, points, is_bench}``.
        ``selected_position`` is the Yahoo roster slot for that week (e.g. "QB",
        "WR", "BN", "IR"); bench/IR slots don't count toward the team's score.
        """
        content = self.get(
            f"team/{team_key}/roster;week={week}/players/stats;type=week;week={week}"
        )
        team_node = flatten(content.get("team"))
        roster = flatten(team_node.get("roster"))
        players_node = roster.get("players")

        players: List[Dict[str, Any]] = []
        for raw_player in iter_collection(players_node):
            node = flatten(raw_player)
            player = flatten(node.get("player")) if "player" in node else node
            name = flatten(player.get("name", {})).get("full", "Unknown")
            position = flatten(player.get("selected_position", {})).get("position", "")
            points = _num(flatten(player.get("player_points", {})).get("total"))
            players.append(
                {
                    "name": name,
                    "selected_position": position,
                    "points": round(points, 2),
                    "is_bench": position in ("BN", "IR", "IR+", "NA"),
                }
            )
        return players

    def fetch_all_rosters(
        self, week: int, team_keys: List[str]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Fetch every team's roster for the week. Best-effort: a team whose

        roster fetch fails is simply omitted rather than failing the whole
        pipeline -- bench-based awards for that team just stay unavailable
        this week instead of blocking the recap.
        """
        rosters: Dict[str, List[Dict[str, Any]]] = {}
        for team_key in team_keys:
            try:
                rosters[team_key] = self.fetch_team_roster(team_key, week)
            except YahooError:
                continue
        return rosters

    def fetch_week_data(self, week: int, with_rosters: bool = True) -> Dict[str, Any]:
        """Fetch and normalize everything the recap context needs for a week."""
        league = self.fetch_league_meta()
        standings = self.fetch_standings()
        matchups = self.fetch_scoreboard(week)

        try:
            next_matchups = self.fetch_scoreboard(week + 1)
        except YahooError:
            # A missing next week is normal at the end of the season.
            next_matchups = []

        teams = [dict(row) for row in standings]

        rosters: Dict[str, List[Dict[str, Any]]] = {}
        if with_rosters:
            team_keys = [t["team_key"] for t in teams if t.get("team_key")]
            rosters = self.fetch_all_rosters(week, team_keys)

        return {
            "week": week,
            "league": league,
            "teams": {"total_teams": len(teams), "teams": teams},
            "standings": {"standings": standings},
            "matchups": {
                "week": week,
                "total_matchups": len(matchups),
                "matchups": matchups,
            },
            "next_week_matchups": {
                "week": week + 1,
                "total_matchups": len(next_matchups),
                "matchups": next_matchups,
            },
            "rosters": rosters,
            "week_stats": compute_week_stats(week, matchups),
            "source": "yahoo",
        }


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


def _parse_managers(team: Dict[str, Any]) -> List[str]:
    names: List[str] = []
    for raw_manager in iter_collection(team.get("managers")):
        manager = flatten(raw_manager).get("manager")
        manager = flatten(manager) if manager is not None else {}
        nickname = manager.get("nickname") or manager.get("manager_id")
        if nickname and nickname != "--hidden--":
            names.append(str(nickname))
    return names


def _parse_team(raw_team: Any) -> Optional[Dict[str, Any]]:
    """Normalize one Yahoo team node (standings or matchup form)."""
    node = flatten(raw_team)
    team = flatten(node.get("team")) if "team" in node else node
    if not team.get("team_key"):
        return None

    standings = flatten(team.get("team_standings"))
    outcome = flatten(standings.get("outcome_totals"))
    points = flatten(team.get("team_points"))
    projected = flatten(team.get("team_projected_points"))
    managers = _parse_managers(team)

    return {
        "team_key": team.get("team_key"),
        "team_id": _int(team.get("team_id")),
        "team_name": team.get("name", "Unknown"),
        "owner": managers[0] if managers else team.get("name", "Unknown"),
        "managers": managers,
        "logo_url": _team_logo(team),
        "rank": _int(standings.get("rank")) or None,
        "wins": _int(outcome.get("wins")),
        "losses": _int(outcome.get("losses")),
        "ties": _int(outcome.get("ties")),
        "win_pct": round(_num(outcome.get("percentage")), 3),
        "points_for": round(_num(standings.get("points_for")), 2),
        "points_against": round(_num(standings.get("points_against")), 2),
        "streak": _parse_streak(standings),
        "moves": _int(team.get("number_of_moves")),
        "trades": _int(team.get("number_of_trades")),
        "week_points": round(_num(points.get("total")), 2),
        "week_projected": round(_num(projected.get("total")), 2),
    }


def _team_logo(team: Dict[str, Any]) -> str:
    for raw_logo in iter_collection(team.get("team_logos")):
        logo = flatten(flatten(raw_logo).get("team_logo"))
        if logo.get("url"):
            return str(logo["url"])
    return ""


def _parse_streak(standings: Dict[str, Any]) -> str:
    streak = flatten(standings.get("streak"))
    kind = (streak.get("type") or "").upper()[:1]
    value = _int(streak.get("value"))
    return f"{kind}{value}" if kind and value else "--"


def _parse_matchup(raw_matchup: Any, index: int) -> Optional[Dict[str, Any]]:
    node = flatten(raw_matchup)
    matchup = flatten(node.get("matchup")) if "matchup" in node else node

    teams = [
        team
        for team in (_parse_team(t) for t in iter_collection(matchup.get("teams")))
        if team
    ]
    if len(teams) != 2:
        return None

    home, away = teams[0], teams[1]
    home_score = home.get("week_points", 0.0)
    away_score = away.get("week_points", 0.0)

    if home_score > away_score:
        winner = home["team_name"]
    elif away_score > home_score:
        winner = away["team_name"]
    else:
        winner = None

    def side(team: Dict[str, Any], score: float) -> Dict[str, Any]:
        return {
            "team_id": team["team_id"],
            "team_key": team["team_key"],
            "team_name": team["team_name"],
            "owner": team["owner"],
            "score": score,
            "projected": team.get("week_projected", 0.0),
            "record": f"{team['wins']}-{team['losses']}-{team['ties']}",
            "starters": [],
            "bench": [],
        }

    return {
        "matchup_id": index,
        "week": _int(matchup.get("week"), 0),
        "is_playoffs": str(matchup.get("is_playoffs", "0")) == "1",
        "is_consolation": str(matchup.get("is_consolation", "0")) == "1",
        "status": matchup.get("status", ""),
        "home_team": side(home, home_score),
        "away_team": side(away, away_score),
        "winner": winner,
        "margin": round(abs(home_score - away_score), 2),
    }


def compute_week_stats(week: int, matchups: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Derive the week's superlative-worthy numbers from parsed matchups."""
    stats: Dict[str, Any] = {
        "week": week,
        "highest_score": None,
        "lowest_score": None,
        "biggest_blowout": None,
        "closest_game": None,
        "average_score": None,
        "biggest_upset": None,
    }
    if not matchups:
        return stats

    scored = []
    for matchup in matchups:
        for key in ("home_team", "away_team"):
            side = matchup[key]
            scored.append(side)

    if scored:
        high = max(scored, key=lambda s: s["score"])
        low = min(scored, key=lambda s: s["score"])
        stats["highest_score"] = {
            "team": high["team_name"],
            "owner": high["owner"],
            "team_key": high.get("team_key"),
            "points": round(high["score"], 2),
        }
        stats["lowest_score"] = {
            "team": low["team_name"],
            "owner": low["owner"],
            "team_key": low.get("team_key"),
            "points": round(low["score"], 2),
        }
        stats["average_score"] = round(
            sum(s["score"] for s in scored) / len(scored), 2
        )

    decided = [m for m in matchups if m["winner"]]
    if decided:
        blowout = max(decided, key=lambda m: m["margin"])
        closest = min(decided, key=lambda m: m["margin"])
        blowout_winner = (
            blowout["home_team"]
            if blowout["winner"] == blowout["home_team"]["team_name"]
            else blowout["away_team"]
        )
        blowout_loser = (
            blowout["away_team"] if blowout_winner is blowout["home_team"] else blowout["home_team"]
        )
        stats["biggest_blowout"] = {
            "winner": blowout["winner"],
            "winner_team_key": blowout_winner.get("team_key"),
            "loser": blowout_loser["team_name"],
            "margin": blowout["margin"],
        }
        stats["closest_game"] = {
            "team1": closest["home_team"]["team_name"],
            "team2": closest["away_team"]["team_name"],
            "margin": closest["margin"],
        }

        # An upset: the side Yahoo's pregame projection favored still lost.
        # Ranked by how big the projection gap was, not the final margin --
        # a team projected to lose by 8 and winning by 1 is a bigger upset
        # than a projected pick'em that goes either way.
        upsets = []
        for matchup in decided:
            home, away = matchup["home_team"], matchup["away_team"]
            winner_side = home if matchup["winner"] == home["team_name"] else away
            loser_side = away if winner_side is home else home
            winner_proj = winner_side.get("projected") or 0.0
            loser_proj = loser_side.get("projected") or 0.0
            if winner_proj and loser_proj and winner_proj < loser_proj:
                upsets.append(
                    {
                        "winner": winner_side["team_name"],
                        "winner_owner": winner_side["owner"],
                        "winner_team_key": winner_side.get("team_key"),
                        "loser": loser_side["team_name"],
                        "winner_projected": round(winner_proj, 2),
                        "loser_projected": round(loser_proj, 2),
                        "projection_gap": round(loser_proj - winner_proj, 2),
                        "actual_margin": matchup["margin"],
                    }
                )
        if upsets:
            stats["biggest_upset"] = max(upsets, key=lambda u: u["projection_gap"])
    return stats
