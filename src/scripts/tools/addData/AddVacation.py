import json
import sys
sys.path.append("src/scripts/tools/")
import pathes

data = dict()

with open(pathes.VACATION_TXT, "r", encoding = "utf8") as file:
    for line in file:
        line = line.replace('\n', '')
        season, start_date, end_date = line.strip().split(" ")
        print(season, start_date, end_date)
        if start_date == "0" and end_date == "0":
            data[season] = None
        else:
            data[season] = {
                "startVacation" : start_date,
                "endVacation" :  end_date
            }
            
with open(pathes.VACATION_JSON, "w",  encoding = "utf8") as file:
    jsonData = json.dumps(data, indent = 4, ensure_ascii = False)
    file.write(jsonData)
