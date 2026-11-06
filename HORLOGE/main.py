from machine import Pin, PWM
import machine
import network
import ntptime
import time
from secrets import SSID, MOT_DE_PASSE

# CONFIGURATION
MODE_PROFILAGE = True   # True = cycle des 4 états pour les mesures avec le PPK2

PIN_SERVO = 20           # D20
PIN_BOUTON = 18          # D18 (bonus)

SERVO_MIN_US = 1000      # impulsion pour 0° (élargir petit à petit si besoin)
SERVO_MAX_US = 2000      # impulsion pour 180°

FUSEAUX = [("UTC", 0), ("UTC+1", 1), ("UTC+2", 2), ("UTC-5", -5), ("UTC+9", 9)]
FICHIER_REGLAGES = "reglages.txt"

PERIODE_SERVO_MS = 30000         # mise à jour de l'aiguille
PERIODE_NTP_MS = 3600000         # resynchronisation toutes les heures
DELAI_DOUBLE_CLIC_MS = 400
ANTI_REBOND_MS = 50

DUREE_ETAT_MS = 10000            # durée de chaque état en mode profilage

# mes outils
servo = PWM(Pin(PIN_SERVO))
servo.freq(50)                   # un servo attend une impulsion toutes les 20 ms
bouton = Pin(PIN_BOUTON, Pin.IN, Pin.PULL_DOWN)
wlan = network.WLAN(network.STA_IF)


# --- Wi-Fi et heure ---
def connecter_wifi():
    wlan.active(True)
    wlan.connect(SSID, MOT_DE_PASSE)
    debut = time.ticks_ms()
    while not wlan.isconnected():
        if time.ticks_diff(time.ticks_ms(), debut) > 15000:
            print("Wi-Fi : echec de connexion")
            return False
        time.sleep_ms(200)
    print("Wi-Fi connecte :", wlan.ifconfig()[0])
    return True


def couper_wifi():
    wlan.disconnect()
    wlan.active(False)


def synchroniser_heure():
    for _ in range(3):
        try:
            ntptime.settime()            # met l'horloge interne à l'heure UTC
            print("Heure synchronisee")
            return True
        except OSError:
            time.sleep(1)
    print("NTP : echec")
    return False


def mettre_a_l_heure():
    if connecter_wifi():
        synchroniser_heure()
    couper_wifi()                        # le Wi-Fi consomme beaucoup : on le coupe


def heure_locale(decalage):
    t = time.localtime(time.time() + decalage * 3600)
    return t[3], t[4]                    # heure, minute


# --- Servo ---
def calculer_angle(heure, minute, mode_24h):
    if mode_24h:
        return (heure + minute / 60) * 7.5          # 24 h sur 180°
    return ((heure % 12) + minute / 60) * 15        # 12 h sur 180°


def placer_servo(angle):
    angle = max(0, min(180, angle))
    impulsion_us = SERVO_MIN_US + (SERVO_MAX_US - SERVO_MIN_US) * angle / 180
    servo.duty_ns(int(impulsion_us * 1000))
    time.sleep_ms(500)               # le servo rejoint l'angle
    servo.duty_ns(0)                 # coupe le signal : il ne force plus et ne chauffe pas


def afficher_heure(index_fuseau, mode_24h):
    nom, decalage = FUSEAUX[index_fuseau]
    heure, minute = heure_locale(decalage)
    angle = calculer_angle(heure, minute, mode_24h)
    placer_servo(angle)
    print("{} {:02d}:{:02d} -> {:.1f} deg ({})".format(
        nom, heure, minute, angle, "24h" if mode_24h else "12h"))


# --- Réglages sauvegardés (conservés après un deep sleep) ---
def charger_reglages():
    try:
        with open(FICHIER_REGLAGES) as fichier:
            index, mode = fichier.read().split(";")
            return int(index) % len(FUSEAUX), mode.strip() == "1"
    except (OSError, ValueError):
        return 1, False                  # UTC+1, mode 12 h


def sauver_reglages(index_fuseau, mode_24h):
    with open(FICHIER_REGLAGES, "w") as fichier:
        fichier.write("{};{}".format(index_fuseau, 1 if mode_24h else 0))


# --- Profilage énergétique ---
def attente_active(duree_ms):
    debut = time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), debut) < duree_ms:
        pass                             # le processeur tourne en continu


def cycle_profilage(index_fuseau, mode_24h):
    print("ETAT 1 : actif + Wi-Fi")
    if connecter_wifi():
        synchroniser_heure()
    attente_active(DUREE_ETAT_MS)
    couper_wifi()
    afficher_heure(index_fuseau, mode_24h)

    print("ETAT 2 : actif sans Wi-Fi")
    attente_active(DUREE_ETAT_MS)

    print("ETAT 3 : light sleep")
    time.sleep_ms(100)
    machine.lightsleep(DUREE_ETAT_MS)

    print("ETAT 4 : deep sleep")
    time.sleep_ms(100)
    machine.deepsleep(DUREE_ETAT_MS)     # le Pico redémarre ensuite (main.py)


# --- Mode horloge ---
def boucle_horloge(index_fuseau, mode_24h):
    mettre_a_l_heure()
    afficher_heure(index_fuseau, mode_24h)

    dernier_servo = time.ticks_ms()
    dernier_ntp = time.ticks_ms()
    etat_prec = False
    dernier_changement = 0
    clic_en_attente = False
    instant_clic = 0

    while True:
        maintenant = time.ticks_ms()

        # bouton avec anti-rebond
        appuye = bouton.value() == 1
        if (appuye != etat_prec and
                time.ticks_diff(maintenant, dernier_changement) > ANTI_REBOND_MS):
            dernier_changement = maintenant
            etat_prec = appuye
            if appuye:
                if clic_en_attente:                  # 2e clic rapide : double clic
                    clic_en_attente = False
                    mode_24h = not mode_24h
                    sauver_reglages(index_fuseau, mode_24h)
                    afficher_heure(index_fuseau, mode_24h)
                else:
                    clic_en_attente = True
                    instant_clic = maintenant

        # simple clic confirmé : changement de fuseau
        if clic_en_attente and time.ticks_diff(maintenant, instant_clic) > DELAI_DOUBLE_CLIC_MS:
            clic_en_attente = False
            index_fuseau = (index_fuseau + 1) % len(FUSEAUX)
            sauver_reglages(index_fuseau, mode_24h)
            afficher_heure(index_fuseau, mode_24h)

        if time.ticks_diff(maintenant, dernier_servo) >= PERIODE_SERVO_MS:
            afficher_heure(index_fuseau, mode_24h)
            dernier_servo = maintenant

        if time.ticks_diff(maintenant, dernier_ntp) >= PERIODE_NTP_MS:
            mettre_a_l_heure()
            dernier_ntp = time.ticks_ms()

        time.sleep_ms(10)


# mon programme
index_fuseau, mode_24h = charger_reglages()

if MODE_PROFILAGE:
    cycle_profilage(index_fuseau, mode_24h)
else:
    boucle_horloge(index_fuseau, mode_24h)
