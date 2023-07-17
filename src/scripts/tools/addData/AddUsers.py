import json
import sys
sys.path.append("src/scripts/tools/")
import pathes

def GetPhoneNum(phone):
    if int(phone) == 0:
        return None
    phone = phone[1:]
    resultStr = "+380 ("
    resultStr += phone[:2] + ") "
    phone = phone[2:]
    resultStr += phone[:3] + " "
    phone = phone[3:]
    resultStr += phone[:2] + " "
    phone = phone[2:]
    resultStr += phone[:2]
    return resultStr

def ProcessUser(lines):
    chat_id, last_name, first_name, father_name, phone, email, login, password, user_type, class_name = map(str.strip, lines[:10])

    user = {
        "chatID": int(chat_id),
        "lastName": last_name,
        "firstName": first_name,
        "fatherName": father_name,
        "phone": None,
        "email": email,
        "logIn": {
            "login": login,
            "password": password,
        },
        "userType": {
            "developer": False,
            "admin"    : False, 
            "teacher"  : False,
            "student"  : False
            
        }
    }

    if user_type == "teacher":
        user["userType"]["teacher"] = True
        user["userType"]["student"] = False
        user["lastName"] = last_name
        user["firstName"] = first_name
        user["fatherName"] = father_name
        user["phone"] = GetPhoneNum(phone)
        user["userType"]["teacher"] = {
        "classTeacher" : None if int(class_name) == "0" else int(class_name)
        }
    elif user_type == "student":
        user["userType"]["teacher"] = False
        user["userType"]["student"] = True
        user["lastName"] = last_name
        user["firstName"] = first_name
        user["fatherName"] = father_name
        user["phone"] = None if phone == "0" else 0
        user["userType"]["student"] = {
            "class": int(class_name)
        }
    elif user_type == "admin":  
        user["userType"]["admin"] = True
        user["phone"] = GetPhoneNum(phone)
    elif user_type == "developer":  
        user["userType"]["developer"] = True
    return user

def ReadUsersFromFile(file_path):
    users = []
    with open(file_path, "r", encoding="utf8") as file:
        lines = []
        for line in file:
            stripped_line = line.strip()
            if stripped_line:
                lines.append(stripped_line)
            elif lines:
                user = ProcessUser(lines)
                users.append(user)
                lines = []
        if lines:
            user = ProcessUser(lines)
            users.append(user)
    return users

def WriteUsersToJson(users, file_path):
    with open(file_path, "w", encoding="utf8") as file:
        json.dump(users, file, indent=4, ensure_ascii=False)

users = ReadUsersFromFile(pathes.USERS_TXT)

WriteUsersToJson(users, pathes.USERS_JSON)
