
from machine import Pin, ADC, PWM, I2C
import time
from lcd1602 import LCD1602, LCD1602_RGB

# Brochage 
PIN_POT = 26            # Port A0  -> GP26 (ADC0)
PIN_LED = 18            # Port D18 -> GP18
PIN_BUZZER = 16         # Port D16 -> GP16

#Parametres
T_MIN, T_MAX = 15.0, 35.0           # Plage
SEUIL_ALARME = 3.0                  # Ecart d'alarme declan
PERIODE_CHAUD_MS = 2000             # 0,5 Hz
PERIODE_ALARME_MS = 400             # 2,5 Hz clignotement plus rapide
RAFRAICH_LCD_MS = 2000              # Reecriture ecran
BUZZER_ACTIF = False                # True = buzzer actif (on/off), False = passif (PWM)
FREQ_BUZZER = 2000                  # Hz buzzer passif

#Bonus
DIMMER = True                       # Battement progressif de la LED
MODE_ALARME = "defile"              # "fixe", "clignote" ou "defile"

#Bus I2C
i2c_lcd = I2C(0, sda=Pin(8), scl=Pin(9), freq=100000)       # port I2C0
i2c_capt = I2C(1, sda=Pin(6), scl=Pin(7), freq=100000)      # port I2C1
adr_lcd = i2c_lcd.scan()
adr_capt = i2c_capt.scan()
print("I2C0 (ecran) :", [hex(a) for a in adr_lcd],
      "| I2C1 (capteur) :", [hex(a) for a in adr_capt])

#Capteur de temperature I2C
class DHT20:
    """Grove DHT20 / AHT20 (adresse 0x38)."""
    def __init__(self, i2c, addr=0x38):
        self.i2c, self.addr = i2c, addr
        time.sleep_ms(100)
        etat = self.i2c.readfrom(self.addr, 1)[0]
        if (etat & 0x08) == 0:                     # non calibre -> initialisation
            self.i2c.writeto(self.addr, b'\xbe\x08\x00')
            time.sleep_ms(10)

    def temperature(self):
        self.i2c.writeto(self.addr, b'\xac\x33\x00')   # lancer une mesure
        time.sleep_ms(80)
        d = self.i2c.readfrom(self.addr, 7)
        if d[0] & 0x80:                            # capteur encore occupe
            raise OSError("capteur occupe")
        brut = ((d[3] & 0x0F) << 16) | (d[4] << 8) | d[5]
        return brut / 1048576 * 200 - 50


class SHT3X:
    """Grove SHT31 / SHT35 (adresse 0x44 ou 0x45)."""
    def __init__(self, i2c, addr=0x44):
        self.i2c, self.addr = i2c, addr

    def temperature(self):
        self.i2c.writeto(self.addr, b'\x24\x00')       # mesure, haute repetabilite
        time.sleep_ms(20)
        d = self.i2c.readfrom(self.addr, 6)
        return -45 + 175 * ((d[0] << 8) | d[1]) / 65535


if 0x38 in adr_capt:
    capteur, TYPE_CAPTEUR = DHT20(i2c_capt), "DHT20"
elif 0x44 in adr_capt or 0x45 in adr_capt:
    capteur = SHT3X(i2c_capt, 0x44 if 0x44 in adr_capt else 0x45)
    TYPE_CAPTEUR = "SHT3x"
else:
    capteur, TYPE_CAPTEUR = None, "AUCUN"
    print("ATTENTION : aucun capteur detecte sur I2C1 (attendu 0x38 ou 0x44)")
PERIODE_MESURE_MS = 1000
print("Capteur utilise :", TYPE_CAPTEUR)


def lire_temperature():
    """Retourne la temperature en degC, ou None en cas d'erreur."""
    if capteur is None:
        return None
    try:
        return capteur.temperature()
    except OSError as e:
        print("Erreur capteur", TYPE_CAPTEUR, ":", e)
        return None

# ================= Ecran LCD =================
if 0x3E not in adr_lcd:
    raise RuntimeError("Ecran LCD (0x3E) introuvable sur I2C0 : verifier le cable")
RGB = 0x62 in adr_lcd

def init_lcd():
    return LCD1602_RGB(i2c_lcd, 2, 0) if RGB else LCD1602(i2c_lcd, 2, 0)

lcd = init_lcd()
DEG = chr(223)                              # symbole degre du HD44780
cache_lcd = ["", ""]
lcd_ok = True

def ecrire(ligne, texte):
    """Ecrit une ligne (16 car.) si elle a change ; reinitialise l'ecran en cas d'erreur."""
    global lcd, lcd_ok
    texte = (texte + " " * 16)[:16]
    if texte == cache_lcd[ligne] and lcd_ok:
        return
    try:
        if not lcd_ok:
            lcd = init_lcd()
            lcd_ok = True
        lcd.setCursor(0, ligne)
        lcd.print(texte)
        cache_lcd[ligne] = texte
    except OSError:
        lcd_ok = False                      # nouvel essai au tour suivant
        cache_lcd[0] = cache_lcd[1] = ""

#otentiometre, LED, buzzer
pot = ADC(Pin(PIN_POT))

led = PWM(Pin(PIN_LED))
led.freq(1000)
led.duty_u16(0)

if BUZZER_ACTIF:
    buz = Pin(PIN_BUZZER, Pin.OUT, value=0)
else:
    buz = PWM(Pin(PIN_BUZZER))
    buz.freq(FREQ_BUZZER)
    buz.duty_u16(0)


def lire_consigne():
    """Potentiometre -> consigne 15..35 degC (moyenne de 16 lectures, pas de 0,5)."""
    somme = 0
    for _ in range(16):
        somme += pot.read_u16()
    t = T_MIN + (T_MAX - T_MIN) * (somme / 16) / 65535
    return round(t * 2) / 2


def maj_led(periode, now):
    if periode is None:
        led.duty_u16(0)
        return
    phase = (now % periode) / periode       # 0 -> 1 sur une periode
    if DIMMER:
        x = 1 - abs(2 * phase - 1)          # triangle 0 -> 1 -> 0
        led.duty_u16(int(65535 * x * x))    # correction gamma approximative
    else:
        led.duty_u16(65535 if phase < 0.5 else 0)


def buzzer(actif):
    if BUZZER_ACTIF:
        buz.value(1 if actif else 0)
    else:
        buz.duty_u16(32768 if actif else 0)


def zone_alarme(now):
    """Texte de 5 caracteres affiche en colonnes 12..16 de la ligne 1."""
    if MODE_ALARME == "clignote":
        return "ALARM" if (now // 400) % 2 == 0 else "     "
    if MODE_ALARME == "defile":
        bande = "     ALARM"
        i = (now // 250) % len(bande)
        return (bande + bande)[i:i + 5]
    return "ALARM"


COULEURS = {"NORMAL": (0, 255, 0), "CHAUD": (255, 120, 0),
            "ALARME": (255, 0, 0), "INCONNU": (255, 255, 255)}


# ================= Boucle principale (non bloquante) =================
t_mesure = None
etat_prec = None
derniere_mesure = time.ticks_add(time.ticks_ms(), -PERIODE_MESURE_MS)
dernier_rafraich = time.ticks_ms()

try:
    while True:
        now = time.ticks_ms()

        # 1) Mesure de temperature environ toutes les secondes
        if time.ticks_diff(now, derniere_mesure) >= PERIODE_MESURE_MS:
            derniere_mesure = now
            t = lire_temperature()
            if t is not None:
                t_mesure = t

        # 2) Consigne
        consigne = lire_consigne()

        # 3) Comparaison -> etat
        if t_mesure is None:
            etat = "INCONNU"
        elif t_mesure >= consigne + SEUIL_ALARME:
            etat = "ALARME"
        elif t_mesure > consigne:
            etat = "CHAUD"
        else:
            etat = "NORMAL"

        if etat != etat_prec:
            print("Etat :", etat, "| Set =", consigne, "| Ambient =", t_mesure)
            if RGB:
                try:
                    lcd.set_rgb(*COULEURS[etat])
                except OSError:
                    lcd_ok = False
            etat_prec = etat

        # 4) Actionneurs
        if etat == "ALARME":
            maj_led(PERIODE_ALARME_MS, now)
            buzzer((now % PERIODE_ALARME_MS) < PERIODE_ALARME_MS // 2)  # bips
        elif etat == "CHAUD":
            maj_led(PERIODE_CHAUD_MS, now)
            buzzer(False)
        else:
            maj_led(None, now)
            buzzer(False)

        # 5) Affichage LCD (reecriture forcee periodique : l'ecran peut
        #    s'effacer tout seul lors du branchement d'un module)
        if time.ticks_diff(now, dernier_rafraich) >= RAFRAICH_LCD_MS:
            dernier_rafraich = now
            cache_lcd[0] = cache_lcd[1] = ""

        ligne1 = "Set: {:4.1f}{}".format(consigne, DEG)          # 10 caracteres
        if etat == "ALARME":
            ligne1 += " " + zone_alarme(now)                      # -> 16 caracteres
        ecrire(0, ligne1)

        if t_mesure is None:
            ecrire(1, "Ambient: --.-" + DEG)
        else:
            ecrire(1, "Ambient: {:.1f}{}".format(t_mesure, DEG))

        time.sleep_ms(20)

except KeyboardInterrupt:
    pass
finally:
    led.duty_u16(0)
    buzzer(False)
    print("Programme arrete.")

