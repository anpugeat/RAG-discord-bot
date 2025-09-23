import asyncio
import sqlite3
import time
from collections import defaultdict, deque
from typing import Dict, Deque, Optional, Tuple
import logging
import os
from discord.ext import commands
import discord

logger = logging.getLogger(__name__)

class RateLimitError(commands.CommandError):
    """Custom exception for rate limit violations"""
    def __init__(self, retry_after: float, limit_type: str):
        self.retry_after = retry_after
        self.limit_type = limit_type
        super().__init__(f"Rate limit exceeded. Try again in {retry_after:.1f} seconds.")

class RateLimitManager:
    """Handles rate limiting with in-memory caching and database persistence"""
    
    def __init__(self, db_path: str = "data/rate_limits.db"):
        self.db_path = db_path
        self.minute_requests: Dict[int, Deque[float]] = defaultdict(deque)
        self.hour_requests: Dict[int, Deque[float]] = defaultdict(deque)
        self.locks: Dict[int, asyncio.Lock] = defaultdict(asyncio.Lock)
        
        # Rate limits (requests per time period)
        self.minute_limit = int(os.getenv('RATE_LIMIT_PER_MINUTE', '5'))
        self.hour_limit = int(os.getenv('RATE_LIMIT_PER_HOUR', '30'))
        
        logger.info(f"Rate limits: {self.minute_limit}/min, {self.hour_limit}/hour")
    
    async def initialize_db(self):
        """Initialize the SQLite database for rate limiting"""
        # Ensure data directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        async with self._get_db_connection() as db:
            await db.execute('PRAGMA journal_mode=WAL')
            await db.execute('''
                CREATE TABLE IF NOT EXISTS rate_limits (
                    user_id INTEGER,
                    request_time REAL,
                    PRIMARY KEY (user_id, request_time)
                )
            ''')
            await db.execute('''
                CREATE INDEX IF NOT EXISTS idx_user_time 
                ON rate_limits(user_id, request_time)
            ''')
            await db.commit()
    
    def _get_db_connection(self):
        """Get database connection with proper configuration"""
        import aiosqlite
        return aiosqlite.connect(self.db_path)
    
    async def _load_user_history(self, user_id: int):
        """Load user's request history from database into memory"""
        current_time = time.time()
        one_hour_ago = current_time - 3600
        
        async with self._get_db_connection() as db:
            await db.execute('PRAGMA journal_mode=WAL')
            cursor = await db.execute(
                'SELECT request_time FROM rate_limits WHERE user_id = ? AND request_time > ?',
                (user_id, one_hour_ago)
            )
            rows = await cursor.fetchall()
        
        # Clear existing data and load from database
        self.minute_requests[user_id].clear()
        self.hour_requests[user_id].clear()
        
        one_minute_ago = current_time - 60
        
        for row in rows:
            request_time = row[0]
            self.hour_requests[user_id].append(request_time)
            if request_time > one_minute_ago:
                self.minute_requests[user_id].append(request_time)
    
    async def _cleanup_old_requests(self, user_id: int):
        """Remove old requests from memory and database"""
        current_time = time.time()
        one_minute_ago = current_time - 60
        one_hour_ago = current_time - 3600
        
        # Clean up minute requests
        while (self.minute_requests[user_id] and 
               self.minute_requests[user_id][0] <= one_minute_ago):
            self.minute_requests[user_id].popleft()
        
        # Clean up hour requests
        while (self.hour_requests[user_id] and 
               self.hour_requests[user_id][0] <= one_hour_ago):
            self.hour_requests[user_id].popleft()
        
        # Clean up database (run periodically, not every request)
        if len(self.hour_requests[user_id]) == 0:
            async with self._get_db_connection() as db:
                await db.execute('PRAGMA journal_mode=WAL')
                await db.execute(
                    'DELETE FROM rate_limits WHERE user_id = ? AND request_time <= ?',
                    (user_id, one_hour_ago)
                )
                await db.commit()
    
    async def check_rate_limit(self, user_id: int) -> Optional[RateLimitError]:
        """Check if user has exceeded rate limits. Returns None if allowed, RateLimitError if not."""
        async with self.locks[user_id]:
            # Load user history if not in memory
            if user_id not in self.minute_requests:
                await self._load_user_history(user_id)
            
            await self._cleanup_old_requests(user_id)
            
            current_time = time.time()
            
            # Check minute limit
            if len(self.minute_requests[user_id]) >= self.minute_limit:
                oldest_request = self.minute_requests[user_id][0]
                retry_after = 60 - (current_time - oldest_request)
                return RateLimitError(retry_after, "per minute")
            
            # Check hour limit
            if len(self.hour_requests[user_id]) >= self.hour_limit:
                oldest_request = self.hour_requests[user_id][0]
                retry_after = 3600 - (current_time - oldest_request)
                return RateLimitError(retry_after, "per hour")
            
            return None
    
    async def record_request(self, user_id: int):
        """Record a new request for the user"""
        current_time = time.time()
        
        async with self.locks[user_id]:
            # Add to in-memory tracking
            self.minute_requests[user_id].append(current_time)
            self.hour_requests[user_id].append(current_time)
            
            # Add to database
            try:
                async with self._get_db_connection() as db:
                    await db.execute('PRAGMA journal_mode=WAL')
                    await db.execute(
                        'INSERT INTO rate_limits (user_id, request_time) VALUES (?, ?)',
                        (user_id, current_time)
                    )
                    await db.commit()
            except Exception as e:
                logger.error(f"Failed to record request in database: {e}")
    
    async def get_user_stats(self, user_id: int) -> Dict[str, int]:
        """Get current rate limit stats for a user"""
        async with self.locks[user_id]:
            if user_id not in self.minute_requests:
                await self._load_user_history(user_id)
            
            await self._cleanup_old_requests(user_id)
            
            return {
                'minute_requests': len(self.minute_requests[user_id]),
                'minute_limit': self.minute_limit,
                'hour_requests': len(self.hour_requests[user_id]),
                'hour_limit': self.hour_limit
            }
    
    async def reset_user_limits(self, user_id: int):
        """Reset rate limits for a specific user (admin function)"""
        async with self.locks[user_id]:
            self.minute_requests[user_id].clear()
            self.hour_requests[user_id].clear()
            
            async with self._get_db_connection() as db:
                await db.execute('DELETE FROM rate_limits WHERE user_id = ?', (user_id,))
                await db.commit()

class RateLimit(commands.Cog):
    """Rate limiting system for Edue Helper"""
    
    def __init__(self, bot):
        self.bot = bot
        self.rate_manager = RateLimitManager()
    
    async def cog_load(self):
        """Initialize the rate limiting system when the cog loads"""
        await self.rate_manager.initialize_db()
        logger.info("Rate limiting system initialized")
    
    def rate_limit(self):
        """Decorator to add rate limiting to commands"""
        def decorator(func):
            async def wrapper(cog_self, ctx, *args, **kwargs):
                user_id = ctx.author.id
                
                # Check rate limit
                rate_error = await self.rate_manager.check_rate_limit(user_id)
                if rate_error:
                    embed = discord.Embed(
                        title="⏱️ Rate Limit Exceeded",
                        description=f"You've exceeded the rate limit ({rate_error.limit_type}).\n"
                                  f"Please wait {rate_error.retry_after:.1f} seconds before trying again.",
                        color=discord.Color.orange()
                    )
                    await ctx.send(embed=embed, ephemeral=True)
                    return
                
                # Record the request
                await self.rate_manager.record_request(user_id)
                
                # Execute the original function
                return await func(cog_self, ctx, *args, **kwargs)
            
            # Copy function attributes to maintain compatibility
            wrapper.__name__ = func.__name__
            wrapper.__doc__ = func.__doc__
            wrapper.__module__ = func.__module__
            wrapper.__qualname__ = func.__qualname__
            
            return wrapper
        return decorator
    
    async def check_user_rate_limit(self, user_id: int) -> Optional[RateLimitError]:
        """Public method to check rate limits for integration with other cogs"""
        return await self.rate_manager.check_rate_limit(user_id)
    
    async def record_user_request(self, user_id: int):
        """Public method to record requests for integration with other cogs"""
        await self.rate_manager.record_request(user_id)
    
    @commands.hybrid_command(name="rlstats")
    @commands.is_owner()
    async def rate_limit_stats(self, ctx, user: Optional[discord.User] = None):
        """Check rate limit statistics for yourself or another user (Owner only)"""
        target_user = user or ctx.author
        stats = await self.rate_manager.get_user_stats(target_user.id)
        
        embed = discord.Embed(
            title=f"📊 Rate Limit Stats for {target_user.display_name}",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="Per Minute",
            value=f"{stats['minute_requests']}/{stats['minute_limit']} requests",
            inline=True
        )
        
        embed.add_field(
            name="Per Hour", 
            value=f"{stats['hour_requests']}/{stats['hour_limit']} requests",
            inline=True
        )
        
        # Calculate remaining requests
        minute_remaining = stats['minute_limit'] - stats['minute_requests']
        hour_remaining = stats['hour_limit'] - stats['hour_requests']
        
        embed.add_field(
            name="Remaining",
            value=f"Minute: {minute_remaining}\nHour: {hour_remaining}",
            inline=True
        )
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="rlreset")
    @commands.is_owner()
    async def reset_rate_limits(self, ctx, user: discord.User):
        """Reset rate limits for a specific user (Owner only)"""
        await self.rate_manager.reset_user_limits(user.id)
        
        embed = discord.Embed(
            title="✅ Rate Limits Reset",
            description=f"Rate limits have been reset for {user.display_name}",
            color=discord.Color.green()
        )
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="rlconfig")
    @commands.is_owner()
    async def rate_limit_config(self, ctx):
        """Show current rate limiting configuration (Owner only)"""
        embed = discord.Embed(
            title="⚙️ Rate Limit Configuration",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="Per Minute Limit",
            value=f"{self.rate_manager.minute_limit} requests",
            inline=True
        )
        
        embed.add_field(
            name="Per Hour Limit", 
            value=f"{self.rate_manager.hour_limit} requests",
            inline=True
        )
        
        embed.add_field(
            name="Database",
            value=f"Path: `{self.rate_manager.db_path}`",
            inline=False
        )
        
        embed.set_footer(text="Configuration can be changed via environment variables")
        
        await ctx.send(embed=embed)

async def setup(bot):
    """Setup function for loading the cog"""
    await bot.add_cog(RateLimit(bot))
