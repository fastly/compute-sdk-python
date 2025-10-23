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
# maybe the entire URL gets truncated at 1965b.)
WIDTH = HEIGHT = 44


@app.route("/board/<cells>")
def board(cells):
    """Return the next frame of the Game Of Life, given the current one. If a ""
    board is given, return a new random board."""
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
    <script defer>
        const colors = {"0": "white",
                        "1": "#E44DA2",
                        "2": "#86E9C9",
                        "3": "#A577DF"};
        let board = "empty";
        const max = %(width)s;
        let recent_boards = ["", "", "", "", "", "", ""];
        let boredom_counter = 0;

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

        async function updateGrid(grid) {
            // Fetch new grid:
            // These days, max querystring URL length is 65K in Firefox. Only Edge is shorter, at 2083.
            board = await (await fetch("./board/" + board)).text();

            // Draw it:
            let i = 0;
            for (let y = 0; y < max; y++) {
                for (let x = 0; x < max; x++) {
                    grid[y][x].setAttribute("fill", colors[board[i++]]);
                }
            }
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
                board = "empty";
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

        function main() {
            let grid = initGrid();
            startAnimation(grid);
        }

        main();
    </script>
</body>
</html>
""" % {"width": WIDTH, "viewbox_width": 10 + WIDTH * 10}


if running_under_compute:
    HttpIncoming = WsgiHttpIncoming(app)
