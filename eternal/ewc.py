import re
import urllib.parse
from urllib.request import urlopen

from bs4 import BeautifulSoup

import eternal.card
import eternal.deck


def parse_deckbuilder_url(url):
    """Parse a deck-builder URL.
    These URLs are simple as the card-ids are right in the URL and can be used directly

    Args:
        url: Eternal warcry deckbuilder URL

    Returns: Deck object
    """
    market = None
    main_deck = None

    parsed_url = urllib.parse.urlparse(url)
    main_deck = parsed_url.query.split('main=')[1]
    market_cards = None
    if 'market' in main_deck:
        main_deck, market = main_deck.split('&market=')
        market_card_id_counts = market.split(';')[:-1]
        market_cards = []
        for id_count in market_card_id_counts:
            cid, count = id_count.split(':')
            market_cards += [eternal.card.ALL[cid]] * int(count)

    main_card_id_counts = main_deck.split(';')[:-1]
    main_cards = []
    for id_count in main_card_id_counts:
        cid, count = id_count.split(':')
        main_cards += [eternal.card.ALL[cid]] * int(count)

    return eternal.deck.Deck(main_cards, market=market_cards)


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


def scrape_draft_pack_boosted_rates(url='https://www.direwolfdigital.com/news/draft-packs-card-list/'):
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
