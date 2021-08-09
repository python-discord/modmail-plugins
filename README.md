# Modmail Plugins
Modmail plugins for our Modmail bot, located at https://github.com/kyb3r/modmail.

## List of plugins
- **Case insensitive snippets**: Allow snippets to be ran even if with the wrong case. For example, `?Dm-RePort` will be recognized as `?dm-report`.
- **Close message:** Add a `?closemessage` command that will close the thread after 15 minutes with a default message.
- **MDLink**: Generate a ready to paste link to the thread logs.
- **Reply cooldown**: Forbid you from sending the same message twice in ten seconds.
- **Tagging**: Add a `?tag` command capable of adding a `$message｜` header to the channel name.

## Installing a plugin
To install a plugin, simply run the following command:
```
?plugin install python-discord/modmail-plugins/$plugin@main
```
