from base64 import urlsafe_b64decode
from random import random

from flask import Flask

try:
    from fastly_compute.wsgi import WsgiHttpIncoming
except ImportError:
    # We're running this using the Flask debug server.
    running_under_compute = False
else:
    running_under_compute = True


app = Flask(__name__)


# Board width and height. We assume a square board for now.
# 45 crashes. Viceroy will pass us no more than 1936 bytes of the board. (Or
# maybe the entire URL gets truncated at 1965b.) If you change this, change the
# f"{i:010000b}" format string below to be the new value squared.
WIDTH = HEIGHT = 100


def decompressed_board(compressed: str) -> str:
    """Decompress the board representation sent from JS, returning a B&W board
    string ("10011011"...).

    :arg compressed: A urlsafe_b64encode()d representation of the bit-packed
        black-and-white board. (We don't need color info in order to compute the
        next board.)

    This saves 83% space. RLE would save about 90% but would depend on the board
    and would be slower to compute.
    """
    if compressed == "none":
        return "none"
    i = int.from_bytes(urlsafe_b64decode(compressed))
    return f"{i:010000b}"


@app.route("/board/<compressed_board>")
def board(compressed_board: str):
    """Return the next frame of the Game Of Life, given the current one. If a ""
    board is given, return a new random board.
    """
    cells = decompressed_board(compressed_board)

    # Random board on start:
    if cells == "none":
        return "".join("1" if random() < 0.1 else "0" for _ in range(HEIGHT * WIDTH))

    # Otherwise, evolve 1 step:
    new_cells = ""
    for i in range(len(cells)):
        new_cells += new_cell_color(cells, i)
    return new_cells


def new_cell_color(cells, cell_index):
    """Compute the new color of a single cell at the given offset."""
    count = sum(
        (cells[neighbor_index] != "0") for neighbor_index in neighbors(cell_index)
    )
    if cells[cell_index] != "0":
        if 2 <= count <= 3:
            return str(count)
        else:
            return "0"
    elif count == 3:
        return "1"
    return "0"


def xy_neighbors(x, y):
    """Return an iterable of the x-y coordinates of all the adjacent cells,
    omitting any that are outside the board bounds."""
    x_can_grow = x + 1 < WIDTH
    y_can_grow = y + 1 < HEIGHT
    x_can_shrink = x >= 1
    y_can_shrink = y >= 1
    if x_can_grow:
        yield x + 1, y
    if x_can_shrink:
        yield x - 1, y
    if y_can_grow:
        yield x, y + 1
    if y_can_shrink:
        yield x, y - 1
    if x_can_grow and y_can_grow:
        yield x + 1, y + 1
    if x_can_grow and y_can_shrink:
        yield x + 1, y - 1
    if x_can_shrink and y_can_grow:
        yield x - 1, y + 1
    if x_can_shrink and y_can_shrink:
        yield x - 1, y - 1


def neighbors(cell_index):
    """Return an iterable of the indices of all the adjacent cells, omitting any
    that are outside the board bounds."""
    y, x = divmod(cell_index, WIDTH)
    for neighbor_x, neighbor_y in xy_neighbors(x, y):
        yield neighbor_y * WIDTH + neighbor_x


@app.route("/")
def root():
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width,
                                   initial-scale=1.0">
    <title>Conway's Game of Life</title>
</head>
<body>
    <svg style="width: 100%%" viewBox="0 0 %(viewbox_width)s %(viewbox_width)s" id="grid" xmlns="http://www.w3.org/2000/svg">
    </svg>
    <p style="color: gray; font-weight: bold; font-family: sans-serif; text-align: right;"><span id="fps">…</span> <span style="font-size: 75%%">FPS</span></p>
    <script defer>
        const colors = {"0": "white",
                        "1": "#E44DA2",
                        "2": "#86E9C9",
                        "3": "#A577DF"};
        let board = "none";
        const max = %(width)s;
        let recent_boards = ["", "", "", "", "", "", ""];
        let boredom_counter = 0;
        let fps = 0;

        // Draw a square grid of circles, and return a 2D array of them.
        function initGrid() {
            let svg = document.getElementById("grid");
            let grid = [];
            for (let y = 0; y < max; y++) {
                row = [];
                grid.push(row);
                for (let x = 0; x < max; x++) {
                    let circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
                    circle.setAttribute("cx", 5 + x * 10);
                    circle.setAttribute("cy", 5 + y * 10);
                    circle.setAttribute("r", 4.5);
                    circle.setAttribute("fill", "white");
                    svg.appendChild(circle);
                    row.push(circle);
                }
            }
            return grid;
        }

        // Compress the board, shucking off color info and interpreting the
        // remaining 1s and 0s as binary digits. Interpret as an int, and
        // encode using URL-safe base64.
        function compressedBoard(board) {
            if (board == "none") {
                return "none";
            }

            // Collapse to black-and-white:
            let binary = board.replace(/2|3/g, "1");

            // Pad to multiple of 8 bits if necessary:
            binary = binary.padStart(Math.ceil(binary.length / 8) * 8, "0");

            // Convert binary string to bytes:
            const bytes = [];
            for (let i = 0; i < binary.length; i += 8) {
                const byte = binary.slice(i, i + 8);
                bytes.push(parseInt(byte, 2));
            }

            // Convert bytes to URL-safe base64:
            let ret = "";
            const base64Chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_";

            for (let i = 0; i < bytes.length; i += 3) {
                // Get next 3 bytes:
                const byte1 = bytes[i] || 0;
                const byte2 = bytes[i + 1] || 0;
                const byte3 = bytes[i + 2] || 0;

                // Pack them into a 24-bit number:
                const combined = (byte1 << 16) | (byte2 << 8) | byte3;

                // Pull out four 6-bit values:
                const char1 = base64Chars[(combined >> 18) & 0x3F];
                const char2 = base64Chars[(combined >> 12) & 0x3F];
                const char3 = i + 1 < bytes.length ? base64Chars[(combined >> 6) & 0x3F] : "=";
                const char4 = i + 2 < bytes.length ? base64Chars[combined & 0x3F] : "=";

                ret += char1 + char2 + char3 + char4;
            }
            return ret;
        }

        async function updateGrid(grid) {
            // Fetch new grid:
            // These days, max querystring URL length is 65K in Firefox. Only Edge is shorter, at 2083.
            board = await (await fetch("./board/" + compressedBoard(board))).text();

            // Draw it:
            let i = 0;
            for (let y = 0; y < max; y++) {
                for (let x = 0; x < max; x++) {
                    grid[y][x].setAttribute("fill", colors[board[i++]]);
                }
            }

            fps += 1;
        }

        // If we've seen this board configuration a bunch of times recently,
        // clear the board and start with a fresh one.
        function assuageBoredom() {
            for (recent_board of recent_boards) {
                if (board == recent_board) {
                    boredom_counter += 1;
                    break;
                }
            }
            recent_boards.shift();
            recent_boards.push(board);
            if (boredom_counter >= 10) {
                board = "none";
                // Has to be at least 7 long to detect the union of 3-tick and
                // 2-tick oscillators going at it:
                recent_boards = ["", "", "", "", "", "", ""];
                boredom_counter = 0;
            }
        }

        // Main loop
        async function startAnimation(grid) {
            await updateGrid(grid);
            assuageBoredom();
            animationId = requestAnimationFrame(function() { startAnimation(grid) });
        }

        function startFpsCounter() {
            el = document.getElementById("fps");
            const secs = 3;
            function updateFpsReadout () {
                el.textContent = Math.round(fps / secs);
                fps = 0;
                setTimeout(updateFpsReadout, secs * 1000);
            }
            setTimeout(updateFpsReadout, secs * 1000);
        }

        function main() {
            let grid = initGrid();
            startAnimation(grid);
            startFpsCounter();
        }

        main();
    </script>
</body>
</html>
""" % {"width": WIDTH, "viewbox_width": 10 + WIDTH * 10}


if running_under_compute:
    HttpIncoming = WsgiHttpIncoming(app)
