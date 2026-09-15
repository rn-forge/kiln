# releases/ — what belongs here

## Belongs here

- One page per release, `release-<n>/index.md`: its `**Status:**` (`planned`,
  `in progress` or `shipped`, with the date), entry criteria, scope, and exit
  criteria.
- Scope named by story ID, linking to the feature file that holds the story.

## Does not belong here

| Instead of | Put it in |
| -- | -- |
| A story's text, acceptance or design | its feature under `specs/` |
| A story's status | the story itself |
| Why a choice was made | an ADR under `adr/` |

## Naming and shape

- `release-<n>/index.md`; the area `index.md` is the list, newest first.
- A story belongs to exactly one release at a time, and that assignment lives
  only on the release page.

## Changing this area

1. Cut a release page when there is scope to put on it, not ahead of time.
1. Give it its status, entry criteria, the scope as story IDs linking to their
   feature files, and exit criteria. Nothing else: the detail lives with the
   story.
1. List it in `index.md`, newest first.

Moving a story between releases edits the two release pages and nothing else.
When a release ships, set `shipped` with the date once its exit criteria hold.
