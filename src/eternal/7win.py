import pandas as pd

import ewc
import plot

if __name__ == '__main__':
    # The structure of this CSV is FarmingEternal's 7-win run breakdown (Google Sheet) exported as CSV
    df_7win_decks = pd.read_csv('7win_decks_set11.csv')[[u'TS', u'Factions', u'Contributor', u'Image', u'EWC', u'EWC-P', u'W',
                                                         u'L', u'Ep. #']]

    df_7win_decks['Deck'] = None
    for id, row in df_7win_decks.iterrows():
        df_7win_decks.at[id, 'Deck'] = ewc.parse_deckbuilder_url(row['EWC-P'])

    # Analyze the top commons
    # TODO: Is there a better way to reduce?
    all_cards = pd.concat(df_7win_decks.Deck.apply(lambda x: x.main_data).tolist())
    all_cards[all_cards.Rarity == 'Common'].Name.value_counts().head(20)

    # Look at the unit-counts by player
    df_7win_decks['n_units'] = df_7win_decks.Deck.apply(lambda x: x.types())['Unit']
    units_by_player = df_7win_decks.groupby('Contributor')['n_units'].describe().unstack(1)
    units_by_player[units_by_player['count'] >= 3].sort_values('mean')[['count', 'mean', 'min', 'max']]

    # Power by deck
    df_7win_decks['n_power'] = df_7win_decks.Deck.apply(lambda x: x.types())['Power']
    power_by_player = df_7win_decks.groupby('Contributor')['n_power'].describe().unstack(1)
    power_by_player[power_by_player['count'] >= 3].sort_values('mean')[['count', 'mean', 'min', 'max']]

    # Augment 7win list with average unit Attack / Health
    df_unit_stats = df_7win_decks.Deck.apply(lambda x: x.unit_stats())
    df_7win_decks['Attack'] = df_unit_stats.Attack
    df_7win_decks['Health'] = df_unit_stats.Health

    # Plot the unit-health by faction
    FACTIONS = set('FJTPS')

    units = all_cards[all_cards.Type == 'Unit']
    units['Faction'] = units.Influence.apply(lambda x: ''.join(FACTIONS.intersection(x)))
    units['Faction'][units['Faction'] == ''] = 'None'
    units_health_by_faction = units.pivot_table(index='Faction', columns=['Health'], values='Name', aggfunc='count')
    sorted_units_faction_by_health = units_health_by_faction.ix[units_health_by_faction.sum(axis=1).order(ascending=False).index].transpose()
    colors = plot.get_faction_colors(sorted_units_faction_by_health.columns)
    sorted_units_faction_by_health.plot(kind='bar', stacked=True, grid=True, color=colors, legend=True)

    # Analyze the top splashed cards
    splashed_cards = []
    n_splash_decks = 0
    for deck in df_7win_decks['Deck']:
        deck_splash_cards = deck.cards_splash()
        if deck_splash_cards:
            splashed_cards += deck_splash_cards
            n_splash_decks += 1
    all_cards_splash = pd.DataFrame( x.data for x in splashed_cards)
    top_splashed_cards = all_cards_splash[ all_cards_splash.Type != 'Power' ]['Name'].value_counts()
    print "******Top 20 splashed for cards****"
    print "(out of {n_splash_decks} decks that splashed)".format(n_splash_decks=n_splash_decks)
    print top_splashed_cards.head(20)
