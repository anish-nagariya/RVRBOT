import time
import hikari
import lightbulb
import requests
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

API_KEY = 'nUYXv5ok9YBi2pCtS7HLUt8vd'
SECRET = '3WlCpGZEXBmYhdE03TtIdLgof8H2hlXZa2AB5Q1xHsxBTd6UyE'
BEARER = 'AAAAAAAAAAAAAAAAAAAAAPEPkwEAAAAAmJseUiM4uyRh5pxEd2ISHhZYOB8' \
         '%3Ddmf62L9uNUY1u8nNjEBJZMrVwIggMAemDH8MKOEGSlNGE6tiOq '
last = {'financialjuice': 1606387376615526413}


def make_request(user):
    url = "https://api.twitter.com/2/tweets/search/recent"
    params = {'query': f'from:{user}', 'since_id': last.get(user, )}
    return requests.request("GET", url, params=params, headers={'Authorization': 'Bearer {}'.format(BEARER)}).json()


def recent_tweets(users):
    global last
    tweets = []
    for user in users:
        resp = make_request(user)
        try:
            last[user] = resp['data'][0]['id']
            resp['data'].reverse()
            for tweet in resp['data']:
                if 'RT @BreakingStocks_:' in tweet['text']:
                    tweets.append((user, tweet['text'][:20]))
                else:
                    tweets.append((user, tweet['text']))
        except Exception:
            print(resp)
    return tweets


if __name__ == '__main__':
    server = 994567402916413491
    channel = 1055999718049714337
    users = ['financialjuice']
    recent_tweets(users)
    bot = lightbulb.BotApp(token='MTA1NTk5OTg2ODI4OTY4NzY0Mg.G-KU7R.AQU1dqgWEslNFbEGZmyFt6hNHOGS3u3fsaFovE',
                           default_enabled_guilds=server)


    @bot.listen(hikari.StartedEvent)
    async def on_started(event):
        await bot.rest.create_message(channel, "**Tweets bot has started!**")
        print('Bot has started!')


    sched = AsyncIOScheduler()
    sched.start()


    @sched.scheduled_job(CronTrigger(second="*/15"))
    async def scan_tweets():
        resp = recent_tweets(users)
        for (us, tweet) in resp:
            await bot.rest.create_message(channel, tweet)
            time.sleep(2)
    bot.run()
