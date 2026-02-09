import os
from dotenv import load_dotenv

import dash
import dash_bootstrap_components as dbc

from ui.layout import make_layout
from callbacks.main import register_callbacks

load_dotenv()

APP_TITLE = os.getenv("APP_TITLE", "PsalmSeeker.ai")

def create_app() -> dash.Dash:
    app = dash.Dash(
        __name__,
        title=APP_TITLE,
        external_stylesheets=[dbc.themes.BOOTSTRAP],
        suppress_callback_exceptions=True,
    )
    app.layout = make_layout()
    register_callbacks(app)
    return app

if __name__ == "__main__":
    app = create_app()
    app.run_server(debug=True, host="127.0.0.1", port=8050)
