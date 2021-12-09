import re

import urllib.parse
from bs4 import BeautifulSoup
from urllib.request import urlopen

import eternal.card
import eternal.deck


def parse_v2_cards(cardstring):
    """Extract card objects from a v2 url encoded list of cards

    Args:
        cardstring: Deckbuilder card string (multiple cards)

    Returns: List of Card objects


    Note: Card string is a concatenate (with no delimiter) set of 3-4 characters with the the format:

    XYZ
    X = card_count (B=1, C=2, D=3, E=4)
    Y = set_number (B=1, C=2, ... M=12)
    Z = eternal_id: (B=1, C=2, ... Z --> a ... f  --> [  gX ... zX --> 0X ... 9X --> -X --> _X  ]  repeating with X == B, C, D etc.)
    """
    cards = []
    ix_card = 0
    while ix_card <= (len(cardstring) - 3):
        count = None
        set_number = None
        eternal_id = None
        x, y, z = cardstring[ix_card:(ix_card + 3)]
        count = parse_v2_cards.CARD_COUNT_LOOKUP[x]
        set_number = parse_v2_cards.SET_NUMBER_LOOKUP[y]

        if z in parse_v2_cards.ETERNAL_ID_1CHAR_LOOKUP:
            eternal_id = parse_v2_cards.ETERNAL_ID_1CHAR_LOOKUP[z]
            ix_card += 3
        else:
            z_repeat = z
            z_multiply = cardstring[ix_card + 3]
            eternal_id = parse_v2_cards.ETERNAIL_ID_2CHAR_REPEATING.index(z_repeat) \
                         + len(parse_v2_cards.ETERNAIL_ID_2CHAR_REPEATING) * (ord(z_multiply) - ord('B')) \
                         + len(parse_v2_cards.ETERNAL_ID_1CHAR_LOOKUP) + 1
            ix_card += 4
        cid = f"{set_number}-{eternal_id}"
        cards += [eternal.card.ALL[cid]] * int(count)
    return cards


# Initialize the static lookup tables
parse_v2_cards.CARD_COUNT_LOOKUP = dict([(x, i + 1) for i, x in enumerate('BCDEFGHIJKLMNOPQRSTUVWXYZ')])
parse_v2_cards.SET_NUMBER_LOOKUP = dict([(x, i ) for i, x in enumerate('ABCDEFGHIJKLM')])
parse_v2_cards.ETERNAL_ID_1CHAR_LOOKUP = dict([(x, i + 1) for i, x in enumerate('BCDEFGHIJKLMNOPQRSTUVWXYZabcdef')])
parse_v2_cards.ETERNAIL_ID_2CHAR_REPEATING = 'ghijklmnopqrstuvwxyz0123456789-_'


def parse_deckbuilder_url_v2(url):
    """Parse a deck-builder v2 URL 

    This format was updated in November 2021 was used starting with the Set 12 7-win sheet.

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
        market_cards = parse_v2_cards(market)

    main_cards = parse_v2_cards(main_deck)
    return eternal.deck.Deck(main_cards, market=market_cards)


def parse_deckbuilder_url_v1(url):
    """Parse a deck-builder v1 URL 

    This format existed prior to change in November 2021 and was last used for the Set 11 7-win sheets.
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


def parse_deckbuilder_url(url):
    """Parse a deck-builder URL (supports both v1 and v2 urls)

    Args:
        url: Eternal warcry deckbuilder URL

    Returns: Deck object
    """
    parsed_url = urllib.parse.urlparse(url)
    main_deck = parsed_url.query.split('main=')[1]
    if ':' in main_deck:
        return parse_deckbuilder_url_v1(url)
    else:
        return parse_deckbuilder_url_v2(url)


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
