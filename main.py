import asyncio
import curses
import itertools
import random
import textwrap
import time

from frames import SPACE_SHIP_FRAMES, EXPLOSION_FRAMES, SPACE_GARBAGE_FRAMES, GAME_OVER_FRAME, PHRASES
from helpers import read_controls, draw_frame, get_frame_size, get_garbage_delay_tics
from obstacles import Obstacle
from physics import update_speed

coroutines = []
obstacles = []
TIC_TIMEOUT = 0.1
STARS_DENSITY = 0.02
TOP_FRAME_BORDER = 3
FRAME_BORDER = 1
SPACE_SHIP_ROW_SPEED = 0
SPACE_SHIP_COLUMN_SPEED = 0
YEAR = 1957
POINTS = 0
PLASMA_GUN_CREATED_AT = 2020


async def explode(canvas, center_row, center_column):
    rows, columns = get_frame_size(EXPLOSION_FRAMES[0])
    corner_row = center_row - rows / 2
    corner_column = center_column - columns / 2

    curses.beep()
    for frame in EXPLOSION_FRAMES:
        draw_frame(canvas, corner_row, corner_column, frame)

        await asyncio.sleep(0)
        draw_frame(canvas, corner_row, corner_column, frame, negative=True)
        await asyncio.sleep(0)


async def sleep(tics=1):
    for _ in range(tics):
        await asyncio.sleep(0)


def get_space_ship_position(
        canvas,
        frame,
        space_ship_row,
        space_ship_column,
        rows_direction,
        columns_direction
):
    global SPACE_SHIP_ROW_SPEED
    global SPACE_SHIP_COLUMN_SPEED

    window_rows, window_columns = canvas.getmaxyx()
    frame_rows, frame_columns = get_frame_size(frame)
    SPACE_SHIP_ROW_SPEED, SPACE_SHIP_COLUMN_SPEED = update_speed(
        SPACE_SHIP_ROW_SPEED,
        SPACE_SHIP_COLUMN_SPEED,
        rows_direction,
        columns_direction,
        row_speed_limit=2,
        column_speed_limit=4
    )
    space_ship_row = min(
        max(TOP_FRAME_BORDER, space_ship_row + SPACE_SHIP_ROW_SPEED),
        window_rows - frame_rows - FRAME_BORDER
    )
    space_ship_column = min(
        max(FRAME_BORDER, space_ship_column + SPACE_SHIP_COLUMN_SPEED),
        window_columns - frame_columns - FRAME_BORDER
    )

    return space_ship_row, space_ship_column


def prepare_space_ship(window_rows, window_columns, space_ship_frames):
    space_ship_frames = [
        textwrap.dedent(frame.strip('\n'))
        for frame in
        space_ship_frames
    ]
    space_ship_frames = sum(zip(space_ship_frames, space_ship_frames), ())
    for frame in space_ship_frames:
        frame_rows, frame_columns = get_frame_size(frame)
        if frame_rows >= window_rows or frame_columns >= window_columns:
            raise ValueError('The window is too small')
    space_ship_start_row = window_rows
    space_ship_start_column = window_columns // 2
    return space_ship_frames, space_ship_start_row, space_ship_start_column


async def animate_spaceship(canvas, space_ship_row, space_ship_column, space_ship_frames):
    global coroutines
    for frame in itertools.cycle(space_ship_frames):
        rows_direction, columns_direction, space_pressed = read_controls(canvas)
        space_ship_row, space_ship_column = get_space_ship_position(
            canvas,
            frame,
            space_ship_row,
            space_ship_column,
            rows_direction,
            columns_direction
        )
        frame_rows, frame_columns = get_frame_size(frame)
        for obstacle in obstacles:
            if obstacle.has_collision(
                    obj_corner_row=space_ship_row,
                    obj_corner_column=space_ship_column,
                    obj_size_rows=frame_rows,
                    obj_size_columns=frame_columns,
            ):
                coroutines.append(
                    show_game_over(canvas)
                )
                return
        if space_pressed and YEAR >= PLASMA_GUN_CREATED_AT:
            _, columns = get_frame_size(space_ship_frames[0])
            coroutines.append(
                fire(
                    canvas,
                    space_ship_row,
                    space_ship_column + columns // 2,
                    rows_speed=-2
                )
            )
        draw_frame(canvas, space_ship_row, space_ship_column, frame)
        await asyncio.sleep(0)
        draw_frame(canvas, space_ship_row, space_ship_column, frame, negative=True)


async def fill_orbit_with_garbage(canvas, garbage_frames):
    global coroutines
    global YEAR
    _, windows_columns = canvas.getmaxyx()
    while True:
        garbage_appearing_delay = get_garbage_delay_tics(YEAR)
        if not garbage_appearing_delay:
            await asyncio.sleep(0)
        else:
            garbage_frame = random.choice(garbage_frames)
            _, frame_columns = get_frame_size(garbage_frame)
            column = random.randint(
                TOP_FRAME_BORDER,
                windows_columns - frame_columns - FRAME_BORDER
            )
            coroutines.append(
                fly_garbage(
                    canvas,
                    column,
                    garbage_frame,
                    speed=random.uniform(0.2, 0.7)
                )
            )
            await sleep(garbage_appearing_delay)


async def fly_garbage(canvas, column, garbage_frame, speed=0.5):
    """Animate garbage, flying from top to bottom. Сolumn position will stay same, as specified on start."""
    global obstacles
    global coroutines

    rows_number, columns_number = canvas.getmaxyx()
    garbage_rows, garbage_columns = get_frame_size(garbage_frame)
    column = min(
        max(column, 0),
        columns_number - FRAME_BORDER
    )
    row = -garbage_rows

    obstacle = Obstacle(
        row,
        column,
        rows_size=garbage_rows - 3,
        columns_size=garbage_columns - 1
    )
    obstacles.append(obstacle)
    while row < rows_number:
        if obstacle.destroyed:
            obstacles.remove(obstacle)
            return
        draw_frame(canvas, row, column, garbage_frame)
        await asyncio.sleep(0)
        draw_frame(canvas, row, column, garbage_frame, negative=True)
        row += speed
        obstacle.row = row + 3
    obstacles.remove(obstacle)


async def show_game_over(canvas):
    window_rows, window_columns = canvas.getmaxyx()
    frame_rows, frame_columns = get_frame_size(GAME_OVER_FRAME)
    while True:
        draw_frame(
            canvas,
            (window_rows - frame_rows) // 2,
            (window_columns - frame_columns) // 2,
            GAME_OVER_FRAME
        )
        await asyncio.sleep(0)


async def count_years(canvas):
    global YEAR
    while True:
        canvas.addstr(1, 2, str(YEAR))
        await sleep(15)
        YEAR += 1


async def count_points(canvas):
    global POINTS
    _, window_columns = canvas.getmaxyx()
    while True:
        canvas.addstr(1, window_columns - 5, f'${POINTS}')
        await asyncio.sleep(0)


async def show_events(canvas):
    _, window_columns = canvas.getmaxyx()
    while True:
        if current_phrase := PHRASES.get(YEAR):
            _, phrase_columns = get_frame_size(current_phrase)
            column = (window_columns - phrase_columns) // 2
            canvas.addstr(1, 8, ' ' * (window_columns - 15))
            canvas.addstr(1, column, current_phrase)
        await asyncio.sleep(0)


async def fire(canvas, start_row, start_column, rows_speed=-0.3, columns_speed=0):
    """Display animation of gun shot, direction and speed can be specified."""
    global obstacles
    global POINTS
    global YEAR

    row, column = start_row, start_column

    canvas.addstr(round(row), round(column), '*')
    await asyncio.sleep(0)

    canvas.addstr(round(row), round(column), 'O')
    await asyncio.sleep(0)
    canvas.addstr(round(row), round(column), ' ')

    row += rows_speed
    column += columns_speed

    symbol = '-' if columns_speed else '|'

    rows, columns = canvas.getmaxyx()
    max_row, max_column = rows - 1, columns - 1

    curses.beep()

    while 0 < row < max_row and 0 < column < max_column:
        for obstacle in obstacles:
            if obstacle.has_collision(
                    obj_corner_row=row,
                    obj_corner_column=column
            ):
                obstacle.destroyed = True
                POINTS += 1
                coroutines.append(explode(canvas, row, column))
                return

        canvas.addstr(round(row), round(column), symbol)
        await asyncio.sleep(0)
        canvas.addstr(round(row), round(column), ' ')
        row += rows_speed
        column += columns_speed


async def blink(canvas, row, column, symbol='*', offset_tics=0):
    frames = [
        {'style': curses.A_DIM, 'delay': 20},
        {'style': curses.A_NORMAL, 'delay': 3},
        {'style': curses.A_BOLD, 'delay': 5},
        {'style': curses.A_NORMAL, 'delay': 3}
    ]
    tics = 0
    frame_num = 0
    while True:
        canvas.addstr(row, column, symbol, frames[frame_num]['style'])
        tics += 1
        delay = offset_tics + frames[frame_num]['delay']
        if tics >= delay:
            tics = 0
            frame_num = (frame_num + 1) % len(frames)
        await asyncio.sleep(0)


def draw(canvas):
    global coroutines

    window_rows, window_columns = canvas.getmaxyx()

    star_sprites = "+*·˖•"
    stars_quantity = int(window_rows * window_columns * STARS_DENSITY)
    stars = [
        blink(
            canvas=canvas,
            row=random.randint(TOP_FRAME_BORDER, window_rows - FRAME_BORDER),
            column=random.randint(FRAME_BORDER, window_columns - FRAME_BORDER),
            symbol=random.choice(star_sprites),
            offset_tics=random.randint(0, 5)
        )
        for _ in range(stars_quantity)
    ]

    space_ship_frames, space_ship_start_row, space_ship_start_column = prepare_space_ship(
        window_rows,
        window_columns,
        SPACE_SHIP_FRAMES
    )
    space_ship_animation = animate_spaceship(
        canvas,
        space_ship_start_row,
        space_ship_start_column,
        space_ship_frames
    )

    garbage_animation = fill_orbit_with_garbage(
        canvas,
        SPACE_GARBAGE_FRAMES
    )

    coroutines = stars + [
        space_ship_animation,
        garbage_animation,
        count_years(canvas),
        count_points(canvas),
        show_events(canvas)
    ]

    canvas.nodelay(True)
    curses.curs_set(False)
    while True:
        for coroutine in coroutines.copy():
            try:
                coroutine.send(None)
            except StopIteration:
                coroutines.remove(coroutine)
        canvas.refresh()
        time.sleep(TIC_TIMEOUT)


if __name__ == '__main__':
    curses.update_lines_cols()
    curses.wrapper(draw)
