import pygame
import random
import time
import os

# ---- Wumpus World Environment ----
class WumpusWorld:
    def __init__(self):
        self.grid_size = 4
        self.agent_pos = (0, 0)
        self.agent_dir = "down"
        self.has_gold = False
        self.has_arrow = True
        self.wumpus_alive = True
        self.world = self.generate_world()
        self.percepts = self.get_percepts()

    def generate_world(self):
        world = [[{"pit": False, "wumpus": False, "gold": False} for _ in range(self.grid_size)] for _ in range(self.grid_size)]
        for i in range(self.grid_size):
            for j in range(self.grid_size):
                if (i, j) != (0, 0) and random.random() < 0.2:
                    world[i][j]["pit"] = True

        # Place Wumpus
        wumpus_pos = (random.randint(0, 3), random.randint(0, 3))
        while wumpus_pos == (0, 0):
            wumpus_pos = (random.randint(0, 3), random.randint(0, 3))
        world[wumpus_pos[0]][wumpus_pos[1]]["wumpus"] = True

        # Place Gold
        gold_pos = (random.randint(0, 3), random.randint(0, 3))
        while gold_pos == (0, 0):
            gold_pos = (random.randint(0, 3), random.randint(0, 3))
        world[gold_pos[0]][gold_pos[1]]["gold"] = True

        return world

    def get_percepts(self):
        x, y = self.agent_pos
        cell = self.world[x][y]
        percepts = {"stench": False, "breeze": False, "glitter": False, "bump": False, "scream": False}

        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < 4 and 0 <= ny < 4:
                if self.world[nx][ny]["wumpus"] and self.wumpus_alive:
                    percepts["stench"] = True
                if self.world[nx][ny]["pit"]:
                    percepts["breeze"] = True

        if cell["gold"]:
            percepts["glitter"] = True

        return percepts

    def move_forward(self):
        x, y = self.agent_pos
        new_x, new_y = x, y
        if self.agent_dir == "up":
            new_x -= 1
        elif self.agent_dir == "down":
            new_x += 1
        elif self.agent_dir == "left":
            new_y -= 1
        elif self.agent_dir == "right":
            new_y += 1

        if 0 <= new_x < 4 and 0 <= new_y < 4:
            self.agent_pos = (new_x, new_y)
            self.percepts = self.get_percepts()
            return True
        else:
            self.percepts["bump"] = True
            return False

    def turn_left(self):
        dirs = ["up", "left", "down", "right"]
        idx = dirs.index(self.agent_dir)
        self.agent_dir = dirs[(idx + 1) % 4]
        self.percepts = self.get_percepts()

    def turn_right(self):
        dirs = ["up", "right", "down", "left"]
        idx = dirs.index(self.agent_dir)
        self.agent_dir = dirs[(idx + 1) % 4]
        self.percepts = self.get_percepts()

    def shoot_arrow(self):
        if not self.has_arrow:
            return False
        self.has_arrow = False
        x, y = self.agent_pos
        wumpus_killed = False
        if self.agent_dir == "up":
            for i in range(x - 1, -1, -1):
                if self.world[i][y]["wumpus"]:
                    wumpus_killed = True
                    break
        elif self.agent_dir == "down":
            for i in range(x + 1, 4):
                if self.world[i][y]["wumpus"]:
                    wumpus_killed = True
                    break
        elif self.agent_dir == "left":
            for j in range(y - 1, -1, -1):
                if self.world[x][j]["wumpus"]:
                    wumpus_killed = True
                    break
        elif self.agent_dir == "right":
            for j in range(y + 1, 4):
                if self.world[x][j]["wumpus"]:
                    wumpus_killed = True
                    break

        if wumpus_killed:
            self.wumpus_alive = False
            self.percepts["scream"] = True
            return True
        return False

    def grab_gold(self):
        x, y = self.agent_pos
        if self.world[x][y]["gold"]:
            self.has_gold = True
            self.world[x][y]["gold"] = False
            self.percepts["glitter"] = False
            return True
        return False
    
    def get_wumpus_position(self):
        if not self.wumpus_alive:
            return None
        for r in range(self.grid_size):
            for c in range(self.grid_size):
                if self.world[r][c]["wumpus"]:
                    return (r, c)
        return None

    def is_game_over(self):
        x, y = self.agent_pos
        cell = self.world[x][y]
        if cell["pit"] or (cell["wumpus"] and self.wumpus_alive):
            return "lose"
        if self.has_gold and self.agent_pos == (0, 0):
            return "win"
        return "continue"

# ---- Simple Logic Agent ----
class Agent:
    def __init__(self):
        self.kb = {}
        self.visited = set()
        self.path = []  # stack for moves

    def update_kb(self, percepts, pos):
        x, y = pos
        # Mark current cell as safe if no breeze or stench
        self.kb[pos] = {"safe": not percepts["breeze"] and not percepts["stench"], "visited": True}
        self.visited.add(pos)

        # If breeze, mark adjacent unvisited cells as unsafe (possible pit)
        if percepts["breeze"]:
            for dx, dy in [(-1,0), (1,0), (0,-1), (0,1)]:
                nx, ny = x + dx, y + dy
                if 0 <= nx < 4 and 0 <= ny < 4:
                    if (nx, ny) not in self.kb:
                        self.kb[(nx, ny)] = {"safe": False, "visited": False}

    def next_move(self, pos):
        x, y = pos
        possible_moves = [(x + dx, y + dy) for dx, dy in [(-1,0), (1,0), (0,-1), (0,1)]
                          if 0 <= x + dx < 4 and 0 <= y + dy < 4]

        for move in possible_moves:
            # Prefer unvisited and safe
            if move not in self.visited and self.kb.get(move, {}).get("safe", True) == True:
                self.path.append(pos)
                return move

        for move in possible_moves:
            # Fallback: visited safe cells (backtracking)
            if self.kb.get(move, {}).get("safe", False):
                self.path.append(pos)
                return move

        return None

# ---- Drawing Function ----
def draw_world(env, screen, images):
    TILE = 100
    screen.fill((255, 255, 255))

    for i in range(4):
        for j in range(4):
            x = j * TILE
            y = i * TILE
            screen.blit(images["tile"], (x, y))

            cell = env.world[i][j]
            if cell["pit"]:
                screen.blit(images["pit"], (x + 10, y + 10))
            if cell["wumpus"] and env.wumpus_alive:
                screen.blit(images["wumpus"], (x + 10, y + 10))
            if cell["gold"]:
                screen.blit(images["gold"], (x + 25, y + 25))

    # Agent
    ax, ay = env.agent_pos
    agent_img = images["agent"]
    screen.blit(agent_img, (ay * TILE + 25, ax * TILE + 25))

    # Draw arrow for direction
    arrow_img = images[f"arrow_{env.agent_dir}"]
    screen.blit(arrow_img, (ay * TILE + 30, ax * TILE + 30))
    pygame.display.flip()

# ---- Main Loop ----
def main():
    pygame.init()
    screen = pygame.display.set_mode((400, 400))
    pygame.display.set_caption("Wumpus World Agent")

    images = {
        "agent": pygame.transform.scale(pygame.image.load("agent.jpg"), (60, 60)),
        "wumpus": pygame.transform.scale(pygame.image.load("wumpus.png"), (80, 80)),
        "pit": pygame.transform.scale(pygame.image.load("pit.jpg"), (80, 80)),
        "gold": pygame.transform.scale(pygame.image.load("gold.png"), (70, 70)),
        "tile": pygame.transform.scale(pygame.image.load("empty.jpg"), (100, 100)),
        "arrow_up": pygame.transform.scale(pygame.image.load("arrow_up.png"), (20, 20)),
        "arrow_down": pygame.transform.scale(pygame.image.load("arrow_down.png"), (20, 20)),
        "arrow_left": pygame.transform.scale(pygame.image.load("arrow_left.png"), (20, 20)),
        "arrow_right": pygame.transform.scale(pygame.image.load("arrow_right.png"), (20, 20))
    }

    env = WumpusWorld()
    agent = Agent()
    running = True
    returning_home = False

    while running:
        draw_world(env, screen, images)
        pygame.time.delay(1000)

        percepts = env.get_percepts()
        agent.update_kb(percepts, env.agent_pos)

        # Shoot Wumpus if stench detected and arrow is available
        if percepts["stench"] and env.has_arrow and env.wumpus_alive:
            wumpus_pos = env.get_wumpus_position()
            agent_row, agent_col = env.agent_pos

            if wumpus_pos:
                wr, wc = wumpus_pos
                # Turn toward Wumpus
                if wr == agent_row:
                    env.agent_dir = "left" if wc < agent_col else "right"
                elif wc == agent_col:
                    env.agent_dir = "up" if wr < agent_row else "down"

                shot = env.shoot_arrow()
                draw_world(env, screen, images)
                pygame.time.delay(500)
                if shot:
                    print("Agent shot the Wumpus! 💥")
                    font = pygame.font.SysFont(None, 36)
                    text = font.render("Wumpus Killed!", True, (200, 0, 0))
                    screen.blit(text, (100, 150))
                    pygame.display.flip()
                    pygame.time.delay(1500)

        # Grab gold if found
        if percepts["glitter"]:
            if env.grab_gold():
                draw_world(env, screen, images)
                font = pygame.font.SysFont(None, 48)
                text = font.render("Agent Won!", True, (0, 100, 0))
                screen.blit(text, (105,150))
                pygame.display.flip()
                print("Agent won! 🎉")
                pygame.time.delay(2000)

                # Reverse path to backtrack home
                agent.path = agent.path[::-1]
                returning_home = True
                continue

        if returning_home:
            if env.agent_pos == (0, 0):
                print("Agent returned home safely with gold! 🎯")
                running = False
            else:
                if agent.path:
                    next_pos = agent.path.pop(0)
                    env.agent_pos = next_pos
                    env.percepts = env.get_percepts()
                else:
                    # No path left but not home yet (should not happen)
                    print("No path back to home!")
                    running = False
        else:
            next_pos = agent.next_move(env.agent_pos)
            if next_pos:
                env.agent_pos = next_pos
                env.percepts = env.get_percepts()
            else:
                print("No safe moves available! Agent stuck.")
                running = False

        # Check for game over (fall in pit or encounter Wumpus alive)
        status = env.is_game_over()
        if status == "lose":
            font = pygame.font.SysFont(None, 48)
            text = font.render("Agent Died!", True, (255, 0, 0))
            screen.blit(text, (120, 150))
            pygame.display.flip()
            print("Agent died! Game over. ☠️")
            pygame.time.delay(2000)
            running = False

        # Event handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

    pygame.quit()

if __name__ == "__main__":
    main()
