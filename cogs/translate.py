import discord
from discord.ext import commands
import aiohttp

LANGUAGE_CODES = {
    'english': 'en', 'spanish': 'es', 'french': 'fr', 'german': 'de',
    'italian': 'it', 'portuguese': 'pt', 'russian': 'ru', 'japanese': 'ja',
    'korean': 'ko', 'chinese': 'zh', 'arabic': 'ar', 'hindi': 'hi',
    'dutch': 'nl', 'polish': 'pl', 'turkish': 'tr', 'vietnamese': 'vi',
    'thai': 'th', 'indonesian': 'id', 'greek': 'el', 'swedish': 'sv',
    'bengali': 'bn', 'urdu': 'ur', 'hebrew': 'he', 'finnish': 'fi',
    'norwegian': 'no', 'danish': 'da', 'czech': 'cs', 'romanian': 'ro',
    'hungarian': 'hu', 'ukrainian': 'uk',
}

MORSE_CODE = {
    'A': '.-', 'B': '-...', 'C': '-.-.', 'D': '-..', 'E': '.', 'F': '..-.',
    'G': '--.', 'H': '....', 'I': '..', 'J': '.---', 'K': '-.-', 'L': '.-..',
    'M': '--', 'N': '-.', 'O': '---', 'P': '.--.', 'Q': '--.-', 'R': '.-.',
    'S': '...', 'T': '-', 'U': '..-', 'V': '...-', 'W': '.--', 'X': '-..-',
    'Y': '-.--', 'Z': '--..', '0': '-----', '1': '.----', '2': '..---',
    '3': '...--', '4': '....-', '5': '.....', '6': '-....', '7': '--...',
    '8': '---..', '9': '----.', ' ': '/',
}
MORSE_REVERSE = {v: k for k, v in MORSE_CODE.items()}

PIG_LATIN_VOWELS = 'aeiouAEIOU'

LEET_MAP = {'a': '4', 'e': '3', 'i': '1', 'o': '0', 's': '5', 't': '7', 'l': '1', 'g': '9'}


class Translate(commands.Cog):
    category = 'utility'

    def __init__(self, bot):
        self.bot = bot
        self._session = None

    async def cog_load(self):
        self._session = aiohttp.ClientSession()

    def cog_unload(self):
        if self._session:
            self.bot.loop.create_task(self._session.close())

    @commands.command(name='translatetext', aliases=['tr3'], help='Translate text. Usage: translate <language> <text>')
    async def translate(self, ctx, language: str, *, text: str):
        lang = language.lower()
        code = LANGUAGE_CODES.get(lang, lang if len(lang) == 2 else None)
        if not code:
            return await ctx.error(f'Unknown language. Try a full name (`spanish`) or 2-letter code (`es`).')
        try:
            url = f'https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl={code}&dt=t&q={text}'
            async with self._session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as r:
                if r.status != 200:
                    return await ctx.error('Translation service unavailable.')
                data = await r.json()
                translated = ''.join([seg[0] for seg in data[0]])
                detected_lang = data[2] if len(data) > 2 else 'unknown'
        except Exception:
            return await ctx.error('Translation failed. Try again later.')

        embed = self.bot.embed_manager.generic(
            description=f'**Original** (`{detected_lang}`):\n{text[:500]}\n\n**Translated** (`{code}`):\n{translated[:500]}',
            title='🌐 Translation'
        )
        await ctx.send(embed=embed)

    @commands.command(name='languages', aliases=['langs'], help='List all supported translation languages.')
    async def languages(self, ctx):
        desc = '\n'.join([f'`{code}` — {name.capitalize()}' for name, code in LANGUAGE_CODES.items()])
        embed = self.bot.embed_manager.generic(description=desc, title='🌐 Supported Languages')
        await ctx.send(embed=embed)

    @commands.command(name='morseencode', help='Convert text to Morse code.')
    async def morse(self, ctx, *, text: str):
        result = ' '.join([MORSE_CODE.get(c.upper(), '') for c in text if c.upper() in MORSE_CODE or c == ' '])
        if not result.strip():
            return await ctx.error('No convertible characters found.')
        await ctx.send(f'```\n{result[:1990]}\n```')

    @commands.command(name='unmorse', help='Convert Morse code back to text.')
    async def unmorse(self, ctx, *, code: str):
        words = code.split('/')
        result = []
        for word in words:
            letters = word.strip().split()
            result.append(''.join([MORSE_REVERSE.get(l, '') for l in letters]))
        text = ' '.join(result).strip()
        if not text:
            return await ctx.error('Invalid Morse code.')
        await ctx.send(f'```\n{text[:1990]}\n```')

    @commands.command(name='piglatin', help='Convert text to Pig Latin.')
    async def piglatin(self, ctx, *, text: str):
        words = text.split()
        result = []
        for word in words:
            if not word.isalpha():
                result.append(word)
                continue
            if word[0] in PIG_LATIN_VOWELS:
                result.append(word + 'way')
            else:
                idx = 0
                while idx < len(word) and word[idx] not in PIG_LATIN_VOWELS:
                    idx += 1
                result.append(word[idx:] + word[:idx] + 'ay')
        await ctx.send(' '.join(result))

    @commands.command(name='leetspeak', aliases=['1337'], help='Convert text to leetspeak.')
    async def leetspeak(self, ctx, *, text: str):
        result = ''.join([LEET_MAP.get(c.lower(), c) for c in text])
        await ctx.send(result)

    @commands.command(name='reverse3', aliases=['bckwrds'], help='Reverse the given text.')
    async def reverse2(self, ctx, *, text: str):
        await ctx.send(text[::-1])

    @commands.command(name='textbinary', help='Convert text to binary.')
    async def binary(self, ctx, *, text: str):
        result = ' '.join([format(ord(c), '08b') for c in text])
        await ctx.send(f'```\n{result[:1990]}\n```')

    @commands.command(name='unbinary', help='Convert binary back to text.')
    async def unbinary(self, ctx, *, binary_str: str):
        try:
            chars = binary_str.split()
            text = ''.join([chr(int(b, 2)) for b in chars])
            await ctx.send(f'```\n{text[:1990]}\n```')
        except Exception:
            await ctx.error('Invalid binary string.')

    @commands.command(name='nato', aliases=['phonetic'], help='Spell text using the NATO phonetic alphabet.')
    async def nato(self, ctx, *, text: str):
        nato_map = {
            'a': 'Alpha', 'b': 'Bravo', 'c': 'Charlie', 'd': 'Delta', 'e': 'Echo',
            'f': 'Foxtrot', 'g': 'Golf', 'h': 'Hotel', 'i': 'India', 'j': 'Juliett',
            'k': 'Kilo', 'l': 'Lima', 'm': 'Mike', 'n': 'November', 'o': 'Oscar',
            'p': 'Papa', 'q': 'Quebec', 'r': 'Romeo', 's': 'Sierra', 't': 'Tango',
            'u': 'Uniform', 'v': 'Victor', 'w': 'Whiskey', 'x': 'X-ray', 'y': 'Yankee', 'z': 'Zulu'
        }
        words = []
        for c in text.lower():
            if c in nato_map:
                words.append(nato_map[c])
            elif c == ' ':
                words.append('/')
            elif c.isdigit():
                words.append(c)
        await ctx.send(' '.join(words[:50]))

async def setup(bot):
    await bot.add_cog(Translate(bot))
