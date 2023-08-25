import json
import scripts.tools.mongo as mongo
import scripts.tools.pathes as pathes



from telegram.ext import ContextTypes


# {
#     "lastName"  : splitedMsg[0], str
#     "firstName" : splitedMsg[1], str
#     "fatherName": splitedMsg[2], str
#     "class"     : int()
#     "login"     : "",
#     "password"  : ""
# }
def StudentExist(user) -> bool:    
    if not user:
        return False
    
    return mongo.students.find_one({ str(user["class"]) : {
                                            "lastName"  : user.get("lastName"),
                                            "firstName" : user.get("firstName"),
                                            "fatherName": user.get("fatherName")}}) != None


# {
#     "login"   : "userLogin",
#     "password": "userPassword"
# }
def UserExistInDB(userLoginData):
    if not userLoginData:
        return None
    
    return mongo.users.find_one({"logIn.login": userLoginData["login"], "logIn.password": userLoginData["password"]})


def LoginExist(login) -> bool:
    if not login:
        return False

    return bool(result := mongo.users.find_one({ "logIn.login": login }))


def ChatIdIExistInDB(chatId):
    return None if not chatId else mongo.users.find_one({"chatID" : chatId})


def CheckPasssword(password):
    if len(password) < 8:
        return False
    if not any(char.isdigit() for char in password):
        return False
    return any((char.isupper() for char in password))


def IsValidEmail(email) -> bool:
    if not email:
        return False
    
    import re
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return re.match(pattern, email) != None


def EmailExistInDB(email) -> bool:
    return False if not email else mongo.users.find_one({"email" : email}) != None


def UserExist(chatId, context: ContextTypes.DEFAULT_TYPE):
    user = mongo.users.find_one({ "_id" : chatId })
    Log(user)
    if user:
        context.user_data["user"] = user["user"]
        return True
    return False


def Log(msg):
    print("--" * 30)
    print(msg)
    print("--" * 30)


def ValidateUserNeme(name : str) -> str:
    name = ValidateMsg(name)
    import re
    name = re.sub(r"\s+", " ", name)
    return name


def IsStudent(name: str) -> bool:
    data     : list = name.split(" ")
    students : dict = dict()

    with open(pathes.STUDENTS_JSON, "r", encoding="utf8") as file:
        students = json.load(file)[data[len(data) - 1]]

    return any(
        item["lastName"] in data
        and item["firstName"] in data
        and item["fatherName"] in data
        for item in students
    )


def ValidateMsg(message : str) -> str:
    message = message.lstrip(' +×÷=/_<>[]!@#₴%^&*()-":;,?`~\|{}€£¥$°•○●□■♤♡◇♧☆▪️¤《》¡¿')
    message = message.rstrip(' +×÷=/_<>[]!@#₴%^&*()-":;,?`~\|{}€£¥$°•○●□■♤♡◇♧☆▪️¤《》¡¿')
    return message