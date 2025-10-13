import pytmx
import pygame

def load_map(filename):
    tmx_data = pytmx.load_pygame(filename)
    platforms = []

    for layer in tmx_data.layers:
        if isinstance(layer, pytmx.TiledTileLayer):
            for x, y, gid in layer:
                tile = tmx_data.get_tile_image_by_gid(gid)
                if tile:
                    screen_x = x * tmx_data.tilewidth
                    screen_y = y * tmx_data.tileheight
                    rect = pygame.Rect(
                        screen_x, screen_y,
                        tmx_data.tilewidth, tmx_data.tileheight
                    )
                    platforms.append((tile, rect))
    return platforms, tmx_data
