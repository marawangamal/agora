# jrun/serve.py

from waitress import serve as waitress_serve
from flask import Flask, jsonify, send_from_directory, request
from pathlib import Path
from jrun.job_viewer import JobViewer


def create_app(default_db: str, web_folder: Path) -> Flask:
    app = Flask(__name__, static_folder=str(web_folder), static_url_path="")

    @app.route("/api/jobs")
    @app.route("/api/jobs/")  # Handle both variations
    def api_jobs():
        db_path = request.args.get("db", default_db) or default_db
        viewer = JobViewer(db_path)
        jobs_data = viewer.get_jobs(filters=None, ignore_status=False)

        # If they asked for JSON mode, wrap with stats/count
        if request.args.get("format") == "json":
            stats = viewer._get_status_totals(jobs_data)
            return jsonify({"jobs": jobs_data, "stats": stats, "count": len(jobs_data)})

        # Otherwise just return array
        return jsonify(jobs_data)

    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def static_proxy(path):
        full = web_folder / path
        if path and full.exists():
            return send_from_directory(str(web_folder), path)
        return send_from_directory(str(web_folder), "index.html")

    return app


def serve(db: str, host: str = "localhost", port: int = 3000, web_folder: str = "web"):
    project_root = Path(__file__).resolve().parent.parent
    web_path = Path(web_folder)
    if not web_path.is_absolute():
        web_path = project_root / web_folder
    if not (web_path / "index.html").exists():
        raise FileNotFoundError(f"Cannot find web/index.html at {web_path!r}")

    app = create_app(default_db=db, web_folder=web_path)
    # print(f"🔌 Serving on http://{host}:{port}  (DB: {db})")

    print("🚀 jrun web server")
    print(f"   Running on http://{host}:{port}")
    print(f"   Database: {Path(db).name}")
    print("")
    print("   Open the URL above to view job graph.")
    print("   Press Ctrl+C to stop")

    waitress_serve(app, host=host, port=port)
