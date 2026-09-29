# Smart Cities – Raspberry Pi Pico W & MicroPython

Ce dépôt rassemble les travaux réalisés avec le **Raspberry Pi Pico W** programmé en **MicroPython**.
Chaque thème (entrées/sorties, PWM, afficheur, LEDs, capteurs, réseau) possède son propre
sous-répertoire contenant un fichier `README.md` explicatif ainsi que les ressources associées :
code source, datasheets, photos, schémas de câblage et explications.

---

## Sommaire

- [Le Raspberry Pi Pico W](#le-raspberry-pi-pico-w)
- [Brochage](#brochage-du-raspberry-pi-pico-w)
- [MicroPython](#micropython)
- [Environnement de travail](#environnement-de-travail)
- [Organisation du dépôt](#organisation-du-dépôt)
- [Liens utiles](#liens-utiles)

---

## Le Raspberry Pi Pico W

Le **Raspberry Pi Pico W** est une carte à microcontrôleur conçue par la fondation Raspberry Pi.
Contrairement aux Raspberry Pi « classiques » (Pi 4, Pi 5…), ce n'est pas un ordinateur : il
n'exécute pas de système d'exploitation, mais un seul programme qui pilote directement le matériel.
Il est idéal pour lire des capteurs, commander des actionneurs et réaliser des objets connectés.

Le « **W** » signifie *wireless* : cette version ajoute une puce Wi-Fi et Bluetooth par rapport au
Pico standard.

### Caractéristiques principales

| Élément | Caractéristique |
|---|---|
| Microcontrôleur | RP2040 (conçu par Raspberry Pi) |
| Processeur | Double cœur ARM Cortex-M0+ jusqu'à 133 MHz |
| Mémoire vive (SRAM) | 264 Ko |
| Mémoire flash | 2 Mo |
| GPIO | 26 broches d'entrée/sortie utilisables |
| Entrées analogiques (ADC) | 3 entrées 12 bits (GP26, GP27, GP28) + capteur de température interne |
| PWM | 16 canaux |
| Bus de communication | 2 × UART, 2 × SPI, 2 × I²C |
| PIO | 8 machines d'état programmables |
| Sans fil | Wi-Fi 802.11n 2,4 GHz et Bluetooth (puce Infineon CYW43439) |
| Tension logique | **3,3 V** (les broches ne tolèrent pas le 5 V) |
| Alimentation | Micro-USB ou broche VSYS (1,8 V à 5,5 V) |
| LED intégrée | Accessible en MicroPython via `Pin("LED")` |

> ⚠️ **Attention** : les GPIO fonctionnent en 3,3 V. Brancher un signal 5 V directement sur une
> broche peut endommager le microcontrôleur.

---

## Brochage du Raspberry Pi Pico W

![Brochage du Raspberry Pi Pico W](https://github.com/hepl-scheen/smartcities/assets/158835010/20d19fc4-b9c3-4903-9ec8-b62cda90aee3)

Points importants à retenir :

- Les broches sont nommées **GP0 à GP28** : c'est ce numéro qu'on utilise dans le code
  (par exemple `Pin(16)` pour GP16).
- Les broches **GND** (masse) sont repérées par un carré sur la carte.
- **3V3(OUT)** fournit du 3,3 V pour alimenter les modules.
- **VBUS** fournit le 5 V de l'USB, **VSYS** est l'entrée d'alimentation principale.
- Seules **GP26, GP27 et GP28** peuvent lire une tension analogique (ADC0, ADC1, ADC2).
- Toutes les broches GP peuvent produire un signal **PWM**.

Le brochage officiel en PDF est disponible ici :
[PicoW-A4-Pinout.pdf](https://datasheets.raspberrypi.com/picow/PicoW-A4-Pinout.pdf)

---

## MicroPython

**MicroPython** est une version allégée du langage **Python 3**, optimisée pour fonctionner sur des
microcontrôleurs disposant de peu de mémoire. Elle permet de programmer le Pico avec une syntaxe
simple et lisible, sans compilation : le code est interprété directement par la carte.

MicroPython fournit des modules spécifiques pour accéder au matériel :

| Module | Rôle |
|---|---|
| `machine` | Accès au matériel : `Pin`, `PWM`, `ADC`, `I2C`, `SPI`, `UART`, `Timer`… |
| `time` | Pauses (`sleep`, `sleep_ms`) et mesure du temps (`ticks_ms`, `ticks_diff`) |
| `network` | Connexion Wi-Fi (spécifique au Pico W) |
| `neopixel` | Pilotage des LEDs adressables WS2812 (néopixels) |
| `rp2` | Fonctions propres au RP2040 (programmation des PIO…) |

### Exemple : faire clignoter la LED intégrée

```python
from machine import Pin
import time

led = Pin("LED", Pin.OUT)   # LED intégrée du Pico W

while True:
    led.toggle()            # inverse l'état de la LED
    time.sleep(0.5)         # attend 0,5 seconde
```

### Installation de MicroPython sur le Pico W

1. Télécharger le firmware `.uf2` pour le Pico W sur
   [micropython.org/download/RPI_PICO_W](https://micropython.org/download/RPI_PICO_W/).
2. Maintenir le bouton **BOOTSEL** enfoncé et brancher le Pico en USB.
3. Le Pico apparaît comme une clé USB nommée **RPI-RP2**.
4. Glisser le fichier `.uf2` dans cette clé : le Pico redémarre automatiquement avec MicroPython.

> L'installation peut aussi se faire directement depuis Thonny
> (menu *Exécuter → Configurer l'interpréteur → Installer ou mettre à jour MicroPython*).

---

## Environnement de travail

### Thonny

L'éditeur utilisé est **[Thonny](https://thonny.org/)**, un environnement Python simple, gratuit et
multiplateforme (Windows, macOS, Linux), qui gère nativement MicroPython sur le Raspberry Pi Pico.

Configuration :

1. Installer Thonny depuis [thonny.org](https://thonny.org/).
2. Brancher le Pico W en USB.
3. Dans Thonny : *Exécuter → Configurer l'interpréteur*, puis choisir
   **MicroPython (Raspberry Pi Pico)** et le port correspondant.
4. La console (*Shell*) en bas de la fenêtre permet de taper des commandes directement sur la carte.

Utilisation :

- **Exécuter** (bouton vert ▶ ou `F5`) : lance le programme ouvert sur le Pico.
- **Arrêter** (bouton rouge ■ ou `Ctrl+F2`) : stoppe le programme en cours.
- **Enregistrer sur le Pico** : *Fichier → Enregistrer sous → Raspberry Pi Pico*.
- Un fichier nommé **`main.py`** enregistré sur le Pico s'exécute automatiquement à chaque mise
  sous tension, même sans ordinateur.
- Les librairies (fichiers `.py` supplémentaires) doivent être copiées sur le Pico, en général dans
  le dossier `/lib`.

### Matériel utilisé

- Raspberry Pi Pico W
- Câble micro-USB (données, pas seulement charge)
- Modules : LED, bouton-poussoir, potentiomètre, buzzer, servomoteur, afficheur LCD,
  LEDs néopixel, capteurs (température/humidité, luminosité, PIR)
- Câbles de connexion

---

## Organisation du dépôt

Chaque sous-répertoire contient un `README.md` décrivant le sujet traité, ainsi que le code, les
datasheets, les photos et les schémas associés.

- [GPIO](GPIO) : LED simple, bouton-poussoir, interruptions.
- [AD-PWM](AD-PWM) : lecture du potentiomètre, PWM (LED, musique, servomoteur).
- [LCD](LCD) : documentation des fonctions de la librairie, affichage de la valeur du potentiomètre.
- [LED_neo](LED_neo) : utilisation des LEDs néopixel, documentation des fonctions de la librairie, effet arc-en-ciel.
- [sensors](sensors) : température et humidité, luminosité, détecteur de mouvement PIR.
- [network](network) : accès réseau avec le Raspberry Pi Pico W.

```
smartcities/
├── README.md        ← ce fichier
├── GPIO/
│   └── README.md
├── AD-PWM/
│   └── README.md
├── LCD/
│   └── README.md
├── LED_neo/
│   └── README.md
├── sensors/
│   └── README.md
└── network/
    └── README.md
```

---

## Liens utiles

- [Documentation officielle du Raspberry Pi Pico W](https://www.raspberrypi.com/documentation/microcontrollers/pico-series.html)
- [Datasheet du Pico W](https://datasheets.raspberrypi.com/picow/pico-w-datasheet.pdf)
- [Datasheet du RP2040](https://datasheets.raspberrypi.com/rp2040/rp2040-datasheet.pdf)
- [Documentation MicroPython pour le RP2040 (référence rapide)](https://docs.micropython.org/en/latest/rp2/quickref.html)
- [Téléchargement du firmware MicroPython pour Pico W](https://micropython.org/download/RPI_PICO_W/)
- [Thonny](https://thonny.org/)
