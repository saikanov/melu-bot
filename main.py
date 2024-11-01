from typing import Final
import os
from dotenv import load_dotenv
from discord import Intents, Client, Message, AppCommandOptionType
from responses import chatbot, delete_memory
from searchlogic import search_runAI2
from discord.ext import commands
 
load_dotenv()
TOKEN: Final[str] = os.getenv("DISCORD_TOKEN")

#BOT SETUP
intents = Intents.default()
intents.message_content = True
client = Client(intents=intents)


####REPLY MESSAGE
async def send_message(message: Message, user_message: str, user_id:str) -> None:
    # Cek apakah bot di-mention
    if str(client.user.id) in str(message.mentions):
        # Ambil teks setelah mention
        if "<@1281133399704338504>" in user_message:
            user_message = user_message.replace("<@1281133399704338504>", "")

    else:
        user_message = ""

    if not user_message:
        print("Message was empty")
        return
    comand = AppCommandOptionType()
    try:
        if "search" in user_message:
            response: str = search_runAI2(user_message, user_id, max_result=3)
        elif "deepsearch" in user_message:
            response: str = search_runAI2(user_message, user_id,max_result=10)
        elif "/reset" in user_message:
            response = delete_memory(user_id)
        else:
            response: str = chatbot(user_message,user_id)

        # Kirim pesan sesuai dengan jenisnya (private atau public)
        await message.channel.send(response)
    except Exception as e:
        print(e)



#HANDLING
@client.event
async def on_ready() -> None:
    print(f'{client.user.id} is now running....')   


#handling response
@client.event
async def on_message(message: Message) -> None:
    if message.author == client.user:
        return 
    
    username: str = str(message.author)
    user_message: str = str(message.content)
    channel: str = str(message.channel)
    user_id = str(message.author.id)

    print(f"[{channel}] {username}: '{user_message}' ")
    await send_message(message, user_message,user_id)

def main() -> None:
    client.run(token=TOKEN)


if __name__ == '__main__':
    main()
