from rightmove import Property, Rightmove, minify, database
import peewee
import smtplib
import ssl
from email.message import EmailMessage
import os
import datetime

def updated_record(house):
    id = house.id
    cursor = database.execute_sql(f'SELECT * FROM property WHERE id="{id}";')
    rows = cursor.fetchall()
    if len(rows) == 1:
        price = rows[0][3]
    else:
        return True
    
    if house.price != price:
        return True
    else:
        return False
    
def send_email(message, SUBJECT = None):

    if SUBJECT is None:
        SUBJECT = "Rightmove New Available Properties"

    port = eval(os.environ['SSL_PORT'])  # For SSL
    smtp_server = os.environ['SMTP_SERVER']
    sender_email = os.environ['SENDER_EMAIL']  # Enter your address
    receiver_email = os.environ['RECEIVER_EMAIL']  # Enter receiver address
    password = os.environ['EMAIL_PASSWORD']
    context = ssl.create_default_context()

    msg = EmailMessage()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = SUBJECT
    msg.set_content(message)

    with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
        server.set_debuglevel(False)
        server.login(sender_email, password)
        server.sendmail(sender_email, receiver_email, msg.as_string())
        server.quit()

def search_for_properties(search_params, subject = None):
    Property.create_table(fail_silently=True)

    rightmove = Rightmove(
            user_agent="Yaroslav is looking for a house so fix and amend Kate's scraper"
        )

    message_houses = list()
    for house in rightmove.search(search_params):
            house.description_minified = minify(house.description)

            yes_pls = [minify(y) for y in eval(os.environ['YES_PLS'])]

            no_thx = [minify(n) for n in eval(os.environ['NO_THX'])]

            if any(
                    y in house.description_minified for y in yes_pls
            ) and not any(
                n in house.description_minified for n in no_thx
            ):
                house.favourite = True

            if house.favourite and updated_record(house):
                try:
                    house.save(force_insert=True)
                    database.commit()
                except peewee.IntegrityError as e:
                    pass

                out = "{} / {} - {}".format(house.title, house.price, house.link)
                message_houses.append(house)

    if len(message_houses) > 0:
        message = "\n".join(["{} / {} - {}".format(house.title, house.price, house.link) for house in message_houses])

        send_email(message, subject)

class Search(peewee.Model):
    location = peewee.CharField(primary_key=True)
    datetime = peewee.DateField()

    class Meta:
        database = database

def maxDaysSinceAdded(locationIdentifier):

    cursor = database.execute_sql(f'SELECT * FROM search WHERE location="{locationIdentifier}";')
    rows = cursor.fetchall()
    if len(rows) == 1:
        date = rows[0][1]
    else:
        return ''
    
    time_delta = datetime.datetime.now() - datetime.datetime.fromisoformat(date)

    if time_delta.days <= 1:
        return '1'
    elif time_delta.days <= 3:
        return '3'
    elif time_delta.days <= 7:
        return '7'
    elif time_delta.days <= 14:
        return '14'
    else: ''

def prepare_search_parameters():

    Search.create_table(fail_silently=True)

    search_params = eval(os.environ['SEARCH_PARAMS'])

    locationIdentifier = search_params['locationIdentifier']
    locationIdentifier = [location.replace("%5E","^") for location in locationIdentifier]
    locationName = search_params['locationName']

    search_params.pop('locationName')

    for name, identifier in zip(locationName, locationIdentifier):

        now = datetime.datetime.now()

        search = Search(
            location = identifier,
            datetime = now
        )

        search_params['maxDaysSinceAdded'] = maxDaysSinceAdded(identifier)

        search_params['locationIdentifier'] = identifier

        search_for_properties(search_params, "Rightmove New Available Properties in " + name)

        try:
            search.save(force_insert=True)
            database.commit()
        except peewee.IntegrityError as e:
            pass