"""
Observability — Sentry error tracking.

A single init used by both the API (app/main.py) and the RQ worker
(app/workers/video_processor.py). Fully a no-op when SENTRY_DSN is unset, so
importing/calling this is always safe in every environment.

sentry-sdk auto-enables its FastAPI/Starlette and RQ integrations when those
libraries are present, so we don't wire integrations by hand.
"""
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

_initialized = False


def init_sentry(component: str = "backend") -> bool:
    """
    Initialize Sentry once for this process.

    Args:
        component: "backend" (API) or "worker" — tagged on every event so you
                   can tell API errors from background-job errors in Sentry.

    Returns:
        True if Sentry was initialized, False if skipped (no DSN) or failed.
    """
    global _initialized
    if _initialized:
        return True
    if not settings.SENTRY_DSN:
        logger.info("SENTRY_DSN not set — error tracking disabled (%s)", component)
        return False

    try:
        import sentry_sdk

        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            environment=settings.ENVIRONMENT,
            traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
            send_default_pii=False,  # don't ship user emails/tokens to Sentry
        )
        sentry_sdk.set_tag("component", component)
        _initialized = True
        logger.info("Sentry initialized (component=%s, env=%s)", component, settings.ENVIRONMENT)
        return True
    except Exception as e:  # never let telemetry break the app
        logger.warning("Sentry init failed (%s): %s", component, e)
        return False
