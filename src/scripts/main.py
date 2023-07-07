import json
from typing import Final
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CallbackContext, ContextTypes, MessageHandler, filters, CommandHandler

TOKEN: Final = "6190355366:AAGl7tLOmkuP9_qAbxy6VHGlGp8VhmS25Y4"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
  await update.message.reply_text(f"Привіт, {update.effective_user.full_name}."
                                  )
  yes = KeyboardButton("Так")
  no = KeyboardButton("Ні")
  reply_markup = ReplyKeyboardMarkup([[yes, no]], resize_keyboard=True)

  await context.bot.send_message(chat_id=update.effective_chat.id,
                                 text="А ти навчаєшся в ЗОШ Вівня?",
                                 reply_markup=reply_markup)
  context.user_data["firstStartCalling"] = True


async def MessagesHandler(update: Update, context: CallbackContext):
  if context.user_data.get("firstStartCalling"):
    if "Так" in update.message.text:
      await context.bot.send_message(chat_id=update.effective_chat.id,
                                     text='''
          Добренько. Тепер введіть прізвише ім'я побатькові та клас.
          Приклад: Петренко Петро Птрович 10
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
  elif context.user_data.get("enteringFullnameAndClass"):
    name: str = update.message.text
    if IsStudent(name):
      await context.bot.send_message(chat_id=update.effective_chat.id,
                                     text="Вітаємо")
    else:
      await context.bot.send_message(chat_id=update.effective_chat.id,
                                     text="Нажаль такого користувача немає")
    del context.user_data["enteringFullnameAndClass"]


def IsStudent(name: str) -> bool:
  data = name.split(" ")

  with open("students.json", "r", encoding="utf8") as file:
    students = json.load(file)

    for item in students[data[len(data) - 1]]:
      if item["lastName"] in data and item["firstName"] in data and item[
          "fatherName"] in data:
        return True

  return False


def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Text(), MessagesHandler))

    app.run_polling()


if __name__ == "__main__":
    main()