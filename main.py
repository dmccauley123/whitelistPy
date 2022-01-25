import discord
import json
import regex as re
import os
from validator import *
import traceback
from copy import deepcopy

GUILD_TEMPLATE = {
    'whitelist_channel': None,
    'whitelist_role': None,
    'blockchain': None,
    'data': {}
}
VALID_BLOCKCHAINS = ['eth', 'sol']


class InvalidCommand(Exception):
    """
    An exception to be thrown when an invalid command is encountered
    """

    def __init__(self):
        pass


class WhitelistClient(discord.Client):
    """
    The discord client which manages all guilds and corrosponding data
    """

    def __init__(self, data, *, loop=None, **options):
        """
        Args:
            data (dict): A data dictionary stored in memory.
        """
        super().__init__(loop=loop, **options)
        self.data = data
        self.admin_commands = {
            'channel': self.set_whitelist_channel,
            'role': self.set_whitelist_role,
            'blockchain': self.set_blockchain,
            'data': self.get_data,
            'config': self.get_config,
            'clear': self.clear_data,
            'help.admin': self.help_admin
        }
        self.public_commands = {
            'help': self.help,
            'check': self.check
        }
        self.validators = {
            'eth': validate_eth,
            'sol': validate_sol
        }
        self.regex = {
            'channel': re.compile(">channel <#\d+>$"),
            'role': re.compile(">role <@&\d+>$"),
            'blockchain': re.compile(">blockchain \w{3}")
        }
    
    def _log(self, head : str, text : str) -> None:
        with open('log.txt', 'a+') as log:
            log.write(f"Head: {head}\n   Text: {str(text)}\n\n")

    def backup_data(self) -> None:
        with open('data.json', 'w+') as out_file:
            json.dump(self.data, out_file)

    async def on_ready(self) -> None:
        print('Logged in as')
        print(self.user.name)
        print(self.user.id)
        print("Initialising...")
        async for guild in self.fetch_guilds():
            if str(guild.id) not in self.data.keys():
                print(f"Adding guild '{str(guild)}' to data.")
                data[str(guild.id)] = deepcopy(GUILD_TEMPLATE)
        print("-------------")

    async def set_whitelist_channel(self, message: discord.Message) -> None:
        """ Handles setting the channel that will be used for whitelisting

        Args:
            message (discord.Message): The discord message containing the command request

        Raises:
            InvalidCommand: The message structure was not as expected.
        """
        channels = message.channel_mentions
        if len(channels) != 1 or not self.regex['channel'].fullmatch(message.content):
            raise InvalidCommand()
        self.data[str(message.guild.id)]['whitelist_channel'] = channels[0].id
        await message.reply(f"Successfully set whitelist channel to <#{channels[0].id}>",
                            mention_author=True)

    async def set_whitelist_role(self, message: discord.Message) -> None:
        """ Handles setting the role that will be used for whitelisting

        Args:
            message (discord.Message): The discord message containing the command request

        Raises:
            InvalidCommand: The message structure was not as expected.
        """
        roles = message.role_mentions
        if len(roles) != 1 or not self.regex['role'].fullmatch(message.content):
            raise InvalidCommand()
        self.data[str(message.guild.id)]['whitelist_role'] = roles[0].id
        await message.reply(f"Successfully set whitelist role to <@&{roles[0].id}>",
                            mention_author=True)

    async def set_blockchain(self, message: discord.Message) -> None:
        """ Handles setting the blockchain that will be used for validating wallet addresses.

        Args:
            message (discord.Message): The discord message containing the command request

        Raises:
            InvalidCommand: The message structure was not as expected.
        """
        code = message.content[-3:]
        if code in VALID_BLOCKCHAINS:
            self.data[str(message.guild.id)]['blockchain'] = code
            await message.reply(f"Successfully set blockchain to {code}",
                                mention_author=True)
        else:
            raise InvalidCommand()

    async def get_config(self, message: discord.Message) -> None:
        """ Returns the current config of a given server to the user.

        Args:
            message (discord.Message): The discord message that sent the request.
        """
        channelID = self.data[str(message.guild.id)]['whitelist_channel']
        roleID = self.data[str(message.guild.id)]['whitelist_role']
        blockchain = self.data[str(message.guild.id)]['blockchain']
        replyStr = f"Whitelist Channel: <#{channelID}>\nWhitelist Role: <@&{roleID}>\nBlockchain: {blockchain}"
        reply = discord.Embed(
            title=f'Config for {message.guild}', description=replyStr)
        await message.reply(embed=reply, mention_author=True)

    async def get_data(self, message: discord.Message) -> None:
        """ Sends a CSV file to the user containing the current data stored by the bot

        Args:
            message (discord.Message): The discord message that sent the request.
        """
        file_name = f'{message.guild.id}.csv'
        with open(file_name, 'w+') as out_file:
            out_file.write('userId, walletAddress\n')
            out_file.writelines(
                map(lambda t: f"{t[0]},{t[1]}\n", self.data[str(message.guild.id)]['data'].items()))
            out_file.flush()
        await message.reply('Data for server is attached.',
                            file=discord.File(file_name))
        os.remove(file_name)

    async def clear_data(self, message: discord.Message) -> None:
        """ Clears the data and config currently stored by the bot regarding the current server

        Args:
            message (discord.Message): The discord message that sent the request.
        """
        self.data[str(message.guild.id)] = deepcopy(GUILD_TEMPLATE)
        await message.reply("Server's data and config has been cleared.")

    async def help_admin(self, message: discord.Message) -> None:
        """ Returns a window that provides some help messages regarding how to use the bot for an admin.

        Args:
            message (discord.Message): The discord message that sent the request.
        """
        msg = discord.Embed(title="Whitelist Manager Help (Admin)")
        desc = "Whitelist Manager is a bot designed to assist you in gathering wallet addresses for NFT drops.\nAfter configuring the discord bot, users who are 'whitelisted' will be able to record their crypto addresses which you can then download as a CSV.\nNote, the `config` must be filled out before the bot will work."
        body = "`>channel #channelName`: Sets the channel to listen for wallet addresses on.\n`>role @roleName`: Sets the role a user must possess to be able to add their address to the whitelist.\n`>blockchain eth/sol`: Select which blockchain this NFT drop will occur on, this allows for validation of the addresses that are added.\n`>config`: View the current server config.\n`>data`: Get discordID:walletAddress pairs in a CSV format.\n`>clear`: Clear the config and data for this server.\n`>help.admin`: This screen.\n`>help`: How to use help screen."
        msg.description = desc
        msg.add_field(name="COMMANDS", value=body)
        await message.reply(embed=msg)
    
    async def help(self, message: discord.Message) -> None:
        """ Returns a window that provides some help messages regarding how to use the bot.

        Args:
            message (discord.Message): The discord message that sent the request.
        """
        msg = discord.Embed(title="Whitelist Manager Help")
        desc = "Whitelist Manager is a bot designed to assist in gathering wallet addresses for NFT drops."
        body = "`>check`: will tell you whether or not your wallet has been recorded in the whitelist\n`>help`: This screen\n`>help.admin`: Provides a help screen to assist in configuring the bot (admin only).\n\nHow to use: Send your wallet address to the whitelist chat to record it!\nThe message should contain just the wallet address (no `>`)."
        msg.description = desc
        msg.add_field(name="COMMANDS", value=body)
        await message.reply(embed=msg)
    
    async def check(self, message: discord.Message) -> None:
        guild_id = str(message.guild.id)
        if str(message.author.id) in self.data[guild_id]['data']:
            await message.reply(f"You are whitelisted! Address: `{self.data[guild_id]['data'][str(message.author.id)]}`")
        else:
            await message.reply(f"Your wallet is not yet on the whitelist. Use `>help` for more info!.")

    async def on_message(self, message: discord.Message) -> None:
        """ Responds to the 'on_message' event. Runs the appropriate commands given the user has valid privellages.

        Args:
            message (discord.Message): The discord message that sent the request.
        """
        
        try:
            # we do not want the bot to reply to itself
            if message.author.bot or not isinstance(message.author, discord.member.Member):
                return

            # Handle commands
            if message.author.guild_permissions.administrator and message.content.startswith(">"):
                print(f"Admin command (from {message.author.id}): {message.content}")
                command = message.content.split()[0][1:]
                if command in self.admin_commands.keys():
                    try:
                        await self.admin_commands[command](message)
                        self.backup_data()
                        return
                    except InvalidCommand:
                        await message.reply("Invalid command argument.", mention_author=True)
            
            if message.content.startswith('>'):
                print(f"User command from {message.author.id}: {message.content}")
                command = message.content.split()[0][1:]
                if command in self.public_commands.keys():
                    try:
                        await self.public_commands[command](message)
                        return
                    except InvalidCommand:
                        await message.reply("Invalid command argument.", mention_author=True)
                else:
                    commands = str(list(self.public_commands.keys()))[1:-1].replace("'","`")
                    await message.reply(f'Valid commands are: {commands}, use `>help` for more info.')

            # Handle whitelist additions
            if (message.channel.id == self.data[str(message.guild.id)]['whitelist_channel']
                and (self.data[str(message.guild.id)]['whitelist_role']
                    in map(lambda x: x.id, message.author.roles))) and not message.content.startswith(">"):
                if self.validators[self.data[str(message.guild.id)]['blockchain']](message.content):
                    self.data[str(message.guild.id)]['data'][str(
                        message.author.id)] = message.content
                    await message.reply(
                        f"Your wallet `{message.content}` has been validated and recorded.", mention_author=True)
                    self.backup_data()
                else:
                    await message.reply(f"The address `{message.content}` is invalid.")
        except Exception:
            tb = traceback.format_exc()
            exception_string = tb.replace('\n','---')
            self._log(exception_string, f"{message}\nContent:   {message.content}")
    
    async def on_guild_join(self, guild: discord.Guild) -> None:
        """ Initialises a server when the bot joins

        Args:
            guild (discord.Guild): The guild that the server has joined
        
        """
        if str(guild.id) not in self.data:
            self.data[str(guild.id)] = deepcopy(GUILD_TEMPLATE)
        
        self._log("New Guild", f"{guild.id}, {guild.name}")
        


if __name__ == '__main__':
    access_token = os.environ["ACCESS_TOKEN"]
    try:
        with open('data.json', 'r') as data_file:
            data = json.load(data_file)
    except FileNotFoundError:
        data = {}
    client = WhitelistClient(data)
    client.run(access_token)
