-- Insert data to Student table
-- NOTE: hashed_dummy_pwd: e9a1b8b1d04e855a86630c40b7d560d0
INSERT INTO Student (First_Name, Last_Name, Email, Password_Hash) VALUES ('Link', 'Hopper', 'e12567890@u.nus.edu','e9a1b8b1d04e855a86630c40b7d560d0');

-- Insert data to Session table. Session value was generated from hashlib in python.
INSERT INTO Session (Session_Token, Student_ID, Login_Time) VALUES ('05b3c9de-76f2-4da3-a30c-3cf7bb1139ea', 1, '2025-06-26 04:29:41');

-- Insert data to Assessment table
INSERT INTO Assessment (Title, Due_Date) VALUES ('Assignment 1', '2025-06-30 20:00:00');

-- Insert data to Tasks table
INSERT INTO Tasks VALUES (1, 1, 'SELECT * FROM Student;');

-- Insert data to Submission table
INSERT INTO Submission (Student_ID, Aid, Tid, Code, Submitted_At, Attempt_No, Score) VALUES (1, 1, 1, 'select * from student.', '2025-06-27 11:10:00',1,0.91);
