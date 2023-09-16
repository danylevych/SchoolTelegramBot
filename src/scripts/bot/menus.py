import asyncio
import scripts.tools.mongo as mongo

from scripts.bot.notify import *
from scripts.bot.toolsFunc import *

from telegram.ext import ContextTypes
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton


async def Start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["user"] = dict()
    
    if user := ChatIdIExistInDB(update.effective_chat.id):
        context.user_data["user"]["id"] = user.get("chatID")
        context.user_data["user"]["firstName"] = user.get("firstName")
        context.user_data["user"]["lastName"] = user.get("lastName")
        context.user_data["user"]["fatherName"] = user.get("fatherName")
        
        userType = user.get("userType")
        
        if userType.get("developer") or userType.get("admin"):
            # So, we might have a situation, when the admin might have subjects, that he is teaching.
            # To diside this issue we create the menu, when the admin who is a teacher at the time 
            # can choose, what type of entrance he feel like,
            if userType.get("admin") and userType.get("teacher"):  # We get the situation, which we discriped top.
                buttons = [["АДМІНІСТРАТОР"], ["ВЧИТЕЛЬ"]]
                replyMarkup = ReplyKeyboardMarkup(buttons, resize_keyboard = True)
                await context.bot.send_message(chat_id = update.effective_chat.id, text = "Виберіть тип користувача під яким намагаєтеся здійснити вхід.", reply_markup = replyMarkup)
                return
            
            context.user_data["user"]["type"] = "developer" if userType.get("developer") else "admin"

            await asyncio.sleep(1)
            await context.bot.send_message(chat_id = update.effective_chat.id, text = "Вхід успішний!")

            await AdminMenu(update, context)

        elif userType.get("teacher"):
            teacher = mongo.teachers.find_one({ "firstName"  : user.get("firstName"), 
                                                "lastName"   : user.get("lastName"),
                                                "fatherName" : user.get("fatherName")})
            
            context.user_data["user"]["classTeacher"] = int(teacher.get("classTeacher"))

            classTeacher = context.user_data.get("user").get("classTeacher")
            if classTeacher != 0 or (type(classTeacher) != list):
                await TeacherLeaderMenu(update, context)
        
            else:
                await TeacherMenu(update, context)
            
        else:
            await StartUserMenu(update, context, user)

    else:
        await update.message.reply_text(f"Привіт, {update.effective_user.full_name}.")
        await EntryMenu(update, context)


async def StartUserMenu(update: Update, context: ContextTypes.DEFAULT_TYPE, user):
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
    context.user_data["alertJob"] = context.job_queue.run_repeating(SendLessonNotification, interval = 2, first = 0, user_id = context.user_data.get("user").get("id"))
    
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
