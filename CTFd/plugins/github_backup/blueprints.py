# plugins/github_backup/blueprints.py
import pytz
from flask import Blueprint, render_template, jsonify, Response

from CTFd.plugins import bypass_csrf_protection
from CTFd.plugins.github_backup.expot_data import is_imported_from_github, prepare_json
from CTFd.plugins.github_backup.import_data import import_challenges_from_repo
from CTFd.utils import get_app_config
from CTFd.utils.decorators import admins_only

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
@admins_only
def vista_panel_admin():
    """
    Esta función renderiza la nueva página que aparecerá
    en el menú 'Plugins → Mi Plugin' (ruta: /admin/plugins/github_backup).
    """
    installation_url = config["GITHUB_APP_INSTALLATION_URL"]
    return render_template("admin/challenges/github_backup.html", installation_url=installation_url)


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
from CTFd.plugins.github_backup.models import db, GithubRepositories, GithubChallengeSync, GithubFlagSync, GithubHintSync, UserGitHubToken
from CTFd.models import db, Challenges, Flags, Hints, Tags
import json
from flask import request, Response, send_file, redirect

from CTFd.utils.decorators import admins_only
from CTFd.utils.user import get_current_user, is_admin

from datetime import datetime
import time
import jwt

import io
import zipfile
from CTFd.plugins.github_backup.config import config

# github_namespace = Namespace(
#     'github', description='Endpoint to manage challenge sync from github'
# )

def generate_jwt():
    """
    Generates a JWT for the GitHub App.
    """
    app_id = config["GITHUB_APP_ID"]
    private_key = config["GITHUB_APP_PRIVATE_KEY"]

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

# TODO esta implementada, pero me parece que no se usa. Github lo envia despues de la instalacion
# @github_namespace.route('/callback')
@my_bp.route("/plugins/github_backup/callback", methods=["GET"])
def recibe_callback():
    installation_id = request.args.get("installation_id")

    if not installation_id:
        return {
            "success": False,
            "message": "No installation_id received."
        }, 400

    user = get_current_user()
    if not user:
        return {
            "success": False,
            "message": "User not authenticated"
        }, 401

    token_entry = UserGitHubToken.query.filter_by(user_id=user.id).first()

    if token_entry:
        token_entry.token = installation_id
    else:
        token_entry = UserGitHubToken(user_id=user.id, token=installation_id)
        db.session.add(token_entry)

    db.session.commit()

    return redirect("/admin/plugins/github_backup")

# @github_namespace.route('/installations')
@my_bp.route("/plugins/github_backup/installations", methods=["GET"])
@admins_only
def link_installation():
    jwt_token = generate_jwt()

    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Accept": "application/vnd.github+json"
    }

    r = requests.get("https://api.github.com/app/installations", headers=headers)

    if r.status_code != 200:
        return {"success": False, "message": "Error retrieving installations"}, 400

    installations = r.json()
    if not isinstance(installations, list):
        return {"success": False, "message": "Unexpected response"}, 400

    if len(installations) == 1:
        installation_id = installations[0]["id"]
    else:
        return {"success": False, "message": "Multiple installations. Filter required.", "r": r.json()}, 400

    user_id = get_current_user().id
    token_entry = UserGitHubToken.query.filter_by(user_id=user_id).first()

    if token_entry:
        token_entry.token = installation_id
    else:
        token_entry = UserGitHubToken(user_id=user_id, token=installation_id)
        db.session.add(token_entry)

    db.session.commit()

    return {"success": True, "message": f"Installation ID {installation_id} saved correctly."}

# lista los repositorios de la cuenta de usuario
@my_bp.route("/plugins/github_backup/repos", methods=["GET"])
@admins_only
def get_repos():
    user_id = get_current_user().id
    token_entry = UserGitHubToken.query.filter_by(user_id=user_id).first()

    if not token_entry:
        return {"success": False, "message": "Installation ID not found"}, 401

    installation_id = get_installation_access_token(token_entry.token)

    if not installation_id:
        return {"success": False, "message": "Could not obtain installation ID"}, 400

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
                "message": "Could not retrieve repositories",
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
@my_bp.route("/plugins/github_backup/repos/selection", methods=["POST"])
@admins_only
def save_selected_repos():
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


# List the saved repos
@my_bp.route("/plugins/github_backup/repos/saved", methods=["GET"])
@admins_only
def list_saved_repos():
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
@my_bp.route("/plugins/github_backup/repos/<int:repo_id>", methods=["DELETE"])
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
@my_bp.route("/plugins/github_backup/repos/<int:repo_id>/import", methods=["POST"])
@admins_only
def import_from_repo(repo_id):
    data = request.get_json()
    delete_mode = data.get("delete_mode")

    try:
        user_id = get_current_user().id
        repo = GithubRepositories.query.filter_by(id=repo_id, user_id=user_id).first()
        if not repo:
            return {"success": False, "message": "Repository not found"}, 404

        # Get token
        token_entry = UserGitHubToken.query.filter_by(user_id=user_id).first()
        if not token_entry:
            return {"success": False, "message": "No GitHub token configured"}, 400
        access_token = get_installation_access_token(token_entry.token)

        result = import_challenges_from_repo(repo, access_token, overwrite_existing=True, delete_mode=delete_mode)

        repo.selected = True
        repo.last_synced_at = datetime.now().astimezone(pytz.utc)
        db.session.commit()

        return {
            "success": result["success"],
            "message": f"{result['created']} challenges imported, {result['updated']} challenges updated, {result['skipped']} already existing, {result['removed']} deleted",
            "errors": result["errors"]
        }
    except Exception as e:
        return {"success": False, "message": e}, 500


@my_bp.route("/plugins/github_backup/challenge/<int:challenge_id>/download", methods=["GET"])
@admins_only
def download_challenge(challenge_id: int) -> tuple[dict[str, bool | str], int] | Response:
    """
    Handles the downloading of a specific challenge data in JSON format. The endpoint generates
    a JSON file for the provided challenge ID and sends it as a downloadable attachment. The
    JSON content is obtained from a helper function and formatted with UTF-8 encoding.

    Args:
        challenge_id (int): The unique ID of the challenge to be downloaded.

    Returns:
        tuple[dict[str, bool | str], int] | Response: A JSON response with success status and
        message in case of errors, or a Response object with the generated JSON file for
        successful requests.

    Raises:
        ValueError: Raised if the provided challenge ID is invalid or the challenge cannot
        be processed.
        Exception: Raised for unexpected internal errors during the process.
    """

    try:
        data, name = prepare_json(challenge_id)

        json_bytes = json.dumps(data, indent=4, ensure_ascii=False).encode("utf-8-sig")

        return Response(
            json_bytes,
            mimetype="application/json",
            headers={
                "Content-Disposition": f'attachment; filename="challenge_{name}.json"'
            },
        )
    except ValueError as e:
        return {"success": False, "message": str(e)}, 400
    except Exception as e:
        return {"success": False, "message": f"Unexpected error: {str(e)}"}, 500

@my_bp.route("/plugins/github_backup/challenges/download/example", methods=["GET"])
@admins_only
def download_example_json():
    example = {
        "challenge": {
            "uuid": "000000000000000",
            "name": "knock, knock, Neo",
            "description": "Wake up. The matrix has you...",
            "attribution": "author",
            "connection_info": "https://link.com",
            "max_attempts": 3,
            "value": 50,
            "category": "web",
            "type": "standard",
            "state": "visibe or hidden",
            "flags": [
                {
                    "uuid": "000000000000000",
                    "type": "static",
                    "content": "flag{answer}",
                    "data": "case_insensitive",
                },
                {
                    "uuid": "000000000000000",
                    "type": "regex",
                    "content": "flag{.a*}",
                    "data": "",
                }
            ],
            "tags": [
                "tag1", "tag2"
            ],
            "hints": [
                {
                    "uuid": "000000000000000",
                    "title": "Hint 1",
                    "type": "standard",
                    "content": "Follow the white rabbit...",
                    "cost": 10
                },
                {
                    "uuid": "000000000000000",
                    "title": "Hint 2",
                    "type": "?",
                    "content": "?",
                    "cost": 20
                }
            ],
        }
    }

    json_bytes = json.dumps(example, indent=4, ensure_ascii=False).encode("utf-8-sig")

    return Response(
        json_bytes,
        mimetype="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="challenge_example.json"'
        },
    )


@my_bp.route("/plugins/github_backup/challenges", methods=["GET"])
@admins_only
def get_challenges():
    challenges = Challenges.query.all()

    data = []
    for challenge in challenges:
        is_imported = is_imported_from_github(challenge.id)
        data.append({
            "id": challenge.id,
            "name": challenge.name,
            "imported": is_imported,
        })

    return {"success": True, "challenges": data}

@my_bp.route("/plugins/github_backup/challenges/download", methods=["POST"])
@admins_only
def download_multiple_challenges():
    """
    Recibe una lista de challenge IDs, genera un ZIP con los JSON de cada uno
    y lo devuelve como descarga.
    """
    try:
        challenge_ids = request.json.get("challenge_ids", [])
        if not challenge_ids:
            return {"success": False, "message": "No challenge IDs provided"}, 400

        # Creamos un buffer en memoria
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for cid in challenge_ids:
                try:
                    data, name = prepare_json(int(cid))
                    json_bytes = json.dumps(data, indent=4, ensure_ascii=False).encode("utf-8-sig")
                    zip_file.writestr(f"challenge_{name}.json", json_bytes)
                except Exception as e:
                    zip_file.writestr(f"challenge_{cid}_error.txt", str(e))

        zip_buffer.seek(0)

        return send_file(
            zip_buffer,
            mimetype="application/zip",
            as_attachment=True,
            download_name="challenges_export.zip",
        )

    except Exception as e:
        return {"success": False, "message": f"Unexpected error: {str(e)}"}, 500