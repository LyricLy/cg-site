# What is code guessing?
__Players write code to confuse each other, then try to guess which person wrote which bit of code.__

[This link](https://cg.esolangs.gay) should take you to the latest round. Rounds take a couple weeks and are open to members of the [Esolangs Discord Server](https://discord.gg/3UXSK5p). You can learn about esoteric programming languages [here](https://esolangs.org).

## Phases
Each round has a writing phase, a guessing phase, and, eventually, a winner!

### Writing Phase
A problem gets written up on the [website](https://cg.esolangs.gay), and announced in the `#event-discussion` channel on Discord. Usually it's something simple like "sort a list". There'll also be a list of programming languages you can choose, and an API for how your submission should take input and output.

__If you feel like participating, write a program that solves the problem.__
Submit it to the site by signing in and uploading the file.

The trick to winning! the game, is that your program should feel like something the other server members wouldn't expect you to write.
That is, if you often write very clean, very well-documented code, you might choose to write messy, incomprehensible code. If you feel like bluffing, you could even write clean, well-documented code in order to confuse people. It's up to you.

Writing usually lasts a week long.

### Guessing Phase
Once writing is over, the guessing phase is announced in `#event-discussion`. On the website you'll see a list of every player who submitted, along with the code they wrote. Except, __the list is shuffled so you have to guess who wrote which bit of code.__

You guess by clicking and dragging to rearrange the names on the participant list. It saves automatically as long as you've changed the order at all.


After about a week to deliberate, the round is over and players are scored. __For every person you guessed correctly, you earn one point. For each person who guessed you correctly, you lose one point.__ On average you'll end up totalling around one point. Whoever gets the most points is the winner! and gets to pick the challenge for the next round.

It could be you. You could win! Wouldn't that be nice?

### Tiebreaker
If there's a tie for the winner! of the round, it's usually broken based on the number of points gained from guessing correctly. If there's still a tie, however, there's another method.

Wait for the Prime Minister of the United Kingdom to write a tweet, with text in it. You take the sha256 hash of the tweet (in UTF-8), and use the result as a (big-endian) number to index into the (numerically) sorted list of all Discord IDs who tied for the top score in the round. (The lowest ID is at index 0, and the index is modulo the length of the list.) Whoever is selected, wins!

I recommend you make friends in high places if you'd like to influence the result of the tiebreaker.

### Likes
During the guessing phase, you can also click the tickbox next to a name to vote that you like that entry. You can like as many entries as you, well, like. At the end, the game will add up how many likes each entry got. That's like, separate to your score from guessing though. There's no prize but pride.

## Plagiarism
Although it's not very interesting, taking code from third-party sources is usually allowed. However, there is an exception to this. There are 3 criteria for code to count as illegally plagiarised:
- The code was written after the challenge for the round was announced
- The code was written by a member of Esolangs
- The author of the code is not the one who submitted it

If your submission contains any code that meets all of these criteria, it is subject to disqualification.

## Anonymity
If you have a question or a comment, you might want to say it anonymously. We have a bot that can relay messages to people and channels, without displaying your real username.

If you __message `@Esobot#0987` the command `!anon event-discussion`__, then your messages sent to the bot will be forwarded to the `#event-discussion` channel by Esobot. You can put any channel name or username instead of `event-discussion`. You'll be assigned a random Toki Pona name like "jan Sasun" or "jan Papan", and the messages you send to Esobot will be stripped of all punctuation and converted to lowercase before they arrive.

Once you're done communicating anonymously, send `!anon stop` or `!anon leave` to Esobot. Your randomly generated name is usually reset between each round, but you can also ask `@LyricLy#9345` to do so manually if you do something foolish. Be warned that if you use the anonymity for rulebreaking mischief, the server admins do have the ability to unmask you; so don't break rules.

If you have a message you don't want stripped of punctuation/capitalisation, type a backslash `\` at the start of the message. You can also block particular users from messaging you anonymously or opt out altogether — type `!help anon` for more info.

## Culture

### Fun entries
You might have realised: the best way to not get guessed, is to write boring code with no clues in it. But __boring code is boring.__

The majority of entries are interesting instead — as interesting as their creator can make it without making it obvious who wrote the code. __People tend to use the competition as a way to show off their cool tricks.__ You'll see golfed code that tries to minimise the amount of characters in the program, outlandishly convoluted ways of doing a simple task, short stories, highly-optimised performant solutions, and more. If you like weird, overengineered code, you'll enjoy reading through [previous rounds](https://cg.esolangs.gay/index/).

### Fun tasks
If you win! and get to pick a new challenge, the best-loved ones are usually very simple. It's never supposed to be difficult to solve the task, because the fun of the game is in writing a program that expresses your individuality without seeming like it expresses your individuality. It's also recommended that your challenges have a language option for everyone who wants to join. Often, you would allow Python and C, Rust or JavaScript if you like them, and another weird language that tickles your fancy.

### Who's who?
Most of the chatter around the round is in the `#event-discussion` channel. If you're new, don't worry, we don't bite.

You'll never know for sure who wrote which entry until the guessing phase is over, but if you look through past rounds you'll probably get some sense of what the regulars write. Check the [stats page](https://cg.esolangs.gay/stats) to sort by rounds played, or to skim all the entries someone has submitted.
