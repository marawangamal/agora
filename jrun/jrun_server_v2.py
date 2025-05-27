# jrun/serve.py

import os
import sqlite3
import json
from pathlib import Path
from flask import Flask, jsonify, send_from_directory, request
from jrun.job_viewer import JobViewer


def create_app(default_db: str, web_folder: Path) -> Flask:
    app = Flask(__name__, static_folder=str(web_folder), static_url_path="")

    @app.route("/api/jobs")
    def api_jobs():
        # only use override if non-empty
        db_override = request.args.get("db", "").strip()
        db_path = db_override or default_db

        app.logger.debug(f"→ Opening DB: {db_path!r}")
        viewer = JobViewer(db_path)

        try:
            jobs = viewer.get_jobs(filters=None)
        except sqlite3.OperationalError as e:
            # if the table doesn't exist yet, just return empty
            if "no such table" in str(e).lower():
                app.logger.warning(
                    f"No jobs table in {db_path!r}, returning empty list"
                )
                return jsonify([])
            raise

        # serialize to plain dicts
        out = [
            {
                "job_id": j.job_id,
                "command": j.command,
                "group_name": j.group_name,
                "depends_on": j.depends_on,
                "status": j.status,
            }
            for j in jobs
        ]
        return jsonify(out)

    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def static_proxy(path):
        target = web_folder / path
        if path and target.exists():
            return send_from_directory(str(web_folder), path)
        return send_from_directory(str(web_folder), "index.html")

    return app


def serve(
    db: str,
    host: str = "localhost",
    port: int = 3000,
    web_folder: str = "web",
):
    """
    Launch the jrun Flask server:

      db         – path to SQLite DB
      host, port – interface to bind
      web_folder – where index.html lives
    """
    # resolve absolute paths
    here = Path(__file__).resolve().parent  # jrun/
    project_root = here.parent  # project root
    web_path = Path(web_folder)
    if not web_path.is_absolute():
        web_path = project_root / web_path

    # sanity check
    if not (web_path / "index.html").exists():
        raise FileNotFoundError(f"❌ Cannot find web/index.html at {web_path!r}")

    print(
        "🔌 jrun server configuration:\n"
        f"    • DB path:    {db}\n"
        f"    • Web folder: {web_path}\n"
        f"    • Host:       {host}\n"
        f"    • Port:       {port}\n"
    )

    app = create_app(default_db=db, web_folder=web_path)
    app.run(host=host, port=port, debug=True)
