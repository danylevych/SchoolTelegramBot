import json
import sys
sys.path.append("src/scripts/tools/")
import pathes

data : dict = dict()
key  : str  = str()
day  : str  = str()

with open(pathes.TIMETABLE_TXT, "r", encoding = "utf8") as file:
    for line in file:  
        line = line.replace('\n', '')  
        if "class" in line[:-1]:
            key = line
            data[key] = dict()
        
        elif line in ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"):
            day = line
            data[key][day] = dict()
            
        else:
            parsedLine : list = list()
            firtsSpace = line.find(' ')
            parsedLine.append(line[ : firtsSpace])
            parsedLine.append(None if line[firtsSpace + 1 : ] == "" else line[firtsSpace + 1 : ])
            print(parsedLine)

            data[key][day][parsedLine[0]] = parsedLine[1]

with open(pathes.TIMETABLE_JSON, "w",  encoding = "utf8") as file:
    jsonData = json.dumps(data, indent = 4, ensure_ascii = False)
    file.write(jsonData)