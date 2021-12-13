import json
import os
import re
import glob

from bs4 import BeautifulSoup
from urllib.request import urlopen

import eternal.card


def text2int(textnum, numwords={}):
    """Convert text words into an integer.

    Source: https://stackoverflow.com/questions/493174/is-there-a-way-to-convert-number-words-to-integers"""
    if not numwords:
        units = [
            "zero", "one", "two", "three", "four", "five", "six", "seven", "eight",
            "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen",
            "sixteen", "seventeen", "eighteen", "nineteen",
        ]

        tens = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]

        scales = ["hundred", "thousand", "million", "billion", "trillion"]

        numwords["and"] = (1, 0)
        for idx, word in enumerate(units):    numwords[word] = (1, idx)
        for idx, word in enumerate(tens):     numwords[word] = (1, idx * 10)
        for idx, word in enumerate(scales):   numwords[word] = (10 ** (idx * 3 or 2), 0)

    current = result = 0
    for word in textnum.split():
        if word not in numwords:
            raise Exception("Illegal word: " + word)

        scale, increment = numwords[word]
        current = current * scale + increment
        if scale > 100:
            result += current
            current = 0

    return result + current


def scrape_dwd_draft_pack_boosted_rates(url='https://www.direwolfdigital.com/news/draft-packs-card-list/'):
    """Scrape the web for Draft Pack boosted rates

    Args:
        url: url to the DWD draft pack boost rate table

    Returns: Cards lookup dictionary (keyed on card.id) with boosted rates attached
    """

    page = urlopen(url)
    html = page.read().decode("utf-8")
    soup = BeautifulSoup(html, "html.parser")

    # Get the boosting rates
    boosted_rates = soup(text=re.compile('This card appears in draft packs'))
    boosting_lookup = {}
    for text in boosted_rates:
        items = text.split(' ')
        asterisk_count = text.count('*')
        boosting_lookup[asterisk_count] = text2int(items[items.index('times') - 1])
    if 0 not in boosting_lookup:
        boosting_lookup[0] = 1

    # Get the tables
    tables = [x for x in soup.find_all('table') if x.find('thead')]

    card_boost_lookup = {}
    for table in tables:
        table_headings = [x.text.strip() for x in table.find_all('th')]
        assert table_headings in [['Name', 'Type', 'Subtype', 'Cost', 'Influence', 'Rarity'],
                                  ['Name', 'Type', 'Subtype', 'Cost', 'Influence', 'Weighted Rarity']]
        for row in table.find('tbody').find_all('tr'):
            values = [x.text.strip() for x in row.find_all('td')]

            name = values[0]
            matched_cards = eternal.card.ALL.data[eternal.card.ALL.data.Name == name]
            assert len(matched_cards) == 1
            card_id = matched_cards.index[0]

            rarity = values[5]
            asterisk_count = rarity.count('*')
            card_boost_lookup[card_id] = boosting_lookup[asterisk_count]
    return card_boost_lookup

def scrape_fandom_draft_pack_boosted_rates( url='https://eternalcardgame.fandom.com/wiki/Module:Data/Draft_Packs/2021-11-11' ):
    """Scrape the Fandom hosted boosting data found on:
    https://eternalcardgame.fandom.com/wiki/Special:PrefixIndex/Module:Data/Draft_Packs
    (Thanks Pusillanimous!)

    Args:
        url: URL to fandom website

    Returns: Cards lookup dictionary (keyed on card.id) with boosted rates attached
    """
    page = urlopen(url)
    html = page.read().decode("utf-8")
    soup = BeautifulSoup(html, "html.parser")

    card_boost_lookup = {}
    span_data = soup.find_all("span", {"class": "s2"})
    for name_data, boost_data in zip( span_data[::2], span_data[1::2]):
        name = name_data.text.replace('"','').strip()

        matched_cards = eternal.card.ALL.data[eternal.card.ALL.data.Name == name]
        assert len(matched_cards) == 1
        card_id = matched_cards.index[0]

        boosting_rate = int(boost_data.text.replace('"','').strip())

        card_boost_lookup[card_id] = boosting_rate
    return card_boost_lookup


class DraftFormat:
    """
    Class to encompass a single draft format which helps list the set of cards in the draft packs, boosting rates etc.
    """


    def __init__(self):
        self.set = None
        self.iteration = None
        self.version = None
        self.startdate = None
        self.enddate = None
        self.boosting = None

    def load_json(self, json_path):
        """Load data from custom JSON format. """
        with open(json_path, 'r') as fin:
            filedata = json.load(fin)
            self.iteration = filedata['iteration']
            self.set = filedata['set']
            self.version = filedata['version']
            self.boosting = filedata['boosting']
            self.startdate = filedata['startdate']
            self.enddate = filedata['enddate']

    def save_json(self, json_path):
        """Save data to custom JSON format."""
        with open(json_path, 'w') as fout:
            filedata = dict(
                set=self.set,
                iteration=self.iteration,
                version=self.version,
                startdate=self.startdate,
                enddate=self.enddate,
                boosting=self.boosting
            )
            json.dump( filedata, fout, indent=2 )
    def __repr__(self):
        r = f"Format {self.version} ({self.startdate} - {self.enddate})"
        return r

class DraftFormatMatcher():
    """Class for holding a set of draft formats to assist with matching decks and determining their format.
    """
    BOOSTING_DATA_DIR = os.path.join(os.path.dirname(__file__), 'boosting_data')

    def __init__(self, setnum=12 ):
        self.formats = {}
        for filepath in glob.glob( os.path.join( self.BOOSTING_DATA_DIR, f"{setnum}*.json")):
            d = DraftFormat()
            d.load_json(filepath)
            self.formats[ d.version  ] = ( d )



