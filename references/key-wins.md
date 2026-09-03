# Key wins

Owns the key wins section. No operational impact row. Scaffold part: `key-wins`.

This is the section the facility manager reads first and the one they forward to the owner. Every other section says how the building performed; this one says what was found, who picked it up and where it got to. It is the evidence the building is in good hands — problems caught early and acted on, not just problems counted — and it is what the owner is paying for.

## Key wins

Statement: "What we found and acted on this quarter". Where every win is a finished repair, "What changed in the building this quarter" is better.
Date: the quarter

**Voice:**

[Writing the narrative](../SKILL.md#writing-the-narrative) governs every sentence in the report. It matters most here, and wins add two rules of their own:

- Write as the engineer on the job: what was wrong, what has been done and by whom, where it stands. Then stop
- Say what was done, not what it demonstrates. "Replaced the belts and had it running the next morning" beats "restored reliability to the unit"

**Selection:**

The test is whether the facility manager would forward it to the owner as evidence the building is in good hands. Two kinds pass:

- **Fixed.** A physical or control change described by whoever made it — a closure verified, not asserted
- **Caught and being worked.** A fault the monitoring found that someone is visibly on: raised, assigned, diagnosed, contractor booked or parts on order. Finding a problem before the building finds it the hard way is worth as much to the owner as closing one, so it belongs on the page

Either way it needs a comment history showing a person engaged with it. Exclude alerts resolved by stopping, tuning or ignoring a rule, platform, integration or data mapping work, and actions marked as not doing.

**Display:**

- Heading names the outcome, or the finding where the work is still live, plus the equipment type and name
- Say where it stands. A win in flight is written as in flight — what was found, who has it, what happens next. The date line under the section heading follows the wins too, so do not leave a line promising everything was fixed when some of it is still open
- Two to three sentences: what was wrong, what was changed, why it matters
- Lead with the building outcome: comfort, reliability, energy, tenant experience
- Rank by what the owner cares about. Critical plant over terminal units, permanent fixes over one-off resets
- Link the action ticket with its PEAK url as evidence, using the action title as the link name, not the id
- Where several tickets form one win, link them all
- Where a win also appears in the equipment health snapshot, say so in the `snap` line — the scaffold keeps that line only when equipment health is in the report, so if it is not there, the cross-reference is not yours to add

**When nothing qualifies:**

This is a client deliverable, so the section carries wins or it does not appear. With live work eligible an empty quarter is rare, but it happens — closures that recovered on their own, work deferred behind a fitout, an alert closed by stopping a rule, open tickets nobody has touched.

- One qualifying win is a section. Show it, with no line apologising for the count
- None means deleting the whole `key-wins` section from the built file. A heading with an explanation under it instead of wins is worse than no heading
- Never write the selection out loud on the page — how many closures you read, which you rejected, or why. Printed, it reads as an audit of the maintenance contractor rather than a review of the building
- Never pad, and never write work as more finished than it is. "The sensor is locked and a replacement is on order" is a win in flight; "the sensor was replaced" is a repair. Dressing the first as the second is the one thing that costs the reader's trust
- Report it in chat instead, to whoever ran the skill: what you read, what you rejected, why. A quarter with no described repairs is a customer-success signal worth someone knowing about
- Where dropping the section would leave nothing but the masthead and the analytics overview, say so before handing the file over rather than shipping two sections as a review

## Data recipes

| Step      | Call                                                                                                    |
| --------- | ------------------------------------------------------------------------------------------------------- |
| Fixed     | `search_action_tickets(status:"closed", resolved_after_local, resolved_before_local)` over the quarter    |
| In flight | `search_action_tickets` once per open status (`open`, `in_progress`, `on_hold`), `created_after_local` over the quarter |
| Evidence  | `search_action_comments`, on the shortlist only — ten to fifteen candidates                               |

The shared pull in SKILL.md carries ids, dates and assignees but not titles or equipment names, and the shortlist is chosen by reading those, so the shortlist call runs whether or not Alerts resolved is also in. Comments are where the work is described, and reading them for every action in the quarter costs many times more than reading them for the few that could lead the page.

Four patterns are visible in the shortlist itself and need no comment read — skip them:

- `age_days: 0` with no `last_comment_author`: created and resolved in the same moment, so nobody worked it
- A run of actions sharing a resolved timestamp to the second: a bulk cleanup, not a quarter of repairs
- An action whose comments were already summarised as still in fault at closure: closed for tidiness while the fault stands
- An open action with no `last_comment_author`: raised but not yet picked up, so there is nothing to show yet
