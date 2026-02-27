import os
import re
import logging
from datetime import datetime

from config import LOG_DIR

logger = logging.getLogger(__name__)


def read_logs_from_files():
    log_entries = []
    start_date = datetime.min
    end_date = datetime.now()
    logger.info(f"Scanning log directory: {LOG_DIR}")

    for filename in sorted(os.listdir(LOG_DIR), reverse=True):
        filepath = os.path.join(LOG_DIR, filename)
        if not filename.endswith('_query.log'):
            logger.info(f"Skipping file: {filename}")
            continue

        logger.info(f"Reading log file: {filepath}")
        try:
            with open(filepath, 'r') as f:
                content = f.read()
                log_entries.extend(parse_log(content, start_date, end_date))
        except Exception as e:
            logger.error(f"Error processing file {filepath}: {e}")

    try:
        log_entries = sorted(
            log_entries,
            key=lambda x: datetime.strptime(x['timestamp'], '%Y-%m-%d %H:%M:%S,%f'),
            reverse=True
        )
    except Exception as e:
        logger.error(f"Error sorting log entries: {e}")

    logger.info(f"Total log entries found: {len(log_entries)}")
    return log_entries


def parse_log(content, start_date, end_date):
    pattern = re.compile(
        r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) - QUERY: (.*?)\nRESPONSE:\s+(.*?)(?:\n+|\s+)MODEL:\s+(.*?)\nTOOL: (.*?)(?:\nTESTER: (.*?))?(?=\n\d{4}-\d{2}-\d{2}|\Z)',
        re.DOTALL | re.MULTILINE
    )
    matches = pattern.finditer(content)
    entries = []
    for match in matches:
        ts_str = match.group(1)
        try:
            ts = datetime.strptime(ts_str, '%Y-%m-%d %H:%M:%S,%f')
        except ValueError:
            continue
        if start_date <= ts <= end_date:
            response = match.group(3).strip()
            response = re.sub(r'\n#+\s*$', '', response)
            entries.append({
                'timestamp': ts_str,
                'query': match.group(2).strip(),
                'response': response,
                'tool': match.group(5).strip(),
                'tester': match.group(6).strip() if match.group(6) else '',
                'is_independent_question': '',
                'response_review': '',
                'query_review': '',
                'urls_review': ''
            })
    return entries
