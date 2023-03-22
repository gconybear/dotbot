import psycopg2 
import pandas as pd
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta

# Load the credentials from the .env file
load_dotenv()

postgres_cred = {
    'host' : os.getenv("POSTGRES_HOST"),
    'database' : os.getenv("POSTGRES_DB"),
    'port' : os.getenv("POSTGRES_PORT"),
    'user' : os.getenv("POSTGRES_USER"),
    'password' : os.getenv("POSTGRES_PASSWORD")
}

def get_sql_connection():
    conn = psycopg2.connect(
        host=postgres_cred['host'],
        database=postgres_cred['database'],
        port=postgres_cred['port'],
        user=postgres_cred['user'],
        password=postgres_cred['password']
    )

    return conn 

def run_sql_query(sql_query):
    conn = get_sql_connection()
    df = pd.read_sql_query(sql_query, conn)
    conn.close()
    return df

def occupancy_kpis(sql_query):
    occupancy_df = run_sql_query(sql_query)
    # Filter data for the latest date and the date one week prior
    latest_date = occupancy_df['date'].max()
    prior_date = occupancy_df['date'].min()

    latest_df = occupancy_df[occupancy_df['date'] == latest_date]
    prior_df = occupancy_df[occupancy_df['date'] == prior_date]

    # Calculate occupancy and expected occupancy for the latest date
    latest_nrsf = latest_df['nrsf'].sum()
    latest_occupied_area = latest_df['occupied_area'].sum()
    latest_expected_occupied_area = (latest_df['expected_occupied_units'] * latest_df['unit_area']).sum()

    latest_occupancy = latest_occupied_area / latest_nrsf
    latest_expected_occupancy = latest_expected_occupied_area / latest_nrsf

    # Calculate occupancy and expected occupancy for the date one week prior
    prior_nrsf = prior_df['nrsf'].sum()

    prior_expected_occupied_area = (prior_df['expected_occupied_units'] * prior_df['unit_area']).sum()

    prior_expected_occupancy = prior_expected_occupied_area / prior_nrsf

    expected_occupancy_change = latest_expected_occupancy - prior_expected_occupancy

    return {'current occupancy':latest_occupancy, 'week over week expected occupancy change': expected_occupancy_change}

def unrentable_kpis(unrentable_query, occupancy_query):
    unrentable_df = run_sql_query(unrentable_query)
    occupancy_df = run_sql_query(occupancy_query)
    latest_date = occupancy_df['date'].max()
    prior_date = occupancy_df['date'].min()

    latest_df = unrentable_df[unrentable_df['date'] == latest_date]
    prior_df = unrentable_df[unrentable_df['date'] == prior_date]

    latest_df_occ = occupancy_df[occupancy_df['date'] == latest_date]
    prior_df_occ = occupancy_df[occupancy_df['date'] == prior_date]

    latest_units = latest_df_occ['units'].sum()
    prior_units = prior_df_occ['units'].sum()

    # Calculate the number of unrentable units for the latest date and prior date
    unrentable_latest_df = latest_df[(latest_df['occupied'] == False) & (latest_df['status'] == 'unrentable')].drop_duplicates(subset='id')
    unrentable_prior_df = prior_df[(prior_df['occupied'] == False) & (prior_df['status'] == 'unrentable')].drop_duplicates(subset='id')

    unrentable_units_latest = len(unrentable_latest_df)
    unrentable_units_prior = len(unrentable_prior_df)

    latest_unrentable_percentage = unrentable_units_latest / latest_units
    prior_unrentable_percentage = unrentable_units_prior / prior_units
    unrentable_percentage_change = latest_unrentable_percentage - prior_unrentable_percentage

    return {'current number of unrentable units':unrentable_units_latest, 'current % of unrentables':latest_unrentable_percentage, 'week over week % unrentable change':unrentable_percentage_change}


def move_kpis(moves_sql):
    # Fetch moves data from database
    moves = run_sql_query(moves_sql)

    # Convert date column to datetime type
    moves['date'] = pd.to_datetime(moves['date'])

    # Calculate dates for two weeks ago and one week ago
    two_weeks_ago = (datetime.now().date() - timedelta(days=14))
    one_week_ago = (datetime.now().date() - timedelta(days=7))

    # Calculate move-ins and move-outs for last week and two weeks ago
    move_ins_last_week = sum(row['move_ins'] for _, row in moves.iterrows() if one_week_ago <= row['date'] <= datetime.now())
    move_ins_two_weeks_ago = sum(row['move_ins'] for _, row in moves.iterrows() if two_weeks_ago <= row['date'] < one_week_ago)
    move_outs_two_weeks_ago = sum(row['move_outs'] for _, row in moves.iterrows() if two_weeks_ago <= row['date'] < one_week_ago)
    move_outs_last_week = sum(row['move_outs'] for _, row in moves.iterrows() if one_week_ago <= row['date'] <= datetime.now())
    expected_move_outs_last_week = sum(row['scheduled_move_outs'] for _, row in moves.iterrows() if one_week_ago <= row['date'] <= datetime.now())
    expected_move_outs_2_weeks_ago = sum(row['scheduled_move_outs'] for _, row in moves.iterrows() if two_weeks_ago <= row['date'] < one_week_ago)

    # Calculate move difference and week-over-week change
    move_ins_ww_change = ((move_ins_last_week - move_ins_two_weeks_ago) / move_ins_two_weeks_ago) if move_ins_two_weeks_ago > 0 else 0
    move_outs_ww_change = ((move_outs_last_week - move_outs_two_weeks_ago) / move_outs_two_weeks_ago) if move_outs_two_weeks_ago > 0 else 0
    expected_move_outs_ww_change = ((expected_move_outs_last_week - expected_move_outs_2_weeks_ago) / expected_move_outs_2_weeks_ago) if expected_move_outs_2_weeks_ago > 0 else 0

    return {
    'last_week_total': move_ins_last_week,
    'two_weeks_ago_total': move_ins_two_weeks_ago,
    'last_week_move_outs': move_outs_last_week,
    'two_weeks_ago_move_outs': move_outs_two_weeks_ago,
    'last_week_expected_move_outs': expected_move_outs_last_week,
    'two_weeks_ago_expected_move_outs': expected_move_outs_2_weeks_ago,
    'move_ins_week_over_week_change': move_ins_ww_change,
    'move_outs_week_over_week_change': move_outs_ww_change,
    'expected_move_outs_week_over_week_change': expected_move_outs_ww_change
}

def online_moves_kpi(online_moves_sql):
    online_moves = run_sql_query(online_moves_sql)

    today = datetime.today()
    last_week_start = (today - timedelta(days=today.weekday(), days=8)).date()
    last_week_end = (last_week_start + timedelta(days=7))
    two_weeks_ago_start = (today - timedelta(days=today.weekday(), days=15)).date()
    two_weeks_ago_end = (two_weeks_ago_start + timedelta(days=7))

    # Filter the data for the last week and two weeks ago
    last_week_data =online_moves[(online_moves['move_in_date'] >= last_week_start) & (online_moves['move_in_date'] <= last_week_end)]
    two_weeks_ago_data = online_moves[(online_moves['move_in_date'] >= two_weeks_ago_start) & (online_moves['move_in_date'] <= two_weeks_ago_end)]

    # Group the data by 'Moved In By' and count the number of move-ins for each group
    last_week_counts = last_week_data.groupby('Moved In By').size().reset_index(name='count')
    two_weeks_ago_counts = two_weeks_ago_data.groupby('Moved In By').size().reset_index(name='count')

    # Calculate the percentage of Customer Portal move-ins for the last week and two weeks ago
    last_week_total = last_week_counts['count'].sum()
    last_week_portal = last_week_counts[last_week_counts['Moved In By'] == 'Customer Portal']['count'].values[0]
    last_week_portal_percentage = (last_week_portal / last_week_total) 

    two_weeks_ago_total = two_weeks_ago_counts['count'].sum()
    two_weeks_ago_portal = two_weeks_ago_counts[two_weeks_ago_counts['Moved In By'] == 'Customer Portal']['count'].values[0]
    two_weeks_ago_portal_percentage = (two_weeks_ago_portal / two_weeks_ago_total)

    # Calculate the percentage growth
    percentage_growth = ((last_week_portal_percentage - two_weeks_ago_portal_percentage) / two_weeks_ago_portal_percentage)

    return {'last week total move ins':last_week_total, 'last week online move ins':last_week_portal, 'last week % of online move ins':last_week_portal_percentage, 'week over week online move in change':percentage_growth}

def rates_kpi(rate_sql):
    rate_ratio = run_sql_query(rate_sql)
    rate_ratio = rate_ratio.dropna(subset=['street_rate', 'In Place Rate'])
    rate_ratio = rate_ratio.drop(rate_ratio[rate_ratio['nrsf'] == 0].index)

    latest_date = rate_ratio['date'].max()
    last_year = rate_ratio['date'].min()

    rate_ratio_latest_date = rate_ratio[rate_ratio['date'] == latest_date]
    rate_ratio_last_year = rate_ratio[(rate_ratio['date'] > last_year) & (rate_ratio['date'] <= latest_date)]

    street_rate_per_nrsf = rate_ratio_latest_date['street_rate'].sum() / rate_ratio_latest_date['nrsf'].sum() * 12
    street_rate_per_nrsf_last_year = rate_ratio_last_year['street_rate'].sum() / rate_ratio_last_year['nrsf'].sum() * 12

    in_place_rate_per_nrsf = rate_ratio_latest_date['In Place Rate'].sum() / rate_ratio_latest_date['occupied_sf'].sum() * 12
    in_place_rate_per_nrsf_last_year = rate_ratio_last_year['In Place Rate'].sum() / rate_ratio_last_year['occupied_sf'].sum() * 12

    rate_ratio_current = street_rate_per_nrsf / in_place_rate_per_nrsf if in_place_rate_per_nrsf > 0 else 0
    street_rate_growth = (street_rate_per_nrsf - street_rate_per_nrsf_last_year) / street_rate_per_nrsf_last_year if street_rate_per_nrsf_last_year > 0 else 0
    in_place_rate_growth = (in_place_rate_per_nrsf - in_place_rate_per_nrsf_last_year) / in_place_rate_per_nrsf_last_year if in_place_rate_per_nrsf_last_year > 0 else 0
    avg_street_ratio = (street_rate_per_nrsf_last_year / in_place_rate_per_nrsf_last_year) - 1 if in_place_rate_per_nrsf_last_year > 0 else 0
    current_street_ratio = (street_rate_per_nrsf / in_place_rate_per_nrsf) - 1 if in_place_rate_per_nrsf > 0 else 0

    return {
        'street_rate_per_nrsf_latest': street_rate_per_nrsf,
        'street_rate_per_nrsf_last_year': street_rate_per_nrsf_last_year,
        'in_place_rate_per_nrsf_latest': in_place_rate_per_nrsf,
        'in_place_rate_per_nrsf_last_year': in_place_rate_per_nrsf_last_year,
        'rate_ratio_current': rate_ratio_current,
        'street_rate_growth': street_rate_growth,
        'in_place_rate_growth': in_place_rate_growth,
        'LTM_avg_street_in_place_ratio': avg_street_ratio,
        'current_ratio': current_street_ratio
    }


    


