import json
import os
import re

import pandas as pd

FACTIONS = set('FJTPS')


def influence_to_faction(influence):
    """Convert influence to faction

    Args:
        influence: string with influence e.g. {F}{F}{J}

    Returns: faction
    faction is a string with JUST the de-deuplicated influence or 'None' (string) for factionless
    """
    faction = sorted(FACTIONS.intersection(influence))
    if faction:
        return ''.join(faction)
    else:
        return 'None'


class CardInfo:
    """Class to represent stats of a card in Eternal"""

    # TODO: Replace with Python 3.7's dataclass
    # TODO: Figure out how to handle-factions more easily
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
        fields = set(d.keys())  # Handles the case of dictionary or pandas Series
        assert cls.BASE_FIELDS.issubset(fields)
        extra_fields = fields.difference(cls.BASE_FIELDS)
        if extra_fields:
            if d['Type'] == 'Unit':
                assert not extra_fields.difference(cls.UNIT_FIELDS)

    def __repr__(self):
        return "<{obj_class}@{address}> {id:>8}: {name:<30} [{type}-{rarity}]".format(
            obj_class=self.__class__.__name__, address=hex(id(self)),
            id=self.id, name=self.data['Name'], type=self.data['Type'], rarity=self.data['Rarity'])

    def power_count(self):
        """Generate the number of power sources a card represents for purposes of power counting within a deck.

        Returns: Amount of power created by the card as a number.
        """
        if self.data['Type'] == 'Power':
            return 1

        card_text = self.data['CardText']
        re_draw_sigil = re.compile("(?i)draw a .*sigil")
        matches = re_draw_sigil.findall(card_text)
        if matches and self.data['Cost'] <= 2:
            LOWCOST_DRAW_SIGIL_EXCEPTIONS = {"1-157": 1,  # Privilege of Rank --> 2J cost draw a justice sigil
                                             "1-513": 1,  # Find the Way      --> 2T cost spell to draw a depleted sigil
                                             "3-108": 0,  # Copperhall Porter --> 2J cost unit... maybe
                                             "4-275": 0,  # Recon Tower
                                             "11-67": 0,  # Reliable Troops
                                             "1105-19": 0,  # Hifos, Reach Captain
                                             }
            if self.id in LOWCOST_DRAW_SIGIL_EXCEPTIONS:
                return LOWCOST_DRAW_SIGIL_EXCEPTIONS[self.id]
            else:
                return 1
        return 0

    def epc_power_count(self):
        """Generate the number of power sources a card represents for purposes of showing total power sources in a deck.
        This method aims to match the logic with https://www.shiftstoned.com/epc/

        Returns: Amount of power created by the card as a number.
        """
        # Short-circuit power cards
        if self.data['Type'] == 'Power':
            return 1

        # Handle some other cases special cases before applying rules
        # * "Draw a power card": (11-43: Conspire) (4-274: Petition), notably excluding (8-25: Midias, Leyline Dragon)
        if self.id in ["11-43", "4-274"]:
            return 1

        # Handle +X Maximum Power cards
        card_text = self.data['CardText']
        re_max_power = re.compile("\+. Maximum Power")
        matches = re_max_power.findall(card_text)
        if matches:
            if len(matches) == 1:
                return int(matches[0][1])
            else:
                # As of Set 11, there are only 4 cards in this case:
                #   Azindel, the Wayfinder
                #   Mask of Torment
                #   High Prophet of Sol
                #   Battery Mage
                # All of these are treated as 1 power source according to https://www.shiftstoned.com/epc/ so we will follow suit
                return int(matches[0][1])

        # Handle "Draw a [XXX] Sigil"

        # Handle some other cases special cases before applying rules
        # The below are done to match https://www.shiftstoned.com/epc/
        # The logic appears to be that no-other conditions need be met in order to get the Sigil*
        # * - Reliable Troops is an exception
        DRAW_SIGIL_EXCEPTIONS = {"1-154": 0,  # Spire Chaplain
                                 "3-305": 0,  # Lieutenant Relia
                                 "6-29": 0,  # Kaleb's Persuader
                                 "7-76": 0,  # Hexcaster
                                 "11-49": 0,  # Nurturing Sentinel
                                 "1087-1": 0,  # Jekk, Mercenary Hunter
                                 "11-67": 1,  # Reliable Troops <-- This seems to be an exception as the Pay 2 cost is ignored by EPC
                                 "2-177": 2  # Brilliant Discovery
                                 }
        if self.id in DRAW_SIGIL_EXCEPTIONS:
            return DRAW_SIGIL_EXCEPTIONS[self.id]
        re_draw_sigil = re.compile("(?i)draw a .*sigil")
        matches = re_draw_sigil.findall(card_text)
        if matches:
            return 1

        # Play a [X] Sigil/Power
        # TODO: Complete the Play a Sigil condition
        re_play_sigil = re.compile("(?i)play a .*sigil")
        PLAY_SIGIL_EXCEPTIONS = {"1-346": 2}  # Minotaur Ambassador

        return 0


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
                self.cards_dict[cardinfo.id] = cardinfo
        self.cards = list(self.cards_dict.values())
        self.data = pd.DataFrame(x.data for x in self.cards)

    def __getitem__(self, key):
        return self.cards_dict[key]


# Eternal Card JSONs can be obtained at https://eternalwarcry.com/cards/download
# All cards is the global card list
ALL_CARDS_JSON_PATH = os.path.join(os.path.dirname(__file__), 'eternal-cards.json')

if os.path.exists(ALL_CARDS_JSON_PATH):
    ALL = CardCollection()
    ALL.load(ALL_CARDS_JSON_PATH)
