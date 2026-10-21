import os
import re
import json
import base64
import requests

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_REPO = "bhandaridharmveer529-lgtm/great-anime-zone"
GITHUB_FILE = "animeData.js"

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

def main():
    print("Resetting badges...")
    content, sha = get_github_file()
    if not content:
        return

    start = content.find("const animeDatabase = [")
    if start == -1:
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

    anime_db = json.loads(content[start:end])

    for anime in anime_db:
        eps_val = str(anime.get("eps", 0) or 0)
        total_eps = int(eps_val) if eps_val.isdigit() else 0

        current_count = 0
        max_ep = 0
        latest_season = 1

        if "seasons" in anime:
            for season_key, season_data in anime["seasons"].items():
                season_num = 1
                if season_key.startswith("s") and season_key[1:].isdigit():
                    season_num = int(season_key[1:])

                for ep in season_data.get("episodes", []):
                    if ep.get("link") and ep.get("link") != "":
                        current_count += 1
                        if ep.get("ep", 0) >= max_ep:
                            max_ep = ep.get("ep", 0)
                            latest_season = season_num

        if current_count == 0:
            anime["latestUpdate"] = "New Ep Added"
            anime["isSeasonCompleted"] = False
        elif total_eps > 0 and current_count >= total_eps:
            anime["latestUpdate"] = "Completed"
            anime["isSeasonCompleted"] = True
        else:
            anime["latestUpdate"] = f"S{latest_season} EP {max_ep} Added" if latest_season > 1 else f"EP {max_ep} Added"
            anime["isSeasonCompleted"] = False

    new_db = json.dumps(anime_db, indent=4, ensure_ascii=False)
    new_content = content[:start] + new_db + content[end:]
    s = update_github(new_content, sha, "Auto badge update")
    print(f"GitHub: {'Updated!' if s in [200,201] else 'Failed: ' + str(s)}")

if __name__ == "__main__":
    main()
