import arcade
import random
from enum import Enum

class Position:
    def __init__(self, x, y):
        self.x = x
        self.y = y
    
    def move(self, by):
        self.x += by.x
        self.y += by.y
    
    def add(self, other):
        return Position(self.x + other.x, self.y + other.y)
    
    def subtract(self, by):
        return Position(self.x - by.x, self.y - by.y)
    
    def copy(self):
        return Position(self.x, self.y)
    
    def __iter__(self):
        return iter((self.x, self.y))

class Direction(Enum):
    UP = Position(0, 1)
    RIGHT = Position(1, 0)
    DOWN = Position(0, -1)
    LEFT = Position(-1, 0)

    def rotate(self, clockwise=True):
        return list(Direction)[(list(Direction).index(self) + (1 if clockwise else -1)) % len(list(Direction))]

    def get_opposite(self):
        opposite_directions = {
            Direction.UP: Direction.DOWN,
            Direction.DOWN: Direction.UP,
            Direction.LEFT: Direction.RIGHT,
            Direction.RIGHT: Direction.LEFT
        }
        return opposite_directions[self]

class Tetromino:
    def __init__(self, shape, color):
        self.shape: list[list[str]] = shape
        self.color: tuple[int, int, int] = color

    def get_origin(self, rotation: Direction = Direction.UP) -> Position:
        for y, row in enumerate(self.rotate(rotation)[::-1]):
            for x, cell in enumerate(row):
                if cell == 'O':
                    return Position(x, y)
        return Position(0, 0)

    def rotate(self, rotation: Direction):
        def transpose(matrix):
            transposed = [['_' for _ in range(len(matrix))] for _ in range(len(matrix[0]))]
            for y, row in enumerate(matrix):
                for x, cell in enumerate(row):
                    transposed[x][y] = cell
            return transposed

        if rotation is Direction.UP:
            return self.shape
        if rotation is Direction.DOWN:
            return [row[::-1] for row in self.shape[::-1]]
        if rotation is Direction.RIGHT:
            reversed_shape = self.shape[::-1]
            return transpose(reversed_shape)
        if rotation is Direction.LEFT:
            transposed_shape = transpose(self.shape)
            return transposed_shape[::-1]

    @staticmethod
    def get_all():
        I = Tetromino([['T'],
                       ['O'],
                       ['T'],
                       ['T']],
                      color=(0, 209, 146))
        J = Tetromino([['_', 'T'],
                       ['_', 'O'],
                       ['T', 'T']],
                      color=(48, 105, 152))
        L = Tetromino([['T', '_'],
                       ['O', '_'],
                       ['T', 'T']],
                      color=(208, 112, 56))
        O = Tetromino([['T', 'T'],
                       ['T', 'T']],
                      color=(221, 225, 0))
        S = Tetromino([['_', 'O', 'T'],
                       ['T', 'T', '_']],
                      color=(123, 209, 46))
        T = Tetromino([['T', 'O', 'T'],
                       ['_', 'T', '_']],
                      color=(186, 0, 166))
        Z = Tetromino([['T', 'T', '_'],
                       ['_', 'O', 'T']],
                      color=(202, 7, 67))
        return I, J, L, O, S, T, Z

class Piece:
    def __init__(self, tetromino, position, rotation=Direction.UP, is_ghost_piece=False):
        self.tetromino = tetromino
        self.position = position
        self.rotation = rotation
        self.is_ghost_piece = is_ghost_piece

    def draw(self, game):
        rotated_shape = self.tetromino.rotate(self.rotation)
        origin = self.tetromino.get_origin(self.rotation)
        if self.is_ghost_piece:
            color = (19, 19, 40)
        else:
            color = self.tetromino.color
        game.draw_cells(rotated_shape[::-1], self.position.subtract(origin), color)

    def is_colliding(self, board):
        rotated_shape = self.tetromino.rotate(self.rotation)
        origin = self.tetromino.get_origin(self.rotation)
        for y, row in enumerate(rotated_shape[::-1]):
            for x, cell in enumerate(row):
                if cell != '_':
                    x_pos, y_pos = self.position.subtract(origin).add(Position(x, y))
                    if not board.is_within_bounds(x_pos, y_pos):
                        return True
                    if board.cells[y_pos][x_pos] != '_':
                        return True
        return False

    def place(self, board):
        rotated_shape = self.tetromino.rotate(self.rotation)
        origin = self.tetromino.get_origin(self.rotation)
        for y, row in enumerate(rotated_shape[::-1]):
            for x, cell in enumerate(row):
                if cell != '_':
                    x_pos, y_pos = self.position.subtract(origin).add(Position(x, y))
                    board.cells[y_pos][x_pos] = self.tetromino.color
        game.clear_rows()

    def fall(self, game):
        self.position.move(Direction.DOWN.value)
        if self.is_colliding(game.board):
            self.position.move(Direction.UP.value)
            self.place(game.board)
            game.falling_piece = game.spawn_piece()
            game.update_ghost_piece()

    def drop(self, board, place=True):
        while not self.is_colliding(board):
            self.position.move(Direction.DOWN.value)
        self.position.move(Direction.UP.value)
        if place:
            self.place(board)

class Board:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.cells = [['_'] * width for _ in range(height)]
    
    def draw(self, game):
        game.draw_cells(self.cells, draw_background=True)
    
    def get_clearable_rows(self) -> list[int]:
        rows = []
        for y, row in enumerate(self.cells):
            if '_' not in row:
                rows.append(y)
        return rows
    
    def is_within_bounds(self, x, y):
        return 0 <= x < len(self.cells[0]) and 0 <= y < len(self.cells)

    def clear_row(self, row):
        self.cells.pop(row)
        new_row = ['_'] * len(self.cells[0])
        self.cells.append(new_row)

class Game(arcade.Window):
    def __init__(self):
        super().__init__(width=400, height=600, title='Simple Tetris', antialiasing=False, resizable=True)
        self.keys = set()
        self.last_keys = set()
        self.repeat_delays = {}
        self.board = Board(width=10, height=20)
        self.score = 0
        self.lines = 0
        self.score_rewards = {
            1: 100,
            2: 300,
            3: 500,
            4: 800
        }
        self.fall_interval = 0.3
        self.min_fall_interval = 0.1
        self.fall_increase_threshold = 1000
        self.fall_increase_rate = 0.05
        self.fall_timer = self.fall_interval
        self.game_over = False
        self.falling_piece = self.spawn_piece()
        self.ghost_piece = Piece(self.falling_piece.tetromino,
                                 self.falling_piece.position.copy(),
                                 is_ghost_piece=True)
        self.ghost_piece.drop(self.board, place=False)

    def on_update(self, time_delta):
        if self.game_over:
            return

        if self.fall_timer <= 0:
            self.falling_piece.fall(self)
            self.fall_timer = self.fall_interval
        else:
            self.fall_timer -= time_delta

        def move(d: Direction):
            self.falling_piece.position.move(d.value)
            if self.falling_piece.is_colliding(self.board):
                self.falling_piece.position.move(d.get_opposite().value)

        def rotate(d: Direction):
            self.falling_piece.rotation = self.falling_piece.rotation.rotate(clockwise=d is Direction.RIGHT)
            if self.falling_piece.is_colliding(self.board):
                def move_piece(direction, distance):
                    for _ in range(distance):
                        self.falling_piece.position.move(direction)
                distance_needed = {}
                for direction in Direction:
                    for distance in range(1, 4):
                        move_piece(direction.value, distance)
                        if not self.falling_piece.is_colliding(self.board):
                            distance_needed[direction] = distance
                            move_piece(direction.get_opposite().value, distance)
                            break
                        move_piece(direction.get_opposite().value, distance)
                if distance_needed:
                    lowest_direction = min(distance_needed, key=distance_needed.get)
                    move_piece(lowest_direction.value, distance_needed[lowest_direction])
                else:
                    self.falling_piece.rotation = self.falling_piece.rotation.rotate(clockwise=d is Direction.LEFT)

        def drop(d):
            self.falling_piece.drop(self.board, place=True)
            self.falling_piece = self.spawn_piece()

        key_actions = {
            arcade.key.UP: (rotate, Direction.RIGHT, None),
            arcade.key.DOWN: (rotate, Direction.LEFT, None),
            arcade.key.LEFT: (move, Direction.LEFT, 0.13),
            arcade.key.RIGHT: (move, Direction.RIGHT, 0.13),
            arcade.key.SPACE: (drop, None, None),
            arcade.key.ENTER: (drop, None, None)
        }

        for key, (action, direction, repeat_after) in key_actions.items():
            delay = self.repeat_delays.get(key, 0)
            if delay == None:
                delay = 0
            if key in self.keys:
                delay = self.repeat_delays.get(key, 0)
                if key not in self.last_keys or (repeat_after is not None and delay <= 0):
                    action(direction)
                    self.update_ghost_piece()
                    self.repeat_delays[key] = repeat_after
                else:
                    self.repeat_delays[key] = max(0, delay - time_delta) if delay is not None else 0
        self.last_keys = self.keys.copy()

    def on_draw(self):
        self.clear()
        if self.game_over:
            arcade.draw_text(
                "Game Over",
                self.width // 2,
                self.height // 2,
                arcade.color.WHITE,
                35,
                anchor_x="center",
                anchor_y="center",
            )
            return
        self.board.draw(self)
        self.ghost_piece.draw(self)
        self.falling_piece.draw(self)
        self.draw_grid()

    def draw_grid(self):
        cell_width = self.width / self.board.width
        cell_height = self.height / self.board.height
        for y in range(self.board.height + 1):
            for x in range(self.board.width + 1):
                pos_x = x * cell_width
                pos_y = y * cell_height
                arcade.draw_rect_outline(
                    arcade.Rect(
                        left=x * cell_width,
                        right=(x + 1) * cell_width,
                        bottom=y * cell_height,
                        top=(y + 1) * cell_height,
                        width=cell_width,
                        height=cell_height,
                        x=x,
                        y=y,
                    ),
                    arcade.color.BLACK,
                    5,
                )
                arcade.draw_circle_filled(pos_x, pos_y, 5, arcade.color.BLACK)

    def draw_cells(self, cells, position=Position(0, 0), color=None, draw_background=False):
        cell_width = self.width / self.board.width
        cell_height = self.height / self.board.height
        for y, row in enumerate(cells):
            for x, cell in enumerate(row):
                center_x = ((position.x + x) * cell_width) + (cell_width / 2)
                center_y = ((position.y + y) * cell_height) + (cell_height / 2)
                if not color and draw_background and cell == '_':
                    draw_color = (7, 7, 30)
                elif cell != '_':
                    draw_color = color if color else cell
                else:
                    continue
                arcade.draw_rect_filled(arcade.Rect(left=center_x - cell_width / 2,
                                                    right=center_x + cell_width / 2,
                                                    bottom=center_y - cell_height / 2,
                                                    top=center_y + cell_height / 2,
                                                    width=cell_width,
                                                    height=cell_height,
                                                    x=center_x,
                                                    y=center_y), draw_color)

    def on_key_press(self, key, modifiers):
        self.keys.add(key)

    def on_key_release(self, key, modifiers):
        self.keys.discard(key)

    def spawn_piece(self) -> Piece:
        tetromino = random.choice(Tetromino.get_all())
        x = self.board.width // 2
        y = self.board.height - (len(tetromino.shape) - tetromino.get_origin(Direction.UP).y)
        new_piece = Piece(tetromino, Position(x, y))
        if new_piece.is_colliding(self.board):
            self.game_over = True
        return new_piece

    def clear_rows(self):
        if len(self.board.get_clearable_rows()) != 0:
            self.score += self.score_rewards[len(self.board.get_clearable_rows())]
        for row in sorted(self.board.get_clearable_rows(), reverse=True):
            self.board.clear_row(row)
            self.lines += 1
        thresholds_crossed = self.score // self.fall_increase_threshold
        new_fall_interval = 1 - (thresholds_crossed * self.fall_increase_rate)
        self.fall_interval = max(new_fall_interval, self.min_fall_interval)
        self.update_caption()

    def update_ghost_piece(self):
        self.ghost_piece.rotation = self.falling_piece.rotation
        self.ghost_piece.position = self.falling_piece.position.copy()
        self.ghost_piece.tetromino = self.falling_piece.tetromino
        self.ghost_piece.drop(self.board, place=False)

    def update_caption(self):
        self.set_caption(f'Simple Tetris - Lines: {self.lines} Score: {self.score}')

if __name__ == "__main__":
    game = Game()
    arcade.run()
