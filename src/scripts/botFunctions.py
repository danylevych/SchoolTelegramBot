import json
import asyncio
import requests
import scripts.tools.mongo as mongo
import scripts.tools.pathes as pathes

from scripts.classes.emailSender import Email
from scripts.tools.phrases import PhrasesGenerator
from scripts.classes.followLesson import FollowLesson
from scripts.classes.timetable import TimetableForTeacher
from scripts.classes.teacherSubjects import TeacherSubjects

from telegram.ext import CallbackContext, ContextTypes
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

import os



def isJsonEmpty(file_path):
    file_size = os.path.getsize(file_path)
    return file_size == 0




async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["user"] = dict()
    
    if user := ChatIdIExistInDB(update.effective_chat.id):
        context.user_data["user"]["id"] = user.get("chatID")
        context.user_data["user"]["firstName"] = user.get("firstName")
        context.user_data["user"]["lastName"] = user.get("lastName")
        context.user_data["user"]["fatherName"] = user.get("fatherName")
        
        userType = user.get("userType")
        
        if userType.get("developer") or userType.get("admin"):
            context.user_data["user"]["type"] = "developer" if userType.get("developer") else "admin"
            await AdminMenu(update, context)
            

        elif user.get("userType").get("teacher"):
            teacher = mongo.teachers.find_one({ "firstName"  : user.get("firstName"), 
                                                "lastName"   : user.get("lastName"),
                                                "fatherName" : user.get("fatherName")})
            
            context.user_data["user"]["classTeacher"] = int(teacher.get("classTeacher"))
            
            if context.user_data.get("user").get("classTeacher") != 0:
                await TeacherMenu1(update, context)
            
            else:
                pass
        else:
            # context.user_data["user"]["class"] = user.get("userType").get("student").get("class")
            # Open student menu.
            pass
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


async def AdminMenu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["isAdminMenu"] = True
        
    notification = KeyboardButton("Створити оголошення")
    exit         = KeyboardButton("Вихід")
    replyMarkup  = ReplyKeyboardMarkup([[notification], [exit]], resize_keyboard = True)
    
    await context.bot.send_message(chat_id = update.effective_chat.id, text = "Ви ввійшли як " + 
                                    ("<b>РОЗРОБНИК</b>" if context.user_data.get("user").get("type") == "developer" else "<b>АДМІНІСТРАТОР ШКОЛИ</b>"),
                                    parse_mode = "HTML", reply_markup = replyMarkup)


async def TeacherMenu1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["isTecherMenu1"] = True
    
    notification   = KeyboardButton("Створити оголошення для учнів")
    checkTimetable = KeyboardButton("Подивитися сьогоднішній розклад")
    createHomeWork = KeyboardButton("Створити домашнє завдання")
    checkClassList = KeyboardButton("Переглянути список учнів")
    exit           = KeyboardButton("Вихід")
    replyMarkup    = ReplyKeyboardMarkup([[notification], [checkTimetable], [checkClassList], [createHomeWork], [exit]], resize_keyboard = True)
    
    await context.bot.send_message(chat_id = update.effective_chat.id, text = "Ви ввійшли як <b>ВЧИТЕЛЬ</b>", parse_mode = "HTML", reply_markup = replyMarkup)


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
        
    elif context.user_data.get("isAdminMenu"):
        await AdminMenuHandler(update, context)
    
    elif context.user_data.get("isTecherMenu1"):
        await TeacherMenuHandler1(update, context)
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
    
    
    if "Вхід" == message:
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
        
        if user := UserExistInDB(userLoginData):
            if not user.get("chatID"):  # User try to entry for other computer. 
                context.user_data["user"]["id"] = chatId
                mongo.users.update_one({ "logIn": userLoginData }, {"$set" : {"chatID" : chatId}})

                userType = user.get("userType")

                if userType.get("developer") or userType.get("admin"):
                    context.user_data["user"]["type"] = "developer" if userType.get("developer") else "admin"

                    del context.user_data["isEntryMenu"]
                    await asyncio.sleep(1)
                    await context.bot.send_message(chat_id = chatId, text = "Вхід успішний!")

                    await AdminMenu(update, context)

                elif userType.get("teacher"):
                    teacher = mongo.teachers.find_one({ "firstName"  : user.get("firstName"), 
                                                        "lastName"   : user.get("lastName"),
                                                        "fatherName" : user.get("fatherName")})
                    
                    context.user_data["user"]["classTeacher"] = int(teacher.get("classTeacher"))
                    if context.user_data.get("user").get("classTeacher") != 0:
                        await TeacherMenu1(update, context)
            
                    else:
                        pass
                # Open Teacher menu.
                else:
                    # context.user_data["user"]["class"] = user.get("userType").get("student").get("class")
                    pass
            else:
                await context.bot.send_message(chat_id = chatId, text = "Подвійний вхід заборонений!")
                await start(update, context)
            
            
            
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

    
    elif "Реєстрація" == message:
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
        if (not IsValidEmail(message) and (text := "Неправильний формат пошти.")) or (EmailExistInDB(message) and (text := "На цю пошту вже є зареєстрований користувач.")):
            context.user_data["signState"] = -3  # Something wrong with email.
            await context.bot.send_message(chat_id = chatId, text = text + "\nСпробувати знову?", reply_markup = replyMarkup)
            
        else:
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
                text = "Тепер потрібно ввести пароль, який будете використовувати при вході.\n" + 
                "Пароль повинен містити:\n" +
                "\t- мінімум 8 символів.\n" +
                "\t- хоча б одну цифру та велику букву.\n" +  
                "<b>(За 1 секунд повідомлення з паролем видалиться, з міркувань конфіденційності)</b>",
                parse_mode = "HTML")
    
    elif signState == 6:
        await asyncio.sleep(1)
        await context.bot.delete_message(chat_id = chatId, message_id = messageId)  # Delete the password, that user provided.
        
        if CheckPasssword(message):
            context.user_data["signInfo"]["password"] = message

            
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
                        "developer" : False,
                        "admin"     : False,
                        "teacher"   : False,
                        "student"   : True
                    }
                }

            mongo.users.insert_one(user)
            del context.user_data["signState"]
            del context.user_data["isEntryMenu"]
            # TODO: add functions calling. 
        
        else:
            await context.bot.send_message(chat_id = chatId, text = "Ви ввели пароль, який не відповідає вимогам. Будь ласка повторіть введення.")

    elif signState == -1:
        await YesNoEntryHandler(update, context, "signState", 1, "Надішліть своє Прізвище Ім'я По-батькові.", "Тоді вертаємося до початкового меню")
    
    elif signState == -2:
        await YesNoEntryHandler(update, context, "signState", 2, "Надішліть клас в якому навчаєтесь.", "Тоді вертаємося до початкового меню")

    elif signState == -3:
        await YesNoEntryHandler(update, context, "signState", 3, "Надішліть нову пошту.", "Тоді вертаємося до початкового меню")


async def AdminMenuHandler(update : Update, context : CallbackContext):
    message         : str = update.message.text
    chatId          : int = update.effective_chat.id
    notifState      : int = context.user_data.get("notifState", 0)
    backState       : int = context.user_data.get("backState", 0)
    back                  = KeyboardButton("Назад")
    
    
    async def CreateNitify():
        context.user_data["backState"] = 1
        await context.bot.send_message(chat_id = chatId, text = "Ви перейшли до меню створення оголошення.")
        
        forEveryone = KeyboardButton("Для усіх")
        forTeachers = KeyboardButton("Для учителів")
        forStydents = KeyboardButton("Для учнів")
        
        replyMarkup = ReplyKeyboardMarkup([[forEveryone], [forTeachers, forStydents], [back]], resize_keyboard = True)
        await context.bot.send_message(chat_id = chatId, text = "Створити оголошення для...", reply_markup = replyMarkup)
    
    async def ForStudents():
        forEveryone  = KeyboardButton("Для усіх учнів")
        forSomeClass = KeyboardButton("Для певного класу")
        
        replyMarkup = ReplyKeyboardMarkup([[forEveryone, forSomeClass], [back]], resize_keyboard = True)
        await context.bot.send_message(chat_id = chatId, text = "Створити оголошення для...", reply_markup = replyMarkup)
        context.user_data["backState"] = 2
        
    async def GoBack(backSate, notifyState):
        await context.bot.send_message(chat_id = chatId, text = "Введіть та відправте текст оголошення.",
                                        reply_markup = ReplyKeyboardMarkup([[back]], resize_keyboard = True))
        context.user_data["backState"] = backSate
        context.user_data["notifState"] = notifyState
        
        
    if "Створити оголошення" == message:  # TODO: try delete the key in this line.
        await CreateNitify()
    
    elif "Вихід" == message:
        mongo.users.update_one({"chatID" : chatId}, {"$set" : {"chatID" : None}})
        del context.user_data["isAdminMenu"]
        await start(update, context)
        
    elif "Для усіх" == message:
        await GoBack(2, 1)
        
    elif "Для учителів" == message:
        await GoBack(2, 2)
    
    elif "Для учнів" == message:
        await ForStudents()
    
    elif "Для усіх учнів" == message:
        await GoBack(3, 3)
        
    elif "Для певного класу" == message:
        await context.bot.send_message(chat_id = chatId, text = "Введіть номер класу, для якого хочете створити оголошення.",
                                        reply_markup = ReplyKeyboardMarkup([[back]], resize_keyboard = True))
        context.user_data["backState"] = 3
        context.user_data["notifState"] = 4
        
    elif "Назад" == message:
        if backState == 1:    # Move to main admin menu.
            notification = KeyboardButton("Створити оголошення")
            replyMarkup = ReplyKeyboardMarkup([[notification]], resize_keyboard = True)

            await context.bot.send_message(chat_id = update.effective_chat.id, text = "Оберіть дію.", reply_markup = replyMarkup)
            
        elif backState == 2:  # Move to creating menu.
            await CreateNitify()
            
        elif backState == 3:  # Move notify for student
            await ForStudents()
            
    elif notifState == 1:  # Enter msg for all users.
        message = "<b>ОГОЛОШЕННЯ ВІД " + ("РОЗРОБНИКІВ" if context.user_data.get("user").get("type") == "developer" else "АДМІНІСТРАЦІЇ ШКОЛИ") + "</b>\n" + message 
        
        firler = {
            "userType.developer": False,
            "userType.admin"    : False
        }
        await SentToAllWho(firler, message, context)
        await context.bot.send_message(chat_id = chatId, text = "Оголошення надіслане.")
    
    elif notifState == 2:  # Enter msg to teachers.
        message = "<b>ОГОЛОШЕННЯ ВІД " + ("РОЗРОБНИКІВ" if context.user_data.get("user").get("type") == "developer" else "АДМІНІСТРАЦІЇ ШКОЛИ") + "</b>\n" + message 
        
        firler = {
            "userType.developer": False,
            "userType.admin"    : False,
            "userType.student"  : False,
        }
        await SentToAllWho(firler, message, context)
        await context.bot.send_message(chat_id = chatId, text = "Оголошення надіслане.")
        
    elif notifState == 3:  # Enter msg to all students.
        message = "<b>ОГОЛОШЕННЯ ВІД " + ("РОЗРОБНИКІВ" if context.user_data.get("user").get("type") == "developer" else "АДМІНІСТРАЦІЇ ШКОЛИ") + "</b>\n" + message
        
        firler = {
            "userType.developer": False,
            "userType.admin"    : False,
            "userType.teacher"  : False,
        }
        await SentToAllWho(firler, message, context)
        await context.bot.send_message(chat_id = chatId, text = "Оголошення надіслане.")
        
    elif notifState == 4:  # Enter msg to some students.
        if context.user_data.get("isSendingNotify"):
            message = "<b>ОГОЛОШЕННЯ ВІД " + ("РОЗРОБНИКІВ" if context.user_data.get("user").get("type") == "developer" else "АДМІНІСТРАЦІЇ ШКОЛИ") + "</b>\n" + message

            students = mongo.students.find_one({}, {context.user_data.get("whichClass") : 1}).get(context.user_data.get("whichClass"))
            
            filter = { "$or" : students }
            
            del context.user_data["whichClass"]
            del context.user_data["isSendingNotify"]
            
            await SentToAllWho(filter, message, context)
            await context.bot.send_message(chat_id = chatId, text = "Оголошення надіслане.")

        else:
            try:
                context.user_data["whichClass"] = int(message)  # <- maybe error
                await context.bot.send_message(chat_id = chatId, text = "Введіть та відправте текст оголошення.")
                context.user_data["isSendingNotify"] = True
            
            except:
                await context.bot.send_message(chat_id = chatId, text = "Вибачте, але ви ввели неправильний формат класу." +
                                                "\nПриклад:\n" + 
                                                "Неправильно - 5 клас\n"
                                                "Правильно - 5\nСпробуйте ще раз.")


async def TeacherMenuHandler1(update : Update, context : CallbackContext):
    message       : str = update.message.text
    chatId        : int = update.effective_chat.id
    backState     : int = context.user_data.get("backState", 0)
    teachingClass : int = context.user_data.get("user").get("classTeacher")
    back                = KeyboardButton("Назад")
    
    
    async def ClassList(classNum, label):
        students = mongo.students.find_one({}, {str(classNum) : 1}).get(str(classNum))
        if students:
            text : str = label + "\n"
            i = 1
            for student in students:
                text += str(i) + ") {} {} {}\n".format(student.get("lastName").upper(), student.get("firstName"), student.get("fatherName"))
                i += 1
            await context.bot.send_message(chat_id = chatId, text = text, reply_markup = ReplyKeyboardMarkup([[back]], resize_keyboard = True))
        else:
            await context.bot.send_message(chat_id = chatId, text = "Вибачте, але учнів у цьому класі поки немає.", reply_markup = ReplyKeyboardMarkup([[back]], resize_keyboard = True))
    
    # -------------------------------- Creating Funcks -------------------------------- 
    def GetClassButtons():
        students = mongo.students.find()
        
        buttons : list = list()
        twoButton : list = list()
        for table in students:
            for (classItem, studentsTable) in table.items():
                if studentsTable:
                    if str(classItem) != "_id":
                        twoButton.append(KeyboardButton(str(classItem)))
                        if len(twoButton) == 2:
                            buttons.append(twoButton)
                            twoButton = list()
        if len(twoButton) > 0:
            buttons.append(twoButton)
        
        return buttons        
    
    
    async def SendNotify(classNum, message):
        message = "<b>Оголошення від {} {} {}".format(context.user_data.get("user").get("lastName").upper(), 
                                                            context.user_data.get("user").get("firstName"),
                                                            context.user_data.get("user").get("fatherName")) + message + ".</b>\n"
        students = mongo.students.find_one({}, {str(classNum) : 1}).get(str(classNum))
            
        filter = { "$or" : students }
        
        await SentToAllWho(filter, message, context)
        await context.bot.send_message(chat_id = chatId, text = "Оголошення надіслане.")
    
    
    async def CreateNotifyMeny():
        context.user_data["backState"] = 1
        forOwnClass   = KeyboardButton("Для власного класу")
        forOtherClass = KeyboardButton("Для учнів іншого класу")

        replyMarkup    = ReplyKeyboardMarkup([[forOwnClass, forOtherClass], [back]], resize_keyboard = True)
        await context.bot.send_message(chat_id = chatId, text = "Оберіть дію.", reply_markup = replyMarkup)
    # ---------------------------------------------------------------------------------  
        
        
    # ----------------------------- Student List Funcks ------------------------------- 
    async def CheckStudentsListMenu():
        context.user_data["backState"] = 1
        forOwnClass   = KeyboardButton("Список власного класу")
        forOtherClass = KeyboardButton("Список учнів іншого класу")

        replyMarkup    = ReplyKeyboardMarkup([[forOwnClass], [forOtherClass], [back]], resize_keyboard = True)
        await context.bot.send_message(chat_id = chatId, text = "Оберіть дію.", reply_markup = replyMarkup)
    # ---------------------------------------------------------------------------------
    
    
    # ------------------------------- Homework Funcks ---------------------------------
    async def ChooseSubject():
        context.user_data["backState"] = 1
            
        context.user_data["subjects"] = TeacherSubjects(context.user_data.get("user").get("lastName"), context.user_data.get("user").get("firstName"), context.user_data.get("user").get("fatherName")).GetSubjects()
            
        buttons = [[item] for item in context.user_data.get("subjects").keys()]
        buttons.append([back])
        await context.bot.send_message(chat_id = chatId, text = "Оберіть предмет.", reply_markup = ReplyKeyboardMarkup(buttons, resize_keyboard = True))
        
    
    async def ChooseClass():
        context.user_data["backState"] = 4
        del context.user_data["isEnterSubject"]

        context.user_data["homework"] = { "lesson" : message}

        classButtons = [[item] for item in context.user_data.get("subjects").get(message)]
        classButtons.append([back])
        await context.bot.send_message(chat_id = chatId, text = "Оберіть клас.", reply_markup = ReplyKeyboardMarkup(buttons, resize_keyboard = True))
    # ---------------------------------------------------------------------------------
    
    
    if "Створити оголошення для учнів" == message:
        await CreateNotifyMeny()
    
    elif "Для власного класу" == message or context.user_data.get("isEnterOwnNotify"):
        isEnterOwnNotify = context.user_data.get("isEnterOwnNotify", False)
        
        if not isEnterOwnNotify:
            await context.bot.send_message(chat_id = chatId, text = "Введіть текст оголошення.", reply_markup = ReplyKeyboardMarkup([[back]], resize_keyboard = True))
            context.user_data["backState"] = 2
        else:
            await SendNotify(teachingClass)
            del context.user_data["isEnterOwnNotify"]
            
    elif "Для учнів іншого класу" == message or context.user_data.get("isEnterClass") or context.user_data.get("isEnterNotify"):
        isEnterClass = context.user_data.get("isEnterClass", False)
        isEnterNotify = context.user_data.get("isEnterNotify", False)
        
        if not isEnterNotify and not isEnterClass:
            buttons = GetClassButtons()
            buttons.append([back])
            await context.bot.send_message(chat_id = chatId, text = "Оберіть клас.", reply_markup = ReplyKeyboardMarkup(buttons, resize_keyboard = True))
            context.user_data["backState"] = 2
            context.user_data["isEnterClass"] = True
            
        elif isEnterClass:
            await context.bot.send_message(chat_id = chatId, text = "Введіть текст оголошення.")
            context.user_data["whichClass"] = int(message)
            del context.user_data["isEnterClass"]
            context.user_data["isEnterNotify"] = True
        else:
            await SendNotify(context.user_data.get("whichClass"), message)
            del context.user_data["isEnterNotify"]
            del context.user_data["whichClass"]
    
    elif "Подивитися сьогоднішній розклад" == message:
        context.user_data["backState"] = 1
        await context.bot.send_message(chat_id = chatId, text = "Ось ваш розклад на сьогоднішній день", reply_markup = ReplyKeyboardMarkup([[back]], resize_keyboard = True))
        await context.bot.send_message(chat_id = chatId, text = TimetableForTeacher(context.user_data.get("user").get("lastName"),
                                                                                    context.user_data.get("user").get("firstName"),
                                                                                    context.user_data.get("user").get("fatherName")).GetTimetable()[1].AsString())

    elif "Створити домашнє завдання" == message or context.user_data.get("isEnterSubject") or context.user_data.get("isHomeworkClass") or context.user_data.get("isEnterHomework"):
        isEnterSubject  = context.user_data.get("isEnterSubject")
        isHomeworkClass = context.user_data.get("isHomeworkClass")
        isEnterHomework = context.user_data.get("isEnterHomework")
        
        if not isEnterSubject and not isHomeworkClass and isEnterHomework:
            await ChooseSubject()
        
        elif isEnterSubject:
            await ChooseClass()
        
        elif isHomeworkClass:
            context.user_data["backState"] = 5
            del context.user_data["isHomeworkClass"]
            
            context.user_data["homework"]["class"] = int(message)
            await context.bot.send_message(chat_id = chatId, text = "Введіть домашнє завдання.", reply_markup = ReplyKeyboardMarkup([[back]], resize_keyboard = True))
        
        elif isEnterHomework:
            del context.user_data["isEnterHomework"]
            
            import pytz
            import datetime
            
            homework = {
                "_id" : context.user_data.get("homework"),
                "task": message,
                "creator": "{} {} {}".format(context.user_data.get("user").get("lastName").upper(), context.user_data.get("user").get("firstName"), context.user_data.get("user").get("fatherName")),
                "when"   : datetime.datetime.now(pytz.timezone('Europe/Kiev')).strftime("%H:%M %d-%m-%Y")
            }

            mongo.homeworks.update_one({"_id" : context.user_data.get("homework")}, homework, upsert=True)
            await context.bot.send_message(chat_id = chatId, text = "Домашнє завдання додано.")
            del context.user_data["homework"]
    
    
    elif "Переглянути список учнів" == message:
        await CheckStudentsListMenu()
        
    elif "Список власного класу" == message:
        context.user_data["backState"] = 3
        await ClassList(teachingClass, "Список вашого класу:")

    elif "Список учнів іншого класу" == message or context.user_data.get("isSelectClass"):        
        context.user_data["backState"] = 3
        isSelectClass = context.user_data.get("isSelectClass")
        
        if not isSelectClass:
            buttons = GetClassButtons()
            buttons.append([back])
            
            await context.bot.send_message(chat_id = chatId, text = "Оберіть клас.", reply_markup = ReplyKeyboardMarkup(buttons, resize_keyboard = True))
            context.user_data["isSelectClass"] = True
        
        else:
            del context.user_data["isSelectClass"]
            await ClassList(message, "Список учнів " + message + "-го класу:")
            
    elif "Вихід" == message:
        mongo.users.update_one({"chatID" : chatId}, {"$set" : {"chatID" : None}})
        del context.user_data["isTecherMenu1"]
        await start(update, context)
    
    elif "Назад" == message:
        if backState == 1:
            notification   = KeyboardButton("Створити оголошення для учнів")
            checkTimetable = KeyboardButton("Подивитися сьогоднішній розклад")
            createHomeWork = KeyboardButton("Створити домашнє завдання")
            checkClassList = KeyboardButton("Переглянути список учнів")
            exit           = KeyboardButton("Вихід")
            replyMarkup    = ReplyKeyboardMarkup([[notification], [checkTimetable], [checkClassList], [createHomeWork], [exit]], resize_keyboard = True)

            await context.bot.send_message(chat_id = update.effective_chat.id, text = "Оберіть дію.", reply_markup = replyMarkup)

        elif backState == 2:  # <- Select type of notify.
            await CreateNotifyMeny()
            
        elif backState == 3:  # <- Select type of students' list.
            await CheckStudentsListMenu()
        
        elif backState == 4:  # Now we need to chose the subject
            await ChooseSubject()
        
        elif backState == 5:  # Now we need to chose the class.
            await ChooseClass()


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
    
    result = mongo.users.find_one({ "logIn.login": login })
    if result:
        return True
    return False



def ChatIdIExistInDB(chatId):
    if not chatId:
        return None
    
    return mongo.users.find_one({"chatID" : chatId})

def CheckPasssword(password) :
    if len(password) < 8:
        return False
    if not any(char.isdigit() for char in password):
        return False
    if not any(char.isupper() for char in password):
        return False
    return True


def IsValidEmail(email) -> bool:
    if not email:
        return False
    
    import re
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return re.match(pattern, email) != None


def EmailExistInDB(email) -> bool:
    if not email:
        return False
    
    return mongo.users.find_one({"email" : email}) != None


async def SentToAllWho(filter, message : str , context : CallbackContext):
    users = mongo.users.find(filter)
    for user in users:
        if user.get("chatID"):
            await context.bot.send_message(chat_id = user.get("chatID"), text = message, parse_mode = "HTML")
    















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