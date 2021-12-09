import pytest

import eternal.ewc


@pytest.fixture
def ewc_v2_siegesupplier():
    """
    1x 10-362 Siege Supplier
    2x 1-1 Fire Sigil
    """
    url = "https://eternalwarcry.com/deck-builder?main=BKqLCBB"
    return url


@pytest.fixture
def ewc_v1_set11_deck():
    return "https://eternalwarcry.com/deck-builder?main=11-4:1;1-408:1;11-7:3;11-8:2;11-10:1;11-11:1;10-198:2;1-21:1;10-368:2;11-105:1;1-212:2;7-14:1;11-17:1;10-385:1;1-30:1;11-115:1;1-40:1;1-224:1;11-169:2;11-119:1;11-121:1;2-26:1;1-1:6;1-187:8;11-2:2;"


@pytest.fixture
def ewc_v2_set11_deck():
    return "https://eternalwarcry.com/deck-builder?main=BLEBB4MDLHCLIBLKBLLCKmGBBVCKwLBLpDCB0GBHOBLRBKhMBBeBLzDBBoBBBgHCLpFBL3DBL5DBCaGBBIB7FCLC"

@pytest.fixture
def ewc_cids_set11_deck():
    return ['1-1', '1-1', '1-1', '1-1', '1-1', '1-1', '1-187', '1-187', '1-187', '1-187', '1-187', '1-187', '1-187', '1-187', '1-21', '1-212', '1-212', '1-224',
            '1-30', '1-40', '1-408', '10-198', '10-198', '10-368', '10-368', '10-385', '11-10', '11-105', '11-11', '11-115', '11-119', '11-121', '11-169',
            '11-169', '11-17', '11-2', '11-2', '11-4', '11-7', '11-7', '11-7', '11-8', '11-8', '2-26', '7-14']


def test_parse_deckbuilder_url_v2_siegesupplier(ewc_v2_siegesupplier):
    deck = eternal.ewc.parse_deckbuilder_url_v2(ewc_v2_siegesupplier)
    assert sorted(deck.main_data.index) == ['1-1', '1-1', '10-362']

def test_parse_v1_set11_deck(ewc_v1_set11_deck, ewc_cids_set11_deck):
    deck = eternal.ewc.parse_deckbuilder_url(ewc_v1_set11_deck)
    assert sorted(deck.main_data.index) == ewc_cids_set11_deck

def test_parse_v2_set11_deck(ewc_v2_set11_deck, ewc_cids_set11_deck):
    deck = eternal.ewc.parse_deckbuilder_url(ewc_v2_set11_deck)
    assert sorted(deck.main_data.index) == ewc_cids_set11_deck