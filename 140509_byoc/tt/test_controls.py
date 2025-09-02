#!/usr/bin/env python3

import pygame
import sys

# Initialize Pygame
pygame.init()
screen = pygame.display.set_mode((400, 300))
pygame.display.set_caption("Control Test")
clock = pygame.time.Clock()

print("🎮 Control test started!")
print("Press W/S for left paddle, ↑/↓ for right paddle, ESC to quit")

left_paddle_y = 150
right_paddle_y = 150
PADDLE_SPEED = 6

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
    
    keys = pygame.key.get_pressed()
    
    # Test left paddle controls (W/S)
    if keys[pygame.K_w]:
        left_paddle_y = max(40, left_paddle_y - PADDLE_SPEED)
        print(f"W pressed - Left paddle: {left_paddle_y}")
    elif keys[pygame.K_s]:
        left_paddle_y = min(260, left_paddle_y + PADDLE_SPEED)
        print(f"S pressed - Left paddle: {left_paddle_y}")
    
    # Test right paddle controls (Arrow keys)
    if keys[pygame.K_UP]:
        right_paddle_y = max(40, right_paddle_y - PADDLE_SPEED)
        print(f"↑ pressed - Right paddle: {right_paddle_y}")
    elif keys[pygame.K_DOWN]:
        right_paddle_y = min(260, right_paddle_y + PADDLE_SPEED)
        print(f"↓ pressed - Right paddle: {right_paddle_y}")
    
    # Draw
    screen.fill((0, 100, 0))
    pygame.draw.rect(screen, (255, 255, 255), (50, left_paddle_y - 40, 10, 80))
    pygame.draw.rect(screen, (255, 255, 255), (340, right_paddle_y - 40, 10, 80))
    pygame.display.flip()
    clock.tick(60)

pygame.quit()
print("🏓 Test complete")