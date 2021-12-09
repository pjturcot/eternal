import pandas as pd

from .card import FACTIONS

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
        self.main_data = pd.DataFrame(x.data for x in self.main_cards)

        if market is not None:
            self.market_cards = market
            self.market_data = pd.DataFrame(x.data for x in self.market_cards)
        else:
            self.market_cards = None
            self.market_data = None

    def _faction_counts(self):
        """Get the count of non-power cards by faction.
        NOTE: This does not count factionless cards

        Returns: Dictionary with keys 'F','J','T','P','S' with values of the card-count
        """
        non_power_influence = self.main_data[self.main_data.Type != 'Power'].Influence
        faction_counts = pd.Series(index=list(FACTIONS), data=0)
        for faction in FACTIONS:
            faction_counts[faction] = non_power_influence.str.contains(faction).sum()
        return faction_counts

    def faction(self):
        """Determine the faction of the deck based on main/market cards.

        Logic for determining deck faction:
         - 10 non-power cards shows a full pip (main color) in-game (when building a deck)
         - 1-9 non-power cards show a full pip (splash color) in-game (when building a deck)

        With 5 factions in a 75-card constructed deck (with 1/3 power requirement):
        main factions are ones with >= 1/5th (5 factions total) of the non-power deck requirement

        Adapted for Draft (45 card deck) we use 6 as the cutoff.

        Returns: (main_factions, splash_factions) - Lists containing 'F','J','T','P' and/or 'S'
        """
        MAIN_FACTION_COUNT = 6  # Adapted from 10 in constructed (to be confirmed)
        faction_counts = self._faction_counts()
        main_factions = faction_counts[faction_counts >= MAIN_FACTION_COUNT].index.tolist()
        splash_factions = faction_counts[(faction_counts > 0) & (faction_counts < MAIN_FACTION_COUNT)].index.tolist()
        return (main_factions, splash_factions)

    def faction_string(self):
        """Get deck faction strings

        Returns: Faction string with splashes in lowercase
        e.g. 'FT' for praxis and 'FJt' for rakano splashing time
        """

        main_factions, splash_factions = self.faction()
        return ''.join(main_factions) + ''.join(splash_factions).lower()

    def cards_splash(self):
        """Return list of most splashed cards."""
        main_factions, splash_factions = self.faction()
        splashed_set = set(splash_factions)
        is_splash = lambda x: bool(splashed_set.intersection(x))
        return [x for x in self.main_cards if is_splash(x.data['Influence'])]

    def types(self):
        """Return unit-type breakdown of the maindeck
        Returns: Series with value-counts of card types.
        """
        return self.main_data.Type.value_counts()

    def unit_stats(self):
        """Returns statics on units.

        Returns: Series with mean unit stats
        """
        return self.main_data[self.main_data.Type == 'Unit'][['Attack', 'Health']].mean()
