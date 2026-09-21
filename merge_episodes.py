import json
import os
import re

DATA_FILE = "animeData.js"
OLD_DATA_FILE = "episodes.js"

def read_old_data():
    """Purana episodes.js padho (const allAnimeData = {...})"""
    if not os.path.exists(OLD_DATA_FILE):
        print(f"❌ {OLD_DATA_FILE} nahi mili")
        return {}
    with open(OLD_DATA_FILE, "r", encoding="utf-8") as f:
        content = f.read()
    
    # const allAnimeData = {...} nikaalo
    match = re.search(r'const allAnimeData\s*=\s*(\{.*\});?\s*$', content, re.DOTALL)
    if not match:
        print("❌ allAnimeData format nahi mila")
        return {}
    
    try:
        # JavaScript object ko JSON me convert karo
        js_obj = match.group(1)
        # Single quotes ko double quotes me badlo
        js_obj = re.sub(r"'([^']*)'", r'"\1"', js_obj)
        # Trailing commas hataao
        js_obj = re.sub(r',\s*([}\]])', r'\1', js_obj)
        # Keys ko quote karo (agar nahi hai)
        js_obj = re.sub(r'(\w+):', r'"\1":', js_obj)
        
        data = json.loads(js_obj)
        return data
    except Exception as e:
        print(f"❌ Parse error: {e}")
        return {}

def read_current_data():
    """Nayi animeData.js padho"""
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        content = f.read()
    
    # const animeDatabase = [...] nikaalo
    start = content.find("const animeDatabase = [")
    if start == -1:
        return []
    start = content.find("[", start)
    depth = 0
    end = -1
    for i in range(start, len(content)):
        if content[i] == "[":
            depth += 1
        elif content[i] == "]":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    if end == -1:
        return []
    
    try:
        return json.loads(content[start:end])
    except Exception as e:
        print(f"⚠️ Read error: {e}")
        return []

def normalize_name(name):
    """Naam ko lowercase + trim karo"""
    return name.lower().strip()

def merge_episodes():
    print("🔄 Episodes merge kar rahe hain...\n")
    
    old_data = read_old_data()
    if not old_data:
        print("❌ Purana data nahi mila")
        return
    
    print(f"📊 Purane data me {len(old_data)} anime hain")
    
    current_data = read_current_data()
    if not current_data:
        print("❌ Current data nahi mila")
        return
    
    print(f"📊 Current data me {len(current_data)} anime hain\n")
    
    # Old data ko normalize karo (lowercase names)
    old_normalized = {normalize_name(k): v for k, v in old_data.items()}
    
    updated_count = 0
    matched_anime = []
    
    for anime in current_data:
        name = normalize_name(anime.get("name", ""))
        
        # Old data me dhoondo
        if name in old_normalized:
            old_anime = old_normalized[name]
            
            # Sirf seasons update karo
            if "seasons" in old_anime:
                anime["seasons"] = old_anime["seasons"]
                updated_count += 1
                matched_anime.append(anime.get("name"))
                print(f"✅ {anime.get('name')} — episodes update hue")
        
        # Agar exact match nahi mila, toh partial match try karo
        else:
            for old_name, old_anime in old_normalized.items():
                if old_name in name or name in old_name:
                    if "seasons" in old_anime:
                        anime["seasons"] = old_anime["seasons"]
                        updated_count += 1
                        matched_anime.append(anime.get("name"))
                        print(f"✅ {anime.get('name')} — partial match se update hua")
                    break
    
    print(f"\n📊 Total {updated_count} anime ke episodes update hue")
    
    # Save karo
    save_data(current_data)
    print("✅ animeData.js save ho gayi!")

def save_data(data):
    """animeData.js me save karo"""
    output = f"const animeDatabase = {json.dumps(data, indent=4, ensure_ascii=False)};\n"
    
    # heroSlides preserve karo
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            old = f.read()
        hs_start = old.find("const heroSlides =")
        if hs_start != -1:
            output += "\n" + old[hs_start:]
    
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        f.write(output)

if __name__ == "__main__":
    merge_episodes()
