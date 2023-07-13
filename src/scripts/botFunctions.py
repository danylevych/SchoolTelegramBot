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
    await update.message.reply_text(f"Привіт, {update.effective_user.full_name}.")
    
    signUp = KeyboardButton("Реєстрація")
    logIn  = KeyboardButton("Вхід")
    reply_markup = ReplyKeyboardMarkup([[signUp, logIn]], resize_keyboard=True)
    
    context.user_data["isEntryMenu"] = True
    
    await asyncio.sleep(1)
    await context.bot.send_message(chat_id = update.effective_chat.id, text = "Оберіть дію", reply_markup = reply_markup)
    
    # if UserExist(update.effective_chat.id, context):
    #     context.job_queue.run_repeating(send_lesson_start_notification, interval = 2, first = 0, user_id = context.user_data.get("user").get("_id"))
    
    # else:
    #     context.user_data["user"]["firstStartCalling"] = True
    #     context.user_data["user"]["_id"] = update.effective_chat.id

    #     await update.message.reply_text(f"Привіт, {update.effective_user.full_name}.")

    #     yes = KeyboardButton("Так")
    #     no = KeyboardButton("Ні")
    #     reply_markup = ReplyKeyboardMarkup([[yes, no]], resize_keyboard=True)

    #     await asyncio.sleep(1)
    #     await context.bot.send_message(chat_id = update.effective_chat.id,
    #                                     text = "А ти навчаєшся в ЗОШ Вівня?",
    #                                     reply_markup = reply_markup)


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
        await EntryMenu(update.message.text, update.effective_chat.id, context, update.effective_message.id)
        
    
    # if context.user_data.get("user").get("firstStartCalling"):  # The first calling.
    #     await StartCallMsgHandler(update.message.text, update.effective_chat.id, context)
    #     del context.user_data["user"]["firstStartCalling"]  # The info about first calling has deleted.
    
    # elif context.user_data.get("user").get("enteringFullnameAndClass"):  # User entered his name.
    #     await StudentNameInputHandler(update.message.text, update.effective_chat.id, context)
    
    # else:
    #     await context.bot.send_message(chat_id = update.effective_chat.id, text = "Нажаль такої команди не існує)")



async def EntryMenu(message : str, chatId, context : CallbackContext, messageId):
    logInState : int = context.user_data.get("logInState", 0)
    signState  : int = context.user_data.get("signState", 0)
    
    if "Вхід" in message:
        await context.bot.send_message(chat_id = chatId, text = "Введіть ваш логін", reply_markup = ReplyKeyboardRemove())
        context.user_data["logInState"] = 1  # User is going to send the login. 
        
    elif logInState == 1:
        await context.bot.send_message(chat_id = chatId, text = "Введіть ваш пароль")
        context.user_data["logIn"] = dict()
        context.user_data["logIn"]["login"] = message
        context.user_data["logInState"] = 2  # User is going to send the password.
    
    elif logInState == 2:
        context.user_data["logIn"]["password"] = message
        # await asyncio.sleep(5)
        await context.bot.delete_message(chat_id = chatId, message_id = messageId)
        await context.bot.send_message(chat_id = chatId, text = "Здійснюється перевірка введених даних. Зачекайте.")
        
        userLoginData = context.user_data.get("logIn")
        print(userLoginData)
        if UserExistInDB(userLoginData):
            print("now we here")
            # TODO: open all fiches.
            context.user_data["user"] = { "class", mongo.users.find_one({"logIn.login"   : userLoginData["login"], 
                                                                        "logIn.password": userLoginData["password"]}).get("class") }
            del context.user_data["isEntryMenu"]
        else:
            await context.bot.send_message(chat_id = chatId, text = "Такого користувача не знайдено!")
            # TODO: move to first menu.
    
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
            
            result = mongo.users.find_one(studentData)
            
            if result:
                context.user_data["signState"] = -1  # User does not exist.
                yes = KeyboardButton("Так")
                no = KeyboardButton("Ні")
                reply_markup = ReplyKeyboardMarkup([[yes, no]], resize_keyboard=True)
                await context.bot.send_message(chat_id = chatId, text = "Вибачте але такий користувач вже зареєстрований. Можливо ви помилилися, спробувати знову?",
                                            reply_markup = reply_markup)
                # del context.user_data["signState"] 
                # TODO: Move to start funk.
            else:
                context.user_data["signInfo"] = studentData
                await context.bot.send_message(chat_id = chatId, text = "Наступний крок - введіть клас в якому ви навчаєтеся")
                context.user_data["signState"] = 2  # User is going to send his class.
            
        except:
            print("he wrote less args")
            await context.bot.send_message(chat_id = chatId, 
                    text = "Виввели неправильну кількість даних.\n" +
                    "Переконайтеся що попереднє повідомлення було коректне.\n" + 
                    "Наприклад:\n\tПетренко Петро <- НЕПРАВИЛЬНО\n"+
                    "\tПетренко Петро Петрович <- ПРАВИЛЬНО")
        
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
                yes = KeyboardButton("Так")
                no = KeyboardButton("Ні")
                reply_markup = ReplyKeyboardMarkup([[yes, no]], resize_keyboard=True)
                
                await context.bot.send_message(chat_id = chatId, text = "Вибачте такого учня в цьому класі немає.\n" + 
                                                "Можливо ви ввели неправильні дані. Спробувати ще раз?",
                                                reply_markup = reply_markup)
            
        except:
            print("he wrote incorect args")
            await context.bot.send_message(chat_id = chatId, 
                    text = "Виввели неправильні дані.\n" +
                    "Переконайтеся що попереднє повідомлення було коректне.\n" + 
                    "Наприклад:\n\t9 клас ← НЕПРАВИЛЬНО\n"+
                    "\t9 ← ПРАВИЛЬНО")
    
    elif signState == 3:
        import random
        code : int = random.randint(1000, 9999)
        
        await context.bot.send_message(chat_id = chatId, text = "Зараз на вашу пошту надійде повідомлення, яке буде складатися з чотирьох цифр" + 
                                                                "\nЯкщо повідомлення довго не зявляється перевірте СПАМ.")
        
        try:
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
        rightCode = context.user_data.get("signInfo").get("code")
        
        if rightCode:
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
        await context.bot.delete_message(chat_id = chatId, message_id = messageId)
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
        if "Так" in message:
            await context.bot.send_message(chat_id = chatId, 
                                            text = "Надішліть своє Прізвище Ім'я По-батькові знову.", 
                                            reply_markup = ReplyKeyboardRemove())
            context.user_data["signState"] = 1
        elif "Ні" in message:
            await context.bot.send_message(chat_id = chatId, 
                                            text = "Тоді вертаємося до початкового меню", 
                                            reply_markup = ReplyKeyboardRemove())
            # TODO: To first menu.
        else:
            await context.bot.send_message(chat_id = chatId, text = "Введено некоректне повідомлення")
    elif signState == -2:
        if "Так" in message:
            await context.bot.send_message(chat_id = chatId, 
                                            text = "Надішліть клас в якому навчаєтесь.", 
                                            reply_markup = ReplyKeyboardRemove())
            context.user_data["signState"] = 2
        elif "Ні" in message:
            await context.bot.send_message(chat_id = chatId, 
                                            text = "Тоді вертаємося до початкового меню", 
                                            reply_markup = ReplyKeyboardRemove())
            # TODO: To first menu.
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

def UserExistInDB(userLoginData) -> bool:
    if not userLoginData:
        return False
    
    user = mongo.users.find_one({"logIn.login": userLoginData["login"], "logIn.password": userLoginData["password"]})

    if user:
        return True
    else:
        return False

def LoginExist(login) -> bool:
    if not login:
        return False
    
    result = mongo.users.find_one({ "logIn.login": login })
    if result:
        return True
    return False


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