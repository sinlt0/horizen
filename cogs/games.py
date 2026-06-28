import discord
from discord.ext import commands
import random
import asyncio

BLACKJACK_VALUES = {'2':2,'3':3,'4':4,'5':5,'6':6,'7':7,'8':8,'9':9,'10':10,'J':10,'Q':10,'K':10,'A':11}
SUITS = ['♠','♥','♦','♣']

def build_deck():
    return [f'{v}{s}' for s in SUITS for v in ['2','3','4','5','6','7','8','9','10','J','Q','K','A']]

def hand_value(hand):
    vals = [BLACKJACK_VALUES[c[:-1] if len(c)>1 else c[0]] for c in hand]
    total = sum(vals)
    aces = vals.count(11)
    while total > 21 and aces:
        total -= 10
        aces -= 1
    return total

def format_hand(hand):
    return ' '.join([f'`{c}`' for c in hand])

HANGMAN_WORDS = ['python','discord','programming','keyboard','monitor','elephant','waterfall','universe','javascript','algorithm','database','framework','developer','community','adventure','mountain','chocolate','telephone','butterfly','president']

TRIVIA_QUESTIONS = [
    ('What is the capital of Japan?', 'tokyo'),
    ('How many sides does a hexagon have?', '6'),
    ('What is the largest planet in our solar system?', 'jupiter'),
    ('What is 12 multiplied by 12?', '144'),
    ('Who wrote Romeo and Juliet?', 'shakespeare'),
    ('What is the chemical symbol for gold?', 'au'),
    ('What is the fastest land animal?', 'cheetah'),
    ('How many continents are there?', '7'),
    ('What is the boiling point of water in Celsius?', '100'),
    ('What language does Discord use for its API?', 'http'),
    ('What planet is closest to the sun?', 'mercury'),
    ('What is the square root of 144?', '12'),
    ('In what year did World War 2 end?', '1945'),
    ('What is the powerhouse of the cell?', 'mitochondria'),
    ('How many bones are in the human body?', '206'),
    ('What is the largest ocean?', 'pacific'),
    ('What gas do plants absorb?', 'carbon dioxide'),
    ('Who painted the Mona Lisa?', 'da vinci'),
    ('What is the longest river in the world?', 'nile'),
    ('How many players are in a basketball team?', '5'),
]

WOULD_YOU_RATHER = [
    ('be able to fly', 'be invisible'),
    ('never sleep again', 'never eat again'),
    ('have unlimited money', 'have unlimited knowledge'),
    ('be 10 years older', 'be 10 years younger'),
    ('lose all your money', 'lose all your memories'),
    ('speak every language', 'play every instrument'),
    ('explore space', 'explore the deep ocean'),
    ('have no internet', 'have no phone'),
    ('be famous', 'be rich'),
    ('live in the past', 'live in the future'),
]

DARES = [
    'Do 10 push-ups right now.',
    'Send a voice message singing a song.',
    'Change your nickname to something embarrassing for 1 hour.',
    'Type a paragraph using only your elbows.',
    'Speak in rhymes for the next 5 minutes.',
    'Write a love poem about your keyboard.',
    'Do your best robot impression in chat.',
    'Type the alphabet backwards from memory.',
    'Make up a fake country and describe it in detail.',
    'Roast the next person who sends a message.',
]

TRUTHS = [
    'What is your most embarrassing moment?',
    'Have you ever lied to a friend?',
    'What is your biggest fear?',
    'Have you ever cheated on a test?',
    'What is the most childish thing you still do?',
    'Have you ever blamed someone else for something you did?',
    'What is your most useless talent?',
    'Have you ever stalked someone on social media?',
    'What is the weirdest dream you have had?',
    'What is something you have never told anyone?',
]

EIGHT_BALL_RESPONSES = [
    'It is certain.','It is decidedly so.','Without a doubt.','Yes, definitely.',
    'You may rely on it.','As I see it, yes.','Most likely.','Outlook good.',
    'Yes.','Signs point to yes.','Reply hazy, try again.','Ask again later.',
    'Better not tell you now.','Cannot predict now.','Concentrate and ask again.',
    "Don't count on it.",'My reply is no.','My sources say no.',
    'Outlook not so good.','Very doubtful.',
]

class BlackjackView(discord.ui.View):
    def __init__(self, bot, ctx, player_hand, dealer_hand, deck):
        super().__init__(timeout=60)
        self.bot = bot
        self.ctx = ctx
        self.player_hand = player_hand
        self.dealer_hand = dealer_hand
        self.deck = deck
        self.ended = False

    def build_embed(self, result=None):
        pval = hand_value(self.player_hand)
        dval = hand_value(self.dealer_hand)
        desc = (
            f'**Your Hand:** {format_hand(self.player_hand)} — `{pval}`\n'
            f'**Dealer:** {format_hand(self.dealer_hand if result else [self.dealer_hand[0], "❓"])} — `{dval if result else "?"}`'
        )
        if result:
            desc += f'\n\n{result}'
        color = discord.Color.green() if result and 'win' in result.lower() else discord.Color.red() if result and ('bust' in result.lower() or 'lose' in result.lower()) else discord.Color.gold()
        embed = discord.Embed(title='🃏 Blackjack', description=desc, color=color)
        return embed

    @discord.ui.button(label='Hit', style=discord.ButtonStyle.primary, emoji='🃏')
    async def hit(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author or self.ended:
            return await interaction.response.send_message('Not your game!', ephemeral=True)
        self.player_hand.append(self.deck.pop())
        pval = hand_value(self.player_hand)
        if pval > 21:
            self.ended = True
            for c in self.children: c.disabled = True
            return await interaction.response.edit_message(embed=self.build_embed('💥 Bust! You lose.'), view=self)
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(label='Stand', style=discord.ButtonStyle.danger, emoji='🛑')
    async def stand(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author or self.ended:
            return await interaction.response.send_message('Not your game!', ephemeral=True)
        self.ended = True
        while hand_value(self.dealer_hand) < 17:
            self.dealer_hand.append(self.deck.pop())
        pval = hand_value(self.player_hand)
        dval = hand_value(self.dealer_hand)
        if dval > 21 or pval > dval:
            result = f'🎉 You win! `{pval}` vs `{dval}`'
        elif pval == dval:
            result = f'🤝 Push! Tie at `{pval}`'
        else:
            result = f'😔 You lose! `{pval}` vs `{dval}`'
        for c in self.children: c.disabled = True
        await interaction.response.edit_message(embed=self.build_embed(result), view=self)


class HangmanView(discord.ui.View):
    STAGES = ['```\n  +---+\n  |   |\n      |\n      |\n      |\n      |\n=========```','```\n  +---+\n  |   |\n  O   |\n      |\n      |\n      |\n=========```','```\n  +---+\n  |   |\n  O   |\n  |   |\n      |\n      |\n=========```','```\n  +---+\n  |   |\n  O   |\n /|   |\n      |\n      |\n=========```','```\n  +---+\n  |   |\n  O   |\n /|\\  |\n      |\n      |\n=========```','```\n  +---+\n  |   |\n  O   |\n /|\\  |\n /    |\n      |\n=========```','```\n  +---+\n  |   |\n  O   |\n /|\\  |\n / \\  |\n      |\n=========```']

    def __init__(self, bot, ctx, word):
        super().__init__(timeout=120)
        self.bot = bot
        self.ctx = ctx
        self.word = word
        self.guessed = set()
        self.wrong = 0
        self.ended = False

    def display(self):
        return ' '.join([c if c in self.guessed else '_' for c in self.word])

    def build_embed(self, result=None):
        display = self.display()
        wrong_letters = ' '.join([f'`{l}`' for l in sorted(self.guessed) if l not in self.word]) or 'None'
        desc = f'{self.STAGES[self.wrong]}\n**Word:** `{display}`\n**Wrong guesses:** {wrong_letters}'
        if result:
            desc += f'\n\n{result}'
        embed = discord.Embed(title='🪓 Hangman', description=desc, color=discord.Color.orange())
        return embed

    @discord.ui.button(label='Guess Letter', style=discord.ButtonStyle.primary, emoji='🔤')
    async def guess_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author or self.ended:
            return await interaction.response.send_message('Not your game!', ephemeral=True)

        class GuessModal(discord.ui.Modal, title='Guess a Letter'):
            letter = discord.ui.TextInput(label='Letter', min_length=1, max_length=1)

        modal = GuessModal()
        await interaction.response.send_modal(modal)
        await modal.wait()
        letter = modal.letter.value.lower()
        if not letter.isalpha():
            return
        if letter in self.guessed:
            return
        self.guessed.add(letter)
        if letter not in self.word:
            self.wrong += 1
        display = self.display()
        if '_' not in display:
            self.ended = True
            for c in self.children: c.disabled = True
            return await interaction.edit_original_response(embed=self.build_embed(f'🎉 You won! The word was `{self.word}`.'), view=self)
        if self.wrong >= 6:
            self.ended = True
            for c in self.children: c.disabled = True
            return await interaction.edit_original_response(embed=self.build_embed(f'💀 You lost! The word was `{self.word}`.'), view=self)
        await interaction.edit_original_response(embed=self.build_embed(), view=self)


class Games(commands.Cog):
    category = 'fun'

    def __init__(self, bot):
        self.bot = bot
        self._active_games = {}

    @commands.command(name='blackjack', aliases=['bj2'], help='Play a game of blackjack against the dealer.')
    async def blackjack(self, ctx):
        deck = build_deck()
        random.shuffle(deck)
        player = [deck.pop(), deck.pop()]
        dealer = [deck.pop(), deck.pop()]
        view = BlackjackView(self.bot, ctx, player, dealer, deck)
        await ctx.send(embed=view.build_embed(), view=view)

    @commands.command(name='hangman', aliases=['hm'], help='Play a game of hangman.')
    async def hangman(self, ctx):
        word = random.choice(HANGMAN_WORDS)
        view = HangmanView(self.bot, ctx, word)
        await ctx.send(embed=view.build_embed(), view=view)

    @commands.command(name='wordchain', help='Start a word chain game. Each word must start with the last letter of the previous.')
    async def wordchain(self, ctx):
        await ctx.send('🔤 **Word Chain!** I\'ll start: `apple`\nEach word must start with the last letter of the previous. You have 30 seconds per turn. Type `stop` to end.')
        last_word = 'apple'
        used = {'apple'}
        while True:
            def check(m):
                return m.author == ctx.author and m.channel == ctx.channel
            try:
                msg = await self.bot.wait_for('message', timeout=30, check=check)
            except asyncio.TimeoutError:
                return await ctx.send(f'⏱️ Time\'s up! The last word was `{last_word}`.')
            word = msg.content.lower().strip()
            if word == 'stop':
                return await ctx.send(f'Game ended! Last word: `{last_word}`. You used `{len(used)}` words.')
            if not word.isalpha():
                await ctx.send('Only letters please!', delete_after=3)
                continue
            if word[0] != last_word[-1]:
                return await ctx.send(f'❌ `{word}` doesn\'t start with `{last_word[-1]}`! Game over.')
            if word in used:
                return await ctx.send(f'❌ `{word}` was already used! Game over.')
            used.add(word)
            last_word = word
            await msg.add_reaction('✅')

    @commands.command(name='numguess', aliases=['numbergame', 'ng'], help='Guess the number the bot is thinking of (1-100).')
    async def numguess(self, ctx):
        number = random.randint(1, 100)
        attempts = 0
        await ctx.send('🔢 I\'m thinking of a number between **1** and **100**. You have **7** attempts!')

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content.isdigit()

        while attempts < 7:
            try:
                msg = await self.bot.wait_for('message', timeout=30, check=check)
            except asyncio.TimeoutError:
                return await ctx.send(f'⏱️ Time\'s up! The number was **{number}**.')
            guess = int(msg.content)
            attempts += 1
            remaining = 7 - attempts
            if guess == number:
                return await ctx.send(f'🎉 Correct! It was **{number}**! You got it in **{attempts}** attempt{"s" if attempts != 1 else ""}!')
            elif guess < number:
                await ctx.send(f'📈 Too low! {remaining} attempt{"s" if remaining != 1 else ""} left.')
            else:
                await ctx.send(f'📉 Too high! {remaining} attempt{"s" if remaining != 1 else ""} left.')
        await ctx.send(f'💀 Out of attempts! The number was **{number}**.')

    @commands.command(name='scramble', aliases=['wordscramble'], help='Unscramble the jumbled word.')
    async def scramble(self, ctx):
        word = random.choice(HANGMAN_WORDS)
        letters = list(word)
        random.shuffle(letters)
        scrambled = ''.join(letters)
        while scrambled == word:
            random.shuffle(letters)
            scrambled = ''.join(letters)
        await ctx.send(f'🔀 Unscramble this word: **`{scrambled}`**\nYou have **30 seconds**!')

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        try:
            msg = await self.bot.wait_for('message', timeout=30, check=check)
        except asyncio.TimeoutError:
            return await ctx.send(f'⏱️ Time\'s up! The word was **{word}**.')

        if msg.content.lower().strip() == word:
            await ctx.send(f'🎉 Correct! The word was **{word}**!')
        else:
            await ctx.send(f'❌ Nope! The word was **{word}**.')

    @commands.command(name='fasttype', aliases=['typingtest', 'typerace'], help='Test your typing speed.')
    async def fasttype(self, ctx):
        sentences = [
            'the quick brown fox jumps over the lazy dog',
            'discord is a great platform for communities',
            'programming is the art of telling a computer what to do',
            'practice makes perfect when learning new skills',
            'the best way to predict the future is to create it',
        ]
        sentence = random.choice(sentences)
        await ctx.send(f'⌨️ **Typing Test!** Type this exactly:\n```\n{sentence}\n```\nTimer starts now!')
        start = asyncio.get_event_loop().time()

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        try:
            msg = await self.bot.wait_for('message', timeout=60, check=check)
        except asyncio.TimeoutError:
            return await ctx.send('⏱️ Time\'s up!')

        elapsed = asyncio.get_event_loop().time() - start
        if msg.content.strip() == sentence:
            wpm = int((len(sentence.split()) / elapsed) * 60)
            await ctx.send(f'✅ Correct! Time: **{elapsed:.2f}s** — **{wpm} WPM**')
        else:
            await ctx.send(f'❌ Incorrect! Time: **{elapsed:.2f}s**\nExpected: `{sentence}`')

    @commands.command(name='akinator', aliases=['aki'], help='Think of something and the bot will try to guess it with Yes/No questions.')
    async def akinator(self, ctx):
        questions = [
            ('Is it a living thing?', True),
            ('Is it an animal?', True),
            ('Does it have four legs?', True),
            ('Is it commonly kept as a pet?', True),
        ]
        guesses = {'yes': 0, 'no': 0}
        await ctx.send('🧞 **Akinator!** Think of something. Answer with `yes` or `no`.\n\nIs it something **real** (not fictional)?')

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() in ('yes','no','y','n','stop')

        for q, _ in questions[:3]:
            try:
                msg = await self.bot.wait_for('message', timeout=20, check=check)
            except asyncio.TimeoutError:
                return await ctx.send('⏱️ Timed out.')
            if msg.content.lower() in ('stop',):
                return await ctx.send('Game cancelled.')
            if msg.content.lower() in ('yes','y'):
                guesses['yes'] += 1
            else:
                guesses['no'] += 1
            await ctx.send(q)

        try:
            await self.bot.wait_for('message', timeout=20, check=check)
        except asyncio.TimeoutError:
            return await ctx.send('⏱️ Timed out.')

        if guesses['yes'] >= 2:
            await ctx.send('🎯 I think you\'re thinking of a **dog**! Was I right?')
        else:
            await ctx.send('🤔 I\'m not sure... I give up! What were you thinking of?')

    @commands.command(name='rps2', aliases=['rps3', 'rockpaperscissors2'], help='Play Rock Paper Scissors against the bot.')
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def rps(self, ctx, choice: str):
        choices = ['rock', 'paper', 'scissors']
        choice = choice.lower()
        if choice not in choices:
            return await ctx.error('Choose `rock`, `paper`, or `scissors`.')
        bot_choice = random.choice(choices)
        emojis = {'rock': '🪨', 'paper': '📄', 'scissors': '✂️'}
        if choice == bot_choice:
            result = "🤝 It's a tie!"
        elif (choice == 'rock' and bot_choice == 'scissors') or \
             (choice == 'paper' and bot_choice == 'rock') or \
             (choice == 'scissors' and bot_choice == 'paper'):
            result = '🎉 You win!'
        else:
            result = '😔 You lose!'
        embed = self.bot.embed_manager.generic(
            description=f'You: {emojis[choice]} **{choice}**\nBot: {emojis[bot_choice]} **{bot_choice}**\n\n{result}',
            title='Rock Paper Scissors'
        )
        await ctx.send(embed=embed)

    @commands.command(name='neverhaveiever', aliases=['nhie2'], help='Play Never Have I Ever with a random statement.')
    async def neverhaveiever(self, ctx):
        statements = [
            'gone skydiving', 'eaten sushi', 'pulled an all-nighter coding',
            'forgotten someone\'s name mid-conversation', 'sent a message to the wrong person',
            'pretended to be busy to avoid someone', 'cried at a movie',
            'eaten an entire pizza by myself', 'ghosted someone',
            'stayed up past 3am for no reason',
        ]
        stmt = random.choice(statements)
        embed = self.bot.embed_manager.generic(
            description=f'**Never have I ever... {stmt}**\n\nReact with 🤚 if you have!',
            title='🙅 Never Have I Ever'
        )
        msg = await ctx.send(embed=embed)
        await msg.add_reaction('🤚')

    @commands.command(name='wouldyou', aliases=['wy'], help='Get a Would You Rather question.')
    async def wouldyou(self, ctx):
        a, b = random.choice(WOULD_YOU_RATHER)
        embed = self.bot.embed_manager.generic(
            description=f'🅰️ **{a.capitalize()}**\n\nor\n\n🅱️ **{b.capitalize()}**',
            title='🤔 Would You Rather...'
        )
        msg = await ctx.send(embed=embed)
        await msg.add_reaction('🅰️')
        await msg.add_reaction('🅱️')

    @commands.command(name='truth2', aliases=['tr2'], help='Get a random truth question.')
    async def truth2(self, ctx, member: discord.Member = None):
        target = member or ctx.author
        q = random.choice(TRUTHS)
        embed = self.bot.embed_manager.generic(
            description=f'**{target.mention}:** {q}',
            title='💬 Truth'
        )
        await ctx.send(embed=embed)

    @commands.command(name='dare2', aliases=['dr2'], help='Get a random dare.')
    async def dare2(self, ctx, member: discord.Member = None):
        target = member or ctx.author
        d = random.choice(DARES)
        embed = self.bot.embed_manager.generic(
            description=f'**{target.mention}:** {d}',
            title='🎯 Dare'
        )
        await ctx.send(embed=embed)

    @commands.command(name='quiz', aliases=['trivia2'], help='Get a random trivia question.')
    async def quiz(self, ctx):
        q, a = random.choice(TRIVIA_QUESTIONS)
        embed = self.bot.embed_manager.generic(description=f'**{q}**\nYou have **15 seconds**!', title='🧠 Trivia')
        await ctx.send(embed=embed)

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        try:
            msg = await self.bot.wait_for('message', timeout=15, check=check)
        except asyncio.TimeoutError:
            return await ctx.send(f'⏱️ Time\'s up! The answer was **{a}**.')

        if a.lower() in msg.content.lower():
            await ctx.send(f'🎉 Correct! The answer was **{a}**.')
        else:
            await ctx.send(f'❌ Wrong! The answer was **{a}**.')

    @commands.command(name='coinbet', aliases=['bet', 'gamble'], help='Bet heads or tails. Usage: coinbet heads')
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def coinbet(self, ctx, side: str):
        side = side.lower()
        if side not in ('heads', 'tails', 'h', 't'):
            return await ctx.error('Choose `heads` or `tails`.')
        side = 'heads' if side in ('heads', 'h') else 'tails'
        result = random.choice(['heads', 'tails'])
        emoji = '🟡' if result == 'heads' else '⚪'
        if result == side:
            await ctx.success(f'{emoji} It\'s **{result}**! You win!')
        else:
            await ctx.error(f'{emoji} It\'s **{result}**! You lose.')

    @commands.command(name='slotmachine', aliases=['slot2', 'slots2'], help='Spin the slot machine.')
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def slotmachine(self, ctx):
        symbols = ['🍒','🍋','🍊','🍇','⭐','💎','7️⃣']
        reels = [random.choice(symbols) for _ in range(3)]
        display = ' | '.join(reels)
        if reels[0] == reels[1] == reels[2]:
            if reels[0] == '💎':
                result = '💰 **JACKPOT!** Triple diamonds!'
            elif reels[0] == '7️⃣':
                result = '🎰 **BIG WIN!** Triple sevens!'
            else:
                result = f'🎉 **Winner!** Triple {reels[0]}!'
        elif reels[0] == reels[1] or reels[1] == reels[2]:
            result = '✨ Small win! Two in a row.'
        else:
            result = '😔 No match. Try again!'
        embed = self.bot.embed_manager.generic(
            description=f'[ {display} ]\n\n{result}',
            title='🎰 Slot Machine'
        )
        await ctx.send(embed=embed)

    @commands.command(name='rpg', help='Quick RPG battle against a random enemy.')
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def rpg(self, ctx):
        enemies = [('Goblin', 30), ('Orc', 50), ('Dragon', 80), ('Skeleton', 25), ('Troll', 60)]
        enemy, ehp = random.choice(enemies)
        php = 100
        php_start = php
        log = []
        while php > 0 and ehp > 0:
            pdmg = random.randint(10, 25)
            edmg = random.randint(5, 20)
            ehp -= pdmg
            php -= edmg
            log.append(f'⚔️ You deal `{pdmg}` dmg | {enemy} deals `{edmg}` dmg')
        log = log[:5]
        if php > 0:
            result = f'🏆 **Victory!** You defeated the **{enemy}** with `{php}` HP remaining!'
        else:
            result = f'💀 **Defeated!** The **{enemy}** won with `{ehp if ehp > 0 else 0}` HP remaining.'
        embed = self.bot.embed_manager.generic(
            description='\n'.join(log) + f'\n\n{result}',
            title=f'⚔️ RPG Battle vs {enemy}'
        )
        await ctx.send(embed=embed)

    @commands.command(name='checkers', aliases=['c4', 'connect4'], help='Start a Connect 4 game against another member.')
    async def checkers(self, ctx, opponent: discord.Member):
        if opponent.bot or opponent == ctx.author:
            return await ctx.error('Choose a valid human opponent.')
        EMPTY, P1, P2 = '⬛', '🔴', '🟡'
        board = [[EMPTY]*7 for _ in range(6)]
        players = {ctx.author: P1, opponent: P2}
        turn = ctx.author

        def render():
            header = '1️⃣2️⃣3️⃣4️⃣5️⃣6️⃣7️⃣'
            rows = '\n'.join([''.join(r) for r in board])
            return f'{header}\n{rows}'

        def drop(col, piece):
            for r in range(5, -1, -1):
                if board[r][col] == EMPTY:
                    board[r][col] = piece
                    return True
            return False

        def check_win(piece):
            for r in range(6):
                for c in range(4):
                    if all(board[r][c+i] == piece for i in range(4)): return True
            for r in range(3):
                for c in range(7):
                    if all(board[r+i][c] == piece for i in range(4)): return True
            for r in range(3):
                for c in range(4):
                    if all(board[r+i][c+i] == piece for i in range(4)): return True
            for r in range(3, 6):
                for c in range(4):
                    if all(board[r-i][c+i] == piece for i in range(4)): return True
            return False

        msg = await ctx.send(f'{render()}\n{turn.mention}\'s turn ({players[turn]}). Type column (1-7):')

        def chk(m):
            return m.author == turn and m.channel == ctx.channel and m.content in [str(i) for i in range(1,8)]

        for _ in range(42):
            try:
                m = await self.bot.wait_for('message', timeout=30, check=chk)
            except asyncio.TimeoutError:
                return await ctx.send(f'⏱️ {turn.mention} timed out. Game over.')
            col = int(m.content) - 1
            if not drop(col, players[turn]):
                await ctx.send('Column full!', delete_after=3)
                continue
            if check_win(players[turn]):
                return await ctx.send(f'{render()}\n🎉 {turn.mention} wins!')
            turn = opponent if turn == ctx.author else ctx.author
            await msg.edit(content=f'{render()}\n{turn.mention}\'s turn ({players[turn]}). Type column (1-7):')
        await ctx.send(f'{render()}\n🤝 It\'s a draw!')

    @commands.command(name='emoji_quiz', aliases=['emojiquiz','eq'], help='Guess the word/phrase from emojis.')
    async def emoji_quiz(self, ctx):
        puzzles = [
            ('🍕🍕🍕', 'pizza'),
            ('🎬🌟', 'movie star'),
            ('🐍🐍🐍', 'python'),
            ('🌍🌎🌏', 'world'),
            ('🎵🎶🎸', 'rock music'),
            ('🦁👑', 'lion king'),
            ('🕷️👨', 'spider man'),
            ('❄️👸', 'frozen'),
            ('🤖⚡', 'electric robot'),
            ('🌊🏄', 'surfing'),
        ]
        emojis, answer = random.choice(puzzles)
        await ctx.send(f'🧩 **Emoji Quiz!** What does this represent?\n\n**{emojis}**\n\nYou have **20 seconds**!')

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        try:
            msg = await self.bot.wait_for('message', timeout=20, check=check)
        except asyncio.TimeoutError:
            return await ctx.send(f'⏱️ Time\'s up! The answer was **{answer}**.')

        if answer.lower() in msg.content.lower():
            await ctx.send(f'🎉 Correct! It was **{answer}**!')
        else:
            await ctx.send(f'❌ Nope! It was **{answer}**.')

    @commands.command(name='highlow', aliases=['hl'], help='Guess if the next card is higher or lower.')
    async def highlow(self, ctx):
        deck = list(range(1, 14)) * 4
        random.shuffle(deck)
        names = {1:'Ace',11:'Jack',12:'Queen',13:'King'}
        score = 0

        def cname(v):
            return names.get(v, str(v))

        current = deck.pop()
        await ctx.send(f'🃏 **High or Low!** Current card: **{cname(current)}**\nType `higher` or `lower` (5 rounds):')

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() in ('higher','lower','h','l')

        for i in range(5):
            try:
                msg = await self.bot.wait_for('message', timeout=20, check=check)
            except asyncio.TimeoutError:
                break
            guess = msg.content.lower()
            nxt = deck.pop()
            correct = (guess in ('higher','h') and nxt > current) or (guess in ('lower','l') and nxt < current)
            if correct:
                score += 1
                await ctx.send(f'✅ Correct! Next card was **{cname(nxt)}**. Score: `{score}`')
            else:
                await ctx.send(f'❌ Wrong! Next card was **{cname(nxt)}**. Score: `{score}`')
            current = nxt

        await ctx.send(f'🏁 Game over! Final score: **{score}/5**')

    @commands.command(name='riddle', help='Get a random riddle to solve.')
    async def riddle(self, ctx):
        riddles = [
            ("I speak without a mouth and hear without ears. I have no body but come alive with the wind. What am I?", "echo"),
            ("The more you take, the more you leave behind. What am I?", "footsteps"),
            ("I have cities, but no houses live there. I have mountains but no trees. I have water but no fish. What am I?", "map"),
            ("What has keys but no locks, space but no room, and you can enter but can't go inside?", "keyboard"),
            ("The more you remove from me, the bigger I get. What am I?", "hole"),
        ]
        q, a = random.choice(riddles)
        await ctx.send(f'🤔 **Riddle!**\n\n{q}\n\nYou have **30 seconds**!')

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        try:
            msg = await self.bot.wait_for('message', timeout=30, check=check)
        except asyncio.TimeoutError:
            return await ctx.send(f'⏱️ The answer was **{a}**!')
        if a.lower() in msg.content.lower():
            await ctx.send(f'🎉 Correct! The answer was **{a}**!')
        else:
            await ctx.send(f'❌ Nope! The answer was **{a}**.')

    @commands.command(name='flipcard', aliases=['fc'], help='Flip a random playing card.')
    async def flipcard(self, ctx):
        suits = ['♠️','♥️','♦️','♣️']
        values = ['2','3','4','5','6','7','8','9','10','J','Q','K','A']
        card = f'{random.choice(values)}{random.choice(suits)}'
        embed = self.bot.embed_manager.generic(description=f'You flipped: **`{card}`**', title='🃏 Card Flip')
        await ctx.send(embed=embed)

    @commands.command(name='mathrace', aliases=['speedmath'], help='Race to solve math problems fastest.')
    async def mathrace(self, ctx):
        a = random.randint(10, 99)
        b = random.randint(10, 99)
        op = random.choice(['+', '-', '*'])
        answer = eval(f'{a}{op}{b}')
        await ctx.send(f'⚡ **Math Race!** Solve: `{a} {op} {b} = ?`\nFirst to answer wins! (30s)')

        def check(m):
            return m.channel == ctx.channel and not m.author.bot and m.content.strip().lstrip('-').isdigit()

        try:
            msg = await self.bot.wait_for('message', timeout=30, check=check)
        except asyncio.TimeoutError:
            return await ctx.send(f'⏱️ No one answered! It was **{answer}**.')
        if int(msg.content.strip()) == answer:
            await ctx.send(f'🏆 {msg.author.mention} got it first! The answer was **{answer}**.')
        else:
            await ctx.send(f'❌ Wrong! The answer was **{answer}**.')

async def setup(bot):
    await bot.add_cog(Games(bot))
