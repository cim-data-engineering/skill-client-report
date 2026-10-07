# Key wins

Owns the key wins section. No operational impact row. Scaffold part: `key-wins`. Script: `scripts/key_wins.py`. One choice in the section prompt with `alerts-resolved.md`, Actions and key wins.

## What you write

The choosing and the words. Everything else is the script's: the candidates, the evidence calls, the impact tags, the levels, the ticket links, the order, the statement and date line, the photo downloads and crops.

1. Read `report/kw/digest.md`: the quarter's closures with comments and the open actions with comments, with their comment histories, after the patterns that need no reading are screened out
2. Choose by **Selection** below, and write `report/wins.json`, best first:

```json
[{"tickets": ["afbbae74"], "state": "fixed", "heading": "...", "body": "...", "snap": "..."},
 {"tickets": ["9df9aa6a", "1f788c8e"], "state": "in_flight", "heading": "...", "body": "..."}]
```

   `tickets` are the 8-character ids in the digest, every ticket the win stands on. `state` is `fixed` or `in_flight`, which sets the section's statement and date line. `snap` only with equipment health in, per **Display**
3. `report.py next` prints the impact, photo and level calls for those tickets; make them, then run `key_wins.py photos report`
4. Look at the one numbered contact sheet per win, choose by **Photos** below, and add the picks to each win: `"photos": ["w1-2", {"pick": "w1-4", "focus": [0.7, 0.4], "zoom": 2}]`. A win with nothing worth showing gets none
5. After `report.py fill`, look at every tile in `report/tiles/`: a crop can cut off the very detail that earned the photo its place. Adjust `focus` and `zoom` and fill again

This is the section the facility manager reads first and the one they forward to the owner. Every other section says how the building performed; this one says what was found, who picked it up and where it got to. It is the evidence the building is in good hands: problems caught early and acted on, rather than counted. It is what the owner is paying for.

## Key wins

Statement: "What we found and acted on this quarter". Where every win is a finished repair, "What changed in the building this quarter" is better.
Date: the quarter

**Voice:**

[Writing the narrative](../../SKILL.md#writing-the-narrative) governs every sentence in the report. It matters most here, and wins add two rules of their own:

- Write as the engineer on the job: what was wrong, what has been done and by whom, where it stands. Then stop
- Say what was done, not what it demonstrates. "Replaced the belts and had it running the next morning" beats "restored reliability to the unit"

**Selection:**

The test is whether the facility manager would forward it to the owner as evidence the building is in good hands. Two kinds pass:

- **Fixed.** A physical or control change described by whoever made it, so a closure verified rather than asserted
- **Caught and being worked.** A fault the monitoring found that someone is visibly on: raised, assigned, diagnosed, contractor booked or parts on order. Finding a problem before the building finds it the hard way is worth as much to the owner as closing one, so it belongs on the page

Either way it needs a comment history showing a person engaged with it. Exclude alerts resolved by stopping, tuning or ignoring a rule, platform, integration or data mapping work, and actions marked as not doing.

**Display:**

- Heading names the outcome, or the finding where the work is still live, plus the equipment type and name
- Under the heading, the level the equipment serves, so the reader can place the win in the building. It is the win's `level`, PEAK's level name as it stands, and a list where the equipment spans levels. Leave it off where PEAK holds no real level for the equipment
- Tag the win with its impact, above the heading: one of `energy`, `comfort`, `reliability`, `water`, `safety`, `other`, carried in the bundle as the win's `impact` key. It renders as a small uppercase word with a coloured dot, and the word is what states the impact — the dot only speeds up scanning down the page
- The impact is the one its linked action tickets carry, never one you read off the story. A win about a chiller that plainly saves energy is tagged `reliability` if that is what the tickets say. The engineer who worked the ticket set that field, and the report has no standing to overrule it
- Where a win links several tickets whose impacts differ, take the most severe: `safety`, then `reliability`, `comfort`, `energy`, `water`, `other`. Never merge two into a compound tag, and never show two tags on one win
- Where the tickets carry no impact at all, or carry `other`, tag it `Other` rather than picking the one that would look best. Then say so in chat — name the ticket and its title — so the user can set the impact in PEAK and re-run. Fixing the ticket fixes every report that reads it; guessing here fixes nothing and puts a claim on the page the ticket does not support
- Say where it stands. A win in flight is written as in flight: what was found, who has it, what happens next. The date line under the section heading follows the wins too, so do not leave a line promising everything was fixed when some of it is still open
- Two to three sentences: what was wrong, what was changed, why it matters
- Lead with the building outcome: comfort, reliability, energy, tenant experience
- Rank by what the owner cares about. Critical plant over terminal units, permanent fixes over one-off resets
- Link the action ticket as evidence with the `ticket_link` its row carries, using the action title as the link name, not the id
- Where several tickets form one win, link them all
- Where a win also appears in the equipment health snapshot, say so in the `snap` line. The scaffold keeps that line only when equipment health is in the report, so if it is not there the cross-reference is not yours to add

**Photos:**

Engineers often attach photos to an action ticket as they work it, screenshots among them, and a win the reader can see is easier to believe than one they can only read. Where a win's tickets carry photos, show the ones that best help explain and support it. Space is tight, so the work is choosing, not collecting.

- Choose by one question: which photos best explain and support this win? Usually that is the fault or the fix itself, close up: the seized part, the failed reading, the repaired component in place. Then the equipment the win is about, then a screen that shows the fault or the result, such as a trend with the value that gave it away boxed, or a corrected schedule. For a controls fix, a screen is often the only evidence there is
- Each photo adds something the others do not. Two shots of the same thing waste a tile
- A photo stands for the fix only where the comments say that part was repaired. A tidier view of the same part is more often the fault from another angle
- It has to read at about 5 cm across. A close shot reads at a glance, while a whole BMS page or a plant room from the doorway shrinks to a texture, so prefer the tighter view of the same evidence, or crop in on the part that matters
- Leave out anything irrelevant or inappropriate for a client report: cartoons and mascots, memes, email signature logos, a person's face, anything that is not this site's plant or its data. Use judgement: a photo that would puzzle or embarrass the reader stays off
- Up to four, in the order the story runs: the unit or the fault, the finding, the fix
- No captions. The win's text explains its photos, and a caption is one more claim to get wrong
- Wins with photos lead: those with a row, then those with one, then the rest, with the ranking above ordering each group. The layout follows the count and is not yours to set: one photo sits beside the text, two to four run in a row under the heading
- Photos never decide whether a win qualifies. They change how a win is shown and where it sits, nothing else

**When nothing qualifies:**

This is a client deliverable, so the section carries wins or it does not appear. With live work eligible an empty quarter is rare, but it happens: closures that recovered on their own, work deferred behind a fitout, an alert closed by stopping a rule, open tickets nobody has touched.

- One qualifying win is a section. Show it, with no line apologising for the count
- None means deleting the whole `key-wins` section from the built file. A heading with an explanation under it instead of wins is worse than no heading
- Never write the selection out loud on the page: how many closures you read, which you rejected, or why. Printed, it reads as an audit of the maintenance contractor rather than a review of the building
- Never pad, and never write work as more finished than it is. "The sensor is locked and a replacement is on order" is a win in flight; "the sensor was replaced" is a repair. Dressing the first as the second is the one thing that costs the reader's trust
- Report it in chat instead, to whoever ran the skill: what you read, what you rejected, why. A quarter with no described repairs is a customer-success signal worth someone knowing about
- Where dropping the section would leave nothing but the masthead and the analytics overview, say so before handing the file over rather than shipping two sections as a review

## Data

| Step | Call |
| --- | --- |
| Fixed | In the main batch: `tickets.tickets` `status_id:6`, `has_comments:true`, resolved inside the quarter, with `summary`, `equipment_ids` and `comments` (`limit:8`, `user_only:true`) inline |
| In flight | The leaderboard's Open now pull, which carries the same fields |
| Impact, link, title | Once `wins.json` exists: one `search_action_tickets` on the wins' tickets, reading `impacts`, `ticket_link` and `title` |
| Photos | In the same batch: one `tickets.tickets` on the wins' tickets selecting `attachments.attachment_id`, `file_name`, `mime_type`, `preview.link.url` and `link.url` |
| Level | In the same batch: one `platform.equipment` on the wins' `equipment_ids`, selecting `zone.level.level_name` and `zone.level.system` |

Key wins runs its own closed pull rather than riding the leaderboard's, because the two want opposite shapes: the leaderboard wants every row and few fields, this wants few rows and every field. `has_comments:true` drops each closure nobody wrote on, and holding to the quarter cuts it again, leaving a set small enough to carry its comments inline.

The digest screens out what needs no reading: a closure created and resolved the same moment, nobody worked it; three or more sharing a resolved second, a bulk cleanup; a ticket whose only commenter is an agent. Two more patterns are left to you, since only the comments show them: closures summarised as still in fault, and alerts closed by stopping or tuning a rule.

`impacts` comes back as a list, sometimes `[]`: a ticket with an empty list has no impact set, which is the `Other` case in **Display**, and `report.py fill` names each such ticket for you to say in chat. A level with `system:true` is PEAK's placeholder, `__SYSTEM__`, not a place, so that equipment gets no line.

`key_wins.py photos` keeps the image attachments, one copy per file name and sixteen per win, downloads the originals in parallel and tiles them into `report/kw/sheet-w<n>.jpg`, each tile labelled with its pick and the original's size. The links are signed and lapse twenty minutes after the call: if the photos step reports them lapsed, make the photo call again and re-run it. Where they cannot be fetched from where you are running, the wins go out without photos; say so in chat. `fill_report.py` turns each photo upright, crops it to its tile around `focus` (fractions across and down the frame) and `zoom` (that many times tighter), shrinks and re-encodes it, which also drops the original's EXIF block, GPS position included. A photo reaches the report only through the script.
