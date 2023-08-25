import json

import asyncio
import requests
import scripts.tools.mongo as mongo
import scripts.tools.pathes as pathes

from telegram.ext import CallbackContext
from scripts.tools.phrases import PhrasesGenerator
from scripts.classes.followLesson import FollowLesson


async def CheckAirDangerous(context : CallbackContext):
    # Another way to get air alert.
    
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


async def SentToAllWho(filter, message : str , context : CallbackContext):
    users = mongo.users.find(filter)
    for user in users:
        if user.get("chatID"):
            await context.bot.send_message(chat_id = user.get("chatID"), text = message, parse_mode = "HTML")    