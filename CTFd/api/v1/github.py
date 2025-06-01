import requests
from flask_restx import Namespace, Resource
from flask import redirect, url_for, request
import urllib.parse
from CTFd.utils import get_app_config
from CTFd.models import db, GithubRepositories
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
        all_repos = []
        page = 1

        while True:
            response = requests.get(
                f"{github_api_url}?per_page=100&page={page}",
                headers=headers
            )

            if response.status_code != 200:
                return {
                    "success": False,
                    "message": "No se pudo obtener los repositorios",
                    "details": response.json()
                }, 400

            repos_page = response.json().get("repositories", [])
            all_repos.extend(repos_page)

            # Si no hay más repos, termina
            if "next" not in response.links:
                break

            page += 1

        repo_names = [
            {"id": r["id"], "name": r["name"], "full_name": r["full_name"]}
            for r in all_repos
        ]

        return {"success": True, "repos": repo_names}


@github_namespace.route('/repos/selection')
class GithubRepoSelection(Resource):
    @admins_only
    def post(self):
        data = request.get_json()
        selected_repos = data.get("repos", [])
        user = get_current_user()

        if not isinstance(selected_repos, list):
            return {"success": False, "message": "Formato de datos inválido"}, 400

        for repo in selected_repos:
            existing = GithubRepositories.query.filter_by(
                user_id=user.id,
                github_repo_id=repo["id"]
            ).first()

            if not existing:
                new_repo = GithubRepositories(
                    user_id=user.id,
                    github_repo_id=repo["id"],
                    name=repo["name"],
                    full_name=repo["full_name"],
                    selected=True,
                    last_synced_at=None
                )
                db.session.add(new_repo)

        db.session.commit()

        return {"success": True, "message": "Repositorios guardados correctamente"}


@github_namespace.route('/repos/saved')
class GithubSavedRepos(Resource):
    @admins_only
    def get(self):
        user_id = get_current_user().id
        saved_repos = GithubRepositories.query.filter_by(user_id=user_id).all()

        result = []
        for repo in saved_repos:
            result.append({
                "id": repo.id,
                "name": repo.name,
                "full_name": repo.full_name,
                "selected": repo.selected,
                "last_synced_at": repo.last_synced_at.isoformat() if repo.last_synced_at else None,
            })

        return {"success": True, "repos": result}

@github_namespace.route('/repos/<int:repo_id>')
class GithubRepoDelete(Resource):
    @admins_only
    def delete(self, repo_id):
        user_id = get_current_user().id
        repo = GithubRepositories.query.filter_by(id=repo_id, user_id=user_id).first()

        if not repo:
            return {"success": False, "message": "Repositorio no encontrado"}, 404

        db.session.delete(repo)
        db.session.commit()

        return {"success": True, "message": "Repositorio eliminado"}

@github_namespace.route('/repos/<int:repo_id>/toggle')
class GithubRepoToggle(Resource):
    @admins_only
    def patch(self, repo_id):
        user_id = get_current_user().id
        repo = GithubRepositories.query.filter_by(id=repo_id, user_id=user_id).first()

        if not repo:
            return {"success": False, "message": "Repositorio no encontrado"}, 404

        repo.selected = not repo.selected
        db.session.commit()

        return {
            "success": True,
            "message": f"Sincronización {'activada' if repo.selected else 'desactivada'}",
            "selected": repo.selected
        }
