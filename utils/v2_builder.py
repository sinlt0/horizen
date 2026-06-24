import discord

class V2Component:
    def to_dict(self):
        raise NotImplementedError

class V2Container(V2Component):
    def __init__(self, accent_color: int = None, spoiler: bool = False):
        self.type = 17
        self.accent_color = accent_color
        self.spoiler = spoiler
        self.components = []

    def add_item(self, component: V2Component):
        self.components.append(component)
        return self

    def to_dict(self):
        data = {
            "type": self.type,
            "spoiler": self.spoiler,
            "components": [c.to_dict() for c in self.components]
        }
        if self.accent_color:
            data["accent_color"] = self.accent_color
        return data

class V2Section(V2Component):
    def __init__(self, accessory: dict = None):
        self.type = 9
        self.components = []
        self.accessory = accessory

    def add_text(self, content: str):
        self.components.append(V2Text(content))
        return self

    def set_button(self, label: str, custom_id: str, style: int = 1, emoji: dict = None, disabled: bool = False):
        self.accessory = {
            "type": 2,
            "style": style,
            "label": label,
            "custom_id": custom_id,
            "disabled": disabled
        }
        if emoji:
            self.accessory["emoji"] = emoji
        return self

    def set_thumbnail(self, url: str):
        self.accessory = {
            "type": 11,
            "media": {
                "url": url
            }
        }
        return self

    def to_dict(self):
        data = {
            "type": self.type,
            "components": [c.to_dict() for c in self.components]
        }
        if self.accessory:
            data["accessory"] = self.accessory
        return data

class V2Text(V2Component):
    def __init__(self, content: str):
        self.type = 10
        self.content = content

    def to_dict(self):
        return {"type": self.type, "content": self.content}

class V2Separator(V2Component):
    def __init__(self):
        self.type = 14

    def to_dict(self):
        return {"type": self.type}

class V2MessageBuilder:
    def __init__(self):
        self.flags = 32768
        self.components = []

    def add_container(self, container: V2Container):
        self.components.append(container)
        return self

    def add_action_row(self, components: list):
        self.components.append({"type": 1, "components": components})
        return self

    def build(self):
        # Hybrid support: Convert V2 components and ensure standard ActionRows are properly formatted
        built_components = []
        for c in self.components:
            if hasattr(c, 'to_dict'):
                built_components.append(c.to_dict())
            else:
                built_components.append(c)
        
        return {
            "flags": self.flags,
            "components": built_components
        }

async def send_v2(ctx, builder: V2MessageBuilder):
    payload = builder.build()
    return await ctx.bot.http.request(
        discord.http.Route('POST', '/channels/{channel_id}/messages', channel_id=ctx.channel.id),
        json=payload
    )

async def edit_v2(interaction: discord.Interaction, builder: V2MessageBuilder):
    payload = builder.build()
    # Using interaction response/edit for updates
    if not interaction.response.is_done():
        return await interaction.response.edit_message(json=payload)
    else:
        return await interaction.edit_original_response(json=payload)

async def callback_v2(interaction: discord.Interaction, builder: V2MessageBuilder):
    payload = builder.build()
    # Type 7: UPDATE_MESSAGE - Updates the message the component is attached to
    return await interaction.client.http.request(
        discord.http.Route('POST', '/interactions/{interaction_id}/{interaction_token}/callback', 
                           interaction_id=interaction.id, 
                           interaction_token=interaction.token),
        json={
            "type": 7,
            "data": payload
        }
    )
