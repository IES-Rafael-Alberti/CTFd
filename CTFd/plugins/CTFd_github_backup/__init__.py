# plugins/github_backup/__init__.py
from pathlib import Path

from jinja2 import ChoiceLoader, FileSystemLoader
from CTFd.plugins import register_plugin_assets_directory
from .blueprints import my_bp
from CTFd.plugins.CTFd_github_backup.models import UserGitHubToken, GithubRepositories, GithubChallengeSync, GithubFlagSync, GithubHintSync


def load(app):
    app.register_blueprint(my_bp)

    from CTFd.models import db
    db.create_all()

    plugin_templates_path = Path(__file__).parent / "templates"
    plugin_loader = FileSystemLoader(str(plugin_templates_path))

    if isinstance(app.jinja_loader, ChoiceLoader):
        app.jinja_loader.loaders.insert(0, plugin_loader)
    else:
        app.jinja_loader = ChoiceLoader([plugin_loader, app.jinja_loader])

    register_plugin_assets_directory(app, base_path="/plugins/github_backup/assets/")
