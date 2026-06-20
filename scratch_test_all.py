import json
import os
import sys

# Add current dir to path to import engine
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from engine.simulation import DixonColesSimulator
from engine.calibration import suggest_xg, suggest_rho

def run():
    with open('data/teams.json', 'r', encoding='utf-8') as f:
        teams_data = json.load(f)
    teams_dict = {t['code']: t for t in teams_data['teams']}

    with open('data/matches.json', 'r', encoding='utf-8') as f:
        matches_data = json.load(f)
    
    print("=== SIMULANDO TODOS LOS PARTIDOS PROGRAMADOS ===")
    
    scheduled_matches = [m for m in matches_data['matches'] if m['status'] == 'scheduled']
    
    for m in scheduled_matches:
        home_code = m['home']
        away_code = m['away']
        h_team = teams_dict[home_code]
        a_team = teams_dict[away_code]
        
        # Calibration
        h_xg_data = suggest_xg(h_team, a_team, {'stage': 'group'})
        a_xg_data = suggest_xg(a_team, h_team, {'stage': 'group'})
        rho_data = suggest_rho(h_team['style'], a_team['style'], 'group')
        
        lam_home = h_xg_data['xg']
        lam_away = a_xg_data['xg']
        rho = rho_data['rho']
        
        sim = DixonColesSimulator(lam_home=lam_home, lam_away=lam_away, rho=rho, n_sims=300000, seed=42)
        r = sim.get_results()
        
        rec = r['recommendation']
        top_scores = [f"{s['score']} ({s['pct']}%)" for s in r['exact_scores'][:5]]
        
        print(f"\n⚽ {h_team['name']} ({lam_home:.2f}) vs {a_team['name']} ({lam_away:.2f}) [rho: {rho}]")
        print(f"  1X2 Probs: Local={r['one_x_two']['home']*100:.1f}%, Empate={r['one_x_two']['draw']*100:.1f}%, Visitante={r['one_x_two']['away']*100:.1f}%")
        print(f"  Top 5 scores: {', '.join(top_scores)}")
        print(f"  Sugerido Prode: Winner={rec['result'].upper()}, Score={rec['score']}")

if __name__ == '__main__':
    run()
