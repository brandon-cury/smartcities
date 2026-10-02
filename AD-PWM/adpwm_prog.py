from machine import Pin, PWM, ADC
import time

# CONFIGURATION
PIN_POTENTIOMETRE = 26   # A0 du shield 
PIN_BUZZER = 20          # D20 du shield (GP20)
PIN_BOUTON = 18          # BONUS : connect D18 - change de mélodie
PIN_LED = 16             # BONUS : connect D16 - clignote au rythme des notes

VOLUME_MAX = 32768       # rapport cyclique max = 50 % (le plus fort possible)
SEUIL_SILENCE = 3        # en dessous de ce pourcentage, le buzzer se tait
NB_MESURES = 4           # lectures moyennées du potentiomètre

TEMPO = 120              # nombre de noires par minute
PAUSE_ENTRE_NOTES = 40   # ms de silence entre deux notes (les notes sont détachées)
PAUSE_FIN = 800          # ms de silence avant de rejouer la mélodie
TRANSPOSITION = 2        # 1 = normal, 2 = une octave plus aigu (le buzzer sonne plus fort dans l'aigu)
ANTI_REBOND_MS = 50

# frequence de mes note
NOTES = {
    "SOL3": 196, "LA3": 220, "SI3": 247,
    "DO4": 262, "RE4": 294, "MI4": 330, "FA4": 349,
    "SOL4": 392, "LA4": 440, "SI4": 494,
    "DO5": 523, "RE5": 587, "MI5": 659,
    "-": 0,
}

# Durées, nombre de temps que dure mes note : 1 = noire, 0.5 = croche, 2 = blanche, 4 = ronde
MELODIES = [
    ("Frere Jacques", [
        ("DO4", 1), ("RE4", 1), ("MI4", 1), ("DO4", 1),
        ("DO4", 1), ("RE4", 1), ("MI4", 1), ("DO4", 1),
        ("MI4", 1), ("FA4", 1), ("SOL4", 2),
        ("MI4", 1), ("FA4", 1), ("SOL4", 2),
        ("SOL4", 0.5), ("LA4", 0.5), ("SOL4", 0.5), ("FA4", 0.5), ("MI4", 1), ("DO4", 1),
        ("SOL4", 0.5), ("LA4", 0.5), ("SOL4", 0.5), ("FA4", 0.5), ("MI4", 1), ("DO4", 1),
        ("DO4", 1), ("SOL3", 1), ("DO4", 2),
        ("DO4", 1), ("SOL3", 1), ("DO4", 2),
    ]),
    ("Ode a la joie", [
        ("MI4", 1), ("MI4", 1), ("FA4", 1), ("SOL4", 1),
        ("SOL4", 1), ("FA4", 1), ("MI4", 1), ("RE4", 1),
        ("DO4", 1), ("DO4", 1), ("RE4", 1), ("MI4", 1),
        ("MI4", 1.5), ("RE4", 0.5), ("RE4", 2),
        ("MI4", 1), ("MI4", 1), ("FA4", 1), ("SOL4", 1),
        ("SOL4", 1), ("FA4", 1), ("MI4", 1), ("RE4", 1),
        ("DO4", 1), ("DO4", 1), ("RE4", 1), ("MI4", 1),
        ("RE4", 1.5), ("DO4", 0.5), ("DO4", 2),
    ]),
    ("Au clair de la lune", [
        ("DO4", 1), ("DO4", 1), ("DO4", 1), ("RE4", 1),
        ("MI4", 2), ("RE4", 2),
        ("DO4", 1), ("MI4", 1), ("RE4", 1), ("RE4", 1),
        ("DO4", 4),
    ]),
    ("Fanfare perso", [  
        ("DO4", 0.5), ("MI4", 0.5), ("SOL4", 0.5), ("DO5", 1.5),
        ("-", 0.5),
        ("SOL4", 0.5), ("DO5", 0.5), ("MI5", 2),
        ("RE5", 0.5), ("DO5", 0.5), ("SI4", 0.5), ("LA4", 0.5),
        ("SOL4", 1), ("MI4", 1),
        ("FA4", 0.5), ("LA4", 0.5), ("SOL4", 0.5), ("FA4", 0.5),
        ("MI4", 0.5), ("RE4", 0.5), ("DO4", 2),
    ]),
]

# mes outils
potentiometre = ADC(Pin(PIN_POTENTIOMETRE))
buzzer = PWM(Pin(PIN_BUZZER))
buzzer.duty_u16(0)
bouton = Pin(PIN_BOUTON, Pin.IN, Pin.PULL_DOWN)   # le bouton Grove envoie 1 quand on appuie
led = Pin(PIN_LED, Pin.OUT)
led.off()

etat_bouton_prec = False
dernier_changement_bouton = 0


def lire_volume():
    """Lit le potentiomètre et renvoie le rapport cyclique à appliquer au buzzer."""
    total = 0
    for _ in range(NB_MESURES):
        total += potentiometre.read_u16()
    valeur = total // NB_MESURES
    if valeur * 100 // 65535 < SEUIL_SILENCE:
        return 0
    rapport = valeur / 65535
    return int(rapport * rapport * VOLUME_MAX)   # courbe au carré : variation plus naturelle


def bouton_appuye():
    """Renvoie True une seule fois au moment où le bouton est enfoncé (avec anti-rebond)."""
    global etat_bouton_prec, dernier_changement_bouton
    maintenant = time.ticks_ms()
    appuye = bouton.value() == 1
    if (appuye != etat_bouton_prec and
            time.ticks_diff(maintenant, dernier_changement_bouton) > ANTI_REBOND_MS):
        dernier_changement_bouton = maintenant
        etat_bouton_prec = appuye
        return appuye
    return False


def attendre(duree_ms, son_actif):
    """duree_ms en mettant à jour le volume en continu et en surveillant le bouton.
    Renvoie True si le bouton a été appuyé pendant l'attente."""
    debut = time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), debut) < duree_ms:
        if son_actif:
            buzzer.duty_u16(lire_volume())       # le volume suit le potentiomètre en direct
        if bouton_appuye():
            return True
        time.sleep_ms(10)
    return False


def jouer_note(nom, duree):
    """Joue une note. Renvoie True si le bouton a été appuyé pendant la note."""
    duree_ms = int(duree * 60000 / TEMPO)        # durée d'une noire = 60000 / TEMPO ms
    frequence = NOTES[nom]

    if frequence == 0:                           # silence
        buzzer.duty_u16(0)
        led.off()
        return attendre(duree_ms, False)

    buzzer.freq(frequence * TRANSPOSITION)
    led.on()                                     # BONUS : LED allumée pendant la note
    if attendre(duree_ms - PAUSE_ENTRE_NOTES, True):
        return True
    buzzer.duty_u16(0)                           # petit silence pour détacher les notes
    led.off()
    return attendre(PAUSE_ENTRE_NOTES, False)


def couper_son():
    buzzer.duty_u16(0)
    led.off()


# mon programme
melodie_actuelle = 0
print("Tourne le potentiometre pour le volume, appuie sur le bouton pour changer de melodie")

try:
    while True:
        nom, notes = MELODIES[melodie_actuelle]
        print("Melodie :", nom)

        changement = False
        for note, duree in notes:
            if jouer_note(note, duree):
                changement = True
                break
        couper_son()

        # on change de mélodie si le bouton a été appuyé pendant la mélodie ou pendant la pause
        if changement or attendre(PAUSE_FIN, False):
            melodie_actuelle = (melodie_actuelle + 1) % len(MELODIES)

