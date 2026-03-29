#!/usr/bin/env python3
"""
ADP Data Fetcher
Fetches Average Draft Position data from multiple sources with fuzzy name matching
"""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
from typing import Dict, Optional, Tuple, List
import logging
import unicodedata
from fuzzywuzzy import fuzz, process
from .cache_manager import get_cache

logger = logging.getLogger(__name__)


class ADPFetcher:
    """Fetches ADP data from various sources with smart name matching"""
    
    FANTASYPROS_URL = "https://www.fantasypros.com/mlb/adp/overall.php"
    CACHE_KEY = "adp_data"
    CACHE_TTL_HOURS = 24  # Refresh daily
    TIMEOUT = 30  # seconds
    
    def __init__(self):
        self.session = self._create_session_with_retries()
        self.cache = get_cache()
        self._adp_cache: Dict[str, float] = {}
    
    def _create_session_with_retries(self) -> requests.Session:
        """Create session with automatic retries on failures"""
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        
        # Retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    @staticmethod
    def normalize_name(name: str) -> str:
        """
        Normalize a player name for matching
        - Remove accents (José -> Jose)
        - Remove suffixes (Jr., Sr., III)
        - Lowercase
        - Remove extra whitespace
        """
        # Remove accents
        name = unicodedata.normalize('NFKD', name)
        name = ''.join([c for c in name if not unicodedata.combining(c)])
        
        # Remove common suffixes
        suffixes = [' Jr.', ' Jr', ' Sr.', ' Sr', ' II', ' III', ' IV', ' V']
        for suffix in suffixes:
            if name.endswith(suffix):
                name = name[:-len(suffix)]
        
        # Remove periods (A.J. -> AJ)
        name = name.replace('.', '')
        
        # Lowercase and strip
        name = name.lower().strip()
        
        # Remove extra whitespace
        name = ' '.join(name.split())
        
        return name
    
    def fetch_fantasypros_adp(self) -> Dict[str, float]:
        """
        Scrape ADP data from FantasyPros
        
        Returns:
            Dictionary mapping player names to their ADP values
        """
        # Check in-memory cache first
        if self._adp_cache:
            return self._adp_cache
        
        # Check persistent cache (24 hour TTL)
        cached_data = self.cache.get(self.CACHE_KEY, max_age_hours=self.CACHE_TTL_HOURS)
        if cached_data:
            logger.info(f"Using cached ADP data ({len(cached_data)} players)")
            self._adp_cache = cached_data
            return cached_data
        
        try:
            logger.info("Fetching ADP data from FantasyPros...")
            response = self.session.get(self.FANTASYPROS_URL, timeout=self.TIMEOUT)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find the ADP table
            adp_data = {}
            
            # Look for table rows
            rows = soup.select('table tbody tr')
            
            for row in rows:
                try:
                    # FantasyPros has multiple players per row
                    # Pattern: rank, player_name, yahoo, cbs, rts, nfbc, ft, avg (repeats)
                    cells = row.find_all('td')
                    
                    # Process every 8 cells as one player
                    for i in range(0, len(cells), 8):
                        if i + 7 >= len(cells):
                            break
                        
                        # Cell pattern: [rank, player, yahoo, cbs, rts, nfbc, ft, avg]
                        player_cell = cells[i + 1]
                        avg_cell = cells[i + 7]
                        
                        # Extract player name (text before the parenthesis with team)
                        player_text = player_cell.text.strip()
                        # Remove team/position info: "Mookie Betts (LAD - 2B,SS)" -> "Mookie Betts"
                        if '(' in player_text:
                            player_name = player_text.split('(')[0].strip()
                        else:
                            player_name = player_text
                        
                        # Extract ADP value
                        adp_text = avg_cell.text.strip()
                        try:
                            adp = float(adp_text)
                            adp_data[player_name] = adp
                        except ValueError:
                            continue
                
                except Exception as e:
                    logger.debug(f"Error parsing row: {e}")
                    continue
            
            if adp_data:
                logger.info(f"Fetched {len(adp_data)} player ADPs")
                self._adp_cache = adp_data
                # Save to persistent cache
                self.cache.set(self.CACHE_KEY, adp_data)
                return adp_data
            else:
                logger.warning("No ADP data found in table")
                return {}
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching ADP data: {e}")
            return {}
    
    def get_player_adp(self, player_name: str, fuzzy_threshold: int = 85) -> Optional[float]:
        """
        Get ADP for a specific player with fuzzy matching
        
        Args:
            player_name: Player's name to look up
            fuzzy_threshold: Minimum similarity score (0-100) for fuzzy matching
            
        Returns:
            ADP value or None if not found
        """
        # Fetch ADP data if not already loaded
        if not self._adp_cache:
            self.fetch_fantasypros_adp()
        
        if not self._adp_cache:
            return None
        
        # Try exact match first
        if player_name in self._adp_cache:
            return self._adp_cache[player_name]
        
        # Try case-insensitive match
        for name, adp in self._adp_cache.items():
            if name.lower() == player_name.lower():
                return adp
        
        # Try normalized name matching
        normalized_query = self.normalize_name(player_name)
        for name, adp in self._adp_cache.items():
            if self.normalize_name(name) == normalized_query:
                logger.debug(f"Normalized match: '{player_name}' -> '{name}'")
                return adp
        
        # Try fuzzy matching as last resort
        if fuzzy_threshold > 0:
            best_match = process.extractOne(
                player_name,
                self._adp_cache.keys(),
                scorer=fuzz.token_sort_ratio,
                score_cutoff=fuzzy_threshold
            )
            
            if best_match:
                matched_name, score = best_match[0], best_match[1]
                logger.debug(f"Fuzzy match: '{player_name}' -> '{matched_name}' (score: {score})")
                return self._adp_cache[matched_name]
        
        logger.debug(f"No ADP found for {player_name}")
        return None
    
    def find_similar_names(self, player_name: str, limit: int = 5) -> List[Tuple[str, float, int]]:
        """
        Find similar player names in the ADP database
        Useful for debugging name mismatches
        
        Args:
            player_name: Name to search for
            limit: Maximum number of results
            
        Returns:
            List of (name, adp, similarity_score) tuples
        """
        if not self._adp_cache:
            self.fetch_fantasypros_adp()
        
        if not self._adp_cache:
            return []
        
        matches = process.extract(
            player_name,
            self._adp_cache.keys(),
            scorer=fuzz.token_sort_ratio,
            limit=limit
        )
        
        return [(name, self._adp_cache[name], score) for name, score in matches]
    
    def update_roster_with_adp(self, roster_file: str) -> None:
        """
        Update a roster CSV file with fresh ADP data
        
        Args:
            roster_file: Path to CSV file (must have 'player_name' and 'adp' columns)
        """
        import csv
        from pathlib import Path
        
        path = Path(roster_file)
        if not path.exists():
            raise FileNotFoundError(f"Roster file not found: {roster_file}")
        
        # Fetch latest ADP
        adp_data = self.fetch_fantasypros_adp()
        if not adp_data:
            logger.error("Could not fetch ADP data")
            return
        
        # Read current roster
        with open(path, 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            fieldnames = reader.fieldnames
        
        # Update ADP values
        updated_count = 0
        for row in rows:
            player_name = row.get('player_name', '')
            if player_name:
                adp = self.get_player_adp(player_name)
                if adp:
                    row['adp'] = str(adp)
                    updated_count += 1
                else:
                    logger.warning(f"No ADP found for: {player_name}")
        
        # Write back to file
        with open(path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        
        logger.info(f"Updated {updated_count}/{len(rows)} players with ADP data")
