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
    author_id INTEGER NOT NULL,
    round_num INTEGER NOT NULL,
    submitted_at TIMESTAMP,
    position INTEGER,
    FOREIGN KEY (author_id) REFERENCES People(id),
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
    FOREIGN KEY (author_id, round_num) REFERENCES Submissions(author_id, round_num)
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
    FOREIGN KEY (player_id, round_num) REFERENCES Submissions(author_id, round_num),
    FOREIGN KEY (guess, round_num) REFERENCES Submissions(author_id, round_num),
    FOREIGN KEY (actual, round_num) REFERENCES Submissions(author_id, round_num)
);

CREATE TABLE Likes (
    round_num INTEGER NOT NULL,
    player_id INTEGER NOT NULL,
    liked INTEGER NOT NULL,
    UNIQUE (round_num, player_id, liked),
    FOREIGN KEY (player_id, round_num) REFERENCES Submissions(author_id, round_num),
    FOREIGN KEY (liked, round_num) REFERENCES Submissions(author_id, round_num)
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
    posted_at TIMESTAMP NOT NULL,
    edited_at TIMESTAMP,
    reply INTEGER,
    anonymous INTEGER NOT NULL,
    FOREIGN KEY (parent, round_num) REFERENCES Submissions(author_id, round_num),
    FOREIGN KEY (reply) REFERENCES Comments(id)
);
