import sys
sys.path.append("src/scripts/tools")
import pathes
import mongo
from phrases import PhrasesGenerator

import json
import asyncio
import requests
from followLesson import FollowLesson
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import CallbackContext, ContextTypes
import os



def isJsonEmpty(file_path):
    file_size = os.path.getsize(file_path)
    return file_size == 0

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["user"] = dict()
    
    if UserExist(update.effective_chat.id, context):
        context.job_queue.run_repeating(send_lesson_start_notification, interval = 2, first = 0, user_id = context.user_data.get("user").get("_id"))
    
    else:
        context.user_data["user"]["firstStartCalling"] = True
        context.user_data["user"]["_id"] = update.effective_chat.id

        await update.message.reply_text(f"Привіт, {update.effective_user.full_name}.")

        yes = KeyboardButton("Так")
        no = KeyboardButton("Ні")
        reply_markup = ReplyKeyboardMarkup([[yes, no]], resize_keyboard=True)

        await asyncio.sleep(1)
        await context.bot.send_message(chat_id = update.effective_chat.id,
                                        text = "А ти навчаєшся в ЗОШ Вівня?",
                                        reply_markup = reply_markup)


async def CheckAirDangerous(context : CallbackContext):
    state = await requests.request("https://ubilling.net.ua/aerialalerts/")["states"]["Луганська область"]
    if state["alertnow"]:
        await context.bot.send_message(chat_id = context.user_data.get("user").get("_id"),
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
    if context.user_data.get("user").get("firstStartCalling"):  # The first calling.
        await StartCallMsgHandler(update.message.text, update.effective_chat.id, context)
        del context.user_data["user"]["firstStartCalling"]  # The info about first calling has deleted.
    
    elif context.user_data.get("user").get("enteringFullnameAndClass"):  # User entered his name.
        await StudentNameInputHandler(update.message.text, update.effective_chat.id, context)
    
    else:
        await context.bot.send_message(chat_id = update.effective_chat.id, text = "Нажаль такої команди не існує)")


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