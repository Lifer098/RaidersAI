import os
import math
import numpy as np
from enum import IntEnum

import pygame
import pygame.surfarray as surfarray

class Actives(IntEnum):
    SWORD = 1
    BOW = 2
    AXE = 3
    FRAG = 4
    WOODWALL = 5
    STONEWALL = 6
    SPIKE = 7
    TURRET = 8
    HEAL = 9
    SCATTERSHOT = 10
    BIGTURRET = 11

class DisplayLayers(IntEnum):
    BACKGROUND_ELEMENT = 1
    BOTTOM_EFFECT = 2
    BOTTOM_RESOURCE = 3
    DEFAULT = 4
    PLAYER_BOTTOM_ELEMENT = 5
    PLAYER = 6
    PLAYER_TOP_ELEMENT = 7
    TOP_RESOURCE = 8
    OBJECT_HUD = 9
    TOP_EFFECT = 10
    PLAYER_HUD = 11


def load_asset(file):
    base_dir = os.path.dirname(__file__)
    assets_dir = os.path.join(base_dir, "..", "assets")

    if ".png" == file[-4:]:
        return pygame.image.load(os.path.join(assets_dir, "images", file))
    else:
        print("Cannot load asset {file}")

def darken(color, scale=0.8):
    return tuple(c*scale for c in color)

def polygon(center, radius, n, flip=1):
    radius = radius/math.cos(math.pi/n)
    cx,cy = center
    points = []
    for i in range(n):
        angle = 2*math.pi * (i+0.5)/n
        x = radius * math.cos(angle) * flip
        y = radius * math.sin(angle)
            
        points.append((x+cx, y+cy))
    return points

def fill_visible_pixels(surface, fill_color=(255, 255, 255), scale=0.65):
    colorkey = surface.get_colorkey()
    if colorkey is None:
        raise ValueError("Surface must have a colorkey set")
    
    # Get array view of the surface
    arr = surfarray.pixels3d(surface)

    # Create a mask of visible pixels
    mask = (arr != colorkey[:3]).any(axis=-1)

    # Apply fill color only where mask is True
    arr[mask] = scale * np.array(fill_color) + (1-scale) * arr[mask]

    # Important: delete the array view to unlock the surface
    del arr

def scale_contents(surface, scale_factor):
    """Return a new surface with same size, but contents scaled and centered."""
    width, height = surface.get_size()

    # Scale the contents down
    new_w = int(width * scale_factor)
    new_h = int(height * scale_factor)
    scaled = pygame.transform.scale(surface, (new_w, new_h))

    # Create a new surface with the original size
    result = pygame.Surface((width, height), pygame.SRCALPHA)

    # Compute centered position
    x = (width - new_w) // 2
    y = (height - new_h) // 2

    # Blit scaled contents into the center
    result.blit(scaled, (x, y))

    return result

