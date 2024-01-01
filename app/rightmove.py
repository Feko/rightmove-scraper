import re
import smtplib
import ssl
import json

from bs4 import BeautifulSoup
import requests
import peewee

class SearchScraper:
    def __init__(
            self,
            page_param,
            per_page,
            get_item_link_list_func,
            user_agent,
            start_page=0
    ):
        self.page_param = page_param
        self.per_page = per_page
        self.get_item_link_list_func = get_item_link_list_func
        self.user_agent = user_agent
        self.start_page = start_page

    def search(self, starting_endpoint, params={}, v=False):
        page = int(self.start_page)
        while True:
            print("Processing page {}".format(page))
            html = self.get(starting_endpoint, page, params)
            links = self.get_item_link_list_func(html)
            if not links:
                print("Finished searching")
                break
            for link in links:
                yield self.get(link)
            soup = BeautifulSoup(html, "html.parser")
            pagination = json.loads(re.search('{.*}', soup(text=re.compile(r'window.jsonModel'))[0])[0])['pagination']
            if 'next' in pagination.keys():
                page = int(pagination['next'])
            else:
                break

    def get(self, endpoint, page=0, params={}):
        headers = {
            'User-Agent': self.user_agent
        }
        if page:
            params[self.page_param] = page

        while True:
            try:
                r = requests.get(endpoint, headers=headers, params=params)
            except Exception as e:
                print("Couldn't connect, retrying...")
                continue
            r.raise_for_status()
            break
        return r.text

class Rightmove:
    def __init__(self, user_agent):
        self.params = {
            #'searchType': 'RENT',
            #'locationIdentifier': 'REGION%5E357',
            'insId': '1',
            #'radius': '0.0',
            #'minPrice': '2750',
            #'maxPrice': '3250',
            #'minBedrooms': '2',
            #'maxDaysSinceAdded': '7',
            # 'includeSSTC': 'true',
            # '_includeSSTC': 'on'
        }
        self.endpoint = "http://www.rightmove.co.uk/"
        self.endpoint_rent_search = "property-to-rent/find.html"
        self.endpoint_buy_search = "property-for-sale/find.html"

        self.scraper = SearchScraper(
            page_param="index",
            per_page=10,
            get_item_link_list_func=lambda html: self.get_item_link_list_func(html),
            user_agent=user_agent
        )

    def get_item_link_list_func(self, html):
        soup = BeautifulSoup(html, "html.parser")
        properties = json.loads(re.search('{.*}', soup(text=re.compile(r'window.jsonModel'))[0])[0])['properties']
        return {self.endpoint[:-1] + url['propertyUrl'] for url in properties}

    def search(self, params={}):
        merged_params = self.params.copy()
        merged_params.update(params)
        for property_html in self.scraper.search(
                self.endpoint + (self.endpoint_rent_search if params['searchType']=='RENT' else self.endpoint_buy_search),
                merged_params,
                True
        ):
            soup = BeautifulSoup(property_html, "html.parser")
            propertyDATA = json.loads(re.search('{.*}', soup(text=re.compile(r'window.PAGE_MODEL'))[0])[0])['propertyData']
            yield Property(
                id=int(propertyDATA['id']),
                title=propertyDATA['text']['pageTitle'],
                link="https://www.rightmove.co.uk/properties/" + propertyDATA['id'],
                price=propertyDATA['prices']['primaryPrice'],
                description=propertyDATA['text']['description'],
                stations=[station['name'] for station in propertyDATA['nearestStations']],
                images=[img['url'] for img in propertyDATA['images']]
            )

database = peewee.SqliteDatabase("rightmove.db")

class Property(peewee.Model):
    id = peewee.BigIntegerField(primary_key=True)
    title = peewee.CharField()
    link = peewee.CharField()
    price = peewee.CharField()
    description = peewee.CharField()
    description_minified = peewee.CharField()
    stations = peewee.CharField()
    images = peewee.CharField()
    favourite = peewee.BooleanField(default=False)

    class Meta:
        database = database

def minify(text):
    return re.sub('[^0-9a-zA-Z]+', '', text).lower()


if __name__ == "__main__":
    print("Starting house search...")

    Property.create_table(fail_silently=True)

    rightmove = Rightmove(
        user_agent="Kate is looking for a flat so made her own scraper"
    )

    properties = ""

    SUBJECT = "Rightmove New Available Properties"

    port = 465  # For SSL
    smtp_server = "smtp.gmail.com"
    sender_email = ""  # Enter your address
    receiver_email = ""  # Enter receiver address
    password = ""

    context = ssl.create_default_context()

    for house in rightmove.rental_search({"radius": "0.0"}):
        house.description_minified = minify(house.description)

        yes_pls = [
            'underfloor',
            'stunning',
            'wooden floor',
            'balcony',
            'terrace',
            'loft'
        ]

        no_thx = [
            'groundfloor'
        ]
        if any(
                y in house.description_minified for y in yes_pls
        ) and not any(
            n in house.description_minified for n in no_thx
        ):
            house.favourite = True

        try:
            house.save(force_insert=True)
            database.commit()
        except peewee.IntegrityError as e:
            pass

        out = "{} / {} - {}".format(house.title, house.price, house.link)
        properties = properties + '\n' + "{} - {}".format(house.title, house.link)
        message = 'Subject: {}\n\n{}'.format(SUBJECT, properties)
        if house.favourite:
            out = "OMG! {}".format(out)
            properties = properties + '\n' + "{} - {}".format(house.title, house.link)
            message = 'Subject: {}\n\n{}'.format(SUBJECT, properties)
        print(out)

    with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
        server.login(sender_email, password)
        server.sendmail(sender_email, receiver_email, message)



