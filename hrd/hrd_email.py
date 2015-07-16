import smtplib
from email.mime.text import MIMEText

from hrd import config

def send_email(recipient, subject, content, sender):
    msg = MIMEText(content, 'plain', 'utf-8')
    if hasattr(config, 'EMAIL_ENABLED') and not config.EMAIL_ENABLED:
        print 'EMAIL:'
        print msg.as_string()
        return
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = recipient

    # Send the message via our own SMTP server, but don't include the
    # envelope header.
    s = smtplib.SMTP('localhost')
    s.sendmail(sender, [recipient], msg.as_string())
    s.quit()
