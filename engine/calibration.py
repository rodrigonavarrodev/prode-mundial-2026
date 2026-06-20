"""
xG Calibration Helpers.

Provides utilities to suggest adjusted xG values based on team strength,
opponent quality, and match context. Also includes market validation tools.
"""

import os
import json
import time
import requests

FOTMOB_LEAGUE_ID = 77
FOTMOB_TEAM_MAPPING = {
    'ALG': 6317, 'ARG': 6706, 'AUS': 6716, 'AUT': 8255, 'BEL': 8263,
    'BIH': 10106, 'BRA': 8256, 'CAN': 5810, 'CPV': 5888, 'COL': 8258,
    'CRO': 10155, 'CUW': 287981, 'CZE': 8496, 'COD': 6321, 'ECU': 6707,
    'EGY': 10255, 'ENG': 8491, 'FRA': 6723, 'GER': 8570, 'GHA': 6714,
    'HAI': 5934, 'IRN': 6711, 'IRQ': 5819, 'CIV': 6709, 'JPN': 6715,
    'JOR': 5816, 'MEX': 6710, 'MAR': 6262, 'NED': 6708, 'NZL': 5820,
    'NOR': 8492, 'PAN': 5922, 'PAR': 6724, 'POR': 8361, 'QAT': 5902,
    'KSA': 7795, 'SCO': 8498, 'SEN': 6395, 'RSA': 6316, 'KOR': 7804,
    'ESP': 6720, 'SWE': 8520, 'SUI': 6717, 'TUN': 6719, 'TUR': 6595,
    'USA': 6713, 'URU': 5796, 'UZB': 8700
}

CACHE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'fotmob_cache.json')
# Use /tmp for cache on Vercel or in read-only environments
if os.environ.get('VERCEL') or not os.access(os.path.dirname(CACHE_FILE) or '.', os.W_OK):
    CACHE_FILE = '/tmp/fotmob_cache.json'

CACHE_EXPIRY = 3600  # 1 hour

def fetch_fotmob_stats():
    """
    Fetch expected goals and conceded stats from FotMob CDN.
    Uses local cache to avoid rate limits/heavy traffic.
    Returns:
        dict: Mapped team stats {team_code: {'xg': avg_xg, 'xga': avg_xga, 'matches': matches_played}}
    """
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                cached = json.load(f)
            if time.time() - cached.get('timestamp', 0) < CACHE_EXPIRY:
                return cached.get('data', {})
        except Exception:
            pass

    stats_data = {}
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        league_url = f"https://www.fotmob.com/api/data/leagues?id={FOTMOB_LEAGUE_ID}"
        res = requests.get(league_url, headers=headers, timeout=5)
        
        xg_url = None
        xga_url = None
        
        if res.status_code == 200:
            league_data = res.json()
            teams_stats = league_data.get('stats', {}).get('teams', [])
            for item in teams_stats:
                name = item.get('name')
                if name == 'expected_goals_team':
                    xg_url = item.get('fetchAllUrl')
                elif name == 'expected_goals_conceded_team':
                    xga_url = item.get('fetchAllUrl')

        if not xg_url:
            xg_url = f"https://data.fotmob.com/stats/{FOTMOB_LEAGUE_ID}/season/24254/expected_goals_team.json"
        if not xga_url:
            xga_url = f"https://data.fotmob.com/stats/{FOTMOB_LEAGUE_ID}/season/24254/expected_goals_conceded_team.json"

        xg_res = requests.get(xg_url, headers=headers, timeout=5)
        if xg_res.status_code == 200:
            xg_data = xg_res.json()
            stat_list = xg_data.get('TopLists', [{}])[0].get('StatList', [])
            for item in stat_list:
                team_id = item.get('TeamId')
                tot_xg = item.get('StatValue', 0.0)
                matches = item.get('MatchesPlayed', 0)
                if matches > 0:
                    avg_xg = tot_xg / matches
                    stats_data[team_id] = {'xg': avg_xg, 'matches': matches}

        xga_res = requests.get(xga_url, headers=headers, timeout=5)
        if xga_res.status_code == 200:
            xga_data = xga_res.json()
            stat_list = xga_data.get('TopLists', [{}])[0].get('StatList', [])
            for item in stat_list:
                team_id = item.get('TeamId')
                tot_xga = item.get('StatValue', 0.0)
                matches = item.get('MatchesPlayed', 0)
                if matches > 0 and team_id in stats_data:
                    avg_xga = tot_xga / matches
                    stats_data[team_id]['xga'] = avg_xga
                    stats_data[team_id]['matches'] = max(stats_data[team_id]['matches'], matches)
                elif matches > 0:
                    avg_xga = tot_xga / matches
                    stats_data[team_id] = {'xga': avg_xga, 'matches': matches}

        mapped_data = {}
        for code, team_id in FOTMOB_TEAM_MAPPING.items():
            if team_id in stats_data:
                team_info = stats_data[team_id]
                mapped_data[code] = {
                    'xg': round(team_info.get('xg', 0.0), 2),
                    'xga': round(team_info.get('xga', 0.0), 2),
                    'matches': team_info.get('matches', 0)
                }

        try:
            os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
            with open(CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump({'timestamp': time.time(), 'data': mapped_data}, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

        return mapped_data
    except Exception as e:
        print(f"Error fetching stats from FotMob: {e}")
        return {}


def suggest_xg(team, opponent, context=None):
    """
    Suggest adjusted xG for a team against a specific opponent.

    The adjustment logic:
    1. Start with the team's base offensive xG
    2. Adjust based on opponent's defensive quality (xGA)
    3. Apply context modifiers (tournament stage, motivation, etc.)

    Args:
        team: dict with 'xg_base', 'style', etc.
        opponent: dict with 'xga_base', 'style', etc.
        context: dict with optional modifiers like 'stage', 'motivation',
                 'tournament_avg_goals', 'key_absences', etc.

    Returns:
        dict with 'xg' (adjusted value) and 'reasoning' (explanation).
    """
    if context is None:
        context = {}

    base_xg = team.get('xg_base', 1.0)
    opp_xga = opponent.get('xga_base', 1.2)

    live_stats = context.get('live_stats')
    opp_live_stats = context.get('opp_live_stats')

    used_live_team = False
    used_live_opp = False

    if live_stats and live_stats.get('matches', 0) > 0:
        base_xg = live_stats['xg']
        used_live_team = True

    if opp_live_stats and opp_live_stats.get('matches', 0) > 0:
        opp_xga = opp_live_stats['xga']
        used_live_opp = True

    # Average defensive quality is ~1.2 xGA. If opponent concedes less,
    # reduce our xG; if more, increase it.
    avg_xga = 1.2
    defensive_factor = opp_xga / avg_xga
    adjusted = base_xg * defensive_factor

    reasoning_parts = []
    if used_live_team:
        reasoning_parts.append(f"Base xG (FotMob Live, {live_stats['matches']} matches): {base_xg:.2f}")
    else:
        reasoning_parts.append(f"Base xG (Historical Base): {base_xg:.2f}")

    if used_live_opp:
        reasoning_parts.append(f"Opponent xGA (FotMob Live, {opp_live_stats['matches']} matches): {opp_xga:.2f} (factor: {defensive_factor:.2f})")
    else:
        reasoning_parts.append(f"Opponent xGA (Historical Base): {opp_xga:.2f} (factor: {defensive_factor:.2f})")

    reasoning_parts.append(f"After opponent adjustment: {adjusted:.2f}")

    # Style matchup adjustment
    team_style = team.get('style', 'balanced')
    opp_style = opponent.get('style', 'balanced')

    if team_style == 'offensive' and opp_style == 'defensive':
        # Offensive team vs low block: slight reduction
        adjusted *= 0.92
        reasoning_parts.append(
            "Offensive vs defensive block: -8% efficiency"
        )
    elif team_style == 'offensive' and opp_style == 'offensive':
        # Open game: slight boost
        adjusted *= 1.05
        reasoning_parts.append(
            "Open game (both offensive): +5%"
        )
    elif team_style == 'defensive' and opp_style == 'defensive':
        # Tight game: slight reduction
        adjusted *= 0.93
        reasoning_parts.append(
            "Tight game (both defensive): -7%"
        )

    # Tournament stage modifier
    stage = context.get('stage', 'group')
    if stage == 'knockout':
        adjusted *= 0.90
        reasoning_parts.append(
            "Knockout stage (more cautious): -10%"
        )
    elif stage == 'final':
        adjusted *= 0.85
        reasoning_parts.append(
            "Final (maximum caution): -15%"
        )

    # Tournament average goals adjustment
    tournament_avg = context.get('tournament_avg_goals')
    if tournament_avg:
        # Normal WC average is ~2.5 goals/game, so ~1.25 per team
        normal_avg = 1.25
        tournament_factor = tournament_avg / (normal_avg * 2)
        adjusted *= tournament_factor
        reasoning_parts.append(
            f"Tournament goals trend ({tournament_avg:.1f}/game): "
            f"factor {tournament_factor:.2f}"
        )

    # Key absences
    absence_impact = context.get('absence_impact', 0)
    if absence_impact != 0:
        adjusted *= (1 + absence_impact)
        direction = "boost" if absence_impact > 0 else "reduction"
        reasoning_parts.append(
            f"Key player impact: {absence_impact:+.0%} {direction}"
        )

    # Motivation factor
    motivation = context.get('motivation', 'normal')
    if motivation == 'must_win':
        adjusted *= 1.08
        reasoning_parts.append("Must-win motivation: +8%")
    elif motivation == 'nothing_to_play_for':
        adjusted *= 0.92
        reasoning_parts.append("Nothing to play for: -8%")

    # Clamp to reasonable range
    adjusted = max(0.2, min(3.5, adjusted))

    reasoning_parts.append(f"Final adjusted xG: {adjusted:.2f}")

    return {
        'xg': round(adjusted, 2),
        'reasoning': reasoning_parts
    }


def suggest_rho(team_style, opponent_style, match_type='group'):
    """
    Suggest appropriate rho (Dixon-Coles parameter) based on match context.

    More negative rho for tighter/defensive games.
    Less negative rho for open/attacking games.

    Returns:
        dict with 'rho' value and 'reasoning'.
    """
    base_rho = -0.06  # Default

    if team_style == 'defensive' or opponent_style == 'defensive':
        rho = -0.07
        reason = "Defensive team involved → tighter game expected"
    elif team_style == 'offensive' and opponent_style == 'offensive':
        rho = -0.04
        reason = "Both teams offensive → more open game"
    else:
        rho = -0.06
        reason = "Standard/balanced matchup"

    if match_type == 'knockout':
        rho -= 0.01
        reason += " | Knockout caution: rho shifted -0.01"
    elif match_type == 'final':
        rho -= 0.02
        reason += " | Final: rho shifted -0.02"

    rho = max(-0.10, min(-0.02, rho))

    return {
        'rho': round(rho, 3),
        'reasoning': reason
    }


def validate_against_market(model_probs, market_odds=None):
    """
    Compare model probabilities against market odds (de-vigorized).

    Args:
        model_probs: dict with 'home', 'draw', 'away' from our model.
        market_odds: dict with 'home', 'draw', 'away' decimal odds.

    Returns:
        dict with comparison and deviation analysis.
    """
    if market_odds is None:
        return {
            'comparison': None,
            'note': 'No market odds provided for validation'
        }

    from engine.markets import devig_odds
    market_probs = devig_odds(
        market_odds['home'],
        market_odds['draw'],
        market_odds['away']
    )

    comparison = {
        'model': {
            'home': model_probs['home'],
            'draw': model_probs['draw'],
            'away': model_probs['away']
        },
        'market': {
            'home': market_probs['home'],
            'draw': market_probs['draw'],
            'away': market_probs['away'],
            'margin': market_probs['margin']
        },
        'deviation': {
            'home': round(
                abs(model_probs['home'] - market_probs['home']) * 100, 1
            ),
            'draw': round(
                abs(model_probs['draw'] - market_probs['draw']) * 100, 1
            ),
            'away': round(
                abs(model_probs['away'] - market_probs['away']) * 100, 1
            ),
        }
    }

    max_dev = max(comparison['deviation'].values())
    if max_dev > 7:
        comparison['alert'] = (
            f"⚠️ Max deviation {max_dev}pp — review calibration"
        )
    elif max_dev > 5:
        comparison['alert'] = (
            f"⚡ Moderate deviation {max_dev}pp — acceptable but check"
        )
    else:
        comparison['alert'] = (
            f"✅ Good alignment (max {max_dev}pp)"
        )

    return comparison
