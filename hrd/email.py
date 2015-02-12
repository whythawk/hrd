import smtplib
from email.mime.text import MIMEText

def send_email(recipient, subject, content):
    sender = 'noreply@hrdrelocation.eu'
    msg = MIMEText(content, 'plain', 'utf-8')
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = recipient

    # Send the message via our own SMTP server, but don't include the
    # envelope header.
    s = smtplib.SMTP('localhost')
    s.sendmail(sender, [recipient], msg.as_string())
    s.quit()
