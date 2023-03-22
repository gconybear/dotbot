from database_connection import *
from sql_queries import *
import numpy as np
from ..embed import Embedder
from ..helpers import get_id
from ..app import get_index


occ = occupancy_kpis(occupancy_sql)
unrentables = unrentable_kpis(unrentables_sql, occupancy_sql)
moves = move_kpis(moves_sql)
online_moves = online_moves_kpi(online_moves_sql)
rates = rates_kpi(street_ratio_sql)

summary = str(f"The current occupancy is {occ['current occupancy']: .2%} and the week over week expected occupancy change is {occ['week over week expected occupancy change']: .2%}. \n \
      Changes in occupancy are a result of tenants moving in or moving out. In the last week, {moves['last_week_total']} new tenants moved in and {moves['last_week_move_outs']} tenants moved out. \n \
      But there are expected to be {moves['last_week_expected_move_outs']} move outs as {moves['last_week_expected_move_outs'] - moves['last_week_move_outs']} move outs have not been confirmed by the Facility Supervisor yet. \n \
      This can take up to 7 days after a tenant moves out depending on the Facility Supervisor's task load in Atlas. \n \
      The week over week change in move ins is {moves['move_ins_week_over_week_change']: .2%} and the change in expected move outs is {moves['expected_move_outs_week_over_week_change']: .2%} \n \
      The current number of unrentable units is {unrentables['current number of unrentable units']}. The current percent unrentables of total units is {unrentables['current % of unrentables']: .2%}\
      The week over week % unrentable change is {unrentables['week over week % unrentable change']: .2%}. \n \
      The last week saw {online_moves['last week % of online move ins']: .2%} of move ins come through the customer portal online. This is a {online_moves['week over week online move in change']:.2%} change from the previous week.\n\
      The current average street rate is ${rates['street_rate_per_nrsf_latest']: .3} and current average in place rate is ${rates['in_place_rate_per_nrsf_latest']: .3}. \n \
      The year over year street rate growth is {rates['street_rate_growth']: .2%} and year over year in place rate growth is {rates['in_place_rate_growth']: .2%}. \n \
      The current street rate over in place rate ratio is {rates['current_ratio']: .2%}. The average street rate over in place rate ratio for the last year is {rates['LTM_avg_street_in_place_ratio']: .2%}.")

content_id = get_id()
index = get_index()
em = Embedder(index) 

metadata = {
      'text_upload': summary, 
      'doc_upload': '', 
      'tags': '', 
      'submitted_by': 'Holly Nereson', 
      'date': str(np.datetime64('today')), 
      'timestamp': str(np.datetime64('now'))
}

metadata['topic'] = 'executive summary for today'
user_text = f"The topic of this text is about: {metadata['topic']}\n\n" + summary 

em.embed_and_save(content_id=content_id, text=user_text, metadata=metadata, aws=True)

# maybe need to do the overwrite parameter within embed_and_save or make a new function to do so?

