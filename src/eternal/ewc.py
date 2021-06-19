
import card
import deck
import urlparse

def parse_deckbuilder_url(url):
    """Parse a deck-builder URL.
    These URLs are simple as the card-ids are right in the URL and can be used directly

    Args:
        url: Eternal warcry deckbuilder URL

    Returns: Deck object
    """
    market = None
    main_deck = None

    parsed_url = urlparse.urlparse(url)
    main_deck = parsed_url.query.split('main=')[1]
    market_cards = None
    if 'market' in main_deck:
        main_deck, market = main_deck.split('&market=')
        market_card_id_counts = market.split(';')[:-1]
        market_cards = []
        for id_count in market_card_id_counts:
            cid, count = id_count.split(':')
            market_cards += [card.ALL[ cid] ] * int(count)

    main_card_id_counts = main_deck.split(';')[:-1]
    main_cards = []
    for id_count in main_card_id_counts:
        cid, count = id_count.split(':')
        main_cards += [card.ALL[ cid] ] * int(count)


    return deck.Deck( main_cards, market=market_cards )