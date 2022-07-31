import numpy as np
import pandas as pd
import requests
import pytz
from datetime import datetime
from numpy.lib.recfunctions import unstructured_to_structured

# Fixed price including tax (cents/kWh)
price_day_fixed = 15.93
price_night_fixed = 11.97

# Market price marginal including tax (cents/kWh)
price_marginal_market = 0.26

# Transmission price including tax
price_trans_day = 7.3     # Elektrilevi Võrk 1 from 01.06.2022
price_trans_night = 7.3


eet = pytz.timezone("Europe/Tallinn")
utc = pytz.UTC

def str2date(dstr):
    date_naive = datetime.strptime(dstr, '%d.%m.%Y %H:%M')
    date_eet = eet.localize(date_naive)
    date_utc = date_eet.astimezone(utc)
    date_np = np.datetime64(date_utc.replace(tzinfo=None))
    return date_np

comma2dot = lambda x: x.replace(',', '.')

consumption = np.genfromtxt('Tunnitarbimise andmed.csv', delimiter=';', skip_header=11, 
    names=True, dtype='M8[m],M8[m],U4,U10,f,U10', encoding='utf-8',
    converters = {0: str2date, 1: str2date, 4: comma2dot})

np_datetime_start = consumption[0][0]
np_datetime_end = consumption[-1][0]

r = requests.get(url = 'https://dashboard.elering.ee/api/nps/price', 
    params = {'start': str(np_datetime_start) + 'Z', 'end': str(np_datetime_end) + 'Z'})

price_np = pd.DataFrame(r.json()['data']['ee']).to_numpy()    # Convert JSON to numpy array with Pandas - any better way of doing this?
price = unstructured_to_structured(price_np, np.dtype([('time', 'M8[s]'), ('price', 'f4')])) # Structured array to convert time to np.datetime64

size_consumption = np.size(consumption['Algusaeg'])
size_price = np.size(price['time'])

if size_consumption != size_price:
    print("Consumption and price arrays do not match in size!")
    if size_consumption > size_price:
        difference = np.isin(consumption['Algusaeg'], price['time'])
    else:
        difference = np.isin(price['time'], consumption['Algusaeg'])
    difference_indexes = np.where(difference == False)
    print(difference_indexes)
    first_difference = difference_indexes[0][0] # Put this into try: to handle exceptions
    print(consumption[first_difference - 1 : first_difference + 2])
    print(price[first_difference - 1 : first_difference + 2])

if np.isin(consumption['Algusaeg'], price['time']).all():
    print("%.1f kWh consumed from %s to %s" % (np.sum(consumption['Tarbimine']), str(np_datetime_start), str(np_datetime_end)))
    avg_price_market_night = np.average(price['price'][consumption['Päevöö'] == 'Öö']) / 10
    avg_price_market_day = np.average(price['price'][consumption['Päevöö'] == 'Päev']) / 10
    print("Average market price at given range %.2f c/kWh night %.2f c/kWh day" % (avg_price_market_night, avg_price_market_day))
    euros_market = consumption['Tarbimine'] * (price['price'] / 10 + price_marginal_market) / 100
    print("Total electricity cost at market price %.2f €" % np.sum(euros_market))
    euros_fixed_night = consumption['Tarbimine'][consumption['Päevöö'] == 'Öö'] * price_night_fixed / 100
    euros_fixed_day = consumption['Tarbimine'][consumption['Päevöö'] == 'Päev'] * price_day_fixed / 100
    print("Electricity cost at fixed night price %.2f €" % np.sum(euros_fixed_night))
    print("Electricity cost at fixed day price %.2f €" % np.sum(euros_fixed_day))
    print("Total electricity cost at fixed price %.2f €" % (np.sum(euros_fixed_night) + np.sum(euros_fixed_day)))
    euros_trans_night = consumption['Tarbimine'][consumption['Päevöö'] == 'Öö'] * price_trans_night / 100
    euros_trans_day = consumption['Tarbimine'][consumption['Päevöö'] == 'Päev'] * price_trans_day / 100
    print("Transmission cost at night price %.2f €" % np.sum(euros_trans_night))
    print("Transmission cost at day price %.2f €" % np.sum(euros_trans_day))
    print("Total transmission cost %.2f €" % (np.sum(euros_trans_night) + np.sum(euros_trans_day)))
    
# TODO: verify if consumption and price times align
# TODO: Visulize price difference
# TODO: Is (average) market price with or without tax?

