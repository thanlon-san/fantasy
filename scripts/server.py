#!/usr/bin/env python3
"""
Simple server management script for Fantasy Football Recap API
Provides start/stop/restart/status commands with PID tracking
"""

import sys
import os
import signal
import time
import subprocess
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
PID_FILE = PROJECT_ROOT / ".server.pid"
LOG_FILE = Path("/tmp/api_fantasy.log")


def read_pid():
    """Read PID from file"""
    if PID_FILE.exists():
        try:
            return int(PID_FILE.read_text().strip())
        except:
            return None
    return None


def write_pid(pid):
    """Write PID to file"""
    PID_FILE.write_text(str(pid))


def is_running(pid):
    """Check if process is running"""
    if not pid:
        return False
    try:
        os.kill(pid, 0)  # Doesn't actually kill, just checks if process exists
        return True
    except OSError:
        return False


def start_server():
    """Start the API server"""
    pid = read_pid()
    
    if pid and is_running(pid):
        print(f"❌ Server already running (PID: {pid})")
        print(f"   Use 'pnpm stop' or 'pnpm restart' instead")
        return 1
    
    # Clean up stale PID file
    if PID_FILE.exists():
        PID_FILE.unlink()
    
    print("🚀 Starting Fantasy Football API server...")
    
    # Start server in background
    process = subprocess.Popen(
        [sys.executable, "-m", "src.api"],
        cwd=PROJECT_ROOT,
        stdout=open(LOG_FILE, "w"),
        stderr=subprocess.STDOUT,
        start_new_session=True  # Detach from parent
    )
    
    write_pid(process.pid)
    
    # Wait a moment and check if it started
    time.sleep(2)
    
    if is_running(process.pid):
        print(f"✅ Server started successfully (PID: {process.pid})")
        print(f"   📖 API: http://localhost:8000")
        print(f"   📝 Logs: {LOG_FILE}")
        print(f"   🔍 Status: pnpm status")
        print(f"   🛑 Stop: pnpm stop")
        return 0
    else:
        print(f"❌ Server failed to start")
        print(f"   Check logs: pnpm logs:api")
        PID_FILE.unlink()
        return 1


def stop_server():
    """Stop the API server"""
    pid = read_pid()
    
    if not pid:
        print("❌ No server PID found")
        return 1
    
    if not is_running(pid):
        print("❌ Server not running")
        PID_FILE.unlink()
        return 1
    
    print(f"🛑 Stopping server (PID: {pid})...")
    
    try:
        # Try graceful shutdown first
        os.kill(pid, signal.SIGTERM)
        time.sleep(2)
        
        # Force kill if still running
        if is_running(pid):
            print("   Force killing...")
            os.kill(pid, signal.SIGKILL)
            time.sleep(1)
        
        if not is_running(pid):
            print("✅ Server stopped successfully")
            PID_FILE.unlink()
            return 0
        else:
            print("❌ Failed to stop server")
            return 1
            
    except Exception as e:
        print(f"❌ Error stopping server: {e}")
        return 1


def restart_server():
    """Restart the API server"""
    print("🔄 Restarting server...")
    stop_server()
    time.sleep(1)
    return start_server()


def status_server():
    """Check server status"""
    pid = read_pid()
    
    if not pid:
        print("❌ No server running (no PID file)")
        return 1
    
    if is_running(pid):
        print(f"✅ Server is running (PID: {pid})")
        print(f"   📖 API: http://localhost:8000")
        print(f"   📝 Logs: pnpm logs:api")
        
        # Try to hit health endpoint
        try:
            import urllib.request
            import json
            
            with urllib.request.urlopen("http://localhost:8000/health", timeout=2) as response:
                data = json.loads(response.read())
                print(f"   🏈 League: {data.get('league_name', 'Unknown')}")
                print(f"   📅 Week: {data.get('current_nfl_week', 'Unknown')}")
        except:
            print("   ⚠️  Health check failed (server may be starting up)")
        
        return 0
    else:
        print(f"❌ Server not running (stale PID: {pid})")
        PID_FILE.unlink()
        return 1


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/server.py [start|stop|restart|status]")
        return 1
    
    command = sys.argv[1].lower()
    
    commands = {
        "start": start_server,
        "stop": stop_server,
        "restart": restart_server,
        "status": status_server,
    }
    
    if command not in commands:
        print(f"❌ Unknown command: {command}")
        print(f"   Available: {', '.join(commands.keys())}")
        return 1
    
    return commands[command]()


if __name__ == "__main__":
    sys.exit(main())

