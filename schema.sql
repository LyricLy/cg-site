CREATE TABLE People (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL
);

CREATE TABLE Rounds (
    num INTEGER PRIMARY KEY,
    stage INTEGER NOT NULL,
    spec TEXT NOT NULL,
    started_at TIMESTAMP NOT NULL,
    stage2_at TIMESTAMP NOT NULL,
    ended_at TIMESTAMP
);

CREATE TABLE Submissions (
    author_id INTEGER NOT NULL,
    round_num INTEGER NOT NULL,
    submitted_at TIMESTAMP,
    cached_display TEXT,
    position INTEGER,
    persona INTEGER,
    bonus_given INTEGER NOT NULL DEFAULT 0,
    finished_guessing INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (author_id) REFERENCES People(id) ON UPDATE CASCADE,
    FOREIGN KEY (round_num) REFERENCES Rounds(num),
    PRIMARY KEY (author_id, round_num),
    UNIQUE (position, round_num)
);

CREATE TABLE Files (
    name TEXT NOT NULL,
    author_id INTEGER NOT NULL,
    round_num INTEGER NOT NULL,
    content BLOB NOT NULL,
    lang TEXT,
    PRIMARY KEY (name, round_num),
    FOREIGN KEY (author_id, round_num) REFERENCES Submissions(author_id, round_num) ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE Guesses (
    round_num INTEGER NOT NULL,
    player_id INTEGER NOT NULL,
    guess INTEGER NOT NULL,
    actual INTEGER NOT NULL,
    locked INTEGER NOT NULL DEFAULT 0,
    UNIQUE (round_num, player_id, guess),
    UNIQUE (round_num, player_id, actual),
    CHECK (player_id <> guess AND player_id <> actual),
    FOREIGN KEY (player_id, round_num) REFERENCES Submissions(author_id, round_num) ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (guess, round_num) REFERENCES Submissions(author_id, round_num) ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (actual, round_num) REFERENCES Submissions(author_id, round_num) ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE Likes (
    round_num INTEGER NOT NULL,
    player_id INTEGER NOT NULL,
    liked INTEGER NOT NULL,
    UNIQUE (round_num, player_id, liked),
    FOREIGN KEY (player_id, round_num) REFERENCES Submissions(author_id, round_num) ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (liked, round_num) REFERENCES Submissions(author_id, round_num) ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE Targets (
    round_num INTEGER NOT NULL,
    player_id INTEGER NOT NULL,
    target INTEGER NOT NULL,
    PRIMARY KEY (round_num, player_id),
    FOREIGN KEY (player_id, round_num) REFERENCES Submissions(author_id, round_num),
    FOREIGN KEY (target, round_num) REFERENCES Submissions(author_id, round_num)
);

CREATE TABLE Comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    round_num INTEGER NOT NULL,
    parent INTEGER NOT NULL,
    author_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    unchanged_content TEXT,
    posted_at TIMESTAMP NOT NULL,
    edited_at TIMESTAMP,
    reply INTEGER,
    persona INTEGER NOT NULL,
    og_persona INTEGER,
    FOREIGN KEY (parent, round_num) REFERENCES Submissions(author_id, round_num) ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (reply) REFERENCES Comments(id) ON DELETE SET NULL
);

CREATE TABLE Tiebreaks (
    round_num INTEGER NOT NULL,
    player_id INTEGER NOT NULL,
    new_rank INTEGER NOT NULL,
    PRIMARY KEY (round_num, player_id),
    FOREIGN KEY (player_id, round_num) REFERENCES Submissions(author_id, round_num)
);

CREATE VIEW Scores
AS SELECT *, COUNT(*) OVER (PARTITION BY round_num) > 1 AND rank == 1 AS won
FROM (SELECT 
    *, 
    COALESCE(
        (SELECT new_rank FROM Tiebreaks AS T WHERE T.round_num = S.round_num AND T.player_id = S.player_id),
        RANK() OVER (PARTITION BY round_num ORDER BY plus+bonus-minus DESC, plus DESC)
    ) AS rank,
    plus+bonus-minus AS total
FROM (SELECT
    round_num,
    author_id AS player_id,
    (SELECT COUNT(*) FROM Guesses WHERE player_id = author_id AND guess = actual AND Guesses.round_num = Submissions.round_num) AS plus,
    (
        SELECT COUNT(*) FROM Guesses
        INNER JOIN Targets ON Targets.round_num = Guesses.round_num AND Targets.player_id = actual
        WHERE actual = author_id AND guess = Targets.target AND Guesses.round_num = Submissions.round_num
    ) + bonus_given AS bonus,
    (SELECT COUNT(*) FROM Guesses WHERE guess = author_id AND guess = actual AND Guesses.round_num = Submissions.round_num) AS minus
FROM Submissions) AS S);
