import sqlite3
from datetime import datetime, timedelta

import bleach
import markdown
from flask import (
    Blueprint, request, render_template, session,
    redirect, url_for, jsonify, flash, current_app
)
from markupsafe import Markup, escape

from app_auth import login_required
from config import DB_FILE, PER_PAGE, ALLOWED_TAGS, ALLOWED_ATTRIBUTES
from db import get_logs, insert_log
from log_parser import read_logs_from_files
from metrics import (
    calculate_metrics, calculate_review_counts, build_metrics_summary,
    generate_graph, get_paginated_logs, pct
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
    page = int(request.args.get('page', 1))

    selected_tool = request.args.get('tool', 'All')
    selected_independent = request.args.get('independent', 'All')
    selected_response_review = request.args.getlist('response_review')
    selected_query_review = request.args.getlist('query_review')
    selected_urls_review = request.args.getlist('urls_review')
    selected_review_status = request.args.get('review_status', 'All')

    all_entries = get_logs(
        start_date, end_date,
        tool=selected_tool,
        independent=selected_independent,
        response_reviews=selected_response_review,
        query_reviews=selected_query_review,
        urls_reviews=selected_urls_review,
        review_status=selected_review_status,
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
            log['response'] = bleach.clean(
                log['response'],
                tags=ALLOWED_TAGS,
                attributes=ALLOWED_ATTRIBUTES,
                strip=True
            )
            log['response'] = markdown.markdown(log['response'])
        else:
            log['response'] = '(No Response Provided)'

    mets = calculate_metrics(all_entries, view_by)
    rc = calculate_review_counts(all_entries)
    metrics_summary = build_metrics_summary(rc)

    def param_escape(v):
        return v.replace('&', '%26').replace('=', '%3D').replace(' ', '+')

    param_str = (
        f"&start_date={param_escape(start_date)}"
        f"&end_date={param_escape(end_date)}"
        f"&view_by={param_escape(view_by)}"
        f"&independent={param_escape(selected_independent)}"
        f"&review_status={param_escape(selected_review_status)}"
    )
    for rr in selected_response_review:
        param_str += f"&response_review={param_escape(rr)}"
    for qr in selected_query_review:
        param_str += f"&query_review={param_escape(qr)}"
    for ur in selected_urls_review:
        param_str += f"&urls_review={param_escape(ur)}"

    return render_template(
        'index.html',
        logs=paginated_logs,
        total_logs=total_logs,
        graph_html=generate_graph(mets),
        metrics_text=[f"{k}: {v} queries" for k, v in mets.items()],
        metrics_summary=metrics_summary,
        filter_summary_message=Markup('<h3>Total Queries in Selected Range</h3>'),
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
        response_review_options=['Excellent', 'Good', 'Satisfactory', 'Unsatisfactory', 'Not Sure'],
        query_review_options=['Relevant', 'Irrelevant', 'Violation', 'Badly Formed', 'Not Sure'],
        urls_review_options=['Good', 'Acceptable', 'Bad', "I Don't Know"],
        page=page,
        total_pages=total_pages,
        next_page=next_page,
        prev_page=prev_page,
        param_str=param_str,
        read_only=session.get('read_only', False),
        review_counts=rc,
    )


@main_bp.route('/update_entry', methods=['POST'])
def update_entry():
    if session.get('read_only'):
        return jsonify({'status': 'error', 'message': 'Read-only users cannot update entries.'}), 403

    try:
        data = request.json
        log_id = data['id']

        with sqlite3.connect(DB_FILE) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("""
                SELECT is_independent_question AS independent,
                       response_review        AS response,
                       query_review           AS query,
                       urls_review            AS urls
                  FROM logs
                 WHERE id=?
            """, (log_id,))
            old = dict(cur.fetchone())

        new = {
            'independent': data.get('is_independent_question', ''),
            'response':    data.get('response_review', ''),
            'query':       data.get('query_review', ''),
            'urls':        data.get('urls_review', ''),
            'notes':       data.get('notes', ''),
        }

        if new['independent'] == 'No':
            new.update({'response': '', 'query': '', 'urls': ''})

        reviewer = session.get('user_id', 'anonymous')
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        with sqlite3.connect(DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute("""
                UPDATE logs
                   SET is_independent_question=?,
                       response_review=?,
                       query_review=?,
                       urls_review=?,
                       notes=?,
                       last_updated_by=?,
                       last_updated_at=?
                 WHERE id=?
            """, (
                new['independent'], new['response'], new['query'],
                new['urls'], new['notes'], reviewer, ts, log_id
            ))
            conn.commit()

        changed = [k for k in old if old[k] != new[k]]
        msg = f"Record {log_id} updated: fields changed = {', '.join(changed) or 'none'}"
        print(msg)
        current_app.logger.info(msg)

        return jsonify({'status': 'success', 'last_updated_at': ts, 'last_updated_by': reviewer})

    except Exception as e:
        err = f"Error updating record {data.get('id')}: {e}"
        print(err)
        current_app.logger.error(err, exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500


@main_bp.route('/get_metrics', methods=['GET'])
def get_metrics_endpoint():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    view_by = request.args.get('view_by', 'daily')

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
    metrics_summary = build_metrics_summary(rc)

    return jsonify({
        'metrics_summary': metrics_summary,
        'review_counts': {
            'total':       rc['total'],
            'reviewed':    rc['reviewed'],
            'not_reviewed': rc['not_reviewed'],
        }
    })


@main_bp.route('/update_table', methods=['POST'])
def update_table():
    latest_logs = read_logs_from_files()
    with sqlite3.connect(DB_FILE) as conn:
        for log in latest_logs:
            insert_log(conn, log)
    return jsonify({'status': 'ok'})
