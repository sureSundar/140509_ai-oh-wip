#!/usr/bin/env python3

import pygame
import pymunk
import pymunk.pygame_util
import requests
import os
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Game Constants
WIDTH, HEIGHT = 800, 400
BALL_RADIUS = 10
PADDLE_WIDTH, PADDLE_HEIGHT = 10, 80
TABLE_MARGIN = 30
PADDLE_SPEED = 6
AI_DECISION_INTERVAL = 5  # Frames between AI decisions
WIN_SCORE = 11  # Standard table tennis score
SERVICE_ALTERNATE_EVERY = 2  # Standard table tennis service
BALL_SPEED_MIN = 100
BALL_SPEED_MAX = 500
BALL_SPEED_STEP = 50

# Colors
GREEN = (34, 139, 34)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
NET_COLOR = (200, 200, 200)

# Initialize Pygame with display driver
print("🎮 Initializing Pygame...")
os.environ['SDL_VIDEODRIVER'] = 'x11'
pygame.init()
pygame.display.init()
print("📺 Creating game window...")
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("🏓 AI Table Tennis Arena - Claude vs OpenAI vs Ollama")
print("✅ Game window created successfully!")
print(f"Display driver: {pygame.display.get_driver()}")
print(f"Window size: {screen.get_size()}")
clock = pygame.time.Clock()
font = pygame.font.SysFont("Arial", 20)
font_large = pygame.font.SysFont("Arial", 24)
draw_options = pymunk.pygame_util.DrawOptions(screen)

# AI Providers
class AIProvider:
    def __init__(self, name, color):
        self.name = name
        self.color = color
        self.timeout = int(os.getenv('AI_TIMEOUT_SECONDS', '3'))
    
    def query(self, game_state, side):
        """Override in subclasses"""
        return "stay", 0

class ClaudeAI(AIProvider):
    def __init__(self):
        super().__init__("Claude", BLUE)
        self.api_key = os.getenv('ANTHROPIC_API_KEY')
        self.available = bool(self.api_key)
    
    def query(self, game_state, side):
        if not self.available:
            return "stay", 0
            
        prompt = f'''You are the {side} paddle in table tennis. 
Ball: x={game_state['ball']['x']}, y={game_state['ball']['y']}, vx={game_state['ball']['vx']}, vy={game_state['ball']['vy']}
Your paddle y={game_state[f'{side}_paddle']['y']}

Respond ONLY with: "up 6", "down 6", or "stay"'''
        
        try:
            response = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "x-api-version": "2023-06-01"
                },
                json={
                    "model": "claude-3-haiku-20240307",
                    "max_tokens": 20,
                    "messages": [{"role": "user", "content": prompt}]
                },
                timeout=self.timeout
            )
            if response.status_code == 200:
                text = response.json()['content'][0]['text'].strip().lower()
                return self._parse_response(text)
        except Exception as e:
            print(f"Claude {side} error: {e}")
        
        # Fallback strategy when API fails
        ball_y = game_state['ball']['y']
        paddle_y = game_state[f'{side}_paddle']['y']
        if ball_y < paddle_y - 20:
            return "up", PADDLE_SPEED
        elif ball_y > paddle_y + 20:
            return "down", PADDLE_SPEED
        return "stay", 0
    
    def _parse_response(self, text):
        text = text.strip().lower()
        if "up" in text:
            try:
                parts = text.split()
                speed = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else PADDLE_SPEED
                return "up", min(speed, PADDLE_SPEED * 2)
            except:
                return "up", PADDLE_SPEED
        elif "down" in text:
            try:
                parts = text.split()
                speed = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else PADDLE_SPEED
                return "down", min(speed, PADDLE_SPEED * 2)
            except:
                return "down", PADDLE_SPEED
        return "stay", 0

class OpenAI(AIProvider):
    def __init__(self):
        super().__init__("OpenAI", RED)
        self.api_key = os.getenv('OPENAI_API_KEY')
        self.available = bool(self.api_key)
    
    def query(self, game_state, side):
        if not self.available:
            return "stay", 0
            
        prompt = f'''You are the {side} paddle in table tennis.
Ball: x={game_state['ball']['x']}, y={game_state['ball']['y']}, vx={game_state['ball']['vx']}, vy={game_state['ball']['vy']}
Your paddle y={game_state[f'{side}_paddle']['y']}

Respond ONLY with: "up 6", "down 6", or "stay"'''
        
        try:
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "gpt-3.5-turbo",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 20
                },
                timeout=self.timeout
            )
            if response.status_code == 200:
                text = response.json()['choices'][0]['message']['content'].strip().lower()
                return self._parse_response(text)
        except Exception as e:
            print(f"OpenAI {side} error: {e}")
        
        # Fallback strategy when API fails
        ball_y = game_state['ball']['y']
        paddle_y = game_state[f'{side}_paddle']['y']
        if ball_y < paddle_y - 20:
            return "up", PADDLE_SPEED
        elif ball_y > paddle_y + 20:
            return "down", PADDLE_SPEED
        return "stay", 0
    
    def _parse_response(self, text):
        text = text.strip().lower()
        if "up" in text:
            try:
                parts = text.split()
                speed = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else PADDLE_SPEED
                return "up", min(speed, PADDLE_SPEED * 2)
            except:
                return "up", PADDLE_SPEED
        elif "down" in text:
            try:
                parts = text.split()
                speed = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else PADDLE_SPEED
                return "down", min(speed, PADDLE_SPEED * 2)
            except:
                return "down", PADDLE_SPEED
        return "stay", 0

class OllamaAI(AIProvider):
    def __init__(self):
        super().__init__("Ollama", YELLOW)
        self.base_url = os.getenv('OLLAMA_BASE_URL', "http://localhost:11434")
        self.model = os.getenv('OLLAMA_MODEL', "llama3.1")
        self.available = self._check_availability()
    
    def _check_availability(self):
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def query(self, game_state, side):
        if not self.available:
            return "stay", 0
            
        prompt = f'''You are the {side} paddle in table tennis.
Ball: x={game_state['ball']['x']}, y={game_state['ball']['y']}, vx={game_state['ball']['vx']}, vy={game_state['ball']['vy']}
Your paddle y={game_state[f'{side}_paddle']['y']}

Respond ONLY with: "up 6", "down 6", or "stay"'''
        
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={"model": self.model, "prompt": prompt, "stream": False},
                timeout=self.timeout
            )
            if response.status_code == 200:
                text = response.json()["response"].strip().lower()
                return self._parse_response(text)
        except Exception as e:
            print(f"Ollama {side} error: {e}")
        
        # Fallback strategy when API fails
        ball_y = game_state['ball']['y']
        paddle_y = game_state[f'{side}_paddle']['y']
        if ball_y < paddle_y - 20:
            return "up", PADDLE_SPEED
        elif ball_y > paddle_y + 20:
            return "down", PADDLE_SPEED
        return "stay", 0
    
    def _parse_response(self, text):
        text = text.strip().lower()
        if "up" in text:
            try:
                parts = text.split()
                speed = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else PADDLE_SPEED
                return "up", min(speed, PADDLE_SPEED * 2)
            except:
                return "up", PADDLE_SPEED
        elif "down" in text:
            try:
                parts = text.split()
                speed = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else PADDLE_SPEED
                return "down", min(speed, PADDLE_SPEED * 2)
            except:
                return "down", PADDLE_SPEED
        return "stay", 0

# Initialize AI providers
claude_ai = ClaudeAI()
openai_ai = OpenAI()
ollama_ai = OllamaAI()

# Game Physics
def create_space():
    space = pymunk.Space()
    space.gravity = (0, 0)
    return space

def create_ball(space):
    body = pymunk.Body(1, pymunk.moment_for_circle(1, 0, BALL_RADIUS))
    body.position = WIDTH // 2, HEIGHT // 2
    shape = pymunk.Circle(body, BALL_RADIUS)
    shape.elasticity = 1.0
    shape.friction = 0.0
    body.velocity = (250, 150)
    space.add(body, shape)
    return body, shape

def create_paddle(space, x):
    body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
    body.position = x, HEIGHT // 2
    shape = pymunk.Poly.create_box(body, (PADDLE_WIDTH, PADDLE_HEIGHT))
    shape.elasticity = 1.0
    shape.friction = 0.0
    space.add(body, shape)
    return body

def create_walls(space):
    top = pymunk.Segment(space.static_body, (0, 0), (WIDTH, 0), 1)
    bottom = pymunk.Segment(space.static_body, (0, HEIGHT), (WIDTH, HEIGHT), 1)
    for wall in [top, bottom]:
        wall.elasticity = 1.0
    space.add(top, bottom)

def cpu_strategy(ball_y, paddle_y):
    """Improved CPU strategy"""
    diff = ball_y - paddle_y
    if abs(diff) < 15:  # Dead zone for smoother play
        return "stay", 0
    elif diff < 0:
        return "up", PADDLE_SPEED
    else:
        return "down", PADDLE_SPEED

def move_paddle(paddle, direction, amount):
    """Move paddle with boundary checking"""
    if direction == "up":
        new_y = max(PADDLE_HEIGHT / 2, paddle.position.y - amount)
    elif direction == "down":
        new_y = min(HEIGHT - PADDLE_HEIGHT / 2, paddle.position.y + amount)
    else:
        new_y = paddle.position.y
    
    paddle.position = (paddle.position.x, new_y)

def draw_game(space, left_score, right_score, server, mode, ball_speed_mult=1.0, left_ai=None, right_ai=None):
    """Draw the complete game state"""
    screen.fill(GREEN)
    
    # Draw table borders
    pygame.draw.rect(screen, WHITE, screen.get_rect(), 3)
    
    # Draw net
    pygame.draw.line(screen, WHITE, (WIDTH // 2, 0), (WIDTH // 2, HEIGHT), 2)
    for y in range(0, HEIGHT, 15):
        pygame.draw.line(screen, NET_COLOR, (WIDTH // 2 - 1, y), (WIDTH // 2 + 1, y + 8), 1)
    
    # Draw physics objects
    space.debug_draw(draw_options)
    
    # Draw score
    score_text = f"{left_score} : {right_score}"
    server_text = f"Server: {'Left' if server else 'Right'}"
    speed_text = f"Speed: {ball_speed_mult:.1f}x"
    screen.blit(font.render(score_text, True, WHITE), (WIDTH // 2 - 40, 10))
    screen.blit(font.render(server_text, True, WHITE), (WIDTH // 2 - 60, 35))
    screen.blit(font.render(speed_text, True, WHITE), (WIDTH // 2 - 40, 60))
    
    # Draw mode and AI info
    mode_text = mode.replace("_", " ").title()
    screen.blit(font.render(mode_text, True, WHITE), (10, 10))
    
    # Show AI provider info
    if left_ai:
        pygame.draw.circle(screen, left_ai.color, (50, HEIGHT - 30), 8)
        screen.blit(font.render(left_ai.name, True, left_ai.color), (65, HEIGHT - 40))
    
    if right_ai:
        pygame.draw.circle(screen, right_ai.color, (WIDTH - 100, HEIGHT - 30), 8)
        screen.blit(font.render(right_ai.name, True, right_ai.color), (WIDTH - 85, HEIGHT - 40))
    
    # Draw controls
    controls = [
        "Left: W/S or ↑/↓", 
        "Right: Arrow Keys",
        "ESC: Menu"
    ]
    for i, control in enumerate(controls):
        screen.blit(font.render(control, True, WHITE), (10, HEIGHT - 80 + i * 20))

def reset_ball(ball_body, serve_left, speed_multiplier=1.0):
    """Reset ball position and velocity for serve"""
    ball_body.position = WIDTH // 2, HEIGHT // 2
    # Serve towards the serving side
    base_vel_x = -200 if serve_left else 200
    base_vel_y = 100 if serve_left else -100
    vel_x = base_vel_x * speed_multiplier
    vel_y = base_vel_y * speed_multiplier
    ball_body.velocity = (vel_x, vel_y)

def get_game_state(ball, left_paddle, right_paddle):
    """Get current game state for AI"""
    return {
        "ball": {
            "x": round(ball.position.x, 2),
            "y": round(ball.position.y, 2),
            "vx": round(ball.velocity.x, 2),
            "vy": round(ball.velocity.y, 2)
        },
        "left_paddle": {"y": round(left_paddle.position.y, 2)},
        "right_paddle": {"y": round(right_paddle.position.y, 2)}
    }

def run_game(mode, left_ai=None, right_ai=None):
    """Main game loop"""
    # Create physics space
    space = create_space()
    create_walls(space)
    
    # Create game objects
    left_paddle = create_paddle(space, TABLE_MARGIN)
    right_paddle = create_paddle(space, WIDTH - TABLE_MARGIN)
    ball, ball_shape = create_ball(space)
    
    # Game state
    left_score = right_score = total_points = 0
    serve_left = True
    frame = 0
    left_direction, left_val = "stay", 0
    right_direction, right_val = "stay", 0
    game_running = True
    ball_speed_multiplier = 1.0
    
    print(f"🏓 Starting {mode} - Left: {left_ai.name if left_ai else 'Human'}, Right: {right_ai.name if right_ai else 'Human'}")
    print(f"Debug: left_ai={left_ai is not None}, right_ai={right_ai is not None}")
    
    # Initial serve
    reset_ball(ball, serve_left, ball_speed_multiplier)
    
    while game_running and max(left_score, right_score) < WIN_SCORE:
        # Handle events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return
                elif event.key == pygame.K_PLUS or event.key == pygame.K_EQUALS:
                    # Increase ball speed
                    ball_speed_multiplier = min(ball_speed_multiplier + 0.2, 3.0)
                    current_vel = ball.velocity
                    if abs(current_vel.x) > 10 or abs(current_vel.y) > 10:  # Only if ball is moving
                        ball.velocity = (current_vel.x * 1.2, current_vel.y * 1.2)
                    print(f"⚡ Ball speed increased: {ball_speed_multiplier:.1f}x")
                elif event.key == pygame.K_MINUS:
                    # Decrease ball speed
                    ball_speed_multiplier = max(ball_speed_multiplier - 0.2, 0.5)
                    current_vel = ball.velocity
                    if abs(current_vel.x) > 10 or abs(current_vel.y) > 10:  # Only if ball is moving
                        ball.velocity = (current_vel.x * 0.8, current_vel.y * 0.8)
                    print(f"🐌 Ball speed decreased: {ball_speed_multiplier:.1f}x")
        
        # Get current game state
        state = get_game_state(ball, left_paddle, right_paddle)
        
        # Handle keyboard input (improved)
        keys = pygame.key.get_pressed()
        
        # Left player controls (W/S keys)
        if not left_ai:  # Human player
            if keys[pygame.K_w]:
                move_paddle(left_paddle, "up", PADDLE_SPEED)
            elif keys[pygame.K_s]:
                move_paddle(left_paddle, "down", PADDLE_SPEED)
        else:  # AI player
            if frame % AI_DECISION_INTERVAL == 0:
                left_direction, left_val = left_ai.query(state, "left")
                print(f"AI left decision: {left_direction}, {left_val}")
            move_paddle(left_paddle, left_direction, left_val)
        
        # Right player controls (Arrow keys)
        if not right_ai:  # Human player
            if keys[pygame.K_UP]:
                move_paddle(right_paddle, "up", PADDLE_SPEED)
            elif keys[pygame.K_DOWN]:
                move_paddle(right_paddle, "down", PADDLE_SPEED)
        else:  # AI player
            if frame % AI_DECISION_INTERVAL == 0:
                right_direction, right_val = right_ai.query(state, "right")
                print(f"AI right decision: {right_direction}, {right_val}")
            move_paddle(right_paddle, right_direction, right_val)
        
        # CPU strategy for CPU modes
        if mode == "cpu_vs_cpu":
            if frame % AI_DECISION_INTERVAL == 0:
                left_direction, left_val = cpu_strategy(state["ball"]["y"], state["left_paddle"]["y"])
                right_direction, right_val = cpu_strategy(state["ball"]["y"], state["right_paddle"]["y"])
            move_paddle(left_paddle, left_direction, left_val)
            move_paddle(right_paddle, right_direction, right_val)
        elif mode == "human_vs_cpu":
            if frame % AI_DECISION_INTERVAL == 0:
                right_direction, right_val = cpu_strategy(state["ball"]["y"], state["right_paddle"]["y"])
            move_paddle(right_paddle, right_direction, right_val)
        
        # Physics step
        space.step(1 / 60.0)
        
        # Draw everything
        draw_game(space, left_score, right_score, serve_left, mode, ball_speed_multiplier, left_ai, right_ai)
        pygame.display.flip()
        clock.tick(60)
        
        # Score detection
        if ball.position.x < 0:
            right_score += 1
            total_points += 1
            serve_left = (total_points % (SERVICE_ALTERNATE_EVERY * 2)) < SERVICE_ALTERNATE_EVERY
            reset_ball(ball, serve_left, ball_speed_multiplier)
            print(f"Point! Score: {left_score}-{right_score}")
        elif ball.position.x > WIDTH:
            left_score += 1
            total_points += 1
            serve_left = (total_points % (SERVICE_ALTERNATE_EVERY * 2)) < SERVICE_ALTERNATE_EVERY
            reset_ball(ball, serve_left, ball_speed_multiplier)
            print(f"Point! Score: {left_score}-{right_score}")
        
        frame += 1
    
    # Game over screen
    show_winner(left_score, right_score, left_ai, right_ai)

def show_winner(left_score, right_score, left_ai, right_ai):
    """Display winner screen"""
    screen.fill(BLACK)
    
    winner = "Left" if left_score > right_score else "Right"
    winner_name = ""
    if winner == "Left":
        winner_name = left_ai.name if left_ai else "Human"
    else:
        winner_name = right_ai.name if right_ai else "Human"
    
    # Winner text
    win_text = font_large.render(f"🏆 {winner_name} Wins!", True, WHITE)
    score_text = font.render(f"Final Score: {left_score} - {right_score}", True, WHITE)
    
    screen.blit(win_text, (WIDTH // 2 - win_text.get_width() // 2, HEIGHT // 2 - 40))
    screen.blit(score_text, (WIDTH // 2 - score_text.get_width() // 2, HEIGHT // 2))
    
    # Instructions
    continue_text = font.render("Press SPACE to return to menu, ESC to quit", True, WHITE)
    screen.blit(continue_text, (WIDTH // 2 - continue_text.get_width() // 2, HEIGHT // 2 + 40))
    
    pygame.display.flip()
    
    # Wait for input
    waiting = True
    while waiting:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    waiting = False
                elif event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    exit()

def select_mode():
    """Enhanced mode selection with AI status"""
    while True:
        screen.fill(BLACK)
        
        # Title
        title = font_large.render("🏓 AI Table Tennis Arena", True, WHITE)
        screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 30))
        
        # AI Status
        ai_status = []
        if claude_ai.available:
            ai_status.append(f"🎯 Claude: Ready")
        if openai_ai.available:
            ai_status.append(f"🔥 OpenAI: Ready")
        if ollama_ai.available:
            ai_status.append(f"🦙 Ollama: Ready")
        
        if not ai_status:
            ai_status.append("⚠️ No AI providers available")
        
        for i, status in enumerate(ai_status):
            color = WHITE if "Ready" in status else RED
            text = font.render(status, True, color)
            screen.blit(text, (WIDTH // 2 - text.get_width() // 2, 70 + i * 25))
        
        # Mode options
        modes = [
            ("1", "Human vs Claude", claude_ai.available),
            ("2", "Human vs OpenAI", openai_ai.available), 
            ("3", "Human vs Ollama", ollama_ai.available),
            ("4", "Claude vs OpenAI", claude_ai.available and openai_ai.available),
            ("5", "Claude vs Ollama", claude_ai.available and ollama_ai.available),
            ("6", "OpenAI vs Ollama", openai_ai.available and ollama_ai.available),
            ("7", "Human vs CPU", True),
            ("8", "CPU vs CPU", True),
            ("9", "Human vs Human", True)
        ]
        
        y_start = 150
        for i, (key, description, available) in enumerate(modes):
            color = WHITE if available else (128, 128, 128)
            text = font.render(f"Press {key}: {description}", True, color)
            screen.blit(text, (WIDTH // 2 - text.get_width() // 2, y_start + i * 30))
        
        # Controls
        controls = [
            "Controls: W/S for left paddle, ↑/↓ for right paddle",
            "Ball Speed: +/= to increase, - to decrease",
            "ESC: Return to menu during game"
        ]
        for i, control in enumerate(controls):
            text = font.render(control, True, (200, 200, 200))
            screen.blit(text, (WIDTH // 2 - text.get_width() // 2, HEIGHT - 60 + i * 25))
        
        pygame.display.flip()
        
        # Handle mode selection
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_1 and claude_ai.available:
                    run_game("human_vs_claude", None, claude_ai)
                elif event.key == pygame.K_2 and openai_ai.available:
                    run_game("human_vs_openai", None, openai_ai)
                elif event.key == pygame.K_3 and ollama_ai.available:
                    run_game("human_vs_ollama", None, ollama_ai)
                elif event.key == pygame.K_4 and claude_ai.available and openai_ai.available:
                    run_game("claude_vs_openai", claude_ai, openai_ai)
                elif event.key == pygame.K_5 and claude_ai.available and ollama_ai.available:
                    run_game("claude_vs_ollama", claude_ai, ollama_ai)
                elif event.key == pygame.K_6 and openai_ai.available and ollama_ai.available:
                    run_game("openai_vs_ollama", openai_ai, ollama_ai)
                elif event.key == pygame.K_7:
                    run_game("human_vs_cpu", None, None)
                elif event.key == pygame.K_8:
                    run_game("cpu_vs_cpu", None, None)
                elif event.key == pygame.K_9:
                    run_game("human_vs_human", None, None)
                elif event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    exit()
        
        clock.tick(60)

if __name__ == "__main__":
    print("🏓 AI Table Tennis Arena Starting...")
    print(f"Claude available: {claude_ai.available}")
    print(f"OpenAI available: {openai_ai.available}")
    print(f"Ollama available: {ollama_ai.available}")
    
    # Force window to front
    os.environ['SDL_VIDEO_WINDOW_POS'] = 'centered'
    
    print("🎯 Showing game menu...")
    try:
        select_mode()
    except KeyboardInterrupt:
        print("\n🏓 Game interrupted")
    except Exception as e:
        print(f"Game error: {e}")
    finally:
        pygame.quit()
        print("🏓 Game closed")