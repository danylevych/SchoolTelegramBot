import scripts.tools.pathes as pathes
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY

pdfmetrics.registerFont(TTFont('LiberationSans', pathes.REGULAR_FONT))
pdfmetrics.registerFont(TTFont('LiberationSansBold', pathes.BOLD_FONT))
pdfmetrics.registerFont(TTFont('LiberationSansItalic', pathes.ITALIC_FONT))
pdfmetrics.registerFont(TTFont('LiberationSansBoldItalic', pathes.BOLD_ITALIC_FONT))


def CreatePDF(notes, filename):
    doc = SimpleDocTemplate(filename, pagesize = letter)

    styles = getSampleStyleSheet()

    title_style = styles['Title']
    title_style.fontName = 'LiberationSansBold'
    title_style.alignment = TA_CENTER
    text_style = styles['Normal']
    text_style.fontName = 'LiberationSans'
    text_style.alignment = TA_JUSTIFY
    italic_style = styles['Italic']
    italic_style.fontName = 'LiberationSansItalic'

    story = []

    for note in notes:
        (id, text, when) = note.values()
        title = id.get("title").upper()
        text_lines = text.split("\n")

        story.append(Paragraph(title, title_style))
        story.append(Spacer(1, 12))

        for line in text_lines:
            story.append(Paragraph(line, text_style))
        story.append(Spacer(1, 12))

        story.append(Paragraph("Створено:" + when, italic_style))

        story.append(Spacer(1, 20))
        story.append(PageBreak())

    doc.build(story)

