import smtplib
import scripts.tools.config as config
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


class Email:
    def __init__(self):
        self.senderEmail     = config.EMAIL
        self.senderPassword  = config.EMAIL_PASSWORD
        self.smtpServer      = "smtp.gmail.com"
        self.smtpPort        = 587
        self.imapServer      = "imap.gmail.com"
        self.imapPort        = 993

    def Send(self, recipientEmail: str, title: str, body: str):
        smtpUsername = self.senderEmail
        smtpPassword = self.senderPassword
        
        server = smtplib.SMTP(self.smtpServer, self.smtpPort)
        server.starttls()
        server.login(smtpUsername, smtpPassword)
        
        msg = MIMEMultipart()
        msg['From'] = self.senderEmail
        msg['To'] = recipientEmail
        msg['Subject'] = title

        msg.attach(MIMEText(body, 'plain'))

        server.send_message(msg)
        server.quit()

