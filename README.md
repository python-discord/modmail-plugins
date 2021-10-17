# Modmail Plugins
Modmail plugins for our Modmail bot, located at https://github.com/kyb3r/modmail.

## List of plugins
- **Ban appeals**: Threads created by users in a defined "appeal" guild get moved to a configured appeal category. This also both kicks users from the appeal guild when they rejoin the main guild, and kicks users from the appeal guild if they're not banned in the main guild.
- **Close message:** Add a `?closemessage` command that will close the thread after 15 minutes with a default message.
- **MDLink**: Generate a ready to paste link to the thread logs.
- **Ping manager**: Delay pings by a configurable time period, cancel the ping task if a message is sent in the thread (Other than an author message).
- **Reply cooldown**: Forbid you from sending the same message twice in ten seconds.
- **Tagging**: Add a `?tag` command capable of adding a `$message｜` header to the channel name.

## Installing a plugin
To install a plugin, simply run the following command:
```
?plugin install python-discord/modmail-plugins/$plugin@main
```
