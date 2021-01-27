# egs_guess_bot

This is a bot on the El Goonish Shive Discord server that clips a random square in the webcomic and lets users try to find which comic it is. 

Pull requests appreciated. License: GPLv3. 

## Setup

Initialize `save.data` with a pickle file with the information in the correct format (read the code for what it expects, sorry). Put a bot token in `token.txt`. Edit hardcoded guild ID and whatnot in `bot.py`. Then bring it up using docker-compose, or just install the `requirements.txt` and run `bot.py`. 