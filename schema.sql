CREATE TABLE People (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL
);

CREATE TABLE Rounds (
    num INTEGER PRIMARY KEY,
    stage INTEGER NOT NULL,
    spec TEXT NOT NULL,
    started_at TIMESTAMP NOT NULL,
    stage2_at TIMESTAMP,
    ended_at TIMESTAMP
);

CREATE TABLE Submissions (
    round_num INTEGER NOT NULL,
    author_id INTEGER NOT NULL,
    submitted_at TIMESTAMP,
    cached_display TEXT,
    position INTEGER,
    persona INTEGER,
    target INTEGER,
    rank_override INTEGER,
    bonus_given INTEGER NOT NULL DEFAULT 0,
    finished_guessing INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (author_id) REFERENCES People(id) ON UPDATE CASCADE,
    FOREIGN KEY (round_num) REFERENCES Rounds(num),
    FOREIGN KEY (round_num, target) REFERENCES Submissions(round_num, author_id),
    PRIMARY KEY (round_num, author_id),
    UNIQUE (round_num, position)
);

CREATE INDEX submissions_by_author ON Submissions (author_id);

CREATE TABLE Files (
    round_num INTEGER NOT NULL,
    author_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    lang TEXT,
    content BLOB NOT NULL,
    PRIMARY KEY (round_num, name),
    FOREIGN KEY (round_num, author_id) REFERENCES Submissions(round_num, author_id) ON DELETE CASCADE ON UPDATE CASCADE
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
    FOREIGN KEY (round_num, player_id) REFERENCES Submissions(round_num, author_id) ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (round_num, guess) REFERENCES Submissions(round_num, author_id) ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (round_num, actual) REFERENCES Submissions(round_num, author_id) ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE Likes (
    round_num INTEGER NOT NULL,
    player_id INTEGER NOT NULL,
    liked INTEGER NOT NULL,
    UNIQUE (round_num, player_id, liked),
    FOREIGN KEY (round_num, player_id) REFERENCES Submissions(round_num, author_id) ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (round_num, liked) REFERENCES Submissions(round_num, author_id) ON DELETE CASCADE ON UPDATE CASCADE
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
    FOREIGN KEY (round_num, parent) REFERENCES Submissions(round_num, author_id) ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (reply) REFERENCES Comments(id) ON DELETE SET NULL
);

CREATE VIEW Scores
AS SELECT *, COUNT(*) OVER (PARTITION BY round_num) > 1 AND rank == 1 AS won
FROM (SELECT 
    round_num, player_id, plus, bonus, minus,
    COALESCE(
        rank_override,
        RANK() OVER (PARTITION BY round_num ORDER BY plus+bonus-minus DESC, plus DESC)
    ) AS rank,
    plus+bonus-minus AS total
FROM (SELECT
    round_num,
    author_id AS player_id,
    (SELECT COUNT(*) FROM Guesses WHERE player_id = author_id AND guess = actual AND Guesses.round_num = Submissions.round_num) AS plus,
    (SELECT COUNT(*) FROM Guesses WHERE actual = author_id AND guess = target AND Guesses.round_num = Submissions.round_num) + bonus_given AS bonus,
    (SELECT COUNT(*) FROM Guesses WHERE guess = author_id AND guess = actual AND Guesses.round_num = Submissions.round_num) AS minus,
    rank_override
FROM Submissions));
