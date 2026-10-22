import os
import re
import json
import base64
import requests
from datetime import datetime

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_REPO = "bhandaridharmveer529-lgtm/great-anime-zone"
GITHUB_FILE = "animeData.js"
LINKS_FILE = "links.txt"

def get_github_file():
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE}"
    r = requests.get(url, headers={"Authorization": f"token {GITHUB_TOKEN}", "Cache-Control": "no-cache"})
    if r.status_code != 200:
        return None, None
    d = r.json()
    return requests.get(d["download_url"]).text, d["sha"]

def update_github(content, sha, msg):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE}"
    enc = base64.b64encode(content.encode()).decode()
    r = requests.put(url, headers={"Authorization": f"token {GITHUB_TOKEN}"},
                     json={"message": msg, "content": enc, "sha": sha})
    return r.status_code

def main():
    print("links.txt padh rahe hain...")
    links = {}
    if os.path.exists(LINKS_FILE):
        with open(LINKS_FILE) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"): continue
                parts = [p.strip() for p in line.split("|")]
                if len(parts) != 4: continue
                anime_name, ep, stream, download = parts
                m = re.search(r'S(\d+)E(\d+)', ep, re.IGNORECASE)
                if not m: continue
                season = int(m.group(1))
                ep_num = int(m.group(2))
                if anime_name not in links: links[anime_name] = {}
                if season not in links[anime_name]: links[anime_name][season] = []
                links[anime_name][season].append({"ep": ep_num, "link": stream, "download": download})

    if not links:
        print("Koi link nahi mila")
        return

    content, sha = get_github_file()
    if not content: return

    start = content.find("const animeDatabase = [")
    if start == -1: return
    start = content.find("[", start)
    depth, end = 0, -1
    for i in range(start, len(content)):
        if content[i] == "[": depth += 1
        elif content[i] == "]":
            depth -= 1
            if depth == 0:
                end = i + 1
                break

    try:
        anime_db = json.loads(content[start:end])
    except Exception as e:
        print(f"Parse error: {e}")
        return

    added = 0
    for anime_name, seasons in links.items():
        # 🎯 SMART MATCH: Naam English ho ya Japanese, match ho jayega
        found_anime = None
        name_lower = anime_name.lower().strip()
        
        for a in anime_db:
            db_name = a.get("name", "").lower().strip()
            romaji = a.get("romaji_name", "").lower().strip()
            
            if name_lower == db_name or name_lower == romaji:
                found_anime = a
                break
                
        if not found_anime:
            # Thoda flexible match (Part 2, Cour 2, III vs 3)
            clean_name = name_lower.replace("season ", "").replace(" iii", " 3").replace(" ii", " 2").replace("part ", "").replace("cour ", "").strip()
            for a in anime_db:
                db_clean = a.get("name", "").lower().replace("season ", "").replace(" iii", " 3").replace(" ii", " 2").replace("part ", "").replace("cour ", "").strip()
                romaji_clean = a.get("romaji_name", "").lower().replace("season ", "").replace(" iii", " 3").replace(" ii", " 2").replace("part ", "").replace("cour ", "").strip()
                
                if clean_name == db_clean or clean_name == romaji_clean:
                    found_anime = a
                    break
                    
        if not found_anime:
            print(f"❌ Skip: Match nahi mila '{anime_name}'")
            continue

        print(f"✅ Matched: '{anime_name}' -> '{found_anime.get('name')}'")
        
        if "seasons" not in found_anime: found_anime["seasons"] = {}

        anime_updated = False
        for season_num, eps in seasons.items():
            sk = f"s{season_num}"
            if sk not in found_anime["seasons"]:
                found_anime["seasons"][sk] = {"seasonName": f"Season {season_num}", "seasonZip": "", "episodes": []}
            
            existing_eps = found_anime["seasons"][sk]["episodes"]
            for new_ep in eps:
                existing = next((e for e in existing_eps if e["ep"] == new_ep["ep"]), None)
                if existing:
                    existing["link"] = new_ep["link"]
                    existing["download"] = new_ep["download"]
                else:
                    existing_eps.append({"ep": new_ep["ep"], "title": f"Episode {new_ep['ep']}", "link": new_ep["link"], "download": new_ep["download"]})
                added += 1
                anime_updated = True
            existing_eps.sort(key=lambda x: x["ep"])
        
        if anime_updated:
            found_anime["addedDate"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 🎯 SMART BADGE RECALCULATE (Khud hi sahi badge laga dega)
    for anime in anime_db:
        max_ep = 0
        latest_season = 1
        if "seasons" in anime:
            for season_key, season_data in anime["seasons"].items():
                season_num = int(season_key[1:]) if season_key.startswith("s") and season_key[1:].isdigit() else 1
                for ep in season_data.get("episodes", []):
                    if ep.get("link") and ep.get("link") != "":
                        if ep.get("ep", 0) >= max_ep:
                            max_ep = ep.get("ep", 0)
                            latest_season = season_num

        if max_ep == 0:
            anime["latestUpdate"] = "New Ep Added"
            anime["isSeasonCompleted"] = False
            anime["isNewEp"] = False
        else:
            eps_val = str(anime.get("eps", 0) or 0)
            total_eps = int(eps_val) if eps_val.isdigit() else 0
            if total_eps > 0 and max_ep >= total_eps:
                anime["latestUpdate"] = "Completed"
                anime["isSeasonCompleted"] = True
                anime["isNewEp"] = False
            else:
                anime["latestUpdate"] = f"S{latest_season} EP {max_ep} Added" if latest_season > 1 else f"EP {max_ep} Added"
                anime["isSeasonCompleted"] = False
                anime["isNewEp"] = True

    new_db = json.dumps(anime_db, indent=4, ensure_ascii=False)
    new_content = content[:start] + new_db + content[end:]
    s = update_github(new_content, sha, f"Links update + Auto badges ({added} added)")
    print(f"\nGitHub: {'Updated!' if s in [200,201] else 'Failed: ' + str(s)}")

if __name__ == "__main__":
    main()
