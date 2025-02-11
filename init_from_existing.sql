ATTACH 'the.db' AS Other;

INSERT INTO People (id, name)
             SELECT id, name
 FROM Other.People;
INSERT INTO Rounds (num, stage, spec, started_at, stage2_at, ended_at)
             SELECT num, stage, spec, started_at, stage2_at, ended_at
 FROM Other.Rounds;
INSERT INTO Submissions (round_num, author_id, submitted_at, cached_display, position, persona, target, rank_override, bonus_given, finished_guessing)
                  SELECT round_num, author_id, submitted_at, cached_display, position, persona, target, rank_override, bonus_given, finished_guessing
 FROM Other.Submissions;
INSERT INTO Files (round_num, author_id, name, lang, content)
            SELECT round_num, author_id, name, lang, content
 FROM Other.Files;
INSERT INTO Guesses (round_num, player_id, guess, actual, locked)
              SELECT round_num, player_id, guess, actual, locked
 FROM Other.Guesses;
INSERT INTO Likes (round_num, player_id, liked)
            SELECT round_num, player_id, liked
 FROM Other.Likes;
INSERT INTO Comments (id, round_num, parent, author_id, content, unchanged_content, posted_at, edited_at, reply, persona, og_persona)
               SELECT id, round_num, parent, author_id, content, unchanged_content, posted_at, edited_at, reply, persona, og_persona
 FROM Other.Comments;
