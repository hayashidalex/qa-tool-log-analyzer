import os
import re
import logging

from config import LOG_DIR

logger = logging.getLogger(__name__)


def read_logs_from_files():
    log_entries = []
    logger.info(f"Scanning log directory: {LOG_DIR}")

    for filename in sorted(os.listdir(LOG_DIR), reverse=True):
        filepath = os.path.join(LOG_DIR, filename)
        if not filename.endswith('_query.log'):
            continue

        logger.info(f"Reading log file: {filepath}")
        try:
            with open(filepath, 'r') as f:
                content = f.read()
                log_entries.extend(parse_log(content))
        except Exception as e:
            logger.error(f"Error processing file {filepath}: {e}")

    logger.info(f"Total log entries found: {len(log_entries)}")
    return log_entries


_TOOL_ALIASES = {
    'qa': 'Q&A',
    'q&a': 'Q&A',
    'code generation': 'Code Generation',
    'code gen': 'Code Generation',
    'codegen': 'Code Generation',
}

def _normalize_tool(raw):
    return _TOOL_ALIASES.get(raw.lower(), raw)


def parse_log(content):
    pattern = re.compile(
        r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) - QUERY: (.*?)\nRESPONSE:\s+(.*?)\s+MODEL:\s+(?:[^\n]*)\nTOOL: ([^\n]*)(?:\nTESTER: ([^\n]*))?(?=\n\d{4}-\d{2}-\d{2}|\Z)',
        re.DOTALL | re.MULTILINE
    )
    entries = []
    for match in pattern.finditer(content):
        ts_str = match.group(1)
        response = match.group(3).strip()
        response = re.sub(r'\n#+\s*$', '', response)
        tool = match.group(4).strip()
        tool = _normalize_tool(tool)
        entries.append({
            'timestamp': ts_str,
            'query': match.group(2).strip(),
            'response': response,
            'tool': tool,
            'tester': match.group(5).strip() if match.group(5) else '',
            'is_independent_question': '',
            'response_review': '',
            'query_review': '',
            'urls_review': ''
        })
    return entries
