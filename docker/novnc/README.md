# koru noVNC desktop lab

Browser-accessible **X11 + XFCE** environment for light koru GUI/smoke work.

```bash
# from repository root
docker compose -f docker/novnc/docker-compose.yml up --build -d
# open: http://127.0.0.1:6080/vnc.html?autoconnect=true
docker exec -it koru-novnc bash /home/koru/smoke-desktop.sh
docker compose -f docker/novnc/docker-compose.yml down
```

## What this is / is not

| Yes | No |
| --- | -- |
| noVNC web UI (port 6080) | Full Wayland session |
| Editable koru from bind-mount `/opt/koru` | Real JetBrains / Cursor install |
| xdotool, scrot, basic desktop | Production photo-VQL proof |
| Smoke script for DISPLAY + `koru --version` | Replacement for host `docs/photo-vql-jetbrains-wayland.md` |

## Related

- Full e2e map: [`docs/docker-e2e-testing.md`](../../docs/docker-e2e-testing.md)
- Goal tags vs Releases: [`docs/goal-tags-and-releases.md`](../../docs/goal-tags-and-releases.md)
