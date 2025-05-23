import requests
from flask_restx import Namespace, Resource
from flask import redirect, url_for, request, flash
import urllib.parse
from CTFd.utils import get_app_config

from CTFd.utils.decorators import admins_only

github_namespace = Namespace(
    'github', description='Endpoint to manage challenge sync from github'
)

@github_namespace.route('/login')
class GithubLogin(Resource):
    @admins_only
    def get(self):
        client_id = get_app_config('GITHUB_APP_CLIENT_ID')
        redirect_uri = get_app_config("GITHUB_APP_REDIRECT_URI")
        scopes = "repo"

        github_auth_url = "https://github.com/login/oauth/authorize"
        query = urllib.parse.urlencode({
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": scopes,
        })

        return redirect(f"{github_auth_url}?{query}")


@github_namespace.route('/callback')
class GithubCallback(Resource):
    @admins_only
    def get(self):
        code = request.args.get("code")
        if not code:
            return {"success": False, "message": "No se recibió el código."}, 400

        # Intercambia el `code` por un `access_token`
        token_url = "https://github.com/login/oauth/access_token"
        response = requests.post(
            token_url,
            headers={"Accept": "application/json"},
            data={
                "client_id": get_app_config("GITHUB_APP_CLIENT_ID"),
                "client_secret": get_app_config("GITHUB_APP_CLIENT_SECRET"),
                "code": code,
            },
        )

        print("🔁 Respuesta de GitHub:", response.json())

        if response.status_code != 200:
            return {"success": False, "message": "Error al obtener el token."}, 400

        access_token = response.json().get("access_token")
        if not access_token:
            return {"success": False, "message": "No se recibió el token."}, 400

        # 💾 Aquí deberías guardar el access_token relacionado con el usuario actual
        # Por ejemplo:
        # save_token(current_user.id, access_token)

        return {
            "success": True,
            "message": "Token de GitHub obtenido correctamente.",
            "token": access_token  # Solo para depuración, no lo muestres en producción
        }