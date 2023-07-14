import sys
sys.path.append("src/scripts/tools")
import pathes
import mongo
from phrases import PhrasesGenerator


import json
import asyncio
import requests
from emailSender import Email
from followLesson import FollowLesson
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import CallbackContext, ContextTypes
import os



def isJsonEmpty(file_path):
    file_size = os.path.getsize(file_path)
    return file_size == 0

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["user"] = dict()
    
    if user := ChatIdIExistInDB(update.effective_chat.id):
        context.user_data["user"]["id"] = user.get("chatId")
        
        if user.get("userType").get("teacher"):
            context.user_data["user"]["teachingClass"] = user.get("userType").get("teacher").get("class")
        else:
            context.user_data["user"]["class"] = user.get("userType").get("student").get("class")
        
        # TODO: Open fiches.
    else:
        await update.message.reply_text(f"Привіт, {update.effective_user.full_name}.")
        await EntryMenu(update, context)


async def EntryMenu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    signUp = KeyboardButton("Реєстрація")
    logIn  = KeyboardButton("Вхід")
    reply_markup = ReplyKeyboardMarkup([[signUp, logIn]], resize_keyboard=True)
    
    context.user_data["isEntryMenu"] = True
    
    await asyncio.sleep(1)
    await context.bot.send_message(chat_id = update.effective_chat.id, text = "Оберіть дію", reply_markup = reply_markup)


async def CheckAirDangerous(context : CallbackContext):
    state = await requests.get("https://ubilling.net.ua/aerialalerts/").json()["states"]["Луганська область"]
    
    # TODO: will try to save the data of current state in context.caht_data and read this stuff from it
    
    if state["alertnow"]:
        users = mongo.users.find()  # Get all users.
        for user in users:
            await context.bot.send_message(chat_id = user.get("_id"),
                                            text = "УВАГА!\nОголошена повітряна тривога!\n" + 
                                            "Уроки призупинені!\n" + 
                                            "Пройдіть в укриття!\n" + 
                                            "Бережіться. Цьом)")


async def send_lesson_start_notification(context : CallbackContext):
    followLesson = FollowLesson(int(context.user_data.get("user").get("class")))
    lessonData = await followLesson.GetCurrentLessonAsync()
    
    if lessonData is not None:  # The lessons' time.
        if not lessonData["isHoliday"] and not lessonData["isBreak"]:  # The lesson start or heppen.
            sendedLessonData = context.user_data.get("user").get("lessonData")
            if sendedLessonData:
                # If we have sended msg about lesson to current user.
                if sendedLessonData["infoLesson"] == lessonData["infoLesson"]:
                    return
            
            # Sending.
            await context.bot.send_message(chat_id = context.user_data.get("user").get("_id"), 
                                            text = PhrasesGenerator(lessonData["infoLesson"]["name"], 
                                                                    pathes.START_LESSON_PHRASES_TXT).GetRandomPhrase() +
                                            "\nПочаток уроку : {}".format(lessonData["infoLesson"]["startTime"]) + 
                                            "\nКінець уроку  : {}".format(lessonData["infoLesson"]["endTime"]),
                                            parse_mode = "HTML")
            
            context.user_data["user"]["lessonData"] = lessonData  # Save the info about lesson in our user.
            print("the msg has been sent")
        
        elif lessonData["isBreak"]:  # if we have a break.
            # If we have sended the msg about the break.
            sendedLessonData = context.user_data.get("user").get("lessonData")
            if sendedLessonData:                
                if sendedLessonData["infoLesson"] == lessonData["infoLesson"]:
                    return
            
            # Sending.
            await context.bot.send_message(chat_id = context.user_data.get("user").get("_id"), 
                    text = PhrasesGenerator(lessonData["infoLesson"]["name"], 
                                            pathes.BREAK_PHRASES_TXT).GetRandomPhrase() +
                                            "\nПочаток уроку : {}".format(lessonData["infoLesson"]["startTime"]) + 
                                            "\nКінець уроку  : {}".format(lessonData["infoLesson"]["endTime"]),
                                            parse_mode = "HTML")
            
            context.user_data["user"]["lessonData"] = lessonData  # Save the info about lesson in our user.
            print("the msg has been sent")



async def MessagesHandler(update: Update, context: CallbackContext):
    if context.user_data.get("isEntryMenu"):
        await EntryMenuHandler(update, context)
        
    
    # if context.user_data.get("user").get("firstStartCalling"):  # The first calling.
    #     await StartCallMsgHandler(update.message.text, update.effective_chat.id, context)
    #     del context.user_data["user"]["firstStartCalling"]  # The info about first calling has deleted.
    
    # elif context.user_data.get("user").get("enteringFullnameAndClass"):  # User entered his name.
    #     await StudentNameInputHandler(update.message.text, update.effective_chat.id, context)
    
    # else:
    #     await context.bot.send_message(chat_id = update.effective_chat.id, text = "Нажаль такої команди не існує)")



async def EntryMenuHandler(update : Update, context : CallbackContext):
    message   : str = update.message.text
    chatId    : int = update.effective_chat.id
    messageId : int = update.effective_message.id
    
    logInState : int = context.user_data.get("logInState", 0)
    signState  : int = context.user_data.get("signState", 0)
    
    # The buttons for issues.
    yes = KeyboardButton("Так")
    no = KeyboardButton("Ні")
    replyMarkup = ReplyKeyboardMarkup([[yes, no]], resize_keyboard=True)
    
    
    if "Вхід" in message:
        await context.bot.send_message(chat_id = chatId, text = "Введіть ваш логін", reply_markup = ReplyKeyboardRemove())
        context.user_data["logInState"] = 1  # User is going to send the login. 
        
    elif logInState == 1:
        if LoginExist(message):
            await context.bot.send_message(chat_id = chatId, text = "Вітаю. Логін успішно прийнято.")
            
            context.user_data["logIn"] = dict()
            context.user_data["logIn"]["login"] = message
            context.user_data["logInState"] = 2  # User is going to send the password.
            
            await context.bot.send_message(chat_id = chatId, text = "Введіть ваш пароль.")
            
        else:
            await context.bot.send_message(chat_id = chatId, text = "Зареєстрованого користувача із таким логіном немає!.")
            await asyncio.sleep(1)
            await context.bot.send_message(chat_id = chatId, text = "Можливо ви ввели щось неправильно. Спробувати ще раз?",
                                            reply_markup = replyMarkup)
            
            context.user_data["logInState"] = -1
    
    elif logInState == 2:
        context.user_data["logIn"]["password"] = message
        
        await asyncio.sleep(1)
        await context.bot.delete_message(chat_id = chatId, message_id = messageId)
        await context.bot.send_message(chat_id = chatId, text = "Здійснюється перевірка введених даних. Зачекайте.")
        
        userLoginData = context.user_data.get("logIn")
        print(userLoginData)
        
        if user := UserExistInDB(userLoginData):
            context.user_data["user"]["id"] = chatId
            
            if user.get("userType").get("teacher"):
                context.user_data["user"]["teachingClass"] = user.get("userType").get("teacher").get("class")
            else:
                context.user_data["user"]["class"] = user.get("userType").get("student").get("class")
            
            del context.user_data["isEntryMenu"]
            await context.bot.send_message(chat_id = chatId, text = "Вхід успішний!")
            await asyncio.sleep(2)
            
            # TODO: open all fiches.
            
        else:
            await context.bot.send_message(chat_id = chatId, text = "Пароль неправильний!")
            await asyncio.sleep(1)
            await context.bot.send_message(chat_id = chatId, text = "Спробувати ще раз!", reply_markup = replyMarkup)
            context.user_data["logInState"] = -2
    
    elif logInState == -1:
        await YesNoEntryHandler(update, context, "logInState", 1, "Надішліть свій логін.", "Тоді вертаємося до початкового меню")
    
    elif logInState == -2:
        await YesNoEntryHandler(update, context, "signState", 2, "Надішліть свій пароль.", "Тоді вертаємося до початкового меню")

    
    elif "Реєстрація" in message:
        await context.bot.send_message(chat_id = chatId, 
                    text = "Для початку введіть своє Прізвище Ім'я По-батькові", 
                    reply_markup = ReplyKeyboardRemove())
        
        context.user_data["signState"] = 1  # User is going to send his first last & father names.
    
    elif signState == 1:
        splitedMsg = message.split(' ')
        
        try:
            studentData = {
                "lastName"  : splitedMsg[0],
                "firstName" : splitedMsg[1],
                "fatherName": splitedMsg[2],
            }
            
            if mongo.users.find_one(studentData):
                context.user_data["signState"] = -1  # User exists.
                
                await context.bot.send_message(chat_id = chatId, text = "Вибачте але такий користувач вже зареєстрований. Можливо ви помилилися, спробувати знову?",
                                                reply_markup = replyMarkup)
            else:
                context.user_data["signInfo"] = studentData
                await context.bot.send_message(chat_id = chatId, text = "Наступний крок - введіть клас в якому ви навчаєтеся")
                context.user_data["signState"] = 2  # User is going to send his class.
            
        except:
            print("he wrote less args")
            await context.bot.send_message(chat_id = chatId, 
                    text = "Виввели неправильну кількість даних.\nПереконайтеся що попереднє повідомлення було коректне.\n" + 
                    "Наприклад:\n\tПетренко Петро <- НЕПРАВИЛЬНО\n\tПетренко Петро Петрович <- ПРАВИЛЬНО")
        
    elif signState == 2:
        try:
            classNum = int(message)
            print("class ", classNum)
            
            context.user_data["signInfo"]["class"] = classNum
            await context.bot.send_message(chat_id = chatId, text = "Зачекайте! Здійснюється перевірка ваших даних!")
            # TODO: sleep
            if StudentExist(context.user_data["signInfo"]):
                print("we are here")
                await context.bot.send_message(chat_id = chatId, text = "Перевірка пройшла успішно!")
                await context.bot.send_message(chat_id = chatId, text = "Далі введіть свою електронну пошту.")
                context.user_data["signState"] = 3  # User is going to send his e-mail.
                
            else:
                context.user_data["signState"] = -2  # User does not exist.
                await context.bot.send_message(chat_id = chatId, text = "Вибачте такого учня в цьому класі немає.\n" + 
                                                "Можливо ви ввели неправильні дані. Спробувати ще раз?",
                                                reply_markup = replyMarkup)
            
        except:
            print("he wrote incorect args")
            await context.bot.send_message(chat_id = chatId, 
                    text = "Виввели неправильні дані.\nПереконайтеся що попереднє повідомлення було коректне.\n" + 
                    "Наприклад:\n\t9 клас ← НЕПРАВИЛЬНО\n\t9 ← ПРАВИЛЬНО")
    
    elif signState == 3:
        import random
        code : int = random.randint(1000, 9999)
        
        await context.bot.send_message(chat_id = chatId, text = "Зараз на вашу пошту надійде повідомлення, яке буде складатися з чотирьох цифр" + 
                                                                "\nЯкщо повідомлення довго не зявляється перевірте СПАМ.")
        
        try:
            # TODO: check email existing.
            Email().Send(message, "РЕЄСТРАЦІЙНИЙ ЛИСТ", "Вітаю ви реєструєтеся в чат-боті Вівнянського ЗНЗ І-ІІ ст. - ДНЗ.\n" + 
                        "Це код який ви повинні ввести в боті: " + str(code) + "\nНікому стононньому не повідомляйте його.\n" +
                        "Бажаємо гарного дня")
            
            context.user_data["signInfo"]["email"] = message
            context.user_data["signInfo"]["code"] = str(code)
            
            context.user_data["signState"] = 4  # User is going to send the code.
        except:
            print("something wrong in sending letter")
            await context.bot.send_message(chat_id = chatId, text = "Вибачте але сталася якась помилка, перевірте правильність вказання пошти")
    
    elif signState == 4:
        if rightCode := context.user_data.get("signInfo").get("code"):
            if rightCode in message:
                await context.bot.send_message(chat_id = chatId, text = "Ви успішно підтвердили свою пошту.\nДалі введіть логін, який будете" +
                                            " використовувати під час входу.\n<b>Радимо використати свою пошту.</b>", parse_mode = "HTML") 
                
                del context.user_data["signInfo"]["code"]
                context.user_data["signState"] = 5  # User is going to send his login.
                
            else:
                await context.bot.send_message(chat_id = chatId, text = "На жаль, ви ввели неправильний код.") 
        else:
            print("Code dosen't exist")
    
    elif signState == 5:
        if LoginExist(message):
            await context.bot.send_message(chat_id = chatId, text = "Введений логін уже занятий, спробуйте будь ласка інший!")
        else:
            context.user_data["signInfo"]["login"] = message
            await context.bot.send_message(chat_id = chatId, text = "Логін успішно додано.")
            
            context.user_data["signState"] = 6  # User is going to send his password.
            
            await context.bot.send_message(chat_id = chatId,
                text = "Тепер потрібно ввести пароль, який будете використовувати при вході.<b>(За 5 секунд це повідомлення з паролем видалиться, з міркувань конфіденційності)</b>",
                parse_mode = "HTML")
    
    elif signState == 6:
        context.user_data["signInfo"]["password"] = message
        
        await asyncio.sleep(5)
        await context.bot.delete_message(chat_id = chatId, message_id = messageId)  # Delete the password, that user provided.
        await context.bot.send_message(chat_id = chatId, text = "Пароль успішно додано.")
        
        user = {
            "chatID"    : chatId,
            "fatherName": context.user_data["signInfo"]["fatherName"],
            "firstName" : context.user_data["signInfo"]["firstName"],
            "lastName"  : context.user_data["signInfo"]["lastName"],
            "phone"     : None,
            "email"     : context.user_data["signInfo"]["email"],
            "logIn"     : {
                    "login"   : context.user_data["signInfo"]["login"],
                    "password": context.user_data["signInfo"]["password"] 
                },
            "userType"  : {
                    "teacher": False,
                    "student": {
                        "class": context.user_data["signInfo"]["class"]
                    }
                }
            }
        
        mongo.users.insert_one(user)
        del context.user_data["signState"]
        del context.user_data["isEntryMenu"]
        # TODO: add functions calling. 

    elif signState == -1:
        await YesNoEntryHandler(update, context, "signState", 1, "Надішліть своє Прізвище Ім'я По-батькові.", "Тоді вертаємося до початкового меню")
    
    elif signState == -2:
        await YesNoEntryHandler(update, context, "signState", 2, "Надішліть клас в якому навчаєтесь.", "Тоді вертаємося до початкового меню")


async def YesNoEntryHandler(update : Update, context : CallbackContext, stateName : str, statePos : int, yesText : str, noText : str):
    message : str = update.message.text
    chatId  : int = update.effective_chat.id
    
    if "Так" in message:
            await context.bot.send_message(chat_id = chatId, 
                                            text = yesText, 
                                            reply_markup = ReplyKeyboardRemove())
            context.user_data[stateName] = statePos
            
    elif "Ні" in message:
            await context.bot.send_message(chat_id = chatId, 
                                            text = noText, 
                                            reply_markup = ReplyKeyboardRemove())
            EntryMenu(update, context)  # TODO: To first menu.
    
    else:
            await context.bot.send_message(chat_id = chatId, text = "Введено некоректне повідомлення")


# {
#     "lastName"  : splitedMsg[0], str
#     "firstName" : splitedMsg[1], str
#     "fatherName": splitedMsg[2], str
#     "class"     : int()
#     "login"     : "",
#     "password"  : ""
# }
def StudentExist(user) -> bool:    
    with open (pathes.STUDENTS_JSON, "r", encoding = "utf8") as file:
        data = json.load(file)
    
        if str(user["class"]) in data:
            students = data [str(user["class"])]
            for student in students:
                if (student ["lastName"] == user["lastName"] and
                    student ["firstName"] == user["firstName"] and 
                    student ["fatherName"] == user["fatherName"]):
                    return True
            return False


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
    
    result = mongo.users.find_one({ "logIn.login": login })
    if result:
        return True
    return False


def ChatIdIExistInDB(chatId):
    if not chatId:
        return None
    
    return mongo.users.find_one({"chatId" : chatId})





async def StartCallMsgHandler(message : str, chatId, context : CallbackContext):
    message = ValidateMsg(message).lower()
    
    if "так" in message:
        await context.bot.send_message(chat_id = chatId,
                                    text = """
        Добренько. Тоді введіть ваше прізвише ім'я побатькові та клас.\nПриклад: Петренко Петро Пeтрович 10""",
                                    reply_markup = ReplyKeyboardRemove())
        
        # The variable that store user ability to the next msg input.
        context.user_data["user"]["enteringFullnameAndClass"] = True  
        
    elif "ні" in message:
        await context.bot.send_message(chat_id = chatId,
                                    text = """Тоді вам немає що тут робити :)\nБувайте""",
                                    reply_markup = ReplyKeyboardRemove())
        
    else:
        await context.bot.send_message(chat_id=chatId,
                                    text = """Не коректне повідомлення, впевніться, що ви натисли на потрібну кнопку""")


async def StudentNameInputHandler(message : str, chatId, context : CallbackContext):
    name : str = ValidateUserNeme(message)
    
    if IsStudent(name):
        del context.user_data["user"]["enteringFullnameAndClass"]
        context.user_data["user"]["class"] = name.split(' ')[-1] # TODO: Maybe delete this stuff if the json users file will be create. 
        
        await context.bot.send_message(chat_id = chatId, text = "Вітаємо")
        context.job_queue.run_repeating(send_lesson_start_notification, interval = 2, first = 0, user_id = chatId)
        
        user = mongo.users.find_one({ "_id" : chatId })
        if user:
            # TODO: Update values.
            pass
        else:
            user : dict = {
                "_id"  : context.user_data.get("user").get("_id"),
                "user" : context.user_data["user"]
            }
            mongo.users.insert_one(user)
        # with open(pathes.USERS_JSON, 'w', encoding = "utf8") as file:
        #     json.dump({ str(chatId) : context.user_data.get("user") }, file, indent = 4, ensure_ascii = False)

    else:
        await context.bot.send_message(chat_id = chatId, text = """
            Нажаль такого користувача немає. Впевніться що ввели дані коректно. Або зверніться в технічну підтримку.""")




def UserExist(chatId, context: ContextTypes.DEFAULT_TYPE):
    user = mongo.users.find_one({ "_id" : chatId })
    Log(user)
    if user:
        context.user_data["user"] = user["user"]
        return True
    return False
    # if not isJsonEmpty(pathes.USERS_JSON):
    #     with open(pathes.USERS_JSON, 'r', encoding="utf8") as file:
    #         userData = json.load(file).get(str(chatId))
    #         if userData:
    #             context.user_data["user"] = userData
    #             return True
    # return False

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

    for item in students:
        # If we have the user.
        if item["lastName"] in data and item["firstName"] in data and item["fatherName"] in data:
            return True
    return False


def ValidateMsg(message : str) -> str:
    message = message.lstrip(' +×÷=/_<>[]!@#₴%^&*()-":;,?`~\|{}€£¥$°•○●□■♤♡◇♧☆▪️¤《》¡¿')
    message = message.rstrip(' +×÷=/_<>[]!@#₴%^&*()-":;,?`~\|{}€£¥$°•○●□■♤♡◇♧☆▪️¤《》¡¿')
    return message