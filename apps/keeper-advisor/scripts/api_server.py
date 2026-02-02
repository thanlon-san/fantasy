#!/usr/bin/env python3
"""
Simple Flask API server to serve baseball intelligence data to the dashboard.
"""

from flask import Flask, jsonify
from flask_cors import CORS
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

app = Flask(__name__)
CORS(app)  # Enable CORS for Next.js frontend

@app.route('/api/health')
def health():
    """Health check endpoint"""
    return jsonify({"status": "ok"})

@app.route('/api/daily-lineup')
def daily_lineup():
    """Get daily lineup recommendations"""
    try:
        from src.lineup_optimizer import LineupOptimizer
        from src.daily_matchups import get_todays_games
        
        # Get today's games
        games = get_todays_games()
        
        # TODO: Load user's roster (for now return sample)
        # optimizer = LineupOptimizer()
        # recommendations = optimizer.get_recommendations(roster, games)
        
        # Sample data matching Python tool output
        return jsonify({
            "starters": [
                {
                    "player": "Mookie Betts",
                    "position": "2B",
                    "opponent": "vs COL (Freeland)",
                    "confidence": 92,
                    "matchup": "Excellent",
                    "parkFactor": "+15%",
                    "platoon": "Favorable"
                }
            ],
            "bench": []
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/waiver-wire')
def waiver_wire():
    """Get waiver wire recommendations"""
    try:
        from src.waiver_analyzer import WaiverAnalyzer
        
        # TODO: Implement real waiver analysis
        return jsonify({
            "targets": [
                {
                    "player": "Spencer Steer",
                    "position": "3B/OF",
                    "adp": 145,
                    "reason": "Hot streak + favorable schedule",
                    "signal": "Strong"
                }
            ]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/breakouts')
def breakouts():
    """Get breakout player alerts"""
    try:
        from src.breakout_detector import BreakoutDetector
        
        # TODO: Run breakout scanner
        return jsonify({
            "alerts": [
                {
                    "player": "Elly De La Cruz",
                    "signal": "STRONG",
                    "stat": "Exit velo: 94.2 mph (↑3.5)",
                    "category": "Power"
                }
            ]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/keepers')
def keepers():
    """Get keeper value analysis"""
    try:
        # TODO: Run keeper analysis
        return jsonify({
            "keepers": [
                {
                    "player": "Mookie Betts",
                    "round": "R1",
                    "adp": 3,
                    "surplus": "+427 ADP",
                    "value": "Elite"
                }
            ]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=True)
