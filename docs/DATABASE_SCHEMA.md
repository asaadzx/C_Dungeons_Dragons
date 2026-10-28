# C1 RAS Hub - Database Schema

## announcements

| Column | Type | Constraints |
| --- | --- | --- |
| id | INTEGER | PK, NOT NULL |
| title | VARCHAR(200) | NOT NULL |
| content | TEXT | NOT NULL |
| category | VARCHAR(20) | NOT NULL |
| created_at | DATETIME | NOT NULL |

## lhr_games

| Column | Type | Constraints |
| --- | --- | --- |
| id | INTEGER | PK, NOT NULL |
| title | VARCHAR(200) | NOT NULL |
| rules | TEXT | NOT NULL |
| max_players | INTEGER | NOT NULL |
| status | VARCHAR(20) | NOT NULL |

## memes

| Column | Type | Constraints |
| --- | --- | --- |
| id | INTEGER | PK, NOT NULL |
| image_url | VARCHAR(300) | NOT NULL |
| caption | TEXT | NOT NULL |

## news_sources

| Column | Type | Constraints |
| --- | --- | --- |
| id | INTEGER | PK, NOT NULL |
| label | VARCHAR(100) | NOT NULL |
| url | VARCHAR(500) | NOT NULL |
| active | BOOLEAN | NOT NULL |
| created_at | DATETIME | NOT NULL |

## students

| Column | Type | Constraints |
| --- | --- | --- |
| id | INTEGER | PK, NOT NULL |
| name_en | VARCHAR(200) | NOT NULL |
| name_ar | VARCHAR(200) | NOT NULL |
| interests | TEXT | NOT NULL |
| website | VARCHAR(300) | NOT NULL |
| facebook | VARCHAR(300) | NOT NULL |
| instagram | VARCHAR(300) | NOT NULL |
| phone | VARCHAR(50) | NOT NULL |
| email | VARCHAR(200) | NOT NULL |
| active | BOOLEAN | NOT NULL |

## ted_talks

| Column | Type | Constraints |
| --- | --- | --- |
| id | INTEGER | PK, NOT NULL |
| title | VARCHAR(300) | NOT NULL |
| url | VARCHAR(500) | NOT NULL |
| thumbnail | VARCHAR(300) | NOT NULL |
| description | TEXT | NOT NULL |

## users

| Column | Type | Constraints |
| --- | --- | --- |
| id | INTEGER | PK, NOT NULL |
| username | VARCHAR(80) | NOT NULL, UNIQUE |
| password_hash | VARCHAR(255) | NOT NULL |
| role | VARCHAR(20) | NOT NULL |
| active | BOOLEAN | NOT NULL |

## attendance_sessions

| Column | Type | Constraints |
| --- | --- | --- |
| id | INTEGER | PK, NOT NULL |
| date | DATE | NOT NULL |
| created_by | INTEGER | FK → users.id, NOT NULL |
| created_at | DATETIME | NOT NULL |
| updated_at | DATETIME | NOT NULL |

## events

| Column | Type | Constraints |
| --- | --- | --- |
| id | INTEGER | PK, NOT NULL |
| organizer_id | INTEGER | FK → students.id, NOT NULL |
| title | VARCHAR(200) | NOT NULL |
| link | VARCHAR(500) | NOT NULL |
| description | TEXT | NOT NULL |
| event_date_actual | DATE | - |
| event_date | VARCHAR(100) | NOT NULL |
| location | VARCHAR(200) | NOT NULL |
| created_at | DATETIME | NOT NULL |

## attendance_audits

| Column | Type | Constraints |
| --- | --- | --- |
| id | INTEGER | PK, NOT NULL |
| session_id | INTEGER | FK → attendance_sessions.id, NOT NULL |
| changed_by | INTEGER | FK → users.id |
| action | VARCHAR(50) | NOT NULL |
| day | DATE | NOT NULL |
| created_at | DATETIME | NOT NULL |

## attendance_records

| Column | Type | Constraints |
| --- | --- | --- |
| id | INTEGER | PK, NOT NULL |
| session_id | INTEGER | FK → attendance_sessions.id, NOT NULL |
| student_id | INTEGER | FK → students.id, NOT NULL |
| status | VARCHAR(20) | NOT NULL |
| note | TEXT | NOT NULL |

## event_requests

| Column | Type | Constraints |
| --- | --- | --- |
| id | INTEGER | PK, NOT NULL |
| event_id | INTEGER | FK → events.id, NOT NULL |
| requester_name | VARCHAR(200) | NOT NULL |
| message | TEXT | NOT NULL |
| status | VARCHAR(20) | NOT NULL |
| user_id | INTEGER | FK → users.id |
| created_at | DATETIME | NOT NULL |

## Relationships

- **events.organizer_id** → **students.id**
- **event_requests.event_id** → **events.id**
- **event_requests.user_id** → **users.id** (optional)
- **attendance_sessions.created_by** → **users.id**
- **attendance_records.session_id** → **attendance_sessions.id**, **attendance_records.student_id** → **students.id**
- **attendance_audits.session_id** → **attendance_sessions.id**, **attendance_audits.changed_by** → **users.id** (optional)
