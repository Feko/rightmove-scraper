# rightmove-scraper (Yes, another one)

Forked from: [https://github.com/whoiskatrin/rightmove-scraper](https://github.com/whoiskatrin/rightmove-scraper)

## Decription (Original)
rightmove.co.uk is one of the UK's largest property listings websites, hosting thousands of listings of properties for sale and to rent.

rightmove.py is a simple Python interface to scrape property listings to buy or rent from the website and prepare them in a Pandas dataframe with a possibility to email to desired recipient.

## Changes in this version
 - Removed e-mail sending feature, you can find it in the original version.
 - Added 2 seconds delay between requests to avoid throttling.
 - Changed the values exraction from RegEx and DOM Navigation to a JSON-Parsed Dictionary.
 - Changed the search from `Rent` to `Buy`.
 - `no_thx` filter no longer unfavourites a property, but filter it out instead.
 - Added new columns that are important to me:
   - bedrooms
   - bathrooms
   - area
   - tenure (leasehold / freehold)
   - property_type
   - post_code
 - Filters out retirement out by default
 - Filters only houses by default 

## Usage
Tested in Python 3.11. Ensure to have the dependencies installed with `$ pip install -r requirements.txt`

Change the filters as you wish in the end of the file, and run `$ python rightmove.py`. It will take quite a while to run (It takes about 3~4 seconds per property it finds in the list). Once finished, you'll have a `rightmove.db` SQLite for basing your analysis on.
