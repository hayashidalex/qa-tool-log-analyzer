import sqlite3
from datetime import datetime, timedelta
from urllib.parse import urlencode

import bleach
import markdown
from flask import (
    Blueprint, request, render_template, session,
    redirect, url_for, jsonify, flash, current_app
)
from markupsafe import escape

from app_auth import login_required
from config import DB_FILE, PER_PAGE, ALLOWED_TAGS, ALLOWED_ATTRIBUTES
from db import get_logs, insert_log
from log_parser import read_logs_from_files
from metrics import (
    calculate_metrics, calculate_review_counts,
    generate_graph, get_paginated_logs
)

main_bp = Blueprint('main', __name__)


@main_bp.route('/', methods=['GET'])
@login_required
def home_route():
    today = datetime.now().strftime('%Y-%m-%d')
    seven_days_ago = (datetime.now() - timedelta(days=6)).strftime('%Y-%m-%d')
    start_date = request.args.get('start_date', seven_days_ago)
    end_date = request.args.get('end_date', today)
    view_by = request.args.get('view_by', 'daily')
    try:
        page = max(1, int(request.args.get('page', 1)))
    except (ValueError, TypeError):
        page = 1

    selected_tool = request.args.get('tool', 'Q&A')
    selected_independent = request.args.get('independent', 'All')
    selected_response_review = request.args.getlist('response_review')
    selected_query_review = request.args.getlist('query_review')
    selected_urls_review = request.args.getlist('urls_review')
    selected_review_status = request.args.get('review_status', 'All')
    show_others_only = request.args.get('reviewed_by_others', '')

    all_entries = get_logs(
        start_date, end_date,
        tool=selected_tool,
        independent=selected_independent,
        response_reviews=selected_response_review,
        query_reviews=selected_query_review,
        urls_reviews=selected_urls_review,
        review_status=selected_review_status,
        reviewed_by_others=session.get('user_id') if show_others_only == 'on' else None,
    )

    total_logs = len(all_entries)
    paginated_logs = get_paginated_logs(all_entries, page, PER_PAGE)
    total_pages = (total_logs + PER_PAGE - 1) // PER_PAGE
    next_page = page + 1 if page < total_pages else None
    prev_page = page - 1 if page > 1 else None

    for log in paginated_logs:
        if not log.get('query', '').strip():
            log['query'] = '(No Query Provided)'
        else:
            log['query'] = escape(log['query'])
        if log.get('response'):
            log['response'] = markdown.markdown(log['response'])
            log['response'] = bleach.clean(
                log['response'],
                tags=ALLOWED_TAGS,
                attributes=ALLOWED_ATTRIBUTES,
                strip=True
            )
        else:
            log['response'] = '(No Response Provided)'

    mets = calculate_metrics(all_entries, view_by)
    rc = calculate_review_counts(all_entries)

    params = [
        ('start_date', start_date),
        ('end_date', end_date),
        ('view_by', view_by),
        ('tool', selected_tool),
        ('independent', selected_independent),
        ('review_status', selected_review_status),
    ]
    params += [('response_review', rr) for rr in selected_response_review]
    params += [('query_review', qr) for qr in selected_query_review]
    params += [('urls_review', ur) for ur in selected_urls_review]
    if show_others_only == 'on':
        params.append(('reviewed_by_others', 'on'))
    param_str = '&' + urlencode(params)

    return render_template(
        'index.html',
        logs=paginated_logs,
        total_logs=total_logs,
        graph_html=generate_graph(mets),
        start_date=start_date,
        end_date=end_date,
        view_by=view_by,
        selected_tool=selected_tool,
        selected_independent=selected_independent,
        selected_response_review=selected_response_review,
        selected_query_review=selected_query_review,
        selected_urls_review=selected_urls_review,
        selected_review_status=selected_review_status,
        review_status_options=['All', 'Reviewed', 'Not Reviewed'],
        tool_options=['All', 'Code Generation', 'Q&A'],
        is_independent_options=['All', 'Yes', 'No'],
        response_review_options=['Excellent', 'Satisfactory', 'Unsatisfactory', 'Not Sure'],
        query_review_options=['Relevant', 'Irrelevant', 'Violation', 'Unclear', 'Not Sure'],
        urls_review_options=['Good', 'Acceptable', 'Bad', "I Don't Know"],
        page=page,
        per_page=PER_PAGE,
        total_pages=total_pages,
        next_page=next_page,
        prev_page=prev_page,
        param_str=param_str,
        read_only=session.get('read_only', False),
        review_counts=rc,
        show_others_only=show_others_only,
    )


@main_bp.route('/update_entry', methods=['POST'])
@login_required
def update_entry():
    if session.get('read_only'):
        return jsonify({'status': 'error', 'message': 'Read-only users cannot update entries.'}), 403

    try:
        data = request.json
        log_id = data['id']
        independent = data.get('is_independent_question', '')
        reviewer = session.get('user_id', 'anonymous')
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        response_review = data.get('response_review', '') if independent != 'No' else ''
        query_review    = data.get('query_review', '')    if independent != 'No' else ''
        urls_review     = data.get('urls_review', '')     if independent != 'No' else ''

        with sqlite3.connect(DB_FILE) as conn:
            conn.cursor().execute("""
                UPDATE logs
                   SET is_independent_question=?,
                       response_review=?,
                       query_review=?,
                       urls_review=?,
                       notes=?,
                       last_updated_by=?,
                       last_updated_at=?
                 WHERE id=?
            """, (independent, response_review, query_review, urls_review,
                  data.get('notes', ''), reviewer, ts, log_id))

        current_app.logger.info(f"Record {log_id} updated by {reviewer}")
        return jsonify({'status': 'success', 'last_updated_at': ts, 'last_updated_by': reviewer})

    except Exception as e:
        current_app.logger.error(f"Error updating record {data.get('id')}: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500


@main_bp.route('/get_metrics', methods=['GET'])
@login_required
def get_metrics_endpoint():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    rows = get_logs(
        start_date, end_date,
        tool=request.args.get('tool', 'All'),
        independent=request.args.get('independent', 'All'),
        response_reviews=request.args.getlist('response_review'),
        query_reviews=request.args.getlist('query_review'),
        urls_reviews=request.args.getlist('urls_review'),
        review_status=request.args.get('review_status', 'All'),
    )

    rc = calculate_review_counts(rows)

    return jsonify({
        'review_counts': {
            'total':        rc['total'],
            'reviewed':     rc['reviewed'],
            'not_reviewed': rc['not_reviewed'],
        },
    })


@main_bp.route('/update_table', methods=['POST'])
@login_required
def update_table():
    if session.get('read_only'):
        return jsonify({'status': 'error', 'message': 'Read-only users cannot update the table.'}), 403
    latest_logs = read_logs_from_files()
    with sqlite3.connect(DB_FILE) as conn:
        for log in latest_logs:
            insert_log(conn, log)
    return jsonify({'status': 'ok'})
