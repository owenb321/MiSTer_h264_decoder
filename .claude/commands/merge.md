Merge the current feature branch into main via its PR, then clean up.

A merge request is authorisation to publish THIS branch. If the branch has never been
pushed, or has no open PR, create those first (steps 4-5) rather than stopping — but do
not take it as permission to push anything else.

**Host detection.** Read `git remote get-url origin` first and use the matching CLI for
every remote operation below:
- contains `github.com` → **`gh`**
- anything else (the Forgejo bring-up repository) → **`tea`**, passing
  `--repo owenb321/MiSTer_h264_decoder`

Steps:
1. Check the current branch. If it's already `main`, tell the user and stop.
2. Confirm the working tree is clean. If there are uncommitted changes, tell the user and
   stop — do not commit on their behalf.
3. **Sweep the user docs before publishing anything.** The manual is built as a check on
   every merge and deployed only on a release, but a stale page merged to `main` is what
   the next release ships. Invoke the `docs-sweep` skill for `main...HEAD`, or at minimum:

   ```bash
   .venv/bin/python3 tools/docs_check.py
   .venv/bin/mkdocs build --strict
   grep -on "](#[a-z0-9-]*)" README.md
   ```

   If the branch changed anything user-visible and the manual does not reflect it, fix
   that first and commit it to the branch. If it needs a judgement call, report and stop.
4. **If the branch has no upstream** (`git rev-parse --abbrev-ref @{u}` fails), push it:
   `git push -u origin <branch>`. Say that you are publishing it.
5. **Find the open PR** for this branch and match the head ref:
   - gh: `gh pr list --head <branch> --state open`
   - tea: `tea pr list --repo owenb321/MiSTer_h264_decoder --state open`

   If none exists, create one — write the body to a temp file, never inline:
   - gh: `gh pr create --base main --head <branch> --title "<title>" --body-file /tmp/pr_body.md`
   - tea: `tea pr create --repo owenb321/MiSTer_h264_decoder --base main --head <branch> --title "<title>" --description "$(cat /tmp/pr_body.md)"`

   Derive the title from the branch's commits. Include a short summary and a markdown
   test-plan checklist reflecting what was actually verified.
6. **Merge it:**
   - gh: `gh pr merge <number> --merge`
   - tea: `tea pr merge --repo owenb321/MiSTer_h264_decoder <index>` — pass ONLY the index
     (`--merge` is not a valid flag there; `--style` already defaults to a merge commit).

   If the merge fails right after another merge, re-check the PR state before retrying.
7. `git checkout main`
8. `git pull`
9. `git fetch --prune`
10. `git branch -d <branch-name>` (`-D` only if `-d` refuses over the host's merge commit).

Report the PR URL, the branch deleted, and confirm main is up to date. If steps 3 or 4
had to publish or create anything, say so explicitly.
