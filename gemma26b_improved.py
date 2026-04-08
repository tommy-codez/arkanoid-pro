import pygame
import math
import random
import struct

# --- KONFIGURATION & KONSTANTEN ---
WIDTH, HEIGHT = 800, 600
FPS = 60
PADDLE_WIDTH, PADDLE_HEIGHT = 100, 15
BALL_RADIUS = 8
BRICK_ROWS = 5
BRICK_COLS = 10
BRICK_PADDING = 5
BRICK_HEIGHT = 25

# Farben
COLOR_BG = (15, 15, 25)
COLOR_PADDLE = (0, 200, 255)
COLOR_BALL = (255, 255, 255)
COLOR_TEXT = (240, 240, 240)

# --- AUDIO MANAGER ---
class SoundManager:
    def __init__(self):
        try:
            pygame.mixer.pre_init(44100, -16, 2, 512)
            pygame.mixer.init()
            self.sample_rate = 44100
        except Exception as e:
            print(f"Audio-Fehler: {e}")
            self.sample_rate = None

    def _generate_wave(self, func, duration, volume=0.5):
        if not self.sample_rate: return None
        n_samples = int(self.sample_rate * duration)
        buf = bytearray()
        for i in range(n_samples):
            t = i / self.sample_rate
            val = func(t) * volume
            sample = int(max(-1, min(1, val)) * 32767)
            buf.extend(struct.pack('<h', sample))
            buf.extend(struct.pack('<h', sample))
        return pygame.mixer.Sound(buffer=buf)

    def play_ping(self):
        def sine_sweep(t): return math.sin(2 * math.pi * (600 + t*400) * t)
        snd = self._generate_wave(sine_sweep, 0.1, 0.3)
        if snd: snd.play()

    def play_explosion(self):
        def thud(t): return math.sin(2 * math.pi * (150 * math.exp(-t*10)) * t) * math.exp(-t*8)
        snd = self._generate_wave(thud, 0.15, 0.5)
        if snd: snd.play()

    def play_powerup(self):
        def chirp(t): return math.sin(2 * math.pi * (400 + math.sin(t*25)*200) * t)
        snd = self._generate_wave(chirp, 0.3, 0.2)
        if snd: snd.play()

    def play_laser(self):
        def laser(t): return math.sin(2 * math.pi * (1000 - t*500) * t)
        snd = self._generate_wave(laser, 0.1, 0.3)
        if snd: snd.play()

# --- OBJEKT-KLASSEN ---

class Particle:
    def __init__(self, x, y, color):
        self.x, self.y = x, y
        self.vx = random.uniform(-3, 3)
        self.vy = random.uniform(-5, -1)
        self.life = 1.0
        self.decay = random.uniform(0.02, 0.04)
        self.color = color

    def update(self):
        self.vy += 0.2
        self.x += self.vx
        self.y += self.vy
        self.life -= self.decay

    def draw(self, surface):
        alpha = max(0, int(self.life * 255))
        s = pygame.Surface((4, 4))
        s.set_alpha(alpha)
        s.fill(self.color)
        surface.blit(s, (self.x, self.y))

class Ball:
    def __init__(self, x, y, speed_multiplier, is_ghost=False, is_fire=False):
        self.base_speed = 4.0 * speed_multiplier
        angle = random.uniform(math.pi/4, 3*math.pi/4)
        self.dx = math.cos(angle) * self.base_speed
        self.dy = -math.sin(angle) * self.base_speed
        
        self.rect = pygame.Rect(x, y, BALL_RADIUS*2, BALL_RADIUS*2)
        self.is_ghost = is_ghost
        self.is_fire = is_fire
        self.stuck = False
        self.relative_x = 0

    def update(self, paddle, time_scale):
        if self.stuck:
            self.rect.centerx = paddle.rect.centerx + self.relative_x
            self.rect.centery = paddle.rect.top - BALL_RADIUS
            return

        self.rect.x += self.dx * time_scale
        self.rect.y += self.dy * time_scale

        if self.rect.left <= 0 or self.rect.right >= WIDTH:
            self.dx *= -1
        if self.rect.top <= 0:
            self.dy *= -1
        
    def draw(self, surface):
        if self.is_fire: color, alpha = (255, 100, 0), 255
        elif self.is_ghost: color, alpha = (200, 200, 255), 130
        else: color, alpha = COLOR_BALL, 255
        
        s = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
        pygame.draw.ellipse(s, (*color, alpha), (0, 0, self.rect.width, self.rect.height))
        surface.blit(s, self.rect.topleft)

class Brick:
    def __init__(self, x, y, w, h, color):
        self.rect = pygame.Rect(x, y, w, h)
        self.color = color

class Powerup:
    def __init__(self, x, y, type_char):
        self.rect = pygame.Rect(x, y, 25, 25)
        self.type = type_char 
        self.speed = 3

    def update(self):
        self.rect.y += self.speed

    def draw(self, surface):
        colors = {'M': (0, 255, 0), 'T': (255, 255, 0), 'G': (150, 150, 255), 
                  'L': (255, 0, 0), 'W': (0, 255, 255), 'F': (255, 69, 0), 'S': (200, 200, 200)}
        pygame.draw.rect(surface, colors[self.type], self.rect)
        font = pygame.font.SysFont("Arial", 18, bold=True)
        txt = font.render(self.type, True, (0,0,0))
        surface.blit(txt, (self.rect.x + 5, self.rect.y + 2))

class Projectile:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 5, 15)
        self.speed = -8
    def update(self): self.rect.y += self.speed

class Paddle:
    def __init__(self):
        self.width = PADDLE_WIDTH
        self.rect = pygame.Rect(WIDTH//2 - PADDLE_WIDTH//2, HEIGHT - 40, PADDLE_WIDTH, PADDLE_HEIGHT)
        self.vel_x = 0
        self.accel = 0.8
        self.friction = 0.85
        self.max_speed = 9

    def update(self):
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]: self.vel_x -= self.accel
        elif keys[pygame.K_RIGHT]: self.vel_x += self.accel
        else: self.vel_x *= self.friction

        if abs(self.vel_x) > self.max_speed: self.vel_x = math.copysign(self.max_speed, self.vel_x)
        self.rect.x += self.vel_x
        if self.rect.left < 0: self.rect.left = 0; self.vel_x = 0
        if self.rect.right > WIDTH: self.rect.right = WIDTH; self.vel_x = 0

    def draw(self, surface):
        pygame.draw.rect(surface, COLOR_PADDLE, self.rect, border_radius=5)

# --- GAME ENGINE ---

class ArkanoidGame:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Arkanoid Pro - Ultimate Edition")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Arial", 24)
        self.small_font = pygame.font.SysFont("Arial", 18, bold=True)
        self.sound = SoundManager()
        self.highscore = 0
        self.shake_timer = 0
        self.reset_game()

    def reset_game(self):
        """Kompletter Reset (Game Over Szenario)"""
        self.level = 1
        self.score = 0
        self.lives = 3  # Start mit 3 Leben
        self.paddle = Paddle()
        self.balls = []
        self.bricks = []
        self.particles = []
        self.powerups = []
        self.projectiles = []
        self.magnet_timer = 0
        self.ghost_timer = 0
        self.laser_timer = 0
        self.wide_timer = 0
        self.slow_timer = 0
        self._spawn_ball_for_current_level()
        self.generate_level()

    def _spawn_ball_for_current_level(self):
        """Spawnt einen neuen Ball basierend auf dem aktuellen Level-Faktor."""
        speed_mult = 1.0 + (self.level - 1) * 0.15
        self.balls = [Ball(WIDTH//2, HEIGHT-60, speed_mult)]

    def generate_level(self):
        self.bricks = []
        colors = [(255, 50, 50), (50, 255, 50), (50, 50, 255), (255, 255, 50), (255, 50, 255)]
        w = (WIDTH - (BRICK_COLS + 1) * BRICK_PADDING) // BRICK_COLS
        for r in range(BRICK_ROWS):
            for c in range(BRICK_COLS):
                x = c * (w + BRICK_PADDING) + BRICK_PADDING
                y = r * (BRICK_HEIGHT + BRICK_PADDING) + 60
                self.bricks.append(Brick(x, y, w, BRICK_HEIGHT, random.choice(colors)))

    def trigger_shake(self, duration): self.shake_timer = duration

    def handle_collisions(self):
        time_scale = 0.5 if self.slow_timer > 0 else 1.0

        for ball in self.balls:
            if not ball.stuck and ball.rect.colliderect(self.paddle.rect):
                if self.magnet_timer > 0:
                    ball.stuck = True
                    ball.relative_x = ball.rect.centerx - self.paddle.rect.centerx
                else:
                    diff = (ball.rect.centerx - self.paddle.rect.centerx) / (self.paddle.width/2)
                    ball.dx = diff * 7
                    ball.dy = -abs(ball.dy)
                self.trigger_shake(4)
                self.sound.play_ping()

            for brick in self.bricks[:]:
                if ball.rect.colliderect(brick.rect):
                    for _ in range(10):
                        self.particles.append(Particle(brick.rect.centerx, brick.rect.centery, brick.color))
                    self.score += 10
                    self.bricks.remove(brick)
                    self.sound.play_explosion()
                    self.trigger_shake(3)

                    if random.random() < 0.2:
                        ptype = random.choice(['M', 'T', 'G', 'L', 'W', 'F', 'S'])
                        self.powerups.append(Powerup(brick.rect.centerx, brick.rect.centery, ptype))

                    if not ball.is_ghost and not ball.is_fire:
                        ball.dy *= -1
                    break 

        for pu in self.powerups[:]:
            if pu.rect.colliderect(self.paddle.rect):
                self.apply_powerup(pu.type)
                self.powerups.remove(pu)
                self.sound.play_powerup()

        for proj in self.projectiles[:]:
            hit = False
            for brick in self.bricks[:]:
                if proj.rect.colliderect(brick.rect):
                    self.bricks.remove(brick)
                    hit = True
                    self.sound.play_explosion()
                    break
            if hit: self.projectiles.remove(proj)
            elif proj.rect.bottom < 0: self.projectiles.remove(proj)

    def apply_powerup(self, ptype):
        if ptype == 'M': self.magnet_timer = 30 * FPS
        elif ptype == 'T':
            count = len(self.balls)
            speed_mult = 1.0 + (self.level - 1) * 0.15
            for _ in range(count): self.balls.append(Ball(self.paddle.rect.centerx, self.paddle.rect.top, speed_mult))
        elif ptype == 'G':
            for b in self.balls: b.is_ghost = True
            self.ghost_timer = 30 * FPS
        elif ptype == 'L': self.laser_timer = 10 * FPS
        elif ptype == 'W':
            self.paddle.width = 180
            self.paddle.rect.width = 180
            self.wide_timer = 20 * FPS
        elif ptype == 'F':
            for b in self.balls: b.is_fire = True
            self.ghost_timer = 15 * FPS 
        elif ptype == 'S': self.slow_timer = 10 * FPS

    def update(self):
        if self.magnet_timer > 0: self.magnet_timer -= 1
        if self.laser_timer > 0: self.laser_timer -= 1
        if self.slow_timer > 0: self.slow_timer -= 1
        if self.wide_timer > 0:
            self.wide_timer -= 1
            if self.wide_timer <= 0:
                self.paddle.width = PADDLE_WIDTH
                self.paddle.rect.width = PADDLE_WIDTH
        if self.ghost_timer > 0:
            self.ghost_timer -= 1
            if self.ghost_timer <= 0:
                for b in self.balls: 
                    b.is_ghost = False
                    b.is_fire = False

        time_scale = 0.5 if self.slow_timer > 0 else 1.0
        self.paddle.update()
        
        for ball in self.balls[:]:
            ball.update(self.paddle, time_scale)
            if ball.rect.top > HEIGHT: self.balls.remove(ball)

        for pu in self.powerups[:]:
            pu.update()
            if pu.rect.top > HEIGHT: self.powerups.remove(pu)
        
        for proj in self.projectiles[:]: proj.update()
        for p in self.particles[:]:
            p.update()
            if p.life <= 0: self.particles.remove(p)

        self.handle_collisions()

        # Level Clear Check
        if not self.bricks:
            self.level += 1
            self._spawn_ball_for_current_level()
            self.generate_level()

        # Life / Game Over Check
        if not self.balls:
            self.lives -= 1
            if self.lives > 0:
                # Ball verloren, aber Leben noch da -> Respawn im aktuellen Level
                self._spawn_ball_for_current_level()
                self.trigger_shake(15) # Starker Shake bei Lebensverlust
            else:
                # Game Over
                if self.score > self.highscore: self.highscore = self.score
                self.reset_game()

    def draw(self):
        off_x, off_y = 0, 0
        if self.shake_timer > 0:
            off_x, off_y = random.randint(-3, 3), random.randint(-3, 3)
            self.shake_timer -= 1

        self.screen.fill(COLOR_BG)
        for b in self.bricks: pygame.draw.rect(self.screen, b.color, b.rect.move(off_x, off_y))
        for p in self.particles: p.draw(self.screen)
        for pu in self.powerups: pu.draw(self.screen)
        for proj in self.projectiles: pygame.draw.rect(self.screen, (255, 0, 0), proj.rect.move(off_x, off_y))
        for ball in self.balls: ball.draw(self.screen)
        self.paddle.draw(self.screen)

        # UI - Score, Level, Lives, Highscore
        ui_txt = self.font.render(f"Score: {self.score}  Level: {self.level}  Lives: {self.lives}  High: {self.highscore}", True, COLOR_TEXT)
        self.screen.blit(ui_txt, (10, 10))

        # Powerup Timer Anzeige
        y_off = 40
        timers = [
            (self.magnet_timer, "MAGNET", (0,255,0)),
            (self.ghost_timer, "GHOST/FIRE", (150,150,255)),
            (self.laser_timer, "LASER", (255,0,0)),
            (self.wide_timer, "WIDE", (0,255,255)),
            (self.slow_timer, "SLOW-MO", (200,200,200))
        ]
        for t_val, name, col in timers:
            if t_val > 0:
                txt = self.small_font.render(f"{name}: {t_val//60}s", True, col)
                self.screen.blit(txt, (10, y_off))
                y_off += 20

        pygame.display.flip()

def main():
    game = ArkanoidGame()
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    released = False
                    for ball in game.balls:
                        if ball.stuck:
                            ball.stuck = False
                            ball.dy = -5
                            ball.dx = (ball.relative_x / 10) + game.paddle.vel_x * 2
                            released = True
                    if released: game.sound.play_ping()
                    if game.laser_timer > 0:
                        game.projectiles.append(Projectile(game.paddle.rect.centerx, game.paddle.rect.top))
                        game.sound.play_laser()

        game.update()
        game.draw()
        game.clock.tick(FPS)
    pygame.quit()

if __name__ == "__main__":
    main()

