import pygame

def draw_menu(surface):
    # placeholder: draw a simple title
    font = pygame.font.SysFont("Arial", 48)
    text = font.render("My Game Menu", True, (255, 255, 255))
    w, h = surface.get_size()
    surface.blit(text, (w//2 - text.get_width()//2, 50))
