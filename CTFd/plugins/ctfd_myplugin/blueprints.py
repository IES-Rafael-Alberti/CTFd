# plugins/ctfd_myplugin/blueprints.py

from flask import Blueprint, render_template, jsonify
from CTFd.models import Challenges
from CTFd import utils

# Definimos un Blueprint propio.
# Elegimos un nombre (interno) y un prefijo de URL.
# En este caso, agregaremos endpoints:
#   - /admin/plugins/ctfd_myplugin       ← página HTML nueva
#   - /api/v1/ctfd_myplugin/challenges   ← endpoint JSON con datos de challenges
my_bp = Blueprint(
    "ctfd_myplugin",                    # nombre interno
    __name__,
    template_folder="templates",            # buscamos plantillas en .../templates
    static_folder="static",
    static_url_path="/plugins/ctfd_myplugin/static",
    url_prefix=""                           # Nota: la ruta absoluta la concatena CTFd con lo que pongamos en @my_bp.route
)

@my_bp.route("/admin/plugins/ctfd_myplugin")
def vista_panel_admin():
    """
    Esta función renderiza la nueva página que aparecerá
    en el menú 'Plugins → Mi Plugin' (ruta: /admin/plugins/ctfd_myplugin).
    """
    total = Challenges.query.count()
    return render_template("admin/challenges/mi_pagina.html", total_challenges=total)


@my_bp.route("/api/v1/ctfd_myplugin/challenges", methods=["GET"])
def endpoint_challenges_json():
    """
    Ejemplo simple: devuelve JSON con todos los challenges.
    Tú puedes filtrar, paginar, añadir seguridad, etc.
    """
    # Obtener todos los challenges de la base de datos
    # chal_objs = Challenges.query.all()
    #
    # # Mapear a una lista de diccionarios ligeros
    # data = []
    # for c in chal_objs:
    #     data.append({
    #         "id": c.id,
    #         "name": c.name,
    #         "category": c.category,
    #         "value": c.value
    #     })
    #
    # return jsonify(data)
    return jsonify([
        {"id": 1, "name": "Challenge 1", "category": "Crypto", "value": 100},
        {"id": 2, "name": "Challenge 2", "category": "Forensics", "value": 200}
    ])
