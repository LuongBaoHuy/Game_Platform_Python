import pygame
import sys
from game.menu import MenuItem, SettingsMenu
import os, math


def _fast_blur(surf, scale=0.25, passes=2):
    """Blur giả lập bằng smoothscale xuống rồi phóng lên."""
    w, h = surf.get_size()
    tmp = surf.copy()
    for _ in range(max(1, passes)):
        dw, dh = max(1, int(w * scale)), max(1, int(h * scale))
        tmp = pygame.transform.smoothscale(tmp, (dw, dh))
        tmp = pygame.transform.smoothscale(tmp, (w, h))
    return tmp


def _vignette(size, alpha=180):
    w, h = size
    v = pygame.Surface((w, h), pygame.SRCALPHA)
    steps = 10
    for i in range(steps):
        a = int(alpha * (i + 1) / steps)
        pygame.draw.rect(v, (0, 0, 0, a), (i, i, w - 2 * i, h - 2 * i), width=4)
    return v


class PauseMenu:
    def __init__(
        self, screen, game_surface, font_file="assets/fonts/SVN-Determination.ttf"
    ):
        self.screen = screen
        self.w, self.h = screen.get_size()
        self.game_surface = game_surface

        # Fonts
        if os.path.isfile(font_file):
            self.title_font = pygame.font.Font(font_file, 82)
            self.item_font = pygame.font.Font(font_file, 44)
        else:
            self.title_font = pygame.font.SysFont("Arial", 82)
            self.item_font = pygame.font.SysFont("Arial", 44)

        # Sounds
        self.sfx_hover = self._safe_sfx("assets/sounds/hover.wav")
        self.sfx_click = self._safe_sfx("assets/sounds/click.wav")

        # Blur + overlay
        self.bg_blurred = _fast_blur(game_surface, 0.25, 2)
        self.overlay = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        self.overlay.fill((0, 0, 0, 140))
        self.vignette = _vignette((self.w, self.h), 200)

        # Menu items
        self.items = ["CONTINUE", "PLAY AGAIN", "SETTINGS", "MAIN MENU", "EXIT"]
        self.index = 0

        # Fade
        self.alpha = 255

    def _safe_sfx(self, path):
        try:
            if os.path.isfile(path):
                return pygame.mixer.Sound(path)
        except Exception:
            pass
        return None

    def _draw_centered_text(self, surface, font, text, y, color=(255, 255, 255)):
        render = font.render(text, True, color)
        rect = render.get_rect(center=(self.w // 2, y))
        surface.blit(render, rect)
        return rect

    def _show_settings(self):
        """Show settings menu from pause menu"""
        try:
            # Get sound manager from somewhere - we'll need to import it
            from game.sound_manager import SoundManager

            sound_manager = SoundManager()

            settings_menu = SettingsMenu(self.screen, sound_manager)
            settings_menu.run()
        except Exception as e:
            print(f"Error showing settings: {e}")

    def run(self):
        clock = pygame.time.Clock()
        while True:
            clock.tick(60)
            self.screen.blit(self.bg_blurred, (0, 0))
            self.screen.blit(self.overlay, (0, 0))
            self.screen.blit(self.vignette, (0, 0))

            # Title
            self._draw_centered_text(
                self.screen, self.title_font, "PAUSED", self.h // 3, (255, 235, 180)
            )

            # Draw items
            y0 = self.h // 2
            for i, text in enumerate(self.items):
                color = (255, 255, 180) if i == self.index else (200, 235, 255)
                rect = self._draw_centered_text(
                    self.screen, self.item_font, text, y0 + i * 70, color
                )
                if i == self.index:
                    glow = pygame.Surface(
                        (rect.width + 40, rect.height + 40), pygame.SRCALPHA
                    )
                    for k in range(5):
                        a = int(60 * (k + 1) / 5)
                        pygame.draw.circle(
                            glow,
                            (160, 220, 255, a),
                            (glow.get_width() // 2, glow.get_height() // 2),
                            rect.width // 2 + 12 - k * 2,
                        )
                    self.screen.blit(glow, (rect.x - 20, rect.y - 20))

            # Input
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    return "exit"
                if e.type == pygame.KEYDOWN:
                    if e.key == pygame.K_ESCAPE:
                        return "continue"
                    if e.key in (pygame.K_UP, pygame.K_w):
                        self.index = (self.index - 1) % len(self.items)
                        if self.sfx_hover:
                            self.sfx_hover.play()
                    if e.key in (pygame.K_DOWN, pygame.K_s):
                        self.index = (self.index + 1) % len(self.items)
                        if self.sfx_hover:
                            self.sfx_hover.play()
                    if e.key in (pygame.K_RETURN, pygame.K_SPACE):
                        if self.sfx_click:
                            self.sfx_click.play()
                        selected_item = self.items[self.index]
                        if selected_item == "CONTINUE":
                            return "continue"
                        elif selected_item == "PLAY AGAIN":
                            return "play_again"
                        elif selected_item == "SETTINGS":
                            self._show_settings()
                            # Continue in pause menu loop after settings
                        elif selected_item == "MAIN MENU":
                            return "main_menu"
                        else:
                            return "exit"
                if e.type == pygame.MOUSEMOTION:
                    mx, my = e.pos
                    for i, text in enumerate(self.items):
                        y = self.h // 2 + i * 70
                        rect = pygame.Rect(self.w // 2 - 150, y - 25, 300, 50)
                        if rect.collidepoint(mx, my):
                            if self.index != i and self.sfx_hover:
                                self.sfx_hover.play()
                            self.index = i
                if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                    if self.sfx_click:
                        self.sfx_click.play()
                    selected_item = self.items[self.index]
                    if selected_item == "CONTINUE":
                        return "continue"
                    elif selected_item == "PLAY AGAIN":
                        return "play_again"
                    elif selected_item == "SETTINGS":
                        self._show_settings()
                        # Continue in pause menu loop after settings
                    elif selected_item == "MAIN MENU":
                        return "main_menu"
                    else:
                        return "exit"

            # Fade in
            if self.alpha > 0:
                fade = pygame.Surface((self.w, self.h))
                fade.fill((0, 0, 0))
                fade.set_alpha(self.alpha)
                self.screen.blit(fade, (0, 0))
                self.alpha = max(0, self.alpha - 25)

            pygame.display.flip()
