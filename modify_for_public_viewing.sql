DROP TABLE Likes;
DROP TABLE Comments;
ALTER TABLE Submissions DROP COLUMN cached_display;
ALTER TABLE Submissions DROP COLUMN persona;
ALTER TABLE Submissions DROP COLUMN finished_guessing;
ALTER TABLE Guesses DROP COLUMN locked;
