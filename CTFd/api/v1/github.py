import requests
from flask_restx import Namespace, Resource
from flask import redirect, url_for, request
import urllib.parse
from CTFd.utils import get_app_config
from CTFd.models import db, GithubRepositories, GithubChallengeSync, Challenges, GithubFlagSync, Flags
from CTFd.utils import user as current_user
from CTFd.models import UserGitHubToken

from CTFd.utils.decorators import admins_only
from CTFd.utils.user import get_current_user

from datetime import datetime
import base64
import time
import jwt
import json

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

# lista los repositorios de la cuenta de usuario
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


# guarda los repositorios seleccionados en la tabla
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

# lista los retos guardados
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

# elimina un repositorio de la tabla
@github_namespace.route('/repos/<int:repo_id>')
class GithubRepoDelete(Resource):
    @admins_only
    def delete(self, repo_id):
        user_id = get_current_user().id
        repo = GithubRepositories.query.filter_by(id=repo_id, user_id=user_id).first()

        if not repo:
            return {"success": False, "message": "Repositorio no encontrado"}, 404

        # Obtener y eliminar sincronizaciones de retos
        challenge_syncs = GithubChallengeSync.query.filter_by(github_repo_id=repo.id).all()
        for sync in challenge_syncs:
            db.session.delete(sync)

        # Obtener y eliminar sincronizaciones de flags
        flag_syncs = GithubFlagSync.query.filter_by(github_repo_id=repo.id).all()
        for sync in flag_syncs:
            db.session.delete(sync)

        db.session.delete(repo)
        db.session.commit()

        return {"success": True, "message": "Repositorio y datos relacionados eliminados correctamente."}


# activa y desactiva la sincronizacion
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

# importa desde el boton de la tabla
@github_namespace.route('/repos/<int:repo_id>/import')
class GithubRepoImport(Resource):
    @admins_only
    def post(self, repo_id):
        user_id = get_current_user().id
        repo = GithubRepositories.query.filter_by(id=repo_id, user_id=user_id).first()
        if not repo:
            return {"success": False, "message": "Repositorio no encontrado"}, 404

        # Obtener token
        token_entry = UserGitHubToken.query.filter_by(user_id=user_id).first()
        access_token = get_installation_access_token(token_entry.token)

        result = import_challenges_from_repo(repo, access_token, overwrite_existing=False)

        return {
            "success": result["success"],
            "message": f"{result['created']} retos importados, {result['skipped']} ya existentes.",
            "errors": result["errors"]
        }

# recibe los push del repositorio
@github_namespace.route('/webhook', methods=["POST"])
class GithubWebhook(Resource):
    def post(self):
        event = request.headers.get("X-GitHub-Event")
        payload = request.get_json()

        if event != "push":
            return {"success": True, "message": "Evento ignorado"}, 200

        repo_full_name = payload.get("repository", {}).get("full_name")
        if not repo_full_name:
            return {"success": False, "message": "No se encontró el nombre del repo"}, 400

        modified_files = []
        for commit in payload.get("commits", []):
            modified_files.extend(commit.get("added", []) + commit.get("modified", []))
        modified_files = list(set(modified_files))

        repo = GithubRepositories.query.filter_by(full_name=repo_full_name).first()
        if not repo:
            return {"success": False, "message": "Repositorio no registrado"}, 404

        token_entry = UserGitHubToken.query.filter_by(user_id=repo.user_id).first()
        access_token = get_installation_access_token(token_entry.token)

        result = import_challenges_from_repo(repo, access_token, only_paths=modified_files, overwrite_existing=True)

        return {
            "success": result["success"],
            "message": f"{result['updated']} retos actualizados, {result['created']} creados.",
            "errors": result["errors"]
        }

# valida los retos
def validate_challenge_data(data, path):
    required_fields = ["uuid", "name", "description", "category", "value", "type", "state"]

    for field in required_fields:
        if field not in data:
            raise ValueError(f"{path}: Falta el campo obligatorio '{field}'")

    if not isinstance(data["uuid"], str):
        raise ValueError(f"{path}: 'uuid' debe ser una cadena")

    if not isinstance(data["name"], str) or len(data["name"]) > 80:
        raise ValueError(f"{path}: 'name' debe ser una cadena de hasta 80 caracteres")

    if not isinstance(data["category"], str) or len(data["category"]) > 80:
        raise ValueError(f"{path}: 'category' debe ser una cadena de hasta 80 caracteres")

    if not isinstance(data["description"], str):
        raise ValueError(f"{path}: 'description' debe ser una cadena")

    if not isinstance(data["value"], int) or data["value"] < 0:
        raise ValueError(f"{path}: 'value' debe ser un número entero positivo")

    if data["type"] not in ["standard", "dynamic"]:
        raise ValueError(f"{path}: 'type' no es válido")

    if data["state"] not in ["visible", "hidden"]:
        raise ValueError(f"{path}: 'state' no es válido")

    return data

def validate_flag_data(flag, path):
    required_fields = ["uuid", "type", "content"]

    for field in required_fields:
        if field not in flag:
            raise ValueError(f"{path}: flag sin campo obligatorio '{field}'")

    if not isinstance(flag["uuid"], str):
        raise ValueError(f"{path}: 'uuid' de flag debe ser cadena")

    if flag["type"] not in ["static", "regex"]:
        raise ValueError(f"{path}: tipo de flag no soportado")

    if not isinstance(flag["content"], str):
        raise ValueError(f"{path}: contenido de flag no válido")

    if flag["data"] not in ["case_insensitive", ""]:
        raise ValueError(f"{path}: data de flag no soportado")


def import_flags(challenge_id, flags, repo_id, challenge_uuid, path, overwrite_existing):
    json_flag_uuids = set()
    now = datetime.utcnow()

    for flag in flags:
        try:
            validate_flag_data(flag, path)
        except ValueError as ve:
            raise ValueError(str(ve))

        flag_uuid = flag["uuid"]
        json_flag_uuids.add(flag_uuid)

        existing_flag_sync = GithubFlagSync.query.filter_by(flag_uuid=flag_uuid).first()

        if existing_flag_sync:
            if overwrite_existing:
                existing_flag = Flags.query.get(existing_flag_sync.flag_id)
                if existing_flag:
                    existing_flag.type = flag["type"]
                    existing_flag.content = flag["content"]
                    existing_flag.data = flag.get("data", "")
                    existing_flag_sync.last_updated_at = now
        else:
            new_flag = Flags(
                challenge_id=challenge_id,
                type=flag["type"],
                content=flag["content"],
                data=flag.get("data", "")
            )
            db.session.add(new_flag)
            db.session.flush()

            db.session.add(GithubFlagSync(
                flag_id=new_flag.id,
                github_repo_id=repo_id,
                challenge_uuid=challenge_uuid,
                flag_uuid=flag_uuid,
                last_updated_at=now
            ))

    # Eliminar flags que ya no existen en el JSON
    synced_flags = GithubFlagSync.query.filter_by(
        github_repo_id=repo_id,
        challenge_uuid=challenge_uuid
    ).all()

    for synced in synced_flags:
        if synced.flag_uuid not in json_flag_uuids:
            flag = Flags.query.get(synced.flag_id)
            if flag:
                db.session.delete(flag)
            db.session.delete(synced)

from datetime import datetime
from CTFd.models import Challenges

def import_or_update_challenge(challenge_info, repo, path, overwrite_existing):
    uuid = challenge_info.get("uuid")
    if not uuid:
        return None, False, "Falta el campo 'uuid'"

    try:
        validated_data = validate_challenge_data(challenge_info, path)
    except ValueError as ve:
        return None, False, str(ve)

    existing_sync = GithubChallengeSync.query.filter_by(challenge_uuid=uuid).first()

    if existing_sync:
        if overwrite_existing:
            challenge = Challenges.query.get(existing_sync.challenge_id)
            if challenge:
                challenge.name = validated_data["name"]
                challenge.description = validated_data["description"]
                challenge.category = validated_data["category"]
                challenge.value = validated_data["value"]
                challenge.state = validated_data["state"]
                challenge.type = validated_data["type"]
                challenge.connection_info = validated_data.get("conection_info")
                challenge.max_attempts = validated_data.get("max_attemps", 0)
                challenge.attribution = validated_data.get("attribution")
                existing_sync.last_updated_at = datetime.utcnow()
                return challenge, False, None
            else:
                return None, False, "No se encontró el reto sincronizado en la base de datos"
        else:
            return None, False, "Reto ya sincronizado (sin sobrescritura)"
    else:
        challenge = Challenges(
            name=validated_data["name"],
            description=validated_data["description"],
            category=validated_data["category"],
            value=validated_data["value"],
            state=validated_data["state"],
            type=validated_data["type"],
            connection_info=validated_data.get("conection_info"),
            max_attempts=validated_data.get("max_attemps", 0),
            attribution=validated_data.get("attribution")
        )
        db.session.add(challenge)
        db.session.flush()

        db.session.add(GithubChallengeSync(
            challenge_id=challenge.id,
            github_repo_id=repo.id,
            challenge_uuid=uuid,
            challenge_path=path,
            last_updated_at=datetime.utcnow()
        ))

        return challenge, True, None

# importa los retos
def import_challenges_from_repo(repo, access_token, only_paths=None, overwrite_existing=False):
    headers = {
        "Authorization": f"token {access_token}",
        "Accept": "application/vnd.github+json"
    }

    base_url = f"https://api.github.com/repos/{repo.full_name}/contents/challenges"
    file_list_resp = requests.get(base_url, headers=headers)

    if file_list_resp.status_code != 200:
        return {"success": False, "message": "No se pudo acceder a /challenges en el repositorio."}

    file_list = file_list_resp.json()
    count_created = 0
    count_updated = 0
    count_skipped = 0
    errors = []

    for file in file_list:
        if not file["name"].endswith(".json"):
            continue

        path = file["path"]
        if only_paths and path not in only_paths:
            continue

        file_resp = requests.get(file["download_url"], headers=headers)
        if file_resp.status_code != 200:
            errors.append({"file": path, "error": f"HTTP {file_resp.status_code}"})
            continue

        try:
            challenge_data = json.loads(file_resp.text)
            challenge_info = challenge_data.get("challenge", {})

            challenge, created, error_msg = import_or_update_challenge(challenge_info, repo, path, overwrite_existing)

            if error_msg:
                if error_msg != "Reto ya sincronizado (sin sobrescritura)":
                    errors.append({"file": path, "error": error_msg})
                else:
                    count_skipped += 1
                continue

            # Flags
            try:
                import_flags(
                    challenge_id=challenge.id,
                    flags=challenge_info.get("flags", []),
                    repo_id=repo.id,
                    challenge_uuid=challenge_info["uuid"],
                    path=path,
                    overwrite_existing=overwrite_existing
                )
            except ValueError as ve:
                errors.append({"file": path, "error": str(ve)})
                continue

            if created:
                count_created += 1
            else:
                count_updated += 1

        except Exception as e:
            errors.append({"file": path, "error": str(e)})
            continue

    repo.last_synced_at = datetime.utcnow()
    db.session.commit()

    return {
        "success": True,
        "created": count_created,
        "updated": count_updated,
        "skipped": count_skipped,
        "errors": errors
    }