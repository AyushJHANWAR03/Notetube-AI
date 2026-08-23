#!/usr/bin/env python3
"""
NoteTube AI — business health-check (cron).

Runs on the droplet every N minutes and emails an alert (via Resend, to
ADMIN_EMAILS) when something is silently broken. Built in response to two
outages that went undetected for days:

  1. OpenAI credits ran dry  -> videos FAILED silently for ~2 days
  2. nginx dead for 2 days    -> caught only by opening the site by hand
     (that one is covered by external UptimeRobot; this script covers the
      internal/business failures UptimeRobot can't see)

Checks:
  - FAILED videos spike   : too many videos flipped to FAILED recently
  - Stuck PROCESSING       : videos stuck mid-processing -> worker dead/wedged
  - RQ queue backlog       : video_processing queue piling up -> worker down
  - OpenAI liveness        : a 1-token probe; catches "credits dry" / bad key
                             directly (OpenAI's billing endpoint is deprecated,
                             so we probe the API instead of reading a balance)

Only emails when a check trips, and suppresses repeat emails for the same
issue within ALERT_COOLDOWN_HOURS so an ongoing incident doesn't spam you.

Usage:
    python scripts/health_check.py           # normal run (cron)
    python scripts/health_check.py --test     # send a test alert email and exit
    python scripts/health_check.py --verbose  # print each check's result

Tune via env (all optional, sensible defaults below):
    HEALTHCHECK_FAILED_THRESHOLD   (default 5)   FAILED videos in the window to alert
    HEALTHCHECK_LOOKBACK_HOURS     (default 2)   window for the FAILED-spike check
    HEALTHCHECK_STUCK_MINUTES      (default 30)  PROCESSING older than this = stuck
    HEALTHCHECK_QUEUE_THRESHOLD    (default 25)  queued jobs to alert on
    HEALTHCHECK_COOLDOWN_HOURS     (default 3)   suppress repeat alerts per check
    HEALTHCHECK_ALERT_EMAILS       (default ADMIN_EMAILS) comma-separated recipients
"""
import os
import sys
import json
import warnings
import argparse
from datetime import datetime, timedelta
from pathlib import Path

# Naive UTC datetimes intentionally match the DB's naive-UTC columns; silence
# the 3.12 utcnow() deprecation so cron logs stay clean.
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Make `app` importable when run as `python scripts/health_check.py` from backend/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings  # noqa: E402

# ---------------------------------------------------------------------------
# Config (env-overridable)
# ---------------------------------------------------------------------------
FAILED_THRESHOLD = int(os.getenv("HEALTHCHECK_FAILED_THRESHOLD", "5"))
LOOKBACK_HOURS = int(os.getenv("HEALTHCHECK_LOOKBACK_HOURS", "2"))
STUCK_MINUTES = int(os.getenv("HEALTHCHECK_STUCK_MINUTES", "30"))
# Upper bound so we only flag *recently* stuck videos, not multi-day zombie
# rows abandoned by past crashes (which would otherwise alert forever).
STUCK_WINDOW_HOURS = int(os.getenv("HEALTHCHECK_STUCK_WINDOW_HOURS", "24"))
QUEUE_THRESHOLD = int(os.getenv("HEALTHCHECK_QUEUE_THRESHOLD", "25"))
COOLDOWN_HOURS = int(os.getenv("HEALTHCHECK_COOLDOWN_HOURS", "3"))

_default_recipients = os.getenv("HEALTHCHECK_ALERT_EMAILS", settings.ADMIN_EMAILS)
ALERT_RECIPIENTS = [e.strip() for e in _default_recipients.split(",") if e.strip()]

STATE_FILE = Path(__file__).resolve().parent / ".health_state.json"


def log(msg: str) -> None:
    print(f"[{datetime.utcnow().isoformat(timespec='seconds')}Z] {msg}", flush=True)


# ---------------------------------------------------------------------------
# Individual checks. Each returns (ok: bool, alert_key: str, detail: str).
# ok=True means healthy; ok=False means fire an alert.
# ---------------------------------------------------------------------------
def _pg_dsn() -> str:
    """Convert the app's SQLAlchemy URL to a plain libpq DSN for psycopg."""
    dsn = settings.DATABASE_URL
    for prefix in ("postgresql+asyncpg://", "postgresql+psycopg://"):
        if dsn.startswith(prefix):
            return "postgresql://" + dsn[len(prefix):]
    return dsn


def check_failed_videos():
    import psycopg

    cutoff = datetime.utcnow() - timedelta(hours=LOOKBACK_HOURS)
    with psycopg.connect(_pg_dsn(), connect_timeout=10) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM videos "
                "WHERE status = 'FAILED' AND updated_at >= %s",
                (cutoff,),
            )
            count = cur.fetchone()[0]
            # Breakdown of *why* they failed — most useful line in the alert.
            cur.execute(
                "SELECT COALESCE(failure_reason, 'unknown') AS reason, COUNT(*) "
                "FROM videos WHERE status = 'FAILED' AND updated_at >= %s "
                "GROUP BY reason ORDER BY COUNT(*) DESC LIMIT 8",
                (cutoff,),
            )
            rows = cur.fetchall()

    if count >= FAILED_THRESHOLD:
        breakdown = "\n".join(f"    - {n}x  {reason}" for reason, n in rows)
        detail = (
            f"{count} videos FAILED in the last {LOOKBACK_HOURS}h "
            f"(threshold {FAILED_THRESHOLD}).\n  Top reasons:\n{breakdown}"
        )
        return False, "failed_videos", detail
    return True, "failed_videos", f"{count} failed in last {LOOKBACK_HOURS}h (ok)"


def check_stuck_processing():
    import psycopg

    now = datetime.utcnow()
    stale_after = now - timedelta(minutes=STUCK_MINUTES)      # stuck if older than this
    recent_since = now - timedelta(hours=STUCK_WINDOW_HOURS)  # but only within this window
    with psycopg.connect(_pg_dsn(), connect_timeout=10) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM videos "
                "WHERE status = 'PROCESSING' AND updated_at < %s AND updated_at >= %s",
                (stale_after, recent_since),
            )
            count = cur.fetchone()[0]

    if count > 0:
        detail = (
            f"{count} video(s) stuck in PROCESSING for >{STUCK_MINUTES} min "
            f"(within the last {STUCK_WINDOW_HOURS}h). Worker likely dead or wedged."
        )
        return False, "stuck_processing", detail
    return True, "stuck_processing", "0 recently stuck (ok)"


def check_queue_backlog():
    from redis import Redis
    from rq import Queue

    conn = Redis.from_url(settings.REDIS_URL, socket_connect_timeout=10)
    depth = Queue("video_processing", connection=conn).count

    if depth >= QUEUE_THRESHOLD:
        detail = (
            f"{depth} jobs queued in 'video_processing' (threshold {QUEUE_THRESHOLD}). "
            f"Worker not keeping up or down."
        )
        return False, "queue_backlog", detail
    return True, "queue_backlog", f"{depth} queued (ok)"


def check_openai():
    """1-token probe. Directly catches credit-exhaustion / bad key."""
    from openai import OpenAI

    try:
        client = OpenAI(api_key=settings.OPENAI_API_KEY, timeout=20)
        client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=1,
        )
        return True, "openai", "probe ok"
    except Exception as e:
        name = type(e).__name__
        msg = str(e)
        # insufficient_quota / RateLimitError / AuthenticationError are the
        # signatures of "credits dry" or "key revoked" — the Aug incident.
        detail = f"OpenAI probe FAILED ({name}): {msg[:300]}"
        return False, "openai", detail


CHECKS = [
    ("OpenAI API", check_openai),
    ("Failed videos", check_failed_videos),
    ("Stuck processing", check_stuck_processing),
    ("Queue backlog", check_queue_backlog),
]


# ---------------------------------------------------------------------------
# Cooldown state — don't re-alert the same issue every run.
# ---------------------------------------------------------------------------
def load_state() -> dict:
    try:
        return json.loads(STATE_FILE.read_text())
    except Exception:
        return {}


def save_state(state: dict) -> None:
    try:
        STATE_FILE.write_text(json.dumps(state, indent=2))
    except Exception as e:
        log(f"WARN: could not write state file: {e}")


def in_cooldown(state: dict, key: str) -> bool:
    ts = state.get(key)
    if not ts:
        return False
    try:
        last = datetime.fromisoformat(ts)
    except Exception:
        return False
    return datetime.utcnow() - last < timedelta(hours=COOLDOWN_HOURS)


# ---------------------------------------------------------------------------
# Alert email (Resend)
# ---------------------------------------------------------------------------
def send_alert(subject: str, body: str) -> bool:
    if not settings.RESEND_API_KEY:
        log("RESEND_API_KEY not set — cannot send alert. Body:\n" + body)
        return False
    import resend

    resend.api_key = settings.RESEND_API_KEY
    html = (
        "<div style='font-family:monospace;white-space:pre-wrap;font-size:14px;"
        "line-height:1.5'>" + body.replace("<", "&lt;") + "</div>"
    )
    try:
        resend.Emails.send({
            "from": f"NoteTube Alerts <hello@{settings.RESEND_FROM_DOMAIN}>",
            "to": ALERT_RECIPIENTS,
            "subject": subject,
            "text": body,
            "html": html,
        })
        log(f"Alert email sent to {', '.join(ALERT_RECIPIENTS)}")
        return True
    except Exception as e:
        log(f"ERROR: failed to send alert email: {e}")
        return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def run(verbose: bool = False) -> int:
    state = load_state()
    problems = []          # (label, detail) currently firing
    suppressed = []        # labels tripped but within cooldown

    for label, fn in CHECKS:
        try:
            ok, key, detail = fn()
        except Exception as e:
            ok, key, detail = False, f"error_{fn.__name__}", (
                f"{label} check itself errored: {type(e).__name__}: {e}"
            )
        if verbose or not ok:
            log(f"{'OK ' if ok else 'FAIL'} {label}: {detail}")
        if ok:
            state.pop(key, None)          # clear cooldown once healthy again
            continue
        if in_cooldown(state, key):
            suppressed.append(label)
            continue
        problems.append((label, detail))
        state[key] = datetime.utcnow().isoformat()

    if problems:
        lines = [
            "NoteTube AI health-check tripped on the following:",
            "",
        ]
        for label, detail in problems:
            lines.append(f"[{label}]\n  {detail}\n")
        lines.append(f"Host time (UTC): {datetime.utcnow().isoformat(timespec='seconds')}Z")
        lines.append(f"(repeat alerts for the same issue are suppressed for {COOLDOWN_HOURS}h)")
        subject = f"🚨 NoteTube alert: {', '.join(l for l, _ in problems)}"
        send_alert(subject, "\n".join(lines))

    if suppressed:
        log(f"Still failing but within cooldown (no email): {', '.join(suppressed)}")

    save_state(state)

    if problems:
        return 1
    if not suppressed:
        log("All checks healthy.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="NoteTube health-check")
    parser.add_argument("--test", action="store_true",
                        help="send a test alert email and exit")
    parser.add_argument("--verbose", action="store_true",
                        help="print every check's result")
    args = parser.parse_args()

    if args.test:
        ok = send_alert(
            "✅ NoteTube health-check test",
            "This is a test alert from scripts/health_check.py.\n"
            "If you're reading this, alert delivery works.\n"
            f"Recipients: {', '.join(ALERT_RECIPIENTS)}\n"
            f"Time (UTC): {datetime.utcnow().isoformat(timespec='seconds')}Z",
        )
        return 0 if ok else 2

    return run(verbose=args.verbose)


if __name__ == "__main__":
    sys.exit(main())
