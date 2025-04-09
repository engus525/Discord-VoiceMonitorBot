import discord
from datetime import datetime, timedelta
import pytz
import asyncio
import os
from aiohttp import web

async def health_check(request):
  return web.Response(text="OK", status=200)

async def start_web_server():
  app = web.Application()
  app.router.add_get('/health', health_check)
  runner = web.AppRunner(app)
  await runner.setup()
  site = web.TCPSite(runner, '0.0.0.0', 8000)
  await site.start()

d_intents = discord.Intents.all()
client = discord.Client(intents=d_intents)

KST = pytz.timezone("Asia/Seoul")

user_entry_time = {}
user_total_time = {}


@client.event
async def on_ready():
  print("Bot Started")
  await client.change_presence(status=discord.Status.online, activity=discord.Game("지켜보고 있다.👀"))
  client.loop.create_task(report_every_day())
  client.loop.create_task(start_web_server())



@client.event
async def on_voice_state_update(member, before, after):
  ch = client.get_channel(1359358645137182958)
  if ch is None:
    print("❌ 채널을 찾을 수 없습니다.")
    return

  now_dt = datetime.now(KST)
  hour_12 = now_dt.strftime("%p").replace("AM", "오전").replace("PM", "오후")
  now = now_dt.strftime(f"%Y년 %m월 %d일 {hour_12} %I시 %M분 %S초")

  name = member.nick if member.nick else member.display_name
  name_bold = f"**{name}**"

  # 입장
  if not before.channel and after.channel:
    user_entry_time[member.id] = datetime.now(KST)
    embed = discord.Embed(
        title="✅ 입장",
        description=f"{name_bold} 님이 🎧 **{after.channel.name}** 에 입장하셨습니다!",
        color=discord.Color.green()
    )
    embed.add_field(name="🕒 시간", value=now, inline=False)
    embed.add_field(name="💬 메시지", value=f"파이팅 {name}!", inline=False)
    if member.avatar:
      embed.set_thumbnail(url=member.avatar.url)
    await ch.send(embed=embed)

  # 퇴장
  elif before.channel and not after.channel:
    entry_time = user_entry_time.pop(member.id, None)
    if entry_time:
      duration = datetime.now(KST) - entry_time
      user_total_time[member.id] = user_total_time.get(member.id, timedelta()) + duration

    embed = discord.Embed(
        title="⛔ 퇴장",
        description=f"{name_bold} 님이 🎧 **{before.channel.name}** 에서 퇴장하셨습니다!",
        color=discord.Color.red()
    )
    embed.add_field(name="🕒 시간", value=now, inline=False)
    embed.add_field(name="💬 메시지", value="수고했어! ~~(근데 조금 더 하지?!)~~", inline=False)
    if member.avatar:
      embed.set_thumbnail(url=member.avatar.url)
    await ch.send(embed=embed)

  # 이동
  elif before.channel != after.channel:
    user_entry_time[member.id] = datetime.now(KST)
    embed = discord.Embed(
        title="🔁 이동",
        description=f"{name_bold} 님이 🎧 **{before.channel.name}** → **{after.channel.name}** 로 이동하셨습니다!",
        color=discord.Color.blurple()
    )
    if member.avatar:
      embed.set_thumbnail(url=member.avatar.url)
    await ch.send(embed=embed)


# 매일 자정 현재 누적 시간 출력
async def report_every_day():
  await client.wait_until_ready()
  while not client.is_closed():
    now = datetime.now(KST)
    next_run = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    # next_run = now + timedelta(seconds=5)
    wait_seconds = (next_run - now).total_seconds()
    await asyncio.sleep(wait_seconds)

    ch = client.get_channel(1359420116986626159)
    if ch is None:
      print("❌ 채널을 찾을 수 없습니다.")
      continue

    embed = discord.Embed(
        title="🕛 오늘의 공부 누적 시간",
        description=f"🗓 {datetime.now(KST).strftime('%Y년 %m월 %d일')} 기준",
        color=discord.Color.gold()
    )

    guild = ch.guild
    now = datetime.now(KST)
    updated_totals = {}

    for user_id in set(list(user_total_time.keys()) + list(user_entry_time.keys())):
      total = user_total_time.get(user_id, timedelta())
      if user_id in user_entry_time:
        total += now - user_entry_time[user_id]
      updated_totals[user_id] = int(total.total_seconds())

    if not updated_totals:
      embed.add_field(name="😴 활동 없음", value="오늘은 아무도 음성 채널에 참여하지 않았어요!", inline=False)
    else:
      for user_id, seconds in sorted(updated_totals.items(), key=lambda x: -x[1]):
        member = guild.get_member(user_id)
        if member:
          name = member.nick if member.nick else member.display_name
          hours, remainder = divmod(seconds, 3600)
          minutes, sec = divmod(remainder, 60)
          embed.add_field(
              name=f"🎧 {name}",
              value=f"{hours}시간 {minutes}분 {sec}초 동안 참여했습니다!",
              inline=False
          )

    await ch.send(embed=embed)
    user_total_time.clear()
    user_entry_time.clear()


client.run(os.environ['TOKEN'])