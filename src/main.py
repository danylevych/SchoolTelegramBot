import scripts.tools.config as config
import scripts.botFunctions as botFunctions
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

def main():
    app_builder = ApplicationBuilder()
    app = app_builder.token(config.BOT_TOKEN).build()

    if app is not None:
        specialKeywords = ["АДМІНІСТРАТОР", "ВЧИТЕЛЬ"]
        # Create a custom filter that checks if the message contains any of the special keywords
        specialKeywordFilter = filters.Text() & (filters.Regex(r'\b(?:' + '|'.join(specialKeywords) + r')\b'))
        app.add_handler(MessageHandler(filters.Text(["АДМІНІСТРАТОР", "ВЧИТЕЛЬ"]), botFunctions.MessagesHandlerAdminTeacher))
        
        app.add_handler(CommandHandler("start", botFunctions.Start))
        app.job_queue.run_repeating(botFunctions.CheckAirDangerous, interval = 60, first = 0)
        app.add_handler(MessageHandler(filters.Text(), botFunctions.MessagesHandler))
        app.run_polling()
    else:
        print("Failed to create the application object.")

if __name__ == "__main__":
    main()