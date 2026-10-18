from __future__ import annotations

import json

from app.db import database
from app.seed import seed_if_needed
from app.services.escalation import run_escalations


def main() -> None:
    database.connect()
    seed_if_needed(database)
    result = run_escalations(database, triggered_by="cli")
    print(json.dumps(result))
    database.close()


if __name__ == "__main__":
    main()
