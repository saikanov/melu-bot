from typing import Final
import os
from dotenv import load_dotenv
from discord import Intents, Client, Message, app_commands, Interaction
from searchlogic import search_runAI2
from responses import melu
import discord

load_dotenv()
TOKEN: Final[str] = os.getenv("DISCORD_TOKEN")

# BOT SETUP
intents = Intents.default()
intents.message_content = True
client = Client(intents=intents)
tree = app_commands.CommandTree(client)  # CommandTree untuk application commands


#### REPLY MESSAGE
async def send_message(message: Message, user_message: str, user_id: str, private_msg, attachment) -> None:
    if str(client.user.id) in str(message.mentions):
        if "<@1281133399704338504>" in user_message:
            user_message = user_message.replace("<@1281133399704338504>", "")
    elif private_msg:
        user_message = user_message
    else:
        user_message = ""

    if not user_message:
        print("Message was empty")
        return
    try:
        async with (message.author.typing() if private_msg else message.channel.typing()):
            if "/reset" in user_message:
                response = melu.delete_memory(user_id)
            else:
                response: str = melu.response(user_message, user_id, attachment=attachment)
            
            if len(response) >= 2000:
                for i in range(0, len(response), 2000):
                    await message.author.send(response[i:i+2000]) if private_msg else await message.channel.send(response[i:i+2000])
            else:
                await message.author.send(response) if private_msg else await message.channel.send(response)
    except Exception as e:
        print(e)


# HANDLING
@client.event
async def on_ready() -> None:
    print(f'{client.user.id} is now running....')
    try:
        synced = await tree.sync()  # Sinkronisasi command tree
        print(f"Synced {len(synced)} commands.")
    except Exception as e:
        print(f"Failed to sync commands: {e}")


@client.event
async def on_message(message: Message) -> None:
    if message.author == client.user:
        return
    
    username: str = str(message.author)
    user_message: str = str(message.content)
    channel: str = str(message.channel)
    user_id = str(message.author.id)
    attachments = message.attachments

    private_msg = "Direct Message" in channel

    print(f"""[{channel}] {username}: '{user_message}' 
            Attachment = '{attachments.url}'
            """)
    await send_message(message, user_message, user_id, private_msg, attachments)


#### Slash Command: /delete_memory
@tree.command(name="delete_memory", description="Delete user-specific memory.")
async def delete_memory(interaction: Interaction):
    user_id = str(interaction.user.id)
    try:
        melu.delete_memory(user_id)  # Memanggil fungsi delete_memory
        await interaction.response.send_message("Your memory has been successfully deleted!", ephemeral=True)
    except Exception as e:
        print(e)
        await interaction.response.send_message("Failed to delete memory. Please try again later.", ephemeral=True)


def main() -> None:
    client.run(TOKEN)

if __name__ == '__main__':
    main()
