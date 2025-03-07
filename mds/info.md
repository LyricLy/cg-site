# What is code guessing?
__Players write code to confuse each other, then try to guess which person wrote which bit of code.__

[This link](/) should take you to the latest round. Rounds take a couple weeks and are open to members of the [official Discord server](https://discord.gg/gUNZvN3k7p).

## Phases
Each round has a writing phase, a guessing phase, and, eventually, a winner!

### Writing Phase
A problem gets written up on the [website](/), and announced in the `#new-rounds` channel on Discord. Usually it's something simple like "sort a list". The programming languages you're allowed to use will be specified, along with an outline of the interface your program has to follow.

__If you feel like participating, write a program that solves the problem.__
Submit it to the site by signing in and uploading the file.

The trick to winning! the game, is that your program should feel like something the other server members wouldn't expect you to write.
That is, if you often write very clean, very well-documented code, you might choose to write messy, incomprehensible code. If you feel like bluffing, you could even write clean, well-documented code in order to confuse people. It's up to you.

Writing usually lasts a week long.

### Guessing Phase
Once writing is over, the guessing phase begins. On the website you'll see a list of every player who submitted, along with the code they wrote. Except, __the list is shuffled so you have to guess who wrote which bit of code.__

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
Although it's not very interesting, taking code from third-party sources is usually allowed. However, there is an exception to this. There are 3 criteria for code to count as illegally plagiarised:
- The code was written after the challenge for the round was announced
- The code was written by a member of the server
- The author of the code is not the one who submitted it

If your submission contains any code that meets all of these criteria, it is subject to disqualification.

## Anonymity
If you have a question or a comment, you might want to say it anonymously. We have a bot that can relay messages to people and channels, without displaying your real username.

If you __message `@Canon#8213` the command `!anon cg-discussion`__, then your messages sent to the bot will be forwarded to the `#cg-discussion` channel by Canon. You can also write someone's username to speak to them privately. By default, you'll be assigned a random Toki Pona name like "jan Sasun" or "jan Papan", and the messages you send to Canon will be stripped of all punctuation and converted to lowercase before they arrive. You can change name or turn off the message translation using the bot or by visiting this site's [anon settings page](/anon).

Once you're done communicating anonymously, send `!anon stop` or `!anon leave` to Canon. Your randomly generated name is usually reset between each round, but you have the option of switching to other names through the bot or site. Be warned that if you use the anonymity for mischief, the server admins do have the ability to unmask you.

If you have a message you don't want stripped of punctuation/capitalisation, type a backslash `\` at the start of the message.

Those are the basics, but the bot has a few more features as well, which you can find out about through `!help anon` or by checking out the [anonymous settings page](/anon). Happy hiding!

## Culture

### Fun entries
You might have realised: the best way to not get guessed, is to write boring code with no clues in it. But __boring code is boring.__

The majority of entries are interesting instead — as interesting as their creator can make it without making it obvious who wrote the code. __People tend to use the competition as a way to show off their cool tricks.__ You'll see golfed code that tries to minimise the amount of characters in the program, outlandishly convoluted ways of doing a simple task, short stories, highly-optimised performant solutions, and more. If you like weird, overengineered code, you'll enjoy reading through [previous rounds](/index/).

### Fun tasks
If you win! and get to pick a new challenge, the best-loved ones are usually very simple. It's never supposed to be difficult to solve the task, because the fun of the game is in writing a program that expresses your individuality without seeming like it expresses your individuality. Challenges usually allow any language, but you can restrict the selection as long as you include Python and a few other common languages.

### Who's who?
Most of the chatter around the round is in the `#cg-discussion` channel. If you're new, don't worry, we don't bite.

You'll never know for sure who wrote which entry until the guessing phase is over, but if you look through past rounds you'll probably get some sense of what the regulars write. Check the [stats page](/stats/) to sort by rounds played, or to skim all the entries someone has submitted.
