# Scheduled jobs

`chumber-weekly-reward.timer` runs the Baghdad Tuesday draw. It mirrors the
existing `chumber-backup.timer` pattern already on the server.

Not installed by this change — install on the production host with:

```bash
sudo cp deploy/chumber-weekly-reward.{service,timer} /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now chumber-weekly-reward.timer
systemctl list-timers chumber-weekly-reward.timer   # verify
```

`Persistent=true` means a Tuesday missed because the box was down is drawn as
soon as it comes back up. Re-running is harmless: `UNIQUE(reward_date, region)`
makes a second award for the same Tuesday impossible.
