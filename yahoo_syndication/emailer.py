from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os
import smtplib


class SendingEmailException(Exception):
    pass


def generate_email(subject, from_name, from_address, to_address, html):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{from_name} <{from_address}>"
    msg["To"] = to_address
    msg.attach(MIMEText(html, "html"))
    return msg.as_string()


def generate_body(articles):
    tmpl = """<p>Hi there,</p>
<p>The following Full Fact article{s} {waswere} recently syndicated to Yahoo!:</p>
<ul>
{articles_html}
</ul>
"""
    articles_html = "\n".join([
        """<li><a href="{url}">{title}</a></li>""".format(
            url=article["url"],
            title=article["title"],
        )
        for article in articles
    ])

    return tmpl.format(
        s="" if len(articles) == 1 else "s",
        waswere="was" if len(articles) == 1 else "were",
        articles_html=articles_html,
    )


def send_email(
    articles,
    from_address,
    from_pwd,
    to_addresses,
    smtp_server,
    smtp_port,
):
    from_name = "Full Fact"

    email_subject = (
        "A Full Fact article was recently syndicated"
        if len(articles) == 1
        else "Some Full Fact articles were recently syndicated"
    )

    msg = generate_email(
        email_subject,
        from_name,
        from_address,
        to_addresses,
        generate_body(articles),
    )

    with smtplib.SMTP_SSL(smtp_server, smtp_port) as s:
        s.login(from_address, from_pwd)
        try:
            errs = s.sendmail(from_address, to_addresses.split(","), msg)
            if errs:
                raise SendingEmailException()
        except smtplib.SMTPException as e:
            raise SendingEmailException() from e
