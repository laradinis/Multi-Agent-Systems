import json
import os

from config import EVENTS_DIR


class EventLog:
    """Registo de tudo o que acontece numa simulação, com o minuto simulado."""

    def __init__(self, run_id):
        self.run_id = run_id
        self.events = []

    def add(self, sim_time, agent, event, **data):
        self.events.append({"t": round(sim_time, 2), "agent": agent, "event": event, **data})

    def count(self, event):
        return sum(1 for e in self.events if e["event"] == event)

    def save(self):
        os.makedirs(EVENTS_DIR, exist_ok=True)
        path = os.path.join(EVENTS_DIR, f"{self.run_id}.jsonl")
        with open(path, "w", encoding="utf-8") as f:
            for e in self.events:
                f.write(json.dumps(e, ensure_ascii=False, default=str) + "\n")
        return path