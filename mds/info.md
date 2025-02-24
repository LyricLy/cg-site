# What is miscellanea guessing?
__Players make things to confuse each other, then try to guess which person made what.__

This is a game based on [code guessing](https://codeguessing.gay/info) with the same rules but different mediums. [This link](/) should take you to the latest round. Rounds take a couple weeks and are open to members of the [code guessing Discord server](https://discord.gg/gUNZvN3k7p).

## Phases
Each round has a creation phase, a guessing phase, and, eventually, a winner!

### Creation Phase
A task gets written up on the [website](/), and announced in the `#event-announcements` channel on Discord. Usually it's something simple like "take a picture". The specifics of what you are to submit will be described.

__If you feel like participating, follow the instructions and make what the specification calls for.__
Submit it to the site by signing in and uploading the file(s).

The trick to winning! the game, is that your creation should feel like something the other server members wouldn't expect you to make.
For instance, if you're someone who would take a very clean picture with great composition, you might choose to take a chaotic, blurry picture. If you feel like bluffing, you could even take a good photo in order to confuse people. It's up to you.

Creation usually lasts a week long.

### Guessing Phase
Once creation is over, the guessing phase begins. On the website you'll see a list of every player who submitted, along with the work they did. Except, __the list is shuffled so you have to guess who did what.__

You guess by clicking and dragging to rearrange the names on the participant list. It saves automatically as long as you've changed the order at all.


After about a week to deliberate, the round is over and players are scored. __For every person you guessed correctly, you earn one point. For each person who guessed you correctly, you lose one point.__ On average you'll end up totalling around one point. Whoever gets the most points is the winner! and gets to pick the challenge for the next round.

It could be you. You could win! Wouldn't that be nice?

### Tiebreaker
If there's a tie for the winner! of the round, it's usually broken based on the number of points gained from guessing correctly. If there's still a tie, however, there's another method.

You take the sha256 hash of the round number (in base-10, in ASCII), and use the result as a (big-endian) number to index into the (numerically) sorted list of all Discord IDs who tied for the top score in the round. (The lowest ID is at index 0, and the index is modulo the length of the list.) Whoever is selected, wins!

To ensure victory, we recommend you pay off other players to throw the game. You cannot influence the result of the tiebreaker.

### Likes
During the guessing phase, you can click the "like" button on an entry to show that you like it. You can like as many entries as you, well, like. At the end, the game will add up how many likes each entry got. That's like, separate to your score from guessing though. There's no prize but pride.

## Plagiarism
Although it's not very interesting, taking things from third-party sources is usually allowed. However, there is an exception to this. There are 3 criteria for part of a submission to count as illegally plagiarised:
- It was made after the challenge for the round was announced
- It was made by a member of the server
- The author of the content is not the one who submitted it

If your submission contains anything that meets all of these criteria, it is subject to disqualification.

## Anonymity
If you have a question or a comment, you might want to say it anonymously. We have a bot that can relay messages to people and channels, without displaying your real username.

If you __message `@Canon#8213` the command `!anon event-discussion`__, then your messages sent to the bot will be forwarded to the `#event-discussion` channel by Canon. You can also write someone's username to speak to them privately. By default, you'll be assigned a random Toki Pona name like "jan Sasun" or "jan Papan", and the messages you send to Canon will be stripped of all punctuation and converted to lowercase before they arrive. You can change name or turn off the message translation using the bot or by visiting this site's [anon settings page](/anon).

Once you're done communicating anonymously, send `!anon stop` or `!anon leave` to Canon. Your randomly generated name is usually reset between each round, but you have the option of switching to other names through the bot or site. Be warned that if you use the anonymity for mischief, the server admins do have the ability to unmask you.

If you have a message you don't want stripped of punctuation/capitalisation, type a backslash `\` at the start of the message.

Those are the basics, but the bot has a few more features as well, which you can find out about through `!help anon` or by checking out the [anonymous settings page](/anon). Happy hiding!

## Culture

### Fun entries
You might have realised: the best way to not get guessed, is to make very simplistic things with no distinguishing features. You might take a photo of a white wall, for example. But __boring things are boring.__

The majority of entries are interesting instead — as interesting as their creator can make it without making it obvious who did it. __People tend to use the competition as a way to show off their cool tricks.__ You'll see creativity in innumerable forms here. If you like weird, you'll enjoy reading through [previous rounds](/index/).

### Who's who?
Most of the chatter around the round is in the `#event-discussion` channel. If you're new, don't worry, we don't bite.

You'll never know for sure who wrote which entry until the guessing phase is over, but if you look through past rounds you'll probably get some sense of what the regulars like to do. Check the [stats page](/stats/) to sort by rounds played, or to skim all the entries someone has submitted.
