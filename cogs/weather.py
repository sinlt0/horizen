import discord
from discord.ext import commands
import aiohttp
import datetime

WIND_DIRECTIONS = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE',
                   'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW']

def wind_dir(deg):
    idx = round(deg / 22.5) % 16
    return WIND_DIRECTIONS[idx]

def weather_emoji(code):
    if code < 300: return '⛈️'
    if code < 400: return '🌧️'
    if code < 600: return '🌧️'
    if code < 700: return '❄️'
    if code < 800: return '🌫️'
    if code == 800: return '☀️'
    return '☁️'

class Weather(commands.Cog):
    category = 'utility'

    def __init__(self, bot):
        self.bot = bot
        self._session = None

    async def cog_load(self):
        self._session = aiohttp.ClientSession()

    def cog_unload(self):
        if self._session:
            self.bot.loop.create_task(self._session.close())

    async def _fetch_weather(self, city, units='metric'):
        key = getattr(self.bot.config, 'OPENWEATHER_API_KEY', None)
        if not key:
            return None, 'OpenWeather API key not configured.'
        try:
            url = f'https://api.openweathermap.org/data/2.5/weather?q={city}&appid={key}&units={units}'
            async with self._session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as r:
                if r.status == 404:
                    return None, f'City `{city}` not found.'
                if r.status == 401:
                    return None, 'Invalid API key.'
                if r.status != 200:
                    return None, 'Weather service unavailable.'
                return await r.json(), None
        except Exception:
            return None, 'Weather service unavailable.'

    @commands.command(name='currentweather', help='Get current weather for a city.')
    async def weather_cmd(self, ctx, *, city: str):
        data, error = await self._fetch_weather(city)
        if error:
            return await ctx.error(error)
        temp = data['main']['temp']
        feels = data['main']['feels_like']
        humidity = data['main']['humidity']
        wind_speed = data['wind']['speed']
        wind_d = wind_dir(data['wind'].get('deg', 0))
        desc_text = data['weather'][0]['description'].capitalize()
        code = data['weather'][0]['id']
        emoji = weather_emoji(code)
        country = data['sys']['country']
        name = data['name']
        sunrise = datetime.datetime.utcfromtimestamp(data['sys']['sunrise']).strftime('%H:%M UTC')
        sunset = datetime.datetime.utcfromtimestamp(data['sys']['sunset']).strftime('%H:%M UTC')

        embed = discord.Embed(
            title=f'{emoji} Weather in {name}, {country}',
            description=f'**{desc_text}**',
            color=discord.Color.blue()
        )
        embed.add_field(name='🌡️ Temperature', value=f'`{temp:.1f}°C` (feels `{feels:.1f}°C`)', inline=True)
        embed.add_field(name='💧 Humidity', value=f'`{humidity}%`', inline=True)
        embed.add_field(name='💨 Wind', value=f'`{wind_speed} m/s {wind_d}`', inline=True)
        embed.add_field(name='🌅 Sunrise', value=f'`{sunrise}`', inline=True)
        embed.add_field(name='🌇 Sunset', value=f'`{sunset}`', inline=True)
        embed.add_field(name='👁️ Visibility', value=f'`{data.get("visibility", 0) // 1000} km`', inline=True)
        embed.set_footer(text='Source: OpenWeatherMap')
        await ctx.send(embed=embed)

    @commands.command(name='weatherf', aliases=['weatherus'], help='Get current weather in Fahrenheit for a city.')
    async def weather_f(self, ctx, *, city: str):
        data, error = await self._fetch_weather(city, units='imperial')
        if error:
            return await ctx.error(error)
        temp = data['main']['temp']
        feels = data['main']['feels_like']
        desc_text = data['weather'][0]['description'].capitalize()
        code = data['weather'][0]['id']
        emoji = weather_emoji(code)
        country = data['sys']['country']
        name = data['name']
        embed = discord.Embed(
            title=f'{emoji} Weather in {name}, {country}',
            description=f'**{desc_text}**\n`{temp:.1f}°F` (feels `{feels:.1f}°F`)',
            color=discord.Color.blue()
        )
        embed.add_field(name='💧 Humidity', value=f'`{data["main"]["humidity"]}%`', inline=True)
        embed.add_field(name='💨 Wind', value=f'`{data["wind"]["speed"]} mph`', inline=True)
        embed.set_footer(text='Source: OpenWeatherMap')
        await ctx.send(embed=embed)

    @commands.command(name='weatherset', help='Save your default city for weather commands.')
    async def weatherset(self, ctx, *, city: str):
        await self.bot.db_manager.update_one('user_weather', {'_id': ctx.author.id}, {'city': city}, upsert=True)
        await ctx.success(f'{self.bot.e.success} Default city set to **{city}**.')

    @commands.command(name='myweather', help='Get weather for your saved default city.')
    async def myweather(self, ctx):
        data = await self.bot.db_manager.find_one('user_weather', {'_id': ctx.author.id})
        if not data or not data.get('city'):
            return await ctx.error('No default city set. Use `weatherset <city>` first.')
        await ctx.invoke(self.weather_cmd, city=data['city'])

    @commands.command(name='citytz', aliases=['cityzone'], help='Get the current time in a city or timezone.')
    async def timezone(self, ctx, *, city: str):
        data, error = await self._fetch_weather(city)
        if error:
            return await ctx.error(error)
        offset_seconds = data.get('timezone', 0)
        local_time = datetime.datetime.utcnow() + datetime.timedelta(seconds=offset_seconds)
        hours, remainder = divmod(abs(offset_seconds), 3600)
        sign = '+' if offset_seconds >= 0 else '-'
        embed = self.bot.embed_manager.generic(
            description=(
                f'**City:** {data["name"]}, {data["sys"]["country"]}\n'
                f'**Local Time:** `{local_time.strftime("%H:%M:%S")}`\n'
                f'**Date:** `{local_time.strftime("%A, %B %d %Y")}`\n'
                f'**UTC Offset:** `UTC{sign}{hours:02d}:{remainder//60:02d}`'
            ),
            title='🕐 Timezone'
        )
        await ctx.send(embed=embed)

    @commands.command(name='humidity', help='Get the humidity for a city.')
    async def humidity(self, ctx, *, city: str):
        data, error = await self._fetch_weather(city)
        if error:
            return await ctx.error(error)
        h = data['main']['humidity']
        bar_len = 20
        filled = int((h / 100) * bar_len)
        bar = '█' * filled + '░' * (bar_len - filled)
        await ctx.send(f'💧 **Humidity in {data["name"]}:** `{h}%`\n{bar}')

    @commands.command(name='windspeed', help='Get the wind speed for a city.')
    async def windspeed(self, ctx, *, city: str):
        data, error = await self._fetch_weather(city)
        if error:
            return await ctx.error(error)
        speed = data['wind']['speed']
        deg = data['wind'].get('deg', 0)
        await ctx.send(f'💨 **Wind in {data["name"]}:** `{speed} m/s` heading `{wind_dir(deg)}`')

    @commands.command(name='uvindex', help='Get approximate UV index info for a city.')
    async def uvindex(self, ctx, *, city: str):
        data, error = await self._fetch_weather(city)
        if error:
            return await ctx.error(error)
        clouds = data.get('clouds', {}).get('all', 0)
        estimated = max(0, round((1 - clouds / 100) * 10, 1))
        levels = [(0, 2, 'Low 🟢'), (3, 5, 'Moderate 🟡'), (6, 7, 'High 🟠'), (8, 10, 'Very High 🔴'), (11, 99, 'Extreme 🟣')]
        level = next(label for lo, hi, label in levels if lo <= estimated <= hi)
        await ctx.send(f'☀️ **Estimated UV Index in {data["name"]}:** `{estimated}` — {level}')

    @commands.command(name='aqi', help='Get approximate air quality information for a city.')
    async def aqi(self, ctx, *, city: str):
        key = getattr(self.bot.config, 'OPENWEATHER_API_KEY', None)
        if not key:
            return await ctx.error('OpenWeather API key not configured.')
        data, error = await self._fetch_weather(city)
        if error:
            return await ctx.error(error)
        lat = data['coord']['lat']
        lon = data['coord']['lon']
        try:
            url = f'http://api.openweathermap.org/data/2.5/air_pollution?lat={lat}&lon={lon}&appid={key}'
            async with self._session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as r:
                if r.status != 200:
                    return await ctx.error('AQI data unavailable.')
                aqi_data = await r.json()
            aqi_val = aqi_data['list'][0]['main']['aqi']
            labels = {1: 'Good 🟢', 2: 'Fair 🟡', 3: 'Moderate 🟠', 4: 'Poor 🔴', 5: 'Very Poor 🟣'}
            label = labels.get(aqi_val, 'Unknown')
            components = aqi_data['list'][0]['components']
            embed = self.bot.embed_manager.generic(
                description=(
                    f'**AQI Level:** {label}\n'
                    f'**CO:** `{components.get("co", 0):.1f}` μg/m³\n'
                    f'**NO₂:** `{components.get("no2", 0):.1f}` μg/m³\n'
                    f'**PM2.5:** `{components.get("pm2_5", 0):.1f}` μg/m³\n'
                    f'**PM10:** `{components.get("pm10", 0):.1f}` μg/m³'
                ),
                title=f'🌫️ Air Quality — {data["name"]}'
            )
            await ctx.send(embed=embed)
        except Exception:
            await ctx.error('AQI data unavailable.')

async def setup(bot):
    await bot.add_cog(Weather(bot))
