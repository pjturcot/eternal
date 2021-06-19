import pandas as pd
import ewc

if __name__ == '__main__':
    # The structure of this CSV is FarmingEternal's 7-win run breakdown (Google Sheet) exported as CSV
    df_7win_decks = pd.read_csv('7win_decks_set11.csv')[[ u'TS', u'Factions', u'Contributor', u'Image', u'EWC', u'EWC-P', u'W',
       u'L', u'Ep. #']]

    df_7win_decks['Deck'] = None
    for id, row in df_7win_decks.iterrows():
        df_7win_decks.at[ id, 'Deck'] = ewc.parse_deckbuilder_url( row['EWC-P'] )

    # Analyze the top commons
    all_cards = pd.concat(df_7win_decks.Deck.apply( lambda x: x.main_data ).tolist())
    all_cards.Name.value_counts()

    # Look at the unit-counts by player
    df_7win_decks['n_units'] = df_7win_decks.Deck.apply( lambda x: x.types())['Unit']
    units_by_player = df_7win_decks.groupby('Contributor')['n_units'].describe().unstack(1)
    units_by_player[ units_by_player['count'] >= 3 ].sort_values('mean')[ ['count','mean', 'min', 'max']]

    # Augment 7win list with average unit Attack / Health
    df_unit_stats = df_7win_decks.Deck.apply( lambda x: x.unit_stats())
    df_7win_decks['Attack'] = df_unit_stats.Attack
    df_7win_decks['Health'] = df_unit_stats.Health