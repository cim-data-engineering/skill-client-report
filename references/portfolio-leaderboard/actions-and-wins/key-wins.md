# Key wins

Owns the key wins section: the strongest wins across the portfolio, ten at most, with no limit per site. Scaffold part: `key-wins`. Script: `scripts/key_wins.py`.

## What you write

The choosing and the words. Everything else is the script's: the candidates, the evidence calls, the impact tags, the levels, the site of each win, the ticket links, the date line, the photo downloads and crops.

A portfolio can hold more candidates than anyone can read, so you read them in two passes, and save neither.

1. **Shortlist.** Read the candidate pulls the plan lists to read, where they come back: the quarter's closures with comments and the open actions with comments, twenty sites a pull. Each row carries the ticket's title, site, priority, saving and who commented, nothing more. A pull whose pagination says `has_more` is read on with the same call at the next `start_index`. One that comes back offloaded as a file prints screened and ranked with `key_wins.py digest report <that file> [...]`: the best 60, a third of them work in flight where there is that much; `--top 0` prints them all. One read inline is screened by eye, by the patterns under **Data**. From the titles, the sites and the ranking, pick up to 25 tickets worth reading in full, by **Selection** and **Ranking** below, and write their full ticket ids to `report/shortlist.json`: `["00000000-0000-4000-8000-000000000001", ...]`
2. **Read in full.** `report.py next` prints one pull of the shortlist with its descriptions, solutions and comments. Read it where it comes back and never save it; offloaded, it prints with `key_wins.py digest report <that file> --top 0`, an agent's comments marked as such. Choose by **Selection**, and write `report/wins.json`, best first by **Ranking**:

```json
[{"tickets": ["00000000-0000-4000-8000-000000000001"], "state": "fixed", "heading": "...", "body": "..."},
 {"tickets": ["00000000-0000-4000-8000-000000000002", "00000000-0000-4000-8000-000000000003"], "state": "in_flight", "heading": "...", "body": "..."}]
```

   `tickets` are full ticket ids, every ticket the win stands on, all at one site. `state` is `fixed` or `in_flight`. Where the tickets reference a saving, the body states it, per **Display**
3. `report.py next` prints the impact and photo calls for those tickets. Once they are saved, run `key_wins.py photos report` straight away, since the photo links lapse twenty minutes after the call, then `report.py next` again for the level call
4. Look at the one numbered contact sheet per win, choose by **Photos** below, and add the picks to each win: `"photos": ["w1-2", {"pick": "w1-4", "focus": [0.7, 0.4], "zoom": 2}]`. A win with nothing worth showing gets none
5. After `report.py fill`, look at every tile in `report/tiles/`: a crop can cut off the very detail that earned the photo its place. Adjust `focus` and `zoom` and fill again

This is the section an owner reads to see the portfolio is in good hands: problems caught early and acted on across their buildings, rather than counted. It says what was found, who picked it up and where it got to.

## Section header

Eyebrow: Key wins  
Statement: What was found and acted on this quarter  
Date line: the period alone, "1 July - 21 October 2026."

## Selection

The test is whether the owner would take it as evidence their buildings are in good hands. Two kinds pass:

- **Fixed.** A physical or control change described by whoever made it, so a closure verified rather than asserted
- **Caught and being worked.** A fault the monitoring found that someone is visibly on: raised, assigned, diagnosed, contractor booked or parts on order. Finding a problem before the building finds it the hard way is worth as much to the owner as closing one

Either way it needs a comment history showing a person engaged with it. Exclude alerts resolved by stopping, tuning or ignoring a rule, platform, integration or data mapping work, and actions marked as not doing.

**How many:** the strongest wins across the portfolio, ten at most. A site can carry several, or none; never pad a site in for balance.

## Ranking

Rank by what an owner cares about:

1. Finished repairs before work in flight
2. Critical plant before terminal units: chillers, boilers, cooling towers, air handlers and packaged units before fan coils and VAV boxes
3. Permanent fixes before resets

Write `wins.json` in that order. The script keeps finished repairs ahead of work in flight whatever the order, and otherwise keeps yours.

## Voice

[Writing the narrative](../../../SKILL.md#writing-the-narrative) governs every sentence in the report. It matters most here, and wins add two rules of their own:

- Write as the engineer on the job: what was wrong, what has been done and by whom, where it stands. Then stop
- Say what was done, not what it demonstrates. "Replaced the belts and had it running the next morning" beats "restored reliability to the unit"

No en or em dash anywhere in a heading or body: the portfolio page carries none, and the fill refuses one.

## Display

- Each card carries its site above the impact tag, as an eyebrow: the site name with its state in muted brackets. The script sets it from the win's tickets
- Heading names the outcome, or the finding where the work is still live, plus the equipment type and name
- Under the heading, the level the equipment serves, so the reader can place the win in the building. It is the win's `level`, PEAK's level name as it stands, and a list where the equipment spans levels. Left off where PEAK holds no real level for the equipment
- Tag the win with its impact, above the heading: one of `energy`, `comfort`, `reliability`, `water`, `safety`, `other`. It renders as a small uppercase word with a coloured dot, and the word is what states the impact; the dot only speeds up scanning down the page
- The impact is the one its linked action tickets carry, never one read off the story. A win about a chiller that plainly saves energy is tagged `reliability` if that is what the tickets say
- Where a win links several tickets whose impacts differ, take the most severe: `safety`, then `reliability`, `comfort`, `energy`, `water`, `other`. Never a compound tag, and never two tags on one win
- Where the tickets carry no impact at all, or carry `other`, the tag is `Other`. The script names each such ticket in chat, so the impact can be set in PEAK and the report re-run
- Say where it stands. A win in flight is written as in flight: what was found, who has it, what happens next
- Two to three sentences: what was wrong, what was changed, why it matters
- Where any of the win's tickets reference a saving, in the savings field, the description, the solution or a comment, state it, and wrap the figure in `**` to set it bold: "…closed by 24 June, with an estimated saving of **$6,800**." Give it in the site's currency, rounded sensibly and summed across the win's tickets, with a period only where the ticket gives one. On a win in flight it is the expected saving. Where the savings field holds a figure the text leaves out, `report.py fill` says so in chat
- Lead with the building outcome: comfort, reliability, energy, tenant experience
- Link each action ticket as evidence, with its title as the link name, not the id. Where several tickets form one win, link them all. A ticket title is quoted as PEAK holds it, an en or em dash set as a hyphen

## Photos

Engineers often attach photos to an action ticket as they work it, screenshots among them, and a win the reader can see is easier to believe than one they can only read. Where a win's tickets carry photos, show the ones that best help explain and support it. Space is tight, so the work is choosing, not collecting.

- Choose by one question: which photos best explain and support this win? Usually that is the fault or the fix itself, close up: the seized part, the failed reading, the repaired component in place. Then the equipment the win is about, then a screen that shows the fault or the result, such as a trend with the value that gave it away boxed, or a corrected schedule. For a controls fix, a screen is often the only evidence there is
- Each photo adds something the others do not. Two shots of the same thing waste a tile
- A photo stands for the fix only where the comments say that part was repaired. A tidier view of the same part is more often the fault from another angle
- It has to read at about 5 cm across. Prefer the tighter view of the same evidence, or crop in on the part that matters
- Leave out anything irrelevant or inappropriate for a client report: cartoons and mascots, memes, email signature logos, a person's face, anything that is not this site's plant or its data
- Up to four, in the order the story runs: the unit or the fault, the finding, the fix
- No captions. The win's text explains its photos
- The layout follows the count: one photo sits beside the text, cropped square; two to four run in a row under the heading, a pair cropped 3:2 and three or four cropped square
- Photos never decide whether a win qualifies, nor where it ranks

## When nothing qualifies

- One qualifying win is a section. Show it, with no line apologising for the count
- None means no section: `report.py fill` leaves it out when `wins.json` is an empty list
- Never write the selection out loud on the page: how many closures you read, which you rejected, or why
- Never pad, and never write work as more finished than it is. "The sensor is locked and a replacement is on order" is a win in flight; "the sensor was replaced" is a repair
- Report it in chat instead: what you read, what you rejected, why

## Data

| Step | Call |
| --- | --- |
| Fixed | In the main batch, read and not saved: `tickets.tickets` `status_id:6`, `has_comments:true`, resolved inside the quarter, twenty sites a call, with `site_id`, `summary`, `priority_id`, `savings`, `status_id` and the `comments` (`limit:8`, `user_only:true`) authors and times only |
| In flight | In the main batch, read and not saved: the same, `status_ids:[1,3,7]`, no date bound |
| The shortlist in full | Once `shortlist.json` exists: one `tickets.tickets` on its tickets, read and not saved, with `description`, `solution`, `equipment_ids`, `assignees` and the comments' text |
| Impact, link, title, site | Once `wins.json` exists: one `search_action_tickets` on the wins' tickets, reading `impacts`, `savings`, `ticket_link`, `title`, `site_id` and `equipment_ids` |
| Photos | In the same batch: one `tickets.tickets` on the wins' tickets selecting `site_id` and `attachments.attachment_id`, `file_name`, `mime_type`, `preview.link.url` and `link.url` |
| Level | Once the impact rows are saved: one `platform.equipment` on their `equipment_ids`, selecting `zone.level.level_name` and `zone.level.system` |

- The candidate pulls are the only responses the report reads without saving. Every saved response holds counts, scores, ids and type, level or company names: what people wrote on a ticket never goes into a file
- `has_comments:true` drops each closure nobody wrote on, and holding to the quarter cuts it again. The first pass carries no text but the title, so a large portfolio's candidates stay small enough to come back whole; only the shortlist carries what people wrote
- The digest ranks finished repairs before open work, then by how many people commented, then priority, then a recorded saving, and keeps a third of the list it prints for work in flight. The ranking orders your reading; it never decides a win
- The digest screens out patterns that need no reading: a closure created and resolved the same moment; three or more at one site sharing a resolved second, a bulk cleanup; a ticket whose only commenter is an agent. Two more are left to you, since only the comments show them: closures summarised as still in fault, and alerts closed by stopping or tuning a rule
- `impacts` comes back as a list, sometimes `[]`, which is the `Other` case in **Display**. A level with `system:true` is PEAK's placeholder, not a place, so that equipment gets no level line
- `key_wins.py photos` keeps the image attachments, one copy per file name and sixteen per win, downloads the originals in parallel and tiles them into `report/kw/sheet-w<n>.jpg`. The links are signed and lapse twenty minutes after the call: if the photos step reports them lapsed, make the photo call again and re-run it. Where they cannot be fetched, the wins go out without photos; say so in chat
- The fill turns each photo upright, crops it to its tile around `focus` (fractions across and down the frame) and `zoom` (that many times tighter), shrinks and re-encodes it, which also drops the original's EXIF block, GPS position included. A photo reaches the report only through the script
- The savings currency is the win's site's, from the site facts it takes
