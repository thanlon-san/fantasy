"""
Configuration constants for fantasy football project
Centralized constants to avoid magic numbers throughout the codebase
"""

from datetime import datetime, timedelta

# ============================================================================
# Team Owner Mapping
# ============================================================================
TEAM_OWNERS = {
    "Scott's Tots": "Marissa Tomko",
    "Beacon": "Han Jang",
    "Show in wallet off": "Achilleas Zilakos",
    "Fly PCIO Fly": "Kristin Mendez",
    "Hut, Hut, Eich": "Adam Eichorn",
    "Laser Focused": "Tiffany Wong",
    "New Vertical Threats": "Morgan Nelson",
    "Monstrous Team": "maia.craver",
    "Purdy Boys": "tyler.hanlon",
    "Hot Chubb Time Machine": "kevin.agresto",
    "High Qual Completion Deliv Rate": "pete.vanoot",
    "Team Tang": "tim.tang",
    "Team Wise": "Christopher Wise",
    "We're More Than Delivery": "Joe Barry",
    "Greg's Great Team": "greg.davis.cw",
    "Monster of the Midway": "Elisa Keny (Ambrose)",
    "Maia's Monstrous Team": "maia.craver",  # Alternate name
}

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
# 2026 NFL Season.
# Kickoff is Wed Sep 9 2026 (Seahawks/Patriots, 8:20pm ET) -- a Wednesday, not
# the usual Thursday, because Labor Day fell late and Thursday is the Melbourne
# game. Week 1 ends with Monday Night Football on Sep 14.
NFL_SEASON_YEAR = 2026
NFL_SEASON_START_DATE = datetime(2026, 9, 9)
# Days from a week's first game to its last (Wed kickoff -> Mon night finish).
NFL_WEEK_SPAN_DAYS = 5
NFL_REGULAR_SEASON_WEEKS = 18
NFL_PLAYOFF_START_WEEK = 15  # Fantasy playoffs typically start week 15

# ============================================================================
# Yahoo Fantasy Configuration
# ============================================================================
# The league lives on Yahoo (not ESPN) as of the 2026 season. Yahoo resolves
# "nfl.l.<id>" to the current season's game key, so we do not pin a game key.
YAHOO_GAME_CODE = "nfl"
YAHOO_LEAGUE_ID = "1324751"
YAHOO_LEAGUE_KEY = f"{YAHOO_GAME_CODE}.l.{YAHOO_LEAGUE_ID}"
YAHOO_API_BASE = "https://fantasysports.yahooapis.com/fantasy/v2"
YAHOO_TOKEN_URL = "https://api.login.yahoo.com/oauth2/get_token"

# Cloud secret / local file holding the OAuth2 credential blob. The blob is the
# same shape yahoo_oauth_manual.YahooOAuth2 writes: consumer_key,
# consumer_secret, access_token, refresh_token, token_type.
YAHOO_OAUTH_ENV_VAR = "YAHOO_OAUTH_JSON"
# Optional override when the team environment keeps injecting a stale
# YAHOO_OAUTH_JSON (RUNTIME_FORWARD_FILL / old build). Paste fresh tokens
# into this *separate* Runtime secret instead of fighting the cached one.
YAHOO_OAUTH_OVERRIDE_ENV_VAR = "YAHOO_OAUTH_JSON_OVERRIDE"
# Paths tried when YAHOO_OAUTH_JSON is unset. Include cwd-relative paths for
# scripts run from apps/football-recap (../baseball-engine/...) and repo-root-
# relative paths for other entrypoints.
YAHOO_OAUTH_FILE_CANDIDATES = (
    "config/oauth2.json",
    "../baseball-engine/config/oauth2.json",
    "apps/football-recap/config/oauth2.json",
    "apps/baseball-engine/config/oauth2.json",
)

# Number of managers the league is locked at for 2026.
LEAGUE_SIZE_2026 = 14

# Fallback roster used only when Yahoo returns no teams (preseason, or the API
# is unreachable). Intentionally EMPTY: we have never successfully fetched the
# 2026 league, so there is no verified manager list to hardcode. Populating this
# with guesses would put fabricated owners on the League HQ canvas.
#
# To populate it, either let a successful prepare_recap_context.py run cache
# output/week-N-weekdata.json, or drop a JSON file at
# apps/football-recap/config/preseason_2026.json shaped like:
#   {"managers": [{"manager": "...", "team_name": "...", "draft_slot": 1}, ...]}
PRESEASON_MANAGERS_2026: list = []
PRESEASON_CONFIG_FILE = "apps/football-recap/config/preseason_2026.json"

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


def has_season_started() -> bool:
    """True once the season's first game has kicked off.

    get_current_nfl_week() returns 1 both before kickoff and during week 1, so
    callers that need to distinguish "preseason" from "week 1 is in the books"
    must check this separately.
    """
    return datetime.now() >= NFL_SEASON_START_DATE


def get_current_nfl_week() -> int:
    """
    Auto-detect the week currently in progress.

    Returns 1 before kickoff as well as during week 1 -- use has_season_started()
    to tell those apart. To pick a week to RECAP, use get_completed_nfl_week()
    instead: a week in progress has no final scores.

    Returns:
        Current week number (1-18)
    """
    if not has_season_started():
        return 1

    weeks_since_start = (datetime.now() - NFL_SEASON_START_DATE).days // 7
    current_week = weeks_since_start + 1

    # Cap at regular season weeks
    return min(max(1, current_week), NFL_REGULAR_SEASON_WEEKS)


def get_completed_nfl_week(now: datetime = None) -> int:
    """Return the most recent week whose games have all finished.

    This is the week to recap. Returns 0 when no week is complete yet, which is
    the signal that there is nothing to write about -- the Tuesday cron fires
    before kickoff too.

    A week runs Wednesday through Monday night, so week N is done once the day
    after its Monday has arrived.
    """
    now = now or datetime.now()
    last_game_of_week_one = NFL_SEASON_START_DATE + timedelta(days=NFL_WEEK_SPAN_DAYS)
    days_past = (now - last_game_of_week_one).days
    if days_past <= 0:
        return 0
    return min((days_past - 1) // 7 + 1, NFL_REGULAR_SEASON_WEEKS)


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
