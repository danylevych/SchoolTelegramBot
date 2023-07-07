import json
import sys
sys.path.append("src/scripts/tools/")
import pathes

data : dict = dict()
key  : str  = str()

with open(pathes.TIMETABLE_LESSONS_TXT, "r", encoding = "utf8") as file:
    for line in file:  
        line = line.replace('\n', '')  
        if "class" in line[:-1]:
            key = line
            data[line] = dict()
        else:
            splitedStr : str = line.split(' ')
            data[key][splitedStr[0]] = {
                "startTime" : {
                    "hour" : int(splitedStr[1]),
                    "minute" : int(splitedStr[2]),
                },
                "endTime" : {
                    "hour" : int(splitedStr[3]),
                    "minute" : int(splitedStr[4]),
                }
            }

with open(pathes.TIMETABLE_LESSONS_JSON, "w",  encoding = "utf8") as file:
    jsonData = json.dumps(data, indent = 4, ensure_ascii = False)
    file.write(jsonData)