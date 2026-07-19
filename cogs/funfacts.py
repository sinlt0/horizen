import discord
from discord.ext import commands
import random

FACTS = [
    "Honey never spoils. Archaeologists have found 3,000-year-old honey in Egyptian tombs that's still edible.",
    "Octopuses have three hearts and blue blood.",
    "A group of flamingos is called a flamboyance.",
    "Bananas are berries, but strawberries aren't.",
    "The Eiffel Tower can grow taller in summer due to thermal expansion of the metal.",
    "Wombat poop is cube-shaped.",
    "A day on Venus is longer than a year on Venus.",
    "Sharks existed before trees.",
    "The shortest war in history lasted 38 minutes (Anglo-Zanzibar War, 1896).",
    "Some cats are allergic to humans.",
    "There are more possible chess games than atoms in the observable universe.",
    "The inventor of the Pringles can is buried in one.",
    "Butterflies taste with their feet.",
    "A single strand of spaghetti is called a spaghetto.",
    "The unicorn is the national animal of Scotland.",
    "Oxford University is older than the Aztec Empire.",
    "Cows have best friends and get stressed when separated.",
    "A bolt of lightning is five times hotter than the surface of the sun.",
    "Jellyfish have no brains, hearts, or bones.",
    "Astronauts grow up to 2 inches taller in space.",
    "The longest recorded flight of a chicken is 13 seconds.",
    "A group of crows is called a murder.",
    "Humans share about 60% of their DNA with bananas.",
    "It's impossible to hum while holding your nose closed.",
    "The first oranges weren't orange — they were green.",
    "Dolphins have names for each other.",
    "There's a species of jellyfish that is biologically immortal.",
    "The Great Wall of China is not visible from space with the naked eye.",
    "A blue whale's heart is roughly the size of a small car.",
    "Sea otters hold hands while sleeping so they don't drift apart.",
]

RANDOM_KNOWLEDGE = [
    ("Who painted the Sistine Chapel ceiling?", "Michelangelo"),
    ("What is the largest planet in our solar system?", "Jupiter"),
    ("What year did World War II end?", "1945"),
    ("What is the chemical symbol for iron?", "Fe"),
    ("Who wrote '1984'?", "George Orwell"),
    ("What is the smallest country in the world?", "Vatican City"),
    ("How many bones are in the adult human body?", "206"),
    ("What is the longest river in the world?", "The Nile"),
    ("Who developed the theory of relativity?", "Albert Einstein"),
    ("What is the capital of Australia?", "Canberra"),
]

DID_YOU_KNOW_SCIENCE = [
    "Light from the Sun takes about 8 minutes and 20 seconds to reach Earth.",
    "The human brain uses about 20% of the body's total energy.",
    "There are more stars in the universe than grains of sand on all of Earth's beaches.",
    "Water can boil and freeze at the same time under the right pressure (triple point).",
    "A teaspoon of neutron star material would weigh about 6 billion tons.",
    "DNA in a single human cell, if stretched out, would be about 2 meters long.",
    "Some metals are so reactive they explode on contact with water.",
    "The Andromeda Galaxy is on a collision course with the Milky Way.",
]

HISTORY_FACTS = [
    "Cleopatra lived closer in time to the Moon landing than to the construction of the Great Pyramid.",
    "Oxford University was already teaching students before the Aztec Empire existed.",
    "The Great Fire of London in 1666 destroyed most of the city but killed very few people.",
    "Napoleon was actually average height for his era — the 'short' myth came from British propaganda.",
    "Vikings used the bones of slain animals to make ice skates.",
    "Ancient Romans used urine as a mouthwash ingredient due to its ammonia content.",
    "The shortest reigning monarch in history ruled for only 20 minutes.",
]


class FunFacts(commands.Cog):
    category = 'fun'

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='funfact', aliases=['fact2'], help='Get a random fun fact.')
    async def funfact(self, ctx):
        embed = discord.Embed(description=f'💡 {random.choice(FACTS)}', color=discord.Color.blue())
        await ctx.send(embed=embed)

    @commands.command(name='sciencefact', help='Get a random science fact.')
    async def sciencefact(self, ctx):
        embed = discord.Embed(description=f'🔬 {random.choice(DID_YOU_KNOW_SCIENCE)}', color=discord.Color.teal())
        await ctx.send(embed=embed)

    @commands.command(name='historyfact', help='Get a random history fact.')
    async def historyfact(self, ctx):
        embed = discord.Embed(description=f'📜 {random.choice(HISTORY_FACTS)}', color=discord.Color.dark_gold())
        await ctx.send(embed=embed)

    @commands.command(name='knowledgetest', aliases=['quicktrivia'], help='Answer a quick knowledge question.')
    async def knowledgetest(self, ctx):
        q, a = random.choice(RANDOM_KNOWLEDGE)
        await ctx.send(f'🧠 **{q}**\nYou have 15 seconds!')

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        try:
            msg = await self.bot.wait_for('message', timeout=15, check=check)
        except Exception:
            return await ctx.send(f'⏱️ Time\'s up! The answer was **{a}**.')

        if a.lower() in msg.content.lower():
            await ctx.send(f'✅ Correct! The answer was **{a}**.')
        else:
            await ctx.send(f'❌ Wrong! The answer was **{a}**.')

    @commands.command(name='todayinhistory', aliases=['onthisday'], help='Get a random historical "on this day" style fact.')
    async def todayinhistory(self, ctx):
        events = [
            "1969 — Apollo 11 astronauts became the first humans to walk on the Moon.",
            "1989 — The Berlin Wall began to fall.",
            "1912 — The Titanic sank on its maiden voyage.",
            "1776 — The United States Declaration of Independence was adopted.",
            "1928 — Alexander Fleming discovered penicillin.",
            "1990 — The World Wide Web became publicly available.",
            "1957 — The Soviet Union launched Sputnik 1, the first artificial satellite.",
        ]
        embed = discord.Embed(description=f'📅 {random.choice(events)}', color=discord.Color.orange())
        await ctx.send(embed=embed)

    @commands.command(name='wouldurather2', aliases=['wyr2'], help='Get a fresh Would You Rather question.')
    async def wouldurather2(self, ctx):
        pairs = [
            ('have super strength', 'have super speed'),
            ('live without music', 'live without movies'),
            ('always be 10 minutes late', 'always be 20 minutes early'),
            ('know how you will die', 'know when you will die'),
            ('be able to talk to animals', 'be able to speak every human language'),
        ]
        a, b = random.choice(pairs)
        await ctx.send(f'🤔 Would you rather **{a}** or **{b}**?')

    @commands.command(name='mythbust', help='Get a common myth debunked.')
    async def mythbust(self, ctx):
        myths = [
            ("Myth: We only use 10% of our brains.", "Fact: Brain scans show we use virtually all of it, just not all at once."),
            ("Myth: Goldfish have a 3-second memory.", "Fact: Goldfish can remember things for months."),
            ("Myth: Bulls hate the color red.", "Fact: Bulls are colorblind to red — they react to movement."),
            ("Myth: You lose most of your body heat through your head.", "Fact: Heat loss is roughly proportional to skin surface exposed."),
            ("Myth: Sugar makes kids hyperactive.", "Fact: Multiple studies found no link between sugar and hyperactivity."),
        ]
        myth, fact = random.choice(myths)
        embed = discord.Embed(description=f'❌ {myth}\n✅ {fact}', color=discord.Color.red())
        await ctx.send(embed=embed)

    @commands.command(name='factcheck', help='Get a surprising true fact you probably didn\'t know.')
    async def factcheck(self, ctx):
        embed = discord.Embed(description=f'🔎 {random.choice(FACTS + DID_YOU_KNOW_SCIENCE)}', color=discord.Color.green())
        await ctx.send(embed=embed)

    @commands.command(name='animalfact', help='Get a random animal fact.')
    async def animalfact(self, ctx):
        animal_facts = [
            "A shrimp's heart is located in its head.",
            "Elephants are the only mammals that can't jump.",
            "A group of pandas is called an embarrassment.",
            "Koalas sleep up to 22 hours a day.",
            "A snail can sleep for three years.",
            "Cows produce more milk when they listen to music.",
            "Owls don't have eyeballs — they have eye tubes that can't move.",
            "Starfish don't have brains or blood.",
            "Giraffes only sleep about 30 minutes a day.",
            "Penguins propose to their mates with a pebble.",
        ]
        embed = discord.Embed(description=f'🐾 {random.choice(animal_facts)}', color=discord.Color.gold())
        await ctx.send(embed=embed)

    @commands.command(name='spacefact', help='Get a random space fact.')
    async def spacefact(self, ctx):
        space_facts = [
            "One day on Mercury lasts about 176 Earth days.",
            "Saturn could float in water because it's mostly gas.",
            "There's a planet made of diamonds called 55 Cancri e.",
            "The footprints on the Moon will last millions of years — there's no wind to erase them.",
            "Neutron stars can spin at 600 rotations per second.",
            "The Sun accounts for 99.86% of the mass in our solar system.",
            "A year on Neptune equals about 165 Earth years.",
            "Space is completely silent — there's no medium for sound to travel through.",
        ]
        embed = discord.Embed(description=f'🚀 {random.choice(space_facts)}', color=discord.Color.dark_blue())
        await ctx.send(embed=embed)

    @commands.command(name='foodfact', help='Get a random food fact.')
    async def foodfact(self, ctx):
        food_facts = [
            "Carrots were originally purple, not orange.",
            "Honey is the only food that never spoils.",
            "Apples float because they're 25% air.",
            "Chocolate was once used as currency by the Aztecs.",
            "Peanuts aren't actually nuts — they're legumes.",
            "White chocolate isn't technically chocolate — it has no cocoa solids.",
            "The world's most expensive spice is saffron.",
            "Pineapples take about 2 years to grow.",
        ]
        embed = discord.Embed(description=f'🍽️ {random.choice(food_facts)}', color=discord.Color.orange())
        await ctx.send(embed=embed)

    @commands.command(name='techfact', help='Get a random technology fact.')
    async def techfact(self, ctx):
        tech_facts = [
            "The first computer mouse was made of wood.",
            "The first 1GB hard drive weighed over 500 pounds.",
            "More than 90% of the world's currency is digital, not physical.",
            "The first webcam was invented to monitor a coffee pot at Cambridge University.",
            "The QWERTY keyboard layout was designed to slow typists down to prevent jams on typewriters.",
            "The first computer virus was created in 1983 as an experiment.",
            "More people have mobile phones than have access to clean toilets.",
        ]
        embed = discord.Embed(description=f'💻 {random.choice(tech_facts)}', color=discord.Color.purple())
        await ctx.send(embed=embed)

    @commands.command(name='bodyfact', help='Get a random human body fact.')
    async def bodyfact(self, ctx):
        body_facts = [
            "Your nose can remember 50,000 different scents.",
            "The human heart beats about 100,000 times a day.",
            "Your bones are about five times stronger than steel of the same weight.",
            "The acid in your stomach is strong enough to dissolve metal.",
            "You produce about 1.5 liters of saliva every day.",
            "Your body has enough iron in it to make a 3-inch nail.",
            "Fingernails grow nearly 4 times faster than toenails.",
        ]
        embed = discord.Embed(description=f'🫀 {random.choice(body_facts)}', color=discord.Color.red())
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(FunFacts(bot))
