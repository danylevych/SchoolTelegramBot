import sys
sys.path.append("src/scripts/tools")
import pathes

import json
import asyncio
from followLesson import FollowLesson
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import CallbackContext, ContextTypes


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["firstStartCalling"] = True
    context.user_data["id"] = update.effective_chat.id
    
    await update.message.reply_text(f"Привіт, {update.effective_user.full_name}.")
    
    yes = KeyboardButton("Так")
    no = KeyboardButton("Ні")
    reply_markup = ReplyKeyboardMarkup([[yes, no]], resize_keyboard=True)
    
    await asyncio.sleep(1)
    await context.bot.send_message(chat_id = update.effective_chat.id,
                                    text = "А ти навчаєшся в ЗОШ Вівня?",
                                    reply_markup = reply_markup)


async def send_lesson_start_notification(context: CallbackContext):
    followLesson = FollowLesson(int(context.user_data.get("class")))
    
    lessonData = await followLesson.GetCurrentLessonAsync()
    if lessonData is not None:  # The lessons' time.
        if not lessonData["isHoliday"] or not lessonData["isBreak"]:  # The lesson start or heppen.
            if context.user_data.get("lessonData"):
                sendedLessonData = context.user_data.get("lessonData")
                if sendedLessonData["infoLesson"] == lessonData["infoLesson"]:
                    return
            await context.bot.send_message(chat_id = context.user_data.get("id"), text = 
                    "{} почалася.\nПочаток - {}\nКінець - {}".format(lessonData["infoLesson"]["name"],
                                                                    lessonData["infoLesson"]["startTime"],
                                                                    lessonData["infoLesson"]["endTime"]))
            context.user_data["lessonData"] = lessonData
            print("the msg has been sent")
        
        elif lessonData["isBreak"]:
            if context.user_data.get("lessonData"):
                sendedLessonData = context.user_data.get("lessonData")
                if sendedLessonData["infoLesson"] == lessonData["infoLesson"]:
                    return
            
            await context.bot.send_message(chat_id = context.user_data.get("id"), 
                    text = "Зараз прерва, але не забудь, що скоро почнеться".format()) # TODO: msg.
            context.user_data["lessonData"] = lessonData
            print("the msg has been sent")


async def MessagesHandler(update: Update, context: CallbackContext):
    if context.user_data.get("firstStartCalling"):  # The first calling.
        StartCallMsgHandler(update.message.text, update.effective_chat.id, context)
        del context.user_data["firstStartCalling"]
    
    elif context.user_data.get("enteringFullnameAndClass"):  # User entered his name.
        if await StudentNameInputHandler(update.message.text, update.effective_chat.id, context):
            del context.user_data["enteringFullnameAndClass"]


async def StartCallMsgHandler(message : str, chatId, context : CallbackContext):
    message = ValidateMsg(message).lover()
    if "так" in message:
        await context.bot.send_message(chat_id = chatId,
                                    text = '''
        Добренько. Тоді введіть ваше прізвише ім'я побатькові та клас.\nПриклад: Петренко Петро Пeтрович 10
        ''',
                                        reply_markup = ReplyKeyboardRemove())
        # The variable that store user ability to the next msg input.
        context.user_data["enteringFullnameAndClass"] = True 

    elif "ні" in message:
            await context.bot.send_message(chat_id = chatId,
                                        text = """
            Тоді вам немає що тут робити :)\nБувайте
            """,
                                        reply_markup = ReplyKeyboardRemove())
    
    else:
            await context.bot.send_message(chat_id=chatId,
                                            text = """
            Не коректне повідомлення, впевніться, що ви натисли на потрібну кнопку""")


async def StudentNameInputHandler(message : str, chatId, context : CallbackContext) -> bool:
    name : str = ValidateUserNeme(message)
    if IsStudent(name):
        context.user_data["class"] = name.split(' ')[-1] # TODO: Maybe delete this stuff if the json users file will be create. 
        await context.bot.send_message(chat_id = chatId, text = "Вітаємо")
        context.job_queue.run_repeating(send_lesson_start_notification, interval = 30, first = 0, user_id = chatId)
        return True
    else:
        await context.bot.send_message(chat_id = chatId, text = """
            Нажаль такого користувача немає. Впевніться що ввели дані коректно. Або зверніться в технічну підтримку.""")
        return False


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
        if item["lastName"] in data and item["firstName"] in data and item["fatherName"] in data:
            return True
    return False


def ValidateMsg(message : str) -> str:
    message = message.lstrip(' +×÷=/_<>[]!@#₴%^&*()-":;,?`~\|{}€£¥$°•○●□■♤♡◇♧☆▪️¤《》¡¿')
    message = message.rstrip(' +×÷=/_<>[]!@#₴%^&*()-":;,?`~\|{}€£¥$°•○●□■♤♡◇♧☆▪️¤《》¡¿')
    return message