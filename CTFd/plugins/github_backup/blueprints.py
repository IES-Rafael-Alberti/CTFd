# plugins/github_backup/blueprints.py
import pytz
from flask import Blueprint, render_template, jsonify
from CTFd.models import Challenges
from CTFd import utils

# Definimos un Blueprint propio.
# Elegimos un nombre (interno) y un prefijo de URL.
# En este caso, agregaremos endpoints:
#   - /admin/plugins/github_backup       ← página HTML nueva
#   - /api/v1/github_backup/challenges   ← endpoint JSON con datos de challenges
my_bp = Blueprint(
    "github_backup",                    # nombre interno
    __name__,
    template_folder="templates",            # buscamos plantillas en .../templates
    static_folder="static",
    static_url_path="/plugins/github_backup/static",
    url_prefix=""                           # Nota: la ruta absoluta la concatena CTFd con lo que pongamos en @my_bp.route
)

@my_bp.route("/admin/plugins/github_backup")
def vista_panel_admin():
    """
    Esta función renderiza la nueva página que aparecerá
    en el menú 'Plugins → Mi Plugin' (ruta: /admin/plugins/github_backup).
    """
    total = Challenges.query.count()
    return render_template("admin/challenges/github_backup.html", total_challenges=total)


@my_bp.route("/api/v1/github_backup/challenges", methods=["GET"])
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

import requests
from flask_restx import Namespace, Resource
from flask import redirect, url_for, request
import urllib.parse
from CTFd.utils import get_app_config
from CTFd.plugins.github_backup.models import db, GithubRepositories, GithubChallengeSync, GithubFlagSync, GithubHintSync, UserGitHubToken
from CTFd.utils import user as current_user
from CTFd.models import Challenges, Flags
from CTFd.plugins.dynamic_challenges import DynamicChallenge
from datetime import datetime
from CTFd.models import Tags
from CTFd.models import Hints, db

from CTFd.utils.decorators import admins_only
from CTFd.utils.user import get_current_user

from datetime import datetime
import base64
import time
import jwt
import json

# github_namespace = Namespace(
#     'github', description='Endpoint to manage challenge sync from github'
# )

def generate_jwt():
    # app_id = get_app_config("GITHUB_APP_ID")
    # private_key = open(get_app_config("GITHUB_APP_PRIVATE_KEY_PATH"), "r").read()
    app_id = "1304835"
    private_key = "-----BEGIN RSA PRIVATE KEY-----\nMIIEpQIBAAKCAQEAySt1/kZawxWG72EgRlDWSPOy2KJvfoWpiZQA+4qKhMqyS+WZ\nHjJ9RXZ3fHdpXjp4vYMb5JPTsGcQUS8dPK97vDw4HELfEtAsKI9WO817e3RZh6Mm\nCELoDcvvHJhPOnYiRQmmHXBLqcgYhzXLn3OQs1iAthVCdzA+QeeHdvesoDM6+jGJ\nRiAUvpIoRnaJw1xUv15fBm/r5qnO9VYndEKCNVpcrJsfAx2YsBlV+Qofn/3zXXRn\nkcHwYXCWqKHi7gVQ4+Yl4UwNbM7EYu9R+9jwdD5QdDOa33LySs/k1c4iiuZRfyea\nSJ6GAYBwbr3z+BiFjRtOupyU1SqKYE4VdU+WmwIDAQABAoIBAFiB+J3xEkm2lPGJ\nCAwn0L+0CMHrZaaC5D6VkYEaSSt3is59q8pvaFJBdvyaBQ/iJfErWABPUdnQ3or5\ncaGbi5Mb44v7l+3NDUCjH8ub8nI0lJdqnncQCMzZJtCr6l/MTfOV9TIKkB+Y28HR\nV09GJynhDHAQFngeD6YrWZxsB9VLLKKDilTJnrr9lgpoqXyr+wTANonUtkABo+N8\neLEYvC7RDQNgXFM6gWf3vB5VScI5iwj3i/snrWOCq6i93BZvK/G80V2WzfLU7+Uk\nHOHy6Cb7XlnMe20UIhy2R4agU71tOv1TEkNkTAU2bofGnhF95SDRLutEHS5RzAhK\nCwPoyIECgYEA9UZVWLpWt4Fk8S1fGbvkjjUI6mhAoOOqxNTKdxH2gL6g6KQuoWPr\nnhplyogeBWzlnaOp6M/11n9iiXNDS++1qkf2u+F9fXh2amXhOD0NjYUBhCyHx5kG\nj/qqAbGGcsx4eN6mfrgiXjElJ/AKqSfU+Fcf5uwRzqp1QtR+I/9zFqECgYEA0fdn\nzdCzgoXaOn1XHU5bmSW/jw6y1bQsupEMtVwWTDlUApSwwCR8/unJmQ9alZ0gkBZ+\ngVxtOLvcBTAHagxdBLHE8p3XTYL+2ciZ8/nbAvW9oSx+8WUBKGaNuh2NLvSz+19D\n51HaCoByZ6N266LTEw4vrxQjvr2aAHuL3qgGr7sCgYEA4/3f4Z08dFFj+ke5ids9\nBe9IfVQxFxzppRNDrFDXOS95tSbAbabK4ukYy52hgluKSPFURCPjGeLJPokU+iY1\nULaaJGTjWFk8gYR4SOV/jpgfI7Sc9i1Ji1Zu5yoUlut35KraSxpwX+wA5NHdpwVu\nkvWxot63YsrSOy/4nQ+b9GECgYEAqOJhYlDeMrxLXgR3T6E5WCPewsjF29LCr4YA\nPNhHLyRliHXk/Yfb6oZNm4mYCQOLr5oIQzD+wUWJobqSHCC5qQ78JVIEXdph9va9\nrlpoaScUUlGiAbSGi+KBWRRv/Tbilex4h9V0lkHew7Hd84bSVF9yx1Zhsgh7mKvH\nQ17PkgUCgYEAy2Bcdey9BBFgnR7daX1FoZokb2fEJp/xEwnXNzWyGcunVE2nTIHl\nhXaei0zYvwhCG76GZnp/EJHCvtfFYCSc26X1VwpPUwA3nS+5UDjvoo5ouT/5Rhvv\nDrR0oMwNmmAGmhIcDPH961etE0GydOAnjyYat2fw8P1OZRUUENYb2Dg=\n-----END RSA PRIVATE KEY-----"

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

# @github_namespace.route('/callback')
@my_bp.route("/callback")
def recibe_callback(self):
    installation_id = request.args.get("installation_id")

    if not installation_id:
        return {
            "success": False,
            "message": "No se recibió installation_id."
        }, 400

    user = get_current_user()
    if not user:
        return {
            "success": False,
            "message": "Usuario no autenticado"
        }, 401

    token_entry = UserGitHubToken.query.filter_by(user_id=user.id).first()

    if token_entry:
        token_entry.token = installation_id
    else:
        token_entry = UserGitHubToken(user_id=user.id, token=installation_id)
        db.session.add(token_entry)

    db.session.commit()

    return render_template("admin/challenges/github_backup.html")

# @github_namespace.route('/installations')
@my_bp.route("/installations")
@admins_only
def link_installation():
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
# @github_namespace.route('/repos')
@my_bp.route("/repos")
@admins_only
def get_repos():
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


# Save the selected repositories in the table
@my_bp.route("/repos/selection")
@admins_only
def save_selected_repos(self):
    data = request.get_json()
    selected_repos = data.get("repos", [])
    user = get_current_user()

    if not isinstance(selected_repos, list):
        return {"success": False, "message": "Invalid data format"}, 400

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
                selected=False,
                last_synced_at=None
            )
            db.session.add(new_repo)

    db.session.commit()

    return {"success": True, "message": "Repositories saved correctly"}


# List the saved challenges
@my_bp.route("/repos/saved")
@admins_only
def list_saved_challenges():
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


# Delete a repository from the table
@my_bp.route("/repos/<int:repo_id>")
@admins_only
def delete_repo(repo_id):
    user_id = get_current_user().id
    repo = GithubRepositories.query.filter_by(id=repo_id, user_id=user_id).first()

    if not repo:
        return {"success": False, "message": "Repository not found"}, 404

    # Get and delete challenge syncs
    challenge_syncs = GithubChallengeSync.query.filter_by(github_repo_id=repo.id).all()
    for sync in challenge_syncs:
        db.session.delete(sync)

    # Get and delete flag syncs
    flag_syncs = GithubFlagSync.query.filter_by(github_repo_id=repo.id).all()
    for sync in flag_syncs:
        db.session.delete(sync)

    # Delete hint syncs
    hint_syncs = GithubHintSync.query.filter_by(github_repo_id=repo.id).all()
    for sync in hint_syncs:
        db.session.delete(sync)

    db.session.delete(repo)
    db.session.commit()

    return {"success": True, "message": "Repository and related data deleted correctly."}


# Import from the table button
@my_bp.route("/repos/<int:repo_id>/import")
@admins_only
def import_from_repo(repo_id):
    user_id = get_current_user().id
    repo = GithubRepositories.query.filter_by(id=repo_id, user_id=user_id).first()
    if not repo:
        return {"success": False, "message": "Repository not found"}, 404

    # Get token
    token_entry = UserGitHubToken.query.filter_by(user_id=user_id).first()
    access_token = get_installation_access_token(token_entry.token)

    result = import_challenges_from_repo(repo, access_token, overwrite_existing=False)

    repo.selected = True
    repo.last_synced_at = datetime.now().astimezone(pytz.utc)
    db.session.commit()

    return {
        "success": result["success"],
        "message": f"{result['created']} challenges imported, {result['skipped']} already existing.",
        "errors": result["errors"]
    }


# Validate challenges
def validate_challenge_data(data, path):
    required_fields = ["uuid", "name", "description", "category", "value", "type", "state"]

    for field in required_fields:
        if field not in data:
            raise ValueError(f"{path}: Missing required field '{field}'")

    if not isinstance(data["uuid"], str):
        raise ValueError(f"{path}: 'uuid' must be a string")

    if not isinstance(data["name"], str) or len(data["name"]) > 80:
        raise ValueError(f"{path}: 'name' must be a string of up to 80 characters")

    if not isinstance(data["category"], str) or len(data["category"]) > 80:
        raise ValueError(f"{path}: 'category' must be a string of up to 80 characters")

    if not isinstance(data["description"], str):
        raise ValueError(f"{path}: 'description' must be a string")

    if not isinstance(data["value"], int) or data["value"] < 0:
        raise ValueError(f"{path}: 'value' must be a positive integer")

    if data["type"] not in ["standard", "dynamic"]:
        raise ValueError(f"{path}: 'type' is not valid")

    if data["state"] not in ["visible", "hidden"]:
        raise ValueError(f"{path}: 'state' is not valid")

    return data


def validate_flag_data(flag, path):
    required_fields = ["uuid", "type", "content"]

    for field in required_fields:
        if field not in flag:
            raise ValueError(f"{path}: Flag missing required field '{field}'")

    if not isinstance(flag["uuid"], str):
        raise ValueError(f"{path}: 'uuid' of flag must be a string")

    if flag["type"] not in ["static", "regex"]:
        raise ValueError(f"{path}: Flag type not supported")

    if not isinstance(flag["content"], str):
        raise ValueError(f"{path}: Flag content is not valid")

    if flag["data"] not in ["case_insensitive", ""]:
        raise ValueError(f"{path}: Flag data not supported")


def validate_tags_data(tags, path):
    if not isinstance(tags, list):
        raise ValueError(f"{path}: The 'tags' field must be a list.")
    for tag in tags:
        if not isinstance(tag, str):
            raise ValueError(f"{path}: Tags must be strings.")


def validate_hints_data(hints, path):
    if not isinstance(hints, list):
        raise ValueError(f"{path}: The 'hints' field must be a list.")

    for i, hint in enumerate(hints):
        if not isinstance(hint, dict):
            raise ValueError(f"{path}: Each hint must be a JSON object (index {i}).")

        required_fields = ["uuid", "content", "type"]
        for field in required_fields:
            if field not in hint:
                raise ValueError(f"{path}: Missing required field '{field}' in hint (index {i}).")

        if not isinstance(hint["uuid"], str):
            raise ValueError(f"{path}: The 'uuid' field of the hint (index {i}) must be a string.")

        if not isinstance(hint["content"], str):
            raise ValueError(f"{path}: The 'content' field of the hint (index {i}) must be a string.")

        if not isinstance(hint["type"], str):
            raise ValueError(f"{path}: The 'type' field of the hint (index {i}) must be a string.")

        if "title" in hint and not isinstance(hint["title"], str):
            raise ValueError(f"{path}: The 'title' field of the hint (index {i}) must be a string if present.")

        if "cost" in hint and not isinstance(hint["cost"], int):
            raise ValueError(f"{path}: The 'cost' field of the hint (index {i}) must be an integer if present.")


def validate_dynamic_data(dynamic, path):
    required_fields = ["initial", "minimum", "decay", "function"]

    for field in required_fields:
        if field not in dynamic:
            raise ValueError(f"{path}: Missing required field '{field}' for dynamic challenge")

    if not isinstance(dynamic["initial"], int) or dynamic["initial"] < 0:
        raise ValueError(f"{path}: 'initial' must be a non-negative integer for dynamic challenge")

    if not isinstance(dynamic["minimum"], int) or dynamic["minimum"] < 0:
        raise ValueError(f"{path}: 'minimum' must be a non-negative integer for dynamic challenge")

    if not isinstance(dynamic["decay"], int) or dynamic["decay"] < 0:
        raise ValueError(f"{path}: 'decay' must be a non-negative integer for dynamic challenge")

    if dynamic["function"] not in ["linear", "logarithmic"]:
        raise ValueError(f"{path}: 'function' must be either 'linear' or 'logarithmic' for dynamic challenge")



def import_tags(challenge, tags_data, path, overwrite_existing):
    validate_tags_data(tags_data, path)

    if overwrite_existing:
        Tags.query.filter_by(challenge_id=challenge.id).delete()

    for tag in tags_data:
        tag_entry = Tags(challenge_id=challenge.id, value=tag)
        db.session.add(tag_entry)


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

    # Delete flags that no longer exist in the JSON
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


def import_hints(*, challenge_id, hints, repo_id, challenge_uuid, path, overwrite_existing=False):

    validate_hints_data(hints, path)

    for hint_data in hints:
        uuid = hint_data.get("uuid")
        if not uuid:
            raise ValueError("One of the hints is missing the 'uuid' field.")

        existing_sync = GithubHintSync.query.filter_by(hint_uuid=uuid).first()

        if existing_sync:
            if overwrite_existing:
                hint = Hints.query.get(existing_sync.hint_id)
                if hint:
                    hint.title = hint_data.get("title", "")
                    hint.content = hint_data.get("content", "")
                    hint.cost = hint_data.get("cost", 0)
                    hint.type = hint_data.get("type", "standard")
                    existing_sync.last_updated_at = datetime.utcnow()
                continue
            else:
                continue

        hint = Hints(
            challenge_id=challenge_id,
            title=hint_data.get("title", ""),
            content=hint_data.get("content", ""),
            cost=hint_data.get("cost", 0),
            type=hint_data.get("type", "standard")
        )
        db.session.add(hint)
        db.session.flush()

        db.session.add(GithubHintSync(
            hint_id=hint.id,
            github_repo_id=repo_id,
            hint_uuid=uuid,
            challenge_uuid=challenge_uuid,
            hint_path=path,
            last_updated_at=datetime.utcnow()
        ))


def import_dynamic(challenge_id, dynamic, path, overwrite_existing=False):
    validate_dynamic_data(dynamic, path)

    # If the challenge is being created or updated, we need to handle its dynamic properties
    existing_dynamic = DynamicChallenge.query.filter_by(id=challenge_id).first()

    if existing_dynamic:
        if overwrite_existing:
            existing_dynamic.initial = dynamic.get("initial", 0)
            existing_dynamic.minimum = dynamic.get("minimum", 0)
            existing_dynamic.decay = dynamic.get("decay", 0)
            existing_dynamic.function = dynamic.get("function", "logarithmic")
    else:
        existing_dynamic = DynamicChallenge(
            id=challenge_id,
            initial=dynamic.get("initial", 0),
            minimum=dynamic.get("minimum", 0),
            decay=dynamic.get("decay", 0),
            function=dynamic.get("function", "logarithmic")
        )
        db.session.add(existing_dynamic)

    db.session.flush()


def import_or_update_challenge(challenge_info, repo, path, overwrite_existing):
    uuid = challenge_info.get("uuid")
    if not uuid:
        return None, False, "Missing 'uuid' field"

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
                return None, False, "Synchronized challenge not found in the database"
        else:
            return None, False, "Challenge already synchronized (no overwrite)"
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


# Import challenges
def import_challenges_from_repo(repo, access_token, only_paths=None, overwrite_existing=False):
    headers = {
        "Authorization": f"token {access_token}",
        "Accept": "application/vnd.github+json"
    }

    base_url = f"https://api.github.com/repos/{repo.full_name}/contents/challenges"
    file_list_resp = requests.get(base_url, headers=headers)

    if file_list_resp.status_code != 200:
        return {"success": False, "message": "Could not access /challenges in the repository."}

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
                if error_msg != "Challenge already synchronized (no overwrite)":
                    errors.append({"file": path, "error": error_msg})
                else:
                    count_skipped += 1
                continue

            if challenge.type == "standard":
                if "dynamic" in challenge_info:
                    errors.append({"file": path, "error": "Standard challenges cannot have dynamic data."})
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

                # After importing flags
                try:
                    import_hints(
                        challenge_id=challenge.id,
                        hints=challenge_info.get("hints", []),
                        repo_id=repo.id,
                        challenge_uuid=challenge_info["uuid"],
                        path=path,
                        overwrite_existing=overwrite_existing
                    )
                except ValueError as ve:
                    errors.append({"file": path, "error": str(ve)})
                    continue

                # Import tags
                tags_data = challenge_info.get("tags", [])
                if tags_data:
                    try:
                        import_tags(challenge, tags_data, path, overwrite_existing)
                    except ValueError as ve:
                        errors.append({"file": path, "error": str(ve)})
                        continue
            else:
                # For dynamic challenges, we don't import flags or hints
                if "hints" in challenge_info or "tags" in challenge_info:
                    errors.append({"file": path, "error": "Dynamic challenges cannot have hints or tags."})
                    continue

                # Import dynamic data
                dynamic_data = challenge_info.get("dynamic", {})
                if dynamic_data:
                    try:
                        import_dynamic(
                            challenge_id=challenge.id,
                            dynamic=dynamic_data,
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