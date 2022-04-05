import glob
import json
import os
import re

import pandas as pd
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


def scrape_fandom_draft_pack_boosted_rates(url='https://eternalcardgame.fandom.com/wiki/Module:Data/Draft_Packs/2021-11-11'):
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
    for name_data, boost_data in zip(span_data[::2], span_data[1::2]):
        name = name_data.text.replace('"', '').strip()

        matched_cards = eternal.card.ALL.data[eternal.card.ALL.data.Name == name]
        assert len(matched_cards) == 1
        card_id = matched_cards.index[0]

        boosting_rate = int(boost_data.text.replace('"', '').strip())

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

        # Calculated fields
        self._offer_rates = None

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

        self._offer_rates = self._calculate_offer_rates()

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
            json.dump(filedata, fout, indent=2)

    def __repr__(self):
        r = f"Format {self.version} ({self.startdate} - {self.enddate})"
        return r

    def _calculate_offer_rates(self):
        """Calculate expected card count in a draft for cards in the format.

        Factors in card rarity and boosting rates.

        Multiple sources on reddit claim this is somwhere between 1/10 and 1/11.
        Ultimately I went with 3/32 as claimed in this thread:
            https://www.reddit.com/r/EternalCardGame/comments/76lu9b/comment/dofjzuv/

        Returns: Pandas series
            index - card-id (e.g. 12-1)
            value - offer rate, the expected count of this card in a draft (2 packs from the set and 2 packs from the draft packs)
        """
        PACK_CARD_COUNT_BY_RARITY = {'Common': 8.0, 'Uncommon': 3.0, 'Rare': 29 / 32.0, 'Legendary': 3 / 32.0}
        ALL_CARD_DATA = eternal.card.ALL.data

        # Determine weighted probability of picking a card (within their rarity)
        # For current set cards, this assumes that all cards are equally likely
        currentset_cards = ALL_CARD_DATA[ALL_CARD_DATA['SetNumber'] == self.set].copy()
        currentset_cards['Boosting'] = 1.0
        currentset_rarity_counts = currentset_cards.groupby('Rarity')['Boosting'].sum()
        currentset_rarity_counts.drop('Promo', inplace=True, errors='ignore')
        currentset_cards['BoostedFreq'] = currentset_cards['Boosting'] / currentset_cards['Rarity'].map(currentset_rarity_counts)

        # For draft pack cards, this pick probability is where the draft-pack boost rates come into play
        draft_pack_cards = ALL_CARD_DATA.loc[self.boosting.keys()].copy()
        draft_pack_cards['Boosting'] = draft_pack_cards.index.map(self.boosting)
        draft_pack_rarity_counts = draft_pack_cards.groupby('Rarity')['Boosting'].sum()
        draft_pack_rarity_counts.drop('Promo', inplace=True, errors='ignore')
        draft_pack_cards['BoostedFreq'] = draft_pack_cards['Boosting'] / draft_pack_cards['Rarity'].map(draft_pack_rarity_counts)

        # Offer rate
        all_format_cards = currentset_cards.append(draft_pack_cards)
        frequency_by_rarity_per_pack = all_format_cards['Rarity'].map(PACK_CARD_COUNT_BY_RARITY)
        offer_rate = 2 * frequency_by_rarity_per_pack * all_format_cards['BoostedFreq']

        return offer_rate

    def get_offer_rates(self):
        """Return expected card count in a draft for cards in the format.
        Factors in card rarity and boosting rates.

        Returns: Pandas series
            index - card-id (e.g. 12-1)
            value - offer rate, the expected count of this card in a draft (2 packs from the set and 2 packs from the draft packs)
        """
        return self._offer_rates


class DraftFormatSet():
    """Class for holding a set of draft formats to assist with matching decks and determining their format.
    """
    BOOSTING_DATA_DIR = os.path.join(os.path.dirname(__file__), 'boosting_data')
    SIGIL_IDS = eternal.card.ALL.data[eternal.card.ALL.data['Name'].str.endswith(' Sigil')].index

    def __init__(self, setnum=None):
        """Iniitalize from all known draft formats

        Args:
            setnum: (optional) Set number (e.g. 12)
        """
        self.formats = self._load_from_disk(setnum=setnum)

    @classmethod
    def _load_from_disk(cls, setnum=None):
        """Load from boosted data JSONs.

        Args:
            setnum: (optional) Set number (e.g. 12)

        Returns: format dictionary
        """
        formats = {}
        if setnum is None:
            setnum = ""
        for filepath in glob.glob(os.path.join(cls.BOOSTING_DATA_DIR, f"{setnum}*.json")):
            dformat = DraftFormat()
            dformat.load_json(filepath)
            formats[dformat.version] = (dformat)
        return formats

    def match_deck_format_version(self, deck):
        """Return the draft format version string from the deck (e.g. "12.1")

        Args:
            deck: eternal.deck.Deck object

        Returns: Draft format version string (e.g. "12.1") which can be used
        """
        card_ids = pd.Series(deck.main_data.index)

        match_score = {}
        for dformat_version, dformat in self.formats.items():
            setnum = dformat.set
            matching_card_ids = (card_ids.str.startswith(f"{setnum}-")) | \
                                card_ids.isin(self.SIGIL_IDS) | \
                                card_ids.isin(dformat.boosting.keys())
            match_score[dformat_version] = matching_card_ids.sum()
        max_score = max(match_score.values())
        if max_score < 45:
            raise ValueError(f"Only able to match {max_score} cards in the deck.")
        versions = [k for k, v in match_score.items() if v == max_score]

        # If we have two matching scores, then sort based on card offer rates
        if len(versions) != 1:
            card_freq_scores = [card_ids.map(self.get_offer_rates(v)).sum() for v in versions]
            versions = [v for (score, v) in sorted(zip(card_freq_scores, versions), reverse=True)]
        return versions[0]

    def get_offer_rates(self, format_version):
        """Return expected card count in a draft for cards in the format.
        Factors in card rarity and boosting rates.

        Args:
            format_version: Version string for the draft format version e.g. "12.1"

        Returns: Pandas series
            index - card-id (e.g. 12-1)
            value - offer rate, the expected count of this card in a draft (2 packs from the set and 2 packs from the draft packs)
        """
        return self.formats[format_version].get_offer_rates()
