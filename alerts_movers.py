# installing necessary libraries
import datetime
import time
import hikari
import lightbulb
from webull import webull
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

wb = webull()


# function to get the biggest gainers for today
def todays_gainers():
    # getting request from polygon api link for top 20 gainers
    if datetime.datetime.now().hour < 9:
        wb.login('anishnagariya07@gmail.com', 'Anish#123')
        resp = wb.active_gainer_loser(direction='gainer', rank_type='preMarket', count=10)['data']
        ans = ["**Todays Biggest Gainers**\n"]
        for i in range(len(resp)):
            ans.append(f"```${resp[i]['ticker']['symbol']} | {float(resp[i]['values']['changeRatio'])*100}% | ${resp[i]['values']['price']}```\n")
            ans.append(f"https://charts.finviz.com/chart.ashx?t={resp[i]['ticker']['symbol']}&p=i5")
    else:
        wb.login('anishnagariya07@gmail.com', 'Anish#123')
        resp = wb.active_gainer_loser(direction='gainer', rank_type='1d', count=10)['data']
        ans = ["**Todays Biggest Gainers**\n"]
        for i in range(len(resp)):
            ans.append(f"```${resp[i]['ticker']['symbol']} | {float(resp[i]['values']['changeRatio'])*100}% | ${resp[i]['ticker']['close']}```\n")
            ans.append(f"https://charts.finviz.com/chart.ashx?t={resp[i]['ticker']['symbol']}&p=i5")
    print(ans)
    return ans


# function to get the biggest losers for today
def todays_losers():
    # getting request from polygon api link for top 20 losers
    wb.login('anishnagariya07@gmail.com', 'Anish#123')
    resp = wb.active_gainer_loser(direction='loser', rank_type='1d', count=10)['data']
    ans = ["**Todays Biggest Losers**\n"]
    for i in range(len(resp)):
        ans.append(
            f"```${resp[i]['ticker']['symbol']} | {float(resp[i]['values']['changeRatio']) * 100}% | ${resp[i]['ticker']['close']}```\n")
        ans.append(f"https://charts.finviz.com/chart.ashx?t={resp[i]['ticker']['symbol']}&p=i5")

    print(ans)
    return ans


if __name__ == '__main__':
    # channel id
    # server = 994567402916413491
    # channel = 1000801445865590784
    server = 733151193471123518
    channel = 1004163426102300743
    # initializing the discord bot
    bot = lightbulb.BotApp(token='',
                           default_enabled_guilds=server)

    # starting the discord bot
    @bot.listen(hikari.StartedEvent)
    async def on_started(event):
        # await bot.rest.create_message(channel, "**Biggest movers bot has started!**")
        print('Bot has started!')

    # starting the scheduler to run bot at specified times
    sched = AsyncIOScheduler()
    sched.start()

    # command for '/gainers'
    @bot.command
    @lightbulb.command('gainers', 'Returns the tickers with the biggest gainers')
    @lightbulb.implements(lightbulb.SlashCommand)
    async def gainers(context):
        start = time.time()
        embeds = todays_gainers()
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

    # function to get the biggest gainers for pre-market hours at 7:30
    @sched.scheduled_job(CronTrigger(hour="7", minute="30", jitter=60))
    async def gainers():
        # getting the biggest gainers of today
        embeds = todays_gainers()
        # printing the pre-market movers
        await bot.rest.create_message(channel, "@everyone\n**Pre Market Hours**", mentions_everyone=True)
        for msg in embeds:
            # scanning through each embed and sending it
            await bot.rest.create_message(channel, msg)
            # sleeping time to avoid messing up the message orders
            time.sleep(2)
        time.sleep(30)

    # function to get the biggest gainers for regular hours at 10:00
    @sched.scheduled_job(CronTrigger(hour="10", minute="30", jitter=10))
    async def gainers():
        # getting the biggest gainers of today
        embeds = todays_gainers()
        # printing the regular hours movers
        await bot.rest.create_message(channel, "**Regular Hours**")
        for msg in embeds:
            # scanning through each embed and sending it
            await bot.rest.create_message(channel, msg)
            # sleeping to avoid messing up the message orders
            time.sleep(2)
        time.sleep(30)

    # function to get the biggest losers for regular hours at 3:30
    @sched.scheduled_job(CronTrigger(hour="15", minute="30", jitter=10))
    async def losers():
        # getting the biggest losers of today
        embeds = todays_losers()
        for msg in embeds:
            # scanning through each embed and sending it
            await bot.rest.create_message(channel, msg)

    # running the bot
    bot.run()
