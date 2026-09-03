# Key wins

Owns the key wins section. No operational impact row. Scaffold part: `key-wins`.

This is the section the facility manager reads first and the one they forward to the owner. Every other section says how the building performed; this one says what was actually fixed, by whom, and what changed as a result. It is where the quarter's monitoring shows up as work on the floor, and it is what the owner is paying for.

## Key wins

What changed in the building this quarter
Date: the quarter

**Voice:**

[Writing the narrative](../SKILL.md#writing-the-narrative) governs every sentence in the report. It matters most here, and wins add two rules of their own:

- Write as the engineer who did the work: what was wrong, what was done and by whom, what it means for the building. Then stop
- Say what was done, not what it demonstrates. "Replaced the belts and had it running the next morning" beats "restored reliability to the unit"

**Selection:**
A win needs a physical or control change described by whoever made it, in the comment history — a closure verified, not asserted. Exclude alerts resolved by stopping, tuning or ignoring a rule, platform, integration or data mapping work, and actions marked as not doing.

**Display:**

- Heading names the outcome and the equipment type and name
- Two to three sentences: what was wrong, what was changed, why it matters
- Lead with the building outcome: comfort, reliability, energy, tenant experience
- Rank by what the owner cares about. Critical plant over terminal units, permanent fixes over one-off resets
- Link the action ticket with its PEAK url as evidence, using the action title as the link name, not the id
- Where several tickets form one win, link them all
- Where a win also appears in the equipment health snapshot, say so in the `snap` line — the scaffold keeps that line only when equipment health is in the report, so if it is not there, the cross-reference is not yours to add

**When nothing qualifies:**

This is a client deliverable, so the section carries wins or it does not appear. Some quarters have one; some have none — closures that recovered on their own, work deferred behind a fitout, an alert closed by stopping a rule.

- One qualifying win is a section. Show it, with no line apologising for the count
- None means deleting the whole `key-wins` section from the built file. A heading with an explanation under it instead of wins is worse than no heading
- Never write the selection out loud on the page — how many closures you read, which you rejected, or why. Printed, it reads as an audit of the maintenance contractor rather than a review of the building
- Never pad, and never promote a diagnosis to a repair. "The sensor was found to be locked" is not a win; "the sensor was replaced" is
- Report it in chat instead, to whoever ran the skill: what you read, what you rejected, why. A quarter with no described repairs is a customer-success signal worth someone knowing about
- Where dropping the section would leave nothing but the masthead and the analytics overview, say so before handing the file over rather than shipping two sections as a review

## Data recipes

| Step      | Call                                                                                                  |
| --------- | ----------------------------------------------------------------------------------------------------- |
| Shortlist | `search_action_tickets(status:"closed", resolved_after_local, resolved_before_local)` over the quarter  |
| Evidence  | `search_action_comments`, on the shortlist only — ten to fifteen candidates                             |

The shared pull in SKILL.md carries ids, dates and assignees but not titles or equipment names, and the shortlist is chosen by reading those, so the shortlist call runs whether or not Alerts resolved is also in. Comments are where the physical work is described, and reading them for every closure in the quarter costs many times more than reading them for the few that could lead the page.

Three patterns are visible in the shortlist itself and need no comment read — skip them:

- `age_days: 0` with no `last_comment_author`: created and resolved in the same moment, so nobody worked it
- A run of actions sharing a resolved timestamp to the second: a bulk cleanup, not a quarter of repairs
- An action whose comments were already summarised as still in fault at closure: closed for tidiness while the fault stands
