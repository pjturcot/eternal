import json

import pytest

import eternal.card


@pytest.fixture
def json_doorbot():
    card_info = json.loads("""{"SetNumber":3,
                 "EternalID":2,
                 "Name":"Helpful Doorbot",
                 "CardText":"",
                 "Cost":0,
                 "Influence":"{F}",
                 "Attack":0,
                 "Health":3,
                 "Rarity":"Common",
                 "Type":"Unit",
                 "UnitType":["Grenadin"],
                 "ImageUrl":"https://cards.eternalwarcry.com/cards/full/Helpful_Doorbot.png",
                 "DetailsUrl":"https://eternalwarcry.com/cards/d/3-2/helpful-doorbot",
                 "DeckBuildable":true}""")
    return card_info


def test_init(json_doorbot):
    card_info = eternal.card.CardInfo(json_doorbot)
    assert isinstance(card_info, eternal.card.CardInfo)
    assert card_info.id == '3-2'


def test_missing_field(json_doorbot):
    del json_doorbot['Name']
    with pytest.raises(AssertionError):
        eternal.card.CardInfo(json_doorbot)


def test_extra_field(json_doorbot):
    json_doorbot['Extra-Field'] = 'This should not be here'
    print(json_doorbot)
    with pytest.raises(AssertionError):
        eternal.card.CardInfo(json_doorbot)

def test_influence_to_faction():
    assert eternal.card.influence_to_faction("''") == 'None'
    assert eternal.card.influence_to_faction("'{F}{F}{J}'") == 'FJ'
    assert eternal.card.influence_to_faction("'{J}{F}'") == 'FJ'
    assert eternal.card.influence_to_faction("'{T}{T}{T}'") == 'T'
