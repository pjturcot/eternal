import matplotlib.pyplot as plt
import pandas as pd

import card
import ewc
import plot

if __name__ == '__main__':
    # The structure of this CSV is FarmingEternal's 7-win run breakdown (Google Sheet) exported as CSV
    df_7win_decks = pd.read_csv('7win_decks_set11.csv')[[u'TS', u'Factions', u'Contributor', u'Image', u'EWC', u'EWC-P', u'W',
                                                         u'L', u'Ep. #']]

    df_7win_decks['Deck'] = None
    for id, row in df_7win_decks.iterrows():
        deck = ewc.parse_deckbuilder_url(row['EWC-P'])
        deck.main_data.name = id
        deck.main_data['DeckId'] = id
        df_7win_decks.at[id, 'Deck'] = deck


    # Analyze the top commons
    # TODO: Is there a better way to reduce?
    all_cards = pd.concat(df_7win_decks.Deck.apply(lambda x: x.main_data).tolist())

    all_cards[all_cards.Rarity == 'Common'].Name.value_counts().head(20)

    # Look at the unit-counts by player
    df_7win_decks['UnitCount'] = df_7win_decks.Deck.apply(lambda x: x.types())['Unit']
    units_by_player = df_7win_decks.groupby('Contributor')['UnitCount'].describe().unstack(1)
    units_by_player[units_by_player['count'] >= 3].sort_values('mean')[['count', 'mean', 'min', 'max']]

    # Look at the unit-counts by player
    df_7win_decks['UnitCount'] = df_7win_decks.Deck.apply(lambda x: x.types())['Unit']
    df_7win_decks['MainFaction'] = df_7win_decks.Deck.apply(lambda x: ''.join(x.faction()[0]) )
    units_by_faction = df_7win_decks.groupby('MainFaction')['UnitCount'].describe().unstack(1)
    print "**** Average unit count by deck main-faction (minimum 3 decks)"
    print units_by_faction[units_by_faction['count'] >= 3].sort_values('mean')[['count', 'mean', 'min', 'max']]

    # Power by deck
    df_7win_decks['n_power'] = df_7win_decks.Deck.apply(lambda x: x.types())['Power']
    power_by_player = df_7win_decks.groupby('Contributor')['n_power'].describe().unstack(1)
    power_by_player[power_by_player['count'] >= 3].sort_values('mean')[['count', 'mean', 'min', 'max']]

    # Mean card cost by deck faction
    # Boxplot
    all_cards[ all_cards.Type != 'Power' ].groupby( 'DeckMainFactions' )['Cost'].mean()
    all_cards[ all_cards.Type != 'Power' ].boxplot( 'Cost', 'DeckMainFactions' ) #Plot

    # Plot curve by deck faction
    MIN_DECK = 10
    curve_by_faction = all_cards[ all_cards.Type != 'Power' ].groupby( ['DeckMainFactions', 'Cost' ])['Name'].count().unstack(1)
    deck_count_by_faction = df_7win_decks['MainFaction'].value_counts()
    normalized_curve_by_faction = pd.DataFrame()
    for faction, count in deck_count_by_faction.iteritems():
        if count >= MIN_DECK:
            normalized_curve_by_faction[ faction ] = curve_by_faction[faction] / (float(count) )
    first_color = plot.get_faction_colors( [ x[0] for x in normalized_curve_by_faction.columns ])
    second_color = plot.get_faction_colors( [ x[1] for x in normalized_curve_by_faction.columns ])
    ax = normalized_curve_by_faction.plot( grid='on', colors=first_color, linewidth=6, alpha=0.5)
    normalized_curve_by_faction.plot( grid='on', colors=second_color, linewidth=1, ax=ax)
    plt.ylabel('Number of cards')
    plt.title('Average curve by deck main faction')
    print "**** Average card cost by deck main faction ****"
    print "(for all main-faction pairs with at least {MIN_DECK} decks)".format( MIN_DECK=MIN_DECK)
    print all_cards[ all_cards.Type != 'Power' ].groupby( 'DeckMainFactions' )['Cost'].mean()[ normalized_curve_by_faction.columns ].sort_values()


    # Augment 7win list with average unit Attack / Health
    df_unit_stats = df_7win_decks.Deck.apply(lambda x: x.unit_stats())
    df_7win_decks['Attack'] = df_unit_stats.Attack
    df_7win_decks['Health'] = df_unit_stats.Health

    # Plot the unit-health by faction
    units = all_cards[all_cards.Type == 'Unit']
    units['Faction'] = units.Influence.apply( card.influence_to_faction )
    units_health_by_faction = units.pivot_table(index='Faction', columns=['Health'], values='Name', aggfunc='count')
    sorted_units_faction_by_health = units_health_by_faction.ix[units_health_by_faction.sum(axis=1).order(ascending=False).index].transpose()
    colors = plot.get_faction_colors(sorted_units_faction_by_health.columns)
    sorted_units_faction_by_health.plot(kind='bar', stacked=True, grid=True, color=colors, legend=True)

    # Plot the unit-health by faction
    plt.figure()
    for i, COST in enumerate([3, 5]):
        ax = plt.subplot( 2, 1, i+1 )
        stealth_units = all_cards[ (all_cards.Type == 'Unit') & ( all_cards.CardText.str.contains('<b>Stealth</b>')) & (all_cards.Cost == COST)]
        stealth_units['Faction'] = stealth_units.Influence.apply(card.influence_to_faction)
        stealth_units_health_by_faction = stealth_units.pivot_table(index='Faction', columns=['Health'], values='Name', aggfunc='count')
        sorted_stealth_units_faction_by_health = stealth_units_health_by_faction.ix[stealth_units_health_by_faction.sum(axis=1).order(ascending=False).index].transpose()
        colors = plot.get_faction_colors(sorted_stealth_units_faction_by_health.columns)
        sorted_stealth_units_faction_by_health.plot(kind='bar', stacked=True, grid=True, color=colors, legend=True, ax=ax)
        plt.ylabel('Count of units')
        plt.title('Health of {COST}-cost *Stealth* units'.format(COST=COST))



    # Analyze the top splashed cards
    # TODO: THIS HAS TO BE MORE ELEGANT!!!
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
