# importing required libraries
import csv
from polygon import RESTClient
import time
import hikari
import lightbulb
import pandas as pd
import requests

from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from multiprocessing import Pool

# parsing ticker list from csv file
tickers = []
for i in csv.reader(open('tickers/finviz1.csv')): tickers.append(i[1])

# initializing the polygon api client
client = RESTClient('WzgZvYjFFgnsHLsyh4dZGjtgPEmBuHlu')

# initializing start and end date for 5 minute bars
start_ = datetime.today() - timedelta(days=5)
end = datetime.today() + timedelta(days=1)


def detect_vol(t):
    try:
        # requesting 5-minute bars from polygon
        resp = requests.get(
            f"https://api.polygon.io/v2/aggs/ticker/{t}/range/5/minute/{start_.__format__('%Y-%m-%d')}/{end.__format__('%Y-%m-%d')}?adjusted=true&sort=asc&limit=4998&apiKey=WzgZvYjFFgnsHLsyh4dZGjtgPEmBuHlu")
    except Exception:
        # in the case of an error, printing the details
        print(t)
        resp = requests.get(
            f"https://api.polygon.io/v2/aggs/ticker/{t}/range/5/minute/{start_.__format__('%Y-%m-%d')}/{end.__format__('%Y-%m-%d')}?adjusted=true&sort=asc&limit=4998&apiKey=WzgZvYjFFgnsHLsyh4dZGjtgPEmBuHlu")
        print(resp.json())
        print(vars(resp))
        return
    try:
        # converting data to a dataframe
        df = pd.DataFrame(resp.json()['results'])
    except Exception:
        # in the case of an error, printing the exception
        print(resp.json())
        return
    # converting milliseconds time to datetime
    df['t'] = df['t'].apply(lambda x: datetime.fromtimestamp(x / 1000))
    df = df.set_index('t')

    # parsing data for regular hourus
    df = df.between_time('9:30', '16:00')
    # calculating average volume for the last 5 bars
    x = df.v.iloc[-1] / (sum(df.v.iloc[-6:-1]) / 5)

    # calculating the price change for a stock
    y = df.c.iloc[-1] / df.c.iloc[-2]

    # checking if volume is more than 75% and price change is more than 1.5%
    if datetime.now().hour < 10 and not (y >= 1.05 or y <= 0.95):
        return
    if x >= 1.75 and (y <= 0.985 or y >= 1.015):
        print(
            f"https://api.polygon.io/v2/aggs/ticker/{t}/range/5/minute/{start_.__format__('%Y-%m-%d')}/{end.__format__('%Y-%m-%d')}?adjusted=true&sort=asc&limit=5000&apiKey=WzgZvYjFFgnsHLsyh4dZGjtgPEmBuHlu")
        # creating embed
        embed = hikari.Embed(description=f"```${t} has had an unusual trading volume of {round((x - 1) * 100, 2)}% "
                                         f"in the last 5 minutes. Current price is {df.c.iloc[-1]}```",
                             colour=hikari.Color(0x50C878),
                             title=f"${t}"
                             )

        # stock chart image
        embed.set_image(
            f"https://charts.finviz.com/chart.ashx?t={t}&p=i5")
        return embed


if __name__ == "__main__":
    # initializing the multiprocessing pool
    p = Pool(16)
    # channel id to send the messages to
    # channel = 996878893699047555
    # server = 994567402916413491
    channel = 1001899929138118786
    server = 733151193471123518

    # initializing discord bot
    bot = lightbulb.BotApp(token='',
                           default_enabled_guilds=server)

    # starting bot
    @bot.listen(hikari.StartedEvent)
    async def on_started(event):
        await bot.rest.create_message(channel, "**Unusual volume bot has started!**")
        print('Bot has started!')


    # starting scheduler to schedule the bot running times
    sched = AsyncIOScheduler()
    sched.start()


    @sched.scheduled_job(CronTrigger(minute="*/5"))
    async def unusual_volume():
        # checking if timings are met for regular hours
        if 15 <= datetime.now().hour < 21 or datetime.now().hour == 14 and datetime.now().minute >= 50:
            start = time.time()
            embeds_ = []
            # multiprocessing the function detect_vol for all tickers
            resp = p.map(detect_vol, tickers)

            # adding tickers that have met the criteria to a list of embeds
            for r in resp:
                if r:
                    embeds_.append(r)
            print(f"Time Taken For Unusual Volume: {time.time() - start}")
            print(len(embeds_))

            # sending the embeds on discord
            x = 0
            while x < len(embeds_):
                await bot.rest.create_message(channel, embeds=embeds_[x: x + 10])
                x += 10
            print(f'Time taken for all calculations: {time.time() - start}')

    # running bot
    bot.run()
