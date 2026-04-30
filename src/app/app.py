from __future__ import annotations

from collections.abc import Sequence
from typing import Any, cast

import dash
import dash_bootstrap_components as dbc  # type: ignore[import-untyped]
import pandas as pd  # type: ignore[import-untyped]
import plotly.express as px  # type: ignore[import-untyped]
from dash import Input, Output, State, callback, dcc, html
from dash.dash_table import DataTable as DashDataTableType

try:
    from app.backend import backend
    from app.models import ActionRecommendation, HighRiskCustomer, SegmentSummary
except ModuleNotFoundError:  # pragma: no cover - supports direct `python app.py` execution
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from app.backend import backend
    from app.models import ActionRecommendation, HighRiskCustomer, SegmentSummary

CHURN_CATEGORY_COLOR_MAP = {
    "High": "#dc3545",
    "Medium": "#f0ad4e",
    "Low": "#198754",
}
PERSONA_BAR_COLOR = "#5bc0de"
GENRE_BAR_COLOR = "#9b59b6"
SUBSCRIPTION_COLOR_MAP = {
    "Subscribed": "#20c997",
    "No Subscription": "#6c757d",
}


def _load_startup_data() -> tuple[list[HighRiskCustomer], SegmentSummary, list[ActionRecommendation]]:
    customers = backend.get_high_risk_customers()
    summary = backend.get_segment_summary()
    recommendations = backend.get_recommendations()
    return customers, summary, recommendations


def _customer_full_name(customer: HighRiskCustomer) -> str:
    return " ".join(part for part in [customer.first_name, customer.last_name] if part) or "Unknown"


def _subscription_status(customer: HighRiskCustomer) -> str:
    if customer.has_subscription:
        if customer.current_subscription_tier:
            return f"Active \u00b7 {customer.current_subscription_tier}"
        return "Active"
    return "Inactive"


def _watch_hours(customer: HighRiskCustomer) -> float:
    return round((customer.total_watch_seconds or 0) / 3600, 2)


def _customer_row(customer: HighRiskCustomer) -> dict[str, Any]:
    return {
        "Name": _customer_full_name(customer),
        "Email": customer.email or "\u2014",
        "Persona": customer.persona or "Unknown",
        "Churn Risk Score": round(customer.churn_risk_score, 2),
        "Churn Risk Category": customer.churn_risk_category,
        "Days Since Last Engagement": customer.days_since_last_engagement or 0,
        "Watch Hours": _watch_hours(customer),
        "Content Viewed": customer.unique_content_viewed or 0,
        "Subscription Status": _subscription_status(customer),
    }


def _filter_customers(
    customers: Sequence[HighRiskCustomer],
    churn_categories: Sequence[str] | None,
    personas: Sequence[str] | None,
) -> list[HighRiskCustomer]:
    selected_categories = set(churn_categories or [])
    selected_personas = set(personas or [])

    filtered = []
    for customer in customers:
        if selected_categories and customer.churn_risk_category not in selected_categories:
            continue
        if selected_personas and (customer.persona or "Unknown") not in selected_personas:
            continue
        filtered.append(customer)
    return filtered


def _dropdown_options(values: Sequence[str]) -> list[dict[str, str]]:
    return [{"label": value, "value": value} for value in values]


def _metric_card(title: str, value: str, accent_class: str) -> dbc.Card:
    return dbc.Card(
        dbc.CardBody(
            [
                html.Div(title, className="text-uppercase text-muted small fw-semibold mb-2"),
                html.H3(value, className="mb-0 text-white"),
            ]
        ),
        class_name=f"h-100 border-0 shadow-sm {accent_class}",
    )


def _build_summary_figures(summary: SegmentSummary) -> tuple[Any, Any, Any, Any]:
    churn_pie = px.pie(
        names=list(summary.churn_risk_category_distribution.keys()),
        values=list(summary.churn_risk_category_distribution.values()),
        hole=0.45,
        color=list(summary.churn_risk_category_distribution.keys()),
        color_discrete_map=CHURN_CATEGORY_COLOR_MAP,
    )
    churn_pie.update_layout(
        template="plotly_dark",
        title="Churn Risk Categories",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend_title_text="Category",
        margin=dict(l=20, r=20, t=48, b=20),
    )

    persona_bar = px.bar(
        x=list(summary.persona_distribution.keys()),
        y=list(summary.persona_distribution.values()),
        labels={"x": "Persona", "y": "Customers"},
        text_auto=True,
    )
    persona_bar.update_traces(marker_color=PERSONA_BAR_COLOR)
    persona_bar.update_layout(
        template="plotly_dark",
        title="Persona Distribution",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=20, r=20, t=48, b=20),
    )

    top_genres = summary.top_genres or []
    genre_bar = px.bar(
        x=[count for _, count in top_genres],
        y=[genre for genre, _ in top_genres],
        orientation="h",
        labels={"x": "Customers", "y": "Genre"},
        text_auto=True,
    )
    genre_bar.update_traces(marker_color=GENRE_BAR_COLOR)
    genre_bar.update_layout(
        template="plotly_dark",
        title="Top Genres",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=20, r=20, t=48, b=20),
        yaxis={"categoryorder": "total ascending"},
    )

    subscription_counts = {
        "Subscribed": summary.subscription_status_breakdown.get(True, 0),
        "No Subscription": summary.subscription_status_breakdown.get(False, 0),
    }
    subscription_pie = px.pie(
        names=list(subscription_counts.keys()),
        values=list(subscription_counts.values()),
        hole=0.45,
        color=list(subscription_counts.keys()),
        color_discrete_map=SUBSCRIPTION_COLOR_MAP,
    )
    subscription_pie.update_layout(
        template="plotly_dark",
        title="Subscription Status",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend_title_text="Status",
        margin=dict(l=20, r=20, t=48, b=20),
    )

    return churn_pie, persona_bar, genre_bar, subscription_pie


def _recommendation_card(recommendation: ActionRecommendation) -> dbc.Card:
    card_class = "border-success bg-success bg-opacity-10" if recommendation.is_triggered else "border-secondary"
    badge_color = "success" if recommendation.is_triggered else "secondary"
    badge_text = "Met" if recommendation.is_triggered else "Not met"
    indicator = "\u25cf"

    return dbc.Card(
        dbc.CardBody(
            [
                html.Div(
                    [
                        html.H4(recommendation.rule_name, className="mb-0 text-white"),
                        dbc.Badge(f"{indicator} {badge_text}", color=badge_color, pill=True, class_name="ms-2"),
                    ],
                    className="d-flex justify-content-between align-items-center gap-2 flex-wrap",
                ),
                html.P(recommendation.recommendation, className="mt-3 mb-2 fs-5"),
                html.P(recommendation.rationale, className="text-muted mb-0"),
            ]
        ),
        class_name=f"h-100 shadow-sm {card_class}",
    )


def _build_layout(
    customers: Sequence[HighRiskCustomer],
    summary: SegmentSummary,
    recommendations: Sequence[ActionRecommendation],
) -> dbc.Container:
    churn_options = sorted({customer.churn_risk_category for customer in customers})
    persona_options = sorted({customer.persona or "Unknown" for customer in customers})
    churn_pie, persona_bar, genre_bar, subscription_pie = _build_summary_figures(summary)

    return dbc.Container(
        [
            dcc.Store(id="customer-store", data=[customer.model_dump() for customer in customers]),
            html.Div(
                [
                    html.P("Paramount+ Retention Command Center", className="text-uppercase text-info fw-semibold mb-2"),
                    html.H1("High Churn Risk Customer Dashboard", className="display-5 fw-bold mb-2"),
                    html.P(
                        "Monitor at-risk subscribers, understand segment patterns, and activate the right retention playbooks.",
                        className="lead text-muted mb-0",
                    ),
                ],
                className="py-4",
            ),
            dbc.Tabs(
                [
                    dbc.Tab(
                        label="High-Risk Customers",
                        tab_id="customers-tab",
                        children=[
                            dbc.Card(
                                dbc.CardBody(
                                    [
                                        dbc.Row(
                                            [
                                                dbc.Col(
                                                    [
                                                        dbc.Label("Filter by churn risk category", html_for="category-filter"),
                                                        dcc.Dropdown(
                                                            id="category-filter",
                                                            options=_dropdown_options(churn_options),
                                                            multi=True,
                                                            placeholder="All categories",
                                                        ),
                                                    ],
                                                    md=4,
                                                ),
                                                dbc.Col(
                                                    [
                                                        dbc.Label("Filter by persona", html_for="persona-filter"),
                                                        dcc.Dropdown(
                                                            id="persona-filter",
                                                            options=_dropdown_options(persona_options),
                                                            multi=True,
                                                            placeholder="All personas",
                                                        ),
                                                    ],
                                                    md=4,
                                                ),
                                                dbc.Col(
                                                    [
                                                        dbc.Label("Customer count", class_name="d-block"),
                                                        dbc.Badge(
                                                            str(len(customers)),
                                                            id="row-count-badge",
                                                            color="info",
                                                            class_name="fs-6 px-3 py-2",
                                                        ),
                                                    ],
                                                    md=2,
                                                    class_name="d-flex flex-column justify-content-end",
                                                ),
                                                dbc.Col(
                                                    dbc.Button(
                                                        "Export CSV",
                                                        id="export-button",
                                                        color="primary",
                                                        class_name="w-100",
                                                    ),
                                                    md=2,
                                                    class_name="d-flex flex-column justify-content-end",
                                                ),
                                            ],
                                            class_name="g-3 align-items-end mb-4",
                                        ),
                                        cast(Any, DashDataTableType)(
                                            id="customers-table",
                                            columns=[
                                                {"name": "Name", "id": "Name"},
                                                {"name": "Email", "id": "Email"},
                                                {"name": "Persona", "id": "Persona"},
                                                {"name": "Churn Risk Score", "id": "Churn Risk Score", "type": "numeric"},
                                                {"name": "Churn Risk Category", "id": "Churn Risk Category"},
                                                {
                                                    "name": "Days Since Last Engagement",
                                                    "id": "Days Since Last Engagement",
                                                    "type": "numeric",
                                                },
                                                {"name": "Watch Hours", "id": "Watch Hours", "type": "numeric"},
                                                {"name": "Content Viewed", "id": "Content Viewed", "type": "numeric"},
                                                {"name": "Subscription Status", "id": "Subscription Status"},
                                            ],
                                            data=[_customer_row(customer) for customer in customers],
                                            sort_action="native",
                                            filter_action="none",
                                            page_size=10,
                                            export_format="none",
                                            style_as_list_view=True,
                                            style_table={"overflowX": "auto"},
                                            style_header={
                                                "backgroundColor": "#111827",
                                                "color": "white",
                                                "fontWeight": "bold",
                                                "border": "1px solid #374151",
                                            },
                                            style_data={
                                                "backgroundColor": "#1f2937",
                                                "color": "#e5e7eb",
                                                "border": "1px solid #374151",
                                            },
                                            style_cell={
                                                "padding": "12px",
                                                "fontFamily": "Inter, system-ui, sans-serif",
                                                "textAlign": "left",
                                                "minWidth": "120px",
                                                "width": "120px",
                                                "maxWidth": "240px",
                                                "whiteSpace": "normal",
                                            },
                                        ),
                                        dcc.Download(id="customer-csv-download"),
                                    ]
                                ),
                                class_name="border-0 shadow-sm bg-dark",
                            )
                        ],
                    ),
                    dbc.Tab(
                        label="Segment Summary",
                        tab_id="summary-tab",
                        children=[
                            dbc.Row(
                                [
                                    dbc.Col(
                                        _metric_card("Total high-risk customers", f"{summary.total_customers}", "border-start border-info border-4"),
                                        md=3,
                                    ),
                                    dbc.Col(
                                        _metric_card(
                                            "Average churn score",
                                            f"{(sum(customer.churn_risk_score for customer in customers) / len(customers)) if customers else 0.0:.2f}",
                                            "border-start border-danger border-4",
                                        ),
                                        md=3,
                                    ),
                                    dbc.Col(
                                        _metric_card("Avg days since engagement", f"{summary.average_days_since_last_engagement:.1f}", "border-start border-warning border-4"),
                                        md=3,
                                    ),
                                    dbc.Col(
                                        _metric_card("Avg watch hours", f"{summary.average_total_watch_seconds / 3600:.2f}", "border-start border-success border-4"),
                                        md=3,
                                    ),
                                ],
                                class_name="g-4 mb-4",
                            ),
                            dbc.Row(
                                [
                                    dbc.Col(dbc.Card(dbc.CardBody(dcc.Graph(figure=churn_pie, config={"displayModeBar": False})), class_name="border-0 shadow-sm bg-dark h-100"), md=6, xl=3),
                                    dbc.Col(dbc.Card(dbc.CardBody(dcc.Graph(figure=persona_bar, config={"displayModeBar": False})), class_name="border-0 shadow-sm bg-dark h-100"), md=6, xl=3),
                                    dbc.Col(dbc.Card(dbc.CardBody(dcc.Graph(figure=genre_bar, config={"displayModeBar": False})), class_name="border-0 shadow-sm bg-dark h-100"), md=6, xl=3),
                                    dbc.Col(dbc.Card(dbc.CardBody(dcc.Graph(figure=subscription_pie, config={"displayModeBar": False})), class_name="border-0 shadow-sm bg-dark h-100"), md=6, xl=3),
                                ],
                                class_name="g-4",
                            ),
                        ],
                    ),
                    dbc.Tab(
                        label="Recommendations",
                        tab_id="recommendations-tab",
                        children=[
                            dbc.Row(
                                [
                                    dbc.Col(_recommendation_card(recommendation), md=6, xl=4)
                                    for recommendation in recommendations
                                ],
                                class_name="g-4 py-2",
                            )
                        ],
                    ),
                ],
                id="main-tabs",
                active_tab="customers-tab",
                class_name="mb-4",
            ),
        ],
        fluid=True,
        class_name="px-4 pb-5 bg-black text-light min-vh-100",
    )


def create_app() -> dash.Dash:
    customers, summary, recommendations = _load_startup_data()
    app_instance = dash.Dash(
        __name__,
        external_stylesheets=[dbc.themes.CYBORG],
        suppress_callback_exceptions=True,
        title="Paramount+ Churn Risk Dashboard",
    )
    app_instance.layout = _build_layout(customers, summary, recommendations)
    return app_instance


app = create_app()
server = app.server


@callback(
    Output("customers-table", "data"),
    Output("row-count-badge", "children"),
    Input("category-filter", "value"),
    Input("persona-filter", "value"),
    State("customer-store", "data"),
)
def update_customer_table(
    selected_categories: Sequence[str] | None,
    selected_personas: Sequence[str] | None,
    stored_customers: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], str]:
    customers = [HighRiskCustomer.model_validate(customer) for customer in stored_customers]
    filtered_customers = _filter_customers(customers, selected_categories, selected_personas)
    table_data = [_customer_row(customer) for customer in filtered_customers]
    return table_data, str(len(table_data))


@callback(
    Output("customer-csv-download", "data"),
    Input("export-button", "n_clicks"),
    State("customers-table", "data"),
    prevent_initial_call=True,
)
def export_customers_to_csv(
    n_clicks: int | None, rows: list[dict[str, Any]]
) -> dict[str, Any]:
    del n_clicks
    dataframe = pd.DataFrame(rows)
    return cast(dict[str, Any], dcc.send_data_frame(dataframe.to_csv, "high_risk_customers.csv", index=False))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)
