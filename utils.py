import datetime
import pytz
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(), logging.FileHandler('bot.log')]
)


def convert_to_local_tz(old_ts, tz="Africa/Lagos"):
    """Convert UTC timestamp to local timezone (WAT)."""
    if not old_ts:
        return None
    try:
        dt_obj = datetime.datetime.fromisoformat(old_ts.replace('Z', '+00:00'))
        old_tz = pytz.timezone("UTC")
        new_tz = pytz.timezone(tz)
        localized = old_tz.localize(dt_obj.replace(tzinfo=None))
        return localized.astimezone(new_tz)
    except ValueError as e:
        logging.error(f"Timezone conversion failed for {old_ts}: {e}")
        return None
