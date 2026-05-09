"""
THE TOWER v2.0
Survival tower defense with prestige, bosses, turrets, abilities, save/load.
"""
import pygame, math, random, time, json, os

# ── CONFIG ──────────────────────────────────────────────
TOWER_SHAPE = "hexagon"
ENEMY_SHAPE = "square"
SHOW_RANGE = True

# ── CONSTANTS ───────────────────────────────────────────
WIDTH, HEIGHT = 1000, 700
CENTER_X, CENTER_Y = 500, 350

BG = (15, 20, 30)
GRID = (30, 35, 50)
TOWER_C = (80, 150, 255)
TOWER_OUT = (150, 200, 255)
TOWER_GUN = (100, 170, 255)
ENEMY_BASIC = (255, 80, 80)
ENEMY_TANK = (180, 60, 60)
ENEMY_SWARM = (255, 150, 50)
ENEMY_HEAL = (80, 255, 120)
ENEMY_BOMB = (255, 180, 0)
ENEMY_INV = (150, 80, 200)
PROJ = (255, 255, 100)
HP_BG = (60, 60, 60)
HP_FG = (80, 220, 80)
HP_RED = (220, 80, 80)
PANEL_BG = (25, 30, 45)
PANEL_BDR = (50, 55, 75)
TEXT = (220, 220, 220)
TEXT_DIM = (150, 150, 170)
GOLD = (255, 215, 0)
BTN = (60, 80, 120)
BTN_HOVER = (80, 110, 160)
BTN_MAXED = (80, 120, 80)
TAB_OFF = (255, 100, 100)
TAB_DEF = (100, 150, 255)
TAB_UTL = (255, 215, 100)

SAVE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "save.json")

# ── PARTICLE ──────────────────────────────────────────────
class Particle:
    def __init__(self, x, y, color, size=None):
        self.x, self.y = x, y
        self.vx = random.uniform(-150, 150)
        self.vy = random.uniform(-150, 150)
        self.life = 0.5
        self.max_life = 0.5
        self.color = color
        self.size = size or random.randint(3, 6)
    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt
        self.size = max(1, self.size - 2 * dt)
    def draw(self, screen):
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), int(self.size))

# ── FLOATING TEXT ───────────────────────────────────────
class FloatingText:
    def __init__(self, x, y, text, color, size=20):
        self.x, self.y = x, y
        self.text = text
        self.color = color
        self.life = 1.2
        self.max_life = 1.2
        self.vy = -60
        self.vx = random.uniform(-20, 20)
        self.alpha = 255
        self.size = size
        self.font = pygame.font.SysFont("Segoe UI", size, bold=True)
    def update(self, dt):
        self.life -= dt
        self.y += self.vy * dt
        self.x += self.vx * dt
        self.alpha = int(255 * (self.life / self.max_life))
    def draw(self, screen):
        if self.alpha <= 0: return
        s = self.font.render(self.text, True, self.color)
        s.set_alpha(self.alpha)
        screen.blit(s, (int(self.x) - s.get_width()//2, int(self.y)))

# ── POWER-UP DROP ───────────────────────────────────────
class PowerUpDrop:
    def __init__(self, x, y, ptype):
        self.x, self.y = x, y
        self.type = ptype
        self.life = 8.0
        self.radius = 12
        self.time_ground = 0.0
        self.collected = False
    def update(self, dt):
        self.life -= dt
        if self.collected:
            self.x += (CENTER_X - self.x) * 5 * dt
            self.y += (CENTER_Y - self.y) * 5 * dt
            if math.hypot(self.x - CENTER_X, self.y - CENTER_Y) < 30:
                self.life = 0
        else:
            self.time_ground += dt
    def draw(self, screen):
        colors = {"damage":(255,100,100), "speed":(100,255,100), "heal":(255,100,200),
                  "gold":(255,215,0), "shield":(100,150,255)}
        c = colors.get(self.type, (200,200,200))
        pygame.draw.circle(screen, c, (int(self.x), int(self.y)), self.radius)
        pygame.draw.circle(screen, (255,255,255), (int(self.x), int(self.y)), self.radius, 2)

# ── ENEMY ───────────────────────────────────────────────
class Enemy:
    TYPES = {
        "basic":  {"hp":1.0, "speed":1.0, "r":12, "c":ENEMY_BASIC},
        "swarm":  {"hp":0.4, "speed":1.5, "r":8,  "c":ENEMY_SWARM},
        "tank":   {"hp":3.0, "speed":0.6, "r":16, "c":ENEMY_TANK},
        "healer": {"hp":0.8, "speed":1.0, "r":10, "c":ENEMY_HEAL},
        "bomber": {"hp":1.2, "speed":1.1, "r":14, "c":ENEMY_BOMB},
        "invis":  {"hp":0.9, "speed":1.2, "r":12, "c":ENEMY_INV},
    }
    def __init__(self, x, y, hp, speed, etype):
        self.x, self.y = x, y
        self.hp = hp
        self.max_hp = hp
        self.speed = speed
        self.type = etype
        t = self.TYPES[etype]
        self.radius = t["r"]
        self.color = t["c"]
        self.reached = False
        self.frozen = False
        self.death_timer = 0
        self.exploded = False
    def move_toward(self, tx, ty, dt):
        dx, dy = tx - self.x, ty - self.y
        dist = math.hypot(dx, dy)
        if dist > 0:
            s = self.speed * 60 * dt
            if self.frozen: s *= 0.2
            self.x += (dx/dist) * s
            self.y += (dy/dist) * s
        return dist
    def draw(self, screen):
        if self.death_timer > 0:
            a = int(255 * (self.death_timer / 0.3))
            r = int(self.radius * (1 + (0.3 - self.death_timer) * 3))
            surf = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
            pygame.draw.circle(surf, (255,255,255,a), (r,r), r)
            screen.blit(surf, (int(self.x)-r, int(self.y)-r))
            return
        c = (100,200,255) if self.frozen else self.color
        if self.type == "invis":
            if math.hypot(self.x - CENTER_X, self.y - CENTER_Y) > 120:
                c = (c[0]//3, c[1]//3, c[2]//3)
        if ENEMY_SHAPE == "square":
            s = self.radius * 2
            r = pygame.Rect(int(self.x)-s//2, int(self.y)-s//2, s, s)
            pygame.draw.rect(screen, c, r)
            pygame.draw.rect(screen, (255,255,255), r, 1)
        else:
            pygame.draw.circle(screen, c, (int(self.x), int(self.y)), self.radius)
            pygame.draw.circle(screen, (255,255,255), (int(self.x), int(self.y)), self.radius, 1)
        # HP bar
        pct = self.hp / self.max_hp
        w = self.radius * 2
        yb = int(self.y) - self.radius - 6
        pygame.draw.rect(screen, HP_BG, (int(self.x)-w//2, yb, w, 3))
        pygame.draw.rect(screen, HP_FG, (int(self.x)-w//2, yb, int(w*pct), 3))

# ── PROJECTILE ──────────────────────────────────────────
class Projectile:
    def __init__(self, x, y, target, damage):
        self.x, self.y = x, y
        self.target = target
        self.damage = damage
        self.speed = 400
        self.active = True
        self.radius = 4
        self.pierce = 0
    def update(self, dt):
        if not self.active or not self.target or self.target.hp <= 0:
            self.active = False
            return
        dx, dy = self.target.x - self.x, self.target.y - self.y
        dist = math.hypot(dx, dy)
        if dist < 10:
            self.target.hp -= self.damage
            self.active = False
            if self.target.hp <= 0 and not self.target.reached:
                self.target.reached = True
                self.target.death_timer = 0.3
                # Award gold and show floating text
                g = int((5 + state.wave) * state.gold_per_kill)
                state.gold += g
                if state.life_steal > 0:
                    state.tower_hp = min(state.tower_hp + state.life_steal * 2, state.tower_max_hp)
                for _ in range(8):
                    state.particles.append(Particle(self.target.x, self.target.y, GOLD))
                state.floating.append(FloatingText(self.target.x, self.target.y, f"+${g}", GOLD, 22))
                if random.random() < 0.1:
                    drop_type = random.choice(["heal", "gold", "damage", "speed", "shield"])
                    state.drops.append(PowerUpDrop(self.target.x, self.target.y, drop_type))
        else:
            self.x += (dx/dist) * self.speed * dt
            self.y += (dy/dist) * self.speed * dt
    def draw(self, screen):
        pygame.draw.circle(screen, PROJ, (int(self.x), int(self.y)), self.radius)

# ── TURRET ──────────────────────────────────────────────
class Turret:
    def __init__(self, orbit_index, total_turrets):
        self.orbit_index = orbit_index
        self.total_turrets = total_turrets
        self.orbit_angle = (360 / total_turrets) * orbit_index
        self.orbit_radius = 120
        self.orbit_speed = 30 + random.uniform(-5, 5)
        self.x = CENTER_X + math.cos(math.radians(self.orbit_angle)) * self.orbit_radius
        self.y = CENTER_Y + math.sin(math.radians(self.orbit_angle)) * self.orbit_radius
        self.damage = 5
        self.range = 150
        self.fire_rate = 0.8
        self.last_shot = 0
        self.hp = 50
        self.max_hp = 50
    def update(self, dt, enemies, state):
        self.orbit_angle += self.orbit_speed * dt
        self.x = CENTER_X + math.cos(math.radians(self.orbit_angle)) * self.orbit_radius
        self.y = CENTER_Y + math.sin(math.radians(self.orbit_angle)) * self.orbit_radius
        now = time.time()
        if now - self.last_shot < self.fire_rate: return
        targets = []
        for e in enemies:
            if e.hp > 0 and not e.reached and math.hypot(e.x-self.x, e.y-self.y) <= self.range:
                targets.append((math.hypot(e.x-self.x, e.y-self.y), e))
        if targets:
            targets.sort(key=lambda x: x[0])
            state.projectiles.append(Projectile(self.x, self.y, targets[0][1], self.damage))
            self.last_shot = now
    def draw(self, screen):
        pygame.draw.circle(screen, (40, 50, 40), (CENTER_X, CENTER_Y), self.orbit_radius, 1)
        pygame.draw.rect(screen, (100,180,100), (int(self.x)-8, int(self.y)-8, 16, 16))
        pygame.draw.rect(screen, (150,220,150), (int(self.x)-8, int(self.y)-8, 16, 16), 2)
        pct = self.hp / self.max_hp
        pygame.draw.rect(screen, HP_BG, (int(self.x)-10, int(self.y)-14, 20, 3))
        pygame.draw.rect(screen, HP_FG, (int(self.x)-10, int(self.y)-14, int(20*pct), 3))
# ── GAME STATE ──────────────────────────────────────────
class GameState:
    def __init__(self):
        self.prestige_level = 0
        self.prestige_dmg = 1.0
        self.prestige_gold = 1.0
        self.highest_wave = 0
        self.reset()
        self.load()
    def reset(self):
        self.gold = int(100 * self.prestige_gold)
        self.wave = 1
        self.wave_active = False
        self.wave_enemies = 0
        self.wave_spawn = 0
        self.wave_cd = 0
        self.wave_popup = None
        self.tower_hp = 100
        self.tower_max_hp = 100
        self.enemies = []
        self.projectiles = []
        self.particles = []
        self.floating = []
        self.drops = []
        self.game_over = False
        self.paused = False
        self.last_shot = 0
        self.shake = 0
        self.turrets = []
        self.boss_active = False
        # Stats
        self.damage = 10 * self.prestige_dmg
        self.fire_rate = 1.0
        self.range_r = 250
        self.multishot = 1
        self.crit_chance = 0.05
        self.crit_mult = 2.0
        # Costs
        self.c_dmg = 50; self.c_speed = 60; self.c_range = 40; self.c_multi = 500
        self.c_critc = 80; self.c_critm = 100; self.c_hp = 30; self.c_turret = 150
        # Powerups
        self.dmg_boost = 1.0
        self.spd_boost = 1.0
        self.life_steal = 0
        self.pierce = 0
        self.has_shield = False
        self.magnet = 0
        self.magnet_cost = 200
        # Gold upgrades
        self.gold_per_kill = 1.0
        self.gold_per_wave = 1.0
        self.c_gkill = 100
        self.c_gwave = 150
        # Abilities
        self.abilities = {
            "bomb":   {"cd":0, "max":15, "ready":True, "icon":"💣"},
            "heal":   {"cd":0, "max":20, "ready":True, "icon":"💖"},
            "freeze": {"cd":0, "max":25, "ready":True, "icon":"❄️"},
            "rage":   {"cd":0, "max":30, "ready":True, "icon":"🔥"},
            "vacuum": {"cd":0, "max":30, "ready":True, "icon":"🧲"},
            "missile":{"cd":0, "max":45, "ready":True, "icon":"💥"},
        }
        self.rage_timer = 0
        self.freeze_timer = 0
        self.missile_target = None
        self.missile_boom = False
        self.missile_r = 0
    def fire_cd(self):
        cd = 1.0 / (self.fire_rate * self.spd_boost)
        if self.rage_timer > 0: cd *= 0.5
        return cd
    def total_dmg(self):
        d = self.damage * self.dmg_boost
        if self.rage_timer > 0: d *= 2
        return d
    def start_wave(self):
        self.wave_active = True
        if self.wave % 5 == 0:
            self.boss_active = True
            self.wave_enemies = 1
            self.wave_popup = {"text": f"BOSS WAVE {self.wave}", "life": 3.0, "max": 3.0}
        else:
            self.boss_active = False
            self.wave_enemies = 10 + self.wave * 3
            self.wave_popup = {"text": f"WAVE {self.wave}", "life": 2.0, "max": 2.0}
        self.wave_spawn = 0
        self.wave_cd = 0
    def enemy_hp(self):
        base = 10 + self.wave * 2
        if self.boss_active: base *= 10
        return base
    def enemy_spd(self):
        s = 1.0 + self.wave * 0.05
        if self.freeze_timer > 0: s *= 0.2
        return s
    def do_prestige(self):
        if self.wave >= 10:
            self.prestige_level += 1
            self.prestige_dmg = 1.0 + self.prestige_level * 0.2
            self.prestige_gold = 1.0 + self.prestige_level * 0.1
            self.highest_wave = max(self.highest_wave, self.wave - 1)
            self.reset()
            return True
        return False
    # Upgrades
    def up_dmg(self):
        if self.gold >= self.c_dmg:
            self.gold -= self.c_dmg; self.damage += 5; self.c_dmg = int(self.c_dmg * 1.4); return True
        return False
    def up_speed(self):
        if self.gold >= self.c_speed:
            self.gold -= self.c_speed; self.fire_rate += 0.3; self.c_speed = int(self.c_speed * 1.5); return True
        return False
    def up_range(self):
        if self.gold >= self.c_range:
            self.gold -= self.c_range; self.range_r += 30; self.c_range = int(self.c_range * 1.35); return True
        return False
    def up_multi(self):
        if self.gold >= self.c_multi and self.multishot < 4:
            self.gold -= self.c_multi; self.multishot += 1; self.c_multi = int(self.c_multi * 3); return True
        return False
    def up_critc(self):
        if self.gold >= self.c_critc and self.crit_chance < 0.5:
            self.gold -= self.c_critc; self.crit_chance = min(0.5, self.crit_chance + 0.03); self.c_critc = int(self.c_critc * 1.45); return True
        return False
    def up_critm(self):
        if self.gold >= self.c_critm and self.crit_mult < 5.0:
            self.gold -= self.c_critm; self.crit_mult += 0.3; self.c_critm = int(self.c_critm * 1.4); return True
        return False
    def up_hp(self):
        if self.gold >= self.c_hp:
            self.gold -= self.c_hp; self.tower_max_hp += 20; self.tower_hp = min(self.tower_hp + 30, self.tower_max_hp); self.c_hp = int(self.c_hp * 1.3); return True
        return False
    def buy_turret(self):
        if self.gold >= self.c_turret and len(self.turrets) < 4:
            self.gold -= self.c_turret
            self.turrets.append(Turret(len(self.turrets), len(self.turrets) + 1))
            self.c_turret = int(self.c_turret * 1.5)
            return True
        return False
    def buy_dmg_boost(self):
        c = 300 * int(self.dmg_boost)
        if self.gold >= c and self.dmg_boost < 3.0:
            self.gold -= c; self.dmg_boost += 0.5; return True
        return False
    def buy_spd_boost(self):
        c = 350 * int(self.spd_boost)
        if self.gold >= c and self.spd_boost < 3.0:
            self.gold -= c; self.spd_boost += 0.5; return True
        return False
    def buy_lifesteal(self):
        c = 400 + self.life_steal * 300
        if self.gold >= c and self.life_steal < 5:
            self.gold -= c; self.life_steal += 1; return True
        return False
    def buy_pierce(self):
        c = 500 + self.pierce * 400
        if self.gold >= c and self.pierce < 3:
            self.gold -= c; self.pierce += 1; return True
        return False
    def buy_shield(self):
        if self.gold >= 250 and not self.has_shield:
            self.gold -= 250; self.has_shield = True; return True
        return False
    def buy_magnet(self):
        if self.gold >= self.magnet_cost and self.magnet < 4:
            self.gold -= self.magnet_cost; self.magnet += 1; self.magnet_cost = int(self.magnet_cost * 1.8); return True
        return False
    def buy_gkill(self):
        if self.gold >= self.c_gkill and self.gold_per_kill < 5.0:
            self.gold -= self.c_gkill; self.gold_per_kill += 0.5; self.c_gkill = int(self.c_gkill * 1.5); return True
        return False
    def buy_gwave(self):
        if self.gold >= self.c_gwave and self.gold_per_wave < 3.0:
            self.gold -= self.c_gwave; self.gold_per_wave += 0.3; self.c_gwave = int(self.c_gwave * 1.6); return True
        return False
    def magnet_delay(self):
        return {0:None, 1:1.0, 2:0.5, 3:0.2, 4:0.0}.get(self.magnet, None)
    # Abilities
    def use_bomb(self):
        ab = self.abilities["bomb"]
        if ab["ready"] and self.enemies:
            ab["ready"] = False; ab["cd"] = ab["max"]
            k = 0
            for e in self.enemies:
                e.hp = 0; e.death_timer = 0.3; k += 1
                for _ in range(5): self.particles.append(Particle(e.x, e.y, (255,200,50)))
            self.shake = 0.3
            return k
        return 0
    def use_heal(self):
        ab = self.abilities["heal"]
        if ab["ready"] and self.tower_hp < self.tower_max_hp:
            ab["ready"] = False; ab["cd"] = ab["max"]
            h = min(self.tower_max_hp - self.tower_hp, self.tower_max_hp * 0.4)
            self.tower_hp += h; return h
        return 0
    def use_freeze(self):
        ab = self.abilities["freeze"]
        if ab["ready"]:
            ab["ready"] = False; ab["cd"] = ab["max"]; self.freeze_timer = 5.0
            for e in self.enemies: e.frozen = True
            return True
        return False
    def use_rage(self):
        ab = self.abilities["rage"]
        if ab["ready"]:
            ab["ready"] = False; ab["cd"] = ab["max"]; self.rage_timer = 8.0; return True
        return False
    def use_vacuum(self):
        ab = self.abilities["vacuum"]
        if ab["ready"]:
            ab["ready"] = False; ab["cd"] = ab["max"]
            c = 0
            for drop in self.drops[:]:
                self._apply_drop(drop); self.drops.remove(drop); c += 1
            return c
        return 0
    def _apply_drop(self, drop):
        if drop.type == "heal":
            h = min(self.tower_max_hp - self.tower_hp, 25)
            self.tower_hp += h
            self.floating.append(FloatingText(drop.x, drop.y, f"+{int(h)} HP", (255,100,200), 20))
        elif drop.type == "gold":
            g = int((25 + self.wave * 5) * self.gold_per_kill)
            self.gold += g
            self.floating.append(FloatingText(drop.x, drop.y, f"+${g}", GOLD, 22))
        elif drop.type == "damage":
            self.damage += 3
            self.floating.append(FloatingText(drop.x, drop.y, "+3 DMG!", (255,100,100), 20))
        elif drop.type == "speed":
            self.fire_rate += 0.2
            self.floating.append(FloatingText(drop.x, drop.y, "+SPD!", (100,255,100), 20))
        elif drop.type == "shield":
            self.has_shield = True
            self.floating.append(FloatingText(drop.x, drop.y, "SHIELD!", (100,150,255), 20))
    def use_missile(self, mx, my):
        ab = self.abilities["missile"]
        if ab["ready"]:
            ab["ready"] = False; ab["cd"] = ab["max"]
            self.missile_target = (mx, my); self.missile_boom = True; self.missile_r = 0
            self.shake = 0.5; return True
        return False
    def update_missile(self, dt):
        if not self.missile_boom: return False
        self.missile_r += 300 * dt
        if self.missile_r >= 120:
            self.missile_boom = False; self.missile_r = 0
            if self.missile_target:
                mx, my = self.missile_target
                for e in self.enemies:
                    if math.hypot(e.x - mx, e.y - my) < 120:
                        e.hp -= self.total_dmg() * 3
                        if e.hp <= 0 and not e.reached:
                            e.reached = True; e.death_timer = 0.3
            return True
        return False
    # Save/Load
    def save(self):
        data = {
            "prestige_level": self.prestige_level, "prestige_dmg": self.prestige_dmg,
            "prestige_gold": self.prestige_gold, "highest_wave": self.highest_wave,
            "gold": self.gold, "wave": self.wave, "damage": self.damage,
            "fire_rate": self.fire_rate, "range_r": self.range_r, "multishot": self.multishot,
            "crit_chance": self.crit_chance, "crit_mult": self.crit_mult,
            "tower_hp": self.tower_hp, "tower_max_hp": self.tower_max_hp,
            "dmg_boost": self.dmg_boost, "spd_boost": self.spd_boost,
            "life_steal": self.life_steal, "pierce": self.pierce,
            "has_shield": self.has_shield, "magnet": self.magnet,
            "magnet_cost": self.magnet_cost, "gold_per_kill": self.gold_per_kill,
            "gold_per_wave": self.gold_per_wave, "c_gkill": self.c_gkill, "c_gwave": self.c_gwave,
            "c_dmg": self.c_dmg, "c_speed": self.c_speed, "c_range": self.c_range,
            "c_multi": self.c_multi, "c_critc": self.c_critc, "c_critm": self.c_critm,
            "c_hp": self.c_hp, "c_turret": self.c_turret,
        }
        try:
            with open(SAVE_FILE, 'w') as f: json.dump(data, f); return True
        except: return False
    def load(self):
        try:
            if not os.path.exists(SAVE_FILE): return False
            with open(SAVE_FILE, 'r') as f: d = json.load(f)
            self.prestige_level = d.get("prestige_level", 0)
            self.prestige_dmg = d.get("prestige_dmg", 1.0)
            self.prestige_gold = d.get("prestige_gold", 1.0)
            self.highest_wave = d.get("highest_wave", 0)
            self.gold = d.get("gold", int(100 * self.prestige_gold))
            self.wave = d.get("wave", 1)
            self.damage = d.get("damage", 10 * self.prestige_dmg)
            self.fire_rate = d.get("fire_rate", 1.0)
            self.range_r = d.get("range_r", 250)
            self.multishot = d.get("multishot", 1)
            self.crit_chance = d.get("crit_chance", 0.05)
            self.crit_mult = d.get("crit_mult", 2.0)
            self.tower_hp = d.get("tower_hp", 100)
            self.tower_max_hp = d.get("tower_max_hp", 100)
            self.dmg_boost = d.get("dmg_boost", 1.0)
            self.spd_boost = d.get("spd_boost", 1.0)
            self.life_steal = d.get("life_steal", 0)
            self.pierce = d.get("pierce", 0)
            self.has_shield = d.get("has_shield", False)
            self.magnet = d.get("magnet", 0)
            self.magnet_cost = d.get("magnet_cost", 200)
            self.gold_per_kill = d.get("gold_per_kill", 1.0)
            self.gold_per_wave = d.get("gold_per_wave", 1.0)
            self.c_gkill = d.get("c_gkill", 100)
            self.c_gwave = d.get("c_gwave", 150)
            self.c_dmg = d.get("c_dmg", 50)
            self.c_speed = d.get("c_speed", 60)
            self.c_range = d.get("c_range", 40)
            self.c_multi = d.get("c_multi", 500)
            self.c_critc = d.get("c_critc", 80)
            self.c_critm = d.get("c_critm", 100)
            self.c_hp = d.get("c_hp", 30)
            self.c_turret = d.get("c_turret", 150)
            return True
        except: return False
# ── DRAWING FUNCTIONS ───────────────────────────────────
def draw_tower(screen, state):
    r = 20 + state.multishot * 3
    if state.has_shield:
        pygame.draw.circle(screen, (100,150,255), (CENTER_X, CENTER_Y), r+8, 2)
    if TOWER_SHAPE == "hexagon":
        pts = [(CENTER_X + math.cos(math.radians(i*60-30))*r, CENTER_Y + math.sin(math.radians(i*60-30))*r) for i in range(6)]
        c = (255,80,80) if state.rage_timer > 0 else TOWER_C
        pygame.draw.polygon(screen, c, pts)
        pygame.draw.polygon(screen, TOWER_OUT, pts, 2)
    else:
        c = (255,80,80) if state.rage_timer > 0 else TOWER_C
        pygame.draw.circle(screen, c, (CENTER_X, CENTER_Y), r)
        pygame.draw.circle(screen, TOWER_OUT, (CENTER_X, CENTER_Y), r, 2)
    if SHOW_RANGE:
        pygame.draw.circle(screen, (100,150,255), (CENTER_X, CENTER_Y), int(state.range_r), 1)
    for i in range(state.multishot):
        a = (i / state.multishot) * 360 + time.time() * 20
        ex = CENTER_X + math.cos(math.radians(a)) * (r+8)
        ey = CENTER_Y + math.sin(math.radians(a)) * (r+8)
        pygame.draw.line(screen, TOWER_GUN, (CENTER_X, CENTER_Y), (ex, ey), 4)

def draw_upgrade_tab(screen, font, state, active_tab):
    # Tab buttons
    tabs = [("OFFENCE", 0), ("DEFENCE", 1), ("UTILITY", 2)]
    tab_w = 80
    tab_x = 750
    tab_y = 60
    for name, idx in tabs:
        color = TAB_OFF if idx == 0 else (TAB_DEF if idx == 1 else TAB_UTL)
        bg = color if active_tab == idx else (40, 40, 50)
        rect = pygame.Rect(tab_x, tab_y, tab_w, 28)
        pygame.draw.rect(screen, bg, rect, border_radius=4)
        pygame.draw.rect(screen, PANEL_BDR, rect, 1, border_radius=4)
        t = font.render(name, True, TEXT if active_tab == idx else TEXT_DIM)
        screen.blit(t, (tab_x + tab_w//2 - t.get_width()//2, tab_y + 5))
        tab_x += tab_w + 5

    # Panel background
    panel_x = 750
    panel_y = 90
    panel_w = 240
    panel_h = 400
    pygame.draw.rect(screen, PANEL_BG, (panel_x, panel_y, panel_w, panel_h), border_radius=8)
    pygame.draw.rect(screen, PANEL_BDR, (panel_x, panel_y, panel_w, panel_h), 2, border_radius=8)

    clickable = []
    y = panel_y + 15
    row_h = 50

    if active_tab == 0:  # OFFENCE
        upgrades = [
            (f"Damage ({state.damage:.0f})", "+5", state.c_dmg, state.up_dmg),
            (f"Fire Rate ({state.fire_rate:.1f}/s)", "+0.3", state.c_speed, state.up_speed),
            (f"Range ({state.range_r:.0f})", "+30", state.c_range, state.up_range),
            (f"Multi-shot ({state.multishot})", "+1", state.c_multi, state.up_multi),
            (f"Crit Chance ({state.crit_chance*100:.0f}%)", "+3%", state.c_critc, state.up_critc),
            (f"Crit Mult ({state.crit_mult:.1f}x)", "+0.3x", state.c_critm, state.up_critm),
        ]
        for name, desc, cost, fn in upgrades:
            is_maxed = ("Multi-shot" in name and state.multishot >= 4) or \
                       ("Crit Chance" in name and state.crit_chance >= 0.5) or \
                       ("Crit Mult" in name and state.crit_mult >= 5.0)
            color = BTN_MAXED if is_maxed else BTN
            rect = pygame.Rect(panel_x + 10, y, panel_w - 20, row_h - 5)
            pygame.draw.rect(screen, color, rect, border_radius=5)
            pygame.draw.rect(screen, PANEL_BDR, rect, 1, border_radius=5)
            screen.blit(font.render(name, True, TEXT), (panel_x + 18, y + 3))
            cost_color = GOLD if state.gold >= cost else (150, 120, 80)
            screen.blit(font.render(f"💰{cost}", True, cost_color), (panel_x + 18, y + 22))
            if not is_maxed:
                clickable.append((rect, fn))
            y += row_h
    elif active_tab == 1:  # DEFENCE
        upgrades = [
            (f"Tower HP ({state.tower_hp:.0f}/{state.tower_max_hp})", "+20", state.c_hp, state.up_hp),
            (f"Shield", "Active" if state.has_shield else "Buy", 250, state.buy_shield),
        ]
        for name, desc, cost, fn in upgrades:
            is_maxed = "Shield" in name and state.has_shield
            color = BTN_MAXED if is_maxed else BTN
            rect = pygame.Rect(panel_x + 10, y, panel_w - 20, row_h - 5)
            pygame.draw.rect(screen, color, rect, border_radius=5)
            pygame.draw.rect(screen, PANEL_BDR, rect, 1, border_radius=5)
            screen.blit(font.render(name, True, TEXT), (panel_x + 18, y + 3))
            cost_color = GOLD if state.gold >= cost else (150, 120, 80)
            screen.blit(font.render(f"💰{cost}", True, cost_color), (panel_x + 18, y + 22))
            if not is_maxed:
                clickable.append((rect, fn))
            y += row_h
    else:  # UTILITY
        upgrades = [
            (f"Gold/Kill ({state.gold_per_kill:.1f}x)", "+0.5x", state.c_gkill, state.buy_gkill),
            (f"Gold/Wave ({state.gold_per_wave:.1f}x)", "+0.3x", state.c_gwave, state.buy_gwave),
            (f"Magnet (Lv{state.magnet})", "Lv up", state.magnet_cost, state.buy_magnet),
            (f"Life Steal (+{state.life_steal})", "+1", 400 + state.life_steal * 300, state.buy_lifesteal),
            (f"Turret ({len(state.turrets)}/4)", "New", state.c_turret, state.buy_turret),
        ]
        for name, desc, cost, fn in upgrades:
            is_maxed = ("Magnet" in name and state.magnet >= 4) or \
                       ("Turret" in name and len(state.turrets) >= 4) or \
                       ("Life Steal" in name and state.life_steal >= 5) or \
                       ("Gold/Kill" in name and state.gold_per_kill >= 5.0) or \
                       ("Gold/Wave" in name and state.gold_per_wave >= 3.0)
            color = BTN_MAXED if is_maxed else BTN
            rect = pygame.Rect(panel_x + 10, y, panel_w - 20, row_h - 5)
            pygame.draw.rect(screen, color, rect, border_radius=5)
            pygame.draw.rect(screen, PANEL_BDR, rect, 1, border_radius=5)
            screen.blit(font.render(name, True, TEXT), (panel_x + 18, y + 3))
            cost_color = GOLD if state.gold >= cost else (150, 120, 80)
            screen.blit(font.render(f"💰{cost}", True, cost_color), (panel_x + 18, y + 22))
            if not is_maxed:
                clickable.append((rect, fn))
            y += row_h

    return clickable

def draw_ability_bar(screen, font, state):
    bar_y = 60
    btn_size = 45
    gap = 8
    bar_x = 10
    abilities = [("1","bomb"), ("2","heal"), ("3","freeze"), ("4","rage"), ("5","vacuum"), ("6","missile")]
    for key, name in abilities:
        ab = state.abilities[name]
        rect = pygame.Rect(bar_x, bar_y, btn_size, btn_size)
        if ab["ready"]:
            pygame.draw.rect(screen, (60,100,60), rect, border_radius=5)
        else:
            pygame.draw.rect(screen, (60,60,60), rect, border_radius=5)
            pct = ab["cd"] / ab["max"]
            overlay_h = int(btn_size * pct)
            pygame.draw.rect(screen, (40,40,40), (bar_x, bar_y, btn_size, overlay_h), border_radius=5)
        pygame.draw.rect(screen, PANEL_BDR, rect, 2, border_radius=5)
        icon_font = pygame.font.SysFont("Segoe UI", 20)
        icon = icon_font.render(ab["icon"], True, TEXT)
        screen.blit(icon, (bar_x + btn_size//2 - icon.get_width()//2, bar_y + 5))
        screen.blit(font.render(key, True, TEXT_DIM), (bar_x + 3, bar_y + btn_size - 16))
        if not ab["ready"]:
            cd_text = font.render(f"{ab['cd']:.0f}", True, (255,100,100))
            screen.blit(cd_text, (bar_x + btn_size - cd_text.get_width() - 3, bar_y + btn_size - 16))
        bar_x += btn_size + gap
    return []

def draw_active_effects(screen, font, state):
    effects = []
    if state.rage_timer > 0:
        effects.append(("RAGE", state.rage_timer, (255,80,80)))
    if state.freeze_timer > 0:
        effects.append(("FREEZE", state.freeze_timer, (100,200,255)))
    x = 10
    y = 120
    for name, timer, color in effects:
        text = font.render(f"{name}: {timer:.1f}s", True, color)
        screen.blit(text, (x, y))
        y += 20

def draw_top_bar(screen, font, state):
    bar_h = 50
    pygame.draw.rect(screen, (20,25,40), (0, 0, WIDTH, bar_h))
    pygame.draw.line(screen, PANEL_BDR, (0, bar_h), (WIDTH, bar_h), 2)
    screen.blit(font.render(f"💰{state.gold}", True, GOLD), (15, 8))
    screen.blit(font.render(f"Wave {state.wave}", True, TEXT), (15, 26))
    hp_pct = state.tower_hp / state.tower_max_hp
    hp_bar_w, hp_bar_h = 180, 18
    hp_bar_x = WIDTH // 2 - hp_bar_w // 2
    pygame.draw.rect(screen, HP_BG, (hp_bar_x, 14, hp_bar_w, hp_bar_h))
    hp_color = HP_RED if hp_pct < 0.3 else HP_FG
    pygame.draw.rect(screen, hp_color, (hp_bar_x, 14, int(hp_bar_w * hp_pct), hp_bar_h))
    hp_text = font.render(f"{int(state.tower_hp)}/{state.tower_max_hp}", True, TEXT)
    screen.blit(hp_text, (hp_bar_x + hp_bar_w//2 - hp_text.get_width()//2, 13))
    if state.wave_active:
        status = font.render("⚔️ ACTIVE" + (" BOSS!" if state.boss_active else ""), True, (255,100,100))
    else:
        cd = max(0, state.wave_cd)
        status = font.render(f"Next: {cd:.1f}s", True, (100,255,100))
    screen.blit(status, (WIDTH - status.get_width() - 20, 14))
    if state.prestige_level > 0:
        prestige_text = font.render(f"P{state.prestige_level}", True, (255,200,100))
        screen.blit(prestige_text, (WIDTH - prestige_text.get_width() - 20, 30))

def draw_boss_hp_bar(screen, font, state):
    if not state.boss_active or not state.enemies:
        return
    boss = None
    for e in state.enemies:
        if e.hp > 0:
            boss = e
            break
    if not boss:
        return
    bar_w = 300
    bar_h = 20
    bar_x = WIDTH // 2 - bar_w // 2
    bar_y = 80
    hp_pct = boss.hp / boss.max_hp
    pygame.draw.rect(screen, (60, 0, 0), (bar_x, bar_y, bar_w, bar_h))
    pygame.draw.rect(screen, (220, 50, 50), (bar_x, bar_y, int(bar_w * hp_pct), bar_h))
    pygame.draw.rect(screen, (255, 100, 100), (bar_x, bar_y, bar_w, bar_h), 2)
    name_text = font.render(f"BOSS WAVE {state.wave}", True, (255, 100, 100))
    screen.blit(name_text, (bar_x + bar_w//2 - name_text.get_width()//2, bar_y - 18))

# ── SPAWN ENEMY ─────────────────────────────────────────
def spawn_enemy(state):
    edge = random.choice(["top", "bottom", "left", "right"])
    if edge == "top":
        x, y = random.randint(50, 700), -20
    elif edge == "bottom":
        x, y = random.randint(50, 700), HEIGHT + 20
    elif edge == "left":
        x, y = -20, random.randint(50, HEIGHT - 50)
    else:
        x, y = 720, random.randint(50, HEIGHT - 50)
    if state.boss_active:
        return Enemy(x, y, state.enemy_hp(), state.enemy_spd(), "tank")
    r = random.random()
    if r < 0.35:
        etype, hp_mult, spd_mult = "basic", 1.0, 1.0
    elif r < 0.55:
        etype, hp_mult, spd_mult = "swarm", 0.5, 1.5
    elif r < 0.75:
        etype, hp_mult, spd_mult = "tank", 3.0, 0.6
    elif r < 0.85:
        etype, hp_mult, spd_mult = "healer", 0.8, 1.0
    elif r < 0.93:
        etype, hp_mult, spd_mult = "bomber", 1.2, 1.1
    else:
        etype, hp_mult, spd_mult = "invis", 0.9, 1.2
    return Enemy(x, y, state.enemy_hp() * hp_mult, state.enemy_spd() * spd_mult, etype)
# ── MAIN ────────────────────────────────────────────────
def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("The Tower 💎")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("Segoe UI", 16)
    font_lg = pygame.font.SysFont("Segoe UI", 36, bold=True)
    font_sm = pygame.font.SysFont("Segoe UI", 14)

    state = GameState()
    upgrade_buttons = []
    active_tab = 0  # 0=Offence, 1=Defence, 2=Utility
    running = True

    while running:
        dt = clock.tick(60) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                state.save()
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    state.paused = not state.paused
                if event.key == pygame.K_SPACE and not state.wave_active and not state.game_over:
                    state.start_wave()
                if event.key == pygame.K_r and state.game_over:
                    state.reset()
                if event.key == pygame.K_p and state.game_over:
                    if state.do_prestige():
                        state.floating.append(FloatingText(CENTER_X, CENTER_Y, "PRESTIGE!", (255, 200, 100), 32))
                if event.key == pygame.K_s:
                    state.save()
                    state.floating.append(FloatingText(CENTER_X, CENTER_Y, "SAVED!", (100, 255, 100), 24))
                if event.key == pygame.K_TAB:
                    active_tab = (active_tab + 1) % 3
                if not state.paused and not state.game_over:
                    if event.key == pygame.K_1:
                        kills = state.use_bomb()
                        if kills > 0:
                            state.floating.append(FloatingText(CENTER_X, CENTER_Y, f"BOOM! {kills} kills", (255, 200, 50), 30))
                    if event.key == pygame.K_2:
                        heal = state.use_heal()
                        if heal > 0:
                            state.floating.append(FloatingText(CENTER_X, CENTER_Y - 30, f"+{int(heal)} HP", (100, 255, 100), 24))
                    if event.key == pygame.K_3:
                        if state.use_freeze():
                            state.floating.append(FloatingText(CENTER_X, CENTER_Y, "FREEZE!", (100, 200, 255), 30))
                    if event.key == pygame.K_4:
                        if state.use_rage():
                            state.floating.append(FloatingText(CENTER_X, CENTER_Y, "RAGE MODE!", (255, 80, 80), 32))
                    if event.key == pygame.K_5:
                        count = state.use_vacuum()
                        if count > 0:
                            state.floating.append(FloatingText(CENTER_X, CENTER_Y, f"🧲 VACUUM: {count} items!", (255, 100, 255), 28))
                    if event.key == pygame.K_6:
                        state.floating.append(FloatingText(CENTER_X, CENTER_Y, "CLICK TARGET!", (255, 200, 100), 24))
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if state.game_over:
                    state.reset()
                    continue
                mx, my = pygame.mouse.get_pos()
                # Missile target
                if state.missile_target is not None and state.abilities["missile"]["ready"]:
                    state.use_missile(mx, my)
                    continue
                # Tab switching
                tab_w = 80
                tab_x = 750
                tab_y = 60
                for idx in range(3):
                    rect = pygame.Rect(tab_x, tab_y, tab_w, 28)
                    if rect.collidepoint(mx, my):
                        active_tab = idx
                        break
                    tab_x += tab_w + 5
                # Upgrade buttons
                for btn_rect, fn in upgrade_buttons:
                    if btn_rect.collidepoint(mx, my):
                        if fn():
                            state.floating.append(FloatingText(mx, my, "UPGRADED!", (100, 255, 100), 20))
                        break
                # Drops
                for drop in state.drops[:]:
                    if math.hypot(drop.x - mx, drop.y - my) < drop.radius + 10:
                        state._apply_drop(drop)
                        state.drops.remove(drop)
                        break

        # Auto-start next wave
        if not state.wave_active and not state.game_over and state.wave_cd > 0:
            state.wave_cd -= dt
            if state.wave_cd <= 0:
                state.start_wave()

        # Main game logic
        if not state.paused and not state.game_over:
            if state.rage_timer > 0:
                state.rage_timer -= dt
            if state.freeze_timer > 0:
                state.freeze_timer -= dt
                if state.freeze_timer <= 0:
                    for e in state.enemies:
                        e.frozen = False

            for ab in state.abilities.values():
                if not ab["ready"]:
                    ab["cd"] -= dt
                    if ab["cd"] <= 0:
                        ab["ready"] = True
                        ab["cd"] = 0

            state.update_missile(dt)

            if state.shake > 0:
                state.shake -= dt
                if state.shake < 0:
                    state.shake = 0

            # Tower shooting
            now = time.time()
            if now - state.last_shot >= state.fire_cd():
                targets = []
                for e in state.enemies:
                    dist = math.hypot(e.x - CENTER_X, e.y - CENTER_Y)
                    if dist <= state.range_r and e.hp > 0 and not e.reached:
                        targets.append((dist, e))
                if targets:
                    targets.sort(key=lambda x: x[0])
                    state.last_shot = now
                    for i in range(min(state.multishot, len(targets))):
                        target = targets[i][1]
                        is_crit = random.random() < state.crit_chance
                        dmg = state.total_dmg() * (state.crit_mult if is_crit else 1.0)
                        proj = Projectile(CENTER_X, CENTER_Y, target, dmg)
                        proj.pierce = state.pierce
                        state.projectiles.append(proj)

            # Turret shooting
            for turret in state.turrets:
                turret.update(dt, state.enemies, state)

            # Spawn enemies
            if state.wave_active:
                state.wave_spawn -= dt
                if state.wave_spawn <= 0 and state.wave_enemies > 0:
                    state.enemies.append(spawn_enemy(state))
                    state.wave_enemies -= 1
                    state.wave_spawn = max(0.2, 1.0 - state.wave * 0.03)

                if state.wave_enemies <= 0 and len(state.enemies) == 0:
                    state.wave_active = False
                    state.boss_active = False
                    state.wave += 1
                    state.gold += int((50 + state.wave * 10) * state.gold_per_wave)
                    state.wave_cd = 3.0
                    state.highest_wave = max(state.highest_wave, state.wave - 1)

            # Update enemies
            for e in state.enemies[:]:
                if e.death_timer > 0:
                    e.death_timer -= dt
                    if e.death_timer <= 0:
                        e.hp = 0
                        state.enemies.remove(e)
                    continue

                dist = e.move_toward(CENTER_X, CENTER_Y, dt)
                if dist < 25:
                    # Bomber explodes
                    if e.type == "bomber":
                        e.exploded = True
                        state.shake = 0.4
                        for other in state.enemies:
                            if other != e and math.hypot(other.x - e.x, other.y - e.y) < 60:
                                other.hp -= 20
                                if other.hp <= 0:
                                    other.death_timer = 0.3
                        for turret in state.turrets:
                            if math.hypot(turret.x - e.x, turret.y - e.y) < 60:
                                turret.hp -= 15
                        state.tower_hp -= 15
                        state.floating.append(FloatingText(CENTER_X, CENTER_Y - 20, "-15", (255, 50, 50), 24))

                    if e.hp > 0:
                        e.hp = 0
                        if state.has_shield:
                            state.has_shield = False
                            state.floating.append(FloatingText(CENTER_X, CENTER_Y, "SHIELD BROKEN!", (100, 150, 255), 24))
                            for _ in range(10):
                                state.particles.append(Particle(CENTER_X, CENTER_Y, (100, 150, 255)))
                        else:
                            state.tower_hp -= 10
                            state.floating.append(FloatingText(CENTER_X, CENTER_Y - 20, "-10", (255, 50, 50), 20))
                            if state.tower_hp <= 0:
                                state.tower_hp = 0
                                state.game_over = True
                        for _ in range(5):
                            state.particles.append(Particle(e.x, e.y, (255, 50, 50)))

                # Healer heals nearby
                if e.type == "healer" and e.hp > 0:
                    for other in state.enemies:
                        if other != e and other.hp > 0 and other.hp < other.max_hp:
                            if math.hypot(other.x - e.x, other.y - e.y) < 80:
                                other.hp = min(other.max_hp, other.hp + 0.5)

            # Update projectiles
            for p in state.projectiles[:]:
                if not p.active:
                    state.projectiles.remove(p)
                    continue
                p.update(dt)
                if p.active and p.target and p.target.hp <= 0 and not p.target.reached:
                    if p.pierce > 0:
                        p.pierce -= 1
                        new_targets = []
                        for e in state.enemies:
                            if e.hp > 0 and not e.reached and e != p.target:
                                d = math.hypot(e.x - p.x, e.y - p.y)
                                if d < 100:
                                    new_targets.append((d, e))
                        if new_targets:
                            new_targets.sort(key=lambda x: x[0])
                            p.target = new_targets[0][1]
                        else:
                            p.active = False
                    else:
                        p.target.reached = True
                        g = int((5 + state.wave) * state.gold_per_kill)
                        state.gold += g
                        if state.life_steal > 0:
                            state.tower_hp = min(state.tower_hp + state.life_steal * 2, state.tower_max_hp)
                        for _ in range(8):
                            state.particles.append(Particle(p.target.x, p.target.y, GOLD))
                        state.floating.append(FloatingText(p.target.x, p.target.y, f"+${g}", GOLD, 22))
                        if random.random() < 0.1:
                            drop_type = random.choice(["heal", "gold", "damage", "speed", "shield"])
                            state.drops.append(PowerUpDrop(p.target.x, p.target.y, drop_type))
                        p.active = False

            # Cleanup dead enemies
            for e in state.enemies[:]:
                if e.hp <= 0 and e.death_timer <= 0:
                    if not e.reached:
                        g = int((5 + state.wave) * state.gold_per_kill)
                        state.gold += g
                        state.floating.append(FloatingText(e.x, e.y, f"+${g}", GOLD, 22))
                        if state.life_steal > 0:
                            state.tower_hp = min(state.tower_hp + state.life_steal * 2, state.tower_max_hp)
                        if random.random() < 0.1:
                            drop_type = random.choice(["heal", "gold", "damage", "speed", "shield"])
                            state.drops.append(PowerUpDrop(e.x, e.y, drop_type))
                    state.enemies.remove(e)

            # Magnet auto-collect
            magnet_delay = state.magnet_delay()
            if magnet_delay is not None:
                for drop in state.drops[:]:
                    drop.time_ground += dt
                    if drop.time_ground >= magnet_delay:
                        drop.collected = True
                    drop.update(dt)
                    if drop.life <= 0:
                        state._apply_drop(drop)
                        state.drops.remove(drop)
            else:
                for drop in state.drops[:]:
                    drop.update(dt)
                    if drop.life <= 0:
                        state.drops.remove(drop)

            # Update particles
            for p in state.particles[:]:
                p.update(dt)
                if p.life <= 0:
                    state.particles.remove(p)

            # Update floating texts
            for ft in state.floating[:]:
                ft.update(dt)
                if ft.life <= 0:
                    state.floating.remove(ft)

            # Update wave popup
            if state.wave_popup:
                state.wave_popup["life"] -= dt
                if state.wave_popup["life"] <= 0:
                    state.wave_popup = None

        # ── RENDER ──
        shake_x = random.randint(-5, 5) if state.shake > 0 else 0
        shake_y = random.randint(-5, 5) if state.shake > 0 else 0

        screen.fill(BG)

        # Grid lines
        for i in range(0, WIDTH, 50):
            pygame.draw.line(screen, GRID, (i + shake_x, 50 + shake_y), (i + shake_x, HEIGHT + shake_y), 1)
        for i in range(50, HEIGHT, 50):
            pygame.draw.line(screen, GRID, (0 + shake_x, i + shake_y), (WIDTH + shake_x, i + shake_y), 1)

        # Missile explosion
        if state.missile_boom and state.missile_target:
            mx, my = state.missile_target
            pygame.draw.circle(screen, (255, 200, 50), (int(mx) + shake_x, int(my) + shake_y), int(state.missile_r), 3)
            pygame.draw.circle(screen, (255, 100, 0), (int(mx) + shake_x, int(my) + shake_y), int(state.missile_r * 0.6))

        # Particles
        for p in state.particles:
            pygame.draw.circle(screen, p.color, (int(p.x) + shake_x, int(p.y) + shake_y), int(p.size))

        # Floating texts
        for ft in state.floating:
            ft.draw(screen)

        # Drops
        for drop in state.drops:
            drop.draw(screen)

        # Turrets
        for turret in state.turrets:
            turret.draw(screen)

        # Enemies
        for e in state.enemies:
            e.draw(screen)

        # Projectiles
        for p in state.projectiles:
            pygame.draw.circle(screen, PROJ, (int(p.x) + shake_x, int(p.y) + shake_y), p.radius)

        # Tower
        draw_tower(screen, state)

        # Wave popup
        if state.wave_popup:
            popup = state.wave_popup
            progress = popup["life"] / popup["max"]
            alpha = int(255 * (1 - progress) / 0.15) if progress > 0.85 else int(255 * min(1.0, progress / 0.5))
            popup_font = pygame.font.SysFont("Segoe UI", 48, bold=True)
            text = popup_font.render(popup["text"], True, (255, 200, 80))
            text.set_alpha(alpha)
            x = WIDTH // 2 - text.get_width() // 2
            y = HEIGHT // 2 - 80
            screen.blit(text, (x + shake_x, y + shake_y))
            sub_font = pygame.font.SysFont("Segoe UI", 20)
            sub = sub_font.render("BOSS INCOMING!" if state.boss_active else "INCOMING!", True, (255, 100, 100))
            sub.set_alpha(alpha)
            sx = WIDTH // 2 - sub.get_width() // 2
            screen.blit(sub, (sx + shake_x, y + 55 + shake_y))

        # UI
        draw_top_bar(screen, font, state)
        draw_boss_hp_bar(screen, font, state)
        draw_ability_bar(screen, font_sm, state)
        draw_active_effects(screen, font_sm, state)
        upgrade_buttons = draw_upgrade_tab(screen, font_sm, state, active_tab)

        # Game over
        if state.game_over:
            overlay = pygame.Surface((WIDTH, HEIGHT))
            overlay.fill((0, 0, 0))
            overlay.set_alpha(180)
            screen.blit(overlay, (0, 0))
            go_text = font_lg.render("GAME OVER", True, (255, 80, 80))
            screen.blit(go_text, (WIDTH//2 - go_text.get_width()//2, HEIGHT//2 - 50))
            wave_text = font.render(f"You survived {state.wave - 1} waves", True, TEXT)
            screen.blit(wave_text, (WIDTH//2 - wave_text.get_width()//2, HEIGHT//2 + 20))
            restart_text = font.render("Press R to Restart", True, GOLD)
            screen.blit(restart_text, (WIDTH//2 - restart_text.get_width()//2, HEIGHT//2 + 60))
            if state.wave >= 10:
                prestige_text = font.render("Press P to Prestige (Keep permanent bonuses)", True, (255, 200, 100))
                screen.blit(prestige_text, (WIDTH//2 - prestige_text.get_width()//2, HEIGHT//2 + 90))

        # Pause
        if state.paused:
            overlay = pygame.Surface((WIDTH, HEIGHT))
            overlay.fill((0, 0, 0))
            overlay.set_alpha(120)
            screen.blit(overlay, (0, 0))
            pause_text = font_lg.render("PAUSED", True, TEXT)
            screen.blit(pause_text, (WIDTH//2 - pause_text.get_width()//2, HEIGHT//2 - 20))
            save_hint = font.render("Press S to Save", True, (100, 255, 100))
            screen.blit(save_hint, (WIDTH//2 - save_hint.get_width()//2, HEIGHT//2 + 20))

        pygame.display.flip()

    pygame.quit()

if __name__ == "__main__":
    main()
# ── DRAWING FUNCTIONS ───────────────────────────────────
def draw_tower(screen, state):
    tower_r = 20 + state.multishot * 3
    if state.has_shield:
        pygame.draw.circle(screen, (100, 150, 255), (CENTER_X, CENTER_Y), tower_r + 8, 2)
    if TOWER_SHAPE == "hexagon":
        points = []
        for i in range(6):
            angle = math.radians(i * 60 - 30)
            px = CENTER_X + math.cos(angle) * tower_r
            py = CENTER_Y + math.sin(angle) * tower_r
            points.append((px, py))
        color = (255, 80, 80) if state.rage_timer > 0 else TOWER_C
        pygame.draw.polygon(screen, color, points)
        pygame.draw.polygon(screen, TOWER_OUT, points, 2)
    else:
        color = (255, 80, 80) if state.rage_timer > 0 else TOWER_C
        pygame.draw.circle(screen, color, (CENTER_X, CENTER_Y), tower_r)
        pygame.draw.circle(screen, TOWER_OUT, (CENTER_X, CENTER_Y), tower_r, 2)
    if SHOW_RANGE:
        pygame.draw.circle(screen, (100, 150, 255), (CENTER_X, CENTER_Y), int(state.range_r), 1)
    for i in range(state.multishot):
        angle = (i / state.multishot) * 360 + time.time() * 20
        rad = math.radians(angle)
        end_x = CENTER_X + math.cos(rad) * (tower_r + 8)
        end_y = CENTER_Y + math.sin(rad) * (tower_r + 8)
        pygame.draw.line(screen, TOWER_GUN, (CENTER_X, CENTER_Y), (end_x, end_y), 4)

def draw_upgrade_tab(screen, font, state, active_tab):
    # Tab buttons
    tabs = [("OFFENCE", 0, TAB_OFF), ("DEFENCE", 1, TAB_DEF), ("UTILITY", 2, TAB_UTL)]
    tab_w = 80
    tab_x = 750
    tab_y = 60
    for name, idx, color in tabs:
        bg = color if active_tab == idx else (40, 40, 50)
        rect = pygame.Rect(tab_x, tab_y, tab_w, 28)
        pygame.draw.rect(screen, bg, rect, border_radius=4)
        pygame.draw.rect(screen, PANEL_BDR, rect, 1, border_radius=4)
        t = font.render(name, True, TEXT if active_tab == idx else TEXT_DIM)
        screen.blit(t, (tab_x + tab_w//2 - t.get_width()//2, tab_y + 5))
        tab_x += tab_w + 5

    # Panel background
    panel_x = 750
    panel_y = 90
    panel_w = 240
    panel_h = 400
    pygame.draw.rect(screen, PANEL_BG, (panel_x, panel_y, panel_w, panel_h), border_radius=8)
    pygame.draw.rect(screen, PANEL_BDR, (panel_x, panel_y, panel_w, panel_h), 2, border_radius=8)

    clickable = []
    y = panel_y + 15
    row_h = 50

    if active_tab == 0:  # OFFENCE
        upgrades = [
            (f"Damage ({state.damage:.0f})", "+5", state.c_dmg, state.up_dmg),
            (f"Fire Rate ({state.fire_rate:.1f}/s)", "+0.3", state.c_speed, state.up_speed),
            (f"Range ({state.range_r:.0f})", "+30", state.c_range, state.up_range),
            (f"Multi-shot ({state.multishot})", "+1", state.c_multi, state.up_multi),
            (f"Crit Chance ({state.crit_chance*100:.0f}%)", "+3%", state.c_critc, state.up_critc),
            (f"Crit Mult ({state.crit_mult:.1f}x)", "+0.3x", state.c_critm, state.up_critm),
        ]
        for name, desc, cost, fn in upgrades:
            is_maxed = ("Multi-shot" in name and state.multishot >= 4) or \
                       ("Crit Chance" in name and state.crit_chance >= 0.5) or \
                       ("Crit Mult" in name and state.crit_mult >= 5.0)
            color = BTN_MAXED if is_maxed else BTN
            rect = pygame.Rect(panel_x + 10, y, panel_w - 20, row_h - 5)
            pygame.draw.rect(screen, color, rect, border_radius=5)
            pygame.draw.rect(screen, PANEL_BDR, rect, 1, border_radius=5)
            screen.blit(font.render(name, True, TEXT), (panel_x + 18, y + 3))
            cost_color = GOLD if state.gold >= cost else (150, 120, 80)
            screen.blit(font.render(f"💰{cost}", True, cost_color), (panel_x + 18, y + 22))
            if not is_maxed:
                clickable.append((rect, fn))
            y += row_h
    elif active_tab == 1:  # DEFENCE
        upgrades = [
            (f"Tower HP ({state.tower_hp:.0f}/{state.tower_max_hp})", "+20", state.c_hp, state.up_hp),
            (f"Shield", "Active" if state.has_shield else "Buy", 250, state.buy_shield),
        ]
        for name, desc, cost, fn in upgrades:
            is_maxed = "Shield" in name and state.has_shield
            color = BTN_MAXED if is_maxed else BTN
            rect = pygame.Rect(panel_x + 10, y, panel_w - 20, row_h - 5)
            pygame.draw.rect(screen, color, rect, border_radius=5)
            pygame.draw.rect(screen, PANEL_BDR, rect, 1, border_radius=5)
            screen.blit(font.render(name, True, TEXT), (panel_x + 18, y + 3))
            cost_color = GOLD if state.gold >= cost else (150, 120, 80)
            screen.blit(font.render(f"💰{cost}", True, cost_color), (panel_x + 18, y + 22))
            if not is_maxed:
                clickable.append((rect, fn))
            y += row_h
    else:  # UTILITY
        upgrades = [
            (f"Gold/Kill ({state.gold_per_kill:.1f}x)", "+0.5x", state.c_gkill, state.buy_gkill),
            (f"Gold/Wave ({state.gold_per_wave:.1f}x)", "+0.3x", state.c_gwave, state.buy_gwave),
            (f"Magnet (Lv{state.magnet})", "Lv up", state.magnet_cost, state.buy_magnet),
            (f"Life Steal (+{state.life_steal})", "+1", 400 + state.life_steal * 300, state.buy_lifesteal),
            (f"Turret ({len(state.turrets)}/4)", "New", state.c_turret, state.buy_turret),
        ]
        for name, desc, cost, fn in upgrades:
            is_maxed = ("Magnet" in name and state.magnet >= 4) or \
                       ("Turret" in name and len(state.turrets) >= 4) or \
                       ("Life Steal" in name and state.life_steal >= 5) or \
                       ("Gold/Kill" in name and state.gold_per_kill >= 5.0) or \
                       ("Gold/Wave" in name and state.gold_per_wave >= 3.0)
            color = BTN_MAXED if is_maxed else BTN
            rect = pygame.Rect(panel_x + 10, y, panel_w - 20, row_h - 5)
            pygame.draw.rect(screen, color, rect, border_radius=5)
            pygame.draw.rect(screen, PANEL_BDR, rect, 1, border_radius=5)
            screen.blit(font.render(name, True, TEXT), (panel_x + 18, y + 3))
            cost_color = GOLD if state.gold >= cost else (150, 120, 80)
            screen.blit(font.render(f"💰{cost}", True, cost_color), (panel_x + 18, y + 22))
            if not is_maxed:
                clickable.append((rect, fn))
            y += row_h

    return clickable

def draw_ability_bar(screen, font, state):
    bar_y = 60
    btn_size = 45
    gap = 8
    bar_x = 10
    abilities = [("1","bomb"), ("2","heal"), ("3","freeze"), ("4","rage"), ("5","vacuum"), ("6","missile")]
    for key, name in abilities:
        ab = state.abilities[name]
        rect = pygame.Rect(bar_x, bar_y, btn_size, btn_size)
        if ab["ready"]:
            pygame.draw.rect(screen, (60,100,60), rect, border_radius=5)
        else:
            pygame.draw.rect(screen, (60,60,60), rect, border_radius=5)
            pct = ab["cd"] / ab["max"]
            overlay_h = int(btn_size * pct)
            pygame.draw.rect(screen, (40,40,40), (bar_x, bar_y, btn_size, overlay_h), border_radius=5)
        pygame.draw.rect(screen, PANEL_BDR, rect, 2, border_radius=5)
        icon_font = pygame.font.SysFont("Segoe UI", 20)
        icon = icon_font.render(ab["icon"], True, TEXT)
        screen.blit(icon, (bar_x + btn_size//2 - icon.get_width()//2, bar_y + 5))
        screen.blit(font.render(key, True, TEXT_DIM), (bar_x + 3, bar_y + btn_size - 16))
        if not ab["ready"]:
            cd_text = font.render(f"{ab['cd']:.0f}", True, (255,100,100))
            screen.blit(cd_text, (bar_x + btn_size - cd_text.get_width() - 3, bar_y + btn_size - 16))
        bar_x += btn_size + gap
    return []

def draw_active_effects(screen, font, state):
    effects = []
    if state.rage_timer > 0:
        effects.append(("RAGE", state.rage_timer, (255,80,80)))
    if state.freeze_timer > 0:
        effects.append(("FREEZE", state.freeze_timer, (100,200,255)))
    x = 10
    y = 120
    for name, timer, color in effects:
        text = font.render(f"{name}: {timer:.1f}s", True, color)
        screen.blit(text, (x, y))
        y += 20

def draw_top_bar(screen, font, state):
    bar_h = 50
    pygame.draw.rect(screen, (20,25,40), (0, 0, WIDTH, bar_h))
    pygame.draw.line(screen, PANEL_BDR, (0, bar_h), (WIDTH, bar_h), 2)
    screen.blit(font.render(f"💰{state.gold}", True, GOLD), (15, 8))
    screen.blit(font.render(f"Wave {state.wave}", True, TEXT), (15, 26))
    hp_pct = state.tower_hp / state.tower_max_hp
    hp_bar_w, hp_bar_h = 180, 18
    hp_bar_x = WIDTH // 2 - hp_bar_w // 2
    pygame.draw.rect(screen, HP_BG, (hp_bar_x, 14, hp_bar_w, hp_bar_h))
    hp_color = HP_RED if hp_pct < 0.3 else HP_FG
    pygame.draw.rect(screen, hp_color, (hp_bar_x, 14, int(hp_bar_w * hp_pct), hp_bar_h))
    hp_text = font.render(f"{int(state.tower_hp)}/{state.tower_max_hp}", True, TEXT)
    screen.blit(hp_text, (hp_bar_x + hp_bar_w//2 - hp_text.get_width()//2, 13))
    if state.wave_active:
        status = font.render("⚔️ ACTIVE" + (" BOSS!" if state.boss_active else ""), True, (255,100,100))
    else:
        cd = max(0, state.wave_cd)
        status = font.render(f"Next: {cd:.1f}s", True, (100,255,100))
    screen.blit(status, (WIDTH - status.get_width() - 20, 14))
    if state.prestige_level > 0:
        prestige_text = font.render(f"P{state.prestige_level}", True, (255,200,100))
        screen.blit(prestige_text, (WIDTH - prestige_text.get_width() - 20, 30))

def draw_boss_hp_bar(screen, font, state):
    if not state.boss_active or not state.enemies:
        return
    boss = None
    for e in state.enemies:
        if e.hp > 0:
            boss = e
            break
    if not boss:
        return
    bar_w = 300
    bar_h = 20
    bar_x = WIDTH // 2 - bar_w // 2
    bar_y = 80
    hp_pct = boss.hp / boss.max_hp
    pygame.draw.rect(screen, (60, 0, 0), (bar_x, bar_y, bar_w, bar_h))
    pygame.draw.rect(screen, (220, 50, 50), (bar_x, bar_y, int(bar_w * hp_pct), bar_h))
    pygame.draw.rect(screen, (255, 100, 100), (bar_x, bar_y, bar_w, bar_h), 2)
    name_text = font.render(f"BOSS WAVE {state.wave}", True, (255, 100, 100))
    screen.blit(name_text, (bar_x + bar_w//2 - name_text.get_width()//2, bar_y - 18))
# ── SPAWN ENEMY ─────────────────────────────────────────
def spawn_enemy(state):
    edge = random.choice(["top", "bottom", "left", "right"])
    if edge == "top":
        x, y = random.randint(50, 700), -20
    elif edge == "bottom":
        x, y = random.randint(50, 700), HEIGHT + 20
    elif edge == "left":
        x, y = -20, random.randint(50, HEIGHT - 50)
    else:
        x, y = 720, random.randint(50, HEIGHT - 50)
    if state.boss_active:
        return Enemy(x, y, state.enemy_hp(), state.enemy_spd(), "tank")
    r = random.random()
    if r < 0.35:
        etype, hp_mult, spd_mult = "basic", 1.0, 1.0
    elif r < 0.55:
        etype, hp_mult, spd_mult = "swarm", 0.5, 1.5
    elif r < 0.75:
        etype, hp_mult, spd_mult = "tank", 3.0, 0.6
    elif r < 0.85:
        etype, hp_mult, spd_mult = "healer", 0.8, 1.0
    elif r < 0.93:
        etype, hp_mult, spd_mult = "bomber", 1.2, 1.1
    else:
        etype, hp_mult, spd_mult = "invis", 0.9, 1.2
    return Enemy(x, y, state.enemy_hp() * hp_mult, state.enemy_spd() * spd_mult, etype)

# ── MAIN ────────────────────────────────────────────────
def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("The Tower 💎")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("Segoe UI", 16)
    font_lg = pygame.font.SysFont("Segoe UI", 36, bold=True)
    font_sm = pygame.font.SysFont("Segoe UI", 14)

    state = GameState()
    upgrade_buttons = []
    active_tab = 0  # 0=Offence, 1=Defence, 2=Utility
    running = True

    while running:
        dt = clock.tick(60) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                state.save()
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    state.paused = not state.paused
                if event.key == pygame.K_SPACE and not state.wave_active and not state.game_over:
                    state.start_wave()
                if event.key == pygame.K_r and state.game_over:
                    state.reset()
                if event.key == pygame.K_p and state.game_over:
                    if state.do_prestige():
                        state.floating.append(FloatingText(CENTER_X, CENTER_Y, "PRESTIGE!", (255, 200, 100), 32))
                if event.key == pygame.K_s:
                    state.save()
                    state.floating.append(FloatingText(CENTER_X, CENTER_Y, "SAVED!", (100, 255, 100), 24))
                if event.key == pygame.K_TAB:
                    active_tab = (active_tab + 1) % 3
                if not state.paused and not state.game_over:
                    if event.key == pygame.K_1:
                        kills = state.use_bomb()
                        if kills > 0:
                            state.floating.append(FloatingText(CENTER_X, CENTER_Y, f"BOOM! {kills} kills", (255, 200, 50), 30))
                    if event.key == pygame.K_2:
                        heal = state.use_heal()
                        if heal > 0:
                            state.floating.append(FloatingText(CENTER_X, CENTER_Y - 30, f"+{int(heal)} HP", (100, 255, 100), 24))
                    if event.key == pygame.K_3:
                        if state.use_freeze():
                            state.floating.append(FloatingText(CENTER_X, CENTER_Y, "FREEZE!", (100, 200, 255), 30))
                    if event.key == pygame.K_4:
                        if state.use_rage():
                            state.floating.append(FloatingText(CENTER_X, CENTER_Y, "RAGE MODE!", (255, 80, 80), 32))
                    if event.key == pygame.K_5:
                        count = state.use_vacuum()
                        if count > 0:
                            state.floating.append(FloatingText(CENTER_X, CENTER_Y, f"🧲 VACUUM: {count} items!", (255, 100, 255), 28))
                    if event.key == pygame.K_6:
                        state.floating.append(FloatingText(CENTER_X, CENTER_Y, "CLICK TARGET!", (255, 200, 100), 24))
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if state.game_over:
                    state.reset()
                    continue
                mx, my = pygame.mouse.get_pos()
                # Missile target
                if state.missile_target is not None and state.abilities["missile"]["ready"]:
                    state.use_missile(mx, my)
                    continue
                # Tab switching
                tab_w = 80
                tab_x = 750
                tab_y = 60
                for idx in range(3):
                    rect = pygame.Rect(tab_x, tab_y, tab_w, 28)
                    if rect.collidepoint(mx, my):
                        active_tab = idx
                        break
                    tab_x += tab_w + 5
                # Upgrade buttons
                for btn_rect, fn in upgrade_buttons:
                    if btn_rect.collidepoint(mx, my):
                        if fn():
                            state.floating.append(FloatingText(mx, my, "UPGRADED!", (100, 255, 100), 20))
                        break
                # Drops
                for drop in state.drops[:]:
                    if math.hypot(drop.x - mx, drop.y - my) < drop.radius + 10:
                        state._apply_drop(drop)
                        state.drops.remove(drop)
                        break

        # Auto-start next wave
        if not state.wave_active and not state.game_over and state.wave_cd > 0:
            state.wave_cd -= dt
            if state.wave_cd <= 0:
                state.start_wave()

        # Main game logic
        if not state.paused and not state.game_over:
            if state.rage_timer > 0:
                state.rage_timer -= dt
            if state.freeze_timer > 0:
                state.freeze_timer -= dt
                if state.freeze_timer <= 0:
                    for e in state.enemies:
                        e.frozen = False

            for ab in state.abilities.values():
                if not ab["ready"]:
                    ab["cd"] -= dt
                    if ab["cd"] <= 0:
                        ab["ready"] = True
                        ab["cd"] = 0

            state.update_missile(dt)

            if state.shake > 0:
                state.shake -= dt
                if state.shake < 0:
                    state.shake = 0

            # Tower shooting
            now = time.time()
            if now - state.last_shot >= state.fire_cd():
                targets = []
                for e in state.enemies:
                    dist = math.hypot(e.x - CENTER_X, e.y - CENTER_Y)
                    if dist <= state.range_r and e.hp > 0 and not e.reached:
                        targets.append((dist, e))
                if targets:
                    targets.sort(key=lambda x: x[0])
                    state.last_shot = now
                    for i in range(min(state.multishot, len(targets))):
                        target = targets[i][1]
                        is_crit = random.random() < state.crit_chance
                        dmg = state.total_dmg() * (state.crit_mult if is_crit else 1.0)
                        proj = Projectile(CENTER_X, CENTER_Y, target, dmg)
                        proj.pierce = state.pierce
                        state.projectiles.append(proj)

            # Turret shooting
            for turret in state.turrets:
                turret.update(dt, state.enemies, state)

            # Spawn enemies
            if state.wave_active:
                state.wave_spawn -= dt
                if state.wave_spawn <= 0 and state.wave_enemies > 0:
                    state.enemies.append(spawn_enemy(state))
                    state.wave_enemies -= 1
                    state.wave_spawn = max(0.2, 1.0 - state.wave * 0.03)

                if state.wave_enemies <= 0 and len(state.enemies) == 0:
                    state.wave_active = False
                    state.boss_active = False
                    state.wave += 1
                    state.gold += int((50 + state.wave * 10) * state.gold_per_wave)
                    state.wave_cd = 3.0
                    state.highest_wave = max(state.highest_wave, state.wave - 1)

            # Update enemies
            for e in state.enemies[:]:
                if e.death_timer > 0:
                    e.death_timer -= dt
                    if e.death_timer <= 0:
                        e.hp = 0
                        state.enemies.remove(e)
                    continue

                dist = e.move_toward(CENTER_X, CENTER_Y, dt)
                if dist < 25:
                    # Bomber explodes
                    if e.type == "bomber":
                        e.exploded = True
                        state.shake = 0.4
                        for other in state.enemies:
                            if other != e and math.hypot(other.x - e.x, other.y - e.y) < 60:
                                other.hp -= 20
                                if other.hp <= 0:
                                    other.death_timer = 0.3
                        for turret in state.turrets:
                            if math.hypot(turret.x - e.x, turret.y - e.y) < 60:
                                turret.hp -= 15
                        state.tower_hp -= 15
                        state.floating.append(FloatingText(CENTER_X, CENTER_Y - 20, "-15", (255, 50, 50), 24))

                    if e.hp > 0:
                        e.hp = 0
                        if state.has_shield:
                            state.has_shield = False
                            state.floating.append(FloatingText(CENTER_X, CENTER_Y, "SHIELD BROKEN!", (100, 150, 255), 24))
                            for _ in range(10):
                                state.particles.append(Particle(CENTER_X, CENTER_Y, (100, 150, 255)))
                        else:
                            state.tower_hp -= 10
                            state.floating.append(FloatingText(CENTER_X, CENTER_Y - 20, "-10", (255, 50, 50), 20))
                            if state.tower_hp <= 0:
                                state.tower_hp = 0
                                state.game_over = True
                        for _ in range(5):
                            state.particles.append(Particle(e.x, e.y, (255, 50, 50)))

                # Healer heals nearby
                if e.type == "healer" and e.hp > 0:
                    for other in state.enemies:
                        if other != e and other.hp > 0 and other.hp < other.max_hp:
                            if math.hypot(other.x - e.x, other.y - e.y) < 80:
                                other.hp = min(other.max_hp, other.hp + 0.5)

            # Update projectiles
            for p in state.projectiles[:]:
                if not p.active:
                    state.projectiles.remove(p)
                    continue
                p.update(dt)
                if p.active and p.target and p.target.hp <= 0 and not p.target.reached:
                    if p.pierce > 0:
                        p.pierce -= 1
                        new_targets = []
                        for e in state.enemies:
                            if e.hp > 0 and not e.reached and e != p.target:
                                d = math.hypot(e.x - p.x, e.y - p.y)
                                if d < 100:
                                    new_targets.append((d, e))
                        if new_targets:
                            new_targets.sort(key=lambda x: x[0])
                            p.target = new_targets[0][1]
                        else:
                            p.active = False
                    else:
                        p.target.reached = True
                        g = int((5 + state.wave) * state.gold_per_kill)
                        state.gold += g
                        if state.life_steal > 0:
                            state.tower_hp = min(state.tower_hp + state.life_steal * 2, state.tower_max_hp)
                        for _ in range(8):
                            state.particles.append(Particle(p.target.x, p.target.y, GOLD))
                        state.floating.append(FloatingText(p.target.x, p.target.y, f"+${g}", GOLD, 22))
                        if random.random() < 0.1:
                            drop_type = random.choice(["heal", "gold", "damage", "speed", "shield"])
                            state.drops.append(PowerUpDrop(p.target.x, p.target.y, drop_type))
                        p.active = False

            # Cleanup dead enemies
            for e in state.enemies[:]:
                if e.hp <= 0 and e.death_timer <= 0:
                    if not e.reached:
                        g = int((5 + state.wave) * state.gold_per_kill)
                        state.gold += g
                        state.floating.append(FloatingText(e.x, e.y, f"+${g}", GOLD, 22))
                        if state.life_steal > 0:
                            state.tower_hp = min(state.tower_hp + state.life_steal * 2, state.tower_max_hp)
                        if random.random() < 0.1:
                            drop_type = random.choice(["heal", "gold", "damage", "speed", "shield"])
                            state.drops.append(PowerUpDrop(e.x, e.y, drop_type))
                    state.enemies.remove(e)

            # Magnet auto-collect
            magnet_delay = state.magnet_delay()
            if magnet_delay is not None:
                for drop in state.drops[:]:
                    drop.time_ground += dt
                    if drop.time_ground >= magnet_delay:
                        drop.collected = True
                    drop.update(dt)
                    if drop.life <= 0:
                        state._apply_drop(drop)
                        state.drops.remove(drop)
            else:
                for drop in state.drops[:]:
                    drop.update(dt)
                    if drop.life <= 0:
                        state.drops.remove(drop)

            # Update particles
            for p in state.particles[:]:
                p.update(dt)
                if p.life <= 0:
                    state.particles.remove(p)

            # Update floating texts
            for ft in state.floating[:]:
                ft.update(dt)
                if ft.life <= 0:
                    state.floating.remove(ft)

            # Update wave popup
            if state.wave_popup:
                state.wave_popup["life"] -= dt
                if state.wave_popup["life"] <= 0:
                    state.wave_popup = None

        # ── RENDER ──
        shake_x = random.randint(-5, 5) if state.shake > 0 else 0
        shake_y = random.randint(-5, 5) if state.shake > 0 else 0

        screen.fill(BG)

        # Grid lines
        for i in range(0, WIDTH, 50):
            pygame.draw.line(screen, GRID, (i + shake_x, 50 + shake_y), (i + shake_x, HEIGHT + shake_y), 1)
        for i in range(50, HEIGHT, 50):
            pygame.draw.line(screen, GRID, (0 + shake_x, i + shake_y), (WIDTH + shake_x, i + shake_y), 1)

        # Missile explosion
        if state.missile_boom and state.missile_target:
            mx, my = state.missile_target
            pygame.draw.circle(screen, (255, 200, 50), (int(mx) + shake_x, int(my) + shake_y), int(state.missile_r), 3)
            pygame.draw.circle(screen, (255, 100, 0), (int(mx) + shake_x, int(my) + shake_y), int(state.missile_r * 0.6))

        # Particles
        for p in state.particles:
            pygame.draw.circle(screen, p.color, (int(p.x) + shake_x, int(p.y) + shake_y), int(p.size))

        # Floating texts
        for ft in state.floating:
            ft.draw(screen)

        # Drops
        for drop in state.drops:
            drop.draw(screen)

        # Turrets
        for turret in state.turrets:
            turret.draw(screen)

        # Enemies
        for e in state.enemies:
            e.draw(screen)

        # Projectiles
        for p in state.projectiles:
            pygame.draw.circle(screen, PROJ, (int(p.x) + shake_x, int(p.y) + shake_y), p.radius)

        # Tower
        draw_tower(screen, state)

        # Wave popup
        if state.wave_popup:
            popup = state.wave_popup
            progress = popup["life"] / popup["max"]
            alpha = int(255 * (1 - progress) / 0.15) if progress > 0.85 else int(255 * min(1.0, progress / 0.5))
            popup_font = pygame.font.SysFont("Segoe UI", 48, bold=True)
            text = popup_font.render(popup["text"], True, (255, 200, 80))
            text.set_alpha(alpha)
            x = WIDTH // 2 - text.get_width() // 2
            y = HEIGHT // 2 - 80
            screen.blit(text, (x + shake_x, y + shake_y))
            sub_font = pygame.font.SysFont("Segoe UI", 20)
            sub = sub_font.render("BOSS INCOMING!" if state.boss_active else "INCOMING!", True, (255, 100, 100))
            sub.set_alpha(alpha)
            sx = WIDTH // 2 - sub.get_width() // 2
            screen.blit(sub, (sx + shake_x, y + 55 + shake_y))

        # UI
        draw_top_bar(screen, font, state)
        draw_boss_hp_bar(screen, font, state)
        draw_ability_bar(screen, font_sm, state)
        draw_active_effects(screen, font_sm, state)
        upgrade_buttons = draw_upgrade_tab(screen, font_sm, state, active_tab)

        # Game over
        if state.game_over:
            overlay = pygame.Surface((WIDTH, HEIGHT))
            overlay.fill((0, 0, 0))
            overlay.set_alpha(180)
            screen.blit(overlay, (0, 0))
            go_text = font_lg.render("GAME OVER", True, (255, 80, 80))
            screen.blit(go_text, (WIDTH//2 - go_text.get_width()//2, HEIGHT//2 - 50))
            wave_text = font.render(f"You survived {state.wave - 1} waves", True, TEXT)
            screen.blit(wave_text, (WIDTH//2 - wave_text.get_width()//2, HEIGHT//2 + 20))
            restart_text = font.render("Press R to Restart", True, GOLD)
            screen.blit(restart_text, (WIDTH//2 - restart_text.get_width()//2, HEIGHT//2 + 60))
            if state.wave >= 10:
                prestige_text = font.render("Press P to Prestige (Keep permanent bonuses)", True, (255, 200, 100))
                screen.blit(prestige_text, (WIDTH//2 - prestige_text.get_width()//2, HEIGHT//2 + 90))

        # Pause
        if state.paused:
            overlay = pygame.Surface((WIDTH, HEIGHT))
            overlay.fill((0, 0, 0))
            overlay.set_alpha(120)
            screen.blit(overlay, (0, 0))
            pause_text = font_lg.render("PAUSED", True, TEXT)
            screen.blit(pause_text, (WIDTH//2 - pause_text.get_width()//2, HEIGHT//2 - 20))
            save_hint = font.render("Press S to Save", True, (100, 255, 100))
            screen.blit(save_hint, (WIDTH//2 - save_hint.get_width()//2, HEIGHT//2 + 20))

        pygame.display.flip()

    pygame.quit()

if __name__ == "__main__":
    main()
