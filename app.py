import os, math, json
from datetime import date, timedelta, datetime, timezone
from pathlib import Path
import requests
from flask import Flask, render_template, jsonify

app = Flask(__name__)
API_TOKEN = os.getenv("FOOTBALL_DATA_TOKEN", "").strip()
API_BASE = "https://api.football-data.org/v4"
CACHE_FILE = Path(os.getenv("CACHE_FILE", "weekly_cache.json"))
LEAGUES = {
    "PL": "Premier League",
    "PD": "La Liga",
    "SA": "Serie A",
    "BL1": "Bundesliga",
    "FL1": "Ligue 1",
    # Süper Lig ücretsiz kapsamda garanti edilmediğinden varsayılan listeye dahil değil.
}
HEADERS = {"X-Auth-Token": API_TOKEN} if API_TOKEN else {}

def api_get(path, params=None):
    if not API_TOKEN:
        raise RuntimeError("FOOTBALL_DATA_TOKEN ayarlanmamış. .env.example dosyasına bakın.")
    response = requests.get(API_BASE + path, headers=HEADERS, params=params, timeout=25)
    if response.status_code == 429:
        raise RuntimeError("API istek sınırına ulaşıldı. Bir süre sonra tekrar deneyin.")
    response.raise_for_status()
    return response.json()

def poisson(k, lam):
    p = math.exp(-lam)
    for i in range(1, k + 1):
        p *= lam / i
    return p

def team_stats(team_id, team_name, matches):
    rows = []
    for m in matches:
        if m.get("status") != "FINISHED":
            continue
        home, away = m.get("homeTeam", {}), m.get("awayTeam", {})
        score = m.get("score", {}).get("fullTime", {})
        hg, ag = score.get("home"), score.get("away")
        if hg is None or ag is None:
            continue
        if home.get("id") == team_id:
            gf, ga = hg, ag
        elif away.get("id") == team_id:
            gf, ga = ag, hg
        else:
            continue
        rows.append({
            "date": (m.get("utcDate") or "")[:10],
            "opponent": away.get("name") if home.get("id") == team_id else home.get("name"),
            "home": home.get("id") == team_id,
            "gf": gf, "ga": ga,
            "result": "G" if gf > ga else ("B" if gf == ga else "M"),
        })
    rows.sort(key=lambda x: x["date"], reverse=True)
    return rows[:10]

def summarize(rows):
    if not rows:
        return {"count": 0, "gf": 0, "ga": 0, "avg_gf": 0, "avg_ga": 0,
                "wins": 0, "draws": 0, "losses": 0, "over25": 0, "btts": 0, "over15": 0, "over35": 0, "clean_sheets": 0, "last5_count": 0, "last5_wins": 0, "last5_draws": 0, "last5_losses": 0}
    n = len(rows)
    last5 = rows[-5:]
    gf, ga = sum(x["gf"] for x in rows), sum(x["ga"] for x in rows)
    return {
        "count": n, "gf": gf, "ga": ga,
        "avg_gf": round(gf / n, 2), "avg_ga": round(ga / n, 2),
        "wins": sum(x["result"] == "G" for x in rows),
        "draws": sum(x["result"] == "B" for x in rows),
        "losses": sum(x["result"] == "M" for x in rows),
        "last5_count": len(last5),
"last5_wins": sum(x["result"] == "G" for x in last5),
"last5_draws": sum(x["result"] == "B" for x in last5),
"last5_losses": sum(x["result"] == "M" for x in last5),
        "over25": round(sum(x["gf"] + x["ga"] >= 3 for x in rows) / n * 100),
        "btts": round(sum(x["gf"] > 0 and x["ga"] > 0 for x in rows) / n * 100),
        "over15": round(sum(x["gf"] + x["ga"] >= 2 for x in rows) / n * 100),
        "over35": round(sum(x["gf"] + x["ga"] >= 4 for x in rows) / n * 100),
        "clean_sheets": round(sum(x["ga"] == 0 for x in rows) / n * 100),
    }

def predict(home_stats, away_stats):
    if not home_stats["count"] or not away_stats["count"]:
        return {"error": "Bu maç için yeterli son maç verisi bulunamadı."}
    # Basit, açıklanabilir model. Ev/deplasman ayrımı daha sonra geliştirilebilir.
    lh = max(0.15, (home_stats["avg_gf"] + away_stats["avg_ga"]) / 2)
    la = max(0.15, (away_stats["avg_gf"] + home_stats["avg_ga"]) / 2)
    p1 = px = p2 = under = btts = over15 = over35 = 0.0
    scores = []
    for i in range(8):
        for j in range(8):
            p = poisson(i, lh) * poisson(j, la)
            if i > j: p1 += p
            elif i == j: px += p
            else: p2 += p
            if i + j <= 2: under += p
            if i + j >= 2: over15 += p
            if i + j >= 4: over35 += p
   
            if i > 0 and j > 0: btts += p
            scores.append({"score": f"{i}-{j}", "probability": round(p * 100, 1)})
    total = p1 + px + p2
    scores.sort(key=lambda x: x["probability"], reverse=True)
    return {
        "home_win": round(p1 / total * 100), "draw": round(px / total * 100),
        "away_win": round(p2 / total * 100), "under25": round(under * 100),
        "over15": round(over15 * 100), "over25": round((1 - under) * 100), "over35": round(over35 * 100), "btts_yes": round(btts * 100),
        "expected_goals": round(lh + la, 2), "top_scores": scores[:3],
        "model": "Basit Poisson gol modeli; kesin sonuç garantisi değildir."
    }

def build_weekly_bulletin():
    today = date.today()
    end = today + timedelta(days=7)
    all_matches, errors = [], []
    for code, league_name in LEAGUES.items():
        try:
            data = api_get(f"/competitions/{code}/matches", {
                "dateFrom": today.isoformat(), "dateTo": end.isoformat()
            })
            for m in data.get("matches", []):
                m["leagueName"] = league_name
                all_matches.append(m)
        except Exception as e:
            errors.append(f"{league_name}: {str(e)}")
    # Her ligin güncel sezon maçlarını alıp takım başına son 10 maçı türet.
    historical_by_league = {}
    for code, league_name in LEAGUES.items():
        try:
            data = api_get(f"/competitions/{code}/matches")
            historical_by_league[code] = data.get("matches", [])
        except Exception as e:
            historical_by_league[code] = []
            errors.append(f"{league_name} geçmiş verisi: {str(e)}")
    output = []
    for m in sorted(all_matches, key=lambda x: x.get("utcDate", "")):
        code = m.get("competition", {}).get("code")
        history = historical_by_league.get(code, [])
        home, away = m.get("homeTeam", {}), m.get("awayTeam", {})
        hs = summarize(team_stats(home.get("id"), home.get("name", "Ev sahibi"), history))
        aws = summarize(team_stats(away.get("id"), away.get("name", "Deplasman"), history))
        pred = predict(hs, aws)
        output.append({
            "id": m.get("id"), "league": m.get("leagueName", code),
            "date": m.get("utcDate"), "status": m.get("status"),
            "home": home.get("name"), "away": away.get("name"),
            "home_stats": hs, "away_stats": aws, "prediction": pred,
        })
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "range_start": today.isoformat(), "range_end": end.isoformat(),
        "matches": output, "errors": errors,
        "data_source": "Football-Data.org API",
        "note": "Veri sağlayıcısının ücretsiz kapsamı ve gecikme koşulları geçerlidir. Tahminler garanti değildir."
    }
    CACHE_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload

def load_bulletin():
    if CACHE_FILE.exists():
        try:
            return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    try:
        return build_weekly_bulletin()
    except Exception as e:
        return {"generated_at": None, "matches": [], "errors": [str(e)],
                "note": "API anahtarı eklenip güncelleme görevi çalıştırılınca bülten burada görünür."}

@app.get("/")
def index():
    return render_template("index.html", bulletin=load_bulletin(), leagues=LEAGUES)

@app.get("/api/bulletin")
def bulletin_json():
    return jsonify(load_bulletin())

@app.post("/api/refresh")
def refresh():
    # Demo/kişisel kurulum içindir. Herkese açık dağıtımda bu endpoint'e kimlik doğrulama ekleyin.
    try:
        return jsonify(build_weekly_bulletin())
    except Exception as e:
        return jsonify({"error": str(e)}), 502

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", "5000")), debug=False)
