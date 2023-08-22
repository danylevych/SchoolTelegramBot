import json
import pytz
import datetime
import asyncio
import requests
import scripts.tools.mongo as mongo
import scripts.tools.pathes as pathes

from scripts.classes.emailSender import Email
from scripts.tools.phrases import PhrasesGenerator
from scripts.classes.followLesson import FollowLesson
from scripts.classes.teacherSubjects import TeacherSubjects
from scripts.classes.timetable import TimetableForTeacher, TimetableForStudent

from telegram.ext import CallbackContext, ContextTypes
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove



async def Start(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
            
            if context.user_data.get("user").get("classTeacher") != 0:  # Teacher teaches any class.
                await TeacherLeaderMenu(update, context)
            
            else:  # Teacher doesn't teach any class.
                await TeacherMenu(update, context)
            
        else:
            await StartUserMenu(update, context, user)

    else:
        await update.message.reply_text(f"Привіт, {update.effective_user.full_name}.")
        await EntryMenu(update, context)


async def StartUserMenu(update: Update, context: ContextTypes.DEFAULT_TYPE, user):
    context.user_data["user"]["_id"] = user.get("_id")
    
    studentInfo = {
        "lastName": user.get("lastName"),
        "firstName": user.get("firstName"),
        "fatherName": user.get("fatherName")
    }

    students = mongo.students.find_one({})

    for (classNum, studentsList) in students.items():
        if classNum != "_id" and studentsList is not None and studentInfo in studentsList:
            context.user_data["user"]["class"] = int(classNum)
            break
    await StudentMenu(update, context)


async def EntryMenu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    signUp = KeyboardButton("Реєстрація")
    logIn  = KeyboardButton("Вхід")
    reply_markup = ReplyKeyboardMarkup([[signUp, logIn]], resize_keyboard=True)
    
    context.user_data["isEntryMenu"] = True

    # Clearing the previous values.
    if context.user_data.get("logInState"):
        del context.user_data["logInState"]

    if context.user_data.get("signState"):
        del context.user_data["signState"]

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


async def TeacherLeaderMenu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["isTecherLeaderMenu"] = True
    
    notification   = KeyboardButton("Створити оголошення для учнів")
    checkTimetable = KeyboardButton("Подивитися сьогоднішній розклад")
    createHomeWork = KeyboardButton("Створити домашнє завдання")
    checkClassList = KeyboardButton("Переглянути список учнів")
    exit           = KeyboardButton("Вихід")
    replyMarkup    = ReplyKeyboardMarkup([[notification], [checkTimetable], [checkClassList], [createHomeWork], [exit]], resize_keyboard = True)
    
    await context.bot.send_message(chat_id = update.effective_chat.id, text = "Ви ввійшли як <b>ВЧИТЕЛЬ</b>", parse_mode = "HTML", reply_markup = replyMarkup)


async def TeacherMenu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["isTecherMenu"] = True
    
    notification   = KeyboardButton("Створити оголошення для учнів")
    checkTimetable = KeyboardButton("Подивитися сьогоднішній розклад")
    createHomeWork = KeyboardButton("Створити домашнє завдання")
    checkClassList = KeyboardButton("Переглянути список учнів")
    exit           = KeyboardButton("Вихід")
    replyMarkup    = ReplyKeyboardMarkup([[notification], [checkTimetable], [checkClassList], [createHomeWork], [exit]], resize_keyboard = True)
    
    await context.bot.send_message(chat_id = update.effective_chat.id, text = "Ви ввійшли як <b>ВЧИТЕЛЬ</b>", parse_mode = "HTML", reply_markup = replyMarkup)


async def StudentMenu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.job_queue.run_repeating(SendLessonNotification, interval = 2, first = 0, user_id = context.user_data.get("user").get("id"))
    context.user_data["isStudentMenu"] = True
    
    buttons = [
        [KeyboardButton("Розклад")],
        [KeyboardButton("Список класу")],
        [KeyboardButton("Домашнє завдання на завтра")],
        [KeyboardButton("Нотатки")],
        [KeyboardButton("Контакти")],
        [KeyboardButton("Вихід")]]
    replyMarkup    = ReplyKeyboardMarkup(buttons, resize_keyboard = True)
    
    await context.bot.send_message(chat_id = update.effective_chat.id, text = "Ви ввійшли як <b>УЧЕНЬ</b>", parse_mode = "HTML", reply_markup = replyMarkup)


async def MessagesHandlerAdminTeacher(update: Update, context: CallbackContext):
    message : str = update.message.text
    
    if message == "АДМІНІСТРАТОР":
        context.user_data["user"]["type"] = "admin"
        await AdminMenu(update, context)
        
    else:
        user = context.user_data.get("user")
        
        teacher = mongo.teachers.find_one({ "firstName"  : user.get("firstName"), 
                                            "lastName"   : user.get("lastName"),
                                            "fatherName" : user.get("fatherName")})
            
        context.user_data["user"]["classTeacher"] = int(teacher.get("classTeacher"))
            
        if context.user_data.get("user").get("classTeacher") != 0:  # Teacher teaches any class.
            await TeacherLeaderMenu(update, context)
            
        else:  # Teacher doesn't teach any class.
            await TeacherMenu(update, context)


async def MessagesHandler(update: Update, context: CallbackContext):
    if context.user_data.get("isEntryMenu"):
        await EntryMenuHandler(update, context)
        
    elif context.user_data.get("isAdminMenu"):
        await AdminMenuHandler(update, context)
    
    elif context.user_data.get("isTecherLeaderMenu"):
        await TeacherLeaderMenuHandler(update, context)

    elif context.user_data.get("isTecherMenu"):
        await TeacherMenuHandler(update, context)
    
    elif context.user_data.get("isStudentMenu"):
        await StudentMenuHandler(update, context)


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
    
    LOGIN_ENTER = 1
    LOGIN_WRONG = -1
    PASSWORD_ENTER = 2
    PASSWORD_WRONG = -2
    FORGOT_PASSWORD = 3
    FORGOT_PASWORD_SHURE = 4
    FORGOT_PASSWORD_ENTER_CODE = 5
    FORGOT_PASSWORD_ENTER_NEW = 6
    
    REGISTRATION_NAME_ENTER = 1
    REGISTRATION_NAME_WRONG = -1
    REGISTRATION_CLASS_ENTER = 2
    REGISTRATION_CLASS_WRONG = -2
    REGISTRATION_EMAIL_ENTER = 3
    REGISTRATION_EMAIL_WRONG = -3
    REGISTRATION_CODE_ENTER = 4
    REGISTRATION_CODE_WRONG = -4
    REGISTRATION_LOGIN_ENTER = 5
    REGISTRATION_LOGIN_WRONG = -5
    REGISTRATION_PASSWORD_ENTER = 6
    REGISTRATION_PASSWORD_WRONG = -6
    

    
    async def EnterLoginHandler():
        if LoginExist(message):
            await context.bot.send_message(chat_id = chatId, text = "Вітаю. Логін успішно прийнято.")
            
            context.user_data["logIn"] = dict()
            context.user_data["logIn"]["login"] = message
            context.user_data["logInState"] = PASSWORD_ENTER  # User is going to send the password.
            
            await context.bot.send_message(chat_id = chatId, text = "Введіть ваш пароль.", reply_markup = ReplyKeyboardMarkup([["Відновити пароль"]], resize_keyboard = True))

        else:
            await context.bot.send_message(chat_id = chatId, text = "Зареєстрованого користувача із таким логіном немає!.")
            await asyncio.sleep(1)
            await context.bot.send_message(chat_id = chatId, text = "Можливо ви ввели щось неправильно. Спробувати ще раз?",
                                            reply_markup = replyMarkup)
            
            context.user_data["logInState"] = LOGIN_WRONG

    async def EnterPasswordHandler():
        context.user_data["logIn"]["password"] = message
        
        await asyncio.sleep(1)
        await context.bot.delete_message(chat_id = chatId, message_id = messageId)
        await context.bot.send_message(chat_id = chatId, text = "Здійснюється перевірка введених даних. Зачекайте.")
        
        userLoginData = context.user_data.get("logIn")
        
        if user := UserExistInDB(userLoginData):
            if not user.get("chatID"):  # User try to entry for other computer. 
                if context.user_data.get("isEntryMenu"):
                    del context.user_data["isEntryMenu"]

                context.user_data["user"]["id"] = chatId
                context.user_data["user"]["firstName"] = user.get("firstName")
                context.user_data["user"]["lastName"] = user.get("lastName")
                context.user_data["user"]["fatherName"] = user.get("fatherName")

                mongo.users.update_one({ "logIn": userLoginData }, {"$set" : {"chatID" : chatId}})

                userType = user.get("userType")

                if userType.get("developer") or userType.get("admin"):
                    # So, we might have a situation, when the admin might have subjects, that he is teaching.
                    # To diside this issue we create the menu, when the admin who is a teacher at the time 
                    # can choose, what type of entrance he feel like,
                    if userType.get("admin") and userType.get("teacher"):  # We get the situation, which we discriped top.
                        buttons = [["АДМІНІСТРАТОР"], ["ВЧИТЕЛЬ"]]
                        replyMarkup = ReplyKeyboardMarkup(buttons, resize_keyboard = True)
                        await context.bot.send_message(chat_id = chatId, text = "Виберіть тип користувача під яким намагаєтеся здійснити вхід.", reply_markup = replyMarkup)
                        return
                    
                    context.user_data["user"]["type"] = "developer" if userType.get("developer") else "admin"

                    await asyncio.sleep(1)
                    await context.bot.send_message(chat_id = chatId, text = "Вхід успішний!")

                    await AdminMenu(update, context)

                elif userType.get("teacher"):
                    teacher = mongo.teachers.find_one({ "firstName"  : user.get("firstName"), 
                                                        "lastName"   : user.get("lastName"),
                                                        "fatherName" : user.get("fatherName")})
                    
                    context.user_data["user"]["classTeacher"] = int(teacher.get("classTeacher"))

                    if context.user_data.get("user").get("classTeacher") != 0:
                        await TeacherLeaderMenu(update, context)
            
                    else:
                        await TeacherMenu(update, context)
                        
                else:
                    await StartUserMenu(update, context, user)
            else:
                await context.bot.send_message(chat_id = chatId, text = "Подвійний вхід заборонений!")
                await Start(update, context)

            
        else:
            await context.bot.send_message(chat_id = chatId, text = "Пароль неправильний!")
            await asyncio.sleep(1)
            await context.bot.send_message(chat_id = chatId, text = "Спробувати ще раз?", reply_markup = replyMarkup)
            context.user_data["logInState"] = PASSWORD_WRONG

    async def ForfotPasswordHandler():
        context.user_data["logInState"] = FORGOT_PASSWORD_ENTER_CODE
        await context.bot.send_message(chat_id = chatId, text = "Зараз на вашу пошту надійде лист в якому буде код, який ви повинні ввести сюди.")
        import random
        
        context.user_data["code"] = (code := random.randint(1000, 9999))
        user = mongo.users.find_one({"logIn.login" : context.user_data.get("logIn").get("login")})
        
        Email().Send(user.get("email"), "ВІДНОВЛЕННЯ ПАРОЛЮ", f"Ви намагаєтеся відновити пароль в чат-боті Вівнянського ЗНЗ І-ІІ ст. - ДНЗ.\n" + 
                        "Код: " + str(code) + "\nНікому стононньому не повідомляйте його.\n" +
                        "Бажаємо гарного дня")

    async def ForfotPasswordEnterCodeHandler():
        if rightCode := context.user_data.get("code"):
            if str(rightCode) in message:
                await context.bot.send_message(chat_id = chatId, text = "Ви успішно підтвердили свою пошту.\nДалі введіть новий пароль", parse_mode = "HTML") 
                
                del context.user_data["code"]
                context.user_data["logInState"] = FORGOT_PASSWORD_ENTER_NEW  # User is going to send his new password.
                
            else:
                await context.bot.send_message(chat_id = chatId, text = "На жаль, ви ввели неправильний код.") 
        else:
            print("Code dosen't exist")

    async def ForgotPasswordEnterNewHandler():
        await asyncio.sleep(1)
        await context.bot.delete_message(chat_id = chatId, message_id = messageId)  # Delete the password, that user provided.
        
        if CheckPasssword(message):
            if context.user_data.get("isEntryMenu"):
                del context.user_data["isEntryMenu"]

            mongo.users.update_one({"logIn.login": context.user_data.get("logIn").get("login")}, {"$set": {"chatID": chatId, "logIn.password": message}})
            await context.bot.send_message(chat_id = chatId, text = "Ви успішно відновили пароль.")
            
            await EnterPasswordHandler()
            
        else:
            await context.bot.send_message(chat_id = chatId, text = "Ви ввели пароль, який не відповідає вимогам. Будь ласка повторіть введення.") 



    async def RegistrationNameEnterHandler():
        splitedMsg = message.split(' ')
        
        try:
            studentData = {
                "lastName"  : splitedMsg[0],
                "firstName" : splitedMsg[1],
                "fatherName": splitedMsg[2],
            }
            
            if mongo.users.find_one(studentData):
                context.user_data["signState"] = REGISTRATION_NAME_WRONG  # User exists.
                
                await context.bot.send_message(chat_id = chatId, text = "Вибачте але такий користувач вже зареєстрований. Можливо ви помилилися, спробувати знову?",
                                                reply_markup = replyMarkup)
            else:
                context.user_data["signInfo"] = studentData
                await context.bot.send_message(chat_id = chatId, text = "Наступний крок - введіть клас в якому ви навчаєтеся")
                context.user_data["signState"] = REGISTRATION_CLASS_ENTER  # User is going to send his class.
            
        except:
            print("he wrote less args")
            await context.bot.send_message(chat_id = chatId, 
                    text = "Виввели неправильну кількість даних.\nПереконайтеся що попереднє повідомлення було коректне.\n" + 
                    "Наприклад:\n\tПетренко Петро <- НЕПРАВИЛЬНО\n\tПетренко Петро Петрович <- ПРАВИЛЬНО")

    async def RegistrationClassEnterHandler():
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
                context.user_data["signState"] = REGISTRATION_EMAIL_ENTER  # User is going to send his e-mail.
                
            else:
                context.user_data["signState"] = REGISTRATION_CLASS_WRONG  # User does not exist.
                await context.bot.send_message(chat_id = chatId, text = "Вибачте такого учня в цьому класі немає.\n" + 
                                                "Можливо ви ввели неправильні дані. Спробувати ще раз?",
                                                reply_markup = replyMarkup)
            
        except:
            print("he wrote incorect args")
            await context.bot.send_message(chat_id = chatId, 
                    text = "Виввели неправильні дані.\nПереконайтеся що попереднє повідомлення було коректне.\n" + 
                    "Наприклад:\n\t9 клас ← НЕПРАВИЛЬНО\n\t9 ← ПРАВИЛЬНО")
    
    async def RegistrationEmailEnterHandler():
        if (not IsValidEmail(message) and (text := "Неправильний формат пошти.")) or (EmailExistInDB(message) and (text := "На цю пошту вже є зареєстрований користувач.")):
            context.user_data["signState"] = REGISTRATION_EMAIL_WRONG  # Something wrong with email.
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

                context.user_data["signState"] = REGISTRATION_CODE_ENTER  # User is going to send the code.
            except:
                print("something wrong in sending letter")
                await context.bot.send_message(chat_id = chatId, text = "Вибачте але сталася якась помилка, перевірте правильність вказання пошти")   

    async def RegistrationCodeEnterHandler():   
        if rightCode := context.user_data.get("signInfo").get("code"):
            if rightCode in message:
                await context.bot.send_message(chat_id = chatId, text = "Ви успішно підтвердили свою пошту.\nДалі введіть логін, який будете" +
                                            " використовувати під час входу.\n<b>Радимо використати свою пошту.</b>", parse_mode = "HTML") 
                
                del context.user_data["signInfo"]["code"]
                context.user_data["signState"] = REGISTRATION_LOGIN_ENTER  # User is going to send his login.
                
            else:
                await context.bot.send_message(chat_id = chatId, text = "На жаль, ви ввели неправильний код.") 
        else:
            print("Code dosen't exist")
    
    async def RegistrationLoginEnterHandler():
        if LoginExist(message):
            await context.bot.send_message(chat_id = chatId, text = "Введений логін уже занятий, спробуйте будь ласка інший!")
        else:
            context.user_data["signInfo"]["login"] = message
            await context.bot.send_message(chat_id = chatId, text = "Логін успішно додано.")
            
            context.user_data["signState"] = REGISTRATION_PASSWORD_ENTER  # User is going to send his password.
            
            await context.bot.send_message(chat_id = chatId,
                text = "Тепер потрібно ввести пароль, який будете використовувати при вході.\n" + 
                "Пароль повинен містити:\n" +
                "\t- мінімум 8 символів.\n" +
                "\t- хоча б одну цифру та велику букву.\n" +  
                "<b>(За 1 секунд повідомлення з паролем видалиться, з міркувань конфіденційності)</b>",
                parse_mode = "HTML")
    
    async def RegistrationPasswordEnterHandler():
        await asyncio.sleep(1)
        await context.bot.delete_message(chat_id = chatId, message_id = messageId)  # Delete the password, that user provided.
        
        if CheckPasssword(message):
            context.user_data["signInfo"]["password"] = message

            
            await context.bot.send_message(chat_id = chatId, text = "Пароль успішно додано.")

            user = {
                "chatID"    : chatId,
                "lastName"  : context.user_data["signInfo"]["lastName"],
                "firstName" : context.user_data["signInfo"]["firstName"],
                "fatherName": context.user_data["signInfo"]["fatherName"],
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
            context.user_data["user"]["class"] = int(context.user_data.get("signInfo").get("class"))
            context.user_data["user"]["_id"] = mongo.users.find_one(user).get("_id")
            
            del context.user_data["signInfo"]
            del context.user_data["signState"]
            del context.user_data["isEntryMenu"]
            
            await StudentMenu(update, context)
            
        else:
            await context.bot.send_message(chat_id = chatId, text = "Ви ввели пароль, який не відповідає вимогам. Будь ласка повторіть введення.")      
    
    
    if "Відновити пароль" == message:
        context.user_data["logInState"] = logInState = FORGOT_PASSWORD
    
    if "Вхід" == message:
        await context.bot.send_message(chat_id = chatId, text = "Введіть ваш логін", reply_markup = ReplyKeyboardRemove())
        context.user_data["logInState"] = LOGIN_ENTER  # User is going to send the login.     

    elif logInState == LOGIN_ENTER:
        await EnterLoginHandler()
    
    elif logInState == PASSWORD_ENTER:
        await EnterPasswordHandler()
    
    elif logInState == LOGIN_WRONG:
        await YesNoEntryHandler(update, context, "logInState", LOGIN_ENTER, "Надішліть свій логін.", "Тоді вертаємося до початкового меню.")
    
    elif logInState == PASSWORD_WRONG:
        
        await YesNoEntryHandler(update, context, "logInState", PASSWORD_ENTER, "Надішліть свій пароль.", "Тоді вертаємося до початкового меню.")
        print("password wrong")

    elif logInState == FORGOT_PASSWORD:
        context.user_data["logInState"] = FORGOT_PASWORD_SHURE
        await context.bot.send_message(chat_id = chatId, text = "Ви дійсно бажаєте відновити пароль?", reply_markup = replyMarkup)
        

    elif logInState == FORGOT_PASWORD_SHURE:
        if "Так" == message:
            await context.bot.send_message(chat_id = chatId, text = "Добре.", reply_markup = ReplyKeyboardRemove())
            context.user_data["logInState"] = FORGOT_PASSWORD_ENTER_CODE
            await ForfotPasswordHandler()

        elif "Ні" == message:
            await context.bot.send_message(chat_id = chatId, text = "Тоді повертаємося до головного меню.", reply_markup = ReplyKeyboardRemove())
            await EntryMenu(update, context)  # TODO: To first menu.

        else:
            await context.bot.send_message(chat_id = chatId, text = "Введено некоректне повідомлення")
    
    elif logInState == FORGOT_PASSWORD_ENTER_CODE:
        await ForfotPasswordEnterCodeHandler()
    
    elif logInState == FORGOT_PASSWORD_ENTER_NEW:
        await ForgotPasswordEnterNewHandler()


    elif "Реєстрація" == message:
        await context.bot.send_message(chat_id = chatId, text = "Для початку введіть своє Прізвище Ім'я По-батькові", reply_markup = ReplyKeyboardRemove())
        
        context.user_data["signState"] = REGISTRATION_NAME_ENTER  # User is going to send his first last & father names.
    
    elif signState == REGISTRATION_NAME_ENTER:
        await RegistrationNameEnterHandler()
    
    elif signState == REGISTRATION_CLASS_ENTER:
        await RegistrationClassEnterHandler()
    
    elif signState == REGISTRATION_EMAIL_ENTER:
        await RegistrationEmailEnterHandler()   
    
    elif signState == REGISTRATION_CODE_ENTER:
        await RegistrationCodeEnterHandler()     
    
    elif signState == REGISTRATION_LOGIN_ENTER:
        await RegistrationLoginEnterHandler()
    
    elif signState == REGISTRATION_PASSWORD_ENTER:
        await RegistrationPasswordEnterHandler()

    elif signState == REGISTRATION_NAME_WRONG:
        await YesNoEntryHandler(update, context, "signState", 1, "Надішліть своє Прізвище Ім'я По-батькові.", "Тоді вертаємося до початкового меню")
    
    elif signState == REGISTRATION_CLASS_WRONG:
        await YesNoEntryHandler(update, context, "signState", 2, "Надішліть клас в якому навчаєтесь.", "Тоді вертаємося до початкового меню")

    elif signState == REGISTRATION_EMAIL_WRONG:
        await YesNoEntryHandler(update, context, "signState", 3, "Надішліть нову пошту.", "Тоді вертаємося до початкового меню")


async def AdminMenuHandler(update : Update, context : CallbackContext):
    message         : str = update.message.text
    chatId          : int = update.effective_chat.id
    notifState      : int = context.user_data.get("notifState", 0)
    backState       : int = context.user_data.get("backState", 0)
    back                  = KeyboardButton("Назад")
    
    
    NOTIFI_ENTER_TO_ALL = 1
    NOTIFI_ENTER_TO_TEACHER = 2
    NOTIFI_ENTER_TO_ALL_STUDENTS = 3
    NOTIFI_ENTER_TO_SOME_CLASS = 4
    
    BACK_TO_ADMIN_MENU = 1
    BACK_TO_CREATING_MENU = 2
    BACK_TO_NOTIFI_FOR_STUDENTS = 3
    
    
    async def CreateNitify():
        context.user_data["backState"] = BACK_TO_ADMIN_MENU
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
        context.user_data["backState"] = BACK_TO_CREATING_MENU
        
    async def SetMenu(backSate, notifyState):
        await context.bot.send_message(chat_id = chatId, text = "Введіть та відправте текст оголошення.", reply_markup = ReplyKeyboardMarkup([[back]], resize_keyboard = True))
        context.user_data["backState"]  = backSate
        context.user_data["notifState"] = notifyState
    
    async def SendNotification(filter, message):
        message = "<b>ОГОЛОШЕННЯ ВІД " + ("РОЗРОБНИКІВ" if context.user_data.get("user").get("type") == "developer" else "АДМІНІСТРАЦІЇ ШКОЛИ") + "</b>\n" + message
        await SentToAllWho(filter, message, context)
        await context.bot.send_message(chat_id = chatId, text = "Оголошення надіслане.")
    
    
    if "Створити оголошення" == message:  # TODO: try delete the key in this line.
        await CreateNitify()
    
    elif "Вихід" == message:
        mongo.users.update_one({"chatID" : chatId}, {"$set" : {"chatID" : None}})
        del context.user_data["isAdminMenu"]
        await Start(update, context)
        
    elif "Для усіх" == message:
        await SetMenu(backSate = BACK_TO_CREATING_MENU, notifyState = NOTIFI_ENTER_TO_ALL)
        
    elif "Для учителів" == message:
        await SetMenu(backSate = BACK_TO_CREATING_MENU, notifyState = NOTIFI_ENTER_TO_TEACHER)
    
    elif "Для учнів" == message:
        await ForStudents()
    
    elif "Для усіх учнів" == message:
        await SetMenu(backSate = BACK_TO_NOTIFI_FOR_STUDENTS, notifyState = NOTIFI_ENTER_TO_ALL_STUDENTS)
        
    elif "Для певного класу" == message:
        await context.bot.send_message(chat_id = chatId, text = "Введіть номер класу, для якого хочете створити оголошення.",
                                        reply_markup = ReplyKeyboardMarkup([[back]], resize_keyboard = True))
        context.user_data["backState"]  = BACK_TO_NOTIFI_FOR_STUDENTS
        context.user_data["notifState"] = NOTIFI_ENTER_TO_SOME_CLASS
        
    elif "Назад" == message:
        if backState == BACK_TO_ADMIN_MENU:    # Move to main admin menu.
            notification = KeyboardButton("Створити оголошення")
            exit         = KeyboardButton("Вихід")
            replyMarkup  = ReplyKeyboardMarkup([[notification], [exit]], resize_keyboard = True)
            await context.bot.send_message(chat_id = update.effective_chat.id, text = "Оберіть дію.", reply_markup = replyMarkup)
            
        elif backState == BACK_TO_CREATING_MENU:  # Move to creating menu.
            await CreateNitify()
            
        elif backState == BACK_TO_NOTIFI_FOR_STUDENTS:  # Move notify for student
            await ForStudents()
    
    elif notifState in (NOTIFI_ENTER_TO_ALL, NOTIFI_ENTER_TO_TEACHER, NOTIFI_ENTER_TO_ALL_STUDENTS, NOTIFI_ENTER_TO_SOME_CLASS):
        if notifState == NOTIFI_ENTER_TO_ALL:
            filter = {
                "userType.developer": False,
                "userType.admin"    : False
            }
            await SendNotification(filter, message)

        elif notifState == NOTIFI_ENTER_TO_TEACHER: 
            filter = {
                "userType.developer": False,
                "userType.admin"    : False,
                "userType.student"  : False,
            }
            await SendNotification(filter, message)
            
        elif notifState == NOTIFI_ENTER_TO_ALL_STUDENTS:
            filter = {
                "userType.developer": False,
                "userType.admin"    : False,
                "userType.teacher"  : False,
            }
            await SendNotification(filter, message)

        elif notifState == NOTIFI_ENTER_TO_SOME_CLASS:
            if context.user_data.get("isSendingNotify"):
                message = "<b>ОГОЛОШЕННЯ ВІД " + ("РОЗРОБНИКІВ" if context.user_data.get("user").get("type") == "developer" else "АДМІНІСТРАЦІЇ ШКОЛИ") + "</b>\n" + message
                students = mongo.students.find_one({}, {str(context.user_data.get("whichClass")): 1}).get(str(context.user_data.get("whichClass")))

                filter = { "$or" : students }
                await SendNotification(filter, message)
                
                del context.user_data["whichClass"]
                del context.user_data["isSendingNotify"]
                
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


async def TeacherLeaderMenuHandler(update : Update, context : CallbackContext):
    message       : str = update.message.text
    chatId        : int = update.effective_chat.id
    backState     : int = context.user_data.get("backState", 0)
    teachingClass : int = context.user_data.get("user").get("classTeacher")
    back                = KeyboardButton("Назад")    
    
    
    BACK_TO_MAIN_MENU = 1
    BACK_TO_CREATING_NOTIFY_MENU = 2
    BACK_TO_CLASS_ENTER_NOTIFY_MENU = 3
    BACK_TO_STUDENTS_LIST_MENU = 4
    BACK_TO_CLASS_ENTER_STUDENTS_MENU = 5
    BACK_TO_CLASS_ENTER_SUBJECTS_MENU = 6
    BACK_TO_CLASS_ENTER_HOMEWORK_MENU = 7
    
    ENTER_CLASS_NOTIFIED, ENTER_NOTIFY, SEND_NOTIFY = range(1, 4)
    ENTER_SUBJECT, ENTER_HOMEWORK_CLASS, ENTER_HOMEWORK, SAVE_HOMEWORK = range(1, 5)
    
    def GetClassButtons():
        students = mongo.students.find()
        
        buttons : list = list()
        twoButton : list = list()
        for table in students:
            for (classItem, studentsTable) in table.items():
                if studentsTable and str(classItem) != "_id":
                    twoButton.append(KeyboardButton(str(classItem)))
                    if len(twoButton) == 2:
                        buttons.append(twoButton)
                        twoButton = list()
        return buttons     
    
    
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
    
    
    async def SendNotify(classNum, message):
        message = "<b>Оголошення від {} {} {}".format(context.user_data.get("user").get("lastName").upper(), 
                                                            context.user_data.get("user").get("firstName"),
                                                            context.user_data.get("user").get("fatherName")) + message + ".</b>\n"
        students = mongo.students.find_one({}, {str(classNum) : 1}).get(str(classNum))
            
        filter = { "$or" : students }
        
        await SentToAllWho(filter, message, context)
        await context.bot.send_message(chat_id = chatId, text = "Оголошення надіслане.")
    
    
    async def MainMenuHandler():
        notification   = KeyboardButton("Створити оголошення для учнів")
        checkTimetable = KeyboardButton("Подивитися сьогоднішній розклад")
        createHomeWork = KeyboardButton("Створити домашнє завдання")
        checkClassList = KeyboardButton("Переглянути список учнів")
        exit           = KeyboardButton("Вихід")
        replyMarkup    = ReplyKeyboardMarkup([[notification], [checkTimetable], [checkClassList], [createHomeWork], [exit]], resize_keyboard = True)

        await context.bot.send_message(chat_id = update.effective_chat.id, text = "Оберіть дію.", reply_markup = replyMarkup)
    
    
    async def CreatingNotifyHandler():
        context.user_data["backState"] = BACK_TO_MAIN_MENU
        
        forOwnClass   = KeyboardButton("Для власного класу")
        forOtherClass = KeyboardButton("Для учнів іншого класу")

        replyMarkup    = ReplyKeyboardMarkup([[forOwnClass, forOtherClass], [back]], resize_keyboard = True)
        await context.bot.send_message(chat_id = chatId, text = "Оберіть дію.", reply_markup = replyMarkup)
    
    
    async def NotifyOwnClassHandler():
        if not context.user_data.get("isNotifyOwnClass"):
            context.user_data["backState"] = BACK_TO_CREATING_NOTIFY_MENU
            context.user_data["isNotifyOwnClass"] = True
            await context.bot.send_message(chat_id = chatId, text = "Введіть текст оголошення.", reply_markup = ReplyKeyboardMarkup([[back]], resize_keyboard = True))
        else:
            await SendNotify(teachingClass, message)
            del context.user_data["isNotifyOwnClass"]
    
    
    async def NotifyClassHandler():
        notifyState = context.user_data.get("notifyState", ENTER_CLASS_NOTIFIED)
        
        if notifyState == ENTER_CLASS_NOTIFIED:
            context.user_data["backState"] = BACK_TO_CREATING_NOTIFY_MENU
            context.user_data["notifyState"] = ENTER_NOTIFY
            
            buttonsNotify = GetClassButtons()
            buttonsNotify.append([back])
            await context.bot.send_message(chat_id = chatId, text = "Оберіть клас.", reply_markup = ReplyKeyboardMarkup(buttonsNotify, resize_keyboard = True))
            
        elif notifyState == ENTER_NOTIFY:
            context.user_data["backState"] = BACK_TO_CLASS_ENTER_NOTIFY_MENU
            context.user_data["notifyState"] = SEND_NOTIFY
            
            try:
                context.user_data["whichClass"] = int(message)
                await context.bot.send_message(chat_id = chatId, text = "Введіть текст оголошення.", reply_markup = ReplyKeyboardMarkup([[back]], resize_keyboard = True))
            except:
                await context.bot.send_message(chat_id = chatId, text = "Ой, щось пішло не так. Можливо ви не обрали клас.", reply_markup = ReplyKeyboardMarkup([[back]], resize_keyboard = True))
        
        elif notifyState == SEND_NOTIFY:
            del context.user_data["notifyState"]
            await SendNotify(context.user_data.get("whichClass"), message)


    async def HomeworkHandler():
        homeworkState = context.user_data.get("homeworkState", ENTER_SUBJECT)
        
        if homeworkState == ENTER_SUBJECT:
            context.user_data["backState"] = BACK_TO_MAIN_MENU
            context.user_data["homeworkState"] = ENTER_HOMEWORK_CLASS
            
            if context.user_data.get("lesson"):
                del context.user_data["lesson"]
            
            subjectsButtons = [[item] for item in context.user_data.get("subjects").keys()]
            subjectsButtons.append([back])
            await context.bot.send_message(chat_id = chatId, text = "Оберіть предмет.", reply_markup = ReplyKeyboardMarkup(subjectsButtons, resize_keyboard = True))
        
        elif homeworkState == ENTER_HOMEWORK_CLASS:
            context.user_data["backState"] = BACK_TO_CLASS_ENTER_SUBJECTS_MENU
            context.user_data["homeworkState"] = ENTER_HOMEWORK
            
            if not context.user_data.get("lesson"):
                context.user_data["lesson"] = message
                
            context.user_data["homework"] = {"lesson" : context.user_data.get("lesson")}
            
            classButtons = [[item] for item in context.user_data.get("subjects").get(context.user_data.get("lesson"))]  # Need to review if user send incorect values. 
            classButtons.append([back])
            await context.bot.send_message(chat_id = chatId, text = "Оберіть клас.", reply_markup = ReplyKeyboardMarkup(classButtons, resize_keyboard = True))
            
        elif homeworkState == ENTER_HOMEWORK:
            context.user_data["backState"] = BACK_TO_CLASS_ENTER_HOMEWORK_MENU
            context.user_data["homeworkState"] = SAVE_HOMEWORK
            
            try:
                context.user_data["homework"]["class"] = int(message) # <- Maybe casting error
                await context.bot.send_message(chat_id = chatId, text = "Введіть домашнє завдання.", reply_markup = ReplyKeyboardMarkup([[back]], resize_keyboard = True))
            except:
                await context.bot.send_message(chat_id = chatId, text = "Ой, щось пішло не так. Можливо ви не обрали клас.", reply_markup = ReplyKeyboardMarkup([[back]], resize_keyboard = True))
                
        elif homeworkState == SAVE_HOMEWORK:
            del context.user_data["homeworkState"]
            context.user_data["backState"] = BACK_TO_CLASS_ENTER_HOMEWORK_MENU
            
            homework = {
                "_id" : context.user_data.get("homework"),
                "task": message,
                "creator": "{} {} {}".format(context.user_data.get("user").get("lastName").upper(), context.user_data.get("user").get("firstName"), context.user_data.get("user").get("fatherName")),
                "when"   : datetime.datetime.now(pytz.timezone('Europe/Kiev')).strftime("%H:%M %d-%m-%Y")
            }

            mongo.homeworks.update_one({"_id" : context.user_data.get("homework")}, {"$set": homework}, upsert=True)
            await context.bot.send_message(chat_id = chatId, text = "Домашнє завдання додано.", reply_markup = ReplyKeyboardMarkup([[back]], resize_keyboard = True))
            del context.user_data["homework"]
    
    
    async def CheckStudentListHandler():
        context.user_data["backState"] = BACK_TO_MAIN_MENU
        
        forOwnClass   = KeyboardButton("Список власного класу")
        forOtherClass = KeyboardButton("Список учнів іншого класу")

        replyMarkup    = ReplyKeyboardMarkup([[forOwnClass], [forOtherClass], [back]], resize_keyboard = True)
        await context.bot.send_message(chat_id = chatId, text = "Оберіть дію.", reply_markup = replyMarkup)
    
    
    async def ClassListHandler():
        isSelectClass = context.user_data.get("isSelectClass")
        
        if not isSelectClass:
            context.user_data["backState"] = BACK_TO_STUDENTS_LIST_MENU
            context.user_data["isSelectClass"] = True
            
            buttons = GetClassButtons()
            buttons.append([back])
            
            await context.bot.send_message(chat_id = chatId, text = "Оберіть клас.", reply_markup = ReplyKeyboardMarkup(buttons, resize_keyboard = True))
        
        else:
            del context.user_data["isSelectClass"]
            context.user_data["backState"] = BACK_TO_CLASS_ENTER_STUDENTS_MENU
            await ClassList(message, "Список учнів " + message + "-го класу:")
    
    
    if "Назад" == message:
        if backState == BACK_TO_MAIN_MENU:
            if context.user_data.get("notifyState"):
                del context.user_data["notifyState"]
                
            if context.user_data.get("isNotifyOwnClass"):
                del context.user_data["isNotifyOwnClass"]
            
            if context.user_data.get("homeworkState"):
                del context.user_data["homeworkState"]
            
            if context.user_data.get("isSelectClass"):
                del context.user_data["isSelectClass"]
            
            await MainMenuHandler()
            
        elif backState == BACK_TO_CREATING_NOTIFY_MENU:
            if context.user_data.get("notifyState"):
                del context.user_data["notifyState"]
                
            if context.user_data.get("isNotifyOwnClass"):
                del context.user_data["isNotifyOwnClass"]
            
            if context.user_data.get("homeworkState"):
                del context.user_data["homeworkState"]
            
            if context.user_data.get("lesson"):
                del context.user_data["lesson"]
            
            await CreatingNotifyHandler()
            
        elif backState == BACK_TO_CLASS_ENTER_NOTIFY_MENU:
            if context.user_data.get("notifyState"):
                del context.user_data["notifyState"]
            await NotifyClassHandler()
            
        elif backState == BACK_TO_STUDENTS_LIST_MENU:
            if context.user_data.get("isSelectClass"):
                del context.user_data["isSelectClass"]
            await CheckStudentListHandler()
            
        elif backState == BACK_TO_CLASS_ENTER_STUDENTS_MENU:
            await ClassListHandler()
        
        elif backState == BACK_TO_CLASS_ENTER_SUBJECTS_MENU:
            context.user_data["homeworkState"] = ENTER_SUBJECT
            await HomeworkHandler()
            
        elif backState == BACK_TO_CLASS_ENTER_HOMEWORK_MENU:
            context.user_data["homeworkState"] = ENTER_HOMEWORK_CLASS
            await HomeworkHandler()
        
    
    elif "Створити оголошення для учнів" == message:
        await CreatingNotifyHandler()
    
    elif "Для власного класу" == message or context.user_data.get("isNotifyOwnClass"):
        await NotifyOwnClassHandler()
            
    elif "Для учнів іншого класу" == message or context.user_data.get("notifyState"):
        await NotifyClassHandler()
    
    elif "Подивитися сьогоднішній розклад" == message:
        context.user_data["backState"] = BACK_TO_MAIN_MENU
        await context.bot.send_message(chat_id = chatId, text = "Ось ваш розклад на сьогоднішній день", reply_markup = ReplyKeyboardMarkup([[back]], resize_keyboard = True))
        await context.bot.send_message(chat_id = chatId, text = TimetableForTeacher(context.user_data.get("user").get("lastName"),
                                                                                    context.user_data.get("user").get("firstName"),
                                                                                    context.user_data.get("user").get("fatherName")).GetTimetable()[0].AsString(), parse_mode = "HTML")

    elif "Створити домашнє завдання" == message or context.user_data.get("homeworkState"):
        context.user_data["subjects"] = TeacherSubjects(context.user_data.get("user").get("lastName"), context.user_data.get("user").get("firstName"), context.user_data.get("user").get("fatherName")).GetSubjects()
        await HomeworkHandler()
    
    elif "Переглянути список учнів" == message:
        await CheckStudentListHandler()
        
    elif "Список власного класу" == message:
        context.user_data["backState"] = BACK_TO_STUDENTS_LIST_MENU
        await ClassList(teachingClass, "Список вашого класу:")

    elif "Список учнів іншого класу" == message or context.user_data.get("isSelectClass"):        
        await ClassListHandler()
            
    elif "Вихід" == message:
        mongo.users.update_one({"chatID" : chatId}, {"$set" : {"chatID" : None}})
        del context.user_data["isTecherLeaderMenu"]
        await Start(update, context)


async def TeacherMenuHandler(update : Update, context : CallbackContext):
    message       : str = update.message.text
    chatId        : int = update.effective_chat.id
    backState     : int = context.user_data.get("backState", 0)
    back                = KeyboardButton("Назад")    
    
    
    BACK_TO_MAIN_MENU = 1
    BACK_TO_CLASS_ENTER_NOTIFY_MENU = 2
    BACK_TO_CLASS_ENTER_STUDENTS_MENU = 3
    BACK_TO_CLASS_ENTER_SUBJECTS_MENU = 4
    BACK_TO_CLASS_ENTER_HOMEWORK_MENU = 5
    
    ENTER_CLASS_NOTIFIED, ENTER_NOTIFY, SEND_NOTIFY = range(1, 4)
    ENTER_SUBJECT, ENTER_HOMEWORK_CLASS, ENTER_HOMEWORK, SAVE_HOMEWORK = range(1, 5)
    
    def GetClassButtons():
        students = mongo.students.find()
        
        buttons : list = list()
        twoButton : list = list()
        for table in students:
            for (classItem, studentsTable) in table.items():
                if studentsTable and str(classItem) != "_id":
                    twoButton.append(KeyboardButton(str(classItem)))
                    if len(twoButton) == 2:
                        buttons.append(twoButton)
                        twoButton = list()
        return buttons     
    
    
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
    
    
    async def SendNotify(classNum, message):
        message = "<b>Оголошення від {} {} {}".format(context.user_data.get("user").get("lastName").upper(), 
                                                            context.user_data.get("user").get("firstName"),
                                                            context.user_data.get("user").get("fatherName")) + message + ".</b>\n"
        students = mongo.students.find_one({}, {str(classNum) : 1}).get(str(classNum))
            
        filter = { "$or" : students }
        
        await SentToAllWho(filter, message, context)
        await context.bot.send_message(chat_id = chatId, text = "Оголошення надіслане.")
    
    
    async def MainMenuHandler():
        notification   = KeyboardButton("Створити оголошення для учнів")
        checkTimetable = KeyboardButton("Подивитися сьогоднішній розклад")
        createHomeWork = KeyboardButton("Створити домашнє завдання")
        checkClassList = KeyboardButton("Переглянути список учнів")
        exit           = KeyboardButton("Вихід")
        replyMarkup    = ReplyKeyboardMarkup([[notification], [checkTimetable], [checkClassList], [createHomeWork], [exit]], resize_keyboard = True)

        await context.bot.send_message(chat_id = update.effective_chat.id, text = "Оберіть дію.", reply_markup = replyMarkup)
    
    
    async def NotifyClassHandler():
        notifyState = context.user_data.get("notifyState", ENTER_CLASS_NOTIFIED)
        
        if notifyState == ENTER_CLASS_NOTIFIED:
            context.user_data["backState"] = BACK_TO_MAIN_MENU
            context.user_data["notifyState"] = ENTER_NOTIFY
            
            buttonsNotify = GetClassButtons()
            buttonsNotify.append([back])
            await context.bot.send_message(chat_id = chatId, text = "Оберіть клас.", reply_markup = ReplyKeyboardMarkup(buttonsNotify, resize_keyboard = True))
            
        elif notifyState == ENTER_NOTIFY:
            context.user_data["backState"] = BACK_TO_CLASS_ENTER_NOTIFY_MENU
            context.user_data["notifyState"] = SEND_NOTIFY
            
            try:
                context.user_data["whichClass"] = int(message)
                await context.bot.send_message(chat_id = chatId, text = "Введіть текст оголошення.", reply_markup = ReplyKeyboardMarkup([[back]], resize_keyboard = True))
            except:
                await context.bot.send_message(chat_id = chatId, text = "Ой, щось пішло не так. Можливо ви не обрали клас.", reply_markup = ReplyKeyboardMarkup([[back]], resize_keyboard = True))
        
        elif notifyState == SEND_NOTIFY:
            del context.user_data["notifyState"]
            await SendNotify(context.user_data.get("whichClass"), message)


    async def HomeworkHandler():
        homeworkState = context.user_data.get("homeworkState", ENTER_SUBJECT)
        
        if homeworkState == ENTER_SUBJECT:
            context.user_data["backState"] = BACK_TO_MAIN_MENU
            context.user_data["homeworkState"] = ENTER_HOMEWORK_CLASS
            
            if context.user_data.get("lesson"):
                del context.user_data["lesson"]
            
            subjectsButtons = [[item] for item in context.user_data.get("subjects").keys()]
            subjectsButtons.append([back])
            await context.bot.send_message(chat_id = chatId, text = "Оберіть предмет.", reply_markup = ReplyKeyboardMarkup(subjectsButtons, resize_keyboard = True))
        
        elif homeworkState == ENTER_HOMEWORK_CLASS:
            context.user_data["backState"] = BACK_TO_CLASS_ENTER_SUBJECTS_MENU
            context.user_data["homeworkState"] = ENTER_HOMEWORK
            
            if not context.user_data.get("lesson"):
                context.user_data["lesson"] = message
                
            context.user_data["homework"] = {"lesson" : context.user_data.get("lesson")}
            
            classButtons = [[item] for item in context.user_data.get("subjects").get(context.user_data.get("lesson"))]  # Need to review if user send incorect values. 
            classButtons.append([back])
            await context.bot.send_message(chat_id = chatId, text = "Оберіть клас.", reply_markup = ReplyKeyboardMarkup(classButtons, resize_keyboard = True))
            
        elif homeworkState == ENTER_HOMEWORK:
            context.user_data["backState"] = BACK_TO_CLASS_ENTER_HOMEWORK_MENU
            context.user_data["homeworkState"] = SAVE_HOMEWORK
            
            try:
                context.user_data["homework"]["class"] = int(message) # <- Maybe casting error
                await context.bot.send_message(chat_id = chatId, text = "Введіть домашнє завдання.", reply_markup = ReplyKeyboardMarkup([[back]], resize_keyboard = True))
            except:
                await context.bot.send_message(chat_id = chatId, text = "Ой, щось пішло не так. Можливо ви не обрали клас.", reply_markup = ReplyKeyboardMarkup([[back]], resize_keyboard = True))
                
        elif homeworkState == SAVE_HOMEWORK:
            del context.user_data["homeworkState"]
            context.user_data["backState"] = BACK_TO_CLASS_ENTER_HOMEWORK_MENU
            
            homework = {
                "_id" : context.user_data.get("homework"),
                "task": message,
                "creator": "{} {} {}".format(context.user_data.get("user").get("lastName").upper(), context.user_data.get("user").get("firstName"), context.user_data.get("user").get("fatherName")),
                "when"   : datetime.datetime.now(pytz.timezone('Europe/Kiev')).strftime("%H:%M %d-%m-%Y")
            }

            mongo.homeworks.update_one({"_id" : context.user_data.get("homework")}, {"$set": homework}, upsert=True)
            await context.bot.send_message(chat_id = chatId, text = "Домашнє завдання додано.", reply_markup = ReplyKeyboardMarkup([[back]], resize_keyboard = True))
            del context.user_data["homework"]
    
    
    async def ClassListHandler():
        isSelectClass = context.user_data.get("isSelectClass")
        
        if not isSelectClass:
            context.user_data["backState"] = BACK_TO_MAIN_MENU
            context.user_data["isSelectClass"] = True
            
            buttons = GetClassButtons()
            buttons.append([back])
            
            await context.bot.send_message(chat_id = chatId, text = "Оберіть клас.", reply_markup = ReplyKeyboardMarkup(buttons, resize_keyboard = True))
        
        else:
            del context.user_data["isSelectClass"]
            context.user_data["backState"] = BACK_TO_CLASS_ENTER_STUDENTS_MENU
            await ClassList(message, "Список учнів " + message + "-го класу:")
    
    
    if "Назад" == message:
        if backState == BACK_TO_MAIN_MENU:
            if context.user_data.get("notifyState"):
                del context.user_data["notifyState"]
                
            if context.user_data.get("isNotifyOwnClass"):
                del context.user_data["isNotifyOwnClass"]
            
            if context.user_data.get("homeworkState"):
                del context.user_data["homeworkState"]
            
            if context.user_data.get("isSelectClass"):
                del context.user_data["isSelectClass"]
            
            await MainMenuHandler()
            
        elif backState == BACK_TO_CLASS_ENTER_NOTIFY_MENU:
            if context.user_data.get("notifyState"):
                del context.user_data["notifyState"]
            await NotifyClassHandler()
            
        elif backState == BACK_TO_CLASS_ENTER_STUDENTS_MENU:
            await ClassListHandler()
        
        elif backState == BACK_TO_CLASS_ENTER_SUBJECTS_MENU:
            context.user_data["homeworkState"] = ENTER_SUBJECT
            await HomeworkHandler()
            
        elif backState == BACK_TO_CLASS_ENTER_HOMEWORK_MENU:
            context.user_data["homeworkState"] = ENTER_HOMEWORK_CLASS
            await HomeworkHandler()
        
    
    elif "Створити оголошення для учнів" == message or context.user_data.get("notifyState"):
        await NotifyClassHandler()
    
    elif "Подивитися сьогоднішній розклад" == message:
        context.user_data["backState"] = BACK_TO_MAIN_MENU
        await context.bot.send_message(chat_id = chatId, text = "Ось ваш розклад на сьогоднішній день", reply_markup = ReplyKeyboardMarkup([[back]], resize_keyboard = True))
        await context.bot.send_message(chat_id = chatId, text = TimetableForTeacher(context.user_data.get("user").get("lastName"),
                                                                                    context.user_data.get("user").get("firstName"),
                                                                                    context.user_data.get("user").get("fatherName")).GetTimetable()[0].AsString(), parse_mode = "HTML")

    elif "Створити домашнє завдання" == message or context.user_data.get("homeworkState"):
        context.user_data["subjects"] = TeacherSubjects(context.user_data.get("user").get("lastName"), context.user_data.get("user").get("firstName"), context.user_data.get("user").get("fatherName")).GetSubjects()
        await HomeworkHandler()
    
    elif "Переглянути список учнів" == message or context.user_data.get("isSelectClass"):
        await ClassListHandler()
            
    elif "Вихід" == message:
        mongo.users.update_one({"chatID" : chatId}, {"$set" : {"chatID" : None}})
        del context.user_data["isTecherMenu"]
        await Start(update, context)


async def StudentMenuHandler(update : Update, context : CallbackContext):
    message       : str = update.message.text
    chatId        : int = update.effective_chat.id
    classNum            = context.user_data.get("user").get("class")  # int 
    backState     : int = context.user_data.get("backState", 0)
    back                = KeyboardButton("Назад")
    
    
    BACK_TO_MAIN_MENU = 1
    BACK_TO_TIMETABLE_MENU = 2
    BACK_TO_CONTACT_MENU = 3
    BACK_TO_NOTE_MENU = 4
    BACK_TO_VIENOTE_MENU = 5
    BACK_TO_CREATE_NOTE_ENTER_TITLE = 6
    BACK_TO_CLEAR_MENU = 7
    BACK_TO_ENTER_TITLE_DEL_NOTE = 8
    BACK_TO_ENTER_TITLE_ARCH_NOTE = 9
    
    # Sates for creating note menu.
    ENTER_NOTE_TITLE, ENTER_NOTE_TEXT, SAVE_NOTE = range(1, 4)
    
    # Sates for delete note menu.
    ENTER_DEL_NOTE_TITLE, USER_IS_SHURE, DELETE_NOTE = range(1, 4)
    
    # Sates for archiving note menu.
    ENTER_ARCHIVE_NOTE_TITLE, USER_WANT_ARCHIVING, ARCHIV_NOTE = range(1, 4)
    
    
    def GetNoteButtons():
        if notes := mongo.notes.find({ "_id.userID" : context.user_data.get("user").get("_id") }):
            buttons : list = list()
            for note in notes:
                if title := note.get("_id").get("title"):
                    buttons.append([title])
            return None if len(buttons) == 0 else buttons
        else:
            return None
    
    
    async def MainMenu():
        context.user_data["isStudenMenu"] = True
    
        buttons = [
            [KeyboardButton("Розклад")],
            [KeyboardButton("Список класу")],
            [KeyboardButton("Домашнє завдання на завтра")],
            [KeyboardButton("Нотатки")],
            [KeyboardButton("Контакти")],
            [KeyboardButton("Вихід")]]
        replyMarkup    = ReplyKeyboardMarkup(buttons, resize_keyboard = True)

        await context.bot.send_message(chat_id = update.effective_chat.id, text = "Оберіть дію.", reply_markup = replyMarkup)
    
    
    async def TimetableMenu():
        context.user_data["backState"] = BACK_TO_MAIN_MENU
        
        buttons = [
            [KeyboardButton("Розклад на сьогодні")],
            [KeyboardButton("Розклад на тиждень")],
            [back]
        ]
        await context.bot.send_message(chat_id = chatId, text = "Оберіть дію.", reply_markup = ReplyKeyboardMarkup(buttons, resize_keyboard = True))
    
    
    async def DailyTimetableMenu():
        context.user_data["backState"] = BACK_TO_TIMETABLE_MENU
        
        await context.bot.send_message(chat_id = chatId, text = "Ось ваш розклад на сьогодні.", reply_markup = ReplyKeyboardMarkup([[back]], resize_keyboard = True))
        await context.bot.send_message(chat_id = chatId, text = TimetableForStudent(classNum).GetDailyTimetable()[0].AsString(), parse_mode = "HTML")
    
    
    async def WeeklyTimetableMenu():
        context.user_data["backState"] = BACK_TO_TIMETABLE_MENU
        
        await context.bot.send_message(chat_id = chatId, text = "Ось ваш розклад на тиждень.", reply_markup = ReplyKeyboardMarkup([[back]], resize_keyboard = True))
        await context.bot.send_message(chat_id = chatId, text = TimetableForStudent(classNum).GetWeeklyTimatable()[0].AsString(), parse_mode = "HTML")
    
    
    async def ClassListMenu():
        context.user_data["backState"] = BACK_TO_MAIN_MENU
        
        if classTeamates := mongo.students.find_one({}, {str(classNum) : 1}).get(str(classNum)):  # here posiable cast error.
            string : str = str()
            index  : int = int(1)
            for classTeamate in classTeamates:
                (lastName, firstName, fatherName) = classTeamate.values()
                if lastName  == context.user_data.get("user").get("lastName") and firstName == context.user_data.get("user").get("firstName") and fatherName == context.user_data.get("user").get("fatherName"):
                    string += f"<b>{index}) {lastName.upper()} {firstName} {fatherName}</b>\n"
                string += f"{index}) {lastName.upper()} {firstName} {fatherName}\n"
                index += 1
            
            await context.bot.send_message(chat_id = chatId, text = "Ось список вашого класу", reply_markup = ReplyKeyboardMarkup([[back]], resize_keyboard = True), parse_mode = "HTML")
            await context.bot.send_message(chat_id = chatId, text = string, parse_mode = "HTML")
    
    
    async def ContactMenu():
        context.user_data["backState"] = BACK_TO_MAIN_MENU
        
        buttons = [
            [KeyboardButton("Класного керівника")],
            [KeyboardButton("Директора")],
            [back]
        ]
        await context.bot.send_message(chat_id = chatId, text = "Контакти...", reply_markup = ReplyKeyboardMarkup(buttons, resize_keyboard = True))
    
    
    async def WhoseContact(type : str, label : str):
        context.user_data["backState"] = BACK_TO_CONTACT_MENU
        
        person = None
        string = str()
        if type == "classTeacher":
            person = mongo.teachers.find_one({"classTeacher" : str(classNum)})
        elif type == "admin":
            person = mongo.users.find_one({"userType.admin" : True})
            person = mongo.teachers.find_one({"firstName" : person.get("firstName"), "lastName" : person.get("lastName"), "fatherName" : person.get("fatherName")})
        
        string += "ПІБ: {} {} {}\n моб.тел.: {}".format(person.get("lastName").upper(), person.get("firstName"), person.get("fatherName"), person.get("phoneNumber"))
        await context.bot.send_message(chat_id = chatId, text = label, reply_markup = ReplyKeyboardMarkup([[back]], resize_keyboard = True))
        await context.bot.send_message(chat_id = chatId, text = string)
    
    
    async def TomorrowHomework():
        context.user_data["backState"] = BACK_TO_MAIN_MENU
        
        await context.bot.send_message(chat_id = chatId, text = "Домашнє завдання на завтра.", reply_markup = ReplyKeyboardMarkup([[back]], resize_keyboard = True))
        await context.bot.send_message(chat_id = chatId, text = TimetableForStudent(classNum).PickTomorrowHomework())
    
    
    async def NoteMenu():
        context.user_data["backState"] = BACK_TO_MAIN_MENU
        # TODO: add the chanche.
        
        buttons = [
            [KeyboardButton("Переглянути")],
            [KeyboardButton("Створити")],
            [KeyboardButton("Очистити")],
            [back]
        ]
        await context.bot.send_message(chat_id = chatId, text = "Ви перейшли в меню нотаток.\nОберіть дію.", reply_markup = ReplyKeyboardMarkup(buttons, resize_keyboard = True))
    
    
    async def ViewNotesMenu():
        if not context.user_data.get("isViewNote") and (buttons := GetNoteButtons()):
            context.user_data["backState"] = BACK_TO_NOTE_MENU
            
            context.user_data["isViewNote"] = True
            buttons.append([back])
            await context.bot.send_message(chat_id = chatId, text = "Виберіть нотатку яку хочете переглянути.", reply_markup = ReplyKeyboardMarkup(buttons, resize_keyboard = True))
        
        elif context.user_data.get("isViewNote"):
            context.user_data["backState"] = BACK_TO_VIENOTE_MENU
            del context.user_data["isViewNote"]
            
            if note := mongo.notes.find_one({"_id" : {"userID" : context.user_data.get("user").get("_id"), "title" : message}}):
                await context.bot.send_message(chat_id = chatId, text = "Ось ваша нотатка.")
                noteStr = "<b><pre>" + note.get("_id").get("title")  + "</pre></b>\n"
                noteStr += note.get("text")
                noteStr += "\n\n<i>Створено: " + note.get("when") + "</i>."
                await context.bot.send_message(chat_id = chatId, text = noteStr, parse_mode = "HTML", reply_markup = ReplyKeyboardMarkup([[back]], resize_keyboard = True))
            else:
                await context.bot.send_message(chat_id = chatId, text = "Щось пішло не так.", reply_markup = ReplyKeyboardMarkup([[back]], resize_keyboard = True))
            
        else:
            context.user_data["backState"] = BACK_TO_NOTE_MENU

            await context.bot.send_message(chat_id = chatId, text = "Нажаль ви не маєте жодної нотатки.", reply_markup = ReplyKeyboardMarkup([[back]], resize_keyboard = True))
    
    
    async def CreateNoteMenu():
        MAX_NUM_NOTE = 25
        MAX_TITLE_LEN = 50
        
        query = {"_id" : {"userID" : context.user_data.get("user").get("_id")}}
        
        if mongo.notes.count_documents(query) < MAX_NUM_NOTE:
            createNoteState = context.user_data.get("createNoteState", ENTER_NOTE_TITLE)

            if createNoteState == ENTER_NOTE_TITLE:
                context.user_data["backState"] = BACK_TO_NOTE_MENU

                context.user_data["createNoteState"] = ENTER_NOTE_TEXT
                await context.bot.send_message(chat_id = chatId, text = "Введіть назву нотатки.", reply_markup = ReplyKeyboardMarkup([[back]], resize_keyboard = True))

            elif createNoteState == ENTER_NOTE_TEXT:
                context.user_data["backState"] = BACK_TO_CREATE_NOTE_ENTER_TITLE

                query["_id"]["title"] = message
                if (len(message) > MAX_TITLE_LEN and (text := f"Назва для нотатки не може бути більшою за {MAX_TITLE_LEN} символів, а ваша містить {len(message)}.") or
                    mongo.notes.find_one(query) and (text := "Ви вже створювали нотатку під цією назвою.")):

                    context.user_data["createNoteState"] = ENTER_NOTE_TITLE

                    await context.bot.send_message(chat_id = chatId, text = text, reply_markup = ReplyKeyboardMarkup([[back]], resize_keyboard = True))

                else:
                    context.user_data["createNoteState"] = SAVE_NOTE
                    context.user_data["noteTitle"] = message
                    # back here move us to Note menu
                    await context.bot.send_message(chat_id = chatId, text = "Введіть текст нотатки.", reply_markup = ReplyKeyboardMarkup([[back]], resize_keyboard = True))

            elif createNoteState == SAVE_NOTE:
                context.user_data["backState"] = BACK_TO_NOTE_MENU

                del context.user_data["createNoteState"]

                note = {
                    "_id" : {
                        "userID" : context.user_data.get("user").get("_id"),
                        "title"  : context.user_data.get("noteTitle")
                    },
                    "text" : message,
                    "when" : datetime.datetime.now(pytz.timezone('Europe/Kiev')).strftime("%H:%M %d-%m-%Y")
                }

                mongo.notes.insert_one(note)
                del context.user_data["noteTitle"]
                await context.bot.send_message(chat_id = chatId, text = "Нотатку створено.", reply_markup = ReplyKeyboardMarkup([[back]], resize_keyboard = True))
        
        else:
            context.user_data["backState"] = BACK_TO_NOTE_MENU
            await context.bot.send_message(chat_id = chatId, text = f"Ви вичерпали ліміт нотаток {MAX_NUM_NOTE}. Видаліть або архівуйте старіші нотатки.", reply_markup = ReplyKeyboardMarkup([[back]], resize_keyboard = True))
    
    
    async def ClearNoteMenu():
        context.user_data["backState"] = BACK_TO_NOTE_MENU
        
        buttons = [
            [KeyboardButton("Видалити")],
            [KeyboardButton("Архівувати")],
            [back]
        ]
        
        await context.bot.send_message(chat_id = chatId, text = "Оберіть дію.", reply_markup = ReplyKeyboardMarkup(buttons, resize_keyboard = True))
    
    
    async def DeleteNoteMenu():
        context.user_data["backState"] = BACK_TO_CLEAR_MENU
        delState = context.user_data.get("delState", ENTER_DEL_NOTE_TITLE)
        
        if delState == ENTER_DEL_NOTE_TITLE and (buttons := GetNoteButtons()):
            context.user_data["delState"] = USER_IS_SHURE
            buttons.append([KeyboardButton("Всі нотатки")])
            buttons.append([back])
            
            await context.bot.send_message(chat_id = chatId, text = "Ви хочете видалити...", reply_markup = ReplyKeyboardMarkup(buttons, resize_keyboard = True))
        
        elif delState == USER_IS_SHURE:
            context.user_data["backState"] = BACK_TO_ENTER_TITLE_DEL_NOTE
            context.user_data["delState"] = DELETE_NOTE
            context.user_data["noteTitle"] = message
            await context.bot.send_message(chat_id = chatId, text = "Ви точно впевненні?", reply_markup = ReplyKeyboardMarkup([["Так"], ["Ні"]], resize_keyboard = True))

        elif delState == DELETE_NOTE:
            context.user_data["backState"] = BACK_TO_ENTER_TITLE_DEL_NOTE
            
            if message == "Так":
                userId = context.user_data.get("user").get("_id")
                title = context.user_data.get("noteTitle")
                del context.user_data["delState"]
                
                if title == "Всі нотатки":
                    mongo.notes.delete_many({"_id.userID": userId})
                    context.user_data["backState"] = BACK_TO_CLEAR_MENU  # We deleted all notes that user had, and move him to clear menu.
                    
                else:
                    mongo.notes.delete_one({"_id" : {"userID" : userId, "title" : title}})
                    
                    # We are checking if current user has notes, if he does not has any we move him to clear menu.
                    if mongo.notes.count_documents({"_id.userID" : context.user_data.get("user").get("_id")}) == 0:
                        context.user_data["backState"] = BACK_TO_CLEAR_MENU
                
                await context.bot.send_message(chat_id = chatId, text = f"{title} видалено.", reply_markup = ReplyKeyboardMarkup([[back]], resize_keyboard = True))
                
            elif message == "Ні":
                await context.bot.send_message(chat_id = chatId, text = "Ви відхилили видалення нотатки.", reply_markup = ReplyKeyboardMarkup([[back]], resize_keyboard = True))
            
            else:
                await context.bot.send_message(chat_id = chatId, text = "Вибачте, але я не розумію такої команди.", reply_markup = ReplyKeyboardMarkup([[back]], resize_keyboard = True))

        else:
            await context.bot.send_message(chat_id = chatId, text = "Ви не маєте жодної нотатки", reply_markup = ReplyKeyboardMarkup([[back]], resize_keyboard = True))
    
    
    async def ArchivingNoteMenu():
        context.user_data["backState"] = BACK_TO_CLEAR_MENU
        delState = context.user_data.get("archState", ENTER_ARCHIVE_NOTE_TITLE)
        
        if delState == ENTER_ARCHIVE_NOTE_TITLE and (buttons := GetNoteButtons()):
            context.user_data["archState"] = USER_WANT_ARCHIVING
            buttons.append([KeyboardButton("Всі нотатки")])
            buttons.append([back])
            
            await context.bot.send_message(chat_id = chatId, text = "Архівація допоможе вам зберегти нотатки у вигляді pdf файлу, але із бази даних їх буде видалено")
            await context.bot.send_message(chat_id = chatId, text = "Ви хочете архівувати...", reply_markup = ReplyKeyboardMarkup(buttons, resize_keyboard = True))
        
        elif delState == USER_WANT_ARCHIVING:
            context.user_data["backState"] = BACK_TO_ENTER_TITLE_ARCH_NOTE
            
            context.user_data["archState"] = ARCHIV_NOTE
            context.user_data["noteTitle"] = message
            await context.bot.send_message(chat_id = chatId, text = "Ви точно впевненні?", reply_markup = ReplyKeyboardMarkup([["Так"], ["Ні"]], resize_keyboard = True))

        elif delState == ARCHIV_NOTE:
            context.user_data["backState"] = BACK_TO_ENTER_TITLE_ARCH_NOTE
            
            if message == "Так":
                import os
                from scripts.tools.pdfCreator import CreatePDF
                
                userId = context.user_data.get("user").get("_id")
                title = context.user_data.get("noteTitle")
                del context.user_data["archState"]
                
                if title == "Всі нотатки":
                    context.user_data["backState"] = BACK_TO_CLEAR_MENU  # We deleted all notes that user had, and move him to clear menu.
                    
                    query = { "_id.userID": userId }
                    notes = mongo.notes.find(query)
                    
                    CreatePDF(notes, fileName := "Всі_нотатки.pdf")
                    await context.bot.send_document(chat_id=chatId, document=open(fileName, 'rb'))
                    
                    os.remove(fileName)
                    mongo.notes.delete_many(query)
                    
                else:
                    context.user_data["backState"] = BACK_TO_ENTER_TITLE_ARCH_NOTE 
                    
                    note = mongo.notes.find_one_and_delete({"_id" : {"userID" : userId, "title" : title}})
                    
                    CreatePDF([note], fileName := note.get("_id").get("title") + ".pdf")
                    await context.bot.send_document(chat_id=chatId, document=open(fileName, 'rb'))
                    os.remove(fileName)
                    
                    # We are checking if current user has notes, if he does not has any we move him to clear menu.
                    if mongo.notes.count_documents({"_id.userID" : context.user_data.get("user").get("_id")}) == 0:
                        context.user_data["backState"] = BACK_TO_CLEAR_MENU
                
                await context.bot.send_message(chat_id = chatId, text = "Ось ваші архівовані нотатки.")
                await context.bot.send_message(chat_id = chatId, text = f"{title} архівовано.", reply_markup = ReplyKeyboardMarkup([[back]], resize_keyboard = True))
                
            elif message == "Ні":
                await context.bot.send_message(chat_id = chatId, text = "Ви відхилили архівацію нотатки.", reply_markup = ReplyKeyboardMarkup([[back]], resize_keyboard = True))
            
            else:
                await context.bot.send_message(chat_id = chatId, text = "Вибачте, але я не розумію такої команди.", reply_markup = ReplyKeyboardMarkup([[back]], resize_keyboard = True))

        else:
            await context.bot.send_message(chat_id = chatId, text = "Ви не маєте жодної нотатки", reply_markup = ReplyKeyboardMarkup([[back]], resize_keyboard = True))
    
    
    
    if "Назад" == message:
        if backState == BACK_TO_MAIN_MENU:
            await MainMenu()
        
        elif backState == BACK_TO_TIMETABLE_MENU:
            await TimetableMenu()
        
        elif backState == BACK_TO_CONTACT_MENU:
            await ContactMenu()
        
        elif backState == BACK_TO_NOTE_MENU:
            if context.user_data.get("isViewNote"):
                del context.user_data["isViewNote"]
            
            if context.user_data.get("createNoteState"):
                del context.user_data["createNoteState"]
            
            await NoteMenu()
        
        elif backState == BACK_TO_VIENOTE_MENU:
            await ViewNotesMenu()
        
        elif backState == BACK_TO_CREATE_NOTE_ENTER_TITLE:
            await CreateNoteMenu()
            
        elif backState == BACK_TO_CLEAR_MENU:
            if context.user_data.get("delState"):
                    del context.user_data["delState"]
            
            if context.user_data.get("archState"):
                del context.user_data["archState"]
            
            if context.user_data.get("noteTitle"):
                del context.user_data["noteTitle"]

            await ClearNoteMenu()
            
        elif backState == BACK_TO_ENTER_TITLE_DEL_NOTE:
            if context.user_data.get("delState"):
                del context.user_data["delState"]
            
            if context.user_data.get("noteTitle"):
                del context.user_data["noteTitle"]
            
            await DeleteNoteMenu()
        
        elif backState == BACK_TO_ENTER_TITLE_ARCH_NOTE:
            if context.user_data.get("archState"):
                del context.user_data["archState"]
            
            if context.user_data.get("noteTitle"):
                del context.user_data["noteTitle"]
            
            await ArchivingNoteMenu()
        
    elif "Розклад" == message:
        await TimetableMenu()
        
    elif "Розклад на тиждень" == message:
        await WeeklyTimetableMenu()
    
    elif "Розклад на сьогодні" == message:
        await DailyTimetableMenu()
        
    elif "Список класу" == message:
        await ClassListMenu()
        
    elif "Домашнє завдання на завтра" == message:
        await TomorrowHomework()
    
    elif "Нотатки" == message:
        await NoteMenu()
    
    elif "Переглянути" == message or context.user_data.get("isViewNote"):
        await ViewNotesMenu()
    
    elif "Створити" == message or context.user_data.get("createNoteState"):
        await CreateNoteMenu()
    
    elif "Очистити" == message:
        await ClearNoteMenu()
    
    elif "Видалити" == message or context.user_data.get("delState"):
        await DeleteNoteMenu()
    
    elif "Архівувати" == message or context.user_data.get("archState"):
        await ArchivingNoteMenu()
    
    elif "Контакти" == message:
        await ContactMenu()
    
    elif "Класного керівника" == message:
        await WhoseContact("classTeacher", "Контакти класного керівника.")
    
    elif "Директора" == message:
        await WhoseContact("admin", "Контакти директора.")
    
    elif "Вихід" == message:
        mongo.users.update_one({"chatID" : chatId}, {"$set" : {"chatID" : None}})
        del context.user_data["isStudentMenu"]
        await Start(update, context)


async def YesNoEntryHandler(update : Update, context : CallbackContext, stateName : str, statePos : int, yesText : str, noText : str):
    message : str = update.message.text
    chatId  : int = update.effective_chat.id
    
    if "Так" == message:
        await context.bot.send_message(chat_id = chatId, text = yesText, reply_markup = ReplyKeyboardRemove())
        context.user_data[stateName] = statePos
            
    elif "Ні" == message:
        await context.bot.send_message(chat_id = chatId, text = noText, reply_markup = ReplyKeyboardRemove())
        await EntryMenu(update, context)  # TODO: To first menu.
    
    else:
        await context.bot.send_message(chat_id = chatId, text = "Введено некоректне повідомлення")


async def CheckAirDangerous(context : CallbackContext):
    # respond = None
    # with open(pathes.AIRDANGEROUS_JSON, 'r', encoding = "utf8") as file:
    #     respond = json.load(file)
        
    # respond = requests.get("https://ubilling.net.ua/aerialalerts/").json()
    # if respond and (state := respond.get("states").get("Львівська область")):
    import scripts.tools.config as config
    respond = requests.get(config.AIR_DANG_URL, headers = config.AIR_DANG_HEADERS).json()[0]
    if respond and (alter := respond.get("activeAlerts")):
        if alter and not context.bot_data.get("isSendedNotifyAirDangerous"):
            context.bot_data["isSendedNotifyAirDangerous"] = True
            users = mongo.users.find({"chatID": {"$ne": None}})  # Get all active users.
            for user in users:
                await context.bot.send_message(chat_id = user.get("chatID"),
                                                text = "🔴<b>УВАГА!\nОголошена повітряна тривога у Львівській області!</b>\n" + 
                                                "Пройдіть в укриття!\n" + 
                                                "Слідкуйте за подальшими повідомленнями.", parse_mode = "HTML")
                
        elif not alter and context.bot_data.get("isSendedNotifyAirDangerous"):
            context.bot_data["isSendedNotifyAirDangerous"] = False
            users = mongo.users.find({"chatID": {"$ne": None}})  # Get all active users.
            for user in users:
                await context.bot.send_message(chat_id = user.get("chatID"), text = "🟢<b>УВАГА! Відбій повітряної тривоги!</b>\n", parse_mode = "HTML")


async def SendLessonNotification(context : CallbackContext):
    if context.bot_data.get("isSendedNotifyAirDangerous"):
        return
    
    chatId = context.user_data.get("user").get("id")
    followLesson = FollowLesson(int(context.user_data.get("user").get("class")))
    lessonData = await followLesson.GetCurrentLessonAsync()
    
    print(lessonData)
    
    if lessonData is not None:  # The lessons' time.
        if not lessonData["isHoliday"] and not lessonData["isBreak"]:  # The lesson start or heppen.
            if sendedLessonData := context.user_data.get("user").get("lessonData"):
                # If we have sended msg about lesson to current user.
                if sendedLessonData["infoLesson"] == lessonData["infoLesson"] and sendedLessonData["isBreak"] == lessonData["isBreak"]:
                    return

            # Sending.
            await context.bot.send_message(chat_id = chatId, 
                                            text = PhrasesGenerator(lessonData["infoLesson"]["name"], 
                                                                    pathes.START_LESSON_PHRASES_TXT).GetRandomPhrase() +
                                            "\nПочаток уроку : {}".format(lessonData["infoLesson"]["startTime"]) + 
                                            "\nКінець уроку  : {}".format(lessonData["infoLesson"]["endTime"]),
                                            parse_mode = "HTML")

            context.user_data["user"]["lessonData"] = lessonData  # Save the info about lesson in our user.
            print("the msg has been sent")

        elif lessonData["isBreak"]:  # if we have a break.
            if sendedLessonData := context.user_data.get("user").get("lessonData"):
                if sendedLessonData["infoLesson"] == lessonData["infoLesson"] and sendedLessonData["isBreak"] == lessonData["isBreak"]:
                    return

            # Sending.
            await context.bot.send_message(chat_id = chatId, 
                    text = PhrasesGenerator(lessonData["infoLesson"]["name"], 
                                            pathes.BREAK_PHRASES_TXT).GetRandomPhrase() +
                                            "\nПочаток уроку : {}".format(lessonData["infoLesson"]["startTime"]) + 
                                            "\nКінець уроку  : {}".format(lessonData["infoLesson"]["endTime"]),
                                            parse_mode = "HTML")

            context.user_data["user"]["lessonData"] = lessonData  # Save the info about lesson in our user.
            print("the msg has been sent")



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


async def SentToAllWho(filter, message : str , context : CallbackContext):
    users = mongo.users.find(filter)
    for user in users:
        if user.get("chatID"):
            await context.bot.send_message(chat_id = user.get("chatID"), text = message, parse_mode = "HTML")    


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