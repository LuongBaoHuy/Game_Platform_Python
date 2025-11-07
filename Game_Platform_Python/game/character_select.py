import pygame
import os
import math
from game.menu import MenuItem


class CharacterSelectMenu:
    def __init__(self, screen):
        self.screen = screen
        self.w, self.h = screen.get_width(), screen.get_height()

        # Vị trí các nút và preview
        self.button_y = int(self.h * 0.8)  # Nút ở 80% chiều cao màn hình
        self.preview_y = int(self.h * 0.5)  # Preview ở giữa màn hình (50%)
        self.title_y = int(self.h * 0.2)  # Tiêu đề ở 20% chiều cao

        # Thông tin nhân vật
        self.character_data = {
            "bluewizard": {
                "name": "Blue Wizard",
                "preview_path": os.path.join(
                    "assets",
                    "characters",
                    "bluewizard",
                    "2BlueWizardIdle",
                    "Chocpic16.png",
                ),
                "description": "A powerful wizard mastering ice and wind magic",
            },
            "firewizard": {
                "name": "Fire Wizard",
                "preview_path": os.path.join(
                    "assets",
                    "characters",
                    "firewizard",
                    "FireWizardIdle",
                    "1_IDLE_001.png",
                ),
                "description": "A fire wizard controlling fire and heat",
            },
        }

        self.character_previews = {}
        self.selected_character = None
        self.current_preview = None

        # Load preview images với fallback
        for char_id, data in self.character_data.items():
            try:
                # Get full path from project root
                project_root = os.path.dirname(os.path.dirname(__file__))
                preview_path = os.path.join(project_root, data["preview_path"])

                if os.path.exists(preview_path):
                    print(f"Loading preview from: {preview_path}")
                    img = pygame.image.load(preview_path).convert_alpha()
                    # Scale to reasonable preview size
                    scale = 0.3  # Giảm kích thước xuống rất nhỏ
                    width = int(300 * scale)
                    height = int(300 * scale)
                    img = pygame.transform.scale(img, (width, height))
                    self.character_previews[char_id] = img
                else:
                    print(f"Could not find preview image at: {preview_path}")
                    print(f"Checking directory exists: {os.path.dirname(preview_path)}")
                    try:
                        parent_dir = os.path.dirname(preview_path)
                        if os.path.exists(parent_dir):
                            print(f"Files in directory: {os.listdir(parent_dir)}")
                    except Exception as e:
                        print(f"Error checking directory: {e}")

                    # Try loading the first frame from idle animation
                    # Xác định đường dẫn thư mục idle animation
                    idle_paths = {
                        "bluewizard": os.path.join(
                            project_root,
                            "assets",
                            "characters",
                            "bluewizard",
                            "2BlueWizardIdle",
                        ),
                        "firewizard": os.path.join(
                            project_root,
                            "assets",
                            "characters",
                            "firewizard",
                            "FireWizardIdle",
                        ),
                    }

                    idle_folder = idle_paths.get(char_id)
                    if os.path.exists(idle_folder):
                        try:
                            files = sorted(
                                [
                                    f
                                    for f in os.listdir(idle_folder)
                                    if f.endswith(".png")
                                ]
                            )
                            print(f"Available files in {idle_folder}: {files}")
                            if files:
                                fallback_path = os.path.join(idle_folder, files[0])
                                print(f"Trying fallback image: {fallback_path}")
                                img = pygame.image.load(fallback_path).convert_alpha()
                                width = int(
                                    300 * 0.5
                                )  # Giảm kích thước của fallback image
                                height = int(300 * 0.5)
                                img = pygame.transform.scale(img, (width, height))
                                self.character_previews[char_id] = img
                                print(
                                    f"Successfully loaded fallback image for {char_id}"
                                )
                            else:
                                print(f"No PNG files found in {idle_folder}")
                        except Exception as e:
                            print(f"Error in fallback loading for {char_id}: {e}")

            except Exception as e:
                print(f"Error loading preview for {char_id}: {e}")
                # In thêm thông tin debug
                print(f"Trying to load from path: {preview_path}")
                if idle_folder:
                    print(f"Fallback folder exists: {os.path.exists(idle_folder)}")
                    if os.path.exists(idle_folder):
                        print(f"Files in fallback folder: {os.listdir(idle_folder)}")

        # Font cho tiêu đề và descriptions
        try:
            font_path = os.path.join("assets", "fonts", "SVN-Determination.ttf")
            self.title_font = pygame.font.Font(
                font_path, 72
            )  # Giảm kích thước font tiêu đề
            self.desc_font = pygame.font.Font(
                font_path, 36
            )  # Giảm kích thước font mô tả
        except:
            self.title_font = pygame.font.Font(None, 82)
            self.desc_font = pygame.font.Font(None, 44)

            # Tạo các nút chọn nhân vật
        button_spacing = 200  # Khoảng cách giữa các nút
        center_x = self.w // 2

        self.char_buttons = []
        self.char_buttons.append(
            {
                "id": "bluewizard",
                "item": MenuItem(
                    "Blue Wizard", (center_x - button_spacing, self.button_y)
                ),
            }
        )
        self.char_buttons.append(
            {
                "id": "firewizard",
                "item": MenuItem(
                    "Fire Wizard", (center_x + button_spacing, self.button_y)
                ),
            }
        )

        # Nút Select (ban đầu bị ẩn)
        self.select_button = MenuItem("SELECT", (center_x, self.button_y + 60))
        self.select_button.is_enabled = False

        # Sound effects
        try:
            self.sfx_hover = pygame.mixer.Sound(
                os.path.join("assets", "sounds", "hover.wav")
            )
            self.sfx_select = pygame.mixer.Sound(
                os.path.join("assets", "sounds", "click.wav")
            )
        except Exception:
            self.sfx_hover = None
            self.sfx_select = None

        self._last_hovered = None

        # In thông tin debug
        if not self.character_previews:
            print("CẢNH BÁO: Không tải được ảnh preview của nhân vật!")
        else:
            print(
                f"Đã tải thành công preview cho: {list(self.character_previews.keys())}"
            )

    def draw_preview(self, char_id):
        if char_id in self.character_previews:
            img = self.character_previews[char_id]
            rect = img.get_rect(center=(self.w // 2, self.preview_y))

            # Vẽ khung cho preview
            padding = 20
            frame_rect = pygame.Rect(
                rect.x - padding,
                rect.y - padding,
                rect.width + padding * 2,
                rect.height + padding * 2,
            )

            # Draw glowing effect if this is the selected character
            if char_id == self.selected_character:
                glow_color = (
                    (100, 200, 255) if char_id == "bluewizard" else (255, 150, 50)
                )
                glow_surf = pygame.Surface(
                    (frame_rect.width + 40, frame_rect.height + 40), pygame.SRCALPHA
                )
                for i in range(3):
                    glow_alpha = 100 - (i * 30)
                    pygame.draw.rect(
                        glow_surf,
                        (*glow_color, glow_alpha),
                        (
                            i * 5,
                            i * 5,
                            frame_rect.width - i * 10,
                            frame_rect.height - i * 10,
                        ),
                        border_radius=10,
                    )
                self.screen.blit(glow_surf, (frame_rect.x - 20, frame_rect.y - 20))

            # Draw frame
            pygame.draw.rect(self.screen, (50, 50, 50), frame_rect, border_radius=10)
            pygame.draw.rect(
                self.screen, (200, 200, 200), frame_rect, 3, border_radius=10
            )

            # Draw preview image
            self.screen.blit(img, rect)

            # Draw character description
            desc = self.character_data[char_id]["description"]
            desc_surf = self.desc_font.render(desc, True, (255, 255, 255))
            desc_rect = desc_surf.get_rect(
                center=(self.w // 2, rect.bottom + 40)
            )  # Tăng khoảng cách với preview để dễ đọc hơn
            self.screen.blit(desc_surf, desc_rect)

    def run(self):
        running = True
        while running:
            # Màu nền tối
            self.screen.fill((15, 15, 30))

            # Vẽ tiêu đề
            title = self.title_font.render("CHOOSE YOUR HERO", True, (255, 255, 255))
            title_rect = title.get_rect(center=(self.w // 2, self.title_y))
            self.screen.blit(title, title_rect)

            # Vẽ preview nếu có
            if self.current_preview:
                self.draw_preview(self.current_preview)

            t = pygame.time.get_ticks() / 1000.0

            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return None

                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    # Check character buttons
                    for btn in self.char_buttons:
                        if btn["item"].clicked(event):
                            if self.sfx_select:
                                self.sfx_select.play()
                            self.selected_character = btn["id"]
                            self.current_preview = btn[
                                "id"
                            ]  # Update preview immediately
                            self.select_button.is_enabled = True

                    # Check select button if enabled
                    if self.select_button.is_enabled and self.select_button.clicked(
                        event
                    ):
                        if self.sfx_select:
                            self.sfx_select.play()
                        return self.selected_character

            # Handle hover states and preview
            mouse = pygame.mouse.get_pos()
            hovered_now = None

            for btn in self.char_buttons:
                btn["item"].update_hover(mouse)
                if btn["item"].is_hovered:
                    hovered_now = btn["item"]
                    self.current_preview = btn["id"]

            if self.select_button.is_enabled:
                self.select_button.update_hover(mouse)
                if self.select_button.is_hovered:
                    hovered_now = self.select_button

            if hovered_now is not self._last_hovered:
                if hovered_now and self.sfx_hover:
                    self.sfx_hover.play()
                self._last_hovered = hovered_now

            # Draw character buttons
            for btn in self.char_buttons:
                btn["item"].draw(self.screen, t)

            # Draw select button if enabled
            if self.select_button.is_enabled:
                self.select_button.draw(self.screen, t)

            pygame.display.flip()

        return None  # Return None if user exits
