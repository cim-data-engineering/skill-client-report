# Key wins

Owns the key wins section. No operational impact row. Scaffold part: `key-wins`.

This is the section the facility manager reads first and the one they forward to the owner. Every other section says how the building performed; this one says what was found, who picked it up and where it got to. It is the evidence the building is in good hands: problems caught early and acted on, rather than counted. It is what the owner is paying for.

## Key wins

Statement: "What we found and acted on this quarter". Where every win is a finished repair, "What changed in the building this quarter" is better.
Date: the quarter

**Voice:**

[Writing the narrative](../SKILL.md#writing-the-narrative) governs every sentence in the report. It matters most here, and wins add two rules of their own:

- Write as the engineer on the job: what was wrong, what has been done and by whom, where it stands. Then stop
- Say what was done, not what it demonstrates. "Replaced the belts and had it running the next morning" beats "restored reliability to the unit"

**Selection:**

The test is whether the facility manager would forward it to the owner as evidence the building is in good hands. Two kinds pass:

- **Fixed.** A physical or control change described by whoever made it, so a closure verified rather than asserted
- **Caught and being worked.** A fault the monitoring found that someone is visibly on: raised, assigned, diagnosed, contractor booked or parts on order. Finding a problem before the building finds it the hard way is worth as much to the owner as closing one, so it belongs on the page

Either way it needs a comment history showing a person engaged with it. Exclude alerts resolved by stopping, tuning or ignoring a rule, platform, integration or data mapping work, and actions marked as not doing.

**Display:**

- Heading names the outcome, or the finding where the work is still live, plus the equipment type and name
- Tag the win with its impact, above the heading: one of `energy`, `comfort`, `reliability`, `water`, `safety`, `other`, carried in the bundle as the win's `impact` key. It renders as a small uppercase word with a coloured dot, and the word is what states the impact — the dot only speeds up scanning down the page
- The impact is the one its linked action tickets carry, never one you read off the story. A win about a chiller that plainly saves energy is tagged `reliability` if that is what the tickets say. The engineer who worked the ticket set that field, and the report has no standing to overrule it
- Where a win links several tickets whose impacts differ, take the most severe: `safety`, then `reliability`, `comfort`, `energy`, `water`, `other`. Never merge two into a compound tag, and never show two tags on one win
- Where the tickets carry no impact at all, or carry `other`, tag it `Other` rather than picking the one that would look best. Then say so in chat — name the ticket and its title — so the user can set the impact in PEAK and re-run. Fixing the ticket fixes every report that reads it; guessing here fixes nothing and puts a claim on the page the ticket does not support
- Say where it stands. A win in flight is written as in flight: what was found, who has it, what happens next. The date line under the section heading follows the wins too, so do not leave a line promising everything was fixed when some of it is still open
- Two to three sentences: what was wrong, what was changed, why it matters
- Lead with the building outcome: comfort, reliability, energy, tenant experience
- Rank by what the owner cares about. Critical plant over terminal units, permanent fixes over one-off resets
- Link the action ticket with its PEAK url as evidence, using the action title as the link name, not the id
- Where several tickets form one win, link them all
- Where a win also appears in the equipment health snapshot, say so in the `snap` line. The scaffold keeps that line only when equipment health is in the report, so if it is not there the cross-reference is not yours to add

**When nothing qualifies:**

This is a client deliverable, so the section carries wins or it does not appear. With live work eligible an empty quarter is rare, but it happens: closures that recovered on their own, work deferred behind a fitout, an alert closed by stopping a rule, open tickets nobody has touched.

- One qualifying win is a section. Show it, with no line apologising for the count
- None means deleting the whole `key-wins` section from the built file. A heading with an explanation under it instead of wins is worse than no heading
- Never write the selection out loud on the page: how many closures you read, which you rejected, or why. Printed, it reads as an audit of the maintenance contractor rather than a review of the building
- Never pad, and never write work as more finished than it is. "The sensor is locked and a replacement is on order" is a win in flight; "the sensor was replaced" is a repair. Dressing the first as the second is the one thing that costs the reader's trust
- Report it in chat instead, to whoever ran the skill: what you read, what you rejected, why. A quarter with no described repairs is a customer-success signal worth someone knowing about
- Where dropping the section would leave nothing but the masthead and the analytics overview, say so before handing the file over rather than shipping two sections as a review

## Data recipes

| Step      | Call                                                                                              |
| --------- | --------------------------------------------------------------------------------------------------- |
| Fixed     | Its own pull: `status_id:6`, `has_comments:true`, resolved inside the quarter, carrying `summary`, `comment_count` and `comments` inline |
| In flight | Its Open now call, `status_ids:[1,3,7]`                                                           |
| Evidence  | Its Shortlist comments call, `ticket_ids:[the ten to fifteen you chose]`                          |
| Impact    | One `search_action_tickets` on the same `ticket_ids`, reading `impacts` and, where a summary lacks one, `equipment_names` |

Key wins runs its own pull rather than riding the leaderboard's, because the two want opposite shapes: the leaderboard wants every row and few fields, this wants few rows and every field. `has_comments:true` drops each closure nobody wrote on, which is most of them, and holding to the quarter cuts it again, leaving a set small enough to carry `comments` inline so the candidates and their evidence arrive together.

The in-flight candidates need no pull of their own: the Open now call already carries `summary` and `comment_count`. Choose from those rows, then fetch the histories with one call passing the whole `ticket_ids` list and selecting `comments` with `limit:8` and `user_only:true`. Never call `search_action_comments` in a loop, one ticket at a time.

Equipment names are usually already in the summary, which reads "L15-VAV-C2 - Inspect VAV Airflow Leak". Only where one does not, resolve the shortlist with a single `search_action_tickets` call on their `ticket_ids`, which returns `equipment_names` per ticket.

Impacts ride on that same call: `search_action_tickets` returns an `impacts` array on every row, so no extra pull is needed. Run it over the whole shortlist rather than only the tickets missing a name, since every win needs its impact and one call covers both. It comes back as a list — `["reliability"]`, sometimes `[]` — so a ticket with an empty array is a ticket with no impact set, which is the `Other` case above and worth naming in chat. The GraphQL pulls are no help here: `tickets.tickets` carries `impact_ids` as raw UUIDs with no names attached.

Five patterns are visible in the candidate rows themselves and need no comment read, so skip them:

- `created_at` and `resolved_at` the same moment: nobody worked it
- `comment_count: 0`: nothing to read, so it can never qualify. Filter it out with `has_comments:true` rather than dropping it by hand
- A run of actions sharing a resolved timestamp to the second: a bulk cleanup, not a quarter of repairs
- An action whose comments were already summarised as still in fault at closure: closed for tidiness while the fault stands
- An open action with no comments: raised but not yet picked up, so there is nothing to show yet
