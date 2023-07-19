import scripts.tools.mongo as mongo


class TeacherSubjects:
    def __init__(self, lastName, firstName, fatherName):
        self.teacher = mongo.teachers.find_one({
            "lastName"  : lastName,
            "firstName" : firstName,
            "fatherName": fatherName
        })
    
    def GetSubjects(self):
        if not self.teacher:
            return None
        return self.teacher.get("subjects")
