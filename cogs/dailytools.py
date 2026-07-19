import discord
from discord.ext import commands
import datetime
import random
import re

class DailyTools(commands.Cog):
    category = 'utility'

    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db_manager

    @commands.command(name='age', help='Calculate age from a birthdate. Usage: age MM/DD/YYYY')
    async def age(self, ctx, birthdate: str):
        try:
            month, day, year = map(int, birthdate.split('/'))
            bdate = datetime.date(year, month, day)
        except Exception:
            return await ctx.error('Invalid date. Use `MM/DD/YYYY` format.')
        today = datetime.date.today()
        years = today.year - bdate.year - ((today.month, today.day) < (bdate.month, bdate.day))
        days_to_next = (bdate.replace(year=today.year if (bdate.month, bdate.day) >= (today.month, today.day) else today.year + 1) - today).days
        await ctx.send(f'🎂 You are **{years}** years old. Next birthday in **{days_to_next}** days.')

    @commands.command(name='dayofweek', help='Find what day of the week a date falls on.')
    async def dayofweek(self, ctx, date: str):
        try:
            month, day, year = map(int, date.split('/'))
            d = datetime.date(year, month, day)
        except Exception:
            return await ctx.error('Invalid date. Use `MM/DD/YYYY` format.')
        await ctx.send(f'📅 `{date}` falls on a **{d.strftime("%A")}**.')

    @commands.command(name='daysuntil', help='Count days until a future date.')
    async def daysuntil(self, ctx, date: str):
        try:
            month, day, year = map(int, date.split('/'))
            target = datetime.date(year, month, day)
        except Exception:
            return await ctx.error('Invalid date. Use `MM/DD/YYYY` format.')
        today = datetime.date.today()
        delta = (target - today).days
        if delta < 0:
            await ctx.send(f'📅 That date was **{abs(delta)}** days ago.')
        elif delta == 0:
            await ctx.send('📅 That\'s today!')
        else:
            await ctx.send(f'📅 **{delta}** days until `{date}`.')

    @commands.command(name='daycount', help='Count days between two dates.')
    async def daycount(self, ctx, date1: str, date2: str):
        try:
            m1, d1, y1 = map(int, date1.split('/'))
            m2, d2, y2 = map(int, date2.split('/'))
            dt1 = datetime.date(y1, m1, d1)
            dt2 = datetime.date(y2, m2, d2)
        except Exception:
            return await ctx.error('Invalid dates. Use `MM/DD/YYYY` format for both.')
        delta = abs((dt2 - dt1).days)
        await ctx.send(f'📅 There are **{delta}** days between those dates.')

    @commands.command(name='unixtime', help='Convert a date/time to a Unix timestamp.')
    async def unixtime(self, ctx, date: str, time: str = '00:00'):
        try:
            month, day, year = map(int, date.split('/'))
            hour, minute = map(int, time.split(':'))
            dt = datetime.datetime(year, month, day, hour, minute, tzinfo=datetime.timezone.utc)
            ts = int(dt.timestamp())
        except Exception:
            return await ctx.error('Invalid format. Use `MM/DD/YYYY HH:MM`.')
        await ctx.send(f'🕐 Unix timestamp: `{ts}`\nDiscord format: `<t:{ts}:F>` → <t:{ts}:F>')

    @commands.command(name='fromunix', help='Convert a Unix timestamp to a readable date.')
    async def fromunix(self, ctx, timestamp: int):
        try:
            dt = datetime.datetime.fromtimestamp(timestamp, tz=datetime.timezone.utc)
        except Exception:
            return await ctx.error('Invalid timestamp.')
        await ctx.send(f'🕐 `{timestamp}` = **{dt.strftime("%A, %B %d, %Y at %H:%M UTC")}**\n<t:{timestamp}:F>')

    @commands.command(name='worldtime', help='Show current time in major world cities (UTC offsets).')
    async def worldtime(self, ctx):
        now = datetime.datetime.utcnow()
        zones = [
            ('New York', -5), ('Los Angeles', -8), ('London', 0),
            ('Paris', 1), ('Dubai', 4), ('Mumbai', 5.5),
            ('Singapore', 8), ('Tokyo', 9), ('Sydney', 11),
        ]
        lines = []
        for name, offset in zones:
            local = now + datetime.timedelta(hours=offset)
            lines.append(f'**{name}:** `{local.strftime("%H:%M")}`')
        embed = self.bot.embed_manager.generic(description='\n'.join(lines), title='🌍 World Clock')
        await ctx.send(embed=embed)

    @commands.command(name='bmi', help='Calculate BMI. Usage: bmi <weight_kg> <height_cm>')
    async def bmi(self, ctx, weight: float, height: float):
        if weight <= 0 or height <= 0:
            return await ctx.error('Weight and height must be positive.')
        height_m = height / 100
        bmi_val = weight / (height_m ** 2)
        category = 'Underweight' if bmi_val < 18.5 else 'Normal' if bmi_val < 25 else 'Overweight' if bmi_val < 30 else 'Obese'
        await ctx.send(f'⚖️ BMI: **{bmi_val:.1f}** — `{category}`')

    @commands.command(name='calories', help='Estimate daily calorie needs. Usage: calories <weight_kg> <height_cm> <age> <activity_level 1-5>')
    async def calories(self, ctx, weight: float, height: float, age: int, activity: int = 3):
        activity = max(1, min(5, activity))
        multipliers = {1: 1.2, 2: 1.375, 3: 1.55, 4: 1.725, 5: 1.9}
        bmr = 10 * weight + 6.25 * height - 5 * age + 5
        needs = bmr * multipliers[activity]
        await ctx.send(f'🍽️ Estimated daily calorie needs: **{needs:.0f} kcal**')

    @commands.command(name='tip', help='Calculate a tip. Usage: tip <amount> <percent>')
    async def tip(self, ctx, amount: float, percent: float = 15):
        tip_amount = amount * (percent / 100)
        total = amount + tip_amount
        await ctx.send(f'💵 Tip (`{percent}%`): **${tip_amount:.2f}**\nTotal: **${total:.2f}**')

    @commands.command(name='splitbill', help='Split a bill among people. Usage: splitbill <amount> <people>')
    async def splitbill(self, ctx, amount: float, people: int):
        if people < 1:
            return await ctx.error('Number of people must be at least 1.')
        each = amount / people
        await ctx.send(f'💰 Split `${amount:.2f}` among `{people}` people: **${each:.2f}** each.')

    @commands.command(name='percentage', aliases=['percent'], help='Calculate a percentage. Usage: percentage <value> <of>')
    async def percentage(self, ctx, value: float, of: float):
        if of == 0:
            return await ctx.error('Cannot divide by zero.')
        pct = (value / of) * 100
        await ctx.send(f'📊 `{value}` is **{pct:.2f}%** of `{of}`.')

    @commands.command(name='discount', help='Calculate a discounted price. Usage: discount <price> <percent_off>')
    async def discount(self, ctx, price: float, percent_off: float):
        savings = price * (percent_off / 100)
        final = price - savings
        await ctx.send(f'🏷️ Original: `${price:.2f}` | Off: `{percent_off}%`\nYou save: **${savings:.2f}** | Final: **${final:.2f}**')

    @commands.command(name='feettometers', aliases=['ft2m'], help='Convert feet to meters.')
    async def feettometers(self, ctx, feet: float):
        meters = feet * 0.3048
        await ctx.send(f'📏 `{feet} ft` = **{meters:.2f} m**')

    @commands.command(name='meterstofeet', aliases=['m2ft'], help='Convert meters to feet.')
    async def meterstofeet(self, ctx, meters: float):
        feet = meters / 0.3048
        await ctx.send(f'📏 `{meters} m` = **{feet:.2f} ft**')

    @commands.command(name='kgtolbs', help='Convert kilograms to pounds.')
    async def kgtolbs(self, ctx, kg: float):
        lbs = kg * 2.20462
        await ctx.send(f'⚖️ `{kg} kg` = **{lbs:.2f} lbs**')

    @commands.command(name='lbstokg', help='Convert pounds to kilograms.')
    async def lbstokg(self, ctx, lbs: float):
        kg = lbs / 2.20462
        await ctx.send(f'⚖️ `{lbs} lbs` = **{kg:.2f} kg**')

    @commands.command(name='celsiustofahrenheit', aliases=['c2f'], help='Convert Celsius to Fahrenheit.')
    async def celsiustofahrenheit(self, ctx, celsius: float):
        f = (celsius * 9/5) + 32
        await ctx.send(f'🌡️ `{celsius}°C` = **{f:.1f}°F**')

    @commands.command(name='fahrenheittocelsius', aliases=['f2c'], help='Convert Fahrenheit to Celsius.')
    async def fahrenheittocelsius(self, ctx, fahrenheit: float):
        c = (fahrenheit - 32) * 5/9
        await ctx.send(f'🌡️ `{fahrenheit}°F` = **{c:.1f}°C**')

    @commands.command(name='kmtomiles', help='Convert kilometers to miles.')
    async def kmtomiles(self, ctx, km: float):
        miles = km * 0.621371
        await ctx.send(f'🛣️ `{km} km` = **{miles:.2f} mi**')

    @commands.command(name='milestokm', help='Convert miles to kilometers.')
    async def milestokm(self, ctx, miles: float):
        km = miles / 0.621371
        await ctx.send(f'🛣️ `{miles} mi` = **{km:.2f} km**')

    @commands.command(name='passwordgen', aliases=['pwgen2'], help='Generate a secure random password. Usage: passwordgen [length]')
    async def passwordgen(self, ctx, length: int = 16):
        length = max(8, min(64, length))
        import string
        chars = string.ascii_letters + string.digits + '!@#$%^&*()_+-='
        password = ''.join(random.choices(chars, k=length))
        try:
            await ctx.author.send(f'🔐 Your generated password:\n`{password}`')
            await ctx.success(f'{self.bot.e.success} Password sent to your DMs.')
        except discord.Forbidden:
            await ctx.error('Could not DM you. Enable DMs from server members.')

    @commands.command(name='pins', aliases=['pingen'], help='Generate a random numeric PIN. Usage: pins [length]')
    async def pins(self, ctx, length: int = 4):
        length = max(4, min(12, length))
        pin = ''.join([str(random.randint(0, 9)) for _ in range(length)])
        try:
            await ctx.author.send(f'🔢 Your generated PIN: `{pin}`')
            await ctx.success(f'{self.bot.e.success} PIN sent to your DMs.')
        except discord.Forbidden:
            await ctx.error('Could not DM you.')

    @commands.command(name='uuid', help='Generate a random UUID.')
    async def uuid_cmd(self, ctx):
        import uuid
        await ctx.send(f'🆔 `{uuid.uuid4()}`')

    @commands.command(name='coinflip2', aliases=['multiflip'], help='Flip multiple coins at once. Usage: coinflip2 [count]')
    async def coinflip2(self, ctx, count: int = 1):
        count = max(1, min(20, count))
        results = [random.choice(['Heads', 'Tails']) for _ in range(count)]
        heads = results.count('Heads')
        emojis = ['🟡' if r == 'Heads' else '⚪' for r in results]
        await ctx.send(f'{"".join(emojis)}\n**{heads}** heads, **{count - heads}** tails')

    @commands.command(name='diceroll2', aliases=['rolldice'], help='Roll multiple dice. Usage: diceroll2 [count] [sides]')
    async def diceroll2(self, ctx, count: int = 1, sides: int = 6):
        count = max(1, min(20, count))
        sides = max(2, min(1000, sides))
        rolls = [random.randint(1, sides) for _ in range(count)]
        await ctx.send(f'🎲 Rolls: {", ".join(str(r) for r in rolls)}\n**Total:** `{sum(rolls)}`')


    @commands.command(name='inchestocm', help='Convert inches to centimeters.')
    async def inchestocm(self, ctx, inches: float):
        cm = inches * 2.54
        await ctx.send(f'📏 `{inches} in` = **{cm:.2f} cm**')

    @commands.command(name='cmtoinches', help='Convert centimeters to inches.')
    async def cmtoinches(self, ctx, cm: float):
        inches = cm / 2.54
        await ctx.send(f'📏 `{cm} cm` = **{inches:.2f} in**')

    @commands.command(name='ouncestograms', aliases=['oz2g'], help='Convert ounces to grams.')
    async def ouncestograms(self, ctx, oz: float):
        grams = oz * 28.3495
        await ctx.send(f'⚖️ `{oz} oz` = **{grams:.2f} g**')

    @commands.command(name='gramstoounces', aliases=['g2oz'], help='Convert grams to ounces.')
    async def gramstoounces(self, ctx, grams: float):
        oz = grams / 28.3495
        await ctx.send(f'⚖️ `{grams} g` = **{oz:.2f} oz**')

    @commands.command(name='gallonstoliters', help='Convert gallons to liters.')
    async def gallonstoliters(self, ctx, gallons: float):
        liters = gallons * 3.78541
        await ctx.send(f'🪣 `{gallons} gal` = **{liters:.2f} L**')

    @commands.command(name='literstogallons', help='Convert liters to gallons.')
    async def literstogallons(self, ctx, liters: float):
        gallons = liters / 3.78541
        await ctx.send(f'🪣 `{liters} L` = **{gallons:.2f} gal**')

    @commands.command(name='hextodecimal', help='Convert a hex number to decimal.')
    async def hextodecimal(self, ctx, hex_val: str):
        try:
            dec = int(hex_val.replace('0x', '').replace('#', ''), 16)
            await ctx.send(f'🔢 `{hex_val}` = **{dec}** (decimal)')
        except ValueError:
            await ctx.error('Invalid hex value.')

    @commands.command(name='decimaltohex', help='Convert a decimal number to hex.')
    async def decimaltohex(self, ctx, decimal: int):
        await ctx.send(f'🔢 `{decimal}` = **{hex(decimal)}** (hex)')

    @commands.command(name='decimaltobinary', help='Convert a decimal number to binary.')
    async def decimaltobinary(self, ctx, decimal: int):
        await ctx.send(f'🔢 `{decimal}` = **{bin(decimal)}** (binary)')

    @commands.command(name='binarytodecimal', help='Convert a binary number to decimal.')
    async def binarytodecimal(self, ctx, binary_val: str):
        try:
            dec = int(binary_val, 2)
            await ctx.send(f'🔢 `{binary_val}` = **{dec}** (decimal)')
        except ValueError:
            await ctx.error('Invalid binary value.')

    @commands.command(name='sqrt', help='Calculate the square root of a number.')
    async def sqrt(self, ctx, number: float):
        if number < 0:
            return await ctx.error('Cannot take the square root of a negative number.')
        import math
        await ctx.send(f'√`{number}` = **{math.sqrt(number):.4f}**')

    @commands.command(name='power', aliases=['pow2'], help='Calculate a number raised to a power. Usage: power <base> <exponent>')
    async def power(self, ctx, base: float, exponent: float):
        result = base ** exponent
        await ctx.send(f'`{base}^{exponent}` = **{result:.4f}**')

    @commands.command(name='factorial', help='Calculate the factorial of a number.')
    async def factorial(self, ctx, number: int):
        if number < 0 or number > 170:
            return await ctx.error('Number must be between 0 and 170.')
        import math
        await ctx.send(f'`{number}!` = **{math.factorial(number):,}**')

    @commands.command(name='gcd', help='Calculate the greatest common divisor of two numbers.')
    async def gcd(self, ctx, a: int, b: int):
        import math
        await ctx.send(f'GCD(`{a}`, `{b}`) = **{math.gcd(a, b)}**')

    @commands.command(name='lcm', help='Calculate the least common multiple of two numbers.')
    async def lcm(self, ctx, a: int, b: int):
        import math
        result = abs(a * b) // math.gcd(a, b) if a and b else 0
        await ctx.send(f'LCM(`{a}`, `{b}`) = **{result}**')

    @commands.command(name='isprime', help='Check if a number is prime.')
    async def isprime(self, ctx, number: int):
        if number < 2:
            return await ctx.send(f'`{number}` is **not prime**.')
        is_p = all(number % i != 0 for i in range(2, int(number**0.5) + 1))
        await ctx.send(f'`{number}` is **{"prime" if is_p else "not prime"}**.')

    @commands.command(name='fibonacci', help='Show the first N Fibonacci numbers.')
    async def fibonacci(self, ctx, count: int = 10):
        count = max(1, min(50, count))
        seq = [0, 1]
        while len(seq) < count:
            seq.append(seq[-1] + seq[-2])
        await ctx.send(f'🔢 {", ".join(str(n) for n in seq[:count])}')

    @commands.command(name='average', aliases=['mean'], help='Calculate the average of a list of numbers.')
    async def average(self, ctx, *numbers: float):
        if not numbers:
            return await ctx.error('Provide at least one number.')
        avg = sum(numbers) / len(numbers)
        await ctx.send(f'📊 Average of `{len(numbers)}` numbers: **{avg:.2f}**')

    @commands.command(name='median', help='Calculate the median of a list of numbers.')
    async def median(self, ctx, *numbers: float):
        if not numbers:
            return await ctx.error('Provide at least one number.')
        sorted_nums = sorted(numbers)
        n = len(sorted_nums)
        mid = n // 2
        med = sorted_nums[mid] if n % 2 else (sorted_nums[mid-1] + sorted_nums[mid]) / 2
        await ctx.send(f'📊 Median: **{med:.2f}**')


    @commands.command(name='mode', help='Find the most frequent number(s) in a list.')
    async def mode(self, ctx, *numbers: float):
        if not numbers:
            return await ctx.error('Provide at least one number.')
        from collections import Counter
        counts = Counter(numbers)
        max_count = max(counts.values())
        modes = [n for n, c in counts.items() if c == max_count]
        await ctx.send(f'📊 Mode: **{", ".join(str(m) for m in modes)}** (appears `{max_count}` time(s))')

    @commands.command(name='stddev', help='Calculate the standard deviation of a list of numbers.')
    async def stddev(self, ctx, *numbers: float):
        if len(numbers) < 2:
            return await ctx.error('Provide at least two numbers.')
        import statistics
        sd = statistics.stdev(numbers)
        await ctx.send(f'📊 Standard Deviation: **{sd:.4f}**')

    @commands.command(name='range2', help='Calculate the range (max - min) of a list of numbers.')
    async def range2(self, ctx, *numbers: float):
        if not numbers:
            return await ctx.error('Provide at least one number.')
        r = max(numbers) - min(numbers)
        await ctx.send(f'📊 Range: **{r:.2f}** (max: `{max(numbers)}`, min: `{min(numbers)}`)')

    @commands.command(name='sum2', help='Add up a list of numbers.')
    async def sum2(self, ctx, *numbers: float):
        if not numbers:
            return await ctx.error('Provide at least one number.')
        await ctx.send(f'➕ Sum: **{sum(numbers):.2f}**')


    @commands.command(name='roundnum', aliases=['round2'], help='Round a number to N decimal places.')
    async def roundnum(self, ctx, number: float, places: int = 2):
        places = max(0, min(10, places))
        await ctx.send(f'🔢 Rounded: **{round(number, places)}**')

    @commands.command(name='absvalue', aliases=['abs2'], help='Get the absolute value of a number.')
    async def absvalue(self, ctx, number: float):
        await ctx.send(f'🔢 |`{number}`| = **{abs(number)}**')

    @commands.command(name='clamp', help='Clamp a number between a min and max value. Usage: clamp <value> <min> <max>')
    async def clamp(self, ctx, value: float, min_val: float, max_val: float):
        result = max(min_val, min(max_val, value))
        await ctx.send(f'🔢 Clamped: **{result}**')

async def setup(bot):
    await bot.add_cog(DailyTools(bot))
