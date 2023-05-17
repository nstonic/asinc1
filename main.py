import asyncio
import curses
import itertools
import random
import textwrap
import time

from helpers import read_controls, draw_frame, get_frame_size

TIC_TIMEOUT = 0.1
STARS_DENSITY = 50
FRAME_BORDER = 1
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


def get_new_space_ship_position(
        canvas,
        frame,
        space_ship_row,
        space_ship_column,
        controls
):
    rows_direction, columns_direction, _ = controls
    window_rows, window_columns = canvas.getmaxyx()
    frame_rows, frame_columns = get_frame_size(frame)

    space_ship_row = min(
        max(FRAME_BORDER, space_ship_row + rows_direction),
        window_rows - frame_rows - FRAME_BORDER
    )
    space_ship_column = min(
        max(FRAME_BORDER, space_ship_column + columns_direction),
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
    for frame in itertools.cycle(space_ship_frames):
        controls = read_controls(canvas)
        space_ship_row, space_ship_column = get_new_space_ship_position(
            canvas,
            frame,
            space_ship_row,
            space_ship_column,
            controls
        )
        draw_frame(canvas, space_ship_row, space_ship_column, frame)
        await asyncio.sleep(0)
        draw_frame(canvas, space_ship_row, space_ship_column, frame, negative=True)


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
            frame_num += 1
            frame_num = frame_num % len(frames)
        await asyncio.sleep(0)


def draw(canvas):
    window_rows, window_columns = canvas.getmaxyx()
    space_ship_frames, space_ship_start_row, space_ship_start_column = prepare_space_ship(
        window_rows,
        window_columns,
        SPACE_SHIP_FRAMES
    )

    star_sprites = "+*·'˖•▪◦▫"
    stars_quantity = window_rows * window_columns // STARS_DENSITY
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
    space_ship_animation = animate_spaceship(
        canvas,
        space_ship_start_row,
        space_ship_start_column,
        space_ship_frames
    )
    coroutines = stars + [space_ship_animation]
    canvas.border()
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
