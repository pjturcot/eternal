import card
import ewc
import matplotlib.pyplot as plt
import pandas as pd
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
        deck.main_data['PowerCount'] = [ card.power_count() for card in deck.main_cards ]
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

    # ********** TOP CARDS (LISTS) **************
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

    # ********** UNIT ANALYSIS **************
    # Look at the unit-counts by player
    df_7win_decks['UnitCount'] = df_7win_decks.Deck.apply(lambda x: x.types())['Unit']
    units_by_player = df_7win_decks.groupby('Contributor')['UnitCount'].describe()
    units_by_player[units_by_player['count'] >= 3].sort_values('mean')[['count', 'mean', 'min', 'max']]

    # Look at the unit-counts by player
    df_7win_decks['UnitCount'] = df_7win_decks.Deck.apply(lambda x: x.types())['Unit']

    units_by_faction = df_7win_decks.groupby('MainFaction')['UnitCount'].describe()
    print("**** Average unit count by deck main-faction (minimum 3 decks)")
    print(units_by_faction[units_by_faction['count'] >= 3].sort_values('mean')[['count', 'mean', 'min', 'max']])

    # ********** DECK POWER ANALYSIS **************
    # Contributor Deck Power (Type==Power)
    df_7win_decks['NumPower'] = df_7win_decks.Deck.apply(lambda x: x.types())['Power']
    power_by_player = df_7win_decks.groupby('Contributor')['NumPower'].describe()[['count', 'mean', 'min', 'max']]
    # print("**** Power played by player (card type = Power) *****")
    # print(power_by_player[power_by_player['count'] >= 3].sort_values('mean')[['count', 'mean', 'min', 'max']])

    # Contributor Deck Power (Effective Power)
    df_7win_decks['EffectivePower'] = df_7win_decks.index.map( all_cards.groupby('DeckId')['PowerCount'].sum() )
    powercount_by_player = df_7win_decks.groupby('Contributor')['EffectivePower'].describe()[['count', 'mean', 'min', 'max']]
    print("**** Power played by player (effective power*) *****")
    print("NOTE: <=2 cost or less spells counted as power e.g. Seek Power/Etchings/BluePrints etc.")
    print(powercount_by_player[powercount_by_player['count'] >= 3].sort_values('mean'))

    # Contributor Deck Power (Type==Power vs. Effective Power)
    power_by_player_merged = pd.merge( power_by_player, powercount_by_player, left_index=True, right_index=True,
                                       suffixes=('_type','_effective'))
    # print( power_by_player_merged[power_by_player_merged['count_type'] >= 3].sort_values('mean_effective'))

    # MainFaction Deck Power (Type==Power vs. Effective Power)
    powercount_by_deck_main_faction = df_7win_decks.groupby('MainFaction')['EffectivePower'].describe()[['count', 'mean', 'min', 'max']]
    print("**** Power played by deck main factions (effective power*) *****")
    print("NOTE: <=2 cost or less spells counted as power e.g. Seek Power/Etchings/BluePrints etc.")
    print(powercount_by_deck_main_faction[powercount_by_deck_main_faction['count'] >= 3].sort_values('mean'))


    # Plot amount of power
    MIN_DECK = 10
    deck_count_by_faction = df_7win_decks['MainFaction'].value_counts()
    deck_power_by_faction = df_7win_decks.groupby('MainFaction')['EffectivePower'].value_counts().sort_index()
    normalized_deck_power_by_faction = pd.DataFrame()
    for faction, count in deck_count_by_faction.items():
        if count >= MIN_DECK:
            normalized_deck_power_by_faction[faction] = deck_power_by_faction.loc[faction] / (float(count)) * 100.0
    first_color = plot.get_faction_colors([x[0] for x in normalized_deck_power_by_faction.columns])
    second_color = plot.get_faction_colors([x[1] for x in normalized_deck_power_by_faction.columns])
    ax = normalized_deck_power_by_faction.plot(grid='on', color=first_color, linewidth=6, alpha=0.5)
    normalized_deck_power_by_faction.plot(grid='on', color=second_color, linewidth=1, ax=ax)
    plt.ylabel('Percentage of decks')
    plt.title('Effective power by deck main faction')
    print("**** Effective power by deck main faction ****")
    print("(for all main-faction pairs with at least {MIN_DECK} decks)".format(MIN_DECK=MIN_DECK))


    # ********** CARD-COST ANALYSIS **************

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
