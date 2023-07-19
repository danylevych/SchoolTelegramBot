import scripts.tools.mongo as mongo
import re

# students = mongo.students.find()
# if students:
#     for student in students:
#         print(student)
students = mongo.students.find()

print(students)
# def CheckTelegramPassword(password):
#     if len(password) < 8:
#         return False
#     if not any(char.isdigit() for char in password):
#         return False
#     if not any(char.isupper() for char in password):
#         return False
#     return True

# # Example usage:
# telegram_password = "привіт1Р"
# is_valid = CheckTelegramPassword(telegram_password)
# print(is_valid) 