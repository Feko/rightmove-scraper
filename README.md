# rightmove-scraper

rightmove.co.uk is one of the UK's largest property listings websites, hosting thousands of listings of properties for sale and to rent.

app/rightmove.py is a simple Python interface to scrape property listings to buy or rent from the website and prepare them in a Pandas dataframe with a possibility to email to desired recipient.

docker-compose.yml builds and runs docker container to scrape property listings for various locations and email them to desired recipient. Script adjusts rightmove property maxDaysSinceAdded automatically and checks if property listing was already scraped so as not to email it twice to the recipient. 