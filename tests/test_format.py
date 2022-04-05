import pytest

import eternal.format


@pytest.fixture
def basic_unboosted_format():
    format = eternal.format.DraftFormat()
    format.set = 12
    format.version = '12.1'
    format.iteration = 1
    format.boosting = {}
    format.boosting['1-4'] = 1  # Common
    format.boosting['1-2'] = 1  # Uncommong
    format.boosting['1-3'] = 1  # Rare
    format.boosting['1-6'] = 1  # Legendary
    return format


@pytest.fixture
def basic_boosted_format():
    format = eternal.format.DraftFormat()
    format.set = 12
    format.version = '12.1'
    format.iteration = 1
    format.boosting = {}
    format.boosting['1-4'] = 10  # Common
    format.boosting['1-8'] = 30  # Common
    format.boosting['1-10'] = 40  # Common
    format.boosting['1-2'] = 1  # Uncommong
    format.boosting['1-3'] = 10  # Rare
    format.boosting['1-9'] = 10  # Rare
    format.boosting['1-6'] = 1  # Legendary
    return format


def test_unboosted_get_offer_rates(basic_unboosted_format):
    offer_rates = basic_unboosted_format._calculate_offer_rates()
    assert offer_rates['1-4'] == 16
    assert offer_rates['1-2'] == 6
    assert offer_rates['1-3'] == 29 / 32.0 * 2
    assert offer_rates['1-6'] == 3 / 32.0 * 2


def test_boosted_get_offer_rates(basic_boosted_format):
    offer_rates = basic_boosted_format._calculate_offer_rates()
    assert offer_rates['1-4'] == 2
    assert offer_rates['1-8'] == 6
    assert offer_rates['1-10'] == 8
    assert offer_rates['1-2'] == 6
    assert offer_rates['1-3'] == 29 / 32.0
    assert offer_rates['1-9'] == 29 / 32.0
    assert offer_rates['1-6'] == 3 / 32.0 * 2
