import requests
from flask_restx import Namespace, Resource
from flask import redirect, url_for, request
import urllib.parse
from CTFd.utils import get_app_config
from CTFd.models import db
from CTFd.utils import user as current_user
from CTFd.models import UserGitHubToken

from CTFd.utils.decorators import admins_only
from CTFd.utils.user import get_current_user

import time
import jwt

github_namespace = Namespace(
    'github', description='Endpoint to manage challenge sync from github'
)

def generate_jwt():
    app_id = get_app_config("GITHUB_APP_ID")
    private_key = open(get_app_config("GITHUB_APP_PRIVATE_KEY_PATH"), "r").read()

    payload = {
        "iat": int(time.time()),
        "exp": int(time.time()) + 600,
        "iss": app_id
    }

    return jwt.encode(payload, private_key, algorithm="RS256")

def get_installation_access_token(installation_id):
    jwt_token = generate_jwt()

    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Accept": "application/vnd.github+json"
    }

    url = f"https://api.github.com/app/installations/{installation_id}/access_tokens"
    r = requests.post(url, headers=headers)

    if r.status_code != 201:
        print("Error:", r.status_code, r.text)
        return None

    return r.json().get("token")

@github_namespace.route('/callback')
class GithubCallback(Resource):
    @admins_only
    def get(self):
        installation_id = request.args.get("installation_id")

        if not installation_id:
            return {"success": False, "message": "No se recibió installation_id."}, 400

        user_id = get_current_user().id
        token_entry = UserGitHubToken.query.filter_by(user_id=user_id).first()

        if token_entry:
            token_entry.token = installation_id  # Cambiar a installation_id más adelante
        else:
            token_entry = UserGitHubToken(user_id=user_id, token=installation_id)
            db.session.add(token_entry)

        db.session.commit()

        return {
            "success": True,
            "message": "Installation ID de GitHub guardado correctamente.",
        }

@github_namespace.route('/installations')
class GithubInstallations(Resource):
    @admins_only
    def get(self):
        jwt_token = generate_jwt()

        headers = {
            "Authorization": f"Bearer {jwt_token}",
            "Accept": "application/vnd.github+json"
        }

        r = requests.get("https://api.github.com/app/installations", headers=headers)

        if r.status_code != 200:
            return {"success": False, "message": "Error al obtener instalaciones"}, 400

        installations = r.json()
        if not isinstance(installations, list):
            return {"success": False, "message": "Respuesta inesperada"}, 400

        if len(installations) == 1:
            installation_id = installations[0]["id"]
        else:
            return {"success": False, "message": "Hay múltiples instalaciones. Filtro requerido.", "r": r.json()}, 400

        user_id = get_current_user().id
        token_entry = UserGitHubToken.query.filter_by(user_id=user_id).first()

        if token_entry:
            token_entry.token = installation_id
        else:
            token_entry = UserGitHubToken(user_id=user_id, token=installation_id)
            db.session.add(token_entry)

        db.session.commit()

        return {"success": True, "message": f"Installation ID {installation_id} guardado correctamente."}

@github_namespace.route('/repos')
class GithubRepos(Resource):
    @admins_only
    def get(self):
        user_id = get_current_user().id
        token_entry = UserGitHubToken.query.filter_by(user_id=user_id).first()

        if not token_entry:
            return {"success": False, "message": "Installation ID no encontrado"}, 401

        installation_id = get_installation_access_token(token_entry.token)

        if not installation_id:
            return {"success": False, "message": "No se pudo obtener el id de instalación"}, 400

        headers = {
            "Authorization": f"token {installation_id}",
            "Accept": "application/vnd.github+json"
        }

        github_api_url = "https://api.github.com/installation/repositories"
        response = requests.get(github_api_url, headers=headers)

        if response.status_code != 200:
            return {"success": False, "message": "No se pudo obtener los repositorios"}, 400

        repos = response.json().get("repositories", [])
        repo_names = [{"id": r["id"], "name": r["name"], "full_name": r["full_name"]} for r in repos]

        return {"success": True, "repos": repo_names}
