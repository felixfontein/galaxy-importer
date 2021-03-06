import glob
import logging
import re
import subprocess
import sys

import requests


LOG = logging.getLogger()


NO_ISSUE = "No-Issue"
ISSUE_LABELS = [
    "Closes-Bug",
    "Closes-Issue",
    "Partial-Bug",
    "Partial-Issue",
    "Implements",
    "Partial-Implements",
    "Issue",
    "Partial-Issue",
    # ChangeLog record not required
    "Related",
    "Related-Bug",
    "Related-Issue",
]
CHANGELOG_REQUIRED_LABELS = set(ISSUE_LABELS) - {
    "Related",
    "Related-Bug",
    "Related-Issue",
}

NO_ISSUE_REGEX = re.compile(r"^\s*{}\s*$".format(NO_ISSUE), re.MULTILINE)
ISSUE_LABEL_REGEX = re.compile(
    r"^\s*({}):\s+AAH-(\d+)\s*$".format("|".join(ISSUE_LABELS)), re.MULTILINE,
)

JIRA_URL = "https://issues.redhat.com/rest/api/latest/issue/AAH-{issue}"

COMMIT_SHA = sys.argv[1]


def git_commit_message(commit_sha):
    cmd = ["git", "show", "-s", "--format=%B", commit_sha]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, encoding="utf-8", check=True)
    return result.stdout


def check_changelog_record(issue):
    reconrds_count = len(glob.glob(f"CHANGES/{issue}.*"))
    if reconrds_count == 0:
        LOG.error(f"Missing change log entry for issue AAH-{issue}.")
        return False
    if reconrds_count == 1:
        return True
    LOG.error(f"Multiple change log records found for issue AAH-{issue}.")
    return False


def check_issue_exists(issue):
    response = requests.head(JIRA_URL.format(issue=issue))
    if response.status_code == 404:
        # 200 is returned for logged in sessions
        # 401 is for not authorized access on existing issue
        # 404 is returned if issue is not found even for unlogged users.
        LOG.error(f"Referenced issue AAH-{issue} not found in Jira.")
        return False
    return True


def check_commit(commit_sha):
    commit_message = git_commit_message(commit_sha)
    issue_labels = ISSUE_LABEL_REGEX.findall(commit_message)
    if not issue_labels:
        no_issue_match = NO_ISSUE_REGEX.search(commit_message)
        if not no_issue_match:
            LOG.error(f"Commit {commit_sha[:8]} has no issue attached")
            return False

    ok = True
    for label, issue in issue_labels:
        if not check_issue_exists(issue):
            ok = False
        if label in CHANGELOG_REQUIRED_LABELS and not check_changelog_record(issue):
            ok = False
    return ok


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    LOG.debug(f"Checking commit {COMMIT_SHA[:8]} ...")
    if not check_commit(COMMIT_SHA):
        sys.exit(1)

    # TODO: Validate pull request message.


if __name__ == "__main__":
    main()
