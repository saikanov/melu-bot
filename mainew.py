from typing import Final
import os
from dotenv import load_dotenv
from discord import Intents, Client, Message, app_commands, Interaction
from response_langgraph import basic_response
import discord

load_dotenv()
TOKEN: Final[str] = os.getenv("DISCORD_TOKEN")

# BOT SETUP
intents = Intents.default()
intents.message_content = True
client = Client(intents=intents)
tree = app_commands.CommandTree(client)  # CommandTree untuk application commands


#### REPLY MESSAGE
async def send_message(message: Message, user_message: str, user_id: str, username, private_msg, attachment) -> None:
    if client.user in message.mentions:
        user_message = user_message.replace(f"<@{client.user.id}>", "")
    elif private_msg:
        user_message = user_message
    else:
        user_message = ""

    try:
        if user_message:
            async with (message.author.typing() if private_msg else message.channel.typing()):
                print(username)
                print("usermessege=",user_message)
                response: str = await basic_response(user_input=user_message,
                                            config= {"configurable": {"thread_id": user_id,
                                                                        "discord_username" : username}})

                if len(response) >= 2000:
                    for i in range(0, len(response), 2000):
                        await message.author.send(response[i:i+2000]) if private_msg else await message.channel.send(response[i:i+2000])
                else:
                    await message.author.send(response) if private_msg else await message.channel.send(response)
        else:
            print("message kosong")
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

    if isinstance(message.channel, discord.channel.DMChannel):
        private_msg = True
    else:
        private_msg = False

    print(f"""
    from [{channel}] 
    {username}: '{user_message}' 
    user_id : '{user_id}'
    Attachment = '{attachments}'
            """)
    await send_message(message, user_message, user_id, username, private_msg, attachments)


# #### Slash Command: /delete_memory
# @tree.command(name="delete_memory", description="Delete user-specific memory.")
# async def delete_memory(interaction: Interaction):
#     user_id = str(interaction.user.id)
#     try:
#         delete_memory(user_id)  # Memanggil fungsi delete_memory
#         await interaction.response.send_message("Your memory has been successfully deleted!", ephemeral=True)
#     except Exception as e:
#         print(e)
#         await interaction.response.send_message("Failed to delete memory. Please try again later.", ephemeral=True)


def main() -> None:
    client.run(TOKEN)

if __name__ == '__main__':
    main()
