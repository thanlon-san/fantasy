#!/usr/bin/env python3
"""
Test the new stats fetcher to verify MLB API integration
"""

import sys
from pathlib import Path

app_root = Path(__file__).parent.parent
sys.path.insert(0, str(app_root))

from src.stats_fetcher import StatsFetcher
import logging

logging.basicConfig(level=logging.INFO)

def test_hitter():
    """Test fetching stats for a known hitter"""
    print("\n" + "="*70)
    print("Testing Hitter Stats (Aaron Judge)")
    print("="*70)
    
    fetcher = StatsFetcher(use_cache=True)
    
    # Get multi-window stats
    stats = fetcher.get_multi_window_stats("Aaron Judge", is_pitcher=False)
    
    for window, data in stats.items():
        if data:
            print(f"\n{window}:")
            if data.avg is not None:
                print(f"  AVG: .{int(data.avg * 1000)}")
            print(f"  HR: {data.hr}")
            print(f"  RBI: {data.rbi}")
            print(f"  SB: {data.sb}")
            print(f"  Games: {data.games}")
    
    trending = fetcher.get_trending_status("Aaron Judge", is_pitcher=False)
    print(f"\nTrending: {trending}")

def test_pitcher():
    """Test fetching stats for a known pitcher"""
    print("\n" + "="*70)
    print("Testing Pitcher Stats (Gerrit Cole)")
    print("="*70)
    
    fetcher = StatsFetcher(use_cache=True)
    
    # Get multi-window stats
    stats = fetcher.get_multi_window_stats("Gerrit Cole", is_pitcher=True)
    
    for window, data in stats.items():
        if data:
            print(f"\n{window}:")
            if data.era is not None:
                print(f"  ERA: {data.era:.2f}")
            if data.whip is not None:
                print(f"  WHIP: {data.whip:.2f}")
            print(f"  K: {data.k}")
            print(f"  Wins: {data.w}")
            print(f"  Games: {data.games}")
    
    trending = fetcher.get_trending_status("Gerrit Cole", is_pitcher=True)
    print(f"\nTrending: {trending}")

def test_cache():
    """Test that caching works"""
    print("\n" + "="*70)
    print("Testing Cache Performance")
    print("="*70)
    
    import time
    fetcher = StatsFetcher(use_cache=True)
    
    # First call (should hit API)
    print("\nFirst call (will fetch from API)...")
    start = time.time()
    stats1 = fetcher.get_recent_stats("Aaron Judge", is_pitcher=False, days=30)
    elapsed1 = time.time() - start
    print(f"  Time: {elapsed1:.2f}s")
    
    # Second call (should use cache)
    print("\nSecond call (should use cache)...")
    start = time.time()
    stats2 = fetcher.get_recent_stats("Aaron Judge", is_pitcher=False, days=30)
    elapsed2 = time.time() - start
    print(f"  Time: {elapsed2:.2f}s")
    
    print(f"\nSpeedup: {elapsed1/elapsed2:.1f}x faster")

if __name__ == "__main__":
    print("\n🧪 Testing Stats Fetcher Module\n")
    
    try:
        test_hitter()
        test_pitcher()
        test_cache()
        
        print("\n" + "="*70)
        print("✅ All tests completed!")
        print("="*70 + "\n")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
