import csv
import requests
import pandas as pd
import time
import hikari
import lightbulb
import btalib
import sys
import os
import warnings

from polygon import RESTClient
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from multiprocessing import Pool

warnings.simplefilter(action='ignore', category=FutureWarning)


tickers = []
for i in csv.reader(open('tickers/finviz1.csv')):
    tickers.append(i[1])

repeat = set()
client = RESTClient('W'
                    'zgZvYjFFgnsHLsyh4dZGjtgPEmBuHlu')
start_ = datetime.today() - timedelta(days=2)
end = datetime.today()


def detect_vwap_rsi(t):
    """
    10M Close < 10M VWAP BY 1%
    10M RSI > 10M RSI 5 PERIODS AGO
    10M RSI 5 PERIODS AGO > 10M RSI 10 PERIODS AGO
    10M PRICE LOW < 10M PRICE LOW 5 CANDLES AGO
    10M PRICE LOW 5 CANDLES AGO  < 10M PRICE LOW 10 CANDLES AGO
    """
    try:
        resp_ = requests.get(f"https://api.polygon.io/v2/aggs/ticker/{t}/range/10/minute/{start_.__format__('%Y-%m-%d')}/{end.__format__('%Y-%m-%d')}?adjusted=true&sort=asc&limit=4998&apiKey=WzgZvYjFFgnsHLsyh4dZGjtgPEmBuHlu")
        df = pd.DataFrame(resp_.json()['results'])
        df.rename(columns={'t': 'timestamp'}, inplace=True)
        df['timestamp'] = df['timestamp'].apply(lambda x: datetime.fromtimestamp(x / 1000))
        df = df.set_index('timestamp')
        df = df.between_time('9:30', '16:00')
        ans = []
        if df.l.iloc[-1] < df.l.iloc[-6] < df.l.iloc[-11]:
            # print('Price Low Constraint Passed')
            rsi = btalib.rsi(df.c.tail(50)).df.rsi
            if rsi.iloc[-1] > rsi.iloc[-6] > rsi.iloc[-11]:
                print(f'RSI Constraint Passed For {t}')
                resp_ = requests.get(
                    f"https://api.polygon.io/v2/aggs/ticker/{t}/range/10/minute/{end.__format__('%Y-%m-%d')}/{end.__format__('%Y-%m-%d')}?adjusted=true&sort=asc&limit=4998&apiKey=WzgZvYjFFgnsHLsyh4dZGjtgPEmBuHlu")
                df2 = pd.DataFrame(resp_.json()['results'])
                df2.rename(columns={'t': 'timestamp'}, inplace=True)
                df2['timestamp'] = df2['timestamp'].apply(lambda x: datetime.fromtimestamp(x / 1000))
                df2 = df2.set_index('timestamp')
                df2 = df2.between_time('9:30', '16:00')
                print(df2)
                vol, vp = 0, 0
                for x in range(len(df2)):
                    vol += df2.v[x]
                    vp += df2.v[x] * df.c[x]
                vwap = vp/vol
                print(vp, vol, t)
                if df.c.iloc[-1] <= vwap * 0.99:
                    embed = hikari.Embed(
                        description=f"```${t} has met the criteria for the vwap and rsi strategy. Current "
                                    f"price is {df.c.iloc[-1]}```",
                        colour=hikari.Color(0x50C878),
                        title=f"${t}"
                    )
                    embed.set_image(
                        f"https://charts.finviz.com/chart.ashx?t={t}&p=i30")
                    ans.append(embed)
        return ans
    except Exception as e:
        print(e)
        return []


if __name__ == "__main__":
    p = Pool(16)

    bot = lightbulb.BotApp(token='OTk2OTEzMjQxODE5MTkzMzg2.GhfnRs.n4ZEN0I-THhsdCVCRgZn1xXRRGOOq0LEFpaHRA',
                           default_enabled_guilds=(994567402916413491, 733151193471123518))


    @bot.listen(hikari.StartedEvent)
    async def on_started(event):
        print('Bot has started!')


    sched = AsyncIOScheduler()
    sched.start()


    @sched.scheduled_job(CronTrigger(minute="*/10"))
    async def vwap_rsi():
        if 10 <= datetime.now().hour or datetime.now().hour == 9 and datetime.now().minute > 50:
            start = time.time()
            embeds_ = []
            result = p.map(detect_vwap_rsi, tickers)
            for re in result:
                if len(re) > 0 and re[0].title not in repeat:
                    embeds_.append(re[0])
                    repeat.add(re[0].title)
            print(f"Time Taken For VWAP & RSI: {time.time() - start}")
            print(len(embeds_))
            x = 0
            while x < len(embeds_):
                await bot.rest.create_message(994587018124345414, embeds=embeds_[x: x + 10])
                x += 10
            print(f'Time taken for all calculations: {time.time() - start}')


    bot.run()
