import json
import pytz
from enum import Enum
from datetime import time, datetime
import scripts.tools.pathes as pathes
import scripts.tools.mongo  as mongo


def GetSeason(month):
    if 3 <= month <= 5:
        return "spring"
    elif 6 <= month <= 8:
        return "summer"
    elif 9 <= month <= 11:
        return "autumn"
    else:
        return "winter"


class Holiday(Enum):
    VACATION = 1,
    WEEKENDS = 2,
    WEEKDAYS = 3


class TimetableBase:
    def __init__(self):
        self.currentTime = None
        self.currentDay  = None
        self.currentDate  = None
    
    def IsHoliday(self) -> Holiday:
        with open(pathes.VACATION_JSON, "r", encoding="utf8") as file:
            if seasonVacation := json.load(file)[GetSeason(self.currentDate.month)]:
                dateFormat = "%d.%m.%Y"
                startVacation = datetime.strptime(seasonVacation.get("startVacation"), dateFormat)
                endVacation = datetime.strptime(seasonVacation.get("endVacation"), dateFormat)

                timezone = pytz.timezone("Europe/Kiev")
                startVacation = timezone.localize(startVacation)
                endVacation = timezone.localize(endVacation)
                # self.currentDate = timezone.localize(self.currentDate)

                if startVacation <= self.currentDate <= endVacation:
                    return Holiday.VACATION

        
        if self.currentDay not in ("monday", "tuesday", "wednesday", "thursday", "friday"):
            self.returnedData = None
            return Holiday.WEEKENDS
        
        return Holiday.WEEKDAYS
    
    
    def SetCurrentDateTime(self):
        self.currentDate = datetime.now(pytz.timezone('Europe/Kiev'))
        self.currentTime = datetime.now(pytz.timezone('Europe/Kiev')).time()
        self.currentDay  = datetime.now(pytz.timezone('Europe/Kiev')).strftime('%A').lower()


class TimetableForTeacher(TimetableBase):
    def __init__(self, lastName, firstName, fatherName):
        TimetableBase.__init__(self)
        self.returnedData = None 
        self.userInfo = mongo.teachers.find_one({"firstName" : firstName, "lastName" : lastName, "fatherName" : fatherName})
    
    
    def GetTimetable(self):
        self.SetCurrentDateTime()
        
        self.holiday = self.IsHoliday()
        if self.holiday in (Holiday.VACATION, Holiday.WEEKENDS):
            self.returnedData = None
            return (self, self.returnedData)
        
        for (name, classArr) in self.userInfo.get("subjects").items():
            with open(pathes.TIMETABLE_JSON, "r", encoding = "utf8") as file:
                timetableInfo = json.load(file)
                for classItem in classArr:
                    if timetableInfo.get(f"class{classItem}"):
                        currentTimetable = timetableInfo.get(f"class{classItem}").get(self.currentDay)
                        for (lessonNum, lessonName) in currentTimetable.items():
                            if name == lessonName:
                                with open(pathes.TIMETABLE_LESSONS_JSON, "r", encoding = "utf8") as file:
                                    lessonTime = json.load(file).get(f"class{classItem}").get(lessonNum)
                                    startTime  = lessonTime.get("startTime")
                                    endTime    = lessonTime.get("endTime")

                                    if not self.returnedData:
                                        self.returnedData = dict()

                                    self.returnedData[lessonNum] = {
                                        "class"     : classItem,
                                        "name"      : lessonName,
                                        "startTime" : time(startTime.get("hour"), startTime.get("minute")),
                                        "endTime"   : time(endTime.get("hour"), endTime.get("minute"))
                                    }

        return (self, self.returnedData)
    
    
    def AsString(self):
        if not self.returnedData:
            if self.holiday == Holiday.WEEKENDS:
                return "Сьогодні заннять немає."
            else:
                return "Зараз в школі канікули."
        
        string = str()
        currentTime = currentTime = datetime.now(pytz.timezone('Europe/Kiev')).time()

        for lessonNum in sorted(self.returnedData.keys()):
            lessonInfo = self.returnedData[lessonNum]
            classNum = lessonInfo.get("class")
            lessonName = lessonInfo.get("name")
            startTime = lessonInfo.get("startTime")
            endTime = lessonInfo.get("endTime")

            string += ("<b>" if startTime <= currentTime <= endTime else "") + f"Урок №{lessonNum} - {lessonName}, у {classNum}-ому класі.\n"
            string += f"\t- Початок: {startTime.strftime('%H:%M')}\n"
            string += f"\t- Кінець:  {endTime.strftime('%H:%M')}" + ("</b>" if startTime <= currentTime <= endTime else "") + "\n\n"

        return string


class TimetableForStudent(TimetableBase):
    def __init__(self, classNum):
        TimetableBase.__init__(self)
        self.classNum = str(classNum)
        self.SetCurrentDateTime()
        self.holiday  = self.IsHoliday()
    
    
    def GetDailyTimetable(self):        
        if self.holiday in (Holiday.VACATION, Holiday.WEEKENDS):
            self.returnedData = None
            return (self, self.returnedData)
        
        with open(pathes.TIMETABLE_JSON, 'r', encoding = "utf8") as file:
            if timetable := json.load(file).get(f"class{self.classNum}").get(self.currentDay):
                self.returnedData = { key : value for (key, value) in timetable.items() if value is not None }
                return (self, self.returnedData)
    
    
    def GetWeeklyTimatable(self):        
        if self.holiday == Holiday.VACATION and GetSeason(self.currentDate.month) in ("summer", "winter"):
            self.returnedData = None
            return (self, self.returnedData)
        
        with open(pathes.TIMETABLE_JSON, 'r', encoding="utf8") as file:
            if timetable := json.load(file).get("class" + self.classNum):
                for (day, dayTimetable) in timetable.items():
                    timetable[day] = {key: value for (key, value) in dayTimetable.items() if value is not None}
                    for (lesson, lessonName) in timetable[day].items():
                        if "/" in lessonName:  # changing timetable.
                            currentWeek = datetime.now().isocalendar()[1]
                            splitedName = lessonName.split('/')
                            timetable[day][lesson] = splitedName[currentWeek % 2]
        
                self.returnedData = timetable
                return (self, self.returnedData)

    
    def GetTomorrow(self):
        tomorrow = None
        
        if self.holiday == Holiday.VACATION:
            return tomorrow
        
        listOfStudyDays = ["monday", "tuesday", "wednesday", "thursday", "friday"]
        if self.currentDay in listOfStudyDays:
            tomorrow = listOfStudyDays[(listOfStudyDays.index(self.currentDay) + 1) % len(listOfStudyDays)]
        else:
            tomorrow = listOfStudyDays[0]
        
        return tomorrow
    
    
    def PickTomorrowHomework(self):
        tomorrow = self.GetTomorrow()
        
        if not tomorrow:
            if self.holiday == Holiday.VACATION:
                return "Домашнього завдання на канікулах не роблять.)"
            else: 
                return "На жаль, сталася якась помилка."

        ukrNamesOfDay : dict = {
                "monday"    : "Понеділок",
                "tuesday"   : "Вівторок",
                "wednesday" : "Середа",
                "thursday"  : "Четвер",
                "friday"    : "П'ятниця",
            }

        tomorrowTimetabe = None
        with open(pathes.TIMETABLE_JSON, 'r', encoding = "utf8") as file:
            tomorrowTimetabe = json.load(file).get(f"class{self.classNum}").get(tomorrow)

        tomorrowTimetabe = { key : value for (key, value) in tomorrowTimetabe.items() if value is not None }  # remove all non-value pairs
        tomorrowTimetabe = [{"_id": {"lesson": item, "class": int(self.classNum)}} for item in list(tomorrowTimetabe.values())]  # made the filter set for mongoDB

        # TODO: check if hommework is actual.
        homeworks = mongo.homeworks.find({"$or": tomorrowTimetabe})
        
        if not list(homeworks):
            return "Домашньої роботи на завтра не знайдено.)"

        string = f"Домашнє завдання на {ukrNamesOfDay.get(tomorrow).lower()}" + ":\n"
        for homework in homeworks:
            (id, creator, task, when) = homework.values()
            string += "- Предмет: " + id.get("lesson") + ":\n"
            string += "    - Завдання: " + task + "\n"
            string += "    - Створено: " + creator + " " + when
            
        return string
    
    
    def AsString(self):
        if self.returnedData is None:
            if self.holiday == Holiday.WEEKDAYS:
                return "Зараз вихідні, ви не можете переглянути розклад на день."
            else:
                return "Зараз канікули."
        
        elif self.returnedData is not None and self.returnedData.get("monday"):  # We are returning the weekly timetable.
            resultStr : str = str()
            ukrNamesOfDay : dict = {
                "monday"    : "Понеділок",
                "tuesday"   : "Вівторок",
                "wednesday" : "Середа",
                "thursday"  : "Четвер",
                "friday"    : "П'ятниця",
            }
            
            for (dayName, dayTimetable) in self.returnedData.items():
                if self.currentDay == dayName:
                    resultStr += "<b>"
                    
                resultStr += f"{ukrNamesOfDay[dayName]}:\n"
                for (lessonNum, lessonName) in dayTimetable.items():
                    resultStr += f"\t\t{lessonNum}) {lessonName}\n"
                resultStr += "\n"
                
                if self.currentDay == dayName:
                    resultStr += "</b>"
            return resultStr
        
        else:
            resultStr   : str  = str()
            lessonsTime : dict = dict()
            with open(pathes.TIMETABLE_LESSONS_JSON, 'r', encoding = "utf8") as file:
                tempData = json.load(file).get(f"class{self.classNum}")
                for (lessonNum, lessonDurations) in tempData.items():
                    lessonsTime[lessonNum] = {
                        "startTime" : time(lessonDurations.get("startTime").get("hour"), lessonDurations.get("startTime").get("minute")),
                        "endTime"   : time(lessonDurations.get("endTime").get("hour"), lessonDurations.get("endTime").get("minute"))
                    }
            for (lessonNum, lessonName) in self.returnedData.items():
                
                startTime = lessonsTime.get(lessonNum).get("startTime")
                endTime   = lessonsTime.get(lessonNum).get("endTime")

                resultStr += ("<b>" if startTime <= self.currentTime <= endTime else "") + f"{lessonNum}-ий урок - {lessonName}.\n"
                resultStr += f"\t\t- Початок: {startTime.strftime('%H:%M')}\n"
                resultStr += f"\t\t- Кінець:  {endTime.strftime('%H:%M')}" + ("</b>" if startTime <= self.currentTime <= endTime else "") + "\n\n"
            
            return resultStr