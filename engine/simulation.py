"""
Dixon-Coles Bivariate Poisson Simulator for Football Match Prediction.

Uses a bivariate Poisson distribution with the Dixon-Coles correction factor
to model the joint probability of scorelines, then samples via Monte Carlo.

Reference: Dixon & Coles (1997) - "Modelling Association Football Scores
and Inefficiencies in the Football Betting Market"
"""

import numpy as np
from scipy.stats import poisson


class DixonColesSimulator:
    """
    Simulates football match outcomes using bivariate Poisson with
    Dixon-Coles low-score correction and Monte Carlo sampling.
    """

    def __init__(self, lam_home, lam_away, rho=-0.06, n_sims=300000,
                 max_goals=8, seed=None):
        """
        Args:
            lam_home: Expected goals (xG) for the home/first team.
            lam_away: Expected goals (xG) for the away/second team.
            rho: Dixon-Coles correction parameter. Typically between
                 -0.03 (open game) and -0.08 (tight/defensive game).
            n_sims: Number of Monte Carlo simulations to run.
            max_goals: Maximum goals per team to model (0 to max_goals).
            seed: Random seed for reproducibility (optional).
        """
        if lam_home <= 0 or lam_away <= 0:
            raise ValueError("Lambda values must be positive")
        if not (-0.15 <= rho <= 0.15):
            raise ValueError("Rho should be between -0.15 and 0.15")

        self.lam_home = float(lam_home)
        self.lam_away = float(lam_away)
        self.rho = float(rho)
        self.n_sims = int(n_sims)
        self.max_goals = int(max_goals)
        self.seed = seed
        self.prob_matrix = None
        self.home_goals = None
        self.away_goals = None

    def _dc_correction(self, i, j):
        """
        Dixon-Coles correction factor tau(i, j).

        Adjusts the joint probability of low-scoring outcomes (0-0, 0-1,
        1-0, 1-1) where independent Poisson underperforms.

        With rho < 0:
          - P(0-0) and P(1-1) are inflated (draws more likely)
          - P(0-1) and P(1-0) are deflated
        """
        lam = self.lam_home
        mu = self.lam_away
        rho = self.rho

        if i == 0 and j == 0:
            return 1 - lam * mu * rho
        elif i == 0 and j == 1:
            return 1 + lam * rho
        elif i == 1 and j == 0:
            return 1 + mu * rho
        elif i == 1 and j == 1:
            return 1 - rho
        else:
            return 1.0

    def _build_probability_matrix(self):
        """
        Build the full (max_goals+1) x (max_goals+1) probability matrix.

        P[i][j] = P(Home scores i, Away scores j)
                 = Poisson(i; lam_home) * Poisson(j; lam_away) * tau(i,j)

        The matrix is normalized to sum to 1.0.
        """
        mg = self.max_goals + 1
        P = np.zeros((mg, mg))

        for i in range(mg):
            for j in range(mg):
                p_h = poisson.pmf(i, self.lam_home)
                p_a = poisson.pmf(j, self.lam_away)
                tau = self._dc_correction(i, j)
                P[i, j] = p_h * p_a * tau

        # Normalize to ensure valid probability distribution
        P /= P.sum()
        self.prob_matrix = P
        return P

    def simulate(self):
        """
        Run Monte Carlo simulation by sampling from the probability matrix.

        Returns:
            tuple: (home_goals_array, away_goals_array) of length n_sims.
        """
        if self.prob_matrix is None:
            self._build_probability_matrix()

        rng = np.random.default_rng(self.seed)
        mg = self.max_goals + 1
        flat = self.prob_matrix.flatten()
        idx = rng.choice(len(flat), size=self.n_sims, p=flat)

        self.home_goals = idx // mg
        self.away_goals = idx % mg

        return self.home_goals, self.away_goals

    def get_results(self):
        """
        Compute comprehensive results from the simulation.

        Returns:
            dict with params, probability matrix, summary stats,
            1X2 probabilities, exact scores, over/under, BTTS,
            clean sheets, and confidence index.
        """
        if self.home_goals is None:
            self.simulate()

        hg = self.home_goals
        ag = self.away_goals
        total = hg + ag
        n = self.n_sims

        # --- 1X2 ---
        home_wins = float(np.sum(hg > ag) / n)
        draws = float(np.sum(hg == ag) / n)
        away_wins = float(np.sum(hg < ag) / n)

        # --- Exact scores (top 15) ---
        from collections import Counter
        scores = Counter(zip(hg.tolist(), ag.tolist()))
        exact_scores = []
        for (h, a), count in scores.most_common(15):
            exact_scores.append({
                'home': int(h),
                'away': int(a),
                'score': f"{h}-{a}",
                'prob': round(count / n, 4),
                'pct': round(count / n * 100, 2)
            })

        # --- Over/Under ---
        over_under = {}
        for threshold in [0.5, 1.5, 2.5, 3.5, 4.5]:
            over = float(np.sum(total > threshold) / n)
            over_under[str(threshold)] = {
                'over': round(over, 4),
                'under': round(1 - over, 4)
            }

        # --- BTTS (Both Teams To Score) ---
        btts_yes = float(np.sum((hg > 0) & (ag > 0)) / n)
        btts = {
            'yes': round(btts_yes, 4),
            'no': round(1 - btts_yes, 4)
        }

        # --- Clean Sheet ---
        cs_home = float(np.sum(ag == 0) / n)
        cs_away = float(np.sum(hg == 0) / n)
        clean_sheet = {
            'home': round(cs_home, 4),
            'away': round(cs_away, 4)
        }

        # --- Goal distribution per team ---
        home_goal_dist = {}
        away_goal_dist = {}
        for g in range(self.max_goals + 1):
            home_goal_dist[str(g)] = round(float(np.sum(hg == g) / n), 4)
            away_goal_dist[str(g)] = round(float(np.sum(ag == g) / n), 4)

        # --- Asian Handicap ---
        asian_handicap = {}
        for line in [-2.5, -1.5, -0.5, 0.5, 1.5, 2.5]:
            diff = hg.astype(float) - ag.astype(float)
            covers = float(np.sum(diff > line) / n)
            asian_handicap[str(line)] = {
                'home_covers': round(covers, 4),
                'away_covers': round(1 - covers, 4)
            }

        # --- Confidence Index ---
        max_1x2 = max(home_wins, draws, away_wins)
        if max_1x2 >= 0.65:
            confidence = 'ALTA'
        elif max_1x2 >= 0.45:
            confidence = 'MEDIA'
        else:
            confidence = 'BAJA'

        # --- Prode Recommendation ---
        if home_wins > draws and home_wins > away_wins:
            rec_result = 'home'
        elif away_wins > draws and away_wins > home_wins:
            rec_result = 'away'
        else:
            rec_result = 'draw'

        # Pick the most probable score that matches the recommended 1X2 outcome
        rec_score = '1-0'
        if exact_scores:
            for s in exact_scores:
                h, a = s['home'], s['away']
                if rec_result == 'home' and h > a:
                    rec_score = s['score']
                    break
                elif rec_result == 'away' and a > h:
                    rec_score = s['score']
                    break
                elif rec_result == 'draw' and h == a:
                    rec_score = s['score']
                    break

        return {
            'params': {
                'lam_home': self.lam_home,
                'lam_away': self.lam_away,
                'rho': self.rho,
                'n_sims': self.n_sims,
                'max_goals': self.max_goals
            },
            'prob_matrix': self.prob_matrix.tolist(),
            'summary': {
                'home_goals_mean': round(float(np.mean(hg)), 3),
                'away_goals_mean': round(float(np.mean(ag)), 3),
                'home_goals_std': round(float(np.std(hg)), 3),
                'away_goals_std': round(float(np.std(ag)), 3),
                'total_goals_mean': round(float(np.mean(total)), 3),
            },
            'one_x_two': {
                'home': round(home_wins, 4),
                'draw': round(draws, 4),
                'away': round(away_wins, 4)
            },
            'exact_scores': exact_scores,
            'over_under': over_under,
            'btts': btts,
            'clean_sheet': clean_sheet,
            'home_goal_dist': home_goal_dist,
            'away_goal_dist': away_goal_dist,
            'asian_handicap': asian_handicap,
            'confidence': confidence,
            'recommendation': {
                'result': rec_result,
                'score': rec_score
            }
        }
