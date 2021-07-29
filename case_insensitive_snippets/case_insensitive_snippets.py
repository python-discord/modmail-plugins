def setup(bot):
    old_process_commands = bot.process_commands

    async def process_commands(message):
        if message.content.startswith(bot.prefix):
            cmd = message.content[len(bot.prefix):].strip().lower()

            # Convert message contents to lowercase if a snippet exists
            if cmd in bot.snippets:
                message.content = bot.prefix + cmd

        await old_process_commands(message)

    bot.process_commands = process_commands
