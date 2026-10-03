import os
import re
import json
import base64
import requests
from difflib import SequenceMatcher

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_REPO = "bhandaridharmveer529-lgtm/great-anime-zone"
GITHUB_FILE = "animeData.js"
LINKS_FILE = "links.txt"

def similarity(a, b):
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()

def find_best_match(name, anime_db):
    best, best_score = None, 0
    for anime in anime_db:
        db_name = anime.get("name", "")
        score = similarity(name, db_name)
        if name.lower() in db_name.lower() or db_name.lower() in name.lower():
            score = max(score, 0.8)
        if score > best_score:
            best_score = score
            best = anime
    return best if best_score >= 0.55 else None

def recalc_badge(anime):
    """Anime ka badge recalculate karo"""
    total_eps = int(anime.get("eps", 0) or 0)
    current_count = 0
    max_ep = 0
    if "seasons" in anime:
        for season in anime["seasons"].values():
            for ep in season.get("episodes", []):
                if ep.get("link") and ep.get("link") != "":
                    current_count += 1
                    if ep.get("ep", 0) > max_ep:
                        max_ep = ep.get("ep", 0)
    
    if current_count == 0:
        anime["latestUpdate"] = "New Ep Added"
        anime["isSeasonCompleted"] = False
        anime["isNewEp"] = False
    elif total_eps > 0 and current_count >= total_eps:
        anime["latestUpdate"] = "Completed"
        anime["isSeasonCompleted"] = True
        anime["isNewEp"] = False
    else:
        anime["latestUpdate"] = f"EP {max_ep} Added"
        anime["isSeasonCompleted"] = False
        anime["isNewEp"] = True

def get_github_file():
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE}"
    r = requests.get(url, headers={"Authorization": f"token {GITHUB_TOKEN}"})
    if r.status_code != 200:
        print(f"GitHub error: {r.status_code}")
        return None, None
    d = r.json()
    return requests.get(d["download_url"]).text, d["sha"]

def update_github(content, sha, msg):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE}"
    enc = base64.b64encode(content.encode()).decode()
    r = requests.put(url, headers={"Authorization": f"token {GITHUB_TOKEN}"},
                     json={"message": msg, "content": enc, "sha": sha})
    return r.status_code

def parse_links():
    links = {}
    if not os.path.exists(LINKS_FILE):
        print(f"{LINKS_FILE} nahi mili")
        return links
    with open(LINKS_FILE) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = [p.strip() for p in line.split("|")]
            if len(parts) != 4:
                print(f"Skip (format galat): {line[:50]}")
                continue
            anime_name, ep, stream, download = parts
            m = re.search(r'S(\d+)E(\d+)', ep, re.IGNORECASE)
            if not m:
                print(f"Skip (episode galat): {ep}")
                continue
            season = int(m.group(1))
            ep_num = int(m.group(2))
            if anime_name not in links:
                links[anime_name] = {}
            if season not in links[anime_name]:
                links[anime_name][season] = []
            links[anime_name][season].append({
                "ep": ep_num, "link": stream, "download": download
            })
    return links

def main():
    print("links.txt padh rahe hain...")
    links = parse_links()
    if not links:
        print("Koi link nahi mila")
        return
    print(f"{len(links)} anime ke links mile")
    
    content, sha = get_github_file()
    if not content:
        return
    
    start = content.find("const animeDatabase = [")
    if start == -1:
        print("animeDatabase nahi mila")
        return
    start = content.find("[", start)
    depth, end = 0, -1
    for i in range(start, len(content)):
        if content[i] == "[":
            depth += 1
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
        found_anime = find_best_match(anime_name, anime_db)
        if not found_anime:
            print(f"Anime nahi mila: {anime_name}")
            continue
        print(f"Matched: '{anime_name}' -> '{found_anime.get('name')}'")
        
        if "seasons" not in found_anime:
            found_anime["seasons"] = {}
        
        for season_num, eps in seasons.items():
            sk = f"s{season_num}"
            if sk not in found_anime["seasons"]:
                found_anime["seasons"][sk] = {
                    "seasonName": f"Season {season_num}",
                    "seasonZip": "",
                    "episodes": []
                }
            
            existing_eps = found_anime["seasons"][sk]["episodes"]
            for new_ep in eps:
                existing = next((e for e in existing_eps if e["ep"] == new_ep["ep"]), None)
                if existing:
                    existing["link"] = new_ep["link"]
                    existing["download"] = new_ep["download"]
                    print(f"Update: {anime_name} S{season_num}E{new_ep['ep']}")
                else:
                    existing_eps.append({
                        "ep": new_ep["ep"],
                        "title": f"Episode {new_ep['ep']}",
                        "link": new_ep["link"],
                        "download": new_ep["download"]
                    })
                    print(f"Add: {anime_name} S{season_num}E{new_ep['ep']}")
                added += 1
            
            existing_eps.sort(key=lambda x: x["ep"])
    
    # ===== SAARE ANIME KE BADGES RECALCULATE KARO =====
    print("\n=== Saare anime ke badges recalculate ===")
    for anime in anime_db:
        recalc_badge(anime)
        print(f"  {anime.get('name')}: {anime.get('latestUpdate')}")
    # ===== END RECALC =====
    
    new_db = json.dumps(anime_db, indent=4, ensure_ascii=False)
    new_content = content[:start] + new_db + content[end:]
    s = update_github(new_content, sha, f"Links update: {added} eps + badge recalc")
    print(f"\nGitHub: {'Updated!' if s in [200,201] else 'Failed: ' + str(s)}")

if __name__ == "__main__":
    main()
