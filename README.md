# Calc ES

Calc ES is a scientific calculator and mathematics workbench with a native
GTK desktop app and a browser-based calculator.

## Try it online

Use the [Calc ES web calculator](https://tofemiodus.github.io/Calc-ES/).
It runs in your browser without an account or installation.

## Download

Download the latest source bundle from
[GitHub Releases](https://github.com/tofemiodus/Calc-ES/releases/latest).
The bundle includes the native app, browser app, installer, tests, and license.

## Native Linux desktop app

Requirements on Debian-based Linux distributions:

```sh
sudo apt install python3-gi gir1.2-gtk-3.0
```

Install Calc ES in the current user's application menu:

```sh
sh install-linux-mint.sh
```

Alternatively, run it directly from the project directory:

```sh
python3 toto.py
```

The desktop app supports multiple resizable windows. Each window has a
scientific calculator, linear/quadratic and simultaneous equation solvers,
polynomial roots and factorization, function graphing, fraction conversion,
and matrix operations.

## Browser app

The browser app is implemented in `index.html`, `toto.css`, and `toto.js`.
To run it locally, open `index.html` in a modern browser.

## Tests

Run the equation-solver and GTK interface regression tests with:

```sh
python3 -m unittest discover -s tests -v
```

GTK interface tests require GTK 3 and an available display.

## License

Calc ES is distributed under the GNU Affero General Public License v3.0. See
[`LICENSE`](LICENSE).
