"""
Chat Cog - Handles basic chat functionality with GPT-4o mini integration
"""

import discord
from discord.ext import commands
import openai
import os
import asyncio
import logging

logger = logging.getLogger(__name__)

class ChatCog(commands.Cog, name="Chat"):
    """
    Handles chat interactions with students using GPT-4o mini.
    Responds to mentions and provides conversational assistance.
    """
    
    def __init__(self, bot):
        self.bot = bot
        # Initialize OpenAI client
        openai.api_key = os.getenv('OPENAI_API_KEY')
        
        # System prompt for educational context
        self.system_prompt = """You are Edue Helper, a friendly and knowledgeable educational assistant for a Discord server. 
Your role is to help students with their learning by:
- Answering questions clearly and concisely
- Providing explanations in an educational context
- Being encouraging and supportive
- Keeping responses appropriate for a learning environment
- If you don't know something, admit it and suggest where they might find the answer

Keep responses conversational but informative. Aim for 1-2 paragraphs unless more detail is specifically requested."""

    async def cog_load(self):
        """Called when the cog is loaded"""
        logger.info("Chat cog loaded successfully")

    async def cog_unload(self):
        """Called when the cog is unloaded"""
        logger.info("Chat cog unloaded")

    async def get_gpt_response(self, message_content: str, user_name: str) -> str:
        """
        Get response from GPT-4o mini API
        
        Args:
            message_content (str): The user's message
            user_name (str): The user's display name for personalization
            
        Returns:
            str: GPT response or error message
        """
        try:
            # Prepare the conversation for GPT
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": f"{user_name} asks: {message_content}"}
            ]
            
            # Call OpenAI API
            response = await asyncio.to_thread(
                openai.chat.completions.create,
                model="gpt-4o-mini",
                messages=messages,
                max_tokens=500,
                temperature=0.7
            )
            
            return response.choices[0].message.content.strip()
            
        except openai.APIError as e:
            logger.error(f"OpenAI API error: {e}")
            return "I'm having trouble connecting to my knowledge base right now. Please try again in a moment!"
            
        except openai.RateLimitError:
            logger.warning("OpenAI rate limit exceeded")
            return "I'm getting too many requests right now. Please wait a moment and try again!"
            
        except Exception as e:
            logger.error(f"Unexpected error in GPT response: {e}")
            return "Sorry, I encountered an unexpected error. Please try again!"

    @commands.Cog.listener()
    async def on_message(self, message):
        """
        Listen for mentions of the bot and respond with GPT
        """
        # Ignore messages from bots (including self)
        if message.author.bot:
            return
            
        # Check if bot is mentioned
        if self.bot.user in message.mentions:
            # Remove the mention from the message content
            content = message.content
            for mention in message.mentions:
                if mention == self.bot.user:
                    content = content.replace(f'<@{mention.id}>', '').replace(f'<@!{mention.id}>', '')
            
            content = content.strip()
            
            # If there's no content after removing mentions, provide a greeting
            if not content:
                content = "Hello! How can I help you today?"
            
            # Show typing indicator while processing
            async with message.channel.typing():
                # Get response from GPT
                response = await self.get_gpt_response(content, message.author.display_name)
                
                # Send response
                await message.reply(response, mention_author=False)

    @commands.hybrid_command(name="chat", description="Have a conversation with Edue Helper")
    async def chat_command(self, ctx, *, question: str):
        """
        Direct command to chat with the bot
        
        Args:
            ctx: Command context
            question (str): The question or message to send to the bot
        """
        # Defer response for slash commands to give more time
        if ctx.interaction:
            await ctx.defer()
        
        # Show typing for text commands
        if not ctx.interaction:
            async with ctx.typing():
                response = await self.get_gpt_response(question, ctx.author.display_name)
                await ctx.send(response)
        else:
            response = await self.get_gpt_response(question, ctx.author.display_name)
            await ctx.send(response)

    @commands.hybrid_command(name="help_topics", description="Get help about what topics I can assist with")
    async def help_topics(self, ctx):
        """
        Show what topics the bot can help with
        """
        embed = discord.Embed(
            title="📚 What I can help you with",
            description="I'm here to assist with your educational needs!",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="💬 General Chat",
            value="Just mention me (@Edue Helper) in any message and I'll respond!",
            inline=False
        )
        
        embed.add_field(
            name="📖 Study Help",
            value="Ask me questions about your coursework, concepts, or study strategies",
            inline=False
        )
        
        embed.add_field(
            name="🤔 Explanations",
            value="Request explanations of complex topics in simple terms",
            inline=False
        )
        
        embed.add_field(
            name="💡 Learning Tips",
            value="Get advice on effective learning techniques and study methods",
            inline=False
        )
        
        embed.set_footer(text="Use /chat <question> or just mention me in your message!")
        
        await ctx.send(embed=embed)

    @chat_command.error
    async def chat_command_error(self, ctx, error):
        """Error handler for chat command"""
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("Please provide a question or message! Use `/chat <your question>` or just mention me in a message.")
        else:
            logger.error(f"Chat command error: {error}")
            await ctx.send("Sorry, something went wrong. Please try again!")

async def setup(bot):
    """Setup function for the cog"""
    await bot.add_cog(ChatCog(bot))
