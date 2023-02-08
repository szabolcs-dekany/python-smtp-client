import logging
import os
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

DEFAULT_SMTP_PORT = 587
DEFAULT_TIMEOUT = 30
SMTP_OK_STATUS_CODE = 250


def get_environment_variable(env_variable):
    return os.getenv(env_variable)


class EmailSender:

    def raise_exception(self, message):
        raise Exception(message)

    def add_attachments(self, message, attachments=None):
        for attachment in attachments or []:
            base_name = os.path.basename(attachment.strip())
            try:
                attachment_part = MIMEApplication(open(attachment, "rb").read())
                attachment_part.add_header('Content-Disposition', 'attachment', filename=base_name)
                message.attach(attachment_part)
            except FileNotFoundError:
                self.raise_exception(f'Failed to add an attachment. No such file {base_name}')

    def get_configuration(self):
        logging.info('Reading configuration...')
        username = get_environment_variable('USERNAME') or self.raise_exception(
            'USERNAME variable not set! Stopping...')
        password = get_environment_variable('PASSWORD') or self.raise_exception(
            'PASSWORD variable not set! Stopping...')
        from_email = get_environment_variable('FROM') or self.raise_exception('FROM variable not set! Stopping...')
        to_email = get_environment_variable('TO') or self.raise_exception('TO variable not set! Stopping...')
        host = get_environment_variable('HOST') or self.raise_exception('HOST variable not set! Stopping...')
        attachments = get_environment_variable('ATTACHMENTS')

        port = get_environment_variable('PORT') or DEFAULT_SMTP_PORT
        use_tls = get_environment_variable('TLS') or True

        timeout = get_environment_variable('TIMEOUT') or DEFAULT_TIMEOUT

        return {'username': username, 'password': password, 'from_email': from_email, 'to_email': to_email,
                'host': host,
                'attachments': attachments, 'port': port, 'use_tls': use_tls, 'timeout': timeout}

    def run(self):
        configuration = self.get_configuration()
        subject = get_environment_variable('SUBJECT') or self.raise_exception('SUBJECT variable not set! Stopping...')

        body_plain = get_environment_variable('BODY_PLAIN')
        body_html_filename = get_environment_variable('BODY_HTML')
        body_html = body_plain

        if body_html_filename is not None:
            try:
                base_name = os.path.basename(body_html_filename.strip())
                with open(base_name, 'r') as f:
                    body_html = f.read()
            except FileNotFoundError as e:
                self.raise_exception("Unable to open HTML body file! Stopping...")

        if body_plain is None and body_html is None:
            self.raise_exception('BODY_PLAIN or BODY_HTML variable not set! Stopping...')

        msg = MIMEMultipart('alternative')
        msg['FROM'] = configuration.get('from_email')
        msg['TO'] = configuration.get('to_email')
        msg['Subject'] = subject

        part1 = MIMEText(body_plain, 'plain', _charset='utf-8')
        part2 = MIMEText(body_html, 'html', _charset='utf-8')

        logging.info(body_html)

        msg.attach(part1)
        msg.attach(part2)

        if configuration.get('attachments') is not None:
            self.add_attachments(msg, configuration.get('attachments').split(','))

        self.send_email(msg, configuration.get('username'), configuration.get('password'), configuration.get('host'),
                        configuration.get('port'), configuration.get('use_tls'), configuration.get('timeout'),
                        configuration.get('to_email'))

    def send_email(self, msg, username, password, host, port, use_tls, timeout, to_email):
        logging.info('Sending email...')

        result = None

        try:
            smtp = smtplib.SMTP(host, port, timeout=timeout)
            smtp.ehlo()
            if use_tls:
                smtp.starttls()
                smtp.ehlo()
            smtp.login(username, password)
            smtp.send_message(msg)
            result = smtp.noop()
            smtp.quit()
        except OSError as e:
            self.raise_exception('Failed to send email. Check your configuration! Stopping...')

        if result is None or result[0] != SMTP_OK_STATUS_CODE:
            self.raise_exception('Failed to send email to %s! response %s.' % (to_email, result))

        logging.info('Email sent!')


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    email_sender = EmailSender()
    email_sender.run()
