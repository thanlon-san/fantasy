#!/usr/bin/env python3
"""
Export Dashboard Data
Generate JSON files for the baseball dashboard from real Python analysis
"""

import json
import sys
from pathlib import Path
from datetime import datetime

app_root = Path(__file__).parent.parent
workspace_root = app_root.parent.parent
sys.path.insert(0, str(app_root))
sys.path.insert(0, str(workspace_root / 'packages'))

from src.yahoo_oauth_manual import YahooOAuth2
from src.yahoo_client import YahooFantasyClient
from src.models import Player, Roster
from src.lineup_optimizer import LineupOptimizer
from src.waiver_analyzer import WaiverAnalyzer
from src.analyzer import KeeperAnalyzer
from src.breakout_detector import BreakoutDetector, BreakoutSignal
from src.accuracy_tracker import AccuracyTracker
from src.injury_tracker import InjuryTracker

# Output directory
dashboard_root = workspace_root / "apps" / "baseball-dashboard"
output_dir = dashboard_root / "public" / "api"
output_dir.mkdir(parents=True, exist_ok=True)

LEAGUE_KEY = "469.l.25136"
MY_TEAM_KEY = "469.l.25136.t.2"

print("\n🔄 Exporting dashboard data...")
print("="*70)

# ─── Yahoo client (initialized once, reused throughout) ───────────────────────

_yahoo_client: YahooFantasyClient | None = None

def _get_yahoo_client() -> YahooFantasyClient:
    global _yahoo_client
    if _yahoo_client is not None:
        return _yahoo_client
    config_path = app_root / "config" / "oauth2.json"
    if not config_path.exists():
        raise FileNotFoundError(f"Yahoo OAuth config not found: {config_path}")
    oauth = YahooOAuth2.load_from_file(str(config_path))
    oauth.refresh_access_token()
    oauth.save_to_file(str(config_path))
    _yahoo_client = YahooFantasyClient(oauth)
    return _yahoo_client


def fetch_roster_from_yahoo() -> tuple:
    """Fetch current roster from Yahoo Fantasy API.
    Returns (roster, player_key_map) where player_key_map is {player_name: yahoo_player_key}.
    """
    client = _get_yahoo_client()

    adp_fetcher = None
    try:
        from src.adp_fetcher import ADPFetcher
        adp_fetcher = ADPFetcher()
    except Exception:
        pass

    raw_players = client.get_team_roster(MY_TEAM_KEY)

    roster = Roster(team_name="2balls", league_name="California Palm League", year=2026)
    player_key_map = {}
    for p in raw_players:
        name = p.get("name", "")
        if not name:
            continue

        position = p.get("display_position") or (
            p.get("eligible_positions", ["UTIL"])[0]
            if p.get("eligible_positions") else "UTIL"
        )
        team = p.get("editorial_team_abbr", "FA")
        player_key_map[name] = p.get("player_key", "")

        adp = 300.0
        if adp_fetcher:
            try:
                adp = adp_fetcher.get_player_adp(name) or 300.0
            except Exception:
                pass

        player = Player(
            name=name,
            position=position,
            team=team,
            draft_round=12,
            draft_year=2025,
            years_kept=0,
            adp=adp,
            is_undrafted_fa=False,
        )
        roster.add_player(player)

    return roster, player_key_map


# Load roster
print("\n📋 Loading roster from Yahoo API...")
roster, player_key_map = fetch_roster_from_yahoo()
print(f"✅ Loaded {len(roster.players)} players from Yahoo API")

# Load injuries (shared across lineup + waiver sections)
print("\n🏥 Loading injury data...")
_injury_tracker = InjuryTracker()
try:
    _injury_tracker.load(force=True)
    print(f"✅ Loaded {len(_injury_tracker.get_all_injuries())} injuries")
except Exception as e:
    print(f"⚠️  Injury fetch failed: {e}")


def _injury_badge(name: str) -> str | None:
    return _injury_tracker.get_badge(name)


# 1. Daily Lineup
print("\n📊 Generating daily lineup recommendations...")
try:
    optimizer = LineupOptimizer(use_breakout_signals=True)
    recommendations = optimizer.get_daily_recommendations(roster, show_all_players=True)
    
    # Log predictions for accuracy tracking
    tracker = AccuracyTracker()
    today = datetime.now().strftime("%Y-%m-%d")
    for rec in recommendations:
        if rec.opponent != "No game":  # Only log games being played
            tracker.log_prediction(
                date=today,
                player_name=rec.player.name,
                player_position=rec.player.position,
                team=rec.player.team,
                opponent=rec.opponent,
                confidence_score=rec.confidence_score,
                recommendation=rec.recommendation.value,
                matchup_score=rec.matchup_score,
                park_score=rec.park_score,
                form_score=rec.form_score,
                platoon_score=rec.platoon_score,
                breakout_boost=rec.breakout_boost
            )
    print(f"✅ Logged {len([r for r in recommendations if r.opponent != 'No game'])} predictions for tracking")
    
    # Group into categories
    playing = [r for r in recommendations if r.opponent != "No game"]
    not_playing = [r for r in recommendations if r.opponent == "No game"]
    
    # Separate into tiers
    must_start = [r for r in playing if r.confidence_score >= 80]
    start = [r for r in playing if 65 <= r.confidence_score < 80]
    flex = [r for r in playing if 50 <= r.confidence_score < 65]
    bench = [r for r in playing if r.confidence_score < 50]
    
    def _fmt(r):
        return {
            "player": r.player.name,
            "player_key": player_key_map.get(r.player.name, ""),
            "position": r.player.position,
            "team": r.player.team,
            "opponent": f"{'@' if r.home_away == 'away' else 'vs'} {r.opponent}",
            "opponent_pitcher": r.opponent_pitcher or "TBD",
            "game_time": r.game_time or "TBD",
            "confidence": int(r.confidence_score),
            "matchup": r.matchup_score,
            "parkFactor": r.park_score,
            "platoon": r.platoon_score,
            "form": r.form_score,
            "breakout": r.breakout_boost,
            "vegas_total": r.vegas_total,
            "reasons": r.reasons,
            "injury": _injury_badge(r.player.name),
        }

    lineup_data = {
        "generated_at": datetime.now().isoformat(),
        "date": datetime.now().strftime("%Y-%m-%d"),
        "must_start": [_fmt(r) for r in must_start],
        "start": [_fmt(r) for r in start],
        "flex": [_fmt(r) for r in flex],
        "bench": [_fmt(r) for r in bench],
        "not_playing": [
            {
                "player": r.player.name,
                "player_key": player_key_map.get(r.player.name, ""),
                "position": r.player.position,
                "team": r.player.team,
                "adp": r.player.adp,
                "injury": _injury_badge(r.player.name),
            }
            for r in not_playing
        ],
        "summary": {
            "total_roster": len(recommendations),
            "playing_today": len(playing),
            "not_playing": len(not_playing),
            "must_start_count": len(must_start),
            "start_count": len(start),
            "flex_count": len(flex),
            "bench_count": len(bench)
        }
    }
    
    with open(output_dir / "daily_lineup.json", "w") as f:
        json.dump(lineup_data, f, indent=2)
    
    print(f"✅ Exported daily lineup: {len(playing)} playing, {len(not_playing)} not playing")
    
except Exception as e:
    print(f"❌ Error generating lineup: {e}")
    # Create minimal data
    lineup_data = {
        "generated_at": datetime.now().isoformat(),
        "error": str(e),
        "must_start": [],
        "start": [],
        "flex": [],
        "bench": [],
        "not_playing": []
    }
    with open(output_dir / "daily_lineup.json", "w") as f:
        json.dump(lineup_data, f, indent=2)

# 2. Waiver Wire Analysis
print("\n🎯 Generating waiver wire data...")
try:
    # Initialize waiver analyzer with breakout detection AND recent stats fetching
    waiver_analyzer = WaiverAnalyzer(
        roster, 
        use_breakout_signals=True,
        fetch_recent_stats=True
    )
    
    # Fetch real free agents from Yahoo
    try:
        print("  Fetching free agents from Yahoo...")
        client = _get_yahoo_client()
        free_agents_raw = client.get_free_agents(LEAGUE_KEY, count=75)
        sample_free_agents = [
            {
                "name": fa["name"],
                "eligible_positions": fa.get("eligible_positions", []),
                "editorial_team_abbr": fa.get("editorial_team_abbr", "FA"),
            }
            for fa in free_agents_raw
            if fa.get("name")
        ]
        print(f"  Got {len(sample_free_agents)} real free agents from Yahoo")
    except Exception as e:
        print(f"  ⚠️  Yahoo FA fetch failed: {e}. Using empty list.")
        sample_free_agents = []
    
    # Analyze free agents against roster
    all_recommendations = waiver_analyzer.analyze_free_agents(sample_free_agents, max_recommendations=20)
    
    # Deduplicate: Keep only the best recommendation per add_player
    seen_players = {}
    for rec in all_recommendations:
        player_key = rec.add_player.name
        if player_key not in seen_players or rec.value_gain > seen_players[player_key].value_gain:
            seen_players[player_key] = rec
    
    # Get top 5 unique add targets
    unique_recommendations = sorted(seen_players.values(), key=lambda x: x.value_gain, reverse=True)[:5]
    
    # Helper function to extract stats safely
    def extract_stats(player, window):
        """Extract stats for a specific window from player.recent_stats"""
        if not player.recent_stats or window not in player.recent_stats:
            return None
        
        stats_obj = player.recent_stats[window]
        return stats_obj.to_dict() if hasattr(stats_obj, 'to_dict') else None
    
    # Helper function to extract Statcast changes
    def extract_statcast_changes(player):
        """Extract Statcast improvements from breakout detector"""
        if not waiver_analyzer.breakout_detector:
            return None
        
        # Check for breakout signal with Statcast data
        parts = player.name.split()
        if len(parts) < 2:
            return None
        
        first_name = parts[0]
        last_name = ' '.join(parts[1:])
        is_pitcher = any(p in player.position for p in ['SP', 'RP', 'P'])
        player_type = 'pitcher' if is_pitcher else 'hitter'
        
        try:
            alert = waiver_analyzer.breakout_detector.analyze_player(
                first_name, last_name, player_type,
                recent_days=14, baseline_days=30
            )
            
            if alert and alert.key_metrics:
                # Convert key metrics to statcast changes format
                changes = {}
                for metric_name, (baseline, recent) in list(alert.key_metrics.items())[:3]:
                    change = recent - baseline
                    # Map metric names to frontend keys
                    if 'exit_velocity' in metric_name.lower():
                        changes['exit_velo'] = f"{change:+.1f} mph"
                    elif 'hard_hit' in metric_name.lower():
                        changes['hard_hit_pct'] = f"{change:+.1f}%"
                    elif 'barrel' in metric_name.lower():
                        changes['barrel_rate'] = f"{change:+.1f}%"
                    elif 'velo' in metric_name.lower() and is_pitcher:
                        changes['velo'] = f"{change:+.1f} mph"
                    elif 'chase' in metric_name.lower():
                        changes['chase_rate'] = f"{change:+.1f}%"
                    elif 'whiff' in metric_name.lower():
                        changes['whiff_rate'] = f"{change:+.1f}%"
                
                return changes if changes else None
        except:
            pass
        
        return None
    
    waiver_data = {
        "generated_at": datetime.now().isoformat(),
        "data_source": "MLB Stats API + Baseball Savant Statcast",
        "targets": [
            {
                "player": rec.add_player.name,
                "position": rec.add_player.position,
                "team": rec.add_player.team,
                "rostered_pct": rec.add_player.rostered_pct,
                "trending": rec.add_player.trending,
                "last_7_days": extract_stats(rec.add_player, 'last_7_days'),
                "last_14_days": extract_stats(rec.add_player, 'last_14_days'),
                "last_30_days": extract_stats(rec.add_player, 'last_30_days'),
                "statcast_changes": extract_statcast_changes(rec.add_player),
                "role_change": None,  # Would need additional data source
                "upcoming_schedule": None,  # Would need schedule API
                "drop_player": rec.drop_player.name,
                "drop_player_position": rec.drop_player.position,
                "confidence": rec.confidence,
                "reason": rec.reason
            }
            for rec in unique_recommendations
        ],
        "summary": {
            "scanned": len(sample_free_agents),
            "recommended": len(unique_recommendations),
            "criteria": "ADP value, breakout signals, recent performance trends",
            "source": "Yahoo Fantasy API (live free agents)"
        }
    }
    
    with open(output_dir / "waiver_wire.json", "w") as f:
        json.dump(waiver_data, f, indent=2)
    
    print(f"✅ Exported waiver wire: {len(unique_recommendations)} unique recommendations from {len(sample_free_agents)} players")
    
except Exception as e:
    print(f"⚠️  Error generating waiver wire: {e}")
    import traceback
    traceback.print_exc()
    # Fallback to placeholder
    waiver_data = {
        "generated_at": datetime.now().isoformat(),
        "error": str(e),
        "targets": []
    }
    with open(output_dir / "waiver_wire.json", "w") as f:
        json.dump(waiver_data, f, indent=2)

# 3. Breakout Detection
print("\n🔬 Generating breakout data...")
try:
    if optimizer.breakout_detector:
        detector = optimizer.breakout_detector
        roster_names = {p.name for p in roster.players}

        # Build candidate list: roster players + free agents
        # Each entry: (name, position, team, is_free_agent)
        candidates: list[tuple[str, str, str, bool]] = [
            (p.name, p.position, p.team, False) for p in roster.players
        ]
        try:
            client = _get_yahoo_client()
            fa_raw = client.get_free_agents(LEAGUE_KEY, count=75)
            for fa in fa_raw:
                if fa.get("name"):
                    pos = fa.get("display_position") or (
                        fa.get("eligible_positions", ["UTIL"])[0]
                        if fa.get("eligible_positions") else "UTIL"
                    )
                    candidates.append((fa["name"], pos, fa.get("editorial_team_abbr", "FA"), True))
            print(f"  Added {len(fa_raw)} free agents to breakout scan")
        except Exception as e:
            print(f"  ⚠️  FA fetch skipped for breakouts: {e}")

        def _analyze_candidate(name, position, team, is_fa):
            name_parts = name.split()
            if len(name_parts) < 2:
                return None
            first_name = name_parts[0]
            last_name = ' '.join(name_parts[1:])
            is_pitcher = any(p in position for p in ('SP', 'RP'))
            player_type = 'pitcher' if is_pitcher else 'hitter'
            alert = detector.analyze_player(
                first_name, last_name, player_type,
                recent_days=14, baseline_days=30
            )
            if not alert or alert.signal not in [BreakoutSignal.STRONG, BreakoutSignal.EMERGING]:
                return None
            metric_changes = []
            for metric_name, (baseline_val, recent_val) in list(alert.key_metrics.items())[:3]:
                change = recent_val - baseline_val
                metric_changes.append(f"{metric_name}: {change:+.1f}")
            return {
                "player": name,
                "position": position,
                "team": team,
                "signal": alert.signal.value,
                "stats": metric_changes,
                "category": player_type.title(),
                "confidence": int(alert.confidence_score),
                "is_free_agent": is_fa,
            }

        breakout_alerts = []
        for (name, position, team, is_fa) in candidates:
            result = _analyze_candidate(name, position, team, is_fa)
            if result:
                breakout_alerts.append(result)

        # Sort: FAs first (actionable adds), then by signal strength and confidence
        signal_order = {"STRONG": 0, "EMERGING": 1}
        breakout_alerts.sort(key=lambda x: (
            0 if x["is_free_agent"] else 1,
            signal_order.get(x["signal"], 2),
            -x["confidence"]
        ))

        breakout_data = {
            "generated_at": datetime.now().isoformat(),
            "alerts": breakout_alerts[:15],  # Up to 15: FAs first, then roster
            "summary": {
                "total_scanned": len(candidates),
                "signals_found": len(breakout_alerts),
                "fa_signals": len([a for a in breakout_alerts if a["is_free_agent"]]),
                "strong_signals": len([a for a in breakout_alerts if a["signal"] == "STRONG"])
            }
        }

        with open(output_dir / "breakouts.json", "w") as f:
            json.dump(breakout_data, f, indent=2)

        fa_count = len([a for a in breakout_alerts if a["is_free_agent"]])
        print(f"✅ Exported breakout data: {len(breakout_alerts)} signals "
              f"({fa_count} free agents, {len(breakout_alerts) - fa_count} roster)")
    else:
        raise Exception("Breakout detector not available")

except Exception as e:
    print(f"⚠️  Error generating breakout data: {e}")
    import traceback
    traceback.print_exc()
    breakout_data = {
        "generated_at": datetime.now().isoformat(),
        "error": str(e),
        "alerts": []
    }
    with open(output_dir / "breakouts.json", "w") as f:
        json.dump(breakout_data, f, indent=2)

# 4. Keepers
print("\n⭐ Generating keeper analysis...")
try:
    analyzer = KeeperAnalyzer(roster)
    analyses = analyzer.analyze_all_players()
    top_keepers = analyzer.get_recommended_keepers(3)
    
    keeper_data = {
        "generated_at": datetime.now().isoformat(),
        "keepers": [
            {
                "player": k.player.name,
                "position": k.player.position,
                "round": k.adjusted_keeper_round or k.keeper_round,
                "adp": int(k.player.adp) if k.player.adp else 0,
                "surplus": f"+{int(k.surplus_value)}" if k.surplus_value else "N/A",
                "value": k.recommendation,
                "years_remaining": k.years_remaining,
                "reason": k.recommendation_reason
            }
            for k in top_keepers
        ],
        "summary": {
            "total_eligible": len([a for a in analyses if a.is_eligible]),
            "recommended": len([a for a in analyses if a.recommendation == "Keep"])
        }
    }
    
    with open(output_dir / "keepers.json", "w") as f:
        json.dump(keeper_data, f, indent=2)
    
    print(f"✅ Exported keeper data: {len(top_keepers)} recommended")
    
except Exception as e:
    print(f"❌ Error generating keepers: {e}")
    keeper_data = {
        "generated_at": datetime.now().isoformat(),
        "error": str(e),
        "keepers": []
    }
    with open(output_dir / "keepers.json", "w") as f:
        json.dump(keeper_data, f, indent=2)

# 5. Regression Candidates (roster + free agents)
print("\n📉 Generating regression candidates...")
try:
    from src.regression_analyzer import RegressionAnalyzer

    reg_analyzer = RegressionAnalyzer()

    # Build combined player list: roster + top free agents
    reg_players: list[dict] = [
        {"name": p.name, "position": p.position, "team": p.team, "is_free_agent": False}
        for p in roster.players
    ]

    try:
        client = _get_yahoo_client()
        free_agents_raw = client.get_free_agents(LEAGUE_KEY, count=50)
        for fa in free_agents_raw:
            if fa.get("name"):
                reg_players.append({
                    "name": fa["name"],
                    "position": fa.get("display_position") or (
                        fa.get("eligible_positions", ["UTIL"])[0]
                        if fa.get("eligible_positions") else "UTIL"
                    ),
                    "team": fa.get("editorial_team_abbr", "FA"),
                    "is_free_agent": True,
                })
        print(f"  Added {len(free_agents_raw)} free agents to regression scan")
    except Exception as e:
        print(f"  ⚠️  FA fetch skipped: {e}")

    reg_results = reg_analyzer.scan_players(reg_players, max_results=20)

    roster_names = {p.name for p in roster.players}

    def _reg_serialize(c):
        return {
            "name": c.name,
            "player_type": c.player_type,
            "team": c.team,
            "position": c.position,
            "direction": c.direction,
            "ba": c.ba,
            "xba": c.xba,
            "slg": c.slg,
            "xslg": c.xslg,
            "xwoba": c.xwoba,
            "ba_delta": c.ba_delta,
            "era": c.era,
            "xera": c.xera,
            "fip": c.fip,
            "era_fip_delta": c.era_fip_delta,
            "confidence": c.confidence,
            "summary": c.summary,
            "improving_metrics": c.improving_metrics,
            "is_free_agent": c.name not in roster_names,
        }

    regression_data = {
        "generated_at": datetime.now().isoformat(),
        "buy_low": [_reg_serialize(c) for c in reg_results["buy_low"]],
        "sell_high": [_reg_serialize(c) for c in reg_results["sell_high"]],
        "scanned": len(reg_players),
    }

    with open(output_dir / "regression.json", "w") as f:
        json.dump(regression_data, f, indent=2)

    print(f"✅ Exported regression: {len(reg_results['buy_low'])} buy-low, "
          f"{len(reg_results['sell_high'])} sell-high from {len(reg_players)} scanned")

except Exception as e:
    print(f"⚠️  Error generating regression data: {e}")
    import traceback
    traceback.print_exc()
    regression_data = {
        "generated_at": datetime.now().isoformat(),
        "error": str(e),
        "buy_low": [],
        "sell_high": [],
        "scanned": 0,
    }
    with open(output_dir / "regression.json", "w") as f:
        json.dump(regression_data, f, indent=2)

print("\n" + "="*70)
print("✅ Dashboard data export complete!")
print(f"📁 Output: {output_dir}")
print("\n💡 To update dashboard:")
print("   1. Run this script: python scripts/export_dashboard_data.py")
print("   2. Commit the updated JSON files")
print("   3. Push to GitHub (auto-deploys to GitHub Pages)")
print("="*70 + "\n")
