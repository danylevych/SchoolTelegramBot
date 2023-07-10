import sys
import pytz
import json
import asyncio
from datetime import time, datetime
sys.path.append("src/scripts/tools/")
import pathes


# This class privide access to cutrently timetable for some school class.
class FollowLesson:
    def __init__(self, wichClass: int):
        self.wichClass = str(wichClass)
        self.timetableLessons = dict()
        self.currentDay = datetime.now(pytz.timezone('Europe/Kiev')).strftime('%A').lower()
        
        with open(pathes.TIMETABLE_LESSONS_JSON, "r") as file:
            import json
            tempData = json.load(file)["class" + self.wichClass]
            for (numLesson, period) in tempData.items():
                self.timetableLessons[numLesson] = {
                    "startTime": time(period["startTime"]["hour"], period["startTime"]["minute"]),
                    "endTime": time(period["endTime"]["hour"], period["endTime"]["minute"])
                }
    
    
    def FindLastLesson(self):
        lastLesson = None
        if self.currentDay in ("monday", "tuesday", "wednesday", "thursday", "friday"):
            
            with open(pathes.TIMETABLE_JSON, "r", encoding="utf8") as file:
                dayTimeTable = json.load(file)["class" + self.wichClass][self.currentDay]
                lastLesson = dayTimeTable.items()
                for item in dayTimeTable:
                    if dayTimeTable[item] is not None:
                        lastLesson = item
        return lastLesson
    
    
    def GetCurrentLesson(self):
        """
        This method returns the set of data represented in the following format:
        "requestTime"           - the time when the request was created.
        "isBreak"               - Is it currently a break?
        "isHoliday"             - Is today a holiday?
        "infoLesson"            - the info about the current lesson.
                "name"          - name of the lesson.
                "startTime"     - starting time of the lesson.
                "endTime"       - ending time of the lesson.
        If the study day has ended, it returns None.
        """

        currentTime = datetime.now(pytz.timezone('Europe/Kiev')).time()

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
                        name = json.load(file)["class" + self.wichClass][self.currentDay][numLesson]

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

            # If it's a break, find the next lesson
            nextLesson = self.GetNextLesson(currentTime)
            if nextLesson:
                return {
                        "requestTime"   : currentTime,
                        "isBreak"       : True,
                        "isHoliday"     : False,
                        "infoLesson"    : {
                            "name"      : nextLesson[0],
                            "startTime" : nextLesson[1],
                            "endTime"   : self.timetableLessons[nextLesson]["endTime"]
                        }
                    }

        return None  # The study day has ended.


    def GetNextLesson(self, time):
        nextLesson = None
        nextStartTime = None
        for (numLesson, period) in self.timetableLessons.items():
            if period["startTime"] > time:
                nextLesson = numLesson
                nextStartTime = period["startTime"]
                break

        if nextLesson:
            with open(pathes.TIMETABLE_JSON, "r", encoding="utf8") as file:
                name = json.load(file)["class" + self.wichClass][self.currentDay][nextLesson]

                return (name, nextStartTime)
    
    
    async def GetCurrentLessonAsync(self):  # Use only for async functions. 
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.GetCurrentLesson)
