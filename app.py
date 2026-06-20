"""
Prode Mundial 2026 — Flask API Server

Serves the web frontend and provides API endpoints for match simulation
using the Dixon-Coles bivariate Poisson model.
"""

import json
import os
from datetime import datetime
from flask import Flask, jsonify, request, render_template, send_from_directory

from engine.simulation import DixonColesSimulator
from engine.calibration import suggest_xg, suggest_rho, validate_against_market, fetch_fotmob_stats

app = Flask(__name__)

# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
SIMS_DIR = os.path.join(DATA_DIR, 'simulations')

# Fallback to /tmp/simulations on Vercel or read-only filesystems
if os.environ.get('VERCEL') or not os.access(DATA_DIR or '.', os.W_OK):
    SIMS_DIR = '/tmp/simulations'

os.makedirs(SIMS_DIR, exist_ok=True)


def load_json(filename):
    """Load a JSON file from the data directory."""
    with open(os.path.join(DATA_DIR, filename), 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(filename, data):
    """Save data to a JSON file in the data directory."""
    with open(os.path.join(DATA_DIR, filename), 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_teams_dict():
    """Return teams data indexed by code."""
    teams_data = load_json('teams.json')
    return {t['code']: t for t in teams_data['teams']}


# ---------------------------------------------------------------------------
# Routes — Pages
# ---------------------------------------------------------------------------
@app.route('/')
def index():
    """Serve the main SPA."""
    return render_template('index.html')


# ---------------------------------------------------------------------------
# Routes — API
# ---------------------------------------------------------------------------
@app.route('/api/teams')
def api_teams():
    """Return all teams data."""
    data = load_json('teams.json')
    return jsonify(data)


@app.route('/api/matches')
def api_matches():
    """Return all matches data with optional filters."""
    data = load_json('matches.json')

    # Optional filters
    status = request.args.get('status')
    group = request.args.get('group')
    date = request.args.get('date')

    matches = data['matches']
    if status:
        matches = [m for m in matches if m.get('status') == status]
    if group:
        matches = [m for m in matches if m.get('group') == group]
    if date:
        matches = [m for m in matches if m.get('date') == date]

    return jsonify({
        'matches': matches,
        'tournament_stats': data.get('tournament_stats', {})
    })


@app.route('/api/groups')
def api_groups():
    """Return group standings calculated from match results."""
    teams_data = load_json('teams.json')
    matches_data = load_json('matches.json')
    teams_dict = {t['code']: t for t in teams_data['teams']}

    # Initialize standings
    standings = {}
    for team in teams_data['teams']:
        code = team['code']
        standings[code] = {
            'code': code,
            'name': team['name'],
            'flag': team['flag'],
            'group': team['group'],
            'played': 0, 'won': 0, 'drawn': 0, 'lost': 0,
            'gf': 0, 'ga': 0, 'gd': 0, 'points': 0
        }

    # Calculate from played matches
    for match in matches_data['matches']:
        if match.get('status') != 'played':
            continue

        h = match['home']
        a = match['away']
        hg = match['home_goals']
        ag = match['away_goals']

        standings[h]['played'] += 1
        standings[a]['played'] += 1
        standings[h]['gf'] += hg
        standings[h]['ga'] += ag
        standings[a]['gf'] += ag
        standings[a]['ga'] += hg

        if hg > ag:
            standings[h]['won'] += 1
            standings[h]['points'] += 3
            standings[a]['lost'] += 1
        elif hg == ag:
            standings[h]['drawn'] += 1
            standings[h]['points'] += 1
            standings[a]['drawn'] += 1
            standings[a]['points'] += 1
        else:
            standings[a]['won'] += 1
            standings[a]['points'] += 3
            standings[h]['lost'] += 1

        standings[h]['gd'] = standings[h]['gf'] - standings[h]['ga']
        standings[a]['gd'] = standings[a]['gf'] - standings[a]['ga']

    # Group teams by group
    groups = {}
    for code, team_data in teams_dict.items():
        group = team_data['group']
        if group not in groups:
            groups[group] = []
        groups[group].append(standings[code])

    # Sort each group
    for group in groups:
        groups[group].sort(
            key=lambda x: (-x['points'], -x['gd'], -x['gf'])
        )

    return jsonify(groups)


@app.route('/api/simulate', methods=['POST'])
def api_simulate():
    """
    Run a Dixon-Coles simulation.

    Expected JSON body:
    {
        "home_team": "ARG",
        "away_team": "AUT",
        "lam_home": 1.8,
        "lam_away": 0.9,
        "rho": -0.06,
        "n_sims": 300000,
        "market_odds": {"home": 1.35, "draw": 5.0, "away": 9.0}  // optional
    }
    """
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No JSON data provided'}), 400

    # Required params
    lam_home = data.get('lam_home')
    lam_away = data.get('lam_away')
    if lam_home is None or lam_away is None:
        return jsonify({'error': 'lam_home and lam_away are required'}), 400

    # Optional params with defaults
    rho = data.get('rho', -0.06)
    n_sims = min(data.get('n_sims', 300000), 500000)  # Cap at 500k
    home_team = data.get('home_team', 'HOME')
    away_team = data.get('away_team', 'AWAY')

    try:
        # Run simulation
        sim = DixonColesSimulator(
            lam_home=float(lam_home),
            lam_away=float(lam_away),
            rho=float(rho),
            n_sims=int(n_sims)
        )
        results = sim.get_results()

        # Add team info
        teams_dict = get_teams_dict()
        results['home_team'] = teams_dict.get(home_team, {'code': home_team, 'name': home_team})
        results['away_team'] = teams_dict.get(away_team, {'code': away_team, 'name': away_team})

        # Market validation if odds provided
        market_odds = data.get('market_odds')
        if market_odds:
            results['market_validation'] = validate_against_market(
                results['one_x_two'],
                market_odds
            )

        results['timestamp'] = datetime.now().isoformat()

        return jsonify(results)

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'Simulation error: {str(e)}'}), 500


@app.route('/api/suggest', methods=['POST'])
def api_suggest():
    """
    Suggest xG and rho values for a matchup.

    Expected JSON body:
    {
        "home_team": "ARG",
        "away_team": "AUT",
        "stage": "group",
        "motivation_home": "normal",
        "motivation_away": "normal"
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No JSON data provided'}), 400

    teams_dict = get_teams_dict()
    home_code = data.get('home_team')
    away_code = data.get('away_team')

    if home_code not in teams_dict or away_code not in teams_dict:
        return jsonify({'error': 'Unknown team code'}), 400

    home_team = teams_dict[home_code]
    away_team = teams_dict[away_code]

    # Fetch live stats from FotMob CDN
    live_stats = fetch_fotmob_stats()

    # Suggest xG for home team
    home_context = {
        'stage': data.get('stage', 'group'),
        'motivation': data.get('motivation_home', 'normal'),
        'live_stats': live_stats.get(home_code),
        'opp_live_stats': live_stats.get(away_code)
    }
    away_context = {
        'stage': data.get('stage', 'group'),
        'motivation': data.get('motivation_away', 'normal'),
        'live_stats': live_stats.get(away_code),
        'opp_live_stats': live_stats.get(home_code)
    }

    home_suggestion = suggest_xg(home_team, away_team, home_context)
    away_suggestion = suggest_xg(away_team, home_team, away_context)
    rho_suggestion = suggest_rho(
        home_team.get('style', 'balanced'),
        away_team.get('style', 'balanced'),
        data.get('stage', 'group')
    )

    return jsonify({
        'home_team': home_team,
        'away_team': away_team,
        'home_xg': home_suggestion,
        'away_xg': away_suggestion,
        'rho': rho_suggestion,
        'live_stats': {
            'home': live_stats.get(home_code),
            'away': live_stats.get(away_code)
        }
    })


@app.route('/api/save-simulation', methods=['POST'])
def api_save_simulation():
    """Save a simulation result for future reference."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No JSON data provided'}), 400

    # Generate filename from teams and timestamp
    home = data.get('home_team', {}).get('code', 'HOME')
    away = data.get('away_team', {}).get('code', 'AWAY')
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{home}_vs_{away}_{ts}.json"

    filepath = os.path.join(SIMS_DIR, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return jsonify({'saved': filename})


@app.route('/api/simulations')
def api_simulations():
    """List saved simulations."""
    files = []
    if os.path.exists(SIMS_DIR):
        for f in sorted(os.listdir(SIMS_DIR), reverse=True):
            if f.endswith('.json'):
                files.append(f)
    return jsonify({'simulations': files})


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    app.run(debug=True, port=5000)
