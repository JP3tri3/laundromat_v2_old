import sys
sys.path.append("..")
from database import database as mdb # type: ignore

def determine_new_trend(symbol, entry_side, num_total_grids, active_grid_pos) -> bool:
    print(f'\ndetermining new trend')
    new_trend = False
    micro_trend_check = False
    macro_trend_check = False
    micro_tf = None
    micro_tf_range = None
    macro_tf = None
    macro_tf_range = None

    num_grids_per_set = (num_total_grids / 2)

    micro_tf_1 = '4m'
    micro_tf_1_range = 10
    micro_tf_2 = '6m'
    micro_tf_2_range = 9

    macro_tf_1 = '24m'
    macro_tf_1_range = 8
    macro_tf_2 = '1hr'
    macro_tf_2_range = 7

    micro_tf_triggers_dict = mdb.get_symbol_row_values_dict(symbol, micro_tf)
    macro_tf_triggers_dict = mdb.get_symbol_row_values_dict(symbol, macro_tf)

    available_grids = num_total_grids - active_grid_pos
    print(f'available_grids: {available_grids}')

    if (active_grid_pos <= num_grids_per_set):
        micro_tf = micro_tf_1
        micro_tf_range = micro_tf_1_range
        macro_tf = macro_tf_1
        macro_tf_range = macro_tf_1_range
    elif (active_grid_pos > num_grids_per_set) and (active_grid_pos < num_total_grids):
        micro_tf = micro_tf_2
        micro_tf_range = micro_tf_2_range
        macro_tf = macro_tf_2
        macro_tf_range = macro_tf_2_range
    else:
        print(f'no available grids')

    micro_tf_vwap = micro_tf_triggers_dict['vwap']
    macro_tf_vwap = macro_tf_triggers_dict['vwap']

    if (entry_side == 'Buy'):
        if (micro_tf_vwap > micro_tf_range) and (macro_tf_vwap > macro_tf_range):
            new_trend = True
    elif (entry_side == 'Sell'):
        if (micro_tf_vwap > micro_tf_range) and (macro_tf_vwap > macro_tf_range):
            new_trend = True
    
    print(f'micro_tf: {micro_tf}')
    print(f'micro_tf: {micro_tf_range}, current: {micro_tf_vwap}')
    print(f'micro_tf: {micro_tf}')
    print(f'micro_tf: {macro_tf}')
    print(f'new_trend: {macro_tf_range}, current: {macro_tf_vwap}\n')
    # return tf_triggers_dict
    return new_trend