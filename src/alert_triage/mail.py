import subprocess
from email.message import EmailMessage
from email.utils import formatdate, make_msgid


class Mailer:
    """Sends through the host's msmtp. The From header and the envelope sender must both be the relay account."""

    def __init__(self, sender, to, command=('msmtp', '-t')):
        self.sender = sender
        self.to = to
        self.command = tuple(command) + ('-f', sender)

    def send(self, subject, body):
        message = EmailMessage()
        message['From'] = self.sender
        message['To'] = self.to
        message['Subject'] = subject
        message['Date'] = formatdate(localtime=True)
        message['Message-ID'] = make_msgid(domain='alert-triage')
        message['Auto-Submitted'] = 'auto-generated'
        message.set_content(body)
        subprocess.run(self.command, input=message.as_bytes(), check=True, timeout=30)
