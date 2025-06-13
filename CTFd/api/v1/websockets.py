from collections import defaultdict
from decimal import Decimal
from flask_socketio import emit
from CTFd.models import Challenges, Solves, Fails, Submissions, Teams, Users, db
from CTFd.utils.config import is_teams_mode
from CTFd.utils.modes import get_model
from CTFd.utils.scores import get_standings, get_user_standings


def convert_json_compatible(obj):
    """
    Recursively converts data to types that are JSON-serializable.
    Converts Decimal to float, and handles dicts, lists, and tuples.
    """
    if isinstance(obj, dict):
        return {k: convert_json_compatible(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_json_compatible(v) for v in obj]
    elif isinstance(obj, tuple):
        return tuple(convert_json_compatible(v) for v in obj)
    elif isinstance(obj, Decimal):
        return float(obj)
    return obj


def emit_challenge_statistics():
    """
    Emits statistics for each challenge, including solve and fail counts.
    """
    challenges = Challenges.query.all()
    Model = get_model()  # Team or User model depending on mode

    solve_counts = db.session.query(
        Solves.challenge_id,
        db.func.count(Solves.challenge_id).label('solves')
    ).join(Model, Solves.account_id == Model.id).filter(
        Model.banned == False,
        Model.hidden == False
    ).group_by(Solves.challenge_id).all()

    fail_counts = db.session.query(
        Fails.challenge_id,
        db.func.count(Fails.challenge_id).label('fails')
    ).join(Model, Fails.account_id == Model.id).filter(
        Model.banned == False,
        Model.hidden == False
    ).group_by(Fails.challenge_id).all()

    data = []
    for challenge in challenges:
        solve_count = next((s.solves for s in solve_counts if s.challenge_id == challenge.id), 0)
        fail_count = next((f.fails for f in fail_counts if f.challenge_id == challenge.id), 0)
        category = challenge.category if challenge.category else "Sin Categoría"

        data.append({
            'id': challenge.id,
            'name': challenge.name,
            'solves': solve_count,
            'unsolved': fail_count,
            'category': category,
            'points': challenge.value
        })

    emit('challenge_stats', {'data': convert_json_compatible(data)}, namespace='/', broadcast=True)


def emit_scores_distribution():
    """
    Emits the distribution of scores grouped by score brackets.
    """
    challenge_count = Challenges.query.count() or 1
    total_points = (
        Challenges.query.with_entities(db.func.sum(Challenges.value).label("sum"))
        .filter_by(state="visible")
        .first()
        .sum
    ) or 0
    total_points = int(total_points)
    bracket_size = total_points // challenge_count if challenge_count else 1

    standings = get_standings(admin=True)
    brackets = defaultdict(lambda: 0)
    bottom, top = 0, bracket_size
    count = 1

    for t in reversed(standings):
        if (bottom <= t.score <= top) or t.score <= 0:
            brackets[top] += 1
        else:
            count += 1
            bottom, top = (bracket_size * (count - 1), bracket_size * count)
            brackets[top] += 1

    emit('scores_distribution', {
        'data': convert_json_compatible({'brackets': dict(brackets)})
    }, namespace='/', broadcast=True)


def emit_submissions_statistics():
    """
    Emits the count of submissions by type (correct/incorrect).
    """
    data = (
        Submissions.query.with_entities(
            Submissions.type, db.func.count(Submissions.type)
        )
        .group_by(Submissions.type)
        .all()
    )
    emit('submissions_stats', {
        'data': convert_json_compatible(dict(data))
    }, namespace='/', broadcast=True)


def emit_teams_statistics():
    """
    Emits the total number of registered teams.
    """
    registered = Teams.query.count()
    emit('teams_stats', {
        'data': convert_json_compatible({'registered': registered})
    }, namespace='/', broadcast=True)


def emit_users_statistics():
    """
    Emits the number of registered and verified users.
    """
    registered = Users.query.count()
    confirmed = Users.query.filter_by(verified=True).count()
    emit('users_stats', {
        'data': convert_json_compatible({'registered': registered, 'confirmed': confirmed})
    }, namespace='/', broadcast=True)


def emit_solve_percentages_statistics():
    """
    Emits solve/fail percentages for each challenge and overall totals.
    """
    challenges = Challenges.query.all()

    solve_counts = db.session.query(
        Solves.challenge_id,
        db.func.count(Solves.challenge_id)
    ).group_by(Solves.challenge_id).all()
    solve_dict = dict(solve_counts)

    fail_counts = db.session.query(
        Fails.challenge_id,
        db.func.count(Fails.challenge_id)
    ).group_by(Fails.challenge_id).all()
    fail_dict = dict(fail_counts)

    challenge_stats = []
    total_solves = 0
    total_fails = 0

    for challenge in challenges:
        solves = solve_dict.get(challenge.id, 0)
        fails = fail_dict.get(challenge.id, 0)
        total = solves + fails

        total_solves += solves
        total_fails += fails

        if total == 0:
            solve_percentage = 0
            unsolve_percentage = 0
        else:
            solve_percentage = (solves / total) * 100
            unsolve_percentage = (fails / total) * 100

        challenge_stats.append({
            'id': challenge.id,
            'name': challenge.name,
            'solves': solves,
            'fails': fails,
            'solve_percentage': round(solve_percentage, 2),
            'unsolve_percentage': round(unsolve_percentage, 2),
        })

    emit('solve_percentages_stats', {
        'data': convert_json_compatible({
            'solved': total_solves,
            'unsolved': total_fails,
            'challenges': challenge_stats
        })
    }, namespace='/', broadcast=True)


def emit_scoreboard_statistics():
    """
    Emits scoreboard standings and user standings (if in team mode).
    """
    standings = get_standings(admin=True)
    user_standings = get_user_standings(admin=True) if is_teams_mode() else None
    mode = "teams" if is_teams_mode() else "users"

    serializable_standings = [
        {
            "id": x.account_id,
            "name": x.name,
            "score": int(x.score),
            "bracket_id": x.bracket_id,
            "bracket_name": x.bracket_name,
        }
        for x in standings
    ]

    serializable_user_standings = None
    if user_standings:
        serializable_user_standings = [
            {
                "user_id": user.user_id,
                "name": user.name,
                "score": user.score,
                "hidden": user.hidden,
                "oauth_id": user.oauth_id,
            }
            for user in user_standings
        ]

    data = {
        "standings": serializable_standings,
        "user_standings": serializable_user_standings,
        "mode": mode,
    }

    emit('scoreboard_update', {
        'data': convert_json_compatible(data)
    }, namespace='/', broadcast=True)
