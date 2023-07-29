DROP TABLE Likes;
DROP TABLE Comments;
ALTER TABLE Files DROP COLUMN hl_content;
ALTER TABLE Submissions DROP COLUMN persona;
ALTER TABLE Submissions DROP COLUMN finished_guessing;
ALTER TABLE Guesses DROP COLUMN locked;
