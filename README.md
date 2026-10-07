# Hill Rider

A 2D hill-climb driving game. Drive as far as you can over hills, bridges and tunnels, collect coins, pull off flips, upgrade your vehicles and race your friends online.

## Play in the browser (phones too)

**https://renyxwebdesigning.github.io/Hillclimb-bruh/**

Works on any computer or phone (hold the phone sideways). Online play needs the download version.

## Download and play (no installing)

| Computer | Download |
|---|---|
| Windows | [HillRider-Windows.zip](https://github.com/renyxwebdesigning/Hillclimb-bruh/releases/latest/download/HillRider-Windows.zip) |
| Linux | [HillRider-Linux.zip](https://github.com/renyxwebdesigning/Hillclimb-bruh/releases/latest/download/HillRider-Linux.zip) |
| macOS | [HillRider-macOS.zip](https://github.com/renyxwebdesigning/Hillclimb-bruh/releases/latest/download/HillRider-macOS.zip) |

1. Download the ZIP for your computer.
2. Unzip it (on Windows: right-click → **Extract All…**).
3. Open the `HillRider` folder and double-click **HillRider** (`HillRider.exe` on Windows).

Windows may show "Windows protected your PC" because the game isn't signed. Click **More info**, then **Run anyway**.

## Playing with friends

Every player gets a permanent **player number** (for example `#482913`), shown at the top right of the menus. The game goes online by itself; there are no IP addresses or router settings.

1. Click **PLAY ONLINE**.
2. Tell your friends your number, or add theirs with **ADD FRIEND**. Friends who are online get a green dot.
3. One player clicks **HOST GAME**. In the lobby, click **INVITE** next to a friend, or invite any player by number.
4. The invited player gets a popup and clicks **JOIN**. (Friends can also type the host's number under **JOIN**.)
5. The host picks the map and mode (Free Ride, or a 500 / 1000 / 2000 m race) and presses **START**.

Online play goes through a free public relay server (HiveMQ, with fallbacks), so it needs an internet connection. Only car positions, names and player numbers are sent.

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

- 8 maps: Countryside, Desert, Arctic, Moon, City, Volcano (jump the lava pits!), Jungle and Mars. Most have a day/night cycle with headlights and street lamps.
- 9 vehicles: Jeep, Dirt Bike, Chopper, Monster Truck, Supercar, Rocket, Tank, Police Car (siren!) and Hoverboard, each with its own upgrades (engine, suspension, tires, boost).
- 13 drivers to choose from, each with their own voice.
- Bridges, tunnels, coins, air-time and flip bonuses, 40 secret trophies and 16 achievements (Trophy Room).
- Daily challenge, ghost of your best run, world leaderboard, online races and 4-race tournaments.
- Random engine seizures: black smoke, a swearing driver, and 5-30 hits of Enter to fix.
- 5 music tracks to choose from, volume settings, graphics quality.

## Running from the source code

You need Python 3.10 or newer.

```
pip install pygame numpy
python main.py
```

On Python 3.14 use `pip install pygame-ce numpy` instead.

Progress and your player number are saved in `~/.hill_rider/save.json`.

## Credits

Fonts: DejaVu Sans (Bitstream Vera license) and Lato (SIL Open Font License), see `assets/fonts/`.
