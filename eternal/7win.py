import json
import re

import matplotlib.pyplot as plt
import pandas as pd
import scipy.stats

import eternal.card
import eternal.ewc
import eternal.format
import eternal.plot

CARDS_DATA = eternal.card.ALL.data


def imode(src):
    """Return a copy of a series where all case-insensitive versions have been replaced with the most common case sensitive variant."""
    dest = src.copy()
    for lower, subset in src.groupby(src.str.lower()):
        dest[subset.index] = subset.mode().values[0]
    return dest


if __name__ == '__main__':

    CURRENT_SET = 12

    # The structure of this CSV is FarmingEternal's 7-win run breakdown (Google Sheet) exported as CSV

    df_7win_decks = pd.read_csv('7win_decks_set13.csv')[['s', 'Factions', 'Contributor', 'Image', 'EWC', 'EWC-P', 'W', 'L']]

    df_7win_decks['Deck'] = None
    for id, row in df_7win_decks.iterrows():
        deck = eternal.ewc.parse_deckbuilder_url(row['EWC-P'])
        deck.main_data.name = id
        deck.main_data['DeckId'] = id
        deck.main_data['PowerCount'] = [card.power_count() for card in deck.main_cards]
        deck.main_data['MarketAccess'] = [card.has_market_access() for card in deck.main_cards]
        df_7win_decks.at[id, 'Deck'] = deck
    df_7win_decks['Contributor'] = imode(df_7win_decks['Contributor'])
    df_7win_decks['MainFaction'] = df_7win_decks.Deck.apply(lambda x: ''.join(x.faction()[0]))
    df_7win_decks['SplashFaction'] = df_7win_decks.Deck.apply(lambda x: ''.join(x.faction()[1]))

    # Format matcher
#    matcher = eternal.format.DraftFormatSet(setnum=CURRENT_SET)
#    df_7win_decks['DraftFormat'] = df_7win_decks.Deck.apply(matcher.match_deck_format_version)

    all_cards = pd.concat(df_7win_decks.Deck.apply(lambda x: x.main_data).tolist())
    all_cards['DeckMainFaction'] = all_cards.DeckId.map(df_7win_decks['MainFaction'])
    all_cards['DeckSplashFaction'] = all_cards.DeckId.map(df_7win_decks['SplashFaction'])
    all_cards['IsSplash'] = all_cards.apply(lambda x: bool(set(x['DeckSplashFaction']).intersection(x['Influence'])), axis=1)
    all_cards['Faction'] = all_cards['Influence'].apply(eternal.card.influence_to_faction)
    all_cards['Contributor'] = all_cards.DeckId.map(df_7win_decks['Contributor'])
    for faction in 'FTJPS':
        all_cards[faction] = all_cards['Faction'].str.contains(faction)

    # Playable deck counts
    card_factions = set(map(eternal.card.influence_to_faction, all_cards[all_cards['Type'] != 'Power']['Influence'].unique()))
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
    card_counts = all_cards.groupby('Name')['Faction'].apply(lambda x: pd.Series({'Faction': x[0], 'Count': int(x.size)})).unstack(1)
    card_counts['Count'] = card_counts['Count'].astype('float')
    card_counts['PossibleDecks'] = card_counts['Faction'].map(playable_deck_count_by_faction)
    card_counts['CountPerDeck'] = card_counts['Count'] / card_counts['PossibleDecks']
    card_counts = card_counts.merge(CARDS_DATA, left_index=True, right_on='Name', how='left')
    card_counts['MarketAccess'] = card_counts.index.map(dict(([(x.id, x.has_market_access()) for x in eternal.card.ALL.cards])))

    # # Frequency normalized (pick, boosting, faction, rarity)
    # DRAFT_FORMAT = '12.1'
    # with open(f'boosting_data/{DRAFT_FORMAT}.json') as fin:
    #     DRAFT_PACK_BOOSTING = json.load(fin)['boosting']
    #
    # freq_faction_lookup = {}
    # for faction in card_counts['Faction'].unique():
    #     freq_faction_lookup[faction] = (df_7win_decks['MainFaction'] + df_7win_decks['SplashFaction']).str.contains(faction).sum() / len(df_7win_decks)
    # freq_faction_lookup['None'] = 1.0
    # freq_faction = card_counts['Faction'].map(freq_faction_lookup)
    #
    # # Determine base offer rates by card (broken in Set13)
    # currentset_rarity_counts = CARDS_DATA[CARDS_DATA['SetNumber'] == CURRENT_SET]['Rarity'].value_counts()
    # currentset_rarity_counts.drop('Promo', inplace=True, errors='ignore')
    #
    # draft_pack_cards = CARDS_DATA.loc[DRAFT_PACK_BOOSTING.keys()].copy()
    # draft_pack_cards['Boosting'] = draft_pack_cards.index.map(DRAFT_PACK_BOOSTING)
    # draft_pack_rarity_counts = draft_pack_cards.groupby('Rarity')['Boosting'].sum()
    # draft_pack_rarity_counts.drop('Promo', inplace=True, errors='ignore')
    # draft_pack_cards['BoostedFreq'] = draft_pack_cards['Boosting'] / draft_pack_cards['Rarity'].map(draft_pack_rarity_counts)
    #
    # currentset_index = card_counts['SetNumber'] == CURRENT_SET
    # draft_pack_index = ~currentset_index & ~(card_counts['Name'].str.endswith('Sigil'))
    # freq_rarity_per_pack = card_counts['Rarity'].map({'Common': 8.0, 'Uncommon': 3.0, 'Rare': 0.905, 'Legendary': 0.095})
    # base_offer_rate = pd.Series(index=card_counts.index, dtype='float64')
    # base_offer_rate[currentset_index] = 1.0 / (card_counts[currentset_index])['Rarity'].map(currentset_rarity_counts)
    # base_offer_rate[draft_pack_index] = draft_pack_cards['BoostedFreq'].loc[base_offer_rate[draft_pack_index].index]
    # offer_rate = 2 * freq_rarity_per_pack * base_offer_rate  # 2 packs for each pool
    #
    # card_counts['OfferRate'] = offer_rate
    # card_counts['CountPerOffer'] = card_counts['Count'] / (card_counts['OfferRate'])
    # card_counts['CountPerOfferDeck'] = (card_counts['Count'] / (card_counts['OfferRate'] * card_counts['PossibleDecks'])).astype('float')

    # Analyze the top commons
    #CARD_COUNT_DISPLAY_COLS = ['Name', 'Rarity', 'Faction', 'PossibleDecks', 'OfferRate', 'Count', 'CountPerDeck', 'CountPerOffer', 'CountPerOfferDeck']
    CARD_COUNT_DISPLAY_COLS = ['Name', 'Rarity', 'Faction', 'PossibleDecks', 'Count']
    N = 20
    RARITY = ['Common', 'Uncommon', 'Rare', 'Legendary']

    # Analyze the top cards by count
    top_common_cards = card_counts[card_counts['Rarity'].isin(RARITY)].sort_values('Count', ascending=False)
    print("******Top {N} {Rarity} cards (by count)*****".format(N=N, Rarity='+'.join(RARITY)))
    print("NOTE: OfferRates is the number of cards you would expect in a given 4-pack draft")
    print("NOTE: CountPerOfferDeck also corrects for possible Decks so faction frequency is accounted for")
    print(top_common_cards[CARD_COUNT_DISPLAY_COLS].head(N))
    print("\n")

    # Analyze the top cards by playable deck faction
    top_common_cards = card_counts[card_counts['Rarity'].isin(RARITY)].sort_values('CountPerDeck', ascending=False)
    print("******Top {N} {Rarity} cards (by count per deck)*****".format(N=N, Rarity='+'.join(RARITY)))
    print("NOTE: OfferRates is the number of cards you would expect in a given 4-pack draft")
    print("NOTE: CounterPerOffer also corrects for possible Decks so faction frequency is accounted for")

    print(top_common_cards[CARD_COUNT_DISPLAY_COLS].head(N))
    print("\n")

    # # Analyze the top cards picked cards
    # top_picked_cards = card_counts[card_counts['Rarity'].isin(RARITY)].sort_values('CountPerOffer', ascending=False)
    # print("******Top {N} {Rarity} cards (by count per offer*)*****".format(N=N, Rarity='+'.join(RARITY)))
    # print("NOTE: OfferRates is the number of cards you would expect in a given 4-pack draft")
    # print("NOTE: CountPerOfferDeck also corrects for possible Decks so faction frequency is accounted for")
    # print(top_picked_cards[CARD_COUNT_DISPLAY_COLS].head(N))
    # print("\n")
    #
    # # Analyze the least picked rare cards
    # least_picked_cards = card_counts[card_counts['Rarity'].isin(RARITY)].sort_values('CountPerOffer', ascending=True)
    # print("******Bottom {N} {Rarity} cards (by count per offer*)*****".format(N=N, Rarity='+'.join(RARITY)))
    # print("NOTE: OfferRates is the number of cards you would expect in a given 4-pack draft")
    # print("NOTE: CountPerOfferDeck also corrects for possible Decks so faction frequency is accounted for")
    # print(least_picked_cards[CARD_COUNT_DISPLAY_COLS].head(N))
    # print("\n")

    # Analyze the top splashed cards
    N = 20
    splash_cards = all_cards[all_cards['IsSplash']].copy()
    n_splash_decks = len(splash_cards['DeckId'].unique())
    top_splashed_cards = splash_cards[splash_cards.Type != 'Power']['Name'].value_counts()

    print("******Top {N} splashed for cards****".format(N=N))
    print("(out of {n_splash_decks} decks that splashed)".format(n_splash_decks=n_splash_decks))
    print(top_splashed_cards.head(N))
    print("\n")

    # Analyz all the market cards in play
    market_cards = card_counts[card_counts['MarketAccess']].sort_values('Count', ascending=False)
    print("*******ALL MARKET ACCESS CARDS********")
    print("NOTE: OfferRates is the number of cards you would expect in a given 4-pack draft")
    print("NOTE: CountPerOfferDeck also corrects for possible Decks so faction frequency is accounted for")
    print(market_cards[CARD_COUNT_DISPLAY_COLS])
    print("\n")

    # Top combat tricks
    N = 20
    print("******Top {N} Fast spells (by count)*****".format(N=N))
    print(all_cards[all_cards['Type'] == 'Fast Spell']['Name'].value_counts().head(N))
    print("\n")

    top_fastspell_cards = card_counts[card_counts['Type'] == 'Fast Spell'].sort_values('CountPerDeck', ascending=False)
    print("******Top {N} Fast spells  (by count per deck)*****".format(N=N))
    print(top_fastspell_cards[CARD_COUNT_DISPLAY_COLS].head(N))
    print("\n")

    # List out all "out of faction" cards
    out_of_faction_cards = pd.DataFrame(
        [x for i, x in all_cards.iterrows() if (not set(x.Faction).issubset(x.DeckMainFaction + x.DeckSplashFaction)) and (x.Faction is not 'None')])
    print("Out of faction most played cards")
    if not out_of_faction_cards.empty:
        print(out_of_faction_cards['Name'].value_counts())
        print("Out of faction card Contributors")
        print(df_7win_decks.loc[out_of_faction_cards['DeckId']]['Contributor'].value_counts())
    else:
        print("No out of faction cards played!!!")

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
    print("**** Power played by player (card type = Power) *****")
    print(power_by_player[power_by_player['count'] >= 3].sort_values('mean')[['count', 'mean', 'min', 'max']])

    # Contributor Deck Power (Effective Power)
    df_7win_decks['EffectivePower'] = df_7win_decks.index.map(all_cards.groupby('DeckId')['PowerCount'].sum())
    powercount_by_player = df_7win_decks.groupby('Contributor')['EffectivePower'].describe()[['count', 'mean', 'min', 'max']]
    print("**** Power played by player (effective power*) *****")
    print("NOTE: <=2 cost or less spells counted as power e.g. Seek Power/Etchings/BluePrints etc.")
    print(powercount_by_player[powercount_by_player['count'] >= 3].sort_values('mean'))

    # Contributor Deck Power (Type==Power vs. Effective Power)
    power_by_player_merged = pd.merge(power_by_player, powercount_by_player, left_index=True, right_index=True,
                                      suffixes=('_type', '_effective'))
    print(power_by_player_merged[power_by_player_merged['count_type'] >= 3].sort_values('mean_effective'))

    # MainFaction Deck Power (Type==Power vs. Effective Power)
    powercount_by_deck_main_faction = df_7win_decks.groupby('MainFaction')['EffectivePower'].describe()[['count', 'mean', 'min', 'max']]
    print("**** Power played by deck main factions (effective power*) *****")
    print("NOTE: <=2 cost or less spells counted as power e.g. Seek Power/Etchings/BluePrints etc.")
    print(powercount_by_deck_main_faction[powercount_by_deck_main_faction['count'] >= 3].sort_values('mean'))

    # Contrbutor power vs. Effective power
    power_by_player_subset = power_by_player_merged[power_by_player_merged['count_type'] >= 3]
    plt.figure()
    plt.scatter(power_by_player_subset['mean_type'].values, power_by_player_subset['mean_effective'].values, label=power_by_player_subset.index)
    for name in power_by_player_subset.index:
        plt.annotate(name, (power_by_player_subset.loc[name]['mean_type'], power_by_player_subset.loc[name]['mean_effective']))
    plt.grid('on')
    plt.xlabel('Power (type) cards')
    plt.ylabel('Effective power')
    plt.show()

    # Plot amount of power
    MIN_DECK = 10
    deck_count_by_faction = df_7win_decks['MainFaction'].value_counts()
    deck_power_by_faction = df_7win_decks.groupby('MainFaction')['EffectivePower'].value_counts().sort_index()
    normalized_deck_power_by_faction = pd.DataFrame()
    for faction, count in deck_count_by_faction.items():
        if count >= MIN_DECK:
            normalized_deck_power_by_faction[faction] = deck_power_by_faction.loc[faction] / (float(count)) * 100.0
    first_color = eternal.plot.get_faction_colors([x[0] for x in normalized_deck_power_by_faction.columns])
    second_color = eternal.plot.get_faction_colors([x[1] for x in normalized_deck_power_by_faction.columns])
    ax = normalized_deck_power_by_faction.plot(grid='on', color=first_color, linewidth=6, alpha=0.5)
    normalized_deck_power_by_faction.plot(grid='on', color=second_color, linewidth=1, ax=ax)
    plt.ylabel('Percentage of decks')
    plt.title('Effective power by deck main faction')

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
    first_color = eternal.plot.get_faction_colors([x[0] for x in normalized_curve_by_faction.columns])
    second_color = eternal.plot.get_faction_colors([x[1] for x in normalized_curve_by_faction.columns])
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
    units['Faction'] = units.Influence.apply(eternal.card.influence_to_faction)
    units_health_by_faction = units.pivot_table(index='Faction', columns=['Health'], values='Name', aggfunc='count')
    sorted_units_faction_by_health = units_health_by_faction.loc[units_health_by_faction.sum(axis=1).sort_values(ascending=False).index].transpose()
    colors = eternal.plot.get_faction_colors(sorted_units_faction_by_health.columns)
    sorted_units_faction_by_health.plot(kind='bar', stacked=True, grid=True, color=colors, legend=True)

    # ##******** BEST AND WORST DECKS **************
    # all_cards['CountPerOffer'] = all_cards.index.map(card_counts['CountPerOffer'])
    # all_cards['CountPerOfferDeck'] = all_cards.index.map(card_counts['CountPerOfferDeck'])
    #
    # best_decks = df_7win_decks.loc[all_cards.groupby('DeckId')['CountPerOfferDeck'].mean().nlargest(10).index]
    # worst_decks = df_7win_decks.loc[all_cards.groupby('DeckId')['CountPerOfferDeck'].mean().nsmallest(10).index]


    def plot_contributor_faction_usage():
        contributor_faction_counts = all_cards[all_cards.Type != 'Power'].groupby('Contributor')[['F', 'T', 'J', 'P', 'S']].sum()
        contributor_faction_percent = contributor_faction_counts.div(contributor_faction_counts.sum(axis=1), axis=0)
        contributor_faction_percent['count'] = contributor_faction_percent.index.map(df_7win_decks['Contributor'].value_counts())
        contributor_faction_percent['deviation'] = (contributor_faction_percent[['F', 'T', 'J', 'P', 'S']] - 0.2).abs().sum(axis=1)
        divergence = lambda x: scipy.stats.entropy(x.values, [0.2, 0.2, 0.2, 0.2, 0.2])
        contributor_faction_percent['divergence'] = contributor_faction_percent[['F', 'T', 'J', 'P', 'S']].apply(divergence, axis=1)
        contributor_faction_percent['top_faction_percent'] = (contributor_faction_percent[['F', 'T', 'J', 'P', 'S']]).max(axis=1)
        contributor_faction_percent['top_faction'] = (contributor_faction_percent[['F', 'T', 'J', 'P', 'S']]).idxmax(axis=1)

        subset = contributor_faction_percent[contributor_faction_percent['count'] >= 7]
        plt.figure()
        plt.plot(subset['divergence'], subset['top_faction_percent'], 'ob')
        for name, data in subset.iterrows():
            top_faction = data['top_faction']
            color = eternal.plot.get_faction_colors(top_faction)
            plt.annotate(f'{name} ({top_faction})', (data['divergence'], data['top_faction_percent']), color=color[0])
        plt.grid('on')
        plt.xlabel('Divergence (0 = generalize, 1.0 = specialist)')
        plt.ylabel('Maximum faction (%)')
        plt.title('Generalist vs. specialist')


    def plot_inscribe_faction_usage(FACTION):
        faction_cards = all_cards[(all_cards.Type != 'Power') & (all_cards.Influence.str.contains(FACTION))].copy()
        faction_cards['IsInscribe'] = faction_cards.CardText.str.contains('<b>Inscribe</b>')
        faction_cards_by_deck = faction_cards.groupby('DeckId')['IsInscribe']
        faction_deck_stats = pd.DataFrame({'total': faction_cards_by_deck.count(), 'inscribe': faction_cards_by_deck.sum()})
        faction_deck_stats['percent'] = faction_deck_stats['inscribe'] / faction_deck_stats['total'] * 100.0
        plt.figure()
        ax = plt.subplot(2, 1, 1)
        faction_deck_stats.boxplot(column=['percent'], by=['total'], ax=ax)
        plt.ylabel('Percent (%) Inscribe')
        plt.xlabel(f'Number of {FACTION} cards')
        plt.title(None)
        ax = plt.subplot(2, 1, 2)
        faction_deck_stats['total'].value_counts().sort_index().plot(kind='bar', ax=ax)
        plt.grid('on')
        plt.ylabel('Number of decks')
        plt.xlabel(f'Number of {FACTION} cards')


    # Plot the unit-health by faction
    def plot_unit_health_by_faction():
        plt.figure()
        for i, COST in enumerate([3, 5]):
            ax = plt.subplot(2, 1, i + 1)
            stealth_units = all_cards[(all_cards.Type == 'Unit') & (all_cards.CardText.str.contains('<b>Stealth</b>')) & (all_cards.Cost == COST)].copy()
            stealth_units['Faction'] = stealth_units.Influence.apply(eternal.card.influence_to_faction)
            stealth_units_health_by_faction = stealth_units.pivot_table(index='Faction', columns=['Health'], values='Name', aggfunc='count')
            sorted_stealth_units_faction_by_health = stealth_units_health_by_faction.loc[
                stealth_units_health_by_faction.sum(axis=1).sort_values(ascending=False).index].transpose()
            colors = eternal.plot.get_faction_colors(sorted_stealth_units_faction_by_health.columns)
            sorted_stealth_units_faction_by_health.plot(kind='bar', stacked=True, grid=True, color=colors, legend=True, ax=ax)
            plt.ylabel('Count of units')
            plt.title('Health of {COST}-cost *Stealth* units'.format(COST=COST))


    # Plot the main popularity over time
    def plot_faction_popularity(faction_type='MainFaction', n_deck_window=100):
        """

        Args:
            faction_type:    'MainFaction', 'SplashFaction', or 'MainFaction + SplashFaction'
        :return:
        """
        plt.figure()
        if faction_type == 'MainFaction':
            deck_factions = df_7win_decks['MainFaction'].str
        elif faction_type == 'SplashFaction':
            deck_factions = df_7win_decks['SplashFaction'].str
        elif faction_type == 'MainFaction + SplashFaction':
            deck_factions = (df_7win_decks['SplashFaction'] + df_7win_decks['SplashFaction']).str
        for faction in eternal.card.FACTIONS:
            color = eternal.plot.get_faction_colors(faction)
            plt.plot(deck_factions.contains(faction).rolling(n_deck_window).mean() * 100.0, color=color[0], label=faction)
        average_n_factions = deck_factions.len().mean()
        plt.legend()
        plt.title(f'Rolling {n_deck_window}-deck average of {faction_type} popularity')
        plt.grid('on')
        plt.ylabel('Percentage of decks')
        xlim = plt.xlim()
        plt.plot(plt.xlim(), [average_n_factions / 5.0 * 100] * 2, '--', color=(0.5, 0.5, 0.5))
        plt.xlim(xlim)
        plt.ylim(0.0, plt.ylim()[1])


    # Plot the main popularity over time
    def plot_bootstrapped_faction_popularity(faction_type='MainFaction', n_deck_window=100, bootstrap_col='Contributor'):
        """Plot a bootstrapped version of faction popularity
        Args:
            faction_type:
            n_deck_window:
            boostrap_col:

        Returns:

        """

        bootstrap_values = df_7win_decks[bootstrap_col]
        N_TRIALS = 1000

        faction_curves = {}
        for faction in eternal.card.FACTIONS:
            faction_curves[faction] = []

        if faction_type == 'MainFaction':
            deck_factions = df_7win_decks['MainFaction'].str
        elif faction_type == 'SplashFaction':
            deck_factions = df_7win_decks['SplashFaction'].str
        elif faction_type == 'MainFaction + SplashFaction':
            deck_factions = (df_7win_decks['SplashFaction'] + df_7win_decks['SplashFaction']).str

        for i_trial in range(N_TRIALS):
            # drop_out_value = np.random.choice( bootstrap_values.unique() )
            drop_out_value = bootstrap_values.sample(1).iloc[0]
            subset_index = (bootstrap_values != drop_out_value).values

            if faction_type == 'MainFaction':
                deck_factions = (df_7win_decks[subset_index])['MainFaction'].str
            elif faction_type == 'SplashFaction':
                deck_factions = df_7win_decks[subset_index]['SplashFaction'].str
            elif faction_type == 'MainFaction + SplashFaction':
                deck_factions = (df_7win_decks[subset_index]['SplashFaction'] + df_7win_decks[subset_index]['SplashFaction']).str

            for faction in eternal.card.FACTIONS:
                sample_curve = deck_factions.contains(faction).rolling(n_deck_window).mean() * 100.0
                faction_curves[faction].append(sample_curve)

        plt.figure()
        average_n_factions = deck_factions.len().mean()
        plt.legend()
        plt.title(f'Rolling {n_deck_window}-deck average of {faction_type} popularity')
        plt.grid('on')
        plt.ylabel('Percentage of decks')
        xlim = plt.xlim()
        plt.plot(plt.xlim(), [average_n_factions / 5.0 * 100] * 2, '--', color=(0.5, 0.5, 0.5))
        plt.xlim(xlim)
        plt.ylim(0.0, plt.ylim()[1])


    # Plot the faction popularity over time (multi-faction)
    def plot_multifaction_popularity():
        MIN_DECK = 10
        N_DECK_WINDOW = 100
        deck_count_by_faction = df_7win_decks['MainFaction'].value_counts()
        deck_popularity_by_faction = pd.DataFrame()
        for faction, count in deck_count_by_faction.items():
            if count >= MIN_DECK:
                deck_popularity_by_faction[faction] = (df_7win_decks['MainFaction'] == faction).rolling(N_DECK_WINDOW).mean() * 100.0

        plt.figure()
        faction_order = deck_popularity_by_faction.iloc[-1].sort_values(ascending=False).index
        ax = plt.subplot(2, 1, 1)
        df_popularity = deck_popularity_by_faction[faction_order[:5]]
        first_color = eternal.plot.get_faction_colors([x[0] for x in df_popularity.columns])
        second_color = eternal.plot.get_faction_colors([x[1] for x in df_popularity.columns])
        df_popularity.plot(grid='on', color=first_color, linewidth=6, alpha=0.5, ax=ax)
        df_popularity.plot(grid='on', color=second_color, linewidth=1, ax=ax)
        plt.ylabel('Percentage of decks')
        plt.title('Deck popularity (top 1-5 popular factions today)')
        ax.get_legend().remove()
        ylim = plt.ylim()

        ax = plt.subplot(2, 1, 2)
        df_popularity = deck_popularity_by_faction[faction_order[5:]]
        first_color = eternal.plot.get_faction_colors([x[0] for x in df_popularity.columns])
        second_color = eternal.plot.get_faction_colors([x[1] for x in df_popularity.columns])
        df_popularity.plot(grid='on', color=first_color, linewidth=6, alpha=0.5, ax=ax)
        df_popularity.plot(grid='on', color=second_color, linewidth=1, ax=ax)
        plt.ylabel('Percentage of decks')
        plt.title('Deck popularity (top 6-10 popular factions today)')
        ax.get_legend().remove()
        plt.ylim(ylim)


    def power_sink_summary():
        """"Analyze decks using Sketches or Rune"""
        cards_sketches = CARDS_DATA[CARDS_DATA['Name'].str.endswith('Sketch')]
        cards_runes = CARDS_DATA[CARDS_DATA['Name'].str.startswith('Rune of')]
        cards_both = pd.concat([cards_runes, cards_sketches])

        power_sink_summary = []
        for id, sketch in cards_both.iterrows():
            n_decks = all_cards[all_cards.index.isin([id])].DeckId.unique().size
            power_sink_summary.append([sketch.Name, n_decks])

        power_sink_summary.append(['Any Rune', all_cards[all_cards.index.isin(cards_runes.index)].DeckId.unique().size])
        power_sink_summary.append(['Any Sketch', all_cards[all_cards.index.isin(cards_sketches.index)].DeckId.unique().size])
        power_sink_summary.append(['Any Rune or Sketch', all_cards[all_cards.index.isin(cards_both.index)].DeckId.unique().size])

        df_power_sink_summary = pd.DataFrame(power_sink_summary, columns=['Scenario', 'NumDecks'])
        df_power_sink_summary['PercentageDecks'] = df_power_sink_summary['NumDecks'] / len(df_7win_decks) * 100.0
        print("**** Percentage of decks containing power sinks (Sketches and/or Runes)****")
        print(df_power_sink_summary)


    def display_cards_in_contention(*args,
                                    stats=['Name', 'PossibleDecks', 'OfferRate', 'Count', 'CountPerDeck', 'CountPerOffer', 'CountPerOfferDeck']):
        """

        Args:
            *args: One (or more) strings to use to search the names of cards to display (case insenstive)
            stats: (optional) List of columns to display
        """
        re_string = '|'.join(args)
        print(card_counts[card_counts['Name'].str.contains(re_string, flags=re.IGNORECASE)][stats])


    # display_cards_in_contention('open', 'protector')

    # Dump outputs
    output_order = ['Faction', 'Count', 'PossibleDecks', 'CountPerDeck', 'SetNumber', 'EternalID', 'OfferRate', 'CountPerOffer', 'CountPerOfferDeck', 'Rarity',
                    'Type', 'Name', 'CardText', 'Cost', 'Influence', 'Attack', 'Health', 'ImageUrl', 'DetailsUrl', 'DeckBuildable', 'UnitType', 'MarketAccess']
    output_order = ['Faction', 'Count', 'PossibleDecks', 'CountPerDeck', 'SetNumber', 'EternalID', 'Rarity',
                    'Type', 'Name', 'CardText', 'Cost', 'Influence', 'Attack', 'Health', 'ImageUrl', 'DetailsUrl', 'DeckBuildable', 'UnitType', 'MarketAccess']
    card_counts[output_order].to_csv('card_counts.csv')

    # Additional analysis
    # plot_unit_health_by_faction()
    plot_faction_popularity('MainFaction', 100)
    plot_faction_popularity('SplashFaction', 100)
    plot_contributor_faction_usage()
