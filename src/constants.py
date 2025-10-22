"""
Configuration constants for fantasy football project
Centralized constants to avoid magic numbers throughout the codebase
"""

from datetime import datetime

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
# 2025 NFL Season
NFL_SEASON_START_DATE = datetime(2025, 9, 5)  # First game of 2025 season
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
