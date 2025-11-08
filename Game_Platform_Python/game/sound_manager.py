import pygame
import os
import time


class SoundManager:
    _instance = None

    def __new__(cls):
        # Singleton pattern - đảm bảo chỉ có một instance của SoundManager
        if cls._instance is None:
            cls._instance = super(SoundManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    # Sound cooldowns in milliseconds
    SOUND_COOLDOWNS = {
        "attack": 100,  # 100ms cooldown for attack sound
        "enemy_attack": 500,  # 500ms cooldown for enemy attack
        "enemy_death": 0,  # no cooldown for death sound
        "hurt": 200,  # 200ms cooldown for hurt sound
        "explosion": 200,  # 200ms cooldown for explosion sound
        "fire": 120,  # 120ms cooldown for fire sound
        "dash": 150,  # 150ms cooldown for dash sound
    }

    def __init__(self):
        # Chỉ khởi tạo một lần
        if self._initialized:
            return

        # Ensure pygame mixer is initialized
        if not pygame.mixer.get_init():
            pygame.mixer.init()

        self.sounds = {}
        self.current_music = None
        self._initialized = True

        # Track last play time for each sound
        self._last_play_times = {}

        # Default volume settings
        self.sound_volume = 0.7  # 70% volume for sound effects
        self.music_volume = 0.5  # 50% volume for background music

        # Load all sounds
        self._load_sounds()

    def _load_sounds(self):
        """Load all sound effects."""
        sound_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "assets", "sounds"
        )

        # Define sound mappings
        sound_files = {
            "jump": "jump.wav",
            "dash": "dash.wav",
            "charge_skill": "charge_skill.wav",
            "attack": "attack.wav",
            "hurt": "hurt.wav",
            "enemy_attack": "enemy_attack.wav",
            "enemy_death": "enemy_death.wav",
            "game_over": "game_over.wav",
            "explosion": "explosion.wav",
            "fire": "hit.wav",  # Use hit.wav for fire sound
        }

        # Load each sound
        for sound_name, filename in sound_files.items():
            try:
                sound_path = os.path.join(sound_dir, filename)
                if os.path.exists(sound_path):
                    sound = pygame.mixer.Sound(sound_path)
                    sound.set_volume(self.sound_volume)
                    self.sounds[sound_name] = sound
            except Exception as e:
                print(f"Error loading sound {filename}: {e}")

    def play_sound(self, sound_name):
        """Play a sound effect by name."""
        try:
            if sound_name not in self.sounds:
                print(f"Warning: Sound '{sound_name}' not found in loaded sounds")
                return

            # Check cooldown
            current_time = time.time() * 1000  # Convert to milliseconds
            last_play_time = self._last_play_times.get(sound_name, 0)
            cooldown = self.SOUND_COOLDOWNS.get(sound_name, 0)

            if current_time - last_play_time >= cooldown:
                self.sounds[sound_name].play()
                self._last_play_times[sound_name] = current_time

        except Exception as e:
            print(f"Error playing sound '{sound_name}': {e}")

    def play_music(self, music_name):
        """Play background music."""
        if self.current_music == music_name:
            return

        music_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "assets", "music"
        )
        music_path = os.path.join(music_dir, f"{music_name}.mp3")

        try:
            if os.path.exists(music_path):
                pygame.mixer.music.load(music_path)
                pygame.mixer.music.set_volume(self.music_volume)
                pygame.mixer.music.play(-1)  # -1 means loop indefinitely
                self.current_music = music_name
        except Exception as e:
            print(f"Error playing music {music_name}: {e}")

    def stop_music(self):
        """Stop currently playing music."""
        pygame.mixer.music.stop()
        self.current_music = None

    def set_sound_volume(self, volume):
        """Set volume for sound effects (0.0 to 1.0)."""
        self.sound_volume = max(0.0, min(1.0, volume))
        for sound in self.sounds.values():
            sound.set_volume(self.sound_volume)

    def set_music_volume(self, volume):
        """Set volume for background music (0.0 to 1.0)."""
        self.music_volume = max(0.0, min(1.0, volume))
        pygame.mixer.music.set_volume(self.music_volume)
