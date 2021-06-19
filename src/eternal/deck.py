import pandas as pd

class Deck:
    """Object representing a deck of cards in Eternal.
    """
    def __init__(self, main, market=[]):
        """Deck object

        Args:
            main: List of Cards in the main deck
            market: List of Cards in the market
        """
        self.main_cards = main
        self.main_data = pd.DataFrame( x.data for x in self.main_cards )

        if market is not None:
            self.market_cards = market
            self.market_data = pd.DataFrame( x.data for x in self.market_cards )
        else:
            self.market_cards = None
            self.market_data = None

    def faction(self, power_only_splash=False):
        """Determine the faction of the deck based on main/market cards.

        According to Reddit user /u/TheZardoz this is 10-cards on faction.
        I assume that 1-9 cards consitutes a splash.

        Source: https://www.reddit.com/r/EternalCardGame/comments/6zim9t/what_determines_what_faction_your_deck_is_in_an/
        """
        raise NotImplementedError("Automatic determination of a Deck's faction(s) has yet to be implemented.")

    def types(self):
        """Return unit-type breakdown of the maindeck
        Returns: Series with value-counts of card types.
        """
        return self.main_data.Type.value_counts()

    def unit_stats(self):
        """Returns statics on units.

        Returns: Series with mean unit stats
        """
        return self.main_data[ self.main_data.Type == 'Unit' ][['Attack','Health']].mean()