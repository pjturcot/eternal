import json
import os

import pandas as pd


class CardInfo:
    """Class to represent stats of a card in Eternal"""

    # TODO: Replace with Python 3.7's dataclass
    BASE_FIELDS = set(['Attack', 'CardText', 'Cost', 'DeckBuildable', 'DetailsUrl', 'EternalID', 'Health',
                       'ImageUrl', 'Influence', 'Name', 'Rarity', 'SetNumber', 'Type'])
    UNIT_FIELDS = set(['UnitType'])

    def __init__(self, card_info):
        """Instantiate an instance of card from a dictionary (obtained from EWC)

        Args:
            card_info: Dictionary containing, pandas Series or CardInfo object

        e.g.
        {u'Attack': 5,
        u'CardText': u'<b>Flying</b>;When you play a curse, deal 2 damage to the enemy player and you gain 2 Health.',
        u'Cost': 6,
        u'DeckBuildable': True,
        u'DetailsUrl': u'https://eternalwarcry.com/cards/d/3-242/malediction-reader',
        u'EternalID': 242,
        u'Health': 5,
        u'ImageUrl': u'https://cards.eternalwarcry.com/cards/full/Malediction_Reader.png',
        u'Influence': u'{S}{S}',
        u'Name': u'Malediction Reader',
        u'Rarity': u'Rare',
        u'SetNumber': 3,
        u'Type': u'Unit',
        u'UnitType': [u'Radiant']}

        Returns: instance of Card
        """

        # TODO: Better handle the case of initialization from a series
        if isinstance(card_info, CardInfo):
            self.data = card_info.data
            self.id = card_info.id
        else:
            self.validate_dict(card_info)
            self.data = pd.Series(card_info)
            self.id = '{set}-{eid}'.format(set=self.data['SetNumber'], eid=self.data['EternalID'])
            self.data.name = self.id

    @classmethod
    def is_valid_dict(cls, d):
        try:
            cls.validate_dict(d)
        except AssertionError:
            return False
        return True

    @classmethod
    def validate_dict(cls, d):
        fields = d.keys()  # Handles the case of dictionary or pandas Series
        assert cls.BASE_FIELDS.issubset(fields)
        extra_fields = cls.BASE_FIELDS.difference(fields)
        if extra_fields:
            if fields['Type'] == 'Unit':
                assert not cls.UNIT_FIELDS.difference(extra_fields)


class CardCollection:
    """Lookup objet for all card info exposing a dictionary like interface based on an identified <set>-<card_id>."""

    def __init__(self):
        """

        Returns:
        """
        self.data = pd.DataFrame()
        self.cards = []
        self.cards_dict = {}

    def load(self, json_path):
        """Load a card collection from JSON.

        Args:
            json_path:
        """
        with open(json_path, 'rb') as fin:
            json_card_list = json.load(fin)
        for card_json in json_card_list:
            if CardInfo.is_valid_dict(card_json):
                cardinfo = CardInfo(card_json)
                self.cards_dict[ cardinfo.id ] = cardinfo
        self.cards = self.cards_dict.values()
        self.data = pd.DataFrame(x.data for x in self.cards)

    def __getitem__(self, key):
        return self.cards_dict[key]


# Eternal Card JSONs can be obtained at https://eternalwarcry.com/cards/download
# All cards is the global card list
ALL_CARDS_JSON_PATH = os.path.join(os.path.dirname(__file__), 'eternal-cards.json')

if os.path.exists(ALL_CARDS_JSON_PATH):
    ALL = CardCollection()
    ALL.load(ALL_CARDS_JSON_PATH)
