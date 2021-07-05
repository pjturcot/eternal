import itertools


def get_faction_colors(faction_list):
    """Take a list of factions and return a list of colors to use for fill colors (e.g. bar/pie chart)

    Args:
        faction_list:  List of factions to find corresponding plot colors
        e.g. [ 'F', 'None', 'FT' ]

    Returns: color_list - List of colors to use for plotting
    """
    # TODO: Find a better color mapping for OTHER colors / common faction pairs
    FACTION_COLORS_LOOKUP = {'F': 'red', 'J': 'green', 'T': 'yellow', 'S': 'purple', 'P': 'blue', 'None': 'grey'}
    OTHER_COLORS = ['magenta', 'black', 'cyan']
    colors = []
    cycler = iter(itertools.cycle(OTHER_COLORS))
    for x in faction_list:
        if x in FACTION_COLORS_LOOKUP:
            colors.append(FACTION_COLORS_LOOKUP[x])
        else:
            colors.append(next(cycler))
    return colors
