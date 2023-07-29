import time
from scripts.classes.followLesson import FollowLesson

while True:
    time.sleep(5)
    print(FollowLesson(8).GetCurrentLesson())