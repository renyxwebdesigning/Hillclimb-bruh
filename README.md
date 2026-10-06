# Hill Rider

A 2D hill-climb driving game written in Python with pygame. Drive as far as you can over procedurally generated hills, bridges and tunnels, collect coins, pull off flips, upgrade your vehicle, and race your friends online.

## Install and run

You need Python 3.10 or newer.

```
pip install pygame numpy
python3 main.py
```

`espeak` (or `espeak-ng`) is optional. With it installed, the drivers say their lines out loud.

## Controls

| Key | Action |
|---|---|
| Right / D / Up | Gas (in the air: tilt back) |
| Left / A / Down | Brake / reverse (in the air: tilt forward) |
| Space | Boost |
| H | Horn (switch between Puppy and Ship in the garage) |
| L | Lights on/off |
| Enter | Hammer a seized engine back to life ("Kolbenklemmer") |
| Esc / P | Pause |
| M | Music on/off |
| F11 | Fullscreen |

The on-screen pedals, boost and horn buttons also work with the mouse.

## Features

- 4 stages: Countryside, Desert, Arctic (slippery) and Moon (low gravity). The first three have a day/night cycle.
- 6 vehicles: Jeep, Dirt Bike, Chopper, Monster Truck, Supercar and Rocket, each with its own upgrades (engine, suspension, tires, boost).
- 11 drivers to choose from.
- Bridges over gorges, tunnels through hills, coins, air-time and flip bonuses.
- Random engine seizures: black smoke, a swearing driver, and 5-30 hits of Enter to fix.
- All graphics, music and sound effects are generated in code.

## Playing online

1. The host clicks **PLAY ONLINE**, then **HOST GAME**. The lobby shows the address to share.
2. Friends click **PLAY ONLINE**, enter that address, then **JOIN GAME**.
3. The host picks the map and mode (Free Ride, or a 500 / 1000 / 2000 m race) and presses **START**.

On the same network, use the host's local address (for example `192.168.x.x`). Over the internet, the host must forward **TCP port 47777** on their router, or both players can use a VPN such as Tailscale or ZeroTier and use that address instead.

Progress is saved in `~/.hill_rider/save.json`.
