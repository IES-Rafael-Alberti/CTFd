from collections import defaultdict
from flask_socketio import emit
from CTFd.models import Challenges, Solves, Fails, Submissions, Teams, Users, db
from CTFd.utils.config import is_teams_mode
from CTFd.utils.modes import get_model
from CTFd.utils.scores import get_standings, get_user_standings

def emit_challenge_statistics():
    challenges = Challenges.query.all()
    Model = get_model()

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

        # Si no hay categoría asignada, se pone como "Sin Categoría"
        category = challenge.category if challenge.category else "Sin Categoría"

        data.append({
            'id': challenge.id,
            'name': challenge.name,
            'solves': solve_count,
            'unsolved': fail_count,
            'category': category,
            'points': challenge.value
        })

    emit('challenge_stats', {'data': data}, namespace='/', broadcast=True)

def emit_scores_distribution():
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
        if ((t.score >= bottom) and (t.score <= top)) or t.score <= 0:
            brackets[top] += 1
        else:
            count += 1
            bottom, top = (bracket_size * (count - 1), bracket_size * count)
            brackets[top] += 1

    emit('scores_distribution', {'data': {'brackets': dict(brackets)}}, namespace='/', broadcast=True)

def emit_submissions_statistics():
    data = (
        Submissions.query.with_entities(
            Submissions.type, db.func.count(Submissions.type)
        )
        .group_by(Submissions.type)
        .all()
    )
    emit('submissions_stats', {'data': dict(data)}, namespace='/', broadcast=True)

def emit_teams_statistics():
    registered = Teams.query.count()
    emit('teams_stats', {'data': {'registered': registered}}, namespace='/', broadcast=True)

def emit_users_statistics():
    registered = Users.query.count()
    confirmed = Users.query.filter_by(verified=True).count()
    emit('users_stats', {'data': {'registered': registered, 'confirmed': confirmed}}, namespace='/', broadcast=True)

def emit_solve_percentages_statistics():
    challenges = Challenges.query.all()

    # Obtener solves y fails agrupados por challenge
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
        'data': {
            'solved': total_solves,
            'unsolved': total_fails,
            'challenges': challenge_stats
        }
    }, namespace='/', broadcast=True)

def emit_scoreboard_statistics():
    standings = get_standings(admin=True)
    user_standings = get_user_standings(admin=True) if is_teams_mode() else None

    # Obtener el modo actual (teams o users)
    mode = "teams" if is_teams_mode() else "users"

    # Convert standings to a serializable format
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

    # Convert user_standings to a serializable format
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

    emit('scoreboard_update', {'data': data}, namespace='/', broadcast=True)