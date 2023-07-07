import json
import sys
sys.path.append("src/scriptsr/tools/")
import pathes


def GetPhoneNum(phone : str):
    if int(phone) == 0:
        return None
    phone = phone[1 : ]
    resultStr : str = "+380 ("
    resultStr += phone[ : 2] + ") "
    phone = phone[2 : ]
    resultStr += phone[ : 3] + " "
    phone = phone[3 : ]
    resultStr += phone[ : 2] + " "
    phone = phone[2 : ]
    resultStr += phone[ : 2]
    return resultStr




data : list = list()

# Прізвище ім'я побатькові клас_який_навчає [предмети та класи] телефон чи адмін 

with open(pathes.TEACHERS_TXT, "r", encoding = "utf8") as file:
    for line in file:  
        line = line.replace('\n', '')
        
        name : str = str()
        
        index : int = int()
        for count in range(3):
            index = line.find(' ', index + 1)
            if count == 2:
                name = line[ : index].split(' ')
                line = line[index + 1: ]

            
        teachingClass = line[ : line.find(' ')]
        line = line[line.find(' ') : ] # + 

        subjectStr = line[line.find('[') + 1 : line.find(']')].split(' ')
        print(subjectStr)
        print(line)
        line = line[line.find(']') + 2 :] # Номер і чи адмін

        currentSubject : str = str()
        listOfSubject  : dict = dict()

        for item in subjectStr:
            if item.isdigit():
                listOfSubject[currentSubject].append(item)
            else:
                currentSubject = item.replace('_', ' ')
                listOfSubject[currentSubject] = list()

        adminPart : int = line.rfind(' ')
        
        teacher : dict = {
            "lastName"    : name[0], 
            "firstName"   : name[1],
            "fatherName"  : name[2],
            "classTeacher": None if teachingClass == 0 else teachingClass,
            "subjects"    : listOfSubject,
            "phoneNumber" : GetPhoneNum(line[ : adminPart]),
            "admin"       : None if int(line[adminPart + 1]) == 0 else int(line[adminPart + 1])
        }
        
        data.append(teacher)
        

with open(pathes.TEACHERS_JSON, "w",  encoding = "utf8") as file:
    jsonData = json.dumps(data, indent = 4, ensure_ascii = False)
    file.write(jsonData)