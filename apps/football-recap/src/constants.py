"""
Configuration constants for fantasy football project
Centralized constants to avoid magic numbers throughout the codebase
"""

from datetime import datetime

# ============================================================================
# Team Owner Mapping
# ============================================================================
# TEAM_OWNERS is a *display-name override only*. Live Yahoo team_name values
# from week_data are the source of truth for recaps and League HQ. If someone
# renames their team in Yahoo, the next prepare_recap_context.py / canvas
# update picks up the new name automatically — no code change needed, except
# optionally adding a TEAM_OWNERS alias here for a nicer owner display.
#
# resolve_owner() looks up this dict first, then the Yahoo manager nickname.
TEAM_OWNERS = {
    # 2026 Yahoo league (1324751) — live mapping from League Members.
    "Purdy Boys": "Tyler Hanlon",
    "Monster of the Midway": "Elisa Keny (Ambrose)",
    "Scott's Tots": "Marissa Tomko",
    "Hut Hut Eich": "Adam Eichorn",
    "The Blackberries": "Gregory Stewart",
    "Morgan's Team!": "Morgan Nelson",
    "High Quality TD Rate": "Peter Van Oot",
    "Blitz Squad Joseph": "Joe Barry",
    "Game of Throws": "Luis Islas",
    "Stiff Arm tim": "Tim Tang",
    "big d's fantasy": "Danielle DiRaddo",
    "Goal Line Stand Jesse": "Jesse Chou",
    "Penalty Flag Sachin": "Sachin Phadkar",
    "Dasher Mafia": "Adam Strutynski",
    # 2025 ESPN (history only — not the live mapping):
    # "Hut, Hut, Eich" -> Adam Eichorn
    # "High Qual Completion Deliv Rate" -> Peter Van Oot
    # "New Vertical Threats" -> Morgan Nelson
    # "Team Tang" -> Tim Tang
    # "We're More Than Delivery" -> Joe Barry
    # "Beacon" -> Han Jang
    # "Show in wallet off" -> Achilleas Zilakos
    # "Fly PCIO Fly" -> Kristin Mendez
    # "Laser Focused" -> Tiffany Wong
    # "Monstrous Team" / "Maia's Monstrous Team" -> maia.craver
    # "Hot Chubb Time Machine" -> kevin.agresto
    # "Team Wise" -> Christopher Wise
    # "Greg's Great Team" -> greg.davis.cw
}

# Fallback roster when week_data has no teams (preseason / Yahoo API down).
# Weekly recap, context builder, and League HQ prefer live Yahoo team_name
# from week_data once fetch_all_for_week() succeeds.
PRESEASON_MANAGERS_2026 = [
    {
        "owner": "Tyler Hanlon",
        "team": "Purdy Boys",
        "last_team": "Purdy Boys",
        "slack_id": "U03FE7P8EEP",
        "status": "locked",
    },
    {
        "owner": "Elisa Keny (Ambrose)",
        "team": "Monster of the Midway",
        "last_team": "Monster of the Midway",
        "slack_id": "U03L8KFL1RS",
        "status": "locked",
    },
    {
        "owner": "Marissa Tomko",
        "team": "Scott's Tots",
        "last_team": "Scott's Tots",
        "slack_id": "U032LD8RMK8",
        "status": "locked",
    },
    {
        "owner": "Adam Eichorn",
        "team": "Hut Hut Eich",
        "last_team": "Hut, Hut, Eich",
        "slack_id": "U0405KM3X7C",
        "status": "locked",
    },
    {
        "owner": "Gregory Stewart",
        "team": "The Blackberries",
        "last_team": "",
        "slack_id": "U08SKVCGDQW",
        "status": "locked",
    },
    {
        "owner": "Morgan Nelson",
        "team": "Morgan's Team!",
        "last_team": "New Vertical Threats",
        "slack_id": "U03R72JAKFH",
        "status": "locked",
    },
    {
        "owner": "Peter Van Oot",
        "team": "High Quality TD Rate",
        "last_team": "High Qual Completion Deliv Rate",
        "slack_id": "UPQ8CPJDR",
        "status": "locked",
    },
    {
        "owner": "Joe Barry",
        "team": "Blitz Squad Joseph",
        "last_team": "We're More Than Delivery",
        "slack_id": "U07JPH677ED",
        "status": "locked",
    },
    {
        "owner": "Luis Islas",
        "team": "Game of Throws",
        "last_team": "Touchback Luis",
        "slack_id": "U0AV2EB5GUD",
        "status": "locked",
    },
    {
        "owner": "Tim Tang",
        "team": "Stiff Arm tim",
        "last_team": "Team Tang",
        "slack_id": "U02C39SFXPD",
        "status": "locked",
    },
    {
        "owner": "Danielle DiRaddo",
        "team": "big d's fantasy",
        "last_team": "",
        "slack_id": "U08SD0PJ3EU",
        "status": "locked",
    },
    {
        "owner": "Jesse Chou",
        "team": "Goal Line Stand Jesse",
        "last_team": "",
        "slack_id": "U09KVP9JHQS",
        "status": "locked",
    },
    {
        "owner": "Sachin Phadkar",
        "team": "Penalty Flag Sachin",
        "last_team": "",
        "slack_id": "U0761N3RYSW",
        "status": "locked",
    },
    {
        "owner": "Adam Strutynski",
        "team": "Dasher Mafia",
        "last_team": "",
        "slack_id": "U08QHPYDZ46",
        "status": "locked",
    },
]

# Randomized Yahoo draft order — Sep 8, 2026 (14-team snake, pick 1–14).
DRAFT_ORDER_2026 = [
    "Scott's Tots",
    "Goal Line Stand Jesse",
    "Stiff Arm tim",
    "High Quality TD Rate",
    "Purdy Boys",
    "Penalty Flag Sachin",
    "Blitz Squad Joseph",
    "The Blackberries",
    "big d's fantasy",
    "Dasher Mafia",
    "Hut Hut Eich",
    "Game of Throws",
    "Monster of the Midway",
    "Morgan's Team!",
]


def _normalize_team_key(name: str) -> str:
    """Normalize Yahoo team_name quirks (curly quotes, etc.) for lookup."""
    if not name:
        return ""
    return name.replace("\u2019", "'").replace("\u2018", "'").strip()


def _slack_id_by_team() -> dict[str, str]:
    """Yahoo team_name (current or last season) → Slack user ID."""
    out: dict[str, str] = {}
    for mgr in PRESEASON_MANAGERS_2026:
        sid = mgr.get("slack_id") or ""
        if not sid:
            continue
        for key in (mgr.get("team"), mgr.get("last_team")):
            if key:
                out[_normalize_team_key(key)] = sid
    return out


def _slack_id_by_owner() -> dict[str, str]:
    """Display owner name → Slack user ID."""
    out: dict[str, str] = {}
    for mgr in PRESEASON_MANAGERS_2026:
        sid = mgr.get("slack_id") or ""
        owner = mgr.get("owner") or ""
        if sid and owner:
            out[owner] = sid
    return out


_SLACK_ID_BY_TEAM = _slack_id_by_team()
_SLACK_ID_BY_OWNER = _slack_id_by_owner()


def resolve_slack_id(team_name: str = "", owner_name: str = "") -> str:
    """
    Resolve a Slack user ID for a manager.

    Matches current Yahoo team_name, last_team alias, TEAM_OWNERS override,
    or curated owner display name from PRESEASON_MANAGERS_2026.
    """
    if team_name:
        norm = _normalize_team_key(team_name)
        sid = _SLACK_ID_BY_TEAM.get(norm)
        if sid:
            return sid
        if norm in TEAM_OWNERS:
            sid = _SLACK_ID_BY_OWNER.get(TEAM_OWNERS[norm])
            if sid:
                return sid
    if owner_name:
        sid = _SLACK_ID_BY_OWNER.get(owner_name)
        if sid:
            return sid
        # Yahoo manager nicknames are often first names only.
        for mgr in PRESEASON_MANAGERS_2026:
            full = mgr.get("owner") or ""
            if not full:
                continue
            if full == owner_name or full.startswith(f"{owner_name} "):
                return mgr.get("slack_id") or ""
            if owner_name == full.split()[0]:
                return mgr.get("slack_id") or ""
    return ""


def format_slack_mention(
    team_name: str = "", owner_name: str = "", fallback_manager: str = ""
) -> str:
    """
    Slack message mention for a manager.

    Returns ``<@U…>`` when a slack_id is known; otherwise the display owner
    name with no leading ``@`` (plain @Name does not ping in Slack).
    """
    resolved_owner = owner_name or resolve_owner(team_name, fallback_manager)
    slack_id = resolve_slack_id(team_name=team_name, owner_name=resolved_owner)
    if slack_id:
        return f"<@{slack_id}>"
    return resolved_owner


def resolve_owner(team_name: str, fallback_manager: str = "") -> str:
    """
    Resolve a friendly owner name for a team.

    TEAM_OWNERS is a display-name override keyed by the *current* Yahoo
    team_name. A rename in Yahoo is picked up automatically from week_data;
    add an alias here only if you want a nicer owner label than the
    manager nickname.

    Priority:
      1. Explicit override in TEAM_OWNERS (curated display names).
      2. Yahoo manager nickname from the API (usually a first name).
      3. Literal "Unknown" as a last resort.
    """
    if team_name in TEAM_OWNERS:
        return TEAM_OWNERS[team_name]
    if fallback_manager:
        return fallback_manager
    return "Unknown"

# ============================================================================
# API Configuration
# ============================================================================
DEFAULT_API_PORT = 8000
DEFAULT_API_HOST = "0.0.0.0"
REQUEST_TIMEOUT_SECONDS = 30
API_RATE_LIMIT = "60/minute"  # Max requests per minute

# ============================================================================
# Data Thresholds
# ============================================================================
# Player Performance
NOTABLE_PLAYER_THRESHOLD = 15.0  # Points to highlight in recap
HIGH_SCORER_THRESHOLD = 25.0  # Exceptional performance
BUST_THRESHOLD = 5.0  # Underperformance threshold

# Projection Variance
PROJECTION_MISS_THRESHOLD = 10.0  # Points off projection to highlight
SIGNIFICANT_PROJECTION_MISS = 20.0  # Major projection miss

# Benching & Roster Decisions
ROASTABLE_START_PERCENTAGE = 20  # ESPN start % to roast benching decisions
DEEP_SLEEPER_THRESHOLD = 10  # Players started in <10% of leagues
SIGNIFICANT_BENCH_POINTS = 40.0  # Total bench points worth mentioning

# Management Quality
SIGNIFICANT_MANAGEMENT_GAP = 20.0  # Points gap for optimal lineup roasting
EXCELLENT_MANAGEMENT_GAP = 5.0  # Well-managed lineup threshold
MANAGEMENT_DISASTER_GAP = 40.0  # Catastrophic mismanagement

# Position Group Thresholds
WEAK_POSITION_GROUP_TOTAL = 15.0  # Combined position points to roast
STRONG_POSITION_GROUP_TOTAL = 50.0  # Strong position group performance

# ============================================================================
# History & Memory
# ============================================================================
MAX_RECAP_HISTORY_WEEKS = 10  # Keep only last N weeks in memory
MAX_TREND_HISTORY_WEEKS = 6  # Weeks to track for trend analysis
PREVIOUS_RECAPS_CONTEXT_LIMIT = 3  # Recaps to check for repetition

# ============================================================================
# File Paths
# ============================================================================
OUTPUT_DIR = "output"
RECAP_HISTORY_FILE = "recap_history.json"
TREND_HISTORY_FILE = "trend_history.json"
RECAP_HISTORY_BACKUP = "recap_history_backup.json"
TREND_HISTORY_BACKUP = "trend_history_backup.json"

# ============================================================================
# Recap Generation
# ============================================================================
# Content Ratios
LOWLIGHT_PERCENTAGE = 85  # Percentage of roasts vs highlights
HIGHLIGHT_PERCENTAGE = 15

# Word Counts
MIN_RECAP_WORDS = 400
MAX_RECAP_WORDS = 500
WORDS_PER_MATCHUP_MIN = 40
WORDS_PER_MATCHUP_MAX = 50

# LLM Configuration
DEFAULT_LLM_MODEL = "claude-sonnet-4-5-20250929"
LLM_MAX_TOKENS = 2000
LLM_TEMPERATURE = 1.0

# CRM Jargon
MIN_CRM_JARGON_COUNT = 3
MAX_CRM_JARGON_COUNT = 5

# ============================================================================
# Trend Analysis
# ============================================================================
HOT_TEAM_THRESHOLD = 110.0  # Average score for "hot" teams
COLD_TEAM_THRESHOLD = 85.0  # Average score for "cold" teams
CONSECUTIVE_FAILS_THRESHOLD = 2  # Consecutive bad management weeks
HIGH_CONSISTENCY_RANGE = 10.0  # Point spread for "high consistency"
MEDIUM_CONSISTENCY_RANGE = 20.0  # Point spread for "medium consistency"

# ============================================================================
# NFL Season Configuration
# ============================================================================
# 2026 NFL Season (kickoff Thu Sep 3, 2026 -> first full slate Sun Sep 6).
# Fantasy Week 1 starts on the Thursday of kickoff week.
NFL_SEASON_START_DATE = datetime(2026, 9, 3)
NFL_REGULAR_SEASON_WEEKS = 18
NFL_PLAYOFF_START_WEEK = 15  # Fantasy playoffs typically start week 15

# ============================================================================
# Waiver Activity
# ============================================================================
HIGH_ACQUISITION_THRESHOLD = 15  # Waiver moves considered "high churn"
HIGH_DROP_THRESHOLD = 10  # Drops considered "high churn"
ZERO_ACTIVITY_FLAG = 0  # No roster moves all season

# ============================================================================
# Validation
# ============================================================================
MIN_VALID_WEEK = 1
MAX_VALID_WEEK = NFL_REGULAR_SEASON_WEEKS
MIN_VALID_SCORE = 0.0
MAX_VALID_SCORE = 250.0  # Sanity check for impossible scores

# ============================================================================
# Helper Functions
# ============================================================================


def get_current_nfl_week() -> int:
    """
    Auto-detect current NFL week based on date

    Returns:
        Current week number (1-18)
    """
    if datetime.now() < NFL_SEASON_START_DATE:
        return 1

    weeks_since_start = (datetime.now() - NFL_SEASON_START_DATE).days // 7
    current_week = weeks_since_start + 1

    # Cap at regular season weeks
    return min(max(1, current_week), NFL_REGULAR_SEASON_WEEKS)


def default_recap_week(
    explicit_week: int | None = None,
    *,
    yahoo_current_week: int | None = None,
) -> int:
    """
    Resolve the week for recap / Slack prep when ``--week`` is omitted.

    Yahoo's ``current_week`` can lag the calendar early in the week; prefer it
    when available (live ``league_info`` or cached ``week_data``), then fall
    back to :func:`get_current_nfl_week`.
    """
    if explicit_week is not None:
        return explicit_week
    if yahoo_current_week is not None:
        cw = int(yahoo_current_week)
        if validate_week_number(cw):
            return cw
    return get_current_nfl_week()


def is_playoff_week(week: int) -> bool:
    """Check if a given week is in fantasy playoffs"""
    return week >= NFL_PLAYOFF_START_WEEK


def validate_week_number(week: int) -> bool:
    """Validate a week number is within valid range"""
    return MIN_VALID_WEEK <= week <= MAX_VALID_WEEK


def validate_score(score: float) -> bool:
    """Validate a score is within reasonable range"""
    return MIN_VALID_SCORE <= score <= MAX_VALID_SCORE


if __name__ == "__main__":
    print("🏈 Fantasy Football Constants")
    print("=" * 60)
    print(f"Current NFL Week: {get_current_nfl_week()}")
    print(f"Season Start: {NFL_SEASON_START_DATE.strftime('%Y-%m-%d')}")
    print(f"Playoff Week: {NFL_PLAYOFF_START_WEEK}")
    print(f"\nThresholds:")
    print(f"  Notable Player: {NOTABLE_PLAYER_THRESHOLD} pts")
    print(f"  Roastable Start %: {ROASTABLE_START_PERCENTAGE}%")
    print(f"  Management Gap: {SIGNIFICANT_MANAGEMENT_GAP} pts")
    print(f"\nHistory Limits:")
    print(f"  Max Recap History: {MAX_RECAP_HISTORY_WEEKS} weeks")
    print(f"  Max Trend History: {MAX_TREND_HISTORY_WEEKS} weeks")
