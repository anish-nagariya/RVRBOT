# importing required libraries and packages
import csv
from datetime import datetime
import sys
import os
import time
import hikari
import lightbulb
import pandas as pd

from polygon import RESTClient
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

# initializing polygon api client
client = RESTClient('WzgZvYjFFgnsHLsyh4dZGjtgPEmBuHlu')

# storing tickers in a list
tickers = []
for i in csv.reader(open('tickers/finviz3.csv')): tickers.append(i[1])

# storing all the embeds here
embeds = []

# storing the support and resistance in this dictionary
support, resistance = {}, {}

# storing previous values for prices
prev = {}


# function for calculating the support/resistance levels of all stocks
def calc_resistance_support():
    # globalizing list of tickers
    global tickers

    # if the fractals are of size 5, and it is a support level
    def issupport(df1, j):
        support_ = df1['low'][j] <= df1['low'][j - 1] <= df1['low'][j - 2] <= df1['low'][j - 3] \
                   and df1['low'][j] <= df1['low'][j + 1] <= df1['low'][j + 2] <= df1['low'][j + 3]
        return support_

    # if the fractals are of size 10, and it is a resistance level
    def isresistance(df1, j):
        resistance_ = df1['high'][j] >= df1['high'][j - 1] >= df1['high'][j - 2] >= df1['high'][j - 3] \
                      and df1['high'][j] >= df1['high'][j + 1] >= df1['high'][j + 2] >= df1['high'][j + 3]
        return resistance_

    # Calculate support and resistance for each ticker
    for t in tickers:
        # initialize the support and resistance levels as an empty list
        support[t] = []
        resistance[t] = []
        # getting daily bars for each ticker
        resp = client.get_aggs(t, 1, 'day', from_='2022-01-01', to=datetime.now())

        # converting daily bars into a dataframe
        df = []
        for x in range(len(resp)):
            df.append([resp[x].close, resp[x].high, resp[x].low])
        df = pd.DataFrame(df, columns=['close', 'high', 'low'])

        # going through each daily bar
        for i in range(4, df.shape[0] - 4):
            # checking each daily bar to see if it is a support level
            if issupport(df, i):
                support[t].append(df['low'][i])
                # support[t] = [df['low'][i], True]

            # checking each daily bar to see if it is a resistance level
            if isresistance(df, i):
                resistance[t].append(df['high'][i])
                # resistance[t] = [df['high'][i], True]

        # if no support levels are found, leaving it as an empty list
        if support.get(t, None) is None:
            support[t] = []

        # if no resistance levels are found, leaving it as an empty list
        if resistance.get(t, None) is None:
            resistance[t] = []

        # sorting the resistance/support levels to find which level has been crossed
        support[t].sort()
        resistance[t].sort(reverse=True)
    return


# function to check through all tickers if they crossed a resistance/support level
def trendline_break():
    global embeds
    global tickers
    global prev

    # getting a snapshot for all tickers
    resp1 = client.get_snapshot_all(tickers=tickers[:1100], market_type='stocks')
    resp2 = client.get_snapshot_all(tickers=tickers[1100:], market_type='stocks')
    resp = resp1 + resp2
    for x in range(len(resp)):
        try:
            # storing last 15-minute prices of the ticker to check the maximum change in the last 15 minutes
            if len(prev.get(resp[x].ticker, [])) < 15:
                if len(prev.get(resp[x].ticker, [])) == 0:
                    prev[resp[x].ticker] = []
                prev[resp[x].ticker].append(resp[x].min.close)
            else:
                prev[resp[x].ticker].pop(0)
                prev[resp[x].ticker].append(resp[x].min.close)
            # checking if volume is met
            if resp[0].day.volume < 750000:
                continue
            # if the current price of the ticker is 1% less than its support price
            if len(support[resp[x].ticker]) != 0 and resp[x].min.close < support[resp[x].ticker][-1] * 0.99:
                # creating an embed for the alert
                embed = hikari.Embed(description=f"```${resp[x].ticker} just crossed the support"
                                                 f" ({support[resp[x].ticker][-1]}). Current price is"
                                                 f" {resp[x].min.close}```",
                                     colour=hikari.Color(0xFF051A),
                                     title=f"${resp[x].ticker}"
                                     )
                embed.set_image(
                    f"https://charts.finviz.com/chart.ashx?t={resp[x].ticker}&p=i5")
                # printing the support, vwap, close values
                print(
                    f'Support, ${resp[x].ticker}, close - {resp[x].min.close}, vwap - {resp[x].min.vwap}, change-{resp[x].min.close / max(prev[resp[x].ticker])}')
                print(prev[resp[x].ticker])
                # checking if close > vwap, price has changed by more than 1%
                if resp[x].min.close > resp[x].min.vwap and resp[x].min.close / max(prev[resp[x].ticker]) <= 0.98:
                    embeds.append(embed)
                # removing all support levels that have been crossed
                while len(support[resp[x].ticker]) and resp[x].min.close < support[resp[x].ticker][-1] * 0.99:
                    support[resp[x].ticker].pop()

            # checking if the current price is 1% more than its resistance level
            elif len(resistance[resp[x].ticker]) != 0 and resp[x].min.close > resistance[resp[x].ticker][-1] * 1.01:
                # creating the embed
                embed = hikari.Embed(description=f"```${resp[x].ticker} just crossed the resistance"
                                                 f" ({resistance[resp[x].ticker][-1]}). Current price is"
                                                 f" {resp[x].min.close}```",
                                     colour=hikari.Color(0x50C878),
                                     title=f"${resp[x].ticker}"
                                     )
                # removing all resistance levels that have been crossed
                while len(resistance[resp[x].ticker]) and resp[x].min.close > resistance[resp[x].ticker][-1] * 1.01:
                    resistance[resp[x].ticker].pop()

                # setting stock chart image for the stock
                embed.set_image(
                    f"https://charts.finviz.com/chart.ashx?t={resp[x].ticker}&p=i5")
                # printing values for the resistance, close, vwap and change price
                print(
                    f'Resistance, ${resp[x].ticker}, close - {resp[x].min.close}, vwap - {resp[x].min.vwap}, change-{resp[x].min.close / min(prev[resp[x].ticker])}')
                print(prev[resp[x].ticker])
                # checking if the close price is more than vwap, current price has changed by at least 1%
                if resp[x].min.close > resp[x].min.vwap and resp[x].min.close / min(prev[resp[x].ticker]) >= 1.02:
                    embeds.append(embed)

        # if any error has occurred, printing the error
        except Exception as e:
            print(e)
            print(resp[x].ticker)
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print(exc_type, fname, exc_tb.tb_lineno)
            return


# calculating the resistance/support levels for all stocks
calc_resistance_support()
print(resistance)
print(support)
time.sleep(10)

# checking all support/resistance levels that have previously been crossed

resp1 = client.get_snapshot_all(tickers=tickers[:1100], market_type='stocks')
resp2 = client.get_snapshot_all(tickers=tickers[1100:], market_type='stocks')
resp = resp1 + resp2
for x in range(len(resp)):
    try:
        while len(resistance[resp[x].ticker]) and resp[x].min.close > resistance[resp[x].ticker][-1]:
            resistance[resp[x].ticker].pop()
        while len(support[resp[x].ticker]) and resp[x].min.close < support[resp[x].ticker][-1]:
            support[resp[x].ticker].pop()
    except Exception as e:
        print(e)

if __name__ == "__main__":
    # channel id to send the messages to
    # server = 994567402916413491
    # channel = 994587041293672558
    channel = 1001900681621426186
    server = 733151193471123518
    # initializing bot
    bot = lightbulb.BotApp(token='',
                           default_enabled_guilds=server)

    # starting bot
    @bot.listen(hikari.StartedEvent)
    async def on_started(event):
        # await bot.rest.create_message(channel, "**Trendline break bot has started!**")
        print('Bot has started!')


    # initializing scheduler to schedule alert scans
    sched = AsyncIOScheduler()
    sched.start()

    # function to run trendline break check
    @sched.scheduled_job(CronTrigger(minute="*/1"))
    async def trendline():
        # checking if timings are met for regular hours
        if 15 <= datetime.now().hour < 21 or datetime.now().hour == 14 and datetime.now().minute > 50:
            start = time.time()
            global embeds
            embeds = []
            # running trendline break function
            trendline_break()

            # sending all alerts to discord channel in the form of embeds
            x = 0
            while x < len(embeds):
                await bot.rest.create_message(channel, embeds=embeds[x:x + 10])
                x += 10
            print(f"Time Taken For Trendline Break: {time.time() - start}")
            print(len(embeds))


    # running bot
    bot.run()
