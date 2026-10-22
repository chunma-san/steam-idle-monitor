# Activity Garden

A small, deliberately decorative daily activity log. This component records an automated date and counter; it does not represent daily manual coding work.

## Behavior

- A Linux server updates `activity.json` once per calendar day.
- Repeated runs on the same day create no duplicate commits.
- The scheduler runs around 22:00 Europe/Paris, including daylight saving changes.
- An interrupted push is retried on a later run. No history is backdated or force-pushed.
- Public output contains only the date, number of recorded days and a fixed automation label.

## Requirements

Python 3.9+, Git, OpenSSH, timezone data and systemd. Use a repository-specific SSH deploy key with write access. Set the author email to your GitHub-provided noreply address so commits can be attributed to your account. Push to the repository's default `main` branch.

## Installation

Create a dedicated `activity-garden` system account with home `/var/lib/activity-garden`. Install `update.py` under `/opt/activity-garden`, and copy the supplied service and timer into `/etc/systemd/system`.

Create a private `/etc/activity-garden.env` from `.env.example`. Add `GIT_SSH_COMMAND` using the dedicated key, `IdentitiesOnly=yes`, `StrictHostKeyChecking=yes`, and a known-hosts file populated from GitHub's official published SSH host keys. Keep the private key readable only by the service account.

```sh
python3 -m unittest -v
sudo systemd-analyze verify activity-garden.service activity-garden.timer
sudo systemctl daemon-reload
sudo systemctl start activity-garden.service
sudo systemctl enable --now activity-garden.timer
sudo systemctl list-timers activity-garden.timer
```

The initial run clones the configured repository and pushes today's first record. Network or authentication failures leave the service in a failed state for inspection with `journalctl -u activity-garden.service`. Fix the cause and restart the service; no force push is needed.

## GitHub contribution rules

Commits must use an email associated with your account and reach the default branch of a standalone repository. GitHub may take up to 24 hours to update the graph. See [GitHub's contribution reference](https://docs.github.com/en/account-and-profile/reference/profile-contributions-reference).

Keep configuration and private keys outside this repository. This project has no dependency on the other applications running on your host.
