from .scroll import Scroll
from redbot.core.bot import Red
import inspect


async def setup(bot: Red):
	cog = Scroll(bot)
	value = bot.add_cog(cog)
	if inspect.isawaitable(value):
		await value
	if hasattr(cog, "cog_load"):
		await cog.cog_load()