import random

class PhrasesGenerator:
    def __init__(self, lessonName : str, path : str):
        self.lessonName = lessonName
        self.phrasers   = list()
        try:
            with open(path, "r", encoding = "utf8") as file:
                self.phrasers = file.readlines()
        except Exception as e:
            self.phrasers.append("Не забудь! Урок з '{}' розпочався! Приєднуйтесь зараз, щоб не пропустити нічого важливого.")
            print("Some trubles", e)
    
    def GetRandomPhrase(self) -> str:
        return self.phrasers[random.randint(0, len(self.phrasers))].format(self.lessonName)
