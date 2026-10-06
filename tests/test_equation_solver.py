import unittest

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

from toto import (
    CalcWindow,
    matrix_determinant,
    matrix_inverse,
    matrix_operation,
    solve_equation,
)


class MatrixCalculatorTests(unittest.TestCase):
    def test_scaled_pivoting_preserves_small_invertible_matrices(self):
        matrix = [[1e-13, 0.0], [0.0, 1e-13]]

        self.assertEqual(matrix_determinant(matrix), 1e-26)
        self.assertEqual(matrix_inverse(matrix), [[1e13, 0.0], [0.0, 1e13]])

    def test_scaled_pivoting_still_detects_singular_matrices(self):
        matrix = [[0.1, 0.2], [0.3, 0.6]]

        self.assertEqual(matrix_determinant(matrix), 0.0)
        with self.assertRaisesRegex(ValueError, "singular"):
            matrix_inverse(matrix)

    def test_matrix_operations_keep_expected_results(self):
        matrix_a = [[1.0, 2.0], [3.0, 4.0]]
        matrix_b = [[5.0, 6.0], [7.0, 8.0]]
        cases = (
            ("Determinant of A", "det(A) = -2"),
            ("Inverse of A", "[ -2    1 ]\n[ 1.5    -0.5 ]"),
            ("Transpose of A", "[ 1    3 ]\n[ 2    4 ]"),
            ("A + B", "[ 6    8 ]\n[ 10    12 ]"),
            ("A − B", "[ -4    -4 ]\n[ -4    -4 ]"),
            ("A × B", "[ 19    22 ]\n[ 43    50 ]"),
        )
        for operation, expected in cases:
            with self.subTest(operation=operation):
                self.assertEqual(matrix_operation(operation, matrix_a, matrix_b), expected)


class SimultaneousEquationSolverTests(unittest.TestCase):
    def test_unique_systems_with_different_numbers_of_variables(self):
        cases = (
            ("2x + y = 5\nx - y = 1", "x = 2, y = 1"),
            (
                "x + y + z = 6\nx - y = 0\nz = 2",
                "x = 2, y = 2, z = 2",
            ),
            (
                "alpha + beta = 7\nalpha - beta = 1",
                "alpha = 4, beta = 3",
            ),
            (
                "x = 2\ny = 3\nz = 4\nx + y + z = 9",
                "x = 2, y = 3, z = 4",
            ),
            (
                "a + b + c + d + f = 15\na - b = 0\nb - c = 0\n"
                "c - d = 0\nd - f = 0\na = 3",
                "a = 3, b = 3, c = 3, d = 3, f = 3",
            ),
        )
        for source, expected in cases:
            with self.subTest(source=source):
                self.assertEqual(
                    solve_equation(source, "Simultaneous", True),
                    expected,
                )

    def test_small_coefficients_are_not_discarded(self):
        self.assertEqual(
            solve_equation("1e-13x = 1e-13\n2y = 4", "Simultaneous", True),
            "x = 1, y = 2",
        )
        self.assertEqual(
            solve_equation("1e-20x + y = 3\ny = 2", "Simultaneous", True),
            "x = 1e+20, y = 2",
        )

    def test_dependent_and_inconsistent_systems(self):
        self.assertEqual(
            solve_equation("x + y = 3\n2x + 2y = 6", "Simultaneous", True),
            "These equations have infinitely many solutions.",
        )
        self.assertEqual(
            solve_equation("x + y = 3\n2x + 2y = 7", "Simultaneous", True),
            "These equations have no solution.",
        )

    def test_rejects_nonlinear_and_incomplete_systems(self):
        for source in (
            "x^2 + y = 3\nx - y = 1",
            "x*y = 3\nx - y = 1",
        ):
            with self.subTest(source=source):
                with self.assertRaisesRegex(ValueError, "linear"):
                    solve_equation(source, "Simultaneous", True)
        with self.assertRaisesRegex(ValueError, "at least two"):
            solve_equation("x = 1", "Simultaneous", True)
        with self.assertRaisesRegex(ValueError, "Complete every equation"):
            solve_equation("x = 1\n\ny = 2", "Simultaneous", True)

    def test_existing_single_equation_modes(self):
        self.assertEqual(solve_equation("2t + 3 = 7", "Linear", True), "t = 2")
        self.assertEqual(
            solve_equation("t^2 - 5t + 6 = 0", "Quadratic", True),
            "t = 2 or t = 3",
        )


class SimultaneousEquationWindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        initialized, _ = Gtk.init_check([])
        if not initialized:
            raise unittest.SkipTest("GTK display is unavailable")

    def setUp(self):
        self.window = CalcWindow()
        self.window.show_all()

    def tearDown(self):
        self.window.destroy()

    def test_add_remove_solve_and_mode_switch(self):
        self.assertFalse(self.window.equation_rows[1][0].get_visible())
        self.assertFalse(self.window.equation_add_button.get_visible())
        self.window.equation_kind.set_active(2)
        self.assertEqual(len(self.window.equation_rows), 2)
        self.assertEqual(
            [label.get_text() for _, label, _, _ in self.window.equation_rows],
            ["Equation 1", "Equation 2"],
        )
        self.assertTrue(
            all(entry.get_visible() and entry.get_can_focus()
                for _, _, entry, _ in self.window.equation_rows)
        )

        self.window.on_add_equation()
        self.assertEqual(len(self.window.equation_rows), 3)
        self.window.equation_rows[0][2].set_text("x + y + z = 6")
        self.window.equation_rows[1][2].set_text("x - y = 0")
        self.window.equation_rows[2][2].set_text("z = 2")
        self.window.on_solve_equation()
        self.assertEqual(self.window.equation_result.get_text(), "x = 2, y = 2, z = 2")

        self.window.equation_rows[-1][3].emit("clicked")
        self.assertEqual(len(self.window.equation_rows), 2)
        self.assertEqual(
            [label.get_text() for _, label, _, _ in self.window.equation_rows],
            ["Equation 1", "Equation 2"],
        )

        self.window.equation_kind.set_active(0)
        self.assertFalse(self.window.equation_rows[1][0].get_visible())
        self.window.equation_kind.set_active(2)
        self.assertTrue(self.window.equation_rows[1][2].get_visible())

    def test_all_simultaneous_rows_must_be_filled(self):
        self.window.equation_kind.set_active(2)
        self.window.equation_rows[0][2].set_text("x + y = 3")
        self.window.on_add_equation()
        self.window.equation_rows[1][2].set_text("x - y = 1")
        self.window.on_solve_equation()
        self.assertEqual(
            self.window.equation_result.get_text(),
            "Complete every equation before solving.",
        )

    def test_calculator_fraction_and_matrix_text_are_black(self):
        for widget in (
            self.window.calc_result,
            self.window.fraction_result,
            self.window.matrix_result,
            self.window.fraction_entry,
            self.window.matrix_entries["A"][0][0],
            self.window.equation_add_button,
        ):
            with self.subTest(widget=widget):
                color = widget.get_style_context().get_color(Gtk.StateFlags.NORMAL)
                self.assertEqual((color.red, color.green, color.blue), (0.0, 0.0, 0.0))

    def test_multiple_windows_are_independently_resizable(self):
        other_windows = [CalcWindow(), CalcWindow()]
        try:
            sizes = ((760, 560), (820, 600))
            for window, size in zip(other_windows, sizes):
                window.set_default_size(*size)
                window.show_all()
            self.assertTrue(self.window.get_resizable())
            self.assertTrue(all(window.get_resizable() for window in other_windows))
            self.assertEqual(
                [window.get_default_size() for window in other_windows],
                [sizes[0], sizes[1]],
            )
            self.assertTrue(all(
                window.stack.get_child_by_name("calculator").get_policy()
                == (Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
                for window in other_windows
            ))
            minimum, _ = other_windows[0].get_preferred_size()
            self.assertLessEqual(minimum.width, 400)
        finally:
            for window in other_windows:
                window.destroy()


if __name__ == "__main__":
    unittest.main()
