from machine import Pin, ADC
import time
import random

# CONFIGURATION
PIN_MICRO = 26           # A0 = 26, A1 = 27, A2 = 28

TYPE_LED = "neopixel"    # "neopixel" (1 fil de signal) ou "pwm" (broches R, G, B)
PIN_LED = 18             # D18
NB_LEDS = 1
PINS_RGB = (16, 17, 18)  # pour "pwm" : rouge, vert, bleu
ANODE_COMMUNE = False    # pour "pwm"
LUMINOSITE = 1.0         # 0.0 à 1.0

DUREE_FENETRE_MS = 20    # durée d'une mesure du son
SENSIBILITE = 1.5        # pic = son 1,5 fois plus fort que la moyenne
NIVEAU_MIN = 1500        # ignore le bruit de fond
ECART_MIN_MS = 250       # temps minimum entre deux battements
VITESSE_MOYENNE = 0.05   # adaptation de la moyenne
EXTINCTION = 0.85        # vitesse à laquelle la couleur s'estompe (1.0 = reste allumée)

BPM_MIN = 40
BPM_MAX = 220
NB_INTERVALLES = 8       # intervalles moyennés pour le BPM
FICHIER_BPM = "bpm.txt"
PERIODE_ENREGISTREMENT_MS = 60000

# mes outils
micro = ADC(Pin(PIN_MICRO))

if TYPE_LED == "neopixel":
    import neopixel
    bande = neopixel.NeoPixel(Pin(PIN_LED), NB_LEDS)

    def afficher(r, g, b):
        for i in range(NB_LEDS):
            bande[i] = (r, g, b)
        bande.write()
else:
    from machine import PWM
    canaux = [PWM(Pin(p)) for p in PINS_RGB]
    for canal in canaux:
        canal.freq(1000)

    def afficher(r, g, b):
        for canal, valeur in zip(canaux, (r, g, b)):
            rapport = valeur * 257   # 0-255 -> 0-65535
            if ANODE_COMMUNE:
                rapport = 65535 - rapport
            canal.duty_u16(rapport)


def mesurer_niveau():
    # écart entre la valeur max et min : plus le son est fort, plus il est grand
    mini = 65535
    maxi = 0
    debut = time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), debut) < DUREE_FENETRE_MS:
        valeur = micro.read_u16()
        if valeur < mini:
            mini = valeur
        if valeur > maxi:
            maxi = valeur
    return maxi - mini


def nouvelle_teinte(teinte_prec):
    # teinte au hasard, assez différente de la précédente
    while True:
        teinte = random.randint(0, 359)
        ecart = abs(teinte - teinte_prec)
        if min(ecart, 360 - ecart) >= 60:
            return teinte


def teinte_vers_rgb(teinte):
    # roue des couleurs -> (r, g, b)
    secteur = teinte // 60
    x = (teinte % 60) * 255 // 60
    if secteur == 0:
        return (255, x, 0)
    if secteur == 1:
        return (255 - x, 255, 0)
    if secteur == 2:
        return (0, 255, x)
    if secteur == 3:
        return (0, 255 - x, 255)
    if secteur == 4:
        return (x, 0, 255)
    return (255, 0, 255 - x)


def enregistrer_bpm(numero_minute, liste_bpm):
    if liste_bpm:
        moyenne = round(sum(liste_bpm) / len(liste_bpm))
        ligne = "Minute {} : {} BPM\n".format(numero_minute, moyenne)
    else:
        ligne = "Minute {} : aucun rythme detecte\n".format(numero_minute)
    try:
        with open(FICHIER_BPM, "a") as fichier:   # "a" = ajout, with = fermeture auto
            fichier.write(ligne)
        print("Enregistre ->", ligne.strip())
    except OSError as erreur:
        print("Erreur d'ecriture :", erreur)


# mon programme
afficher(0, 0, 0)
moyenne_niveau = mesurer_niveau()
teinte = 0
couleur = (0, 0, 0)
intensite = 0.0

dernier_battement = None
intervalles = []
bpm_de_la_minute = []
debut_minute = time.ticks_ms()
numero_minute = 1

print("Ecoute de la musique...")

try:
    while True:
        niveau = mesurer_niveau()
        maintenant = time.ticks_ms()

        # détection d'un battement
        assez_loin = (dernier_battement is None or
                      time.ticks_diff(maintenant, dernier_battement) > ECART_MIN_MS)
        battement = (niveau > moyenne_niveau * SENSIBILITE and
                     niveau > NIVEAU_MIN and assez_loin)

        moyenne_niveau += VITESSE_MOYENNE * (niveau - moyenne_niveau)

        if battement:
            teinte = nouvelle_teinte(teinte)
            couleur = teinte_vers_rgb(teinte)
            intensite = 1.0

            # calcul du BPM
            if dernier_battement is not None:
                intervalle = time.ticks_diff(maintenant, dernier_battement)
                if intervalle > 60000 // BPM_MIN:
                    intervalles = []   # longue pause : on recommence
                elif 60000 / intervalle <= BPM_MAX:
                    intervalles.append(intervalle)
                    if len(intervalles) > NB_INTERVALLES:
                        intervalles.pop(0)
                    bpm = 60000 / (sum(intervalles) / len(intervalles))
                    bpm_de_la_minute.append(bpm)
                    print("Battement ! BPM :", round(bpm))
            dernier_battement = maintenant
        else:
            intensite *= EXTINCTION

        # mise à jour de la LED
        facteur = intensite * LUMINOSITE
        afficher(int(couleur[0] * facteur),
                 int(couleur[1] * facteur),
                 int(couleur[2] * facteur))

        # enregistrement chaque minute
        if time.ticks_diff(maintenant, debut_minute) >= PERIODE_ENREGISTREMENT_MS:
            enregistrer_bpm(numero_minute, bpm_de_la_minute)
            bpm_de_la_minute = []
            numero_minute += 1
            debut_minute = maintenant

except KeyboardInterrupt:
    afficher(0, 0, 0)
    print("Programme arrete")
