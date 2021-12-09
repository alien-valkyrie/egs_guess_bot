import discord
import asyncio
from urllib.request import urlopen, HTTPError
from PIL import Image, ImageDraw
import io
import random
import time
import datetime
import pickle
import re
import sys

# warning, this is very bad code, sorry in advance
# feel free to help clean it up if you want

intents = discord.Intents.default()
intents.members = True
client = discord.Client(intents=intents)

prefix = 'k!'
size = 100
hint_size_inc = 25
admin_uid = 168176809152610304
bot_uid = 400524860113158154
channel_id = 400844273534107648
# channel_id = 307346084483694592
# for cleaning up non bmp characters from log output, for windows reasons
non_bmp_map = dict.fromkeys(range(0x10000, sys.maxunicode + 1), 0xfffd)

# hs = save file, not sure why i called it that
hs_scores = None # userid: [solves, fastest, attempts]
hs_comicstats = None # comicid: [hints, fastest, skips]
hs_pokes = None # (user a, user b): [last a ts, last b ts, turn, streak]

@client.event
async def on_ready():
    # counting channel
    global ct_channel
    await client.change_presence(activity=discord.Game(name=prefix+'help for options'))
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    ct_channel = client.get_channel(528313370424639498)
    print('------')

@client.event
async def on_message(message):
    global hs_scores
    global hs_comicstats
    global gameComicImageUrl
    global gameSuppressAnswers
    
    #counting
    if message.channel.id == 660620075874648075:#528313344340525066
        correct = True
        async for msg in message.channel.history(limit=1, before=message):
            last_num = msg.content.replace(",", "")
            this_num = message.content.replace(",", "");
            try:
                int(last_num)
            except ValueError:
                correct = True #don't correct anything if last number isn't correct
                continue
            
            try:
                int(this_num)
            except ValueError:
                correct = False #correct if this isn't a number
                continue
            
            if int(last_num) + 1 != int(this_num):
                correct = False
            
        if not correct:
            await message.add_reaction(discord.utils.get(client.emojis, name='oeuf'))
            await ct_channel.send(message.author.mention + " sent `" + message.content + "` which is not the number that follows `" + msg.content + "`!")
        return
    
    if message.channel.id == 639864035004645397 and message.author.id != bot_uid:
        try:
            num = int(message.content)
        except ValueError:
            correct = True #don't correct anything if last number isn't correct
            return
        
        num += 1
        if num in [42, 69, 420, 8008135]:
            num += 1
        await message.channel.send(str(num))
    
    #uptime
    """
    if message.content == "k!uptime":
        if str(client.get_server(235843952153067541).get_member(342757470046781450).status) == "offline":
            hrs = int((time.time() - 1576572051) / 60 / 60)
            days = hrs // 24
            hrs = hrs % 24
            await message.channel.send("It has been `" + str(days) + " days and " + str(hrs) + " hours` since <@342757470046781450> went down for maintenance.")
        else:
            await message.channel.send("Rejoice! <@342757470046781450> is back online!")
        return
    """
    
    print (message.author, ":", message.content.translate(non_bmp_map))

    if (message.author.id == bot_uid):
        return
    
    if (message.guild == None): #is a dm
        await message.channel.send("Please don't DM me, I'm incredibly shy! Go DM kuilin instead, she's social :P")
        if (message.author.id != admin_uid):
            return
    
    #hug
    """
    if message.content.startswith('maid!hug'):
        if len(message.mentions) == 0:
            target = message.author
        else:
            target = message.mentions[0]
        await message.channel.send("*hugs " + target.mention + "*")
        return
    """
    
    if message.content.startswith(prefix.upper()):
        message.content = message.content.replace(prefix.upper(), prefix, 1)
    
    if not message.content.startswith(prefix):
        return
    
    # pokes
    if message.content.startswith(prefix + 'daily') or message.content.startswith(prefix + 'poke'):
        if len(message.mentions) == 0:
            await message.channel.send("Tag someone!")
            return
        pair = tuple(sorted([message.mentions[0].id, message.author.id]))
        ab = 0 if pair[0] == message.author.id else 1
        # hs_pokes: (user a, user b): [last a date, last b date, streak], a and b sorted
        # only the date is tracked (to do the "reset at midnight utc" thing)
        # each poke updates the last date of that party
        # also, if both their and their partner's previous poke was yesterday, then increment streak
        # otherwise (except if partner's poke was today, lol) break streak

        today = datetime.datetime.now(tz=datetime.timezone.utc).date()
        yesterday = today - datetime.timedelta(days=1)

        if pair not in hs_pokes:
            hs_pokes[pair] = [0, 0, 0]

        if hs_pokes[pair][ab] == today:
            await message.channel.send("You already poked that user today! Pokes reset at midnight UTC.")
            return

        if hs_pokes[pair][ab] == yesterday and hs_pokes[pair][1-ab] == yesterday:
            hs_pokes[pair][2] += 1
        elif hs_pokes[pair][ab] == yesterday and hs_pokes[pair][1-ab] == today:
            pass
        else:
            hs_pokes[pair][2] = 1
        hs_pokes[pair][ab] = today
        hs_save()

        msg = "\*pokes " + message.mentions[0].mention + "\*"
        if hs_pokes[pair][2] > 1:
            msg += " Streak: " + str(hs_pokes[pair][2])
        if hs_pokes[pair][2] > 10:
            msg += " 🔥"
        elif hs_pokes[pair][2] > 100:
            msg += " ❤"
        elif hs_pokes[pair][2] > 1000:
            msg += " 💕"
        await message.channel.send(msg)
        return

    if (message.channel.id != channel_id): #wontfix but multiple servers makes this not work
        # await message.channel.send("Please play with the bot in <#" + str(channel_id) + "> instead of here.")
        if (message.author.id != admin_uid):
            return
        
    next_round = False
    if message.content == prefix + 'hint':
        secs = (datetime.datetime.now() - gameTime).seconds
        if message.author.id != admin_uid and secs < 4 * 60:
            await message.channel.send('It has only been **' + str(round(secs / 60)) + '** minutes. Hint is only available after **5** minutes.')
        else:
            game_hint()
            await game_print_image(client, message, 'Hint activated. Larger image:')
            hs_inc(hs_comicstats, gameComicId, 0)
    elif message.content == prefix + 'me':
        if (str(message.author.id) not in hs_scores):
            await message.channel.send('No stats saved for you.')
        else:
            #this is very crude, but idc
            ret = "Your place:"
            n = 0
            for x in sorted(hs_scores, key=(lambda x: hs_scores[x][0]), reverse=True):
                n += 1
                if x == str(message.author.id):
                    ret += "\n" + str(n) + ". " + str(message.author.display_name) + ": **" + str(hs_scores[x][0]) + "** solves, **" + str(hs_scores[x][1]) + "**s fastest solve, **" + str(hs_scores[x][2]) + "** attempts"
            await message.channel.send(ret)
    elif message.content == prefix + 'cheat':
        if message.author.id == admin_uid:
            await game_print_big_image(client, message)
            await message.channel.send('Correct answer: '+ str(gameComicId))
        else:
            await message.channel.send('Lol')
    elif message.content == prefix + 'restart':
        if message.author.id == admin_uid:
            import os
            await message.channel.send('OK')
            os._exit(1)
        else:
            await message.channel.send('Lol')
    elif message.content == prefix + 'skip':
        secs = (datetime.datetime.now() - gameTime).seconds
        if message.author.id != admin_uid and secs < 1 * 60 * 60:
            await message.channel.send('It has only been ' + str(round(secs / 60)) + ' minutes! Skip is only available after 1 hour.')
        else:
            hs_inc(hs_comicstats, gameComicId, 2)
            await message.channel.send('Skipped. The correct answer was <http://www.egscomics.com/comic/' + gameComicId + '>.')
            next_round = True
    elif message.content.startswith(prefix + 'solve ') or message.content.startswith(prefix + 's '):
        if gameSuppressAnswers:
            return
        if message.content.startswith(prefix + 'solve '):
            url = message.content.split(' ')[1]
        else:
            url = 'http://www.egscomics.com/comic/' + message.content.split(' ')[1]

        url = url.split('egscomics.com')
        if len(url) != 2:
            await message.channel.send("That doesn't look like a valid URL to the comic.")
            return
        
        url = 'http://www.egscomics.com' + url[1]
        
        correct = False
        if url == 'http://www.egscomics.com/comic/' + gameComicId:
            correct = True
        else:
            content_url = get_comic_url(url)
            if content_url == last_comic_image or content_url == '':
                await message.channel.send("That doesn't look like it links to a particular comic.")
                return
            correct = (gameComicImageUrl == get_comic_url(url))
        
        hs_inc(hs_scores, str(message.author.id), 2)
        if correct:
            gameSuppressAnswers = True
            #intentional bug for fractal (and others!) to find
            ttime = (datetime.datetime.now() - gameInitTime).seconds
            print(ttime < hs_scores[str(message.author.id)][1], ttime, hs_scores[str(message.author.id)][1])
            if message.author.id not in hs_scores or ttime < hs_scores[str(message.author.id)][1]:
                hs_inc(hs_scores, str(message.author.id), 1, ttime)
            if gameComicId not in hs_comicstats or ttime < hs_comicstats[gameComicId][1]:
                hs_inc(hs_comicstats, gameComicId, 1, ttime)
            hs_inc(hs_scores, str(message.author.id), 0)
            await message.channel.send('Congratulations, <@'+str(message.author.id)+'>, <' + url + '> is the correct answer! <@'+str(message.author.id)+'> has solved **' + str(hs_scores[str(message.author.id)][0]) + '** rounds, and this round was solved in **' + str(ttime) + '** seconds.')
            await game_print_big_image(client, message)
            
            person_solved = hs_scores[str(message.author.id)][0]
            if person_solved%100 == 0 or (((person_solved & (person_solved - 1)) == 0) and person_solved > 127): #multiple of 2 starting 128, or multiple of 100
                await message.channel.send("Wow, **"+str(person_solved)+"** rounds, that's a lot! Good job, <@"+str(message.author.id)+">!")
            next_round = True
        else:
            await message.channel.send('Sorry, <@'+str(message.author.id)+'>, <' + url + '> is not the correct answer.')
        """stats disabled because it really didn't add much, plus it was giving away the answer, lol
    elif message.content == prefix + 'stats':
        #there are much, much better ways to do this... lol
        ret = "Most difficult comics:"
        n = 0
        for x in sorted(hs_comicstats, key=(lambda x: hs_comicstats[x][1]), reverse=True)[:10]:
            n += 1
            ret += "\n" + str(n) + ". <http://www.egscomics.com/?id=" + str(x) + ">: **" + str(hs_comicstats[x][0]) + "** hints, **" + str(hs_comicstats[x][1]) + "**s fastest, **" + str(hs_comicstats[x][2]) + "** skips" 
        await message.channel.send(ret)
        """
    elif message.content.startswith(prefix + 'top ') or message.content == prefix + 'top':
        number = -1;
        if message.content == prefix + 'top':
            number = 1
        else:
            try:
                number = int(message.content[len(prefix + 'top '):])
            except ValueError:
                pass
        if number <= 0:
            await message.channel.send('`' + message.content[len(prefix + 'top '):] + '` is not a valid page number!')
            return
        
        ret = "Top players:"
        if number != 1:
            ret += " (page " + str(number) + ")"
        number -= 1
        number *= 10
        n = number
        for x in sorted(hs_scores, key=(lambda x: hs_scores[x][0]), reverse=True)[number:number+10]:
            n += 1
            mem = message.guild.get_member(int(x))
            if mem is None:
                mem = "(member left server)"
            else:
                mem = str(mem.display_name)
            ret += "\n" + str(n) + ". " + mem + ": **" + str(hs_scores[x][0]) + "** solves, **" + str(hs_scores[x][1]) + "**s fastest solve, **" + str(hs_scores[x][2]) + "** attempts"
        if number == 0:
            ret += "\nUse `" + prefix + "top 2` to view the 2nd page!"
        await message.channel.send(ret)
    elif message.content == prefix + 'help':
        await message.channel.send("""This is a simple game created by kuilin to boost its players' memory recall of the nuances of all the EGS main story strips.

Information commands:
`"""+prefix+"""help` - Prints this help message
`"""+prefix+"""me` - Check your own stats
`"""+prefix+"""top` - High scores for players
`"""+prefix+"""source` - Source code information

Gameplay commands:
`"""+prefix+"""check` - Checks the current round's image again
`"""+prefix+"""hint` - Makes the image bigger
`"""+prefix+"""skip` - Skip is available if a round is unsolved for 1 hour
`"""+prefix+"""solve http://www.egscomics.com/comic/2003-04-23` - Try to solve the round, if the answer's that comic (shortcut: `"""+prefix+"""s 2003-04-23`)
The full solve command can take a URL in any form (specifically, it loads the page and checks if it contains the correct image). The shortcut only takes a slug (which isn't necessarily a date - for example, `question-mark-04` is a valid slug).
""")
    elif message.content == prefix + 'source':
        await message.channel.send("https://github.com/likuilin/egs_guess_bot")
    else:
        await game_print_image(client, message, 'Current round: (`' + prefix + 'help` for help)')

    if next_round:
        game_next()
        await game_print_image(client, message, 'Next round:')
    gameSuppressAnswers = False

#this is almost certainly not the right way to do this
def find_mid(text, left, right):
    r = text.rfind(left)
    return text[r + len(left) : text.find(right, r + len(left))];

#game state, all global
gameImage = None #original comic image, of type image
gameComicWhole = None #bytesio for the whole comic plus the pandora around the region
gameComicCrop = None #bytesio for the current cropped section
gameComicId = None #current ID
gameTime = None #time since round begin, or since last hint, for cooldown
gameInitTime = None #time since round began, for stats
gameX = None #x of topleft of pandora
gameY = None #y of topleft of pandora
hint_size = None #current additional size of hint, starts at 0 for each new round
gameSuppressAnswers = False #disallow answering between rounds, fixing race condition

async def game_print_image(client, message, msg = None):
    gameComicCrop.seek(0)
    await message.channel.send(file=discord.File(gameComicCrop, filename="image.png"), content=msg)

async def game_print_big_image(client, message, msg = None):
    gameComicWhole.seek(0)
    await message.channel.send(file=discord.File(gameComicWhole, filename="image.png"), content=msg)

def game_next(getNewComic = True): #getNewComic is false for initial loading
    global gameImage
    global gameComicWhole
    global gameComicId
    global gameComicImageUrl
    global gameTime
    global gameInitTime
    global gameX
    global gameY
    global hint_size
    gameTime = datetime.datetime.now()
    gameInitTime = datetime.datetime.now()

    #random comic id
    if getNewComic:
        gameComicId = random.choice(comic_slugs[:-1]).lower() #do not choose last comic because that is used for error checking

    print ("Next game: ", gameComicId)
    
    #grab the image
    try:
        gameComicImageUrl = get_comic_url("http://egscomics.com/comic/"+gameComicId)
        gameImage = Image.open(urlopen(gameComicImageUrl, timeout=10))
        
        if getNewComic:
            gameX = random.randint(0, gameImage.size[0] - size)
            gameY = random.randint(0, gameImage.size[1] - size)
        x = gameX
        y = gameY
        
        #crop the image
        hint_size = 0
        crop_image()
        
        #draw pandora around the correct region
        img = gameImage.convert("RGBA")
        draw = ImageDraw.Draw(img)
        draw_rectangle(draw, ((x, y), (x+size, y+size)), (255,0,0,255), 5)
        gameComicWhole = io.BytesIO()
        img.save(gameComicWhole, format="png")
        
        print("Next game ready: ", gameComicId)
        hs_save()
    except HTTPError:
        print("Error retrieving ID ", gameComicId)
        time.sleep(10)
        game_next()

def game_hint():
    global hint_size
    global gameTime
    hint_size += hint_size_inc
    gameTime = datetime.datetime.now()
    crop_image()

def crop_image():
    global gameComicCrop
    global hint_size
    x = gameX
    y = gameY
    image = gameImage.crop((x-hint_size, y-hint_size, x+size+hint_size, y+size+hint_size))
    gameComicCrop = io.BytesIO()
    image.save(gameComicCrop, format="png")

def get_comic_url(url):
    page_content = str(urlopen(url, timeout=10).read())
    page_content = find_mid(page_content, "<img title=", ">")
    ret = find_mid(page_content, "comics/", "\"")
    if ret != "":
        return "http://www.egscomics.com/comics/" + ret
    else:
        return ""

#thanks https://stackoverflow.com/questions/34255938/
def draw_rectangle(draw, coordinates, color, width=1):
    for i in range(width):
        rect_start = (coordinates[0][0] - i, coordinates[0][1] - i)
        rect_end = (coordinates[1][0] + i, coordinates[1][1] + i)
        draw.rectangle((rect_start, rect_end), outline = color)

def hs_inc(dic, key, value, set = None): #highscores_increment, or setting, lol
    if (key not in dic):
        dic[key] = [0, 1000000, 0] #hmm
    if set is not None:
        dic[key][value] = set
    else:
        dic[key][value] += 1
    hs_save()

def hs_save():
    fw = open('save.data', 'wb')
    pickle.dump([hs_scores, hs_comicstats, gameComicId, gameX, gameY, hs_pokes], fw)
    fw.close()
    
def hs_load():
    global hs_scores
    global hs_comicstats
    global gameComicId
    global gameX
    global gameY
    global hs_pokes
    with open('save.data', 'rb') as f:
        data = pickle.load(f)
    hs_scores = data[0]
    hs_comicstats = data[1]
    gameComicId = data[2]
    gameX = data[3]
    gameY = data[4]
    if len(data) <= 5:
        hs_pokes = {}
    else:
        hs_pokes = data[5]

hs_load()

#get current comic (at least, first comic of current arc) as limit for random
content = str(urlopen("http://www.egscomics.com/comic/archive", timeout=10).read());
comic_slugs = re.findall('<option value="comic\/([\w-]+)"', content)
print("Loaded comics:", len(comic_slugs))
last_comic_image = get_comic_url("http://egscomics.com/comic/"+comic_slugs[-1])

game_next(False)
with open('token.txt', 'r') as f:
    secret = f.read()
client.run(secret)
