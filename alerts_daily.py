# importing necessary libraries
import csv
import time
import hikari
import lightbulb
import pandas as pd
import requests

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta
from multiprocessing import Pool
from polygon import RESTClient

# reading tickers from finviz.csv
tickers = []
for i in csv.reader(open('tickers/finviz1.csv')):
    tickers.append(i[1])

# initializing polygon api client
client = RESTClient('WzgZvYjFFgnsHLsyh4dZGjtgPEmBuHlu')
avg_vol = {}
embeds = []


# function to calculate the daily average trading volume
def precalc_avg(ticker):
    # link to the polygon request link
    resp_ = requests.get(
        f'https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/day/{(datetime.today() - timedelta(days=30)).__format__("%Y-%m-%d")}/{(datetime.today() - timedelta(days=1)).__format__("%Y-%m-%d")}?adjusted=true&sort=asc&limit=50000&apiKey=WzgZvYjFFgnsHLsyh4dZGjtgPEmBuHlu')
    # converting data to dataframe
    try:
        df = pd.DataFrame(resp_.json()['results'])
    except Exception:
        print(ticker)
        return ticker, float('inf')
    return ticker, sum(df['v']) / len(df)


def daily_alerts():
    global embeds
    global avg_vol
    # getting a snapshot for all the tickers in the ticker list
    resp = client.get_snapshot_all(tickers=tickers, market_type='stocks')
    for x in range(len(resp)):
        # checking if current day volume is 4 times the average daily volume
        if resp[x].day.volume / avg_vol[resp[x].ticker] > 4:
            # determining if trend is bull or bear
            var = 'bullish' if resp[x].todays_change > 0 else 'bearish'
            # determining color of embed depending on bearish/bullish trend
            c = hikari.Color(0x50C878) if var == 'bullish' else hikari.Color(0xFF051A)
            # creating embed
            embed = hikari.Embed(description=f"```${resp[x].ticker} has unusual daily volume "
                                             f"and has a {var} trend. Current price is {resp[x].min.close}```",
                                 colour=c,
                                 title=f"${resp[x].ticker}"
                                 )
            # setting embed image to the stock chart
            embed.set_image(
                f"https://charts.finviz.com/chart.ashx?t={resp[x].ticker}")
            embeds.append(embed)
    return


if __name__ == '__main__':
    # initializing multiprocessing pool to speed up process
    p = Pool(8)
    # getting the average daily volume for all tickers through multiprocessing
    resp = p.map(precalc_avg, tickers)
    # storing average daily volume
    for r in resp: avg_vol[r[0]] = r[1]
    # channel id
    # channel = 994586736078377022
    # server = 994567402916413491
    server = 733151193471123518
    channel = 1004163288231329802
    # initializing bot
    bot = lightbulb.BotApp(token='OTk2ODU0MDg1MDMyNjExOTUx.GYD0xP.k94DJj9osUEtDjlFV57bYdV5xX02Dm0Db_WIKk',
                           default_enabled_guilds=server)

    # starting the bot
    @bot.listen(hikari.StartedEvent)
    async def on_started(event):
        await bot.rest.create_message(channel, "**Daily unusual volume bot has started!**")
        print('Bot has started!')

    # command for '/daily'
    @bot.command
    @lightbulb.command('daily', 'Returns the trend of the tickers that have unusual trading volume for the day')
    @lightbulb.implements(lightbulb.SlashCommand)
    async def daily(context):
        await context.respond("**Todays tickers with unusual daily volume**")
        start = time.time()
        global embeds
        embeds = []
        # running daily alerts function
        daily_alerts()
        # printing number of alerts
        print(len(embeds))
        # iterating through the embeds
        for e in embeds:
            try:
                # printing the embeds in discord
                await context.respond(e)
            except Exception as e:
                print(vars(e))
        print(f'Time Taken For Daily: {time.time() - start}')


    # starting time filter so the function runs at specified times
    sched = AsyncIOScheduler()
    sched.start()

    # scheduling job for daily alert
    @sched.scheduled_job(CronTrigger(hour="13", minute="30"))
    async def alert_daily():
        # mentioning time for the alert
        await bot.rest.create_message(channel, "**Daily Alerts 1:30 PM**")
        start = time.time()
        global embeds
        embeds = []
        # running function to check average daily volume strategy
        daily_alerts()
        print(len(embeds))
        # iterating through embeds
        for e in embeds:
            try:
                # sending the embed to discord
                await bot.rest.create_message(channel, e)
            except Exception as e:
                print(vars(e))
        print(f'Time Taken For Daily: {time.time() - start}')

    # scheduling job for daily alert at 10:00
    @sched.scheduled_job(CronTrigger(hour="10", minute="00"))
    async def alert_daily():
        # mentioning the time for the alert
        await bot.rest.create_message(channel, "**Daily Alerts 10:00 AM**")
        start = time.time()
        global embeds
        embeds = []
        # running function to check average daily volume strategy
        daily_alerts()
        print(len(embeds))
        # iterating through the embeds
        for e in embeds:
            try:
                # sending the embed to discord
                await bot.rest.create_message(channel, e)
            except Exception as e:
                print(vars(e))
        print(f'Time Taken For Daily: {time.time() - start}')

    # running bot
    bot.run()
