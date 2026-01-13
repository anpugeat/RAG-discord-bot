from interactions import Client, Intents, slash_command, SlashContext, listen, slash_option, OptionType
from dotenv import load_dotenv
import os
import logging
from querying import data_querying, detect_academic_dishonesty, generate_quiz
from manage_embedding import update_index

# Suppress noisy warnings from the interactions library
logging.getLogger("interactions").setLevel(logging.ERROR)

load_dotenv()  # load env file

# Initialise bot with all intents (maybe reduce in future)
bot = Client(intents=Intents.ALL)

# Word list loader
def load_wordlist(filename):
    """
    Helper: loads a list of words from file into a set.
    """
    try:
        with open(filename,"r") as f:
            return {line.strip().lower() for line in f if line.strip()}
    except FileNotFoundError:
        print(f"ERROR: {filename} not found. Treating as empty.")
        return set()

blacklist = load_wordlist("blacklist.txt")

whitelist = load_wordlist("whitelist.txt")
sorted_whitelist = sorted(list(whitelist),key=len,reverse=True)  # sort whitelist by length descending so that longer words (class) whitelisted before "ass" is blacklisted

def is_profane(text:str) -> bool:
    """
    Checker: Is inputted string on "blacklist.txt"?
    Whitelisted words are removed from the text before the check is conducted.
    """
    text = text.lower()

    # remove whitelisted words
    for word in sorted_whitelist:
        cleaned_text = cleaned_text.replace(word,"")
    
    # check for blacklisted words
    return any(bad_word in cleaned_text for bad_word in blacklist)

# ---------------- EVENT LISTENERS ----------------
@listen() 
async def on_ready():
    print("Ready")
 
@listen()
async def on_message_create(event):
    """
    Called every time a message is sent in a channel the bot can see.
    1. Logs user activity.
    2. Deletes messages containing profanity.
    """
    # Check if message exists and has content, if not, then return early
    if not hasattr(event, "message") or not event.message.content:
        return

    # Store message content and print out
    content = event.message.content
    print(f"READ: Message received: {content}")

    # ignore messages from bots to prevent loops
    if event.message.author.bot:
        return

    # check for bad words
    if is_profane(content):
        try:
            await event_message.delete()
            print(f"ACTION: Deleted profane message from {event.message.author.username}")
            # DM user that their message was deleted
            await event.message.author.send("Your message was removed due to inappropriate language. Please use safe language to keep our learning space suitable for all. Thank you!")
        except Exception as e:
            print(f"ERROR: Could not delete message: {e}")

# ---------------- SLASH COMMANDS ----------------
# /ask
@slash_command(name="ask", description="Ask EdueBot a question!")
@slash_option(
    name="input_text",
    description="Ask me anything!",
    required=True,
    opt_type=OptionType.STRING,
)
async def get_response(ctx: SlashContext, input_text: str):
    """
    Handles the /ask command. 
    1. Checks for Academic Integrity (Cheating vs Learning).
    2. Runs the RAG search if safe.
    """
    await ctx.defer()

    # First check if they are trying to have AI do their homework for them
    is_safe, warning_msg = await detect_academic_dishonesty(input_text)
    
    if not is_safe:
        # If violation, return the warning and stop.
        response = f"**Sorry, I can't help you with graded assignments. I can do my best to teach you material from your courses.**\n{warning_msg}"
        await ctx.send(response)
        return

    # Call RAG function to search docs, generate answer
    response = await data_querying(input_text)

    # Format output to show user input + bot answer
    response = f'**Question:** {input_text}\n\n{response}'
    await ctx.send(response)

# /quiz
@slash_command(name="quiz", description="Generate a practice quiz based on a topic!")
@slash_option(
    name="topic",
    description="What topic do you want to test yourself on?",
    required=True,
    opt_type=OptionType.STRING,
)

async def create_quiz(ctx: SlashContext, topic: str):
    """
    Handles the /quiz command.
    Generates 3 multiple-choice questions based on the RAG data.
    """
    await ctx.defer()
    
    quiz_content = await generate_quiz(topic)
    
    response = f"**Pop Quiz: {topic}**\n\n{quiz_content}\n\n*Click the black boxes to reveal the answers!*"
    await ctx.send(response)

# /updatedb
@slash_command(name="updatedb", description="Update your RAG information database")
async def updated_database(ctx: SlashContext):
    """
    Handles the /updatedb command.
    Manually triggers the bot to re-scan the 'data/' folder for new PDFs/files.
    """
    await ctx.defer() # same use of defer as above

    # Call update function from manage_embedding.py
    update = await update_index()
    if update:
        response = f'Updated {sum(update)} document chunks'
    else:
        response = f'Error updating index'
    await ctx.send(response)


# Starts our bot with token
bot.start(os.getenv("DISCORD_BOT_TOKEN"))