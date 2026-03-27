import sqlite3
import datetime
from typing import List, Dict, Any

DB_PATH = "anomalies.db"

class AnomalyTracker:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize the SQLite database for tracking risk tier transitions."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS anomalies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    well TEXT NOT NULL,
                    old_tier TEXT NOT NULL,
                    new_tier TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    delta FLOAT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS well_state (
                    well TEXT PRIMARY KEY,
                    current_tier TEXT NOT NULL,
                    last_score FLOAT NOT NULL,
                    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()

    def _calculate_severity(self, old_idx: int, new_idx: int) -> str:
        """Calculate severity based on jump size."""
        if new_idx > old_idx:
            # Escalation
            jump = new_idx - old_idx
            if jump >= 2: return "P1" # e.g. Healthy to Critical
            return "P2" # 1 tier jump
        else:
            return "P3" # Recovery

    def sync_well_state(self, well: str, new_score: float, new_tier: str) -> bool:
        """Sync a well's state. If tier changed, log an anomaly. Returns True if tier changed."""
        tier_levels = {"HEALTHY": 0, "WATCH": 1, "HIGH_RISK": 2, "CRITICAL": 3, "UNKNOWN": 0}
        changed = False
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT current_tier, last_score FROM well_state WHERE well = ?", (well,))
            row = cursor.fetchone()

            if row:
                old_tier, old_score = row
                if old_tier != new_tier:
                    old_idx = tier_levels.get(old_tier, 0)
                    new_idx = tier_levels.get(new_tier, 0)
                    severity = self._calculate_severity(old_idx, new_idx)
                    delta = new_score - old_score
                    
                    cursor.execute('''
                        INSERT INTO anomalies (well, old_tier, new_tier, severity, delta)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (well, old_tier, new_tier, severity, delta))
                    changed = True
                    
                cursor.execute('''
                    UPDATE well_state SET current_tier = ?, last_score = ?, last_updated = CURRENT_TIMESTAMP
                    WHERE well = ?
                ''', (new_tier, new_score, well))
            else:
                cursor.execute('''
                    INSERT INTO well_state (well, current_tier, last_score)
                    VALUES (?, ?, ?)
                ''', (well, new_tier, new_score))
            conn.commit()
        return changed

    def get_recent_anomalies(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Fetch recent anomalies for the UI feed."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, well, old_tier, new_tier, severity, delta, timestamp
                FROM anomalies
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (limit,))
            rows = cursor.fetchall()
            
            anomalies = []
            for r in rows:
                dt = datetime.datetime.fromisoformat(r['timestamp'])
                # Format time string "X mins ago"
                now = datetime.datetime.utcnow()
                diff = now - dt
                if diff.total_seconds() < 60:
                    time_str = "just now"
                elif diff.total_seconds() < 3600:
                    time_str = f"{int(diff.total_seconds()//60)} mins ago"
                elif diff.total_seconds() < 86400:
                    time_str = f"{int(diff.total_seconds()//3600)} hours ago"
                else:
                    time_str = f"{int(diff.total_seconds()//86400)} days ago"
                    
                anomalies.append({
                    "id": str(r['id']),
                    "well": r['well'],
                    "old_tier": r['old_tier'],
                    "new_tier": r['new_tier'],
                    "severity": r['severity'],
                    "delta": float(r['delta']),
                    "timestamp": time_str
                })
            return anomalies

def seed_dummies():
    tracker = AnomalyTracker()
    with sqlite3.connect(tracker.db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM anomalies")
        if cursor.fetchone()[0] == 0:
            print("Seeding dummy anomalies...")
            cursor.execute("INSERT INTO anomalies (well, old_tier, new_tier, severity, delta) VALUES ('RKDS_2026_OP_LOC3', 'WATCH', 'CRITICAL', 'P1', 42.1)")
            cursor.execute("INSERT INTO anomalies (well, old_tier, new_tier, severity, delta) VALUES ('NIMR_WEST_A1', 'HIGH_RISK', 'WATCH', 'P3', -18.4)")
            cursor.execute("INSERT INTO anomalies (well, old_tier, new_tier, severity, delta) VALUES ('HARWEEL_D2', 'HEALTHY', 'HIGH_RISK', 'P1', 35.2)")
            conn.commit()

if __name__ == "__main__":
    seed_dummies()
    print("Anomaly Tracker initialized.")
