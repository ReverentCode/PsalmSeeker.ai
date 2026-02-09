from dash import html, dcc
import dash_bootstrap_components as dbc

from ui.styles import CARD_STYLE, SECTION_GAP


def make_layout() -> html.Div:
    header = dbc.Navbar(
        dbc.Container(
            [
                html.Div(
                    [
                        html.Div("PsalmSeeker", className="ps-title", style={"fontSize": "1.35rem"}),
                        html.Div(
                            "Enter His gates with thanksgiving • His courts with praise • Into His presence by the Word",
                            className="ps-subtitle",
                        ),
                    ]
                ),
                html.Div(
                    [
                        html.Span(
                            [html.Span(className="ps-step-dot", id="step_gates_icon"), "Gates"],
                            className="ps-step",
                            style={"marginRight": "8px"},
                        ),
                        html.Span(
                            [html.Span(className="ps-step-dot", id="step_courts_icon"), "Courts"],
                            className="ps-step",
                            style={"marginRight": "8px"},
                        ),
                        html.Span(
                            [html.Span(className="ps-step-dot", id="step_holy_icon"), "Holy of Holies"],
                            className="ps-step",
                        ),
                    ],
                    className="d-none d-md-flex",
                ),
            ],
            fluid=True,
        ),
        className="ps-header",
        dark=True,
    )

    gates = dbc.Card(
        dbc.CardBody(
            [
                html.Div("Gates", className="ps-pill"),
                html.H4("Come as you are", style={"marginTop": "10px"}),
                html.Div(
                    "Write honestly. This is not a search box—it's a doorway. We’ll retrieve Psalms by meaning, not keywords.",
                    className="ps-small",
                ),
                html.Div(className="ps-divider"),
                dbc.Label("Your prompt", className="ps-label"),
                dbc.Textarea(
                    id="user_prompt",
                    className="ps-textarea",
                    placeholder="Example: I feel fear about the future, but I want to trust God without pretending I’m okay.",
                    rows=4,
                ),
                html.Div(style={"height": "10px"}),
                dbc.Row(
                    [
                        dbc.Col(
                            dbc.Select(
                                id="mood",
                                className="ps-dropdown",
                                options=[
                                    {"label": "No preset (pure semantic)", "value": "none"},
                                    {"label": "Lament → Trust", "value": "lament_trust"},
                                    {"label": "Fear → Refuge", "value": "fear_refuge"},
                                    {"label": "Waiting → Strength", "value": "waiting_strength"},
                                    {"label": "Repentance → Cleansing", "value": "repent_cleansing"},
                                    {"label": "Praise → Thanksgiving", "value": "praise_thanks"},
                                ],
                                value="none",
                            ),
                            width=7,
                        ),
                        dbc.Col(
                            html.Div(
                                [
                                    dbc.Button("Knock", id="btn_seek", className="btn-royal w-100"),
                                    html.Div(
                                        dbc.Spinner(size="sm", color="warning", spinnerClassName="ps-spinner"),
                                        id="seek_spinner",
                                        className="ps-inline-spinner",
                                        style={"opacity": 0},
                                    ),
                                ],
                                className="ps-action-wrap",
                            ),
                            width=5,
                        ),
                    ],
                    align="center",
                    className="g-2",
                ),
                html.Div(style={"height": "8px"}),
                html.Div(id="seek_status", className="ps-small"),
            ]
        ),
        className="ps-card",
        style=CARD_STYLE,
    )

    courts = dbc.Card(
        dbc.CardBody(
            [
                html.Div("Courts", className="ps-pill"),
                html.H4("Psalms that meet you where you are", style={"marginTop": "10px"}),
                html.Div("Select one to enter deeper.", className="ps-small"),
                html.Div(className="ps-divider"),
                # Courts loading is OK: it should show only when Knock is working on Courts.
                dcc.Loading(
                    html.Div(id="results_out", className="ps-scroll-pane"),
                    type="circle",
                    className="ps-loading",
                ),
            ],
            style={"display": "flex", "flexDirection": "column"},
        ),
        className="ps-card",
        style=CARD_STYLE,
    )

    holy = dbc.Card(
        dbc.CardBody(
            [
                html.Div("Holy of Holies", className="ps-pill"),
                html.H4("Remain with the Word", style={"marginTop": "10px"}),
                html.Div("Read slowly. Then receive a guided reflection from your local model.", className="ps-small"),
                html.Div(className="ps-divider"),

                # Manual spinner: only shown when user clicks "Enter with this Psalm"
                html.Div(
                    dbc.Spinner(color="warning", spinnerClassName="ps-spinner", spinner_style={"width": "2.0rem", "height": "2.0rem"}),
                    id="pick_spinner",
                    className="ps-panel-spinner",
                    style={"display": "none"},
                ),

                # No dcc.Loading wrapper here (prevents Knock from showing spinners in Holy)
                html.Div(id="selected_psalm_out"),

                html.Div(style={"height": "12px"}),
                dbc.Button("Generate reflection (Ollama)", id="btn_reflect", className="btn-royal"),
                html.Div(style={"height": "10px"}),

                # Manual spinner: only shown when user clicks "Generate reflection"
                html.Div(
                    dbc.Spinner(color="warning", spinnerClassName="ps-spinner", spinner_style={"width": "2.2rem", "height": "2.2rem"}),
                    id="reflect_spinner",
                    className="ps-panel-spinner",
                    style={"display": "none"},
                ),

                html.Div(
                    id="reflection_out",
                    className="ps-card ps-card-strong",
                    style={"padding": "14px", "borderRadius": "18px"},
                ),
            ]
        ),
        className="ps-card",
        style=CARD_STYLE,
    )

    stores = html.Div(
        [
            dcc.Store(id="results_store"),
            dcc.Store(id="selected_store"),
            dcc.Store(id="progress_store", data={"gates": False, "courts": False, "holy": False}),
        ]
    )

    return html.Div(
        [
            header,
            stores,
            dbc.Container(
                [
                    html.Div(style={"height": "18px"}),
                    dbc.Row(
                        [
                            dbc.Col(gates, md=6),
                            dbc.Col(courts, md=6),
                        ],
                        className="g-3",
                    ),
                    html.Div(style={"height": "14px"}),
                    dbc.Row([dbc.Col(holy)], className="g-3"),
                    html.Div(style={"height": "30px"}),
                    html.Div(
                        "PsalmSeeker v0 • local-first • Scripture retrieval + reflection",
                        className="ps-small",
                        style={"textAlign": "center"},
                    ),
                    html.Div(style={"height": "20px"}),
                ],
                fluid=True,
            ),
        ]
    )