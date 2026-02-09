import json
from dash import html, Input, Output, State, callback_context, ALL, no_update
import dash_bootstrap_components as dbc

from services.retriever import PsalmRetriever
from services.ollama import OllamaClient

retriever = PsalmRetriever()
ollama = OllamaClient()


def _results_list(results: list[dict]) -> html.Div:
    if not results:
        return html.Div("No results yet.", className="ps-small")

    items = []
    for r in results:
        title = (
            f"Psalm {r['psalm']}:{r['verse_start']}-{r['verse_end']}"
            if r.get("verse_start")
            else f"Psalm {r['psalm']}"
        )
        snippet = (r["text"][:240] + "…") if len(r["text"]) > 240 else r["text"]

        items.append(
            dbc.Card(
                dbc.CardBody(
                    [
                        html.Div(title, className="ps-result-title", style={"fontWeight": 800}),
                        html.Div(f"Similarity: {r['score']:.3f}", className="ps-small"),
                        html.Div(snippet, className="ps-small", style={"marginTop": "8px"}),
                        html.Div(style={"height": "10px"}),
                        dbc.Button(
                            "Enter with this Psalm",
                            id={"type": "pick_psalm", "index": r["id"]},
                            className="btn-royal",
                            size="sm",
                        ),
                    ]
                ),
                className="ps-card ps-card-strong",
                style={"marginBottom": "10px"},
            )
        )

    return html.Div(items)


def _icon_state(done: bool):
    """Return (className, children) for the step icon."""
    if done:
        return "ps-step-check", "✓"
    return "ps-step-dot", ""


def register_callbacks(app):

    # -------------------------
    # Knock: retrieval + reset downstream state (Courts/Holy backtracking)
    # -------------------------
    @app.callback(
        Output("seek_status", "children"),
        Output("results_store", "data"),
        Output("results_out", "children"),

        # These are also written by other callbacks, so allow duplicates:
        Output("selected_store", "data", allow_duplicate=True),
        Output("selected_psalm_out", "children", allow_duplicate=True),
        Output("reflection_out", "children", allow_duplicate=True),
        Output("progress_store", "data", allow_duplicate=True),

        Input("btn_seek", "n_clicks"),
        State("user_prompt", "value"),
        State("mood", "value"),
        prevent_initial_call=True,
        running=[
            (Output("btn_seek", "disabled"), True, False),
            (Output("seek_spinner", "style"), {"opacity": 1}, {"opacity": 0}),
        ],
    )
    def on_seek(n_clicks, user_prompt, mood):
        user_prompt = (user_prompt or "").strip()
        if not user_prompt:
            return (
                "Write something first—your words are the doorway.",
                None,
                _results_list([]),
                None,
                html.Div("Seek first, then choose.", className="ps-small"),
                html.Div("", className="ps-small"),
                {"gates": False, "courts": False, "holy": False},
            )

        mood_prefix = {
            "lament_trust": "lament and sorrow moving toward trust and surrender: ",
            "fear_refuge": "fear moving toward refuge and courage in God: ",
            "waiting_strength": "patient waiting and endurance, strength renewed: ",
            "repent_cleansing": "repentance, cleansing, mercy and restoration: ",
            "praise_thanks": "praise, thanksgiving, adoration, joy: ",
            "none": "",
        }.get(mood or "none", "")

        query = f"{mood_prefix}{user_prompt}".strip()

        try:
            results = retriever.search(query=query, k=5)
        except Exception as e:
            return (
                f"Index not ready or retrieval failed: {e}",
                None,
                _results_list([]),
                None,
                html.Div("Seek first, then choose.", className="ps-small"),
                html.Div("", className="ps-small"),
                {"gates": False, "courts": False, "holy": False},
            )

        # Knock means: Gates complete, others reset until user progresses again
        progress = {"gates": True, "courts": False, "holy": False}

        return (
            "The gates are open. Choose a Psalm to step into the courts.",
            results,
            _results_list(results),
            None,  # reset selection
            html.Div("Choose a Psalm from the Courts.", className="ps-small", style={"opacity": 0.7, "fontStyle": "italic"}),
            html.Div("", className="ps-small"),  # reset reflection
            progress,
        )

    # -------------------------
    # Pick: selection + clear reflection (Holy backtracks until reflect)
    # -------------------------
    @app.callback(
        Output("selected_store", "data", allow_duplicate=True),
        Output("selected_psalm_out", "children", allow_duplicate=True),
        Output("reflection_out", "children", allow_duplicate=True),
        Output("progress_store", "data", allow_duplicate=True),

        Input({"type": "pick_psalm", "index": ALL}, "n_clicks"),
        State("results_store", "data"),
        prevent_initial_call=True,
        running=[
        (Output({"type": "pick_psalm", "index": ALL}, "disabled"), True, False),
        (Output("pick_spinner", "style"), {"display": "flex"}, {"display": "none"})],
    )
    def on_pick(_, results):
        if not results:
            return (
                None,
                html.Div("Seek first, then choose.", className="ps-small"),
                html.Div("", className="ps-small"),
                {"gates": False, "courts": False, "holy": False},
            )

        ctx = callback_context
        if not ctx.triggered:
            return (
                None,
                html.Div("Choose a Psalm.", className="ps-small"),
                html.Div("", className="ps-small"),
                {"gates": True, "courts": False, "holy": False},
            )

        # Dash can trigger pattern-matching callbacks when components are CREATED.
        # In that case, n_clicks is None/0 and we must ignore it.
        trig0 = ctx.triggered[0]
        val = trig0.get("value", None)
        if val is None or val == 0:
            return (no_update, no_update, no_update, no_update)

        trig = trig0["prop_id"].split(".")[0]
        trig_id = json.loads(trig)
        pick_id = trig_id["index"]

        chosen = next((r for r in results if r["id"] == pick_id), None)
        if not chosen:
            return (
                None,
                html.Div("Could not find that selection.", className="ps-small"),
                html.Div("", className="ps-small"),
                {"gates": True, "courts": False, "holy": False},
            )

        title = f"Psalm {chosen['psalm']}"
        sub = (
            f"Verses {chosen.get('verse_start','?')}-{chosen.get('verse_end','?')}"
            if chosen.get("verse_start")
            else ""
        )

        selected_view = html.Div(
            [
                html.Div(title, style={"fontWeight": 800, "fontSize": "1.2rem"}),
                html.Div(sub, className="ps-small"),
                html.Div(className="ps-divider"),
                html.Div(chosen["text"], className="ps-verse"),
            ]
        )

        # Pick means: Gates + Courts complete; Holy resets until reflection generated
        progress = {"gates": True, "courts": True, "holy": False}

        return (
            chosen,
            selected_view,
            html.Div("", className="ps-small"),  # clear reflection whenever selection changes
            progress,
        )

    # -------------------------
    # Reflect: final step
    # -------------------------
    @app.callback(
        Output("reflection_out", "children", allow_duplicate=True),
        Output("progress_store", "data", allow_duplicate=True),

        Input("btn_reflect", "n_clicks"),
        State("selected_store", "data"),
        State("user_prompt", "value"),
        prevent_initial_call=True,
        running=[
        (Output("btn_reflect", "disabled"), True, False),
        (Output("reflect_spinner", "style"), {"display": "flex"}, {"display": "none"}),]
    )
    def on_reflect(n_clicks, selected, user_prompt):
        if not selected:
            return (
                html.Div("Choose a Psalm first. Then ask for reflection.", className="ps-small"),
                {"gates": True, "courts": False, "holy": False},
            )

        prompt = (user_prompt or "").strip()

        system = (
            "You are a reverent biblical guide. Speak with humility. "
            "Do not claim new revelation. Use Scripture-centered language. "
            "Offer: (1) a short summary of what the Psalm is doing, "
            "(2) a gentle invitation to respond in prayer, "
            "(3) 2-3 journaling questions. "
            "Avoid manipulative or condemnatory tone."
        )

        user = f"""
User posture:
{prompt}

Selected Scripture:
Psalm {selected['psalm']}
{selected['text']}

Now write a guided reflection that feels like entering God's courts—thanksgiving, awe, and nearness.
""".strip()

        try:
            out = ollama.generate(system=system, prompt=user)
        except Exception as e:
            return (
                html.Div(f"Ollama error: {e}", className="ps-small"),
                {"gates": True, "courts": True, "holy": False},
            )

        # Reflect means: all complete
        return html.Div(out, className="ps-verse"), {"gates": True, "courts": True, "holy": True}

    # -------------------------
    # Navbar progress renderer (single writer to icon outputs)
    # -------------------------
    @app.callback(
        Output("step_gates_icon", "className"),
        Output("step_gates_icon", "children"),
        Output("step_courts_icon", "className"),
        Output("step_courts_icon", "children"),
        Output("step_holy_icon", "className"),
        Output("step_holy_icon", "children"),
        Input("progress_store", "data"),
    )
    def render_steps(progress):
        progress = progress or {"gates": False, "courts": False, "holy": False}

        g_cls, g_child = _icon_state(bool(progress.get("gates")))
        c_cls, c_child = _icon_state(bool(progress.get("courts")))
        h_cls, h_child = _icon_state(bool(progress.get("holy")))

        return g_cls, g_child, c_cls, c_child, h_cls, h_child