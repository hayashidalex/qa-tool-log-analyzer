from collections import defaultdict
from datetime import datetime, timedelta

import plotly.graph_objs as go
import plotly.io as pio


def generate_graph(metrics):
    dates = list(metrics.keys())
    vals = list(metrics.values())
    fig = go.Figure(data=go.Scatter(x=dates, y=vals, mode='lines+markers', name='Queries'))
    fig.update_layout(
        title='Number of Queries',
        xaxis_title='Date',
        yaxis_title='Count',
        template='plotly_white',
        height=400,
        margin=dict(l=40, r=40, t=40, b=40)
    )
    return pio.to_html(fig, full_html=False)


def get_week_range(year, week_num):
    start_of_year = datetime(year, 1, 1)
    start_of_week = start_of_year + timedelta(weeks=week_num - 1)
    start_of_week -= timedelta(days=start_of_week.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    return start_of_week.strftime('%Y-%m-%d'), end_of_week.strftime('%Y-%m-%d')


def calculate_metrics(logs, view_by):
    metrics = defaultdict(int)
    for log in logs:
        dt_str = log['timestamp'].split(' ')[0]
        dt = datetime.strptime(dt_str, '%Y-%m-%d')
        if view_by == 'daily':
            key = dt.strftime('%Y-%m-%d')
        elif view_by == 'weekly':
            y, w = dt.isocalendar()[:2]
            start, end = get_week_range(y, w)
            key = f"{start} - {end}"
        else:  # monthly
            key = dt.strftime('%Y-%m')
        metrics[key] += 1

    if view_by == 'weekly':
        return dict(sorted(
            metrics.items(),
            key=lambda x: datetime.strptime(x[0].split(' - ')[0], '%Y-%m-%d')
        ))
    return dict(sorted(metrics.items(), key=lambda x: x[0]))


def is_reviewed(log):
    if not log.get('is_independent_question'):
        return False
    if log['is_independent_question'] == 'No':
        return True
    return bool(
        log.get('response_review') and
        log.get('query_review') and
        log.get('urls_review')
    )


def cnt(reviewed_logs, field, val):
    return sum(1 for l in reviewed_logs if l.get(field) == val)


def pct(x, base):
    return round(x / base * 100, 1) if base > 0 else 0


def calculate_model_metrics(logs):
    models = {log['model'] for log in logs}
    models_metrics = {}
    for model in models:
        model_logs = [l for l in logs if l['model'] == model]
        reviewed_logs = [l for l in model_logs if is_reviewed(l)]
        models_metrics[model] = {
            'Not Reviewed': len(model_logs) - len(reviewed_logs),
            'Excellent': cnt(reviewed_logs, 'response_review', 'Excellent'),
            'Good': cnt(reviewed_logs, 'response_review', 'Good'),
            'Satisfactory': cnt(reviewed_logs, 'response_review', 'Satisfactory'),
            'Unsatisfactory': cnt(reviewed_logs, 'response_review', 'Unsatisfactory'),
        }
    return models_metrics


def calculate_review_counts(logs):
    total = len(logs)
    reviewed_logs = [l for l in logs if is_reviewed(l)]
    not_reviewed_logs = [l for l in logs if not is_reviewed(l)]
    indep_yes = sum(1 for l in reviewed_logs if l['is_independent_question'] == 'Yes')
    indep_no = sum(1 for l in reviewed_logs if l['is_independent_question'] == 'No')

    return {
        'total': total,
        'reviewed': len(reviewed_logs),
        'not_reviewed': len(not_reviewed_logs),
        'indep_yes': indep_yes,
        'indep_no': indep_no,
        'resp_excellent': cnt(reviewed_logs, 'response_review', 'Excellent'),
        'resp_good': cnt(reviewed_logs, 'response_review', 'Good'),
        'resp_satisfactory': cnt(reviewed_logs, 'response_review', 'Satisfactory'),
        'resp_unsatisfactory': cnt(reviewed_logs, 'response_review', 'Unsatisfactory'),
        'resp_not_sure': cnt(reviewed_logs, 'response_review', 'Not Sure'),
        'query_relevant': cnt(reviewed_logs, 'query_review', 'Relevant'),
        'query_irrelevant': cnt(reviewed_logs, 'query_review', 'Irrelevant'),
        'query_violation': cnt(reviewed_logs, 'query_review', 'Violation'),
        'query_badly_formed': cnt(reviewed_logs, 'query_review', 'Badly Formed'),
        'query_not_sure': cnt(reviewed_logs, 'query_review', 'Not Sure'),
        'urls_good': cnt(reviewed_logs, 'urls_review', 'Good'),
        'urls_acceptable': cnt(reviewed_logs, 'urls_review', 'Acceptable'),
        'urls_bad': cnt(reviewed_logs, 'urls_review', 'Bad'),
        'urls_idk': cnt(reviewed_logs, 'urls_review', "I Don't Know"),
    }


def build_metrics_summary(rc):
    """Build the metrics_summary dict from a calculate_review_counts result."""
    total = rc['total']
    reviewed = rc['reviewed']
    not_rev = rc['not_reviewed']
    p_rev = pct(reviewed, total)
    p_not_rev = pct(not_rev, total)

    indep_yes = rc['indep_yes']
    indep_no = rc['indep_no']
    yn_sum = indep_yes + indep_no
    yes_pct = pct(indep_yes, yn_sum)
    no_pct = pct(indep_no, yn_sum)

    r_excel = rc['resp_excellent']
    r_good = rc['resp_good']
    r_sat = rc['resp_satisfactory']
    r_unsat = rc['resp_unsatisfactory']
    r_not_sure = rc['resp_not_sure']
    sum_resp = r_excel + r_good + r_sat + r_unsat + r_not_sure

    q_relevant = rc['query_relevant']
    q_irrelevant = rc['query_irrelevant']
    q_violation = rc['query_violation']
    q_badly_formed = rc['query_badly_formed']
    q_not_sure = rc['query_not_sure']
    sum_q = q_relevant + q_irrelevant + q_violation + q_badly_formed + q_not_sure

    u_good = rc['urls_good']
    u_acc = rc['urls_acceptable']
    u_bad = rc['urls_bad']
    u_idk = rc['urls_idk']
    sum_u = u_good + u_acc + u_bad + u_idk

    return {
        'overall': (
            f"Total Queries: {total} (100%), "
            f"Reviewed: {reviewed} ({p_rev}%), "
            f"Not Reviewed: {not_rev} ({p_not_rev}%)"
        ),
        'independent': (
            f"Is this an independent question for the QA tool? "
            f"Yes: {indep_yes} ({yes_pct}%), No: {indep_no} ({no_pct}%)"
        ),
        'response': (
            f"Response Review (Reviewed + Independent=Yes): "
            f"Excellent: {r_excel} ({pct(r_excel, sum_resp)}%), "
            f"Good: {r_good} ({pct(r_good, sum_resp)}%), "
            f"Satisfactory: {r_sat} ({pct(r_sat, sum_resp)}%), "
            f"Unsatisfactory: {r_unsat} ({pct(r_unsat, sum_resp)}%), "
            f"Not Sure: {r_not_sure} ({pct(r_not_sure, sum_resp)}%)"
        ),
        'query': (
            f"Query Review (Reviewed + Independent=Yes): "
            f"Relevant: {q_relevant} ({pct(q_relevant, sum_q)}%), "
            f"Irrelevant: {q_irrelevant} ({pct(q_irrelevant, sum_q)}%), "
            f"Violation: {q_violation} ({pct(q_violation, sum_q)}%), "
            f"Badly Formed: {q_badly_formed} ({pct(q_badly_formed, sum_q)}%), "
            f"Not Sure: {q_not_sure} ({pct(q_not_sure, sum_q)}%)"
        ),
        'urls': (
            f"URLs in Response Review (Reviewed + Independent=Yes): "
            f"Good: {u_good} ({pct(u_good, sum_u)}%), "
            f"Acceptable: {u_acc} ({pct(u_acc, sum_u)}%), "
            f"Bad: {u_bad} ({pct(u_bad, sum_u)}%), "
            f"I Don't Know: {u_idk} ({pct(u_idk, sum_u)}%)"
        ),
    }


def get_paginated_logs(logs, page, per_page):
    start = (page - 1) * per_page
    return logs[start:start + per_page]
