# Calc ES for Linux

Calc ES is a scientific calculator and mathematics workbench with a native GTK desktop app and a browser-based calculator.

## Try it online

Use the [Calc ES web calculator](https://tofemiodus.github.io/Calc-ES/). It runs in your browser without an account or installation.

## Download

Download the latest Linux source bundle from [GitHub Releases](https://github.com/tofemiodus/Calc-ES/releases/latest). It contains the GTK desktop app, browser app, Linux installer, tests, and license.

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

The desktop app supports multiple resizable windows. Each window has a scientific calculator, linear/quadratic and simultaneous equation solvers, polynomial roots and factorization, function graphing, fraction conversion, and matrix operations.

## Browser app

The browser app is implemented in `index.html`, `toto.css`, and `toto.js`. To run it locally, open `index.html` in a modern browser.

## Tests

Run the equation-solver and GTK interface regression tests with:

```sh
python3 -m unittest discover -s tests -v
```

GTK interface tests require GTK 3 and an available display.

## License and project name

The current source is offered under the [Calc ES Source Available License](LICENSE): private non-commercial use and modification are permitted; public redistribution of modified copies and commercial use require separate written permission. Earlier versions released under AGPL-3.0 remain governed by that license for recipients who already received them.

“Calc ES” and the logo are claimed as marks of `tofemiodus`; see [TRADEMARKS.md](TRADEMARKS.md). A repository notice does not itself register a trademark. This custom license is not the standard Business Source License; seek legal advice about licensing and trademark registration.
