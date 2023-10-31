# Scroll
 A cog for the Redbot Discord bot framework that adds manual recruitment functionality for use in the Nationstates browser game.

 ## Installation

 To install:
 
```
[p]repo add Scroll https://github.com/Derpseh/Scroll
[p]cog list Scroll
[p]cog install Scroll scroll
[p]load scroll
```
[p] being the prefix set for your specific RedBot instance. Having the downloader cog enabled is also necessary for the above to function.

Please note that you will need to host your own RedBot instance, whether this is on your own machine or a VPS or similar.
Instructions on setting RedBot itself can be found [here](https://docs.discord.red/en/stable/install_guides/index.html).

## Usage

`setagent <str>`: sets the User-Agent which this cog will use to communicate with NS. Common practice would be to use the nation name of whoever's running the bot. **SET YOUR USER-AGENT BEFORE DOING ANYTHING ELSE; MANY OTHER COMMANDS WILL NOT WORK WITHOUT IT**

`queuestart`: Pings NS for a list of newly founded nations every 30 minutes and adds it to a backlog.

`queuestop`: Stops the above process.

`queuesize`: Displays the current backlog size for every region registered to the bot.

`wipequeue <region_name>`: wipes the backlog for the given region (use underscores for regions with more than one word in them)

`template add <%template-id%> <region_url>`: registers a recruitment template for use with the bot (to get a template, send a telegram with your desired body text to "tag:template"; make sure to check the box indicating that said template is for recruitment purposes; then grab the ID it gives you.)

`template remove <%template-id%>`: removes a template currently registered to you.

`template list`: provides a list of templates currently registered to you.

`start <template number>`: starts an active recruiting session. template number here **does not** mean the %template-id% string used above, but rather the number shown when you use `[b]template list`. Thus: recruiting with the first template registered to you would be `[b]start 1`, and so on.

`stop`: removes yourself from the current recruiting session, and ends it if no one is left actively recruiting.

`forcestop`: removes *everyone* from the current recruiting session and ends it.

`delay <number>`: sets the delay between messages during an active session. This can be anything from 50-250 seconds (give or take)

`leaderboards`: displays a list of recruiters, ranked by how many telegrams they've sent in total.

`status`: returns some status info on what the bot's currently doing.

`tgqueue`: displays how many telegrams NS has queued for delivery for manual/api/stamps.

## Credits
[Twentysix26](https://github.com/Twentysix26) - Creator of the Red discord bot framework i'm piggybacking off of.
