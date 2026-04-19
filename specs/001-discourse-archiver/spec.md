# Feature Specification: Discourse Post Archiver

**Feature Branch**: `001-discourse-archiver`
**Created**: 2026-04-18
**Status**: Draft
**Input**: User description: "Download Discourse posts to local storage for archival purposes. Use config.toml file for parameters (API key, Discourse forum URL, output directory, earliest date to be retrieved, post categories or filters, etc.), env variables override config.toml values (at least for the API key). Posts should be downloaded to the specified output directory with subdirectory structure YYYY/MM/<thread-topic.md> based on the date of the first post in the thread, one markdown file per thread with complete thread information (post content, comments, names, dates). The tool should be interruptible with ctrl-c, and when run again it should gracefully resume downloading all remaining posts from the earliest specified date."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Initial Archive Download (Priority: P1)

A user runs the tool for the first time against a Discourse forum. The tool reads
configuration from config.toml, authenticates with the Discourse API, and downloads
all threads from the earliest configured date onward, writing one markdown file per
thread into YYYY/MM/ subdirectories of the output directory.

**Why this priority**: Core value delivery. Without this, nothing else matters.

**Independent Test**: Can be fully tested by running the tool against a Discourse forum
with a valid config.toml and verifying that markdown files appear in the correct directory
structure with correct content.

**Acceptance Scenarios**:

1. **Given** a valid config.toml with API key, forum URL, output directory, and earliest
   date, **When** the tool is run, **Then** all threads with a first post on or after the
   earliest date are downloaded as markdown files under `output_dir/YYYY/MM/<thread-slug.md>`.

2. **Given** a thread with multiple posts (replies), **When** that thread is downloaded,
   **Then** the markdown file contains the original post, all replies, and for each: author
   name, post date, and post body.

3. **Given** an API key in both config.toml and the environment variable `DISCOURSE_API_KEY`,
   **When** the tool runs, **Then** the environment variable value takes precedence over
   config.toml.

---

### User Story 2 - Interrupt and Resume (Priority: P2)

A user starts a download, presses Ctrl-C to stop it partway through, then runs the tool
again. The tool detects which threads have already been fully downloaded and have no new
replies, and skips them; threads with new replies since the last download are re-downloaded
and their files overwritten.

**Why this priority**: Archives are often large; uninterruptible downloads are impractical.

**Independent Test**: Can be tested by running the tool, interrupting it, re-running it,
and verifying that already-downloaded up-to-date files are not re-fetched, threads with
new replies are refreshed, and remaining threads are downloaded.

**Acceptance Scenarios**:

1. **Given** a partial download was interrupted by Ctrl-C, **When** the tool is run again
   with the same configuration, **Then** it skips threads whose output files exist and whose
   post count matches the current count on the forum, and downloads/overwrites the rest.

2. **Given** a previously downloaded thread has received new replies since it was archived,
   **When** the tool is run again, **Then** it re-downloads that thread and overwrites the
   existing file with the updated content.

3. **Given** the tool is running and receives Ctrl-C, **When** it shuts down, **Then** it
   exits cleanly without corrupting any partially-written file (partial files are either
   absent or valid).

4. **Given** a completed prior run (backfill finished), **When** the tool is run again,
   **Then** it queries only topics with forum activity since the last run and does NOT
   re-paginate through historical pages that predate that activity window.

---

### User Story 3 - Category/Filter Selection (Priority: P3)

A user wants to archive only specific categories of a Discourse forum, not the entire
instance. They configure category IDs or names in config.toml and only those categories
are downloaded.

**Why this priority**: Large forums may have irrelevant categories; selective archiving
reduces noise and storage.

**Independent Test**: Can be tested by configuring one category in config.toml and
verifying that only threads from that category appear in the output.

**Acceptance Scenarios**:

1. **Given** one or more category filters in config.toml, **When** the tool runs, **Then**
   only threads belonging to those categories are downloaded.

2. **Given** no category filter in config.toml, **When** the tool runs, **Then** all
   accessible categories are downloaded.

---

### Edge Cases

- What happens when the Discourse API returns a rate-limit response?
- What happens when a thread title contains characters invalid in a filesystem path?
- What happens when the output directory does not exist?
- What happens when the API key is missing from both config.toml and the environment?
- What happens when two threads in the same YYYY/MM have slugs that collide?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The tool MUST read configuration from a `config.toml` file in the working
  directory or at a path specified via a command-line argument.
- **FR-002**: The tool MUST support at minimum these config fields: `api_key`, `forum_url`,
  `output_dir`, `earliest_date`, `categories` (optional list), `max_retries` (integer,
  default 5).
- **FR-003**: The environment variable `DISCOURSE_API_KEY` MUST override the `api_key`
  value from config.toml when set.
- **FR-004**: The tool MUST download all threads whose first post is on or after
  `earliest_date`.
- **FR-005**: Each thread MUST be saved as a single markdown file containing: thread title,
  all posts in order, and for each post: author display name, post date/time (ISO 8601),
  and post body (HTML converted to markdown).
- **FR-006**: Output files MUST be placed at `<output_dir>/YYYY/MM/<thread-slug.md>` where
  YYYY/MM is derived from the date of the first post in the thread.
- **FR-007**: The tool MUST be interruptible via Ctrl-C and exit cleanly without corrupting
  output files.
- **FR-008**: On re-run, the tool MUST skip threads whose output file already exists AND
  whose post count matches the current count on the forum. Threads with new replies since
  the last download MUST be re-downloaded and their output file overwritten.
- **FR-013**: On a rate-limit response or transient network error, the tool MUST retry the
  request using exponential backoff. The number of retry attempts MUST be configurable via
  `max_retries` in config.toml (default: 5). If all retries are exhausted, the tool MUST
  abort with a clear error message and a non-zero exit code.
- **FR-012**: The tool MUST persist a local state record (e.g., a sidecar metadata file)
  for each downloaded thread containing at minimum: thread ID, post count at time of
  download, and download timestamp. This record is used to detect new replies on re-run.
- **FR-009**: When `categories` is specified in config, the tool MUST restrict downloads
  to those categories only.
- **FR-010**: Output filenames MUST use the Discourse-provided topic slug (e.g.,
  `my-topic-title.md`). The slug is already URL-safe; no additional sanitization is
  required.
- **FR-011**: The output directory MUST be created automatically if it does not exist.
- **FR-014**: The tool MUST maintain a global archive state file in the output directory
  (`archive.state.json`) recording: `backfill_complete` (whether full backfill to
  `earliest_date` has finished), `last_run` (timestamp of last clean completion), and
  `oldest_topic_date` (cursor: `created_at` of the oldest topic processed so far).
  `oldest_topic_date` MUST be updated atomically after each page during backfill, so it
  survives interrupts. `backfill_complete` and `last_run` MUST only be written on clean
  (uninterrupted) completion.
- **FR-015**: When `backfill_complete` is `true`, the tool MUST operate in incremental
  mode: paginate only topics with forum activity since `last_run`, stopping as soon as a
  topic's last-activity timestamp predates `last_run`. When `backfill_complete` is `false`
  or absent, the tool operates in backfill mode. If `oldest_topic_date` is present, topics
  newer than that cursor MUST be fast-skipped (no API call) so that resumed backfills do
  not re-check already-processed pages.

### Key Entities

- **Thread**: A top-level Discourse topic. Has a title, slug, creation date, category,
  and one or more posts.
- **Post**: A single message within a thread. Has an author (display name), created-at
  timestamp, and body content.
- **Config**: The set of parameters controlling tool behavior (forum URL, credentials,
  output location, date filter, category filter).
- **DownloadState**: A per-thread metadata record stored locally alongside the output file.
  Contains thread ID, post count at last download, and download timestamp. Used to detect
  when a thread has received new replies and needs to be refreshed.
- **ArchiveState**: A single global state record stored in the output directory. Tracks
  whether the full backfill to `earliest_date` has completed, and the timestamp of the last
  successful run. Used to switch between backfill mode (paginate all historical pages) and
  incremental mode (only examine topics with forum activity since the last run).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can archive an entire Discourse forum category with a single command
  invocation and no manual intervention.
- **SC-002**: After an interrupted run, re-running the tool downloads only the threads not
  yet present on disk — no duplicate network requests for already-archived threads. After a
  completed run, subsequent runs query only topics with recent forum activity, without
  re-paginating through all historical pages.
- **SC-003**: Every downloaded markdown file is human-readable and contains all posts in
  the thread with author names and dates visible.
- **SC-004**: The tool exits within 5 seconds of receiving Ctrl-C, leaving no corrupted
  files behind.
- **SC-006**: The tool prints one output line per downloaded thread and a summary line
  on completion (e.g., "Downloaded 42 threads, skipped 17, updated 3").
- **SC-005**: A user can change `earliest_date` to a later date and re-run without
  re-downloading files that already exist.

## Clarifications

### Session 2026-04-19

- Q: After a completed backfill, should re-runs avoid re-paging through all historical topics? -> A: Yes. A global state file tracks backfill completion and last-run timestamp. Once backfill is complete, subsequent runs operate in incremental mode: only topics with forum activity since the last run are examined. Historical pages are not re-paginated.
- Q: How does graceful resumption work when backfill is interrupted before completion? -> A: archive.state.json includes an oldest_topic_date cursor updated after each page. On resume, topics newer than the cursor are fast-skipped without API calls; pagination resumes from the cursor forward. Only backfill_complete and last_run require a clean completion to write.

### Session 2026-04-18

- Q: When re-running and a previously downloaded thread has new replies, what should happen? -> A: Re-download the thread and overwrite the existing file with updated content.
- Q: What progress output should the tool display during operation? -> A: One line per thread downloaded (e.g., `[2024/03] thread-slug.md`), plus a final summary line on completion.
- Q: Should the tool download threads sequentially or in parallel? -> A: Sequential - one thread at a time.
- Q: When the tool hits a rate limit or transient network error, what should it do? -> A: Exponential backoff with automatic retry; retry limit configurable in config.toml, default 5.
- Q: What should be used as the basis for the output filename? -> A: The Discourse-provided slug (already URL-safe, no sanitization needed).

## Assumptions

- The target Discourse instance exposes the standard Discourse API (v2 or later).
- The API key has at least read access to the categories being archived.
- The tool is a command-line utility, not a daemon or service.
- HTML-to-markdown conversion preserves the semantic meaning of post content; exact
  visual fidelity is not required.
- Thread slugs generated by Discourse are unique within a given month; if a collision
  occurs, a numeric suffix (e.g., `thread-slug-2.md`) is appended.
- Rate limiting and transient network errors are handled by exponential backoff with
  automatic retry. The retry limit defaults to 5 and is configurable via `max_retries`
  in config.toml.
- The tool targets Linux/macOS environments; Windows support is out of scope for v1.
- Threads are downloaded sequentially; parallel downloading is out of scope for v1.
