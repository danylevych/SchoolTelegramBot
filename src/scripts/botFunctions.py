import sys
sys.path.append("src/scripts/tools")
import pathes

import json
import asyncio
from followLesson import FollowLesson
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import CallbackContext, ContextTypes


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["id"] = update.effective_chat.id
    await update.message.reply_text(f"Привіт, {update.effective_user.full_name}.")
    
    yes = KeyboardButton("Так")
    no = KeyboardButton("Ні")
    reply_markup = ReplyKeyboardMarkup([[yes, no]], resize_keyboard=True)
    context.user_data["firstStartCalling"] = True
    await asyncio.sleep(1)
    await context.bot.send_message(chat_id=update.effective_chat.id,
                                text="А ти навчаєшся в ЗОШ Вівня?",
                                reply_markup=reply_markup)


async def send_lesson_start_notification(context: CallbackContext):
    follow = FollowLesson(int(context.user_data.get("class")))
    data = await follow.GetCurrentLessonAsync()
    if data is not None:
        if not data["isHoliday"] or not data["isBreak"]:
            await context.bot.send_message(chat_id = context.user_data.get("id"), text = "Починається урок" + context.user_data.get("class"))
            print("the msg has been sent")
        
        elif data["isBreak"]:
            pass  # TODO: send info about next lesson.


async def MessagesHandler(update: Update, context: CallbackContext):
    if context.user_data.get("firstStartCalling"):  # The first calling.
        if "Так" in update.message.text:
            await context.bot.send_message(chat_id=update.effective_chat.id,
                                        text='''
            Добренько. Тоді введіть ваше прізвише ім'я побатькові та клас.
            Приклад: Петренко Петро Пeтрович 10
            ''',
                                            reply_markup=ReplyKeyboardRemove())
            context.user_data["enteringFullnameAndClass"] = True

        elif "Ні" in update.message.text:
            await context.bot.send_message(chat_id=update.effective_chat.id,
                                        text="Користувач натиснув кнопку 'Ні'",
                                        reply_markup=ReplyKeyboardRemove())
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id,
                                            text="Інше натискання кнопки")

        del context.user_data["firstStartCalling"]
    
    elif context.user_data.get("enteringFullnameAndClass"):  # User entered his name.
        name : str = ValidateUserNeme(update.message.text)
        if IsStudent(name):
            context.user_data["class"] = name.split(' ')[-1]
            await context.bot.send_message(chat_id=update.effective_chat.id,
                                            text="Вітаємо")
            context.job_queue.run_repeating(send_lesson_start_notification, interval = 30, first=0, user_id = update.effective_chat.id)

        else:
            await context.bot.send_message(chat_id=update.effective_chat.id,
                                            text="Нажаль такого користувача немає")
        del context.user_data["enteringFullnameAndClass"]


def ValidateUserNeme(name : str) -> str:
    name = name.lstrip(' +×÷=/_<>[]!@#₴%^&*()-":;,?`~\|{}€£¥$°•○●□■♤♡◇♧☆▪️¤《》¡¿')
    name = name.rstrip(' +×÷=/_<>[]!@#₴%^&*()-":;,?`~\|{}€£¥$°•○●□■♤♡◇♧☆▪️¤《》¡¿')
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