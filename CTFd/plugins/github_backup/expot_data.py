from CTFd.plugins.github_backup.models import GithubChallengeSync, GithubFlagSync, GithubHintSync
from CTFd.models import Tags, Flags, Hints, Challenges
from CTFd.plugins.github_backup.utils import generate_uuid


def is_imported_from_github(challenge_id: int) -> bool:
    """
    Determines if a challenge is imported from GitHub.

    This function checks whether a given challenge, identified by its
    challenge_id, has been imported from GitHub. It queries the
    GithubChallengeSync database table to determine if there is a record
    indicating synchronization with GitHub for that challenge.

    Args:
        challenge_id (int): The unique identifier for the challenge.

    Returns:
        bool: True if the challenge is imported from GitHub, False otherwise.
    """
    challenge_sync = GithubChallengeSync.query.filter_by(challenge_id=challenge_id).first()
    return bool(challenge_sync)


def prepare_json(challenge_id: int) -> tuple[dict, str]:
    """
    Generates a JSON-like structure and corresponding name for a given challenge.

    This function retrieves the challenge data from the database using the provided
    challenge ID. It compiles the challenge information along with associated flags, tags,
    and hints into a dictionary structure. This structure is returned along with the name
    of the challenge.

    Args:
        challenge_id (int): The ID of the challenge to be processed.

    Returns:
        tuple[dict, str]: A tuple containing:
        - A dictionary with the challenge details, flags, tags, and hints.
        - The challenge name.

    Raises:
        ValueError: If the challenge with the given ID is not found.
    """

    challenge = Challenges.query.filter_by(id=challenge_id).first()
    if not challenge:
        raise ValueError("Challenge not found")

    challenge_sync = GithubChallengeSync.query.filter_by(challenge_id=challenge.id).first()

    if not challenge_sync:
        chellenge_uuid = generate_uuid()
    else:
        chellenge_uuid = challenge_sync.challenge_uuid

    # Prepare challenge data
    data = {
        "challenge": {
            "uuid": chellenge_uuid,
            "name": challenge.name,
            "description": challenge.description,
            "attribution": challenge.attribution,
            "connection_info": challenge.connection_info,
            "max_attempts": challenge.max_attempts,
            "value": challenge.value,
            "category": challenge.category,
            "type": challenge.type,
            "state": challenge.state,
            "flags": [],
            "tags": [],
            "hints": [],
        }
    }

    # Prepare flags data
    flags = Flags.query.filter_by(challenge_id=challenge.id).all()
    for f in flags:
        flag_sync = GithubFlagSync.query.filter_by(flag_id=f.id).first()

        if not flag_sync:
            flag_uuid = generate_uuid()
        else:
            flag_uuid = flag_sync.flag_uuid

        data["challenge"]["flags"].append({
            "uuid": flag_uuid,
            "type": f.type,
            "content": f.content,
            "data": f.data
        })

    # Prepare tags data
    tags = Tags.query.filter_by(challenge_id=challenge.id).all()
    data["challenge"]["tags"] = [t.value for t in tags]

    # Prepare hints data
    hints = Hints.query.filter_by(challenge_id=challenge.id).all()
    for h in hints:
        hint_sync = GithubHintSync.query.filter_by(hint_id=h.id).first()

        if not hint_sync:
            hint_uuid = generate_uuid()
        else:
            hint_uuid = hint_sync.hint_uuid

        data["challenge"]["hints"].append({
            "uuid": hint_uuid,
            "title": h.content,
            "type": h.type,
            "content": h.content,
            "cost": h.cost
        })

    return data, challenge.name
