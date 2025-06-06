# plugins/ctfd_myplugin/__init__.py
from pathlib import Path

from jinja2 import ChoiceLoader, FileSystemLoader
from CTFd.plugins import register_plugin_assets_directory
from .blueprints import my_bp


def load(app):
    """
    CTFd ejecuta esto al arrancar el plugin.
    """

    # 1) Blueprint del plugin
    app.register_blueprint(my_bp)

    # 2) Loader de plantillas del plugin
    plugin_templates_path = Path(__file__).parent / "templates"
    plugin_loader = FileSystemLoader(str(plugin_templates_path))

    # Si el core ya tiene un ChoiceLoader, lo ampliamos; si no, creamos uno nuevo
    if isinstance(app.jinja_loader, ChoiceLoader):
        # Insertamos nuestro loader en primer lugar (mayor prioridad)
        app.jinja_loader.loaders.insert(0, plugin_loader)
    else:
        # El core trae un FileSystemLoader simple ➜ construimos un ChoiceLoader
        app.jinja_loader = ChoiceLoader([plugin_loader, app.jinja_loader])

    # 3) Assets estáticos del plugin
    register_plugin_assets_directory(app, base_path="/plugins/ctfd_myplugin/assets/")
