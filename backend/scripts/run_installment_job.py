"""
Daily installment generation job.

Run as daily cron:
    python -m backend.scripts.run_installment_job
  or:
    python backend/scripts/run_installment_job.py

IMPORTANT — Uses SUPABASE_SERVICE_KEY (service role key).
Service role bypasses RLS: this script has full DB access.
Do NOT log or expose the service key value in output.

Cron example (midnight UTC):
    0 0 * * * /usr/bin/python /app/backend/scripts/run_installment_job.py >> /var/log/installment_job.log 2>&1
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# Allow running from repo root: python backend/scripts/run_installment_job.py
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed; rely on environment variables being set

from supabase._async.client import AsyncClient, create_client  # type: ignore

from backend.app.services.installment_service import InstallmentService


SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")


async def main() -> None:
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        print(
            json.dumps(
                {"error": "SUPABASE_URL or SUPABASE_SERVICE_KEY not set", "processed": 0, "errors": []}
            )
        )
        sys.exit(1)

    # Service-role client bypasses RLS — intentional for system-level cron
    db: AsyncClient = await create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    # user_id="system" — generate_next() will be overridden per-credit in run_daily_installment_job
    service = InstallmentService(db=db, user_id="system")

    result = await service.run_daily_installment_job()
    print(json.dumps(result))

    if result["errors"]:
        sys.exit(2)  # partial failure — let monitoring detect non-zero exit


if __name__ == "__main__":
    asyncio.run(main())
