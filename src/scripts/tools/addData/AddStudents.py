import json
import sys
sys.path.append("src/scripts/tools/")
import pathes

data : dict = dict()
key  : int  = int()
with open(pathes.STUDENTS_TXT, "r", encoding = "utf8") as file:
    for line in file:  
        line = line.replace('\n', '')  
        if line.isdigit():
            key = int(line)
            data[key] = list()
        elif line == "":
            data[key] = None
        else:
            parsedLine = line.split(' ')
            print(parsedLine)
            student = {
                "lastName"  : parsedLine[0],
                "firstName" : parsedLine[1],
                "fatherName": parsedLine[2]
            }
            data[key].append(student)

with open(pathes.STUDENTS_JSON, "w",  encoding = "utf8") as file:
    jsonData = json.dumps(data, indent = 4, ensure_ascii = False)
    file.write(jsonData)