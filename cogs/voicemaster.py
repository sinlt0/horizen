import discord
from discord.ext import commands
import asyncio

class VoiceMasterView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def check_ownership(self, interaction: discord.Interaction):
        data = await interaction.client.db_manager.find_one('voicemaster_channels', {'_id': interaction.user.voice.channel.id if interaction.user.voice else 0})
        if not data or data.get('owner_id') != interaction.user.id:
            await interaction.response.send_message('You do not own this voice channel.', ephemeral=True)
            return False
        return True

    @discord.ui.button(label='Lock', style=discord.ButtonStyle.secondary, custom_id='vm:lock')
    async def lock(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.check_ownership(interaction): return
        channel = interaction.user.voice.channel
        await channel.set_permissions(interaction.guild.default_role, connect=False)
        await interaction.response.send_message('Channel locked.', ephemeral=True)

    @discord.ui.button(label='Unlock', style=discord.ButtonStyle.secondary, custom_id='vm:unlock')
    async def unlock(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.check_ownership(interaction): return
        channel = interaction.user.voice.channel
        await channel.set_permissions(interaction.guild.default_role, connect=None)
        await interaction.response.send_message('Channel unlocked.', ephemeral=True)

    @discord.ui.button(label='Hide', style=discord.ButtonStyle.secondary, custom_id='vm:hide')
    async def hide(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.check_ownership(interaction): return
        channel = interaction.user.voice.channel
        await channel.set_permissions(interaction.guild.default_role, view_channel=False)
        await interaction.response.send_message('Channel hidden.', ephemeral=True)

    @discord.ui.button(label='Unhide', style=discord.ButtonStyle.secondary, custom_id='vm:unhide')
    async def unhide(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.check_ownership(interaction): return
        channel = interaction.user.voice.channel
        await channel.set_permissions(interaction.guild.default_role, view_channel=None)
        await interaction.response.send_message('Channel unhidden.', ephemeral=True)

    @discord.ui.button(label='Rename', style=discord.ButtonStyle.primary, custom_id='vm:rename')
    async def rename(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.check_ownership(interaction): return
        
        class RenameModal(discord.ui.Modal, title='Rename Channel'):
            name = discord.ui.TextInput(label='New Name', placeholder='Enter new channel name...', min_length=1, max_length=32)
            async def on_submit(self, itn: discord.Interaction):
                await itn.user.voice.channel.edit(name=self.name.value)
                await itn.response.send_message(f'Channel renamed to **{self.name.value}**.', ephemeral=True)

        await interaction.response.send_modal(RenameModal())

    @discord.ui.button(label='Limit', style=discord.ButtonStyle.primary, custom_id='vm:limit')
    async def limit(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.check_ownership(interaction): return

        class LimitModal(discord.ui.Modal, title='Set User Limit'):
            limit = discord.ui.TextInput(label='Limit (0-99)', placeholder='0 for no limit...', min_length=1, max_length=2)
            async def on_submit(self, itn: discord.Interaction):
                if not self.limit.value.isdigit(): return await itn.response.send_message('Please enter a valid number.', ephemeral=True)
                val = int(self.limit.value)
                if val < 0 or val > 99: return await itn.response.send_message('Limit must be between 0 and 99.', ephemeral=True)
                await itn.user.voice.channel.edit(user_limit=val)
                await itn.response.send_message(f'User limit set to **{val}**.', ephemeral=True)

        await interaction.response.send_modal(LimitModal())

    @discord.ui.button(label='Kick', style=discord.ButtonStyle.danger, custom_id='vm:kick')
    async def kick(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.check_ownership(interaction): return
        members = [m for m in interaction.user.voice.channel.members if m.id != interaction.user.id]
        if not members: return await interaction.response.send_message('There is no one else to kick.', ephemeral=True)
        
        class KickSelect(discord.ui.Select):
            def __init__(self, members):
                super().__init__(placeholder='Select a user to kick...', options=[discord.SelectOption(label=m.display_name, value=str(m.id)) for m in members[:25]])
            async def callback(self, itn: discord.Interaction):
                member = itn.guild.get_member(int(self.values[0]))
                if member and member.voice and member.voice.channel == itn.user.voice.channel:
                    await member.move_to(None)
                    await itn.response.send_message(f'Kicked **{member.display_name}**.', ephemeral=True)

        view = discord.ui.View(timeout=60)
        view.add_item(KickSelect(members))
        await interaction.response.send_message('Select a user:', view=view, ephemeral=True)

    @discord.ui.button(label='Permit', style=discord.ButtonStyle.success, custom_id='vm:permit')
    async def permit(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.check_ownership(interaction): return
        
        class PermitSelect(discord.ui.UserSelect):
            def __init__(self):
                super().__init__(placeholder='Select a user to permit...')
            async def callback(self, itn: discord.Interaction):
                user = self.values[0]
                await itn.user.voice.channel.set_permissions(user, connect=True)
                await itn.response.send_message(f'Permitted **{user.display_name}** to join.', ephemeral=True)

        view = discord.ui.View(timeout=60)
        view.add_item(PermitSelect())
        await interaction.response.send_message('Select a user:', view=view, ephemeral=True)

    @discord.ui.button(label='Transfer', style=discord.ButtonStyle.primary, custom_id='vm:transfer')
    async def transfer(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.check_ownership(interaction): return
        members = [m for m in interaction.user.voice.channel.members if m.id != interaction.user.id]
        if not members: return await interaction.response.send_message('No one else is here to transfer to.', ephemeral=True)

        class TransferSelect(discord.ui.Select):
            def __init__(self, members):
                super().__init__(placeholder='Select a new owner...', options=[discord.SelectOption(label=m.display_name, value=str(m.id)) for m in members[:25]])
            async def callback(self, itn: discord.Interaction):
                member = itn.guild.get_member(int(self.values[0]))
                await itn.client.db_manager.update_one('voicemaster_channels', {'_id': itn.user.voice.channel.id}, {'owner_id': member.id})
                await itn.response.send_message(f'Transferred ownership to **{member.display_name}**.', ephemeral=True)

        view = discord.ui.View(timeout=60)
        view.add_item(TransferSelect(members))
        await interaction.response.send_message('Select a new owner:', view=view, ephemeral=True)

    @discord.ui.button(label='Claim', style=discord.ButtonStyle.success, custom_id='vm:claim')
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.voice or not interaction.user.voice.channel:
            return await interaction.response.send_message('You must be in a VoiceMaster channel to claim it.', ephemeral=True)
        
        channel_id = interaction.user.voice.channel.id
        data = await interaction.client.db_manager.find_one('voicemaster_channels', {'_id': channel_id})
        if not data: return await interaction.response.send_message('This is not a VoiceMaster channel.', ephemeral=True)

        owner = interaction.guild.get_member(data.get('owner_id'))
        if owner and owner in interaction.user.voice.channel.members:
            return await interaction.response.send_message('The owner is still in the channel.', ephemeral=True)

        await interaction.client.db_manager.update_one('voicemaster_channels', {'_id': channel_id}, {'owner_id': interaction.user.id})
        await interaction.response.send_message('You are now the owner of this channel.', ephemeral=True)

class VoiceMaster(commands.Cog):
    category = 'config'

    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db_manager

    async def get_config(self, guild_id):
        return await self.bot.get_config('voicemaster_config', guild_id)

    async def update_config(self, guild_id, data):
        await self.bot.update_config('voicemaster_config', guild_id, data)

    @commands.group(name='voicemaster', aliases=['vm'], invoke_without_command=True, help='VoiceMaster management commands.')
    @commands.has_permissions(administrator=True)
    async def vm_group(self, ctx):
        config = await self.get_config(ctx.guild.id)
        if not config: return await ctx.info('VoiceMaster is not configured.')
        
        category = ctx.guild.get_channel(config.get('category_id'))
        channel = ctx.guild.get_channel(config.get('channel_id'))
        interface = ctx.guild.get_channel(config.get('interface_channel_id'))
        
        desc = f"**Category:** {category.mention if category else 'Not set'}\n**Join to Create:** {channel.mention if channel else 'Not set'}\n**Interface:** {interface.mention if interface else 'Not set'}"
        await ctx.embed(desc, title='VoiceMaster Configuration')

    @vm_group.command(name='setup', help='Automatically setup the VoiceMaster system.')
    @commands.has_permissions(administrator=True, manage_channels=True)
    async def vm_setup(self, ctx):
        await ctx.info('Setting up VoiceMaster...')
        category = await ctx.guild.create_category('Horizen VoiceMaster')
        channel = await ctx.guild.create_voice_channel('Join to Create', category=category)
        interface_ch = await ctx.guild.create_text_channel('vm-interface', category=category)
        await self.update_config(ctx.guild.id, {'category_id': category.id, 'channel_id': channel.id, 'interface_channel_id': interface_ch.id})
        await interface_ch.send(embed=self.bot.embed_manager.generic(title='VoiceMaster Interface', description='Use the buttons below to manage your temporary voice channel.'), view=VoiceMasterView())
        await ctx.success(f'VoiceMaster setup complete in {category.mention}!')

    @vm_group.command(name='category', help='Set the category for temporary voice channels.')
    @commands.has_permissions(administrator=True)
    async def vm_category(self, ctx, category: discord.CategoryChannel):
        await self.update_config(ctx.guild.id, {'category_id': category.id})
        await ctx.success(f'VoiceMaster category set to **{category.name}**.')

    @vm_group.command(name='channel', help='Set the Join to Create voice channel.')
    @commands.has_permissions(administrator=True)
    async def vm_channel(self, ctx, channel: discord.VoiceChannel):
        await self.update_config(ctx.guild.id, {'channel_id': channel.id})
        await ctx.success(f'VoiceMaster Join to Create channel set to {channel.mention}.')

    @vm_group.command(name='interface', help='Set the interface text channel.')
    @commands.has_permissions(administrator=True)
    async def vm_interface(self, ctx, channel: discord.TextChannel):
        await self.update_config(ctx.guild.id, {'interface_channel_id': channel.id})
        await channel.send(embed=self.bot.embed_manager.generic(title='VoiceMaster Interface', description='Use the buttons below to manage your temporary voice channel.'), view=VoiceMasterView())
        await ctx.success(f'VoiceMaster interface set to {channel.mention}.')

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.bot: return
        
        config = await self.get_config(member.guild.id)
        if not config: return

        jtc_id = config.get('channel_id')
        category_id = config.get('category_id')

        if after.channel and after.channel.id == jtc_id:
            category = self.bot.get_channel(category_id)
            temp_channel = await member.guild.create_voice_channel(
                name=f"{member.display_name}'s Lounge",
                category=category,
                reason='VoiceMaster: Temporary channel creation'
            )
            await self.db.update_one('voicemaster_channels', {'_id': temp_channel.id}, {
                'owner_id': member.id,
                'guild_id': member.guild.id
            }, upsert=True)
            await member.move_to(temp_channel)

        if before.channel:
            data = await self.db.find_one('voicemaster_channels', {'_id': before.channel.id})
            if data and len(before.channel.members) == 0:
                await before.channel.delete(reason='VoiceMaster: Temporary channel empty')
                await self.db.delete_one('voicemaster_channels', {'_id': before.channel.id})

async def setup(bot):
    await bot.add_cog(VoiceMaster(bot))
