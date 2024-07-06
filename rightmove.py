import re, json, time

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
            links = self.get_item_link_list_func(
                self.get(starting_endpoint, page, params)
            )
            if not links:
                print("Finished searching")
                break
            for link in links:
                yield self.get(link)
            page = page + self.per_page

    def get(self, endpoint, page=0, params={}):
        time.sleep(2) #Try to avoid rate limiting

        print("Getting " + endpoint)
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
            #r.raise_for_status()
            break
        return r.text

class Rightmove:
    def __init__(self, user_agent):
        self.params = {
            'locationIdentifier': '',
            'minPrice': '',
            'maxPrice': '',
            'minBedrooms': '',
            'propertyTypes': 'detached,semi-detached,terraced',
            'includeSSTC': 'false',
            'dontShow': 'retirement',
        }
        self.endpoint = "https://www.rightmove.co.uk"
        self.endpoint_search = "/property-for-sale/find.html"

        self.scraper = SearchScraper(
            page_param="index",
            per_page=10,
            get_item_link_list_func=lambda html: set([
                self.endpoint + x['href'] for x in
                BeautifulSoup(html, "html.parser").find_all(
                    "a",
                    attrs={'class': 'propertyCard-link'}
                ) if x['href']
            ]),
            user_agent=user_agent
        )
    
    def get_area(self, text):
        nums = re.findall(r'\d+', text)
        if len(nums) == 0 or int(nums[0]) < 1:
            return 0
        return int(nums[0]) / 10.764

    def search(self, params={}):
        merged_params = self.params.copy()
        merged_params.update(params)
        for property_html in self.scraper.search(
                self.endpoint + self.endpoint_search,
                merged_params,
                True
        ):
            raw_html = property_html.splitlines()
            model_lines = [x.replace('window.PAGE_MODEL =','') for x in raw_html if 'window.PAGE_MODEL =' in x]
            if len(model_lines) == 0:
                raise Exception("No model found");
                    
            dict = json.loads(model_lines[0]);
            reel_items = dict["propertyData"]["infoReelItems"]
            yield Property(
                id=int(dict["propertyData"]["id"]),
                title=dict["propertyData"]["text"]["pageTitle"],
                link=dict["metadata"]["copyLinkUrl"],
                price=dict["propertyData"]["prices"]["primaryPrice"],
                description=dict["propertyData"]["text"]["description"],
                stations=[
                    x["name"].strip().replace("\n", " ") for x in
                    dict["propertyData"]["nearestStations"]
                ],
                images=[
                    x["url"] for x in
                    dict["propertyData"]["images"]
                ],
                bedrooms=reel_items[1]["primaryText"] if len(reel_items) >= 2 else "",
                bathrooms=reel_items[2]["primaryText"] if len(reel_items) >= 3 else "",
                area=self.get_area(reel_items[3]["primaryText"] if len(reel_items) >= 4 else "0"),
                tenure=dict["propertyData"]["tenure"]["tenureType"],
                property_type=dict["propertyData"]["propertySubType"],
                address=dict["propertyData"]["address"]["displayAddress"],
                post_code=dict["propertyData"]["address"]["outcode"]
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
    bedrooms = peewee.CharField()
    bathrooms = peewee.CharField()
    area = peewee.CharField()
    tenure = peewee.CharField()
    property_type = peewee.CharField()
    address = peewee.CharField()
    post_code = peewee.CharField()

    class Meta:
        database = database

def minify(text):
    return re.sub('[^0-9a-zA-Z]+', '', text).lower()


if __name__ == "__main__":
    print("Starting house search...")

    Property.create_table(fail_silently=False)

    rightmove = Rightmove(
        user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    )

    # This is used to favourite a property. Favourite means a column in a table, unrelated to RightMove feature
    yes_pls = [
        'conservatory',
        'garage',
        'workshop',
        'balcony',
    ]

    # This is used to filter out a property if it has any of these words in the description
    no_thx = [
        'AUCTION',
        'auction'
    ]

    for house in rightmove.search({
            "radius": "0.0",            
            'locationIdentifier': 'REGION^93917',
            'minPrice': '300000',
            'maxPrice': '400000',
            'minBedrooms': '3'}):
        house.description_minified = minify(house.description)

        if any(n in house.description_minified for n in no_thx):
            continue

        house.favourite = any(y in house.description_minified for y in yes_pls)

        try:
            house.save(force_insert=True)
            database.commit()
        except peewee.IntegrityError as e:
            pass

        out = "{} / {} - {}/{} {}".format(house.title, house.price, house.bedrooms,house.bathrooms, house.area)
        print(out)



