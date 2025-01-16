import subprocess
import os
import re
def get_latest_tag() -> str:
    """
    Get the latest semantic version tag.
    :return: The latest tag in the repository.
    """
    try:
        result = subprocess.run(
            ["git", "tag", "--sort=-v:refname"],
            capture_output=True,
            text=True,
            check=True
        )
        tags = result.stdout.splitlines()
        if not tags:
            raise ValueError("No tags found in the repository.")
        return tags[0]  # The latest tag
    except subprocess.CalledProcessError as e:
        print(f"Error fetching tags: {e.stderr}")
        raise

def validate_semantic_version(tag: str) -> bool:
    """
    Validate if a tag follows semantic versioning.
    :param tag: Tag to validate (e.g., v1.0.0).
    :return: True if valid, False otherwise.
    """
    pattern = r"^v\d+\.\d+\.\d+$"
    return re.match(pattern, tag) is not None

def get_commits_from_pr(base_branch: str, pr_branch: str):
    """
    Get the commit messages and IDs from a PR branch compared to the base branch.
    :param base_branch: The base branch (e.g., develop or main).
    :param pr_branch: The PR branch (e.g., feature/some-new-feature).
    :return: A list of tuples (commit_hash, commit_message).
    """
    try:
        result = subprocess.run(
            ["git", "log", f"{base_branch}..{pr_branch}", "--pretty=format:%h %s"],
            capture_output=True,
            text=True,
            check=True
        )
        commits = result.stdout.splitlines()
        return [(commit.split(" ", 1)[0], commit.split(" ", 1)[1]) for commit in commits]
    except subprocess.CalledProcessError as e:
        print(f"Error fetching commits: {e.stderr}")
        return []

def determine_version_increment(commits):
    """
    Determine the type of version increment based on commit messages.
    :param commits: A list of commit messages.
    :return: The type of version increment ('major', 'minor', 'patch').
    """
    for _, message in commits:
        if "BREAKING CHANGE" in message:
            return "major"
        if "feat" in message or "feature" in message:
            return "minor"
        if "fix" in message:
            return "patch"
    return "patch"

def update_changelog(commits, from_tag, to_tag, output_file="changelog.md"):
    """
    Update the changelog with the commits between tags.
    :param commits: A list of tuples (commit_hash, commit_message).
    :param from_tag: The starting tag.
    :param to_tag: The ending tag.
    :param output_file: The changelog file to update.
    """
    github_repo = os.getenv("GITHUB_REPOSITORY", "unknown/repo")
    base_url = f"https://github.com/{github_repo}/commit"

    with open(output_file, "a") as f:
        f.write(f"\n## Changes from {from_tag} to {to_tag}\n\n")
        for commit_hash, message in commits:
            commit_url = f"{base_url}/{commit_hash}"
            f.write(f"- [{commit_hash}]({commit_url}): {message}\n")

def increment_version(version: str, version_type: str) -> str:
    """
    Increment the version based on the version type.
    :param version: The current version string (e.g., v1.0.0).
    :param version_type: The type of version increment ('major', 'minor', 'patch').
    :return: The new version string.
    """
    major, minor, patch = map(int, version.lstrip("v").split("."))
    
    if version_type == "major":
        major += 1
        minor = 0
        patch = 0
    elif version_type == "minor":
        minor += 1
        patch = 0
    elif version_type == "patch":
        patch += 1
    
    return f"v{major}.{minor}.{patch}"

def generate_pr_based_changelog(base_branch: str, pr_branch: str):
    """
    Generate changelog and manage versioning based on a PR.
    :param base_branch: The base branch (e.g., develop or main).
    :param pr_branch: The PR branch (e.g., feature/some-new-feature).
    """
    try:
        # Fetch PR commits
        commits = get_commits_from_pr(base_branch, pr_branch)
        if not commits:
            print(f"No commits found between {base_branch} and {pr_branch}.")
            return

        # Get the current and new version tags
        from_tag = get_latest_tag()
        print(f"Latest tag: {from_tag}")
        if not validate_semantic_version(from_tag):
            raise ValueError(f"Latest tag {from_tag} is not valid.")

        increment_type = determine_version_increment(commits)
        new_tag = increment_version(from_tag, increment_type)
        print(f"New tag: {new_tag}")

        # Tag the new version and push
        subprocess.run(["git", "tag", new_tag], check=True)
        subprocess.run(["git", "push", "origin", new_tag], check=True)

        # Update the changelog
        update_changelog(commits, from_tag, new_tag)
        subprocess.run(["git", "add", "changelog.md"], check=True)
        subprocess.run(["git", "commit", "-m", f"Update changelog for {new_tag}"], check=True)
        subprocess.run(["git", "push", "origin", base_branch], check=True)

        print(f"Changelog updated and tag {new_tag} pushed.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    # Example usage: base branch is develop, PR branch is feature/new-feature
    generate_pr_based_changelog("develop", "feature/new-feature")
