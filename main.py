import pygame
import math
import random
import time

# ── CONFIG ──────────────────────────────────────────────
# Appearance
TOWER_SHAPE = "hexagon"       # "hexagon", "circle", "square"
ENEMY_SHAPE = "square"        # "square", "circle"
SHOW_RANGE_CIRCLE = True

# UI Layout
UPGRADE_PANEL_SIDE = "right"  # "right", "bottom", or None
PLAY_AREA_W = 740 if UPGRADE_PANEL_SIDE == "right" else 1000

# ── CONSTANTS ───────────────────────────────────────────
WIDTH, HEIGHT = 1000, 700
CENTER_X, CENTER_Y = PLAY_AREA_W // 2, HEIGHT // 2

# Colors
BG = (15, 20, 30)
GRID_COLOR = (30, 35, 50)
TOWER_COLOR = (80, 150, 255)
TOWER_OUTLINE = (150, 200, 255)
TOWER_GUN = (100, 170, 255)
ENEMY_BASIC = (255, 80, 80)
ENEMY_TANK = (180, 60, 60)
ENEMY_SWARM = (255, 150, 50)
PROJECTILE = (255, 255, 100)
HP_BAR_BG = (60, 60, 60)
HP_BAR_FG = (80, 220, 80)
HP_BAR_RED = (220, 80, 80)
PANEL_BG = (25, 30, 45)
PANEL_BORDER = (50, 55, 75)
TEXT_COLOR = (220, 220, 220)
TEXT_DIM = (150, 150, 170)
GOLD_COLOR = (255, 215, 0)
UPGRADE_BTN = (60, 80, 120)
UPGRADE_BTN_HOVER = (80, 110, 160)
UPGRADE_MAXED = (80, 120, 80)

FPS = 60

# ── GAME STATE ──────────────────────────────────────────
class GameState:
    def __init__(self):
        self.reset()

    def reset(self):
        self.gold = 100
        self.wave = 1
        self.wave_active = False
        self.wave_enemies_remaining = 0
        self.wave_spawn_timer = 0
        self.wave_cooldown = 0
        self.wave_popup = None
        self.tower_hp = 100
        self.tower_max_hp = 100
        self.enemies = []
        self.projectiles = []
        self.particles = []
        self.floating_texts = []
        self.game_over = False
        self.paused = False
        self.last_shot = 0

        # Tower stats
        self.damage = 10
        self.fire_rate = 1.0
        self.range_radius = 250
        self.multishot = 1
        self.crit_chance = 0.05
        self.crit_mult = 2.0

        # Upgrade costs
        self.cost_damage = 50
        self.cost_speed = 60
        self.cost_range = 40
        self.cost_multi = 500
        self.cost_crit_chance = 80
        self.cost_crit_mult = 100
        self.cost_hp = 30

        # ── POWER-UPS ──────────────────────────────────
        # Permanent upgrades (bought in shop)
        self.damage_boost = 1.0      # Multiplier
        self.fire_rate_boost = 1.0   # Multiplier
        self.life_steal = 0          # HP healed per enemy kill
        self.pierce_count = 0       # Projectiles pierce through N extra enemies
        self.has_shield = False      # Absorb next tower hit

        # Active abilities (press 1-4 to use, cooldown based)
        self.abilities = {
            "bomb": {"cooldown": 0, "max_cooldown": 15, "ready": True, "icon": "💣"},
            "heal": {"cooldown": 0, "max_cooldown": 20, "ready": True, "icon": "💖"},
            "freeze": {"cooldown": 0, "max_cooldown": 25, "ready": True, "icon": "❄️"},
            "rage": {"cooldown": 0, "max_cooldown": 30, "ready": True, "icon": "🔥"},
        }
        self.rage_timer = 0  # Rage active duration
        self.frozen_timer = 0  # Freeze active duration

    def get_fire_cooldown(self):
        cooldown = 1.0 / (self.fire_rate * self.fire_rate_boost)
        # Rage mode: 2x fire rate
        if self.rage_timer > 0:
            cooldown *= 0.5
        return cooldown

    def get_total_damage(self):
        dmg = self.damage * self.damage_boost
        # Rage mode: 2x damage
        if self.rage_timer > 0:
            dmg *= 2
        return dmg

    def start_wave(self):
        self.wave_active = True
        self.wave_enemies_remaining = 10 + self.wave * 3
        self.wave_spawn_timer = 0
        self.wave_cooldown = 0
        self.wave_popup = {"text": f"WAVE {self.wave}", "life": 2.0, "max_life": 2.0}

    def get_enemy_hp(self):
        return 10 + self.wave * 2

    def get_enemy_speed(self):
        speed = 1.0 + self.wave * 0.05
        # Freeze: enemies move at 20% speed
        if self.frozen_timer > 0:
            speed *= 0.2
        return speed

    # ── UPGRADES ───────────────────────────────────
    def upgrade_damage(self):
        if self.gold >= self.cost_damage:
            self.gold -= self.cost_damage
            self.damage += 5
            self.cost_damage = int(self.cost_damage * 1.4)
            return True
        return False

    def upgrade_speed(self):
        if self.gold >= self.cost_speed:
            self.gold -= self.cost_speed
            self.fire_rate += 0.3
            self.cost_speed = int(self.cost_speed * 1.5)
            return True
        return False

    def upgrade_range(self):
        if self.gold >= self.cost_range:
            self.gold -= self.cost_range
            self.range_radius += 30
            self.cost_range = int(self.cost_range * 1.35)
            return True
        return False

    def upgrade_multishot(self):
        if self.gold >= self.cost_multi and self.multishot < 4:
            self.gold -= self.cost_multi
            self.multishot += 1
            self.cost_multi = int(self.cost_multi * 3)
            return True
        return False

    def upgrade_crit_chance(self):
        if self.gold >= self.cost_crit_chance and self.crit_chance < 0.5:
            self.gold -= self.cost_crit_chance
            self.crit_chance = min(0.5, self.crit_chance + 0.03)
            self.cost_crit_chance = int(self.cost_crit_chance * 1.45)
            return True
        return False

    def upgrade_crit_mult(self):
        if self.gold >= self.cost_crit_mult and self.crit_mult < 5.0:
            self.gold -= self.cost_crit_mult
            self.crit_mult += 0.3
            self.cost_crit_mult = int(self.cost_crit_mult * 1.4)
            return True
        return False

    def upgrade_hp(self):
        if self.gold >= self.cost_hp:
            self.gold -= self.cost_hp
            self.tower_max_hp += 20
            self.tower_hp = min(self.tower_hp + 30, self.tower_max_hp)
            self.cost_hp = int(self.cost_hp * 1.3)
            return True
        return False

    # ── PERMANENT POWER-UPS ────────────────────────
    def buy_damage_boost(self):
        cost = 300 * int(self.damage_boost)
        if self.gold >= cost and self.damage_boost < 3.0:
            self.gold -= cost
            self.damage_boost += 0.5
            return True
        return False

    def buy_fire_rate_boost(self):
        cost = 350 * int(self.fire_rate_boost)
        if self.gold >= cost and self.fire_rate_boost < 3.0:
            self.gold -= cost
            self.fire_rate_boost += 0.5
            return True
        return False

    def buy_life_steal(self):
        cost = 400 + self.life_steal * 300
        if self.gold >= cost and self.life_steal < 5:
            self.gold -= cost
            self.life_steal += 1
            return True
        return False

    def buy_pierce(self):
        cost = 500 + self.pierce_count * 400
        if self.gold >= cost and self.pierce_count < 3:
            self.gold -= cost
            self.pierce_count += 1
            return True
        return False

    def buy_shield(self):
        if self.gold >= 250 and not self.has_shield:
            self.gold -= 250
            self.has_shield = True
            return True
        return False

    # ── ACTIVE ABILITIES ───────────────────────────
    def use_bomb(self):
        ab = self.abilities["bomb"]
        if ab["ready"] and len(self.enemies) > 0:
            ab["ready"] = False
            ab["cooldown"] = ab["max_cooldown"]
            # Kill all enemies on screen
            kill_count = 0
            for e in self.enemies[:]:
                e.hp = 0
                kill_count += 1
                for _ in range(5):
                    self.particles.append(Particle(e.x, e.y, (255, 200, 50)))
            return kill_count
        return 0

    def use_heal(self):
        ab = self.abilities["heal"]
        if ab["ready"] and self.tower_hp < self.tower_max_hp:
            ab["ready"] = False
            ab["cooldown"] = ab["max_cooldown"]
            heal_amount = min(self.tower_max_hp - self.tower_hp, self.tower_max_hp * 0.4)
            self.tower_hp += heal_amount
            return heal_amount
        return 0

    def use_freeze(self):
        ab = self.abilities["freeze"]
        if ab["ready"]:
            ab["ready"] = False
            ab["cooldown"] = ab["max_cooldown"]
            self.frozen_timer = 5.0  # 5 seconds
            return True
        return False

    def use_rage(self):
        ab = self.abilities["rage"]
        if ab["ready"]:
            ab["ready"] = False
            ab["cooldown"] = ab["max_cooldown"]
            self.rage_timer = 8.0  # 8 seconds
            return True
        return False

# ── ENEMY ────────────────────────────────────────────────
class Enemy:
    def __init__(self, x, y, hp, speed, enemy_type):
        self.x = x
        self.y = y
        self.hp = hp
        self.max_hp = hp
        self.speed = speed
        self.type = enemy_type
        self.radius = 8 if enemy_type == "swarm" else (12 if enemy_type == "basic" else 16)
        self.color = ENEMY_SWARM if enemy_type == "swarm" else (ENEMY_BASIC if enemy_type == "basic" else ENEMY_TANK)
        self.reached = False
        self.frozen = False

    def move_toward(self, tx, ty, dt):
        dx = tx - self.x
        dy = ty - self.y
        dist = math.hypot(dx, dy)
        if dist > 0:
            self.x += (dx / dist) * self.speed * 60 * dt
            self.y += (dy / dist) * self.speed * 60 * dt
        return dist

    def draw(self, screen):
        color = (100, 200, 255) if self.frozen else self.color
        if ENEMY_SHAPE == "square":
            size = self.radius * 2
            rect = pygame.Rect(int(self.x - size//2), int(self.y - size//2), size, size)
            pygame.draw.rect(screen, color, rect)
            pygame.draw.rect(screen, (255, 255, 255), rect, 1)
        else:
            pygame.draw.circle(screen, color, (int(self.x), int(self.y)), self.radius)
            pygame.draw.circle(screen, (255, 255, 255), (int(self.x), int(self.y)), self.radius, 1)

        # HP bar
        hp_pct = self.hp / self.max_hp
        bar_w = 20
        bar_h = 4
        bar_x = int(self.x) - bar_w // 2
        bar_y = int(self.y) - self.radius - 8
        pygame.draw.rect(screen, HP_BAR_BG, (bar_x, bar_y, bar_w, bar_h))
        pygame.draw.rect(screen, HP_BAR_FG, (bar_x, bar_y, int(bar_w * hp_pct), bar_h))

# ── PROJECTILE ──────────────────────────────────────────
class Projectile:
    def __init__(self, x, y, target, damage, speed=600):
        self.x = x
        self.y = y
        self.target = target
        self.damage = damage
        self.speed = speed
        self.active = True
        self.pierced = 0  # Number of enemies pierced

    def update(self, dt):
        if not self.active or (self.target and self.target.hp <= 0):
            self.active = False
            return
        if self.target is None:
            self.active = False
            return
        dx = self.target.x - self.x
        dy = self.target.y - self.y
        dist = math.hypot(dx, dy)
        if dist < 8:
            self.active = False
            self.target.hp -= self.damage
            return
        if dist > 0:
            self.x += (dx / dist) * self.speed * dt
            self.y += (dy / dist) * self.speed * dt

    def draw(self, screen):
        pygame.draw.circle(screen, PROJECTILE, (int(self.x), int(self.y)), 4)

# ── PARTICLE ────────────────────────────────────────────
class Particle:
    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        self.vx = random.uniform(-100, 100)
        self.vy = random.uniform(-100, 100)
        self.life = 0.5
        self.max_life = 0.5
        self.color = color
        self.size = random.randint(3, 6)

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
        self.alpha = 255
        self.vy = -60
        self.vx = random.uniform(-20, 20)
        self.life = 1.2
        self.max_life = 1.2
        self.size = size
        self.font = pygame.font.SysFont("Segoe UI", size, bold=True)

    def update(self, dt):
        self.life -= dt
        self.y += self.vy * dt
        self.x += self.vx * dt
        self.alpha = int(255 * (self.life / self.max_life))

    def draw(self, screen):
        if self.alpha <= 0:
            return
        text_surf = self.font.render(self.text, True, self.color)
        text_surf.set_alpha(self.alpha)
        screen.blit(text_surf, (int(self.x) - text_surf.get_width()//2, int(self.y)))

# ── POWER-UP DROP ───────────────────────────────────────
class PowerUpDrop:
    def __init__(self, x, y, powerup_type):
        self.x = x
        self.y = y
        self.type = powerup_type  # "damage", "speed", "heal", "gold", "shield"
        self.life = 8.0  # Disappears after 8 seconds
        self.radius = 12

    def update(self, dt):
        self.life -= dt

    def draw(self, screen):
        colors = {
            "damage": (255, 100, 100),
            "speed": (100, 255, 100),
            "heal": (255, 100, 200),
            "gold": (255, 215, 0),
            "shield": (100, 150, 255),
        }
        color = colors.get(self.type, (200, 200, 200))
        pygame.draw.circle(screen, color, (int(self.x), int(self.y)), self.radius)
        pygame.draw.circle(screen, (255, 255, 255), (int(self.x), int(self.y)), self.radius, 2)

        icons = {"damage": "⚔️", "speed": "⚡", "heal": "💖", "gold": "💰", "shield": "🛡️"}
        font = pygame.font.SysFont("Segoe UI", 14)
        icon = font.render(icons.get(self.type, "?"), True, (255, 255, 255))
        screen.blit(icon, (int(self.x) - icon.get_width()//2, int(self.y) - icon.get_height()//2))

# ── DRAWING ─────────────────────────────────────────────
def draw_tower(screen, state):
    tower_r = 20 + state.multishot * 3

    # Shield aura
    if state.has_shield:
        pygame.draw.circle(screen, (100, 150, 255), (CENTER_X, CENTER_Y), tower_r + 8, 2)

    if TOWER_SHAPE == "hexagon":
        points = []
        for i in range(6):
            angle = math.radians(i * 60 - 30)
            px = CENTER_X + math.cos(angle) * tower_r
            py = CENTER_Y + math.sin(angle) * tower_r
            points.append((px, py))
        # Rage mode: red glow
        if state.rage_timer > 0:
            pygame.draw.polygon(screen, (255, 80, 80), points)
        else:
            pygame.draw.polygon(screen, TOWER_COLOR, points)
        pygame.draw.polygon(screen, TOWER_OUTLINE, points, 2)
    else:
        if state.rage_timer > 0:
            pygame.draw.circle(screen, (255, 80, 80), (CENTER_X, CENTER_Y), tower_r)
        else:
            pygame.draw.circle(screen, TOWER_COLOR, (CENTER_X, CENTER_Y), tower_r)
        pygame.draw.circle(screen, TOWER_OUTLINE, (CENTER_X, CENTER_Y), tower_r, 2)

    # Range circle
    if SHOW_RANGE_CIRCLE:
        pygame.draw.circle(screen, (100, 150, 255), (CENTER_X, CENTER_Y), int(state.range_radius), 1)

    # Gun barrels
    for i in range(state.multishot):
        angle = (i / state.multishot) * 360 + time.time() * 20
        rad = math.radians(angle)
        end_x = CENTER_X + math.cos(rad) * (tower_r + 8)
        end_y = CENTER_Y + math.sin(rad) * (tower_r + 8)
        pygame.draw.line(screen, TOWER_GUN, (CENTER_X, CENTER_Y), (end_x, end_y), 4)

def draw_upgrade_panel(screen, font, state):
    panel_x = PLAY_AREA_W + 10 if UPGRADE_PANEL_SIDE == "right" else 10
    panel_y = 10
    panel_w = 250 if UPGRADE_PANEL_SIDE == "right" else PLAY_AREA_W - 20
    panel_h = HEIGHT - 20 if UPGRADE_PANEL_SIDE == "right" else 140

    if UPGRADE_PANEL_SIDE == "bottom":
        panel_y = HEIGHT - 150

    pygame.draw.rect(screen, PANEL_BG, (panel_x, panel_y, panel_w, panel_h), border_radius=8)
    pygame.draw.rect(screen, PANEL_BORDER, (panel_x, panel_y, panel_w, panel_h), 2, border_radius=8)

    title = font.render("UPGRADES", True, GOLD_COLOR)
    screen.blit(title, (panel_x + panel_w//2 - title.get_width()//2, panel_y + 10))

    upgrades = [
        ("Damage", f"+5 DMG", state.cost_damage, state.upgrade_damage),
        ("Fire Rate", f"+0.3/s", state.cost_speed, state.upgrade_speed),
        ("Range", f"+30", state.cost_range, state.upgrade_range),
        ("Multi-shot", f"+1 shot", state.cost_multi, state.upgrade_multishot),
        ("Crit Chance", f"+3%", state.cost_crit_chance, state.upgrade_crit_chance),
        ("Crit Mult", f"+0.3x", state.cost_crit_mult, state.upgrade_crit_mult),
        ("Tower HP", f"Repair", state.cost_hp, state.upgrade_hp),
    ]

    if UPGRADE_PANEL_SIDE == "right":
        y = panel_y + 50
        btn_h = 45
        btn_gap = 8
        clickable = []
        for name, desc, cost, fn in upgrades:
            can_afford = state.gold >= cost
            is_maxed = (name == "Multi-shot" and state.multishot >= 4) or \
                       (name == "Crit Chance" and state.crit_chance >= 0.5) or \
                       (name == "Crit Mult" and state.crit_mult >= 5.0)

            color = UPGRADE_MAXED if is_maxed else (UPGRADE_BTN_HOVER if can_afford else UPGRADE_BTN)
            rect = pygame.Rect(panel_x + 10, y, panel_w - 20, btn_h)
            pygame.draw.rect(screen, color, rect, border_radius=5)
            pygame.draw.rect(screen, PANEL_BORDER, rect, 1, border_radius=5)

            name_text = font.render(name, True, TEXT_COLOR)
            screen.blit(name_text, (panel_x + 18, y + 5))

            if is_maxed:
                cost_text = font.render("MAXED", True, (150, 255, 150))
            else:
                cost_text = font.render(f"💰 {cost}", True, GOLD_COLOR if can_afford else (150, 120, 80))
            screen.blit(cost_text, (panel_x + 18, y + 22))

            if not is_maxed:
                clickable.append((rect, fn))

            y += btn_h + btn_gap

        return clickable
    else:
        x = panel_x + 10
        y = panel_y + 40
        btn_w = 130
        btn_h = 40
        btn_gap = 8
        clickable = []
        for name, desc, cost, fn in upgrades:
            can_afford = state.gold >= cost
            is_maxed = (name == "Multi-shot" and state.multishot >= 4) or \
                       (name == "Crit Chance" and state.crit_chance >= 0.5) or \
                       (name == "Crit Mult" and state.crit_mult >= 5.0)

            color = UPGRADE_MAXED if is_maxed else (UPGRADE_BTN_HOVER if can_afford else UPGRADE_BTN)
            rect = pygame.Rect(x, y, btn_w, btn_h)
            pygame.draw.rect(screen, color, rect, border_radius=5)
            pygame.draw.rect(screen, PANEL_BORDER, rect, 1, border_radius=5)

            name_text = font.render(name, True, TEXT_COLOR)
            screen.blit(name_text, (x + 8, y + 3))

            if is_maxed:
                cost_text = font.render("MAXED", True, (150, 255, 150))
            else:
                cost_text = font.render(f"💰{cost}", True, GOLD_COLOR if can_afford else (150, 120, 80))
            screen.blit(cost_text, (x + 8, y + 20))

            if not is_maxed:
                clickable.append((rect, fn))

            x += btn_w + btn_gap
        return clickable

def draw_powerup_panel(screen, font, state):
    """Draw permanent power-up shop"""
    panel_x = 10
    panel_y = HEIGHT - 140 if UPGRADE_PANEL_SIDE != "bottom" else HEIGHT - 280
    panel_w = PLAY_AREA_W - 20 if UPGRADE_PANEL_SIDE != "right" else PLAY_AREA_W - 20
    panel_h = 130

    pygame.draw.rect(screen, (20, 25, 35), (panel_x, panel_y, panel_w, panel_h), border_radius=8)
    pygame.draw.rect(screen, PANEL_BORDER, (panel_x, panel_y, panel_w, panel_h), 2, border_radius=8)

    title = font.render("POWER-UPS", True, (255, 100, 255))
    screen.blit(title, (panel_x + 10, panel_y + 5))

    powerups = [
        ("Dmg Boost", f"{state.damage_boost:.1f}x", 300 * int(state.damage_boost), state.buy_damage_boost, state.damage_boost < 3.0),
        ("Speed Boost", f"{state.fire_rate_boost:.1f}x", 350 * int(state.fire_rate_boost), state.buy_fire_rate_boost, state.fire_rate_boost < 3.0),
        ("Life Steal", f"+{state.life_steal}", 400 + state.life_steal * 300, state.buy_life_steal, state.life_steal < 5),
        ("Pierce", f"+{state.pierce_count}", 500 + state.pierce_count * 400, state.buy_pierce, state.pierce_count < 3),
        ("Shield", "Active" if state.has_shield else "Buy", 250, state.buy_shield, not state.has_shield),
    ]

    x = panel_x + 10
    y = panel_y + 30
    btn_w = 135
    btn_h = 45
    btn_gap = 6
    clickable = []

    for name, level, cost, fn, can_buy in powerups:
        can_afford = state.gold >= cost and can_buy
        is_maxed = not can_buy

        color = UPGRADE_MAXED if is_maxed else (UPGRADE_BTN_HOVER if can_afford else UPGRADE_BTN)
        rect = pygame.Rect(x, y, btn_w, btn_h)
        pygame.draw.rect(screen, color, rect, border_radius=5)
        pygame.draw.rect(screen, PANEL_BORDER, rect, 1, border_radius=5)

        name_text = font.render(name, True, TEXT_COLOR)
        screen.blit(name_text, (x + 6, y + 3))

        level_text = font.render(level, True, (180, 180, 200))
        screen.blit(level_text, (x + 6, y + 20))

        if not is_maxed:
            cost_text = font.render(f"💰{cost}", True, GOLD_COLOR if can_afford else (150, 120, 80))
            screen.blit(cost_text, (x + 6, y + 32))
            clickable.append((rect, fn))

        x += btn_w + btn_gap

    return clickable

def draw_ability_bar(screen, font, state):
    """Draw active ability cooldowns"""
    bar_y = 60
    bar_h = 50
    bar_x = 10
    abilities = [
        ("1", state.abilities["bomb"]),
        ("2", state.abilities["heal"]),
        ("3", state.abilities["freeze"]),
        ("4", state.abilities["rage"]),
    ]

    btn_size = 45
    gap = 8
    for key, ab in abilities:
        x = bar_x
        rect = pygame.Rect(x, bar_y, btn_size, btn_size)

        # Background
        if ab["ready"]:
            pygame.draw.rect(screen, (60, 100, 60), rect, border_radius=5)
        else:
            pygame.draw.rect(screen, (60, 60, 60), rect, border_radius=5)
            # Cooldown overlay
            pct = ab["cooldown"] / ab["max_cooldown"]
            overlay_h = int(btn_size * pct)
            pygame.draw.rect(screen, (40, 40, 40), (x, bar_y, btn_size, overlay_h), border_radius=5)

        pygame.draw.rect(screen, PANEL_BORDER, rect, 2, border_radius=5)

        # Icon
        icon_font = pygame.font.SysFont("Segoe UI", 20)
        icon = icon_font.render(ab["icon"], True, TEXT_COLOR)
        screen.blit(icon, (x + btn_size//2 - icon.get_width()//2, bar_y + 5))

        # Key label
        key_text = font.render(key, True, TEXT_DIM)
        screen.blit(key_text, (x + 3, bar_y + btn_size - 16))

        # Cooldown text
        if not ab["ready"]:
            cd_text = font.render(f"{ab['cooldown']:.0f}", True, (255, 100, 100))
            screen.blit(cd_text, (x + btn_size - cd_text.get_width() - 3, bar_y + btn_size - 16))

        bar_x += btn_size + gap

    return []  # No clickable abilities for now

def draw_active_effects(screen, font, state):
    """Draw rage/freeze timers"""
    effects = []
    if state.rage_timer > 0:
        effects.append(("RAGE", state.rage_timer, (255, 80, 80)))
    if state.frozen_timer > 0:
        effects.append(("FREEZE", state.frozen_timer, (100, 200, 255)))

    x = PLAY_AREA_W - 150
    y = 60
    for name, timer, color in effects:
        text = font.render(f"{name}: {timer:.1f}s", True, color)
        screen.blit(text, (x, y))
        y += 20

def draw_top_bar(screen, font, state):
    bar_h = 50
    bar_w = PLAY_AREA_W
    pygame.draw.rect(screen, (20, 25, 40), (0, 0, bar_w, bar_h))
    pygame.draw.line(screen, PANEL_BORDER, (0, bar_h), (bar_w, bar_h), 2)

    # Left: Gold + Wave number
    gold_text = font.render(f"💰{state.gold}", True, GOLD_COLOR)
    screen.blit(gold_text, (15, 8))

    wave_text = font.render(f"Wave {state.wave}", True, TEXT_COLOR)
    screen.blit(wave_text, (15, 26))

    # Center: Tower HP bar
    hp_pct = state.tower_hp / state.tower_max_hp
    hp_bar_w = 180
    hp_bar_h = 18
    hp_bar_x = bar_w // 2 - hp_bar_w // 2
    hp_bar_y = 14
    pygame.draw.rect(screen, HP_BAR_BG, (hp_bar_x, hp_bar_y, hp_bar_w, hp_bar_h))
    hp_color = HP_BAR_RED if hp_pct < 0.3 else HP_BAR_FG
    pygame.draw.rect(screen, hp_color, (hp_bar_x, hp_bar_y, int(hp_bar_w * hp_pct), hp_bar_h))
    hp_text = font.render(f"{int(state.tower_hp)}/{state.tower_max_hp}", True, TEXT_COLOR)
    screen.blit(hp_text, (hp_bar_x + hp_bar_w//2 - hp_text.get_width()//2, hp_bar_y - 1))

    # Right: Wave status
    if state.wave_active:
        status = font.render("⚔️ ACTIVE", True, (255, 100, 100))
    else:
        cd = max(0, state.wave_cooldown)
        status = font.render(f"Next: {cd:.1f}s", True, (100, 255, 100))
    status_x = bar_w - status.get_width() - 20
    screen.blit(status, (status_x, 14))

def spawn_enemy(state):
    edge = random.choice(["top", "bottom", "left", "right"])
    max_x = PLAY_AREA_W - 60 if UPGRADE_PANEL_SIDE == "right" else WIDTH - 60
    if edge == "top":
        x, y = random.randint(50, max_x), -20
    elif edge == "bottom":
        x, y = random.randint(50, max_x), HEIGHT + 20
    elif edge == "left":
        x, y = -20, random.randint(50, HEIGHT - 50)
    else:
        x, y = max_x + 40, random.randint(50, HEIGHT - 50)

    r = random.random()
    if r < 0.5:
        etype = "basic"
        hp_mult = 1.0
        speed_mult = 1.0
    elif r < 0.8:
        etype = "swarm"
        hp_mult = 0.5
        speed_mult = 1.5
    else:
        etype = "tank"
        hp_mult = 3.0
        speed_mult = 0.6

    hp = state.get_enemy_hp() * hp_mult
    speed = state.get_enemy_speed() * speed_mult
    return Enemy(x, y, hp, speed, etype)

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
    powerup_buttons = []
    drops = []  # Power-up drops on ground

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    state.paused = not state.paused
                if event.key == pygame.K_SPACE and not state.wave_active and not state.game_over:
                    state.start_wave()
                if event.key == pygame.K_r and state.game_over:
                    state.reset()
                    drops = []
                # Active abilities: 1-4
                if not state.paused and not state.game_over:
                    if event.key == pygame.K_1:
                        kills = state.use_bomb()
                        if kills > 0:
                            state.floating_texts.append(FloatingText(CENTER_X, CENTER_Y, f"BOOM! {kills} kills", (255, 200, 50), 30))
                    if event.key == pygame.K_2:
                        heal = state.use_heal()
                        if heal > 0:
                            state.floating_texts.append(FloatingText(CENTER_X, CENTER_Y - 30, f"+{int(heal)} HP", (100, 255, 100), 24))
                    if event.key == pygame.K_3:
                        if state.use_freeze():
                            state.floating_texts.append(FloatingText(CENTER_X, CENTER_Y, "FREEZE!", (100, 200, 255), 30))
                    if event.key == pygame.K_4:
                        if state.use_rage():
                            state.floating_texts.append(FloatingText(CENTER_X, CENTER_Y, "RAGE MODE!", (255, 80, 80), 32))
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if state.game_over:
                    state.reset()
                    drops = []
                    continue
                mx, my = pygame.mouse.get_pos()
                # Check upgrade buttons
                for btn_rect, upgrade_fn in upgrade_buttons:
                    if btn_rect.collidepoint(mx, my):
                        if upgrade_fn(state):
                            state.floating_texts.append(FloatingText(mx, my, "UPGRADED!", (100, 255, 100), 20))
                        break
                # Check power-up buttons
                for btn_rect, powerup_fn in powerup_buttons:
                    if btn_rect.collidepoint(mx, my):
                        if powerup_fn(state):
                            state.floating_texts.append(FloatingText(mx, my, "POWER UP!", (255, 100, 255), 20))
                        break
                # Check drops
                for drop in drops[:]:
                    if math.hypot(drop.x - mx, drop.y - my) < drop.radius + 10:
                        # Apply drop effect
                        if drop.type == "heal":
                            heal = min(state.tower_max_hp - state.tower_hp, 25)
                            state.tower_hp += heal
                            state.floating_texts.append(FloatingText(drop.x, drop.y, f"+{int(heal)} HP", (255, 100, 200), 20))
                        elif drop.type == "gold":
                            gold = 25 + state.wave * 5
                            state.gold += gold
                            state.floating_texts.append(FloatingText(drop.x, drop.y, f"+${gold}", GOLD_COLOR, 22))
                        elif drop.type == "damage":
                            state.damage += 3
                            state.floating_texts.append(FloatingText(drop.x, drop.y, "+3 DMG!", (255, 100, 100), 20))
                        elif drop.type == "speed":
                            state.fire_rate += 0.2
                            state.floating_texts.append(FloatingText(drop.x, drop.y, "+SPD!", (100, 255, 100), 20))
                        elif drop.type == "shield":
                            state.has_shield = True
                            state.floating_texts.append(FloatingText(drop.x, drop.y, "SHIELD!", (100, 150, 255), 20))
                        drops.remove(drop)
                        break

        # Auto-start next wave after cooldown
        if not state.wave_active and not state.game_over and state.wave_cooldown > 0:
            state.wave_cooldown -= dt
            if state.wave_cooldown <= 0:
                state.start_wave()

        # Main game logic
        if not state.paused and not state.game_over:
            # Update active effect timers
            if state.rage_timer > 0:
                state.rage_timer -= dt
            if state.frozen_timer > 0:
                state.frozen_timer -= dt
                if state.frozen_timer <= 0:
                    # Unfreeze all enemies
                    for e in state.enemies:
                        e.frozen = False

            # Update ability cooldowns
            for ab in state.abilities.values():
                if not ab["ready"]:
                    ab["cooldown"] -= dt
                    if ab["cooldown"] <= 0:
                        ab["ready"] = True
                        ab["cooldown"] = 0

            # Tower shooting
            now = time.time()
            if now - state.last_shot >= state.get_fire_cooldown():
                targets = []
                for e in state.enemies:
                    dist = math.hypot(e.x - CENTER_X, e.y - CENTER_Y)
                    if dist <= state.range_radius and e.hp > 0:
                        targets.append((dist, e))

                if targets:
                    targets.sort(key=lambda x: x[0])
                    state.last_shot = now

                    for i in range(min(state.multishot, len(targets))):
                        target = targets[i][1]
                        is_crit = random.random() < state.crit_chance
                        base_dmg = state.get_total_damage()
                        dmg = base_dmg * state.crit_mult if is_crit else base_dmg
                        state.projectiles.append(Projectile(CENTER_X, CENTER_Y, target, dmg))

            # Spawn enemies during wave
            if state.wave_active:
                state.wave_spawn_timer -= dt
                if state.wave_spawn_timer <= 0 and state.wave_enemies_remaining > 0:
                    state.enemies.append(spawn_enemy(state))
                    state.wave_enemies_remaining -= 1
                    state.wave_spawn_timer = max(0.2, 1.0 - state.wave * 0.03)

                if state.wave_enemies_remaining <= 0 and len(state.enemies) == 0:
                    state.wave_active = False
                    state.wave += 1
                    state.gold += 50 + state.wave * 10
                    state.wave_cooldown = 3.0  # 3 seconds to next wave

            # Update enemies
            for e in state.enemies[:]:
                dist = e.move_toward(CENTER_X, CENTER_Y, dt)
                if dist < 25:
                    e.hp = 0
                    # Shield absorbs one hit
                    if state.has_shield:
                        state.has_shield = False
                        state.floating_texts.append(FloatingText(CENTER_X, CENTER_Y, "SHIELD BROKEN!", (100, 150, 255), 24))
                        for _ in range(10):
                            state.particles.append(Particle(CENTER_X, CENTER_Y, (100, 150, 255)))
                    else:
                        state.tower_hp -= 10
                        state.floating_texts.append(FloatingText(CENTER_X, CENTER_Y - 20, "-10", (255, 50, 50), 20))
                        if state.tower_hp <= 0:
                            state.tower_hp = 0
                            state.game_over = True
                    for _ in range(5):
                        state.particles.append(Particle(e.x, e.y, (255, 50, 50)))

            # Update projectiles
            for p in state.projectiles[:]:
                p.update(dt)
                if not p.active:
                    # Check if we hit something
                    if p.target and p.target.hp <= 0 and not p.target.reached:
                        p.target.reached = True
                        gold_gain = 5 + state.wave
                        state.gold += gold_gain
                        # Life steal
                        if state.life_steal > 0:
                            heal = state.life_steal * 2
                            state.tower_hp = min(state.tower_hp + heal, state.tower_max_hp)
                        for _ in range(8):
                            state.particles.append(Particle(p.target.x, p.target.y, GOLD_COLOR))
                        state.floating_texts.append(FloatingText(p.target.x, p.target.y, f"+${gold_gain}", GOLD_COLOR, 22))

                        # Chance to drop power-up (10%)
                        if random.random() < 0.1:
                            drop_type = random.choice(["heal", "gold", "damage", "speed", "shield"])
                            drops.append(PowerUpDrop(p.target.x, p.target.y, drop_type))
                    else:
                        state.floating_texts.append(FloatingText(p.target.x, p.target.y, f"-{int(p.damage)}", (255, 80, 80), 18))
                    state.projectiles.remove(p)

            # Cleanup enemies
            state.enemies = [e for e in state.enemies if e.hp > 0]

            # Update drops
            for drop in drops[:]:
                drop.update(dt)
                if drop.life <= 0:
                    drops.remove(drop)

            # Update particles
            for p in state.particles[:]:
                p.update(dt)
                if p.life <= 0:
                    state.particles.remove(p)

            # Update floating texts
            for ft in state.floating_texts[:]:
                ft.update(dt)
                if ft.life <= 0:
                    state.floating_texts.remove(ft)

            # Update wave popup
            if state.wave_popup:
                state.wave_popup["life"] -= dt
                if state.wave_popup["life"] <= 0:
                    state.wave_popup = None

        # ── RENDER ──
        screen.fill(BG)

        # Grid lines
        for i in range(0, PLAY_AREA_W, 50):
            pygame.draw.line(screen, GRID_COLOR, (i, 50), (i, HEIGHT), 1)
        for i in range(50, HEIGHT, 50):
            pygame.draw.line(screen, GRID_COLOR, (0, i), (PLAY_AREA_W, i), 1)

        # Draw particles
        for p in state.particles:
            p.draw(screen)

        # Draw floating texts
        for ft in state.floating_texts:
            ft.draw(screen)

        # Draw drops
        for drop in drops:
            drop.draw(screen)

        # Draw enemies
        for e in state.enemies:
            e.draw(screen)

        # Draw projectiles
        for p in state.projectiles:
            p.draw(screen)

        # Draw tower
        draw_tower(screen, state)

        # Draw wave popup
        if state.wave_popup:
            popup = state.wave_popup
            progress = popup["life"] / popup["max_life"]
            if progress > 0.85:
                alpha = int(255 * (1 - progress) / 0.15)
            else:
                alpha = int(255 * min(1.0, progress / 0.5))

            popup_font = pygame.font.SysFont("Segoe UI", 48, bold=True)
            text = popup_font.render(popup["text"], True, (255, 200, 80))
            text.set_alpha(alpha)
            x = PLAY_AREA_W // 2 - text.get_width() // 2
            y = HEIGHT // 2 - 80
            screen.blit(text, (x, y))

            sub_font = pygame.font.SysFont("Segoe UI", 20)
            sub = sub_font.render("INCOMING!", True, (255, 100, 100))
            sub.set_alpha(alpha)
            sx = PLAY_AREA_W // 2 - sub.get_width() // 2
            screen.blit(sub, (sx, y + 55))

        # UI
        draw_top_bar(screen, font, state)
        draw_ability_bar(screen, font_sm, state)
        draw_active_effects(screen, font_sm, state)
        upgrade_buttons = draw_upgrade_panel(screen, font_sm, state)

        # Power-up panel (only show if enough gold or have power-ups)
        if state.gold >= 250 or state.damage_boost > 1.0 or state.fire_rate_boost > 1.0 or state.life_steal > 0 or state.pierce_count > 0 or state.has_shield:
            powerup_buttons = draw_powerup_panel(screen, font_sm, state)
        else:
            powerup_buttons = []

        # Game over
        if state.game_over:
            overlay = pygame.Surface((WIDTH, HEIGHT))
            overlay.fill((0, 0, 0))
            overlay.set_alpha(180)
            screen.blit(overlay, (0, 0))

            go_text = font_lg.render("GAME OVER", True, (255, 80, 80))
            screen.blit(go_text, (WIDTH//2 - go_text.get_width()//2, HEIGHT//2 - 50))

            wave_text = font.render(f"You survived {state.wave - 1} waves", True, TEXT_COLOR)
            screen.blit(wave_text, (WIDTH//2 - wave_text.get_width()//2, HEIGHT//2 + 20))

            restart_text = font.render("Press R or Click to Restart", True, GOLD_COLOR)
            screen.blit(restart_text, (WIDTH//2 - restart_text.get_width()//2, HEIGHT//2 + 60))

        # Pause
        if state.paused:
            overlay = pygame.Surface((WIDTH, HEIGHT))
            overlay.fill((0, 0, 0))
            overlay.set_alpha(120)
            screen.blit(overlay, (0, 0))
            pause_text = font_lg.render("PAUSED", True, TEXT_COLOR)
            screen.blit(pause_text, (WIDTH//2 - pause_text.get_width()//2, HEIGHT//2 - 20))

        pygame.display.flip()

    pygame.quit()

if __name__ == "__main__":
    main()
