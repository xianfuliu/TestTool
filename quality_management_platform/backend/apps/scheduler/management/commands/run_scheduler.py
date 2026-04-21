from __future__ import annotations

import time

from django.core.management.base import BaseCommand

from apps.scheduler.views import run_due_tasks


class Command(BaseCommand):
    help = "Run due scheduler tasks."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true", help="Run one scan and exit.")
        parser.add_argument("--interval", type=int, default=10, help="Scan interval in seconds.")
        parser.add_argument("--limit", type=int, default=20, help="Maximum due tasks to run per scan.")

    def handle(self, *args, **options):
        interval = max(1, int(options["interval"] or 10))
        limit = max(1, int(options["limit"] or 20))
        once = bool(options["once"])

        self.stdout.write(self.style.SUCCESS(f"Scheduler worker started, interval={interval}s, limit={limit}"))
        while True:
            results = run_due_tasks(limit=limit)
            if results:
                self.stdout.write(self.style.SUCCESS(f"Executed {len(results)} due task(s)."))
                for result in results:
                    self.stdout.write(f"- {result.get('status', '-')}: {result.get('message', '')}")
            if once:
                break
            time.sleep(interval)
