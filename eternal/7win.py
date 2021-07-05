import matplotlib.pyplot as plt
import pandas as pd

import card
import ewc
import plot

if __name__ == '__main__':
    # The structure of this CSV is FarmingEternal's 7-win run breakdown (Google Sheet) exported as CSV
    df_7win_decks = pd.read_csv('7win_decks_set11.csv')[['TS', 'Factions', 'Contributor', 'Image', 'EWC', 'EWC-P', 'W',
                                                         'L', 'Ep. #']]

    df_7win_decks['Deck'] = None
    for id, row in df_7win_decks.iterrows():
        deck = ewc.parse_deckbuilder_url(row['EWC-P'])
        deck.main_data.name = id
        deck.main_data['DeckId'] = id
        df_7win_decks.at[id, 'Deck'] = deck
    df_7win_decks['MainFaction'] = df_7win_decks.Deck.apply(lambda x: ''.join(x.faction()[0]))
    df_7win_decks['SplashFaction'] = df_7win_decks.Deck.apply(lambda x: ''.join(x.faction()[1]))

    all_cards = pd.concat(df_7win_decks.Deck.apply(lambda x: x.main_data).tolist())
    all_cards['DeckMainFaction'] = all_cards.DeckId.map(df_7win_decks['MainFaction'])
    all_cards['DeckSplashFaction'] = all_cards.DeckId.map(df_7win_decks['SplashFaction'])
    all_cards['IsSplash'] = all_cards.apply(lambda x: bool(set(x['DeckSplashFaction']).intersection(x['Influence'])), axis=1)
    all_cards['Faction'] = all_cards['Influence'].apply(card.influence_to_faction)

    # Playable deck counts
    card_factions = set(map(card.influence_to_faction, all_cards[all_cards['Type'] != 'Power']['Influence'].unique()))
    playable_deck_count_by_faction = {}
    for faction in card_factions:
        if faction == 'None':
            faction = ''
        is_deck_playable = lambda x: set(x['MainFaction']).union(set(x['SplashFaction'])).issuperset(faction)
        deck_count = df_7win_decks.apply(is_deck_playable, axis=1).sum()
        playable_deck_count_by_faction[faction] = deck_count
    playable_deck_count_by_faction['None'] = len(df_7win_decks)

    # Figure out card count statistics
    card_counts = all_cards.groupby('Name')['Faction'].apply(lambda x: pd.Series({'Faction': x[0], 'Count': x.size})).unstack(1)
    card_counts['PossibleDecks'] = card_counts['Faction'].map(playable_deck_count_by_faction)
    card_counts['CountPerDeck'] = card_counts['Count'] / card_counts['PossibleDecks']
    card_counts = card_counts.merge(card.ALL.data, left_index=True, right_on='Name', how='left')

    # Analyze the top commons
    N = 20
    print("******Top {N} Common cards (by count)*****".format(N=N))
    print(all_cards[all_cards.Rarity == 'Common'].Name.value_counts().head(N))
    print("\n")

    # Analyze the top commons by playable deck faction
    top_common_cards = card_counts[card_counts['Rarity'] == 'Common'].sort_values('CountPerDeck', ascending=False)
    print("******Top {N} Common cards (by count per deck)*****".format(N=N))
    print(top_common_cards[['Name', 'Faction', 'Count', 'PossibleDecks', 'CountPerDeck']].head(N))
    print("\n")

    # Analyze the top splashed cards
    N = 20
    splash_cards = all_cards[all_cards['IsSplash']].copy()
    n_splash_decks = len(splash_cards['DeckId'].unique())
    top_splashed_cards = splash_cards[splash_cards.Type != 'Power']['Name'].value_counts()

    print("******Top {N} splashed for cards****".format(N=N))
    print("(out of {n_splash_decks} decks that splashed)".format(n_splash_decks=n_splash_decks))
    print(top_splashed_cards.head(N))
    print("\n")

    # Top combat tricks
    N = 20
    print("******Top {N} Fast spells (by count)*****".format(N=N))
    print(all_cards[all_cards['Type'] == 'Fast Spell']['Name'].value_counts().head(N))
    print("\n")

    top_fastspell_cards = card_counts[card_counts['Type'] == 'Fast Spell'].sort_values('CountPerDeck', ascending=False)
    print("******Top {N} Fast spells  (by count per deck)*****".format(N=N))
    print(top_fastspell_cards[['Name', 'Faction', 'Count', 'PossibleDecks', 'CountPerDeck']].head(N))
    print("\n")


    # Top stealth units
    N = 20
    print("******Top {N} Stealth Units (by count)*****".format(N=N))
    print(all_cards[(all_cards['Type'] == 'Unit') & (all_cards['CardText'].str.contains('<b>Stealth</b>'))]['Name'].value_counts().head(N))
    print("\n")

    top_stealth_cards = card_counts[(card_counts['Type'] == 'Unit') & (card_counts['CardText'].str.contains('<b>Stealth</b>'))].sort_values('CountPerDeck', ascending=False)
    print("******Top {N} Steal Units  (by count per deck)*****".format(N=N))
    print(top_stealth_cards[['Name', 'Faction', 'Count', 'PossibleDecks', 'CountPerDeck']].head(N))
    print("\n")


    # Look at the unit-counts by player
    df_7win_decks['UnitCount'] = df_7win_decks.Deck.apply(lambda x: x.types())['Unit']
    units_by_player = df_7win_decks.groupby('Contributor')['UnitCount'].describe()
    units_by_player[units_by_player['count'] >= 3].sort_values('mean')[['count', 'mean', 'min', 'max']]

    # Look at the unit-counts by player
    df_7win_decks['UnitCount'] = df_7win_decks.Deck.apply(lambda x: x.types())['Unit']

    units_by_faction = df_7win_decks.groupby('MainFaction')['UnitCount'].describe()
    print("**** Average unit count by deck main-faction (minimum 3 decks)")
    print(units_by_faction[units_by_faction['count'] >= 3].sort_values('mean')[['count', 'mean', 'min', 'max']])

    # Power by deck
    df_7win_decks['n_power'] = df_7win_decks.Deck.apply(lambda x: x.types())['Power']
    power_by_player = df_7win_decks.groupby('Contributor')['n_power'].describe()
    power_by_player[power_by_player['count'] >= 3].sort_values('mean')[['count', 'mean', 'min', 'max']]

    # Mean card cost by deck faction
    all_cards[all_cards.Type != 'Power'].groupby('DeckMainFaction')['Cost'].mean()
    # all_cards[ all_cards.Type != 'Power' ].boxplot( 'Cost', 'DeckMainFaction' ) # Box plot (not that informative)

    # Plot curve by deck faction
    MIN_DECK = 10
    curve_by_faction = all_cards[all_cards.Type != 'Power'].groupby(['DeckMainFaction', 'Cost'])['Name'].count()
    deck_count_by_faction = df_7win_decks['MainFaction'].value_counts()
    normalized_curve_by_faction = pd.DataFrame()
    for faction, count in deck_count_by_faction.items():
        if count >= MIN_DECK:
            normalized_curve_by_faction[faction] = curve_by_faction.loc[faction] / (float(count))
    first_color = plot.get_faction_colors([x[0] for x in normalized_curve_by_faction.columns])
    second_color = plot.get_faction_colors([x[1] for x in normalized_curve_by_faction.columns])
    ax = normalized_curve_by_faction.plot(grid='on', color=first_color, linewidth=6, alpha=0.5)
    normalized_curve_by_faction.plot(grid='on', color=second_color, linewidth=1, ax=ax)
    plt.ylabel('Number of cards')
    plt.title('Average curve by deck main faction')
    print("**** Average card cost by deck main faction ****")
    print("(for all main-faction pairs with at least {MIN_DECK} decks)".format(MIN_DECK=MIN_DECK))
    print(all_cards[all_cards.Type != 'Power'].groupby('DeckMainFaction')['Cost'].mean()[normalized_curve_by_faction.columns].sort_values())

    # Augment 7win list with average unit Attack / Health
    df_unit_stats = df_7win_decks.Deck.apply(lambda x: x.unit_stats())
    df_7win_decks['Attack'] = df_unit_stats.Attack
    df_7win_decks['Health'] = df_unit_stats.Health

    # Plot the unit-health by faction
    units = all_cards[all_cards.Type == 'Unit'].copy()
    units['Faction'] = units.Influence.apply(card.influence_to_faction)
    units_health_by_faction = units.pivot_table(index='Faction', columns=['Health'], values='Name', aggfunc='count')
    sorted_units_faction_by_health = units_health_by_faction.loc[units_health_by_faction.sum(axis=1).sort_values(ascending=False).index].transpose()
    colors = plot.get_faction_colors(sorted_units_faction_by_health.columns)
    sorted_units_faction_by_health.plot(kind='bar', stacked=True, grid=True, color=colors, legend=True)

    # Plot the unit-health by faction
    plt.figure()
    for i, COST in enumerate([3, 5]):
        ax = plt.subplot(2, 1, i + 1)
        stealth_units = all_cards[(all_cards.Type == 'Unit') & (all_cards.CardText.str.contains('<b>Stealth</b>')) & (all_cards.Cost == COST)].copy()
        stealth_units['Faction'] = stealth_units.Influence.apply(card.influence_to_faction)
        stealth_units_health_by_faction = stealth_units.pivot_table(index='Faction', columns=['Health'], values='Name', aggfunc='count')
        sorted_stealth_units_faction_by_health = stealth_units_health_by_faction.loc[
            stealth_units_health_by_faction.sum(axis=1).sort_values(ascending=False).index].transpose()
        colors = plot.get_faction_colors(sorted_stealth_units_faction_by_health.columns)
        sorted_stealth_units_faction_by_health.plot(kind='bar', stacked=True, grid=True, color=colors, legend=True, ax=ax)
        plt.ylabel('Count of units')
        plt.title('Health of {COST}-cost *Stealth* units'.format(COST=COST))
