# from scripts.tools.pdfCreator import CreatePDF

# note = {
#     "_id" : {
#         "userID" : 1, 
#         "title" : "Перша нотатка"
#         },
#     "text" : """У цьому оновленому коді я додав c.showPage() після виведення кожного запису, щоб перейти на нову сторінку. Після цього змінив позицію y, щоб почати наступний запис на новій сторінці. Тепер кожен елемент notes буде зберігатися на окремій сторінці.
#                 Щодо вирівнювання тексту, я використовував метод drawCentredString() для центрованого вирівнювання тексту. Зазначений метод виводить текст уздовж горизонтального центру сторінки. Я також змінив позиції y для кожного елементу notes, щоб додати відстань між ними.""",
#     "when" : "сьогодні"
#     }

# CreatePDF([note, note, note], "result.pdf")

from scripts.classes.timetable import TimetableForStudent

print(TimetableForStudent(2).GetWeeklyTimatable()[0].AsString())



