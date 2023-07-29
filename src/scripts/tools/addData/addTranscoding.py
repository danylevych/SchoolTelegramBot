import json
import sys
import requests
sys.path.append("src/scripts/tools/")
import pathes

respond = requests.get("https://ubilling.net.ua/aerialalerts/").json()

with open(pathes.AIRDANGEROUS_JSON, "w", encoding="utf8") as file:
    jsonData = json.dumps(respond, indent=4, ensure_ascii=False)
    file.write(jsonData)
