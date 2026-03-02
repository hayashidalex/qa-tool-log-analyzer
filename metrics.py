from collections import defaultdict
from datetime import date, datetime, timedelta

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
    return pio.to_html(fig, full_html=False, include_plotlyjs=False)




def get_week_range(year, week_num):
    start = date.fromisocalendar(year, week_num, 1)
    end = start + timedelta(days=6)
    return start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d')


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



def calculate_review_counts(logs):
    total = len(logs)
    reviewed_logs = [l for l in logs if is_reviewed(l)]
    indep_yes = sum(1 for l in reviewed_logs if l['is_independent_question'] == 'Yes')
    indep_no = sum(1 for l in reviewed_logs if l['is_independent_question'] == 'No')

    return {
        'total': total,
        'reviewed': len(reviewed_logs),
        'not_reviewed': total - len(reviewed_logs),
        'indep_yes': indep_yes,
        'indep_no': indep_no,
        'resp_excellent': cnt(reviewed_logs, 'response_review', 'Excellent'),
        'resp_satisfactory': cnt(reviewed_logs, 'response_review', 'Satisfactory'),
        'resp_unsatisfactory': cnt(reviewed_logs, 'response_review', 'Unsatisfactory'),
        'resp_not_sure': cnt(reviewed_logs, 'response_review', 'Not Sure'),
        'query_relevant': cnt(reviewed_logs, 'query_review', 'Relevant'),
        'query_irrelevant': cnt(reviewed_logs, 'query_review', 'Irrelevant'),
        'query_violation': cnt(reviewed_logs, 'query_review', 'Violation'),
        'query_unclear': cnt(reviewed_logs, 'query_review', 'Unclear'),
        'query_not_sure': cnt(reviewed_logs, 'query_review', 'Not Sure'),
        'urls_good': cnt(reviewed_logs, 'urls_review', 'Good'),
        'urls_acceptable': cnt(reviewed_logs, 'urls_review', 'Acceptable'),
        'urls_bad': cnt(reviewed_logs, 'urls_review', 'Bad'),
        'urls_idk': cnt(reviewed_logs, 'urls_review', "I Don't Know"),
    }


def get_paginated_logs(logs, page, per_page):
    start = (page - 1) * per_page
    return logs[start:start + per_page]
