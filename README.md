# Hill Rider

A 2D hill-climb driving game. Drive as far as you can over hills, bridges and tunnels, collect coins, pull off flips, upgrade your vehicles and race your friends online.

## Play in the browser (phones too)

**https://renyxwebdesigning.github.io/Hillclimb-bruh/**

Works on any computer or phone (hold the phone sideways), including online races: browser and download players can play together.

**Install it like an app** (icon on the home screen, fullscreen, starts without internet after the first time):
- iPhone / iPad: open the link in **Safari**, tap **Share** → **Add to Home Screen**.
- Android: open the link in **Chrome**, tap **⋮** → **Install app** (or **Add to Home screen**).

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

Online play goes through a free public relay server (HiveMQ, with fallbacks), so it needs an internet connection. The download version connects directly, the browser version over a WebSocket; both meet on the same server. Only car positions, names and player numbers are sent. On phones the game shows its own keyboard for typing numbers and names.

## Controls

| Key | Action |
|---|---|
| Right / D / Up | Gas (in the air: tilt back) |
| Left / A / Down | Brake / reverse (in the air: tilt forward) |
| Space | Boost |
| H | Horn (switch between Puppy and Ship in the garage) |
| L | Lights on/off |
| Esc / P | Pause |
| M | Music on/off |
| F11 | Fullscreen |

On a phone: GAS bottom right, BRAKE bottom left, BOOST above the brake (hold it together with the gas), horn above the gas. The on-screen buttons also work with the mouse.

The square button at the top right switches to fullscreen (not available on iPhone; add the page to your home screen instead).

## Features

- 9 maps: Countryside, Desert, Arctic, Moon, City, Volcano (jump the lava pits!), Jungle, Mars and Four Seasons (winter, spring, summer and fall change as you drive; winter is slippery). Every map has its own landmarks (windmills, a pyramid, an oil pump, an igloo, a Moon lander, a jungle temple, a Mars base...), birds and weather. Most have a day/night cycle with headlights and street lamps.
- 14 vehicles: Jeep, Dirt Bike, Chopper, Monster Truck, Supercar, Tank, Police Car (siren!), Hoverboard, Tesla, Mini One, B2 Bomber (it flies), Excavator, LKW and a galloping Horse, each with its own upgrades (engine, suspension, tires, boost).
- 11 drivers to choose from; they swear in their own voice when they crash (natural voices recorded with [Piper](https://github.com/rhasspy/piper), see `tools/make_voices.py`).
- Bridges, tunnels, coins, air-time and flip bonuses, 45 secret trophies and 15 achievements (Trophy Room).
- Daily challenge, ghost of your best run, world leaderboard, online races and 4-race tournaments.
- 5 music tracks to choose from, volume settings, graphics quality, English or German (Settings → Language).

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

Driver voices: recorded with [Piper](https://github.com/rhasspy/piper) using these voice models: Thorsten and Thorsten emotional (Thorsten Müller, CC0), Karlsson (M-AILABS speech dataset), Alba (University of Edinburgh, CC BY 4.0), Dmitri (Nabu Casa, CC0), Norman and Kristin (public domain).
