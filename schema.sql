-- ===========================================================================
-- schema.sql
-- Defines the table structures for the C! RAS Hub SQLite database.
--
-- This file is executed automatically by database.py (init_db) and by
-- seed.py. "IF NOT EXISTS" makes it safe to run multiple times: it will
-- never wipe data that already exists.
--
-- The CHECK(...) rules act as extra safety so that only allowed values can
-- be stored in fields like category, status and role.
-- ===========================================================================


-- ---------------------------------------------------------------------------
-- Table 1: announcements
-- Powers the Official Bulletin & Culture Board on the home page (/).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS announcements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,          -- unique ID, auto-incremented
    title TEXT NOT NULL,                           -- headline of the announcement
    content TEXT NOT NULL,                         -- full body text
    -- category must be exactly one of these four values:
    category TEXT CHECK(category IN ('News', 'Tip', 'Meme', 'TED')) NOT NULL,
    -- timestamp is filled in automatically with the current date/time:
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


-- ---------------------------------------------------------------------------
-- Table 2: lhr_games
-- Powers the LHR Games & Activity Center (/lhr and /lhr/game/<id>).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS lhr_games (
    id INTEGER PRIMARY KEY AUTOINCREMENT,          -- unique ID, auto-incremented
    title TEXT NOT NULL,                           -- name of the game/activity
    rules TEXT NOT NULL,                           -- rulebook / description text
    max_players INTEGER NOT NULL,                  -- maximum team size allowed
    -- status defaults to 'Upcoming' and is restricted to these three values:
    status TEXT CHECK(status IN ('Upcoming', 'Active', 'Completed')) DEFAULT 'Upcoming'
);


-- ---------------------------------------------------------------------------
-- Table 3: students
-- Powers the Student Directory (/directory) and profiles (/student/<id>).
-- Extra columns hold the contact/social links students can fill in.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,          -- unique ID, auto-incremented
    name TEXT NOT NULL,                            -- student's full name
    interests TEXT NOT NULL DEFAULT '',            -- free-text "about me" / interests
    -- role defaults to 'Student' and is restricted to these three values:
    role TEXT CHECK(role IN ('Student', 'Leader', 'Admin')) DEFAULT 'Student',
    website TEXT DEFAULT '',                       -- personal website URL
    facebook TEXT DEFAULT '',                      -- Facebook profile URL
    instagram TEXT DEFAULT '',                     -- Instagram profile URL
    phone TEXT DEFAULT '',                         -- phone number (used in a tel: link)
    email TEXT DEFAULT ''                          -- email (used in a mailto: link)
);


-- ---------------------------------------------------------------------------
-- Table 4: ted_talks
-- Powers the "KOSEN Spotlight" TED talk on the home page (/).
-- One random row from this table is shown on every page load.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ted_talks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,          -- unique ID, auto-incremented
    title TEXT NOT NULL,                           -- talk title
    url TEXT NOT NULL,                             -- link to the talk on ted.com
    thumbnail TEXT NOT NULL,                       -- local image path (static/)
    description TEXT NOT NULL                      -- short blurb shown under the title
);


-- ---------------------------------------------------------------------------
-- Table 5: memes
-- Powers the "KOSEN Spotlight" meme on the home page (/).
-- One random row from this table is shown on every page load.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS memes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,          -- unique ID, auto-incremented
    image_url TEXT NOT NULL,                       -- local image path (static/)
    caption TEXT NOT NULL                          -- punchline shown with the image
);


-- ---------------------------------------------------------------------------
-- Table 6: events
-- Powers the Community Events board (/schedule).
-- Each event is posted by a student (organizer_id -> students.id), so the
-- board links directly to the Student Directory.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,          -- unique ID, auto-incremented
    organizer_id INTEGER NOT NULL,                 -- who is organizing (students.id)
    title TEXT NOT NULL,                           -- e.g. "Cairo Jazz Festival"
    link TEXT DEFAULT '',                          -- festival / hackathon / event link
    description TEXT DEFAULT '',                   -- extra details
    event_date TEXT DEFAULT '',                    -- free-text date, e.g. "Sat 12 Nov"
    location TEXT DEFAULT '',                      -- free-text place
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- Links this event to a student row (SQLite does not enforce it, but it
    -- documents the relationship and powers the profile page).
    FOREIGN KEY (organizer_id) REFERENCES students(id)
);


-- ---------------------------------------------------------------------------
-- Table 7: event_requests
-- Powers the "Ask to go with them" feature on the events board.
-- A visitor types their name (and an optional message) to say they want to
-- join an event. The "user_id" column is reserved for the future login
-- system (Post-Midterm roadmap) and is left NULL for now.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS event_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,          -- unique ID, auto-incremented
    event_id INTEGER NOT NULL,                     -- which event (events.id)
    requester_name TEXT NOT NULL,                  -- name typed by the visitor
    message TEXT DEFAULT '',                       -- optional short message
    user_id INTEGER,                               -- reserved for future login
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (event_id) REFERENCES events(id)
);
