# importing necessary libraries
import csv
import time
import hikari
import lightbulb
import requests
import aiohttp
import asyncio
import pandas as pd
import nest_asyncio

from datetime import datetime, timedelta
from polygon import RESTClient
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from multiprocessing import Pool

# using nest_asyncio for asynchronous calls
nest_asyncio.apply()

# polygon api client initialization
client = RESTClient('WzgZvYjFFgnsHLsyh4dZGjtgPEmBuHlu')

avg = {}


def precalc_avg(ticker):
    # link to the polygon request link
    resp_ = requests.get(
        f'https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/day/{(datetime.today() - timedelta(days=30)).__format__("%Y-%m-%d")}/{(datetime.today() - timedelta(days=1)).__format__("%Y-%m-%d")}?adjusted=true&sort=asc&limit=50000&apiKey=WzgZvYjFFgnsHLsyh4dZGjtgPEmBuHlu')
    # converting data to dataframe
    try:
        df = pd.DataFrame(resp_.json()['results'])
    except Exception:
        # print(ticker)
        return ticker, float('inf')
    return ticker, sum(df['v']) / len(df)


# storing tickers in a ticker array
tickers = []
for i in csv.reader(open('tickers/finviz2.csv')):
    tickers.append(i[1])
tickers = tickers[1:]

# set to make sure gap up extended hours are not repeating tickers
repeat = set()

# storing prices of tickers to check price changes
prev = {}


# function to run gap up for regular hours
def regular():
    global prev
    # storing embeds hear
    embeds = []
    # storing snapshot of all 4000 tickers in embeds
    resp = []
    # iterating through every 1000 tickers because polygon limit is around 1000 tickers
    j = 0
    while j < 3001:
        resp += client.get_snapshot_all(tickers=tickers[j:j + 1000], market_type='stocks')
        j += 1000
    # iterating through each of the tickers
    for i in range(len(resp)):
        # checking if no trade has occurred and price is just at 0
        if resp[i].min.close == 0:
            print(resp[i].ticker)
            continue
        # checking if price has increase by more than 10% in the last 20 minutes
        if resp[i].min.close > prev.get(resp[i].ticker, [resp[i].min.close])[0] * 1.1:
            if resp[i].prev_day.volume > 500000:
                # printing result in console
                print(resp[i].min, resp[i].ticker, resp[i])
                # creating embed for the alert
                embed = hikari.Embed(
                    description=f"```${resp[i].ticker} has had an unusual price increase of {((resp[i].min.close / prev.get(resp[i].ticker, [resp[i].min.close])[0]) - 1) * 100}%"
                                f"in the last 20 minutes. Current price is {resp[i].min.close}```",
                    colour=hikari.Color(0x50C878),
                    title=f"${resp[i].ticker}"
                )

                # stock chart image
                embed.set_image(
                    f"https://charts.finviz.com/chart.ashx?t={resp[i].ticker}&p=i5")
                # adding embed to all embeds
                embeds.append(embed)
                # clearing the previous prices to make sure tickers are not repeated
                prev[resp[i].ticker] = []
        # initializing previous prices array as an empty array if it is the first time
        if not prev.get(resp[i].ticker):
            prev[resp[i].ticker] = []
        # keeping track of the last 20-minute price close to check price change percentage
        prev[resp[i].ticker].append(resp[i].min.close)
        if len(prev[resp[i].ticker]) > 20:
            prev[resp[i].ticker] = prev[resp[i].ticker][1:]
    # print(prev)
    return embeds


# gap up function for extended hours
def extended():
    # storing all embeds
    embeds = []
    # checking if we are currently in after hours or pre-market, and then assigning proper times
    curr = True
    if datetime.now().hour > 16:
        start = datetime.today().strftime('%Y-%m-%d') + ' 16:00:01'
    else:
        start = (datetime.today() - timedelta(days=1)).strftime('%Y-%m-%d') + ' 16:00:01'
        curr = False
    # getting snapshot for all 400 tickers, doing it 1000 at a time because of polygon limits
    quotes1 = requests.get(
        f"https://api.polygon.io/v2/snapshot/locale/us/markets/stocks/tickers?tickers={','.join(tickers[:1000])}&apiKey=WzgZvYjFFgnsHLsyh4dZGjtgPEmBuHlu").json()[
        'tickers']
    quotes2 = requests.get(
        f"https://api.polygon.io/v2/snapshot/locale/us/markets/stocks/tickers?tickers={','.join(tickers[1000:2000])}&apiKey=WzgZvYjFFgnsHLsyh4dZGjtgPEmBuHlu").json()[
        'tickers']
    quotes3 = requests.get(
        f"https://api.polygon.io/v2/snapshot/locale/us/markets/stocks/tickers?tickers={','.join(tickers[2000:3000])}&apiKey=WzgZvYjFFgnsHLsyh4dZGjtgPEmBuHlu").json()[
        'tickers']
    quotes4 = requests.get(
        f"https://api.polygon.io/v2/snapshot/locale/us/markets/stocks/tickers?tickers={','.join(tickers[3000:])}&apiKey=WzgZvYjFFgnsHLsyh4dZGjtgPEmBuHlu").json()[
        'tickers']
    # combining all 4 1000 snapshots
    quotes = quotes1 + quotes2 + quotes3 + quotes4
    # storing previous day close or today's close depending on whether we are in ah/pm
    q = {}
    for i in range(len(quotes)):
        if curr:
            q[quotes[i]['ticker']] = quotes[i]['day']
        else:
            q[quotes[i]['ticker']] = quotes[i]['prevDay']

    # fetching tasks for asynchronous calls
    def get_tasks(session, stocks):
        tasks = []
        # storing days to go back for premarket/afterhours data
        d = timedelta(days=1)
        # adding request link to tasks to get extended hours data
        for t in stocks:
            tasks.append(session.get(f"https://api.polygon.io/v2/aggs/ticker/{t}/range/1/minute/"
                                     f"{(datetime.today() - d).strftime('%Y-%m-%d')}/"
                                     f"{datetime.today().strftime('%Y-%m-%d')}?"
                                     f"adjusted=true&sort=asc&limit=5000&apiKey=WzgZvYjFFgnsHLsyh4dZGjtgPEmBuHlu"))
        return tasks

    async def check():
        # initializing asynchronous session to get all requests
        async with aiohttp.ClientSession() as session:
            # getting all tasks we need
            tasks = get_tasks(session, tickers)
            print('Fetched all tasks, 91')
            # fetching the response for each task in tasks
            responses = await asyncio.gather(*tasks)
            print('Received all responses')
            # iterating through each of the responses
            for resp in responses:
                # parsing the json data
                r = await resp.json()
                try:
                    # converting the json data to a dataframe
                    df = pd.DataFrame(r['results'])
                    # converting the milliseconds time to year-month-day format
                    df['t'] = df['t'].apply(lambda x: datetime.fromtimestamp(x / 1000))
                    # setting dataframe time as index
                    df = df.set_index('t')
                    # parsing data to only look at extended hour times
                    df = df.loc[(df.index > start)]
                    # checking if extended hours price is more/less than day close by at least 1%
                    if df['c'][-1] / q[r['ticker']]['c'] > 1.01 or df['c'][-1] / q[r['ticker']]['c'] < 0.99:
                        if q[r['ticker']]['v'] == 0:
                            continue
                        print('Passed Constraint One')
                        # checking if extended hours' volume is at least half of regular daily volume
                        if sum(df['v']) >= 2 * q[r['ticker']]['v']:
                            # initializing embed with the extended hours volume, daliy volume and current price
                            embed = hikari.Embed(
                                description=f"```${r['ticker']} has met the criteria for premarket/afterhours gap up, "
                                            f"day volume is {q[r['ticker']]['v']}, current extended volume is "
                                            f"{sum(df['v'])}, current price is ${df['c'][-1]}```",
                                colour=hikari.Color(0x50C878),
                                title=f"${r['ticker']}"
                            )
                            # setting embed image as stock chart
                            embed.set_image(
                                f"https://charts.finviz.com/chart.ashx?t={r['ticker']}&p=i5")
                            embeds.append(embed)
                # if any exception occurs, ignoring it
                except Exception as e:
                    pass
                    # print(e)

    # initializing asyncio loop policy
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    # executing the asynchronous calls
    asyncio.run(check())
    return embeds


if __name__ == '__main__':
    # initializing multiprocessing pool
    p = Pool(16)
    resp = p.map(precalc_avg, tickers)
    for r in resp: avg[r[0]] = r[1]
    print(len(tickers))
    # initializing discord bot
    server = 994567402916413491
    channel = 994586936910028910
    # server = 733151193471123518
    bot = lightbulb.BotApp(token='OTk2ODYxOTI1MjAxODEzNjQ1.GQi1WX.RDVwF0VpFuIRA4d3QB3_z1k-0lOXQVg06Xm_Qk',
                           default_enabled_guilds=server)

    # starting bot
    @bot.listen(hikari.StartedEvent)
    async def on_started(event):
        regular()
        await bot.rest.create_message(channel, "**Gap up bot has started!**")
        print('Bot has started!')


    # starting scheduler to run gap up at specified times
    sched = AsyncIOScheduler()
    sched.start()

    # method to run gap up
    @sched.scheduled_job(CronTrigger(minute="*/1"))
    async def gapup():
        # channel name of message
        start = time.time()
        # checking if we are running extended hours alerts or regular hours
        if datetime.now().hour >= 16 or datetime.now().hour < 9 or datetime.now().hour == 9 \
                and datetime.now().minute < 30:
            embeds2 = extended()
            # scanning through embeds for extended hours to make sure we are not repeating
            embeds = []
            for x in embeds2:
                if x.title not in repeat:
                    embeds.append(x)
                    repeat.add(x.title)
        else:
            if datetime.now().hour == 9 and datetime.now().minute < 45:
                return
            # getting regular hours alerts
            embeds = regular()
        # printing number of alerts
        print(len(embeds))
        # sending embeds to discord
        x = 0
        while x < len(embeds):
            # await bot.rest.create_message(channel, embeds=embeds, content='@everyone')
            await bot.rest.create_message(channel, embeds=embeds[x: x + 10])
            x += 10
        print(time.time() - start)


    # running bot
    bot.run()
