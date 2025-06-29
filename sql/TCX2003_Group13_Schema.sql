-- CREATE Student table
CREATE TABLE IF NOT EXISTS Student (
    Student_ID INT PRIMARY KEY AUTO_INCREMENT,
    First_Name VARCHAR(100),
    Last_Name VARCHAR(100),
    Email VARCHAR(100) UNIQUE,
    Password_Hash VARCHAR(255)
);

-- CREATE Session table
CREATE TABLE IF NOT EXISTS Session (
    Session_Token VARCHAR(36) PRIMARY KEY,
    Student_ID INT,
    Login_Time DATETIME DEFAULT CURRENT_TIMESTAMP,
    Is_Active BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (Student_ID) REFERENCES Student(Student_ID)
);

-- CREATE Assessment table
CREATE TABLE IF NOT EXISTS Assessment(
	Aid INT PRIMARY KEY AUTO_INCREMENT,
	Title VARCHAR(255),
	Due_Date DATETIME
);

-- CREATE Tasks table
CREATE TABLE IF NOT EXISTS Tasks(
	Tid INT,
	Aid INT,
	Model_Answer VARCHAR(5000),
	PRIMARY KEY (Aid,Tid),
	FOREIGN KEY (Aid) REFERENCES Assessment(Aid)
);

-- CREATE Submission table
CREATE TABLE IF NOT EXISTS Submission(
	Submission_ID INT PRIMARY KEY AUTO_INCREMENT,
	Student_ID INT,
	Aid INT,
	Tid INT,
	Code VARCHAR(5000),
	Submitted_At DATETIME,
	Attempt_No INT,
	Score DECIMAL(5,2), -- Up to 999.99
	FOREIGN KEY(Student_ID) REFERENCES Student(Student_ID),
	FOREIGN KEY (Aid, Tid) REFERENCES Tasks(Aid, Tid)
);