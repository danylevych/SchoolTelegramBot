import pytz
import json
import asyncio
from datetime import time, datetime
import scripts.tools.pathes as pathes

def GetSeason(month):
    if 3 <= month <= 5:
        return "spring"
    elif 6 <= month <= 8:
        return "summer"
    elif 9 <= month <= 11:
        return "autumn"
    else:
        return "winter"
    
# This class privide access to cutrently timetable for some school class.
class FollowLesson:
    def __init__(self, wichClass: int):
        self.wichClass = str(wichClass)
        self.timetableLessons = dict()
        self.currentDate = datetime.now(pytz.timezone('Europe/Kiev'))
        self.currentDay = "monday" # self.currentDate .strftime('%A').lower()
        
        with open(pathes.TIMETABLE_LESSONS_JSON, "r") as file:
            tempData = json.load(file)[f"class{self.wichClass}"]
            for (numLesson, period) in tempData.items():
                self.timetableLessons[numLesson] = {
                    "startTime": time(period["startTime"]["hour"], period["startTime"]["minute"]),
                    "endTime"  : time(period["endTime"]["hour"], period["endTime"]["minute"])
                }
    
    
    def FindLastLesson(self):
        lastLesson = None
        
        # with open(pathes.VACATION_JSON, "r", encoding="utf8") as file:
        #     if seasonVacation := json.load(file)[GetSeason(self.currentDate.month)]:
        #         dateFormat = "%d.%m.%Y"
        #         startVacation = datetime.strptime(seasonVacation.get("startVacation"), dateFormat)
        #         endVacation = datetime.strptime(seasonVacation.get("endVacation"), dateFormat)
                
        #         timezone = pytz.timezone("Europe/Kiev")
        #         startVacation = timezone.localize(startVacation)
        #         endVacation = timezone.localize(endVacation)

        #         if startVacation <= self.currentDate <= endVacation:
        #             return None
        
        if self.currentDay in ("monday", "tuesday", "wednesday", "thursday", "friday"):
            with open(pathes.TIMETABLE_JSON, "r", encoding = "utf8") as file:
                dayTimeTable = json.load(file)[f"class{self.wichClass}"][self.currentDay]
                lastLesson = dayTimeTable.items()
                for item in dayTimeTable:
                    if dayTimeTable[item] is not None:
                        lastLesson = item
        return lastLesson
    
    
    def GetCurrentLesson(self):
        currentTime = time(12, 25) # datetime.now(pytz.timezone('Europe/Kiev')).time()

        
        firstLesson = '1'
        lastLesson = self.FindLastLesson()

        if lastLesson is None:  # We have a holiday.
            return {
                "requestTime": currentTime,
                "isBreak": False,
                "isHoliday": True,
                "infoLesson": None
            }

        # Current time has plased in borders from first lesson start time to last lesson end time.
        if self.timetableLessons[firstLesson]["startTime"] <= currentTime <= self.timetableLessons[lastLesson]["endTime"]:
            for (numLesson, period) in self.timetableLessons.items():
                if period["startTime"] <= currentTime <= period["endTime"]:
                    with open(pathes.TIMETABLE_JSON, "r", encoding="utf8") as file:
                        name = json.load(file)[f"class{self.wichClass}"][self.currentDay][numLesson]
                        
                        if "/" in name:  # changing timetable.
                            current_week = datetime.now().isocalendar()[1]
                            splitedName = name.split('/')
                            name = splitedName[current_week % 2]
                            
                        return {
                            "requestTime"   : currentTime,
                            "isBreak"       : False,
                            "isHoliday"     : False,
                            "infoLesson"    : {
                                    "name"      : name,
                                    "startTime" : period["startTime"],
                                    "endTime"   : period["endTime"]
                                }
                            }

            if nextLesson := self.GetNextLesson(currentTime):
                return {
                        "requestTime"   : currentTime,
                        "isBreak"       : True,
                        "isHoliday"     : False,
                        "infoLesson"    : {
                            "name"      : nextLesson[0],
                            "startTime" : nextLesson[2],
                            "endTime"   : self.timetableLessons[nextLesson[1]]["endTime"]
                        }
                    }

        return None  # The study day has ended.


    def GetNextLesson(self, time):
        """
        [0] - name
        [1] - order number
        [2] - start time
        """
        nextStartTime = None
        for (numLesson, period) in self.timetableLessons.items():
            if period["startTime"] > time:
                nextStartTime = period["startTime"]
                with open(pathes.TIMETABLE_JSON, "r", encoding = "utf8") as file:
                    name = json.load(file)[f"class{self.wichClass}"][self.currentDay][numLesson]
                return (name, numLesson, nextStartTime)
    
    
    async def GetCurrentLessonAsync(self):  # Use only for async functions. 
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.GetCurrentLesson)