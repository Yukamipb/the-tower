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
        self.tower_hp = 100
        self.tower_max_hp = 100
        self.enemies = []
        self.projectiles = []
        self.particles = []
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
        
    def get_fire_cooldown(self):
        return 1.0 / self.fire_rate
        
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
        
    def start_wave(self):
        self.wave_active = True
        self.wave_enemies_remaining = 10 + self.wave * 3
        self.wave_spawn_timer = 0
        
    def get_enemy_hp(self):
        return 10 + self.wave * 2
        
    def get_enemy_speed(self):
        return 1.0 + self.wave * 0.05

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
        
    def move_toward(self, tx, ty, dt):
        dx = tx - self.x
        dy = ty - self.y
        dist = math.hypot(dx, dy)
        if dist > 0:
            self.x += (dx / dist) * self.speed * 60 * dt
            self.y += (dy / dist) * self.speed * 60 * dt
        return dist
        
    def draw(self, screen):
        if ENEMY_SHAPE == "square":
            size = self.radius * 2
            rect = pygame.Rect(int(self.x - size//2), int(self.y - size//2), size, size)
            pygame.draw.rect(screen, self.color, rect)
            pygame.draw.rect(screen, (255, 255, 255), rect, 1)
        else:
            pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), self.radius)
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
        
    def update(self, dt):
        if not self.active or self.target.hp <= 0:
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

# ── DRAWING ─────────────────────────────────────────────
def draw_tower(screen, state):
    tower_r = 20 + state.multishot * 3
    
    if TOWER_SHAPE == "hexagon":
        points = []
        for i in range(6):
            angle = math.radians(i * 60 - 30)
            px = CENTER_X + math.cos(angle) * tower_r
            py = CENTER_Y + math.sin(angle) * tower_r
            points.append((px, py))
        pygame.draw.polygon(screen, TOWER_COLOR, points)
        pygame.draw.polygon(screen, TOWER_OUTLINE, points, 2)
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
        for name, desc, cost, _ in upgrades:
            can_afford = state.gold >= cost
            is_maxed = (name == "Multi-shot" and state.multishot >= 4) or \
                       (name == "Crit Chance" and state.crit_chance >= 0.5) or \
                       (name == "Crit Mult" and state.crit_mult >= 5.0)
            
            color = UPGRADE_MAXED if is_maxed else (UPGRADE_BTN_HOVER if can_afford else UPGRADE_BTN)
            pygame.draw.rect(screen, color, (panel_x + 10, y, panel_w - 20, btn_h), border_radius=5)
            pygame.draw.rect(screen, PANEL_BORDER, (panel_x + 10, y, panel_w - 20, btn_h), 1, border_radius=5)
            
            name_text = font.render(name, True, TEXT_COLOR)
            screen.blit(name_text, (panel_x + 18, y + 5))
            
            if is_maxed:
                cost_text = font.render("MAXED", True, (150, 255, 150))
            else:
                cost_text = font.render(f"💰 {cost}", True, GOLD_COLOR if can_afford else (150, 120, 80))
            screen.blit(cost_text, (panel_x + 18, y + 22))
            
            y += btn_h + btn_gap
    else:
        # Horizontal layout for bottom
        x = panel_x + 10
        y = panel_y + 40
        btn_w = 130
        btn_h = 40
        btn_gap = 8
        for name, desc, cost, _ in upgrades:
            can_afford = state.gold >= cost
            is_maxed = (name == "Multi-shot" and state.multishot >= 4) or \
                       (name == "Crit Chance" and state.crit_chance >= 0.5) or \
                       (name == "Crit Mult" and state.crit_mult >= 5.0)
            
            color = UPGRADE_MAXED if is_maxed else (UPGRADE_BTN_HOVER if can_afford else UPGRADE_BTN)
            pygame.draw.rect(screen, color, (x, y, btn_w, btn_h), border_radius=5)
            pygame.draw.rect(screen, PANEL_BORDER, (x, y, btn_w, btn_h), 1, border_radius=5)
            
            name_text = font.render(name, True, TEXT_COLOR)
            screen.blit(name_text, (x + 8, y + 3))
            
            if is_maxed:
                cost_text = font.render("MAXED", True, (150, 255, 150))
            else:
                cost_text = font.render(f"💰{cost}", True, GOLD_COLOR if can_afford else (150, 120, 80))
            screen.blit(cost_text, (x + 8, y + 20))
            
            x += btn_w + btn_gap

def draw_top_bar(screen, font, state):
    bar_h = 50
    bar_w = PLAY_AREA_W
    pygame.draw.rect(screen, (20, 25, 40), (0, 0, bar_w, bar_h))
    pygame.draw.line(screen, PANEL_BORDER, (0, bar_h), (bar_w, bar_h), 2)
    
    # Left: Gold + Wave number (stacked or side by side compact)
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
    
    # Right: Wave status (before panel edge)
    if state.wave_active:
        status = font.render("⚔️ ACTIVE", True, (255, 100, 100))
    else:
        status = font.render("SPACE▶", True, (100, 255, 100))
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
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if state.game_over:
                    state.reset()
                    continue
                mx, my = pygame.mouse.get_pos()
                # Check upgrade buttons
                # TODO: Add click detection for upgrade buttons
        
        if state.paused or state.game_over:
            pass
        else:
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
                        dmg = state.damage * state.crit_mult if is_crit else state.damage
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
            
            # Update enemies
            for e in state.enemies[:]:
                dist = e.move_toward(CENTER_X, CENTER_Y, dt)
                if dist < 25:
                    e.hp = 0
                    state.tower_hp -= 10
                    if state.tower_hp <= 0:
                        state.tower_hp = 0
                        state.game_over = True
                    for _ in range(5):
                        state.particles.append(Particle(e.x, e.y, (255, 50, 50)))
            
            # Update projectiles
            for p in state.projectiles[:]:
                p.update(dt)
                if not p.active:
                    if p.target.hp <= 0 and not p.target.reached:
                        p.target.reached = True
                        state.gold += 5 + state.wave
                        for _ in range(8):
                            state.particles.append(Particle(p.target.x, p.target.y, GOLD_COLOR))
                    state.projectiles.remove(p)
            
            # Cleanup
            state.enemies = [e for e in state.enemies if e.hp > 0]
            
            # Update particles
            for p in state.particles[:]:
                p.update(dt)
                if p.life <= 0:
                    state.particles.remove(p)
        
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
        
        # Draw enemies
        for e in state.enemies:
            e.draw(screen)
        
        # Draw projectiles
        for p in state.projectiles:
            p.draw(screen)
        
        # Draw tower
        draw_tower(screen, state)
        
        # UI
        draw_top_bar(screen, font, state)
        draw_upgrade_panel(screen, font_sm, state)
        
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