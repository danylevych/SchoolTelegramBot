import json
import sys
sys.path.append("src/scripts/tools/")
import pathes

# from datetime import datetime

# date_string = "01.01.2023"
# date_format = "%d.%m.%Y"

# try:
#     date_object = datetime.strptime(date_string, date_format)
#     print("Об'єкт datetime:", date_object)
# except ValueError as ve:
#     print("Помилка при перетворенні:", ve)


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
