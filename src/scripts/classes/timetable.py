import json
import pytz
from datetime import time, datetime
import scripts.tools.pathes as pathes


class TimetableForTeacher:
    def __init__(self, lastName, firstName, fatherName):
        self.userInfo = dict()
        
        with open(pathes.TEACHERS_JSON, "r", encoding = "utf8") as file:
            teachers = json.load(file)
            for teacher in teachers:
                if teacher.get("lastName") == lastName and teacher.get("firstName") == firstName and teacher.get("fatherName") == fatherName:
                    self.userInfo = teacher
                    break
    
    
    def GetTimetable(self):
        currentDay = datetime.now(pytz.timezone('Europe/Kiev')).strftime('%A').lower()

        self.returnedData : dict = dict()
        if currentDay not in ("monday", "tuesday", "wednesday", "thursday", "friday"):
            self.returnedData = None
            return (self.returnedData, self)
        for (name, classArr) in self.userInfo.get("subjects").items():
            with open(pathes.TIMETABLE_JSON, "r", encoding = "utf8") as file:
                timetableInfo = json.load(file)
                for classItem in classArr:
                    if timetableInfo.get(f"class{classItem}"):
                        currentTimetable = timetableInfo.get(f"class{classItem}").get(currentDay)
                        for (lessonNum, lessonName) in currentTimetable.items():
                            if name == lessonName:
                                with open(pathes.TIMETABLE_LESSONS_JSON, "r", encoding = "utf8") as file:
                                    lessonTime = json.load(file).get(f"class{classItem}").get(lessonNum)
                                    startTime  = lessonTime.get("startTime")
                                    endTime    = lessonTime.get("endTime")

                                    self.returnedData[lessonNum] = {
                                        "class"     : classItem,
                                        "name"      : lessonName,
                                        "startTime" : time(startTime.get("hour"), startTime.get("minute")),
                                        "endTime"   : time(endTime.get("hour"), endTime.get("minute"))
                                    }

        return (self.returnedData, self)
    
    
    def AsString(self):
        if not self.returnedData:
            return "Сьогодні заннять немає."
        
        string = str()
        currentTime = currentTime  = datetime.now(pytz.timezone('Europe/Kiev')).time()

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
