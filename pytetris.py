import pygame
import random
import os
import copy

# Potential Todo:
# Don't generate new shape until line finishes clearing (kept doing it anyways when I tried?),
# Add config file for controls

controls = {
    "left": {pygame.K_LEFT},
    "right": {pygame.K_RIGHT},
    "down": {pygame.K_DOWN},
    "hard_drop": {pygame.K_SPACE},
    "left_rot": {pygame.K_z},
    "right_rot": {pygame.K_x, pygame.K_UP},  # Added Up Arrow for right rotation
    "rot_180": {pygame.K_a},
    "hold": {pygame.K_c},
    "pause": {pygame.K_p},
    "quit": {pygame.K_ESCAPE},
    "ghost": {pygame.K_g},
    "scale1": {pygame.K_1},
    "scale2": {pygame.K_2},
    "scale3": {pygame.K_3},
    "scale4": {pygame.K_4}
}

# Inits
pygame.init()
clock = pygame.time.Clock()

# Window info
(display_width, display_height) = (256, 224)
window_title = 'PyTetris'

# Create window
display = pygame.display.set_mode((display_width, display_height))
screen = pygame.image.load(f'images/gui/bg.png').convert()
pygame.display.set_caption(window_title)

# Screen overlays
paused_gui = pygame.image.load(f'images/gui/paused.png').convert_alpha()
game_over_gui = pygame.image.load(f'images/gui/gameOver.png').convert_alpha()

# Window scale
def setScale(scale: int):
    global display, display_width, display_height
    os.environ['SDL_VIDEO_CENTERED'] = '1'
    display = pygame.display.set_mode((scale * display_width, scale * display_height))
setScale(3)

def rotateTable(table):
    return [[*r][::-1] for r in zip(*table)]

# Map storage
tileMap = [['' for _ in range(10)] for _ in range(20)]

def setTileonMap(x, y, value):
    tileMap[y][x] = value

def getTileonMap(x, y):
    return tileMap[y][x]

# Draw Text
def writeNums(pos: tuple, num: int, length: int):
    full_num = str(num)
    full_num = (length - len(full_num)) * '0' + full_num
    for i, c in enumerate(full_num):
        screen.blit(pygame.image.load(f'images/gui/text/{c}.png').convert_alpha(), (pos[0] + 8 * i, pos[1]))

def getInp(control_scheme):
    keys = pygame.key.get_pressed()
    for key in controls[control_scheme]:
        if keys[key]:
            return True
    return False

# Define shapes using hashtags
shape_definitions = {
    'I': {'color': 'toi', 'hitbox': [
        "####",
    ]},
    'J': {'color': 'js', 'hitbox': [
        "### ",
        "  #"
    ]},
    'L': {'color': 'zl', 'hitbox': [
        "### ",
        "#   "
    ]},
    'O': {'color': 'toi', 'hitbox': [
        "##",
        "##"
    ]},
    'S': {'color': 'js', 'hitbox': [
        " ##",
        "## "
    ]},
    'T': {'color': 'toi', 'hitbox': [
        "###",
        " # "
    ]},
    'Z': {'color': 'zl', 'hitbox': [
        "## ",
        " ##"
    ]}
}

class Shape:
    def __init__(self, shape_id, is_ghost=False):
        self.id = shape_id
        self.color = 'ghost' if is_ghost else shape_definitions[shape_id]['color']
        self.hitbox = shape_definitions[shape_id]['hitbox']
        self.base_hitbox = self.hitbox
        self.rotation = 0
        self.x = 4
        self.y = 0
        self.create_pieces()

    def create_pieces(self):
        self.pieces = []
        for y, row in enumerate(self.hitbox):
            for x, c in enumerate(row):
                if c == '#':
                    piece = {'image': pygame.image.load(f'images/pieces/{self.color}.png').convert_alpha(),
                             'localx': x, 'localy': y}
                    self.pieces.append(piece)
        self.width = max(len(row) for row in self.hitbox)
        self.height = len(self.hitbox)

    def rotate(self, dir):
        self.rotation = (self.rotation + dir) % 4
        new_hitbox = self.base_hitbox
        for _ in range(self.rotation):
            new_hitbox = self.rotate_hitbox(new_hitbox)
        self.hitbox = new_hitbox
        self.create_pieces()
        self.wall_kick(dir)

    def rotate_hitbox(self, hitbox):
        return [''.join(row) for row in zip(*hitbox[::-1])]

    def wall_kick(self, dir):
        offsets = [0, -1, 1, -2, 2]
        for offset in offsets:
            valid = True
            self.x += offset * dir
            for piece in self.pieces:
                if self.x + piece['localx'] < 0 or self.x + piece['localx'] >= 10 or self.y + piece['localy'] >= 20 or getTileonMap(self.x + piece['localx'], self.y + piece['localy']) != '':
                    valid = False
                    break
            if valid:
                return
            self.x -= offset * dir

    def draw(self, offset_x=0, offset_y=0, center=False):
        for piece in self.pieces:
            piece_rect = piece['image'].get_rect()
            piece_rect.x = 96 + (8 * (self.x + piece['localx'])) + offset_x
            piece_rect.y = 40 + (8 * (self.y + piece['localy'])) + offset_y
            if center:
                piece_rect.x += (4 - self.width) * 4  # Center horizontally
                piece_rect.y += (2 - self.height) * 4  # Center vertically
            screen.blit(piece['image'], piece_rect)


    def stamp(self):
        global stamps
        for piece in self.pieces:
            x = self.x + piece['localx']
            y = self.y + piece['localy']
            setTileonMap(x, y, self.id)
            stamps.append(((96 + (8 * x), 40 + (8 * y)), {'image': piece['image'], 'globalx': x, 'globaly': y}))

# Stats and scores
top_score = 10000
score = 0
lines = 0
stats = {key: 0 for key in shape_definitions.keys()}
lvl = 0

TotalAREpauseLength = 60
AREFlashes = 3

# Clearing Lines
def clearLine(y: int):
    global stamps, lines, lvl, speed, AREpaused, AREpauseLength, flash_stamps, linesCleared
    sounds['line_clear'].play()
    linesCleared += 1
    AREpaused = True
    AREpauseLength = TotalAREpauseLength
    tileMap.pop(y)
    tileMap.insert(0, ['' for _ in range(10)])
    temp = []
    for pos, piece in stamps:
        if piece['globaly'] != y:
            temp.append((pos, piece))
        else:
            flash_stamps.append((pos, piece))
    stamps = temp
    lines += 1
    if lines % 10 == 0:
        lvl += 1
        if lvl < 9:
            speed -= 5
        elif lvl == 9:
            speed -= 2
        elif lvl in [10, 13, 16, 19, 29]:
            speed -= 1
        if lvl > 99:
            lvl = 99
            speed = 48
    if lines > 999:
        lines = 999

# Stamping previous placed shapes
stamps = []

def drawStamps():
    for pos, piece in stamps:
        screen.blit(piece['image'], pos)

flash_stamps = []

def flashStamps():
    global AREpauseLength
    for pos, piece in flash_stamps:
        if AREpauseLength <= (TotalAREpauseLength / (2 * AREFlashes)) or (AREpauseLength > (TotalAREpauseLength / (2 * AREFlashes)) * 2 and AREpauseLength <= (TotalAREpauseLength / (2 * AREFlashes)) * 3) or (AREpauseLength > (TotalAREpauseLength / (2 * AREFlashes)) * 4 and AREpauseLength <= (TotalAREpauseLength / (2 * AREFlashes)) * 5):
            screen.blit(pygame.image.load('images/pieces/ghost.png').convert_alpha(), pos)
        else:
            screen.blit(piece['image'], pos)

# Frame and speed info
frameRate = 60
speed = 48  # ticks between fall
last_fall = 0
last_input = 0
last_soft_input = 0
holding_input = False
show_ghost = True
lock_delay = 30  # Frames to wait before locking a piece
lock_timer = 0

# Pick the first and second shape
currentShape = Shape(random.choice(list(shape_definitions.keys())))
nextShape = Shape(random.choice(list(shape_definitions.keys())))
ghostShape = Shape(currentShape.id, is_ghost=True)

# Music and sounds
pygame.mixer.music.load('music/music.mp3')
pygame.mixer.music.play(-1)

sounds = {
    "move": pygame.mixer.Sound('music/move.mp3'),
    "rotate": pygame.mixer.Sound('music/rotate.mp3'),
    "place": pygame.mixer.Sound('music/place.mp3'),
    "line_clear": pygame.mixer.Sound('music/line_clear.mp3'),
    "death": pygame.mixer.Sound('music/death.mp3')
}

# Main game loop
running = True
closed = False
paused = False
AREpaused = False
AREpauseLength = 0
linesCleared = 0

while running:
    clock.tick(frameRate)
    for event in pygame.event.get():
        # Detect window closed
        if event.type == pygame.QUIT:
            closed = True
        # Scale keys
        if event.type == pygame.KEYDOWN:
            if event.key in controls['scale1']:
                setScale(1)
            elif event.key in controls['scale2']:
                setScale(2)
            elif event.key in controls['scale3']:
                setScale(3)
            elif event.key in controls['scale4']:
                setScale(4)
            if event.key in controls['pause']:
                paused = not paused
            if event.key in controls['quit']:
                closed = True
            if event.key in controls['ghost']:
                show_ghost = not show_ghost
            if (not paused) and (not AREpaused) and event.key in controls['left_rot']:
                currentShape.rotate(-1)
                i = True
                for piece in currentShape.pieces:
                    if currentShape.x + piece['localx'] >= 10 or currentShape.y + piece['localy'] >= 20 or getTileonMap(currentShape.x + piece['localx'], currentShape.y + piece['localy']) != '':
                        currentShape.rotate(1)
                        i = False
                        break
                if i:
                    sounds['rotate'].play()
            if (not paused) and (not AREpaused) and event.key in controls['right_rot']:
                currentShape.rotate(1)
                i = True
                for piece in currentShape.pieces:
                    if currentShape.x + piece['localx'] >= 10 or currentShape.y + piece['localy'] >= 20 or getTileonMap(currentShape.x + piece['localx'], currentShape.y + piece['localy']) != '':
                        currentShape.rotate(-1)
                        i = False
                        break
                if i:
                    sounds['rotate'].play()
            if (not paused) and (not AREpaused) and event.key in controls['rot_180']:
                currentShape.rotate(2)
                i = True
                for piece in currentShape.pieces:
                    if currentShape.x + piece['localx'] >= 10 or currentShape.y + piece['localy'] >= 20 or getTileonMap(currentShape.x + piece['localx'], currentShape.y + piece['localy']) != '':
                        currentShape.rotate(2)
                        i = False
                        break
                if i:
                    sounds['rotate'].play()
            if (not paused) and (not AREpaused) and event.key in controls['hard_drop']:
                while not collided:
                    currentShape.y += 1
                    score += 2
                    if currentShape.y + currentShape.height >= 20:
                        collided = True
                    else:
                        for piece in currentShape.pieces:
                            if getTileonMap(currentShape.x + piece['localx'], currentShape.y + piece['localy']) != '':
                                collided = True
                                break
                currentShape.y -= 1
                currentShape.stamp()
                sounds['place'].play()
                if not currentShape.id in stats.keys():
                    stats[currentShape.id] = 0
                stats[currentShape.id] += 1
                if stats[currentShape.id] > 999:
                    stats[currentShape.id] = 999
                currentShape = nextShape
                nextShape = Shape(random.choice(list(shape_definitions.keys())))
                ghostShape = Shape(currentShape.id, is_ghost=True)

    if (not paused) and (not AREpaused):
        # Input
        if (not getInp('left')) and (not getInp('right')):
            holding_input = False
        if getInp('left') and (not getInp('right')) and (not left_collided) and last_input == 0:
            currentShape.x -= 1
            sounds['move'].play()
            if holding_input == False:
                last_input = 16
            else:
                last_input = 6
            holding_input = True
        if getInp('right') and (not getInp('left')) and (not right_collided) and last_input == 0:
            currentShape.x += 1
            sounds['move'].play()
            if holding_input == False:
                last_input = 16
            else:
                last_input = 6
            holding_input = True
        if getInp('down') and currentShape.y + currentShape.height < 20 and not collided and (last_soft_input == 0 or speed == 1):
            currentShape.y += 1
            score += 1
            if score > 999999:
                score = 999999
            last_soft_input = 2

    # Rendering
    screen = pygame.image.load(f'images/gui/bg.png').convert()
    drawStamps()
    if AREpaused:
        flashStamps()
    writeNums((152, 16), lines, 3)
    writeNums((192, 32), top_score, 6)
    writeNums((192, 56), score, 6)
    writeNums((208, 160), lvl, 2)
    i = 0
    for shape in shape_definitions.keys():
        writeNums((48, 88 + 16 * i), stats[shape], 3)
        i += 1

    # Test game over
    for c in tileMap[0]:
        if c != '':
            running = False
            break
    if running:
        nextShape.x = 0  # Reset the position for the next shape preview
        nextShape.y = 0  # Reset the position for the next shape preview
        nextShape.draw(offset_x=100, offset_y=70, center=True)  # Draw next shape to the right of the main screen
        if show_ghost:
            ghostShape.draw()
    currentShape.draw()
    if paused and running:
        screen.blit(paused_gui, (0, 0))
    if not running:
        screen.blit(game_over_gui, (0, 0))
    scaled = pygame.transform.scale(screen, display.get_size())
    display.blit(scaled, (0, 0))
    pygame.display.flip()

    if (not paused) and (not AREpaused):
        # Collision and line clearing
        collided = False
        left_collided = False
        right_collided = False

        tempMap = copy.deepcopy(tileMap)
        for piece in currentShape.pieces:
            x = currentShape.x + piece['localx']
            y = currentShape.y + piece['localy']
            tempMap[y][x] = 'x'
        x = 0
        y = 0
        for row in tempMap:
            for c in row:
                if c == 'x':
                    if currentShape.y == (20 - currentShape.height):
                        collided = True
                    elif not (tempMap[y + 1][x] in 'x '):
                        collided = True

                    if currentShape.x <= 0:
                        left_collided = True
                    elif not (tempMap[y][x - 1] in 'x '):
                        left_collided = True

                    if currentShape.x >= 10 - currentShape.width:
                        right_collided = True
                    elif not (tempMap[y][x + 1] in 'x '):
                        right_collided = True
                x += 1
            y += 1
            x = 0
        del tempMap

        # Get next frame's ghost
        ghostCollided = False

        ghostShape.x = currentShape.x
        ghostShape.y = currentShape.y - 1
        ghostShape.rotation = currentShape.rotation - 1
        ghostShape.rotate(1)
        while not ghostCollided:
            ghostShape.y += 1
            if ghostShape.y == (20 - ghostShape.height):
                ghostCollided = True
            else:
                tempMap = copy.deepcopy(tileMap)
                for piece in ghostShape.pieces:
                    x = ghostShape.x + piece['localx']
                    y = ghostShape.y + piece['localy']
                    tempMap[y][x] = 'x'
                x = 0
                y = 0
                for row in tempMap:
                    for c in row:
                        if c == 'x':
                            if not (tempMap[y + 1][x] in 'x '):
                                ghostCollided = True
                                break
                        x += 1
                    y += 1
                    x = 0
                del tempMap

        i = 0
        cleared_count = 0
        for row in tileMap:
            cleared = True
            for x in row:
                if x == '':
                    cleared = False
                    break
            if cleared:
                clearLine(i)
                cleared_count += 1
            i += 1
        score += (cleared_count // 4) * (1200 * (lvl + 1))  # tetrises
        score += ((cleared_count % 4) // 3) * (300 * (lvl + 1))  # triples
        score += (((cleared_count % 4) % 3) // 2) * (100 * (lvl + 1))  # doubles
        score += (((cleared_count % 4) % 3) % 2) * (40 * (lvl + 1))  # singles
        if score > 999999:
            score = 999999
        if score > top_score:
            top_score = score

        if collided:
            if lock_timer >= lock_delay:
                currentShape.stamp()
                sounds['place'].play()
                if not currentShape.id in stats.keys():
                    stats[currentShape.id] = 0
                stats[currentShape.id] += 1
                if stats[currentShape.id] > 999:
                    stats[currentShape.id] = 999
                currentShape = nextShape
                nextShape = Shape(random.choice(list(shape_definitions.keys())))
                ghostShape = Shape(currentShape.id, is_ghost=True)
                lock_timer = 0
            else:
                lock_timer += 1
        elif last_fall >= speed and not getInp('down'):
            currentShape.y += 1
            last_fall = 0
            lock_timer = 0
        else:
            last_fall += 1
        if last_input > 0:
            last_input -= 1
        if last_soft_input > 0:
            last_soft_input -= 1
    if AREpaused and AREpauseLength > 0:
        AREpauseLength -= 1
        if AREpauseLength == 0:
            AREpaused = False
            temp = []
            topBadY = 20
            for pos, piece in flash_stamps:
                y = piece['globaly']
                if y < topBadY:
                    topBadY = y
            for pos, piece in stamps:
                if piece['globaly'] < topBadY:
                    piece['globaly'] += linesCleared
                    temp.append(((pos[0], pos[1] + 8 * linesCleared), piece))
                else:
                    temp.append((pos, piece))
            flash_stamps = []
            stamps = temp
            linesCleared = 0
    if closed:
        running = False

# Window closed logic
else:
    pygame.mixer.music.stop()
    sounds['death'].play()
    game_over = True
    while game_over and not closed:
        for event in pygame.event.get():
            # Detect window closed
            if event.type == pygame.QUIT:
                game_over = False
            if event.type == pygame.KEYDOWN:
                if event.key in controls['quit']:
                    closed = True
    else:
        print('crashed :(')  # we love how this is still here lmao
