from machine import Pin, PWM
import time

PIN_LED = 16
PIN_BOUTON = 18

# Mettre False si ton module bouton envoie 0 (GND) quand on appuie
BOUTON_ACTIF_HAUT = True

# BONUS : nombre d'appuis pour passé ) un autre état
APPUIS_PAR_CHANGEMENT = 1

# BONUS : effet de fondu lors du changement de mode
EFFET_TRANSITION = True

ANTI_REBOND_MS = 50  # filtre les rebonds mécaniques du bouton

# Liste des modes
MODES = [
    ("Eteinte", None),
    ("Lent 0,5 Hz", 1000),  
    ("Rapide 2 Hz", 250),   
]

# mes outils
led = PWM(Pin(PIN_LED))  # PWM pour pouvoir faire des fondus
led.freq(1000)

if BOUTON_ACTIF_HAUT:
    bouton = Pin(PIN_BOUTON, Pin.IN, Pin.PULL_DOWN)
else:
    bouton = Pin(PIN_BOUTON, Pin.IN, Pin.PULL_UP)


def led_on():
    led.duty_u16(65535)


def led_off():
    led.duty_u16(0)


def est_appuye():
    return bouton.value() == (1 if BOUTON_ACTIF_HAUT else 0)


def effet_transition():
    """BONUS : petit fondu montant puis descendant (~0,4 s)."""
    for i in range(0, 65536, 4096):
        led.duty_u16(i)
        time.sleep_ms(12)
    for i in range(65535, -1, -4096):
        led.duty_u16(i)
        time.sleep_ms(12)
    led_off()


# mon programme
mode = 0
compteur_appuis = 0
etat_bouton_prec = False
dernier_changement_bouton = 0
etat_led = False
dernier_basculement = time.ticks_ms()

led_off()
print("Pret. Mode :", MODES[mode][0])

while True:
    maintenant = time.ticks_ms()

    # --- Lecture du bouton avec anti-rebond ---
    appuye = est_appuye()
    if (appuye != etat_bouton_prec and
            time.ticks_diff(maintenant, dernier_changement_bouton) > ANTI_REBOND_MS):
        dernier_changement_bouton = maintenant
        etat_bouton_prec = appuye

        if appuye:  # front d'appui détecté
            compteur_appuis += 1
            if compteur_appuis >= APPUIS_PAR_CHANGEMENT:
                compteur_appuis = 0
                mode = (mode + 1) % len(MODES) 
                print("Mode :", MODES[mode][0])

                if EFFET_TRANSITION:
                    effet_transition()
                # On démarre le nouveau mode LED allumée (sauf mode éteint)
                if MODES[mode][1] is None:
                    etat_led = False
                    led_off()
                else:
                    etat_led = True
                    led_on()
                dernier_basculement = time.ticks_ms()

    # --- Clignotement non bloquant ---
    demi_periode = MODES[mode][1]
    if demi_periode is not None:
        print(time.ticks_ms(), dernier_basculement)
        if time.ticks_diff(time.ticks_ms(), dernier_basculement) >= demi_periode:
            etat_led = not etat_led
            if etat_led:
                led_on()
            else:
                led_off()
            dernier_basculement = time.ticks_ms()

    time.sleep_ms(5)