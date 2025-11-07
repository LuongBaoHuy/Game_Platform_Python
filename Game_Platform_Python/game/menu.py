import pygame
import sys
import os
import math

ASSETS_DIR = os.path.join("assets")
FONTS_DIR = os.path.join(ASSETS_DIR, "fonts")
SFX_DIR = os.path.join(ASSETS_DIR, "sounds")
MENU_DIR = os.path.join(ASSETS_DIR, "menu")

TITLE_TEXT = "START GAME"


# ---- tiện ích ----
def load_font(name: str, size: int):
    """Ưu tiên font .ttf trong assets/fonts; nếu không có thì dùng SysFont."""
    ttf = os.path.join(FONTS_DIR, name)
    if os.path.isfile(ttf):
        return pygame.font.Font(ttf, size)
    return pygame.font.SysFont("Arial", size)


def safe_sound(path_rel: str):
    """Trả về Sound nếu tìm thấy, ngược lại None."""
    try:
        full = os.path.join(path_rel)
        if not os.path.isabs(full):
            full = os.path.join(os.getcwd(), path_rel)
        if os.path.isfile(full):
            return pygame.mixer.Sound(full)
    except Exception:
        pass
    return None


def draw_glow(surface, rect, color=(180, 240, 255), radius=18, alpha=60):
    """Vẽ glow mềm quanh rect."""
    glow = pygame.Surface(
        (rect.width + radius * 2, rect.height + radius * 2), pygame.SRCALPHA
    )
    center = (glow.get_width() // 2, glow.get_height() // 2)
    # nhiều vòng tròn alpha giảm dần
    steps = 6
    for i in range(steps, 0, -1):
        a = int(alpha * i / steps)
        r = int(radius * i / steps)
        pygame.draw.circle(glow, (*color, a), center, max(1, r))
    surface.blit(glow, (rect.x - radius, rect.y - radius))


# ---- item ----
class MenuItem:
    def __init__(
        self,
        text,
        center,
        font_file="SVN-Determination.ttf",
        font_size=44,
        color=(200, 235, 255),
        hover_color=(255, 250, 180),
    ):
        self.base_font = load_font(font_file, font_size)
        self.text = text
        self.color = color
        self.hover_color = hover_color
        self.is_hovered = False

        self.surface = self.base_font.render(text, True, color)
        self.rect = self.surface.get_rect(center=center)

        # shadow
        self.shadow = self.base_font.render(text, True, (20, 40, 40))
        self.shadow_rect = self.shadow.get_rect(center=(center[0] + 3, center[1] + 3))

    def update_hover(self, mouse_pos):
        self.is_hovered = self.rect.collidepoint(mouse_pos)

    def draw(self, surface, t):
        # glow khi hover
        if self.is_hovered:
            draw_glow(surface, self.rect, color=(160, 220, 255), radius=20, alpha=70)

        # shadow nhẹ dao động 1px
        jitter = int(1 * math.sin(t * 6))
        self.shadow_rect.center = (
            self.rect.centerx + 3 + jitter,
            self.rect.centery + 3 + jitter,
        )
        surface.blit(self.shadow, self.shadow_rect)

        # chữ
        color = self.hover_color if self.is_hovered else self.color
        self.surface = self.base_font.render(self.text, True, color)
        surface.blit(self.surface, self.rect)

    def clicked(self, event):
        return (
            event.type == pygame.MOUSEBUTTONDOWN
            and event.button == 1
            and self.rect.collidepoint(event.pos)
        )


# ---- menu ----
class Menu:
    def __init__(self, screen):
        self.screen = screen
        self.clock = pygame.time.Clock()
        self.w, self.h = screen.get_width(), screen.get_height()

        # Initialize sound manager for menu
        from game.sound_manager import SoundManager

        self.sound_manager = SoundManager()

        # Start menu music
        try:
            self.sound_manager.stop_music()  # Stop any existing music
            self.sound_manager.play_music("sound_menu")  # Play menu background music
        except Exception as e:
            print(f"Could not play menu music: {e}")

        # Load click sound
        try:
            self.sfx_click = pygame.mixer.Sound(
                os.path.join("assets", "sounds", "menu_click.wav")
            )
            self.sfx_click.set_volume(0.7)
        except Exception as e:
            print(f"Could not load click sound: {e}")
            self.sfx_click = None

        # nền
        self.background = None
        try:
            bg_path = os.path.join(MENU_DIR, "menu.png")
            if os.path.isfile(bg_path):
                self.background = pygame.image.load(bg_path).convert()
                self.background = pygame.transform.smoothscale(
                    self.background, (self.w, self.h)
                )
        except Exception:
            self.background = None

        # âm thanh UI
        try:
            pygame.mixer.set_num_channels(24)
        except Exception:
            pass
        self.sfx_hover = safe_sound(os.path.join(SFX_DIR, "hover.wav"))
        self.sfx_click = safe_sound(os.path.join(SFX_DIR, "click.wav"))

        # tiêu đề
        self.title_font = load_font("SVN-Determination.ttf", 82)
        self.title = self.title_font.render(TITLE_TEXT, True, (255, 230, 150))
        self.title_rect = self.title.get_rect(center=(self.w // 2, self.h // 3))
        self.title_shadow = self.title_font.render(TITLE_TEXT, True, (30, 50, 50))
        self.title_shadow_rect = self.title_shadow.get_rect(
            center=(self.w // 2 + 5, self.h // 3 + 5)
        )

        # items
        y0 = self.h // 2
        self.items = [
            MenuItem("1 PLAYER", (self.w // 2, y0)),
            MenuItem("2 PLAYERS", (self.w // 2, y0 + 70)),
            MenuItem("EXIT", (self.w // 2, y0 + 140)),
        ]
        self._last_hovered = None

        # fade-in
        self.fade_alpha = 255
        self.fade_surface = pygame.Surface((self.w, self.h))
        self.fade_surface.fill((0, 0, 0))

    def run(self):
        running = True
        while running:
            dt_ms = self.clock.tick(60)
            t = pygame.time.get_ticks() / 1000.0

            # nền
            if self.background:
                self.screen.blit(self.background, (0, 0))
            else:
                self.screen.fill((10, 30, 40))

            # tiêu đề nổi nhẹ
            offset = int(6 * math.sin(t * 1.6))
            self.title_rect.centery = self.h // 3 + offset
            self.title_shadow_rect.centery = self.h // 3 + offset + 5

            self.screen.blit(self.title_shadow, self.title_shadow_rect)
            self.screen.blit(self.title, self.title_rect)

            # xử lý sự kiện
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return "exit"
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for it in self.items:
                        if it.clicked(event):
                            if self.sfx_click:
                                self.sfx_click.play()

                            # Stop menu music before returning
                            self.sound_manager.stop_music()

                            if it.text == "EXIT":
                                return "exit"
                            else:
                                return "start"

            # hover detection + hover sound
            mouse = pygame.mouse.get_pos()
            hovered_now = None
            for it in self.items:
                it.update_hover(mouse)
                if it.is_hovered:
                    hovered_now = it
            if hovered_now is not self._last_hovered:
                if hovered_now and self.sfx_hover:
                    self.sfx_hover.play()
                self._last_hovered = hovered_now

            # vẽ items
            for it in self.items:
                it.draw(self.screen, t)

            # fade-in
            if self.fade_alpha > 0:
                self.fade_alpha = max(0, self.fade_alpha - 12)
                self.fade_surface.set_alpha(self.fade_alpha)
                self.screen.blit(self.fade_surface, (0, 0))

            pygame.display.flip()

        return "exit"


# chạy thử độc lập
if __name__ == "__main__":
    pygame.mixer.pre_init(44100, -16, 2, 256)
    pygame.init()
    screen = pygame.display.set_mode((1280, 720))
    pygame.display.set_caption("Menu Demo")
    m = Menu(screen)
    action = m.run()
    print("Action:", action)
    pygame.quit()
    sys.exit()
