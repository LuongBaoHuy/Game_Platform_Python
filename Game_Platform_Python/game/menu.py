import pygame
import sys
import os
import math

ASSETS_DIR = os.path.join("assets")
FONTS_DIR = os.path.join(ASSETS_DIR, "fonts")
SFX_DIR = os.path.join(ASSETS_DIR, "sounds")
MENU_DIR = os.path.join(ASSETS_DIR, "menu")

TITLE_TEXT = "GAME PLATFORM"


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
                os.path.join("assets", "sounds", "click.wav")
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
            MenuItem("START GAME", (self.w // 2, y0)),
            MenuItem("SETTINGS", (self.w // 2, y0 + 70)),
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

                            if it.text == "EXIT":
                                # Stop menu music before exiting
                                self.sound_manager.stop_music()
                                return "exit"
                            elif it.text == "SETTINGS":
                                # Show settings menu
                                settings_menu = SettingsMenu(
                                    self.screen, self.sound_manager
                                )
                                settings_menu.run()
                                # Continue in menu loop after settings
                            else:
                                # Stop menu music before starting game
                                self.sound_manager.stop_music()
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


class SettingsMenu:
    def __init__(self, screen, sound_manager):
        self.screen = screen
        self.sound_manager = sound_manager
        self.clock = pygame.time.Clock()
        self.w, self.h = screen.get_width(), screen.get_height()

        # Fonts
        self.title_font = load_font("SVN-Determination.ttf", 72)
        self.label_font = load_font("SVN-Determination.ttf", 40)
        self.value_font = load_font("SVN-Determination.ttf", 36)

        # Colors
        self.bg_color = (20, 30, 45)
        self.title_color = (255, 230, 150)
        self.label_color = (200, 235, 255)
        self.value_color = (255, 255, 255)
        self.slider_color = (100, 150, 200)
        self.slider_handle_color = (255, 255, 255)

        # Volume settings (0.0 to 1.0)
        self.music_volume = self.sound_manager.music_volume
        self.sfx_volume = self.sound_manager.sound_volume

        # Slider properties
        self.slider_width = 300
        self.slider_height = 20
        self.handle_radius = 12

        # Dragging state
        self.dragging_music = False
        self.dragging_sfx = False

        # Sound effects
        self.sfx_click = safe_sound(os.path.join(SFX_DIR, "click.wav"))
        self.sfx_hover = safe_sound(os.path.join(SFX_DIR, "hover.wav"))

    def draw_slider(self, surface, x, y, value, label):
        """Draw a volume slider with label and value display"""
        # Label
        label_surf = self.label_font.render(label, True, self.label_color)
        label_rect = label_surf.get_rect(midright=(x - 20, y))
        surface.blit(label_surf, label_rect)

        # Slider track
        track_rect = pygame.Rect(
            x, y - self.slider_height // 2, self.slider_width, self.slider_height
        )
        pygame.draw.rect(surface, self.slider_color, track_rect)
        pygame.draw.rect(surface, (255, 255, 255), track_rect, 2)

        # Slider handle
        handle_x = x + int(value * self.slider_width)
        pygame.draw.circle(
            surface, self.slider_handle_color, (handle_x, y), self.handle_radius
        )
        pygame.draw.circle(surface, (0, 0, 0), (handle_x, y), self.handle_radius, 2)

        # Value percentage
        value_text = f"{int(value * 100)}%"
        value_surf = self.value_font.render(value_text, True, self.value_color)
        value_rect = value_surf.get_rect(midleft=(x + self.slider_width + 20, y))
        surface.blit(value_surf, value_rect)

        return track_rect

    def handle_slider_input(self, mouse_pos, mouse_pressed, track_rect, current_value):
        """Handle mouse input for a slider and return new value"""
        if track_rect.collidepoint(mouse_pos):
            if mouse_pressed:
                # Calculate new value based on mouse position
                relative_x = mouse_pos[0] - track_rect.x
                new_value = max(0.0, min(1.0, relative_x / self.slider_width))
                return new_value, True
        return current_value, False

    def run(self):
        running = True

        while running:
            dt_ms = self.clock.tick(60)
            mouse_pos = pygame.mouse.get_pos()
            mouse_pressed = pygame.mouse.get_pressed()[0]

            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        if self.sfx_click:
                            self.sfx_click.play()
                        running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:  # Left click
                        if self.sfx_click:
                            self.sfx_click.play()

            # Update dragging state
            if not mouse_pressed:
                self.dragging_music = False
                self.dragging_sfx = False

            # Clear screen
            self.screen.fill(self.bg_color)

            # Title
            title_surf = self.title_font.render("SETTINGS", True, self.title_color)
            title_rect = title_surf.get_rect(center=(self.w // 2, self.h // 4))
            self.screen.blit(title_surf, title_rect)

            # Music volume slider
            music_y = self.h // 2 - 50
            music_track = self.draw_slider(
                self.screen,
                self.w // 2 - self.slider_width // 2,
                music_y,
                self.music_volume,
                "MUSIC",
            )

            # SFX volume slider
            sfx_y = self.h // 2 + 50
            sfx_track = self.draw_slider(
                self.screen,
                self.w // 2 - self.slider_width // 2,
                sfx_y,
                self.sfx_volume,
                "SFX",
            )

            # Handle slider interactions
            if self.dragging_music or (
                mouse_pressed and music_track.collidepoint(mouse_pos)
            ):
                new_volume, self.dragging_music = self.handle_slider_input(
                    mouse_pos, mouse_pressed, music_track, self.music_volume
                )
                if new_volume != self.music_volume:
                    self.music_volume = new_volume
                    self.sound_manager.set_music_volume(self.music_volume)

            if self.dragging_sfx or (
                mouse_pressed and sfx_track.collidepoint(mouse_pos)
            ):
                new_volume, self.dragging_sfx = self.handle_slider_input(
                    mouse_pos, mouse_pressed, sfx_track, self.sfx_volume
                )
                if new_volume != self.sfx_volume:
                    self.sfx_volume = new_volume
                    self.sound_manager.set_sound_volume(self.sfx_volume)

            # Back button hint
            back_text = self.label_font.render(
                "Press ESC to return", True, (150, 150, 150)
            )
            back_rect = back_text.get_rect(center=(self.w // 2, self.h - 100))
            self.screen.blit(back_text, back_rect)

            pygame.display.flip()


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
