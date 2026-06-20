"""
Market calculation utilities.

Derives betting/prode markets from a Dixon-Coles probability matrix.
These functions work on the raw probability matrix P[i][j] where
i = home goals, j = away goals.
"""

import numpy as np


def calc_1x2(matrix):
    """Calculate 1X2 (home/draw/away) probabilities from score matrix."""
    P = np.array(matrix)
    mg = P.shape[0]

    home = 0.0
    draw = 0.0
    away = 0.0

    for i in range(mg):
        for j in range(mg):
            if i > j:
                home += P[i, j]
            elif i == j:
                draw += P[i, j]
            else:
                away += P[i, j]

    return {
        'home': round(float(home), 4),
        'draw': round(float(draw), 4),
        'away': round(float(away), 4)
    }


def calc_over_under(matrix, thresholds=None):
    """Calculate Over/Under probabilities for various goal thresholds."""
    if thresholds is None:
        thresholds = [0.5, 1.5, 2.5, 3.5, 4.5]

    P = np.array(matrix)
    mg = P.shape[0]
    results = {}

    for t in thresholds:
        over = 0.0
        for i in range(mg):
            for j in range(mg):
                if i + j > t:
                    over += P[i, j]
        results[str(t)] = {
            'over': round(float(over), 4),
            'under': round(float(1 - over), 4)
        }

    return results


def calc_btts(matrix):
    """Calculate Both Teams To Score (BTTS) probability."""
    P = np.array(matrix)
    mg = P.shape[0]

    yes = 0.0
    for i in range(1, mg):
        for j in range(1, mg):
            yes += P[i, j]

    return {
        'yes': round(float(yes), 4),
        'no': round(float(1 - yes), 4)
    }


def calc_clean_sheet(matrix):
    """Calculate clean sheet probability for each team."""
    P = np.array(matrix)

    # Home clean sheet: away scores 0
    home_cs = float(P[:, 0].sum())
    # Away clean sheet: home scores 0
    away_cs = float(P[0, :].sum())

    return {
        'home': round(home_cs, 4),
        'away': round(away_cs, 4)
    }


def calc_exact_scores(matrix, top_n=15):
    """Get the top N most probable exact scorelines."""
    P = np.array(matrix)
    mg = P.shape[0]

    scores = []
    for i in range(mg):
        for j in range(mg):
            scores.append({
                'home': i,
                'away': j,
                'score': f"{i}-{j}",
                'prob': round(float(P[i, j]), 4),
                'pct': round(float(P[i, j]) * 100, 2)
            })

    scores.sort(key=lambda x: x['prob'], reverse=True)
    return scores[:top_n]


def calc_asian_handicap(matrix, lines=None):
    """Calculate Asian Handicap probabilities."""
    if lines is None:
        lines = [-2.5, -1.5, -0.5, 0.5, 1.5, 2.5]

    P = np.array(matrix)
    mg = P.shape[0]
    results = {}

    for line in lines:
        covers = 0.0
        for i in range(mg):
            for j in range(mg):
                diff = i - j
                if diff + line > 0:
                    covers += P[i, j]
        results[str(line)] = {
            'home_covers': round(float(covers), 4),
            'away_covers': round(float(1 - covers), 4)
        }

    return results


def calc_goal_distribution(matrix):
    """Calculate goal distribution for each team."""
    P = np.array(matrix)

    home_dist = {}
    away_dist = {}

    for g in range(P.shape[0]):
        home_dist[str(g)] = round(float(P[g, :].sum()), 4)
        away_dist[str(g)] = round(float(P[:, g].sum()), 4)

    return {'home': home_dist, 'away': away_dist}


def implied_odds(prob):
    """Convert probability to decimal odds."""
    if prob <= 0:
        return float('inf')
    return round(1 / prob, 2)


def devig_odds(odds_home, odds_draw, odds_away):
    """
    De-vigorize (remove bookmaker margin from) decimal odds to get
    'true' implied probabilities.
    """
    p_h = 1 / odds_home
    p_d = 1 / odds_draw
    p_a = 1 / odds_away
    total = p_h + p_d + p_a  # > 1.0 due to vig

    return {
        'home': round(p_h / total, 4),
        'draw': round(p_d / total, 4),
        'away': round(p_a / total, 4),
        'margin': round((total - 1) * 100, 2)  # % margin
    }
