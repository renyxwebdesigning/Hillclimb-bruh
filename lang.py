"""English / German. Every text goes through gfx.text, which calls tr(); German lives in DE below.

Plain strings are looked up as they are (ALL-CAPS strings also match their normal-case entry), and
strings with numbers or names in them go through the PATTERNS (regex -> German template).
"""
import re

LANG = "en"
LANGUAGES = [("en", "ENGLISH"), ("de", "DEUTSCH")]
COLLECT = None              # set() to record every string drawn (used to find missing translations)

DE = {}
PATTERNS = []


def set_lang(code):
    global LANG
    LANG = code if code in dict(LANGUAGES) else "en"


def tr(text):
    if COLLECT is not None:
        COLLECT.add(text)
    if LANG == "en" or not text:
        return text
    hit = DE.get(text)
    if hit is not None:
        return hit
    if text.isupper():
        hit = _UPPER.get(text)
        if hit is not None:
            return hit
    for rx, repl in PATTERNS:
        m = rx.match(text)
        if m:
            return repl(m) if callable(repl) else m.expand(repl)
    return text


_UPPER = {}


def _index():
    _UPPER.clear()
    for en, de in DE.items():
        _UPPER.setdefault(en.upper(), de.upper())


DE.update({
    # home and menus
    "PLAY": "SPIELEN", "PLAY ONLINE": "ONLINE SPIELEN", "GARAGE": "GARAGE", "TROPHIES": "TROPHÄEN",
    "RANKING": "RANGLISTE", "SETTINGS": "EINSTELLUNGEN", "QUIT": "BEENDEN", "HOME": "START", "UPGRADES": "TUNING",
    "START": "LOS", "BACK": "ZURÜCK", "DONE": "FERTIG", "READY TO RACE": "BEREIT ZUM RENNEN", "MAP": "KARTE",
    "VEHICLE": "FAHRZEUG", "DRIVER": "FAHRER", "YOUR RIDE": "DEIN FAHRZEUG",
    "Climb  ·  Flip  ·  Race your friends": "Klettern  ·  Saltos  ·  Gegen Freunde fahren",
    "DAILY CHALLENGE": "TAGES-CHALLENGE", "PLAY CHALLENGE": "CHALLENGE SPIELEN",
    "DONE - COME BACK TOMORROW": "GESCHAFFT - MORGEN WIEDER", "DAILY CHALLENGE DONE!": "TAGES-CHALLENGE GESCHAFFT!",
    "Arrow keys + Enter, or click": "Pfeiltasten + Enter oder klicken", "Tap a button": "Tippe auf einen Knopf",
    "SELECT STAGE": "KARTE WÄHLEN",
    "Pick a map  ·  tap it again (or press Enter) when you're done":
        "Wähle eine Karte  ·  nochmal antippen (oder Enter), wenn du fertig bist",
    # maps
    "Countryside": "Land", "Desert": "Wüste", "Arctic": "Arktis", "Moon": "Mond", "City": "Stadt",
    "Volcano": "Vulkan", "Jungle": "Dschungel", "Mars": "Mars", "Four Seasons": "Vier Jahreszeiten",
    "Rolling hills · day & night": "Sanfte Hügel · Tag & Nacht", "Huge dunes · day & night": "Riesige Dünen · Tag & Nacht",
    "Slippery ice · day & night": "Rutschiges Eis · Tag & Nacht", "Low gravity": "Wenig Schwerkraft",
    "Skyscrapers · night lights": "Wolkenkratzer · Lichter bei Nacht", "Jump the lava pits!": "Spring über die Lavagruben!",
    "Rain, rivers & palms": "Regen, Flüsse & Palmen", "Red dust · very low gravity": "Roter Staub · sehr wenig Schwerkraft",
    "Winter, spring, summer & fall": "Winter, Frühling, Sommer & Herbst", "Underwater": "Unterwasserwelt",
    "Coral, seaweed & shipwrecks": "Korallen, Seetang & Schiffswracks",
    # vehicles
    "Jeep": "Jeep", "Dirt Bike": "Crossmotorrad", "Chopper": "Chopper", "Monster Truck": "Monstertruck",
    "Supercar": "Sportwagen", "Tank": "Panzer", "Police Car": "Polizeiauto", "Hoverboard": "Hoverboard",
    "Tesla": "Tesla", "Mini One": "Mini One", "B2 Bomber": "B2-Bomber", "Excavator": "Bagger", "LKW": "LKW",
    "Horse": "Pferd", "Shark": "Hai", "Swims, bites, flies": "Schwimmt, beißt, fliegt",
    "Trusty all-rounder": "Zuverlässiger Allrounder", "Light and flippy": "Leicht und saltofreudig",
    "Long, low and loud": "Lang, tief und laut", "Crushes every hill": "Plättet jeden Hügel",
    "Fast, but scrapes": "Schnell, aber setzt auf", "Slow. Heavy. Unstoppable.": "Langsam. Schwer. Unaufhaltsam.",
    "Siren on the horn key": "Sirene auf der Hupe", "Glides, slides and flies": "Gleitet, rutscht und fliegt",
    "Silent, instant torque": "Lautlos, sofort volle Kraft", "Small, quick and cheeky": "Klein, flink und frech",
    "Why drive? Fly!": "Wozu fahren? Flieg!", "Digs in, never gives up": "Gräbt sich durch, gibt nie auf",
    "Big, heavy, unstoppable": "Groß, schwer, unaufhaltsam", "Gallops over every hill": "Galoppiert über jeden Hügel",
    "CHOOSE YOUR RIDE": "WÄHLE DEIN FAHRZEUG",
    "Every vehicle is free  ·  tap it again (or press Enter) when you're done":
        "Alle Fahrzeuge gratis  ·  nochmal antippen (oder Enter), wenn du fertig bist",
    # drivers
    "CHOOSE YOUR DRIVER": "WÄHLE DEINEN FAHRER", "Racer": "Rennfahrer",
    "Pick who drives  ·  They will swear when they crash!": "Wer fährt?  ·  Bei einem Unfall wird geflucht!",
    "Click the picture to see everyone": "Klicke aufs Bild, um alle zu sehen",
    "Tap the picture to see everyone": "Tippe aufs Bild, um alle zu sehen",
    # garage
    "ENGINE": "MOTOR", "SUSPENSION": "FEDERUNG", "TIRES": "REIFEN", "BOOST": "BOOST", "MAXED OUT": "MAXIMUM",
    "HORN: PUPPY": "HUPE: WELPE", "HORN: SHIP": "HUPE: SCHIFF",
    "Click an upgrade (or 1-4) to buy  ·  H switches the horn  ·  Enter to start":
        "Upgrade anklicken (oder 1-4) zum Kaufen  ·  H wechselt die Hupe  ·  Enter zum Starten",
    # settings
    "MASTER VOLUME": "GESAMTLAUTSTÄRKE", "MUSIC": "MUSIK", "EFFECTS & HORN": "EFFEKTE & HUPE",
    "DRIVER VOICES": "FAHRERSTIMMEN", "MUSIC WHILE DRIVING": "MUSIK BEIM FAHREN", "AUTO (PER MAP)": "AUTO (JE KARTE)",
    "GRAPHICS": "GRAFIK", "HIGH": "HOCH", "LOW (FASTER)": "NIEDRIG (SCHNELLER)", "FULLSCREEN": "VOLLBILD",
    "ON": "AN", "OFF": "AUS", "GHOST OF YOUR BEST RUN": "GEIST DEINER BESTEN FAHRT", "SHOW": "ZEIGEN",
    "HIDE": "AUSBLENDEN", "NOT ON THIS DEVICE": "AUF DIESEM GERÄT NICHT", "CONTROLS": "STEUERUNG",
    "Gas / Brake": "Gas / Bremse", "Right / Left  (or D / A)": "Rechts / Links  (oder D / A)",
    "Boost  ·  Horn  ·  Lights": "Boost  ·  Hupe  ·  Licht", "Pause": "Pause", "Music / Fullscreen": "Musik / Vollbild",
    "Space  ·  H  ·  L": "Leertaste  ·  H  ·  L",
    "Changing the music plays it so you can listen": "Beim Wechseln hörst du die Musik gleich",
    "LANGUAGE": "SPRACHE",
    # trophies and achievements
    "First Ride": "Erste Fahrt", "Flipper": "Überschlag", "Acrobat": "Akrobat", "Frequent Flyer": "Vielflieger",
    "Marathon": "Marathon", "Explorer": "Entdecker", "Treasure Hunter": "Schatzjäger", "Trophy Master": "Trophäenmeister",
    "Moon Walker": "Mondläufer", "Lava Jumper": "Lavaspringer", "Rich": "Reich", "Collector": "Sammler",
    "Social Driver": "Geselliger Fahrer", "Champion": "Champion", "Night Rider": "Nachtfahrer",
    "Finish your first run": "Beende deine erste Fahrt", "Do a flip": "Mach einen Salto",
    "10 flips in one run": "10 Saltos in einer Fahrt", "5 seconds of air time in one jump": "5 Sekunden Flugzeit in einem Sprung",
    "Drive 1000 m in one run": "Fahre 1000 m in einer Fahrt", "Drive 3000 m in one run": "Fahre 3000 m in einer Fahrt",
    "Find 5 secret trophies": "Finde 5 geheime Trophäen", "Drive 500 m on the Moon": "Fahre 500 m auf dem Mond",
    "Jump 5 lava pits in one run": "Spring über 5 Lavagruben in einer Fahrt",
    "Earn 50,000 coins in total": "Verdiene insgesamt 50.000 Münzen", "Drive every vehicle": "Fahre jedes Fahrzeug",
    "Play an online race": "Fahre ein Online-Rennen", "Win an online race": "Gewinne ein Online-Rennen",
    "Drive 500 m at night": "Fahre 500 m bei Nacht",
    "Secret trophies hide high in the air, over lava and in tunnels - jump for them!":
        "Geheime Trophäen verstecken sich hoch in der Luft, über Lava und in Tunneln - spring danach!",
    # leaderboard
    "WORLD LEADERBOARD": "WELT-RANGLISTE",
    "Best distance per map, from every Hill Rider player. Your records upload automatically.":
        "Beste Strecke pro Karte, von allen Hill-Rider-Spielern. Deine Rekorde werden automatisch hochgeladen.",
    "Connecting to the internet...": "Verbinde mit dem Internet...",
    "connecting to the internet...": "verbinde mit dem Internet...",
    "No records yet - be the first!": "Noch keine Rekorde - sei der Erste!",
    # online
    "PLAY WITH FRIENDS": "MIT FREUNDEN SPIELEN", "YOUR PLAYER NUMBER": "DEINE SPIELERNUMMER", "YOUR NAME": "DEIN NAME",
    "Your name": "Dein Name", "HOST GAME": "SPIEL ERÖFFNEN",
    "JOIN A GAME BY THE HOST'S NUMBER": "MIT DER NUMMER DES GASTGEBERS BEITRETEN", "Number": "Nummer",
    "JOIN": "BEITRETEN", "ADD A FRIEND BY PLAYER NUMBER": "FREUND PER SPIELERNUMMER HINZUFÜGEN",
    "ADD FRIEND": "HINZUFÜGEN", "No friends yet - add one by player number.":
        "Noch keine Freunde - füge einen per Spielernummer hinzu.",
    "Tell friends your number. They add you, and you invite each other from the lobby - no IP addresses needed.":
        "Sag Freunden deine Nummer. Sie fügen dich hinzu, und ihr ladet euch in der Lobby ein - ohne IP-Adressen.",
    "A player number has 6 digits (and can't be your own).": "Eine Spielernummer hat 6 Ziffern (und ist nicht deine).",
    "Type the host's 6-digit player number.": "Gib die 6-stellige Nummer des Gastgebers ein.",
    "Type a 6-digit player number.": "Gib eine 6-stellige Spielernummer ein.",
    "Not connected to the internet yet - wait a moment.": "Noch nicht mit dem Internet verbunden - einen Moment.",
    "Lost the connection to the host.": "Die Verbindung zum Gastgeber ist abgebrochen.",
    "The host closed the game.": "Der Gastgeber hat das Spiel beendet.",
    "The host did not answer.": "Der Gastgeber antwortet nicht.",
    "Different game version - update Hill Rider on both PCs.": "Andere Spielversion - aktualisiere Hill Rider bei beiden.",
    "ONLINE LOBBY": "ONLINE-LOBBY", "YOU ARE THE HOST": "DU BIST DER GASTGEBER", "MODE": "MODUS",
    "FREE RIDE": "FREIE FAHRT", "TOURNAMENT · 4 RACES": "TURNIER · 4 RENNEN", "INVITE FRIENDS": "FREUNDE EINLADEN",
    "INVITE": "EINLADEN", "INVITE ANY PLAYER BY NUMBER": "JEDEN SPIELER PER NUMMER EINLADEN",
    "Player number": "Spielernummer", "Waiting for the host...": "Warte auf den Gastgeber...",
    "YOUR VEHICLE": "DEIN FAHRZEUG", "YOUR DRIVER": "DEIN FAHRER", "LEAVE": "VERLASSEN", "NO THANKS": "NEIN DANKE",
    "RACE RESULTS": "RENNERGEBNIS", "NEXT RACE": "NÄCHSTES RENNEN", "BACK TO LOBBY": "ZURÜCK ZUR LOBBY",
    "LEAVE GAME": "SPIEL VERLASSEN",
    "Points: 10 · 7 · 5 · 3 · 2 · 1  -  next map coming up":
        "Punkte: 10 · 7 · 5 · 3 · 2 · 1  -  gleich kommt die nächste Karte",
    "Finished! Waiting for the others...": "Im Ziel! Warte auf die anderen...",
    # driving
    "SPACE boost  ·  H horn  ·  L lights  ·  ESC pause": "LEERTASTE Boost  ·  H Hupe  ·  L Licht  ·  ESC Pause",
    "BRAKE": "BREMSE", "GAS": "GAS", "HORN": "HUPE", "GO!": "LOS!", "PAUSED": "PAUSE", "RESUME": "WEITER",
    "RESTART": "NEUSTART", "CHANGE RIDE": "WECHSELN", "M toggles music": "M schaltet die Musik um",
    "DRIVER DOWN!": "FAHRER K.O.!", "BURNED IN LAVA!": "IN DER LAVA VERBRANNT!", "BURNED!": "VERBRANNT!",
    "FLIPPED OVER!": "AUF DEM DACH!", "FLIPPED!": "ÜBERSCHLAGEN!", "FINISH!": "ZIEL!", "FLIP": "SALTO",
    "DOUBLE FLIP": "DOPPELSALTO", "NECK FLIP": "GENICKSALTO", "AIR TIME": "FLUGZEIT", "BIG AIR TIME": "GROSSE FLUGZEIT",
    "INSANE AIR TIME": "IRRE FLUGZEIT", "WINTER!": "WINTER!", "SPRING!": "FRÜHLING!", "SUMMER!": "SOMMER!",
    "FALL!": "HERBST!", "SECRET TROPHY!": "GEHEIME TROPHÄE!", "MUD!": "SCHLAMM!", "ICE!": "EIS!",
    "DEEP SNOW!": "TIEFSCHNEE!", "SAND!": "SAND!", "OIL!": "ÖL!", "SEAWEED!": "SEETANG!", "NITRO!": "NITRO!",
    # results
    "Distance": "Strecke", "Coins collected": "Gesammelte Münzen", "Stunt bonuses": "Stunt-Boni", "TOTAL": "GESAMT",
    "NEW RECORD!": "NEUER REKORD!", "RETRY": "NOCHMAL",
    "Enter / R to retry  ·  Esc to change map, vehicle or driver":
        "Enter / R für nochmal  ·  Esc zum Wechseln von Karte, Fahrzeug oder Fahrer",
    # daily challenge pieces
    "Drive": "Fahre",
    # on-screen keyboard
    "space": "Leertaste", "DEL": "ENTF", "DELETE": "LÖSCHEN",
})


def _sub(rx, fn):
    PATTERNS.append((re.compile(rx), fn))


_sub(r"^(\d+)m  \(best: (\d+)m\)$", r"\1m  (Rekord: \2m)")
_sub(r"^(\d+)m  of  (\d+)m$", r"\1m  von  \2m")
_sub(r"^BEST (\d+) ?m$", lambda m: f"REKORD {m.group(1)} m")
_sub(r"^(\d+) upgrades$", r"\1 Upgrades")
_sub(r"^LEVEL (\d+) / (\d+)$", r"STUFE \1 / \2")
_sub(r"^BUY  (.+)$", r"KAUFEN  \1")
_sub(r"^\+([\d,]+) coins$", lambda m: "+" + m.group(1).replace(",", ".") + " Münzen")
_sub(r"^ACHIEVEMENT: (.+)$", lambda m: "ERFOLG: " + tr(m.group(1)))
_sub(r"^TROPHY ROOM  ·  (\d+)/(\d+) ACHIEVEMENTS$", r"TROPHÄENRAUM  ·  \1/\2 ERFOLGE")
_sub(r"^SECRET TROPHIES  (\d+)/(\d+)$", r"GEHEIME TROPHÄEN  \1/\2")
_sub(r"^Find all (\d+) secret trophies$", r"Finde alle \1 geheimen Trophäen")
_sub(r"^Achievements (\d+)/(\d+)   ·   Trophies (\d+)/(\d+)$", r"Erfolge \1/\2   ·   Trophäen \3/\4")
_sub(r"^driven by (.+)$", lambda m: "gefahren von " + tr(m.group(1)))
_sub(r"^(\d+)/5 on (.+)$", lambda m: f"{m.group(1)}/5 auf {tr(m.group(2))}")
_sub(r"^FRIENDS \((\d+)\)$", r"FREUNDE (\1)")
_sub(r"^PLAYERS \((\d+)\)$", r"SPIELER (\1)")
_sub(r"^ROOM #(\d+)$", r"RAUM #\1")
_sub(r"^Added #(\d+) to your friends\.$", r"#\1 ist jetzt dein Freund.")
_sub(r"^Joining #(\d+) \.\.\.$", r"Trete #\1 bei ...")
_sub(r"^Invite sent to #(\d+)\.$", r"Einladung an #\1 geschickt.")
_sub(r"^Player #(\d+) is not hosting a game right now\.$", r"Spieler #\1 eröffnet gerade kein Spiel.")
_sub(r"^Player #(\d+) is hosting a game$", r"Spieler #\1 eröffnet ein Spiel")
_sub(r"^(.+) invites you!$", r"\1 lädt dich ein!")
_sub(r"^Friends can also join with your number #(\d+)$", r"Freunde können auch mit deiner Nummer #\1 beitreten")
_sub(r"^Waiting for the host to start(\.*)$", r"Warte, bis der Gastgeber startet\1")
_sub(r"^Could not host: (.+)$", r"Spiel konnte nicht eröffnet werden: \1")
_sub(r"^Could not connect: (.+)$", r"Keine Verbindung: \1")
_sub(r"^RACE  (\d+) m$", r"RENNEN  \1 m")
_sub(r"^RACE (\d+) OF (\d+)$", r"RENNEN \1 VON \2")
_sub(r"^CHAMPION: (.+)!$", r"CHAMPION: \1!")
_sub(r"^(\d+) pts$", r"\1 Pkt.")
_sub(r"^DNF  \((\d+) m\)$", r"AUSGESCHIEDEN  (\1 m)")
_sub(r"^POS (\d+)/(\d+)$", r"PLATZ \1/\2")
_sub(r"^(\d+)x FLIP$", r"\1x SALTO")
_sub(r"^(.+) FINISHED!$", r"\1 IM ZIEL!")
_sub(r"^(.+) \(you\)$", r"\1 (du)")
_sub(r"^DAILY: (.+) / (\d+) m$", r"TAGESZIEL: \1 / \2 m")
_sub(r"^DAILY: (.+) / (\d+) flips$", r"TAGESZIEL: \1 / \2 Saltos")
_sub(r"^DAILY: (.+) / (\d+) coins$", r"TAGESZIEL: \1 / \2 Münzen")
_sub(r"^DAILY: (.+) / (\d+) s air$", r"TAGESZIEL: \1 / \2 s Flugzeit")
# the daily challenge sentence
_sub(r"^Drive (\d+) m on (.+) with the (.+)$", lambda m: f"Fahre {m.group(1)} m auf {tr(m.group(2))} mit {tr(m.group(3))}")
_sub(r"^Do (\d+) flips on (.+) with the (.+)$", lambda m: f"Mach {m.group(1)} Saltos auf {tr(m.group(2))} mit {tr(m.group(3))}")
_sub(r"^Collect (\d+) coins on (.+) with the (.+)$",
     lambda m: f"Sammle {m.group(1)} Münzen auf {tr(m.group(2))} mit {tr(m.group(3))}")
_sub(r"^(\d+) s of air time in one jump on (.+) with the (.+)$",
     lambda m: f"{m.group(1)} s Flugzeit in einem Sprung auf {tr(m.group(2))} mit {tr(m.group(3))}")
# anything joined with a middle dot: translate the parts
_sub(r"^(.+?)(  ·  |   ·   | · )(.+)$", lambda m: tr(m.group(1)) + m.group(2) + tr(m.group(3)))
_index()
