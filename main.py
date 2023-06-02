import asyncio
import curses
import itertools
import random
import textwrap
import time

from helpers import read_controls, draw_frame, get_frame_size
from physics import update_speed

COROUTINES = []
TIC_TIMEOUT = 0.1
STARS_DENSITY = 0.02
FRAME_BORDER = 1
SPACE_GARBAGE_FILE_PATH = 'space_garbage.txt'
GARBAGE_APPEARING_DELAY = 15
SPACE_SHIP_ROW_SPEED = 0
SPACE_SHIP_COLUMN_SPEED = 0
SPACE_SHIP_FRAMES = [
    """
      .
     .'.
     |o|
    .'o'.
    |.-.|
    '   '
     ( )
      )
     ( )
     """,
    """
      .
     .'.
     |o|
    .'o'.
    |.-.|
    '   '
      )
     ( )
      (
      """
]


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
        max(FRAME_BORDER, space_ship_row + SPACE_SHIP_ROW_SPEED),
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
    global COROUTINES
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
        if space_pressed:
            _, columns = get_frame_size(space_ship_frames[0])

            COROUTINES.append(
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


async def fill_orbit_with_garbage(canvas, garbage_frames, garbage_appearing_delay):
    global COROUTINES
    _, windows_columns = canvas.getmaxyx()
    while True:
        garbage_frame = random.choice(garbage_frames)
        _, frame_columns = get_frame_size(garbage_frame)
        column = random.randint(FRAME_BORDER, windows_columns - frame_columns - FRAME_BORDER)
        COROUTINES.append(fly_garbage(canvas, column, garbage_frame))
        await sleep(garbage_appearing_delay)


async def fly_garbage(canvas, column, garbage_frame, speed=0.5):
    """Animate garbage, flying from top to bottom. Сolumn position will stay same, as specified on start."""
    rows_number, columns_number = canvas.getmaxyx()

    column = min(
        max(column, 0),
        columns_number - 1
    )

    row = FRAME_BORDER

    while row < rows_number:
        draw_frame(canvas, row, column, garbage_frame)
        await asyncio.sleep(0)
        draw_frame(canvas, row, column, garbage_frame, negative=True)
        row += speed


async def fire(canvas, start_row, start_column, rows_speed=-0.3, columns_speed=0):
    """Display animation of gun shot, direction and speed can be specified."""

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
    global COROUTINES
    window_rows, window_columns = canvas.getmaxyx()

    star_sprites = "+*·˖•"
    stars_quantity = int(window_rows * window_columns * STARS_DENSITY)
    stars = [
        blink(
            canvas=canvas,
            row=random.randint(FRAME_BORDER * 2, window_rows - FRAME_BORDER * 2),
            column=random.randint(FRAME_BORDER * 2, window_columns - FRAME_BORDER * 2),
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

    with open(SPACE_GARBAGE_FILE_PATH) as file:
        space_garbage_frames = file.read().split('\n\n')
    garbage_animation = fill_orbit_with_garbage(
        canvas,
        space_garbage_frames,
        GARBAGE_APPEARING_DELAY
    )

    COROUTINES = stars + [space_ship_animation, garbage_animation]
    canvas.nodelay(True)
    curses.curs_set(False)
    while True:
        for coroutine in COROUTINES.copy():
            try:
                coroutine.send(None)
            except StopIteration:
                COROUTINES.remove(coroutine)
        canvas.refresh()
        time.sleep(TIC_TIMEOUT)


if __name__ == '__main__':
    curses.update_lines_cols()
    curses.wrapper(draw)
