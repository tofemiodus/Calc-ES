#!/usr/bin/python3
"""Native GTK desktop calculator and mathematics workbench."""

from __future__ import annotations

import math
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path

import gi

gi.require_version("Gdk", "3.0")
gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, Gtk


ACCENT = "#9f8cff"
FUNCTIONS = {
    "sin", "cos", "tan", "asin", "acos", "atan",
    "sqrt", "log", "ln", "abs",
}
TOKEN_PATTERN = re.compile(
    r"\s+|(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?|[a-zA-Z]+|[()=+\-*/^%!\u00d7\u00f7\u2212]"
)


def format_number(value: float) -> str:
    if not math.isfinite(value):
        raise ValueError("Result is outside the supported range.")
    if value == 0:
        return "0"
    if abs(value) >= 1e12 or abs(value) < 1e-8:
        return f"{value:.8e}".replace(".00000000e", "e").replace(".0e", "e")
    return f"{value:.12g}"


def mixed_fraction_text(numerator: int, denominator: int) -> str:
    if denominator == 0:
        raise ValueError("The denominator cannot be zero.")
    if denominator < 0:
        numerator = -numerator
        denominator = -denominator
    sign = "−" if numerator < 0 else ""
    whole, remainder = divmod(abs(numerator), denominator)
    if remainder == 0:
        return f"{sign}{whole}"
    if whole == 0:
        return f"{sign}{remainder}/{denominator}"
    return f"{sign}{whole} {remainder}/{denominator}"


def tokenize(source: str) -> list[tuple[str, str]]:
    source = source.replace("×", "*").replace("÷", "/").replace("−", "-")
    tokens: list[tuple[str, str]] = []
    position = 0
    while position < len(source):
        match = TOKEN_PATTERN.match(source, position)
        if not match:
            raise ValueError(f"Unsupported character: {source[position]}")
        token = match.group()
        position = match.end()
        if token.isspace():
            continue
        if token[0].isdigit() or token[0] == ".":
            tokens.append(("number", token))
        elif token[0].isalpha():
            tokens.append(("identifier", token.lower()))
        else:
            tokens.append(("symbol", token))
    return tokens


class ExpressionParser:
    """Parse calculator expressions as numbers or low-degree polynomials."""

    def __init__(
        self,
        source: str,
        variables: tuple[str, ...] = (),
        degree_limit: int = 0,
        degrees: bool = True,
    ) -> None:
        self.tokens = tokenize(source)
        self.position = 0
        self.variables = variables
        self.degree_limit = degree_limit
        self.degrees = degrees
        if not self.tokens:
            raise ValueError("Enter an expression.")

    def peek(self) -> tuple[str, str] | None:
        return self.tokens[self.position] if self.position < len(self.tokens) else None

    def accept(self, value: str) -> bool:
        token = self.peek()
        if token and token[1] == value:
            self.position += 1
            return True
        return False

    def parse(self) -> float | dict[tuple[int, int], float]:
        result = self.parse_expression()
        if self.position != len(self.tokens):
            raise ValueError("Check the expression format.")
        return result

    def constant(self, value: float) -> float | dict[tuple[int, int], float]:
        if not self.variables:
            return value
        return {(0, 0): value}

    def variable(self, name: str) -> dict[tuple[int, int], float]:
        if name not in self.variables:
            raise ValueError(f"Use {' and '.join(self.variables)} as the variable(s).")
        index = self.variables.index(name)
        return {(1, 0) if index == 0 else (0, 1): 1.0}

    def add_values(self, left, right, sign: float = 1):
        if not self.variables:
            return left + sign * right
        result = dict(left)
        for key, value in right.items():
            updated = result.get(key, 0.0) + sign * value
            if abs(updated) < 1e-12:
                result.pop(key, None)
            else:
                result[key] = updated
        return result

    def multiply_values(self, left, right):
        if not self.variables:
            return left * right
        result: dict[tuple[int, int], float] = {}
        for (lx, ly), lv in left.items():
            for (rx, ry), rv in right.items():
                if lx + ly + rx + ry > self.degree_limit:
                    raise ValueError(f"Polynomials are limited to degree {self.degree_limit}.")
                key = (lx + rx, ly + ry)
                result[key] = result.get(key, 0.0) + lv * rv
        return result

    def divide_values(self, numerator, denominator):
        if not self.variables:
            if denominator == 0:
                raise ValueError("Cannot divide by zero.")
            return numerator / denominator
        if len(denominator) != 1 or (0, 0) not in denominator or denominator[(0, 0)] == 0:
            raise ValueError("Polynomial division is only supported by a non-zero number.")
        divisor = denominator[(0, 0)]
        return {key: value / divisor for key, value in numerator.items()}

    def parse_expression(self):
        value = self.parse_term()
        while self.peek() and self.peek()[1] in ("+", "-"):
            operator = self.peek()[1]
            self.position += 1
            value = self.add_values(value, self.parse_term(), 1 if operator == "+" else -1)
        return value

    def starts_term(self) -> bool:
        token = self.peek()
        return bool(token and (token[0] in ("number", "identifier") or token[1] == "("))

    def parse_term(self):
        value = self.parse_unary()
        while True:
            token = self.peek()
            if token and token[0] == "identifier" and token[1] in ("npr", "ncr"):
                operation = token[1]
                self.position += 1
                right = self.parse_unary()
                if not float(value).is_integer() or not float(right).is_integer():
                    raise ValueError("nPr and nCr require whole numbers.")
                n, r = int(value), int(right)
                if n < 0 or r < 0 or r > n or n > 170:
                    raise ValueError("Use whole numbers satisfying 0 ≤ r ≤ n ≤ 170.")
                value = float(math.perm(n, r) if operation == "npr" else math.comb(n, r))
            elif self.accept("*"):
                value = self.multiply_values(value, self.parse_unary())
            elif self.accept("/"):
                value = self.divide_values(value, self.parse_unary())
            elif self.starts_term():
                value = self.multiply_values(value, self.parse_unary())
            else:
                return value

    def parse_unary(self):
        if self.accept("+"):
            return self.parse_unary()
        if self.accept("-"):
            value = self.parse_unary()
            if not self.variables:
                return -value
            return {key: -coefficient for key, coefficient in value.items()}
        return self.parse_power()

    def parse_power(self):
        value = self.parse_postfix()
        if not self.accept("^"):
            return value
        exponent = self.parse_unary()
        if self.variables:
            if len(exponent) != 1 or (0, 0) not in exponent:
                raise ValueError(f"Use a whole-number power from 0 to {self.degree_limit}.")
            power = exponent[(0, 0)]
            if not power.is_integer() or not 0 <= power <= self.degree_limit:
                raise ValueError(f"Use a whole-number power from 0 to {self.degree_limit}.")
            result = self.constant(1.0)
            for _ in range(int(power)):
                result = self.multiply_values(result, value)
            return result
        try:
            result = value**exponent
        except (OverflowError, ValueError, ZeroDivisionError) as error:
            raise ValueError("This power is outside the supported range.") from error
        if isinstance(result, complex) or not math.isfinite(result):
            raise ValueError("This power does not have a finite real result.")
        return result

    def parse_postfix(self):
        value = self.parse_primary()
        while True:
            if self.accept("%"):
                if self.variables:
                    value = self.divide_values(value, self.constant(100.0))
                else:
                    value /= 100
            elif self.accept("!"):
                if self.variables or not float(value).is_integer() or not 0 <= value <= 170:
                    raise ValueError("Factorial needs a whole number from 0 to 170.")
                value = math.factorial(int(value))
            else:
                return value

    def parse_primary(self):
        token = self.peek()
        if not token:
            raise ValueError("Complete the expression.")
        self.position += 1
        kind, value = token
        if kind == "number":
            return self.constant(float(value))
        if value == "(":
            result = self.parse_expression()
            if not self.accept(")"):
                raise ValueError("Missing closing parenthesis.")
            return result
        if kind != "identifier":
            raise ValueError("Check the expression.")
        if self.variables and value in self.variables:
            return self.variable(value)
        if value == "pi":
            return self.constant(math.pi)
        if value == "e":
            return self.constant(math.e)
        if self.variables:
            raise ValueError("Polynomials support variables and constants only.")
        if value not in FUNCTIONS:
            raise ValueError(f"Unknown function or variable: {value}")
        if not self.accept("("):
            raise ValueError(f"Add parentheses after {value}.")
        argument = self.parse_expression()
        if not self.accept(")"):
            raise ValueError("Missing closing parenthesis.")
        angle = math.pi / 180 if self.degrees else 1.0
        functions = {
            "sin": lambda x: math.sin(x * angle),
            "cos": lambda x: math.cos(x * angle),
            "tan": lambda x: math.tan(x * angle),
            "asin": lambda x: math.asin(x) / angle,
            "acos": lambda x: math.acos(x) / angle,
            "atan": lambda x: math.atan(x) / angle,
            "sqrt": math.sqrt,
            "log": math.log10,
            "ln": math.log,
            "abs": abs,
        }
        try:
            if value == "tan" and abs(math.cos(argument * angle)) < 1e-14:
                raise ValueError("Tangent is undefined at this angle.")
            if value in ("asin", "acos") and not -1 <= argument <= 1:
                raise ValueError(f"{value} needs a value from −1 to 1.")
            if value in ("sqrt", "log", "ln") and argument < 0:
                raise ValueError(f"{value} needs a non-negative value.")
            if value in ("log", "ln") and argument == 0:
                raise ValueError(f"{value} needs a positive value.")
            return functions[value](argument)
        except (ValueError, OverflowError, ZeroDivisionError) as error:
            if isinstance(error, ValueError) and str(error):
                raise
            raise ValueError(f"{value} is undefined for this input.") from error


def polynomial_variables(source: str) -> tuple[str, ...]:
    names = []
    for kind, value in tokenize(source):
        if kind == "identifier" and value != "pi" and value not in FUNCTIONS and len(value) == 1:
            if value not in names:
                names.append(value)
    return tuple(names)


class LinearExpressionParser:
    """Parse a linear expression into variable coefficients and a constant."""

    def __init__(self, source: str, variables: tuple[str, ...]) -> None:
        self.tokens = tokenize(source)
        self.position = 0
        self.variables = variables
        if not self.tokens:
            raise ValueError("Enter an expression.")

    def peek(self) -> tuple[str, str] | None:
        return self.tokens[self.position] if self.position < len(self.tokens) else None

    def accept(self, value: str) -> bool:
        token = self.peek()
        if token and token[1] == value:
            self.position += 1
            return True
        return False

    def parse(self) -> tuple[dict[str, float], float]:
        result = self.parse_expression()
        if self.position != len(self.tokens):
            raise ValueError("Check the equation format.")
        return result

    @staticmethod
    def add(
        left: tuple[dict[str, float], float],
        right: tuple[dict[str, float], float],
        sign: float = 1.0,
    ) -> tuple[dict[str, float], float]:
        coefficients = dict(left[0])
        for name, value in right[0].items():
            coefficients[name] = coefficients.get(name, 0.0) + sign * value
        constant = left[1] + sign * right[1]
        coefficients = {
            name: value for name, value in coefficients.items() if value != 0
        }
        if not math.isfinite(constant) or any(not math.isfinite(value) for value in coefficients.values()):
            raise ValueError("Equation values are outside the supported range.")
        return coefficients, constant

    @staticmethod
    def scale(
        value: tuple[dict[str, float], float], factor: float
    ) -> tuple[dict[str, float], float]:
        coefficients = {
            name: coefficient * factor
            for name, coefficient in value[0].items()
            if coefficient * factor != 0
        }
        constant = value[1] * factor
        if not math.isfinite(constant) or any(not math.isfinite(item) for item in coefficients.values()):
            raise ValueError("Equation values are outside the supported range.")
        return coefficients, constant

    def parse_expression(self) -> tuple[dict[str, float], float]:
        value = self.parse_term()
        while self.peek() and self.peek()[1] in ("+", "-"):
            sign = 1.0 if self.peek()[1] == "+" else -1.0
            self.position += 1
            value = self.add(value, self.parse_term(), sign)
        return value

    def starts_term(self) -> bool:
        token = self.peek()
        return bool(token and (token[0] in ("number", "identifier") or token[1] == "("))

    def parse_term(self) -> tuple[dict[str, float], float]:
        value = self.parse_unary()
        while True:
            if self.accept("*") or self.starts_term():
                right = self.parse_unary()
                if value[0] and right[0]:
                    raise ValueError("Simultaneous equations must be linear.")
                if right[0]:
                    value = self.scale(right, value[1])
                else:
                    value = self.scale(value, right[1])
            elif self.accept("/"):
                divisor = self.parse_unary()
                if divisor[0] or divisor[1] == 0:
                    raise ValueError("Division is only supported by a non-zero number.")
                value = self.scale(value, 1 / divisor[1])
            else:
                return value

    def parse_unary(self) -> tuple[dict[str, float], float]:
        if self.accept("+"):
            return self.parse_unary()
        if self.accept("-"):
            return self.scale(self.parse_unary(), -1)
        return self.parse_power()

    def parse_power(self) -> tuple[dict[str, float], float]:
        value = self.parse_postfix()
        if not self.accept("^"):
            return value
        exponent = self.parse_unary()
        if exponent[0] or not exponent[1].is_integer():
            raise ValueError("Use a whole-number power in a linear equation.")
        power = int(exponent[1])
        if value[0]:
            if power == 0:
                return {}, 1.0
            if power == 1:
                return value
            raise ValueError("Simultaneous equations must be linear.")
        try:
            result = value[1] ** power
        except (OverflowError, ValueError, ZeroDivisionError) as error:
            raise ValueError("This power is outside the supported range.") from error
        if not math.isfinite(result):
            raise ValueError("This power is outside the supported range.")
        return {}, result

    def parse_postfix(self) -> tuple[dict[str, float], float]:
        value = self.parse_primary()
        while True:
            if self.accept("%"):
                value = self.scale(value, 0.01)
            elif self.accept("!"):
                if value[0] or not value[1].is_integer() or not 0 <= value[1] <= 170:
                    raise ValueError("Factorial requires a whole-number constant from 0 to 170.")
                value = {}, float(math.factorial(int(value[1])))
            else:
                return value

    def parse_primary(self) -> tuple[dict[str, float], float]:
        token = self.peek()
        if not token:
            raise ValueError("Complete the equation.")
        self.position += 1
        kind, name = token
        if kind == "number":
            return {}, float(name)
        if name == "(":
            value = self.parse_expression()
            if not self.accept(")"):
                raise ValueError("Missing closing parenthesis.")
            return value
        if kind != "identifier":
            raise ValueError("Check the equation format.")
        if name in self.variables:
            return {name: 1.0}, 0.0
        if name == "pi":
            return {}, math.pi
        if name == "e":
            return {}, math.e
        raise ValueError(f"Unknown variable or function: {name}")


def polynomial_coefficients(source: str, degree_limit: int = 8) -> tuple[list[float], str]:
    variables = polynomial_variables(source)
    if len(variables) > 1:
        raise ValueError("A polynomial must use only one variable letter.")
    variable = variables[0] if variables else "x"
    polynomial = ExpressionParser(source, (variable,), degree_limit).parse()
    if any(y != 0 for _, y in polynomial):
        raise ValueError(f"Polynomials must use only {variable}.")
    coefficients = [0.0] * (degree_limit + 1)
    for (degree, _), coefficient in polynomial.items():
        coefficients[degree] = coefficient
    while len(coefficients) > 1 and abs(coefficients[-1]) < 1e-12:
        coefficients.pop()
    if not all(math.isfinite(value) for value in coefficients):
        raise ValueError("Polynomial coefficients must be finite.")
    return coefficients, variable


def evaluate_polynomial(coefficients: list[float], x: float) -> float:
    value = 0.0
    for coefficient in reversed(coefficients):
        value = value * x + coefficient
    return value


def polynomial_tolerance(coefficients: list[float], x: float) -> float:
    return max(1.0, sum(abs(c) * abs(x) ** degree for degree, c in enumerate(coefficients))) * 1e-10


def real_roots(coefficients: list[float]) -> list[float]:
    degree = len(coefficients) - 1
    if degree <= 0:
        return []
    if degree == 1:
        return [-coefficients[0] / coefficients[1]]
    derivative = [coefficient * (index + 1) for index, coefficient in enumerate(coefficients[1:])]
    critical = real_roots(derivative)
    leading = abs(coefficients[-1])
    bound = 1 + max((abs(value) / leading for value in coefficients[:-1]), default=0.0)
    if not math.isfinite(bound):
        raise ValueError("This polynomial is too large to solve reliably.")
    points = [-bound, *sorted(point for point in critical if -bound < point < bound), bound]
    roots = [
        point for point in critical
        if abs(evaluate_polynomial(coefficients, point)) <= polynomial_tolerance(coefficients, point)
    ]
    for low, high in zip(points, points[1:]):
        low_value = evaluate_polynomial(coefficients, low)
        high_value = evaluate_polynomial(coefficients, high)
        if not math.isfinite(low_value) or not math.isfinite(high_value) or low_value * high_value >= 0:
            continue
        for _ in range(100):
            middle = (low + high) / 2
            middle_value = evaluate_polynomial(coefficients, middle)
            if middle_value == 0:
                low = high = middle
                break
            if (middle_value < 0) == (low_value < 0):
                low, low_value = middle, middle_value
            else:
                high = middle
        roots.append((low + high) / 2)
    roots.sort()
    distinct = []
    for root in roots:
        if not distinct or abs(root - distinct[-1]) > 1e-7 * max(1.0, abs(root)):
            distinct.append(root)
    return distinct


def polynomial_text(coefficients: list[float], variable: str = "x") -> str:
    terms = []
    for degree in range(len(coefficients) - 1, -1, -1):
        coefficient = coefficients[degree]
        if abs(coefficient) < 1e-10:
            continue
        magnitude = format_number(abs(coefficient))
        factor = magnitude if degree == 0 or abs(coefficient) != 1 else ""
        term = f"{factor}{variable if degree else ''}{f'^{degree}' if degree > 1 else ''}"
        if not terms:
            terms.append(("-" if coefficient < 0 else "") + term)
        else:
            terms.append((" - " if coefficient < 0 else " + ") + term)
    return "".join(terms) or "0"


def solve_equation(source: str, kind: str, degrees: bool) -> str:
    lines = source.splitlines()
    if kind == "Simultaneous" and any(not item.strip() for item in lines):
        raise ValueError("Complete every equation before solving.")
    equations = [item.strip() for item in lines if item.strip()]
    if kind != "Simultaneous" and len(equations) != 1:
        raise ValueError("Enter one equation.")
    if kind == "Simultaneous" and len(equations) < 2:
        raise ValueError("Enter at least two equations, one per line.")
    variable_names = []
    for equation in equations:
        if equation.count("=") != 1:
            raise ValueError("Write each equation with exactly one equals sign.")
        equation_variables = (
            tuple(
                value for token_kind, value in tokenize(equation)
                if token_kind == "identifier"
                and value not in ("pi", "e", "npr", "ncr", *FUNCTIONS)
            )
            if kind == "Simultaneous"
            else polynomial_variables(equation)
        )
        for variable in equation_variables:
            if variable not in variable_names:
                variable_names.append(variable)
    if kind == "Simultaneous" and not variable_names:
        raise ValueError("Simultaneous equations must include at least one variable.")
    elif kind != "Simultaneous" and len(variable_names) > 1:
        raise ValueError("Use only one variable letter in this equation.")

    if kind == "Simultaneous":
        variables = tuple(variable_names)
        rows: list[list[float]] = []
        for equation in equations:
            left, right = equation.split("=")
            lhs = LinearExpressionParser(left, variables).parse()
            rhs = LinearExpressionParser(right, variables).parse()
            coefficients, constant = LinearExpressionParser.add(lhs, rhs, -1)
            row = [coefficients.get(name, 0.0) for name in variables] + [-constant]
            coefficient_scale = max((abs(value) for value in row[:-1]), default=0.0)
            if coefficient_scale == 0 and row[-1] != 0:
                return "These equations have no solution."
            if coefficient_scale:
                row = [value / coefficient_scale for value in row]
            if any(not math.isfinite(value) for value in row):
                raise ValueError("Equation values are outside the supported range.")
            rows.append(row)

        pivot_row = 0
        pivot_columns: list[int] = []
        column_scales = [
            max((abs(row[column]) for row in rows), default=0.0)
            for column in range(len(variables))
        ]
        for column in range(len(variables)):
            if pivot_row >= len(rows):
                break
            best_row = max(range(pivot_row, len(rows)), key=lambda index: abs(rows[index][column]))
            if abs(rows[best_row][column]) <= column_scales[column] * 1e-12:
                continue
            rows[pivot_row], rows[best_row] = rows[best_row], rows[pivot_row]
            pivot = rows[pivot_row][column]
            rows[pivot_row] = [value / pivot for value in rows[pivot_row]]
            for index, row in enumerate(rows):
                if index == pivot_row:
                    continue
                factor = row[column]
                if abs(factor) >= 1e-12:
                    rows[index] = [
                        value - factor * pivot_value
                        for value, pivot_value in zip(row, rows[pivot_row])
                    ]
                    if any(not math.isfinite(value) for value in rows[index]):
                        raise ValueError("Equation values are outside the supported range.")
            pivot_columns.append(column)
            pivot_row += 1
            if pivot_row == len(rows):
                break

        for row in rows:
            if (
                all(abs(value) <= column_scales[column] * 1e-12
                    for column, value in enumerate(row[:-1]))
                and abs(row[-1]) >= 1e-12
            ):
                return "These equations have no solution."
        if len(pivot_columns) < len(variables):
            return "These equations have infinitely many solutions."
        solutions = [""] * len(variables)
        for row_index, column in enumerate(pivot_columns):
            solutions[column] = f"{variables[column]} = {format_number(rows[row_index][-1])}"
        return ", ".join(solutions)

    variables = tuple(variable_names or ("x",))
    results = []
    for equation in equations:
        left, right = equation.split("=")
        lhs = ExpressionParser(left, variables, 2, degrees).parse()
        rhs = ExpressionParser(right, variables, 2, degrees).parse()
        results.append({key: value for key, value in {**lhs}.items()})
        for key, value in rhs.items():
            results[-1][key] = results[-1].get(key, 0.0) - value
        results[-1] = {key: value for key, value in results[-1].items() if abs(value) >= 1e-12}

    polynomial = results[0]
    if any(y != 0 for _, y in polynomial):
        raise ValueError("Use only one variable letter.")
    variable = variables[0]
    if kind == "Linear":
        if any(x > 1 for x, _ in polynomial):
            raise ValueError("A linear equation can only contain the variable to the first power.")
        coefficient = polynomial.get((1, 0), 0)
        value = -polynomial.get((0, 0), 0)
        if coefficient == 0:
            return f"Every value of {variable} is a solution." if value == 0 else "There is no solution."
        return f"{variable} = {format_number(value / coefficient)}"
    a, b, c = polynomial.get((2, 0), 0), polynomial.get((1, 0), 0), polynomial.get((0, 0), 0)
    if a == 0:
        coefficient = b
        value = -c
        if coefficient == 0:
            return f"Every value of {variable} is a solution." if value == 0 else "There is no solution."
        return f"{variable} = {format_number(value / coefficient)}"
    discriminant = b * b - 4 * a * c
    if discriminant < -1e-12:
        return "No real solutions."
    if abs(discriminant) <= 1e-12:
        return f"{variable} = {format_number(-b / (2 * a))}"
    root = math.sqrt(discriminant)
    return (
        f"{variable} = {format_number((-b - root) / (2 * a))} or "
        f"{variable} = {format_number((-b + root) / (2 * a))}"
    )


def factor_text(coefficients: list[float], variable: str) -> str:
    if len(coefficients) == 1:
        return f"Constant polynomial: {format_number(coefficients[0])}."
    remainder = list(coefficients)
    factors = []
    for root in real_roots(coefficients):
        while len(remainder) > 1 and abs(evaluate_polynomial(remainder, root)) <= polynomial_tolerance(remainder, root) * 10:
            factors.append(f"({variable} {'+' if root < 0 else '−'} {format_number(abs(root))})")
            quotient = [0.0] * (len(remainder) - 1)
            quotient[-1] = remainder[-1]
            for index in range(len(quotient) - 2, -1, -1):
                quotient[index] = remainder[index + 1] + root * quotient[index + 1]
            remainder = quotient
    leading = coefficients[-1]
    prefix = "" if leading == 1 else "−1" if leading == -1 else format_number(leading)
    factors.insert(0, prefix)
    if len(remainder) > 1:
        normalized = [coefficient / leading for coefficient in remainder]
        factors.append(f"({polynomial_text(normalized, variable)})")
    return f"{polynomial_text(coefficients, variable)} = {' '.join(part for part in factors if part) or '1'}"


def matrix_determinant(matrix: list[list[float]]) -> float:
    values = [row[:] for row in matrix]
    determinant = 1.0
    for column in range(len(values)):
        pivot = max(range(column, len(values)), key=lambda row: abs(values[row][column]))
        if abs(values[pivot][column]) < 1e-12:
            return 0.0
        if pivot != column:
            values[column], values[pivot] = values[pivot], values[column]
            determinant *= -1
        pivot_value = values[column][column]
        determinant *= pivot_value
        for row in range(column + 1, len(values)):
            scale = values[row][column] / pivot_value
            for entry in range(column + 1, len(values)):
                values[row][entry] -= scale * values[column][entry]
    return determinant


def matrix_inverse(matrix: list[list[float]]) -> list[list[float]]:
    size = len(matrix)
    augmented = [
        row[:] + [1.0 if row_index == column else 0.0 for column in range(size)]
        for row_index, row in enumerate(matrix)
    ]
    for column in range(size):
        pivot = max(range(column, size), key=lambda row: abs(augmented[row][column]))
        if abs(augmented[pivot][column]) < 1e-12:
            raise ValueError("This matrix is singular and has no inverse.")
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        pivot_value = augmented[column][column]
        augmented[column] = [value / pivot_value for value in augmented[column]]
        for row in range(size):
            if row == column:
                continue
            scale = augmented[row][column]
            augmented[row] = [
                value - scale * pivot_entry
                for value, pivot_entry in zip(augmented[row], augmented[column])
            ]
    return [row[size:] for row in augmented]


def matrix_operation(
    operation: str, matrix_a: list[list[float]], matrix_b: list[list[float]]
) -> str:
    if operation == "Determinant of A":
        return f"det(A) = {format_number(matrix_determinant(matrix_a))}"
    if operation == "Inverse of A":
        result = matrix_inverse(matrix_a)
    elif operation == "Transpose of A":
        result = [list(column) for column in zip(*matrix_a)]
    elif operation == "A + B":
        result = [
            [a + b for a, b in zip(row_a, row_b)]
            for row_a, row_b in zip(matrix_a, matrix_b)
        ]
    elif operation == "A − B":
        result = [
            [a - b for a, b in zip(row_a, row_b)]
            for row_a, row_b in zip(matrix_a, matrix_b)
        ]
    elif operation == "A × B":
        result = [
            [
                sum(matrix_a[row][k] * matrix_b[k][column] for k in range(len(matrix_a)))
                for column in range(len(matrix_a))
            ]
            for row in range(len(matrix_a))
        ]
    else:
        raise ValueError("Choose a matrix operation.")
    return "\n".join("[ " + "    ".join(format_number(value) for value in row) + " ]" for row in result)


class CalcWindow(Gtk.Window):
    def __init__(self) -> None:
        super().__init__(title="Calc ES")
        self.set_resizable(True)
        self.set_default_size(900, 650)
        self.set_border_width(0)
        self.degrees = True
        self.memory: float | None = None
        self.last_answer = 0.0
        self.history: list[str] = []
        self.set_icon_from_file(str(Path(__file__).with_name("logo.svg")))
        provider = Gtk.CssProvider()
        provider.load_from_data(f"""
            * {{ outline-color: {ACCENT}; }}
            window {{ background: #f1f3f8; color: #111318; }}
            headerbar {{ background: #ffffff; color: #111318; border: none; border-bottom: 1px solid #d9deea; padding: 5px 10px; }}
            headerbar .title {{ color: #111318; font-weight: 700; letter-spacing: .2px; }}
            headerbar .subtitle {{ color: #111318; font-size: 10px; }}
            stacksidebar {{ background: #e8ecf4; border-right: 1px solid #d3d9e5; }}
            stacksidebar row {{ margin: 4px 8px; padding: 10px 12px; border-radius: 9px; color: #111318; }}
            stacksidebar row:hover {{ background: #dce2ee; color: #111318; }}
            stacksidebar row:selected {{ background: #dcd5ff; color: #171326; font-weight: 600; }}
            stack {{ background: #f7f8fb; }}
            label {{ color: #000000; }}
            entry, textview, spinbutton, combobox, combobox button {{ background: #ffffff; color: #000000; border: 1px solid #c8cfdd; border-radius: 9px; padding: 8px 10px; caret-color: #5641bd; }}
            entry:focus, textview:focus, spinbutton:focus, combobox:focus {{ background: #ffffff; border-color: {ACCENT}; }}
            entry placeholder {{ color: #596273; }}
            combobox arrow {{ color: #202431; }}
            button {{ background: #ffffff; color: #000000; border: 1px solid #cbd2df; border-radius: 10px; padding: 8px 10px; min-height: 34px; }}
            button:hover {{ background: #edf0f7; border-color: #9b91c8; }}
            button:active {{ background: #e4e0f6; }}
            button:focus {{ border-color: {ACCENT}; }}
            button.accent {{ background: #d8d0ff; color: #000000; border-color: #aa9cff; font-weight: 700; }}
            button.accent:hover {{ background: #c9beff; border-color: #8774e8; }}
            button.operator {{ background: #e7e2fa; color: #000000; font-size: 16px; }}
            button.function {{ background: #edf0f6; color: #000000; }}
            button.utility {{ background: #eceaf4; color: #000000; }}
            button.danger {{ background: #ffeaed; color: #000000; }}
            button.number {{ background: #ffffff; font-size: 17px; font-weight: 600; }}
            label.heading {{ font-size: 20px; font-weight: 700; color: #000000; }}
            label.subheading {{ color: #000000; font-size: 12px; }}
            label.field-label {{ color: #000000; font-size: 11px; font-weight: 600; }}
            box.equation-card {{ background: #ffffff; border: 1px solid #d1d7e2; border-radius: 12px; padding: 12px; }}
            label.result {{ font-size: 16px; padding: 8px 4px; color: #000000; }}
            label.typing-line {{ color: #000000; background: #eceff5; border: 1px solid #d5dbe6; border-radius: 9px; padding: 10px 12px; }}
            label.display-expression {{ color: #000000; font-size: 17px; }}
            label.display-result {{ color: #000000; font-size: 38px; font-weight: 700; }}
            frame.display-frame {{ background: #ffffff; border: 1px solid #d1d7e2; border-radius: 16px; }}
            frame.display-frame > border {{ border: none; }}
            frame.card {{ background: #ffffff; border: 1px solid #d1d7e2; border-radius: 14px; }}
            frame.card > border {{ border: none; }}
            drawingarea {{ background: #1d2230; }}
        """.encode())
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        header = Gtk.HeaderBar()
        header.set_show_close_button(True)
        header.set_title("Calc ES")
        header.set_subtitle("Scientific calculator")
        app_icon = Gtk.Image.new_from_file(str(Path(__file__).with_name("logo.svg")))
        app_icon.set_pixel_size(28)
        header.pack_start(app_icon)
        self.set_titlebar(header)
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_UP_DOWN)
        self.stack.set_transition_duration(140)
        sidebar = Gtk.StackSidebar()
        sidebar.set_stack(self.stack)
        sidebar.set_size_request(150, -1)
        self.add_tool(self.make_calculator(), "calculator", "Calculator")
        self.add_tool(self.make_equations(), "equations", "Equation solver")
        self.add_tool(self.make_polynomial(False), "roots", "Polynomial roots")
        self.add_tool(self.make_polynomial(True), "factorizer", "Factorizer")
        self.add_tool(self.make_graph(), "graph", "Function graph")
        self.add_tool(self.make_fraction(), "fractions", "Fractions")
        self.add_tool(self.make_matrices(), "matrices", "Matrices")
        layout = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        layout.pack_start(sidebar, False, False, 0)
        layout.pack_start(self.stack, True, True, 0)
        self.add(layout)

    def add_tool(self, content: Gtk.Widget, name: str, title: str) -> None:
        page = Gtk.ScrolledWindow()
        page.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        page.add(content)
        self.stack.add_titled(page, name, title)

    def content_box(self) -> Gtk.Box:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        box.set_border_width(22)
        return box

    def result_label(self, text: str = "") -> Gtk.Label:
        label = Gtk.Label(label=text)
        label.set_xalign(0)
        label.set_line_wrap(True)
        label.get_style_context().add_class("result")
        return label

    def labeled_entry(self, parent: Gtk.Box, label: str, initial: str = "") -> Gtk.Entry:
        parent.pack_start(Gtk.Label(label=label, xalign=0), False, False, 0)
        entry = Gtk.Entry()
        entry.set_text(initial)
        parent.pack_start(entry, False, False, 0)
        return entry

    def add_typing_line(self, parent: Gtk.Box, initial: str = "") -> Gtk.Label:
        line = Gtk.Label(label=f"Typing: {initial or '—'}", xalign=0)
        line.set_line_wrap(True)
        line.set_selectable(True)
        line.get_style_context().add_class("typing-line")
        parent.pack_start(line, False, False, 0)
        return line

    def connect_entry_typing_line(self, entry: Gtk.Entry, line: Gtk.Label, prefix: str = "Typing: ") -> None:
        entry.connect(
            "changed",
            lambda widget: line.set_text(f"{prefix}{widget.get_text() or '—'}"),
        )

    def add_button(self, parent: Gtk.Box, text: str, callback) -> Gtk.Button:
        button = Gtk.Button(label=text)
        button.connect("clicked", callback)
        parent.pack_start(button, False, False, 0)
        return button

    def show_result(self, output: Gtk.Label, callback) -> None:
        try:
            output.set_text(callback())
        except (ValueError, OverflowError, ZeroDivisionError) as error:
            output.set_text(str(error))

    def make_calculator(self) -> Gtk.Widget:
        box = self.content_box()
        box.set_border_width(20)
        title = Gtk.Label(label="Scientific calculator", xalign=0)
        title.get_style_context().add_class("heading")
        box.pack_start(title, False, False, 0)
        display = Gtk.Frame()
        display.get_style_context().add_class("display-frame")
        display_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=7)
        display_box.set_border_width(14)
        display.add(display_box)
        self.calc_entry = Gtk.Entry()
        self.calc_entry.set_alignment(1)
        self.calc_entry.set_placeholder_text("Type an expression or use the keys")
        self.calc_entry.get_style_context().add_class("display-expression")
        self.calc_entry.connect("activate", self.on_calculate)
        display_box.pack_start(self.calc_entry, False, False, 0)
        self.calc_result = Gtk.Label(label="0", xalign=1)
        self.calc_result.get_style_context().add_class("display-result")
        display_box.pack_start(self.calc_result, False, False, 0)
        box.pack_start(display, False, False, 0)

        toolbar = Gtk.Box(spacing=8)
        box.pack_start(toolbar, False, False, 0)
        self.angle_button = Gtk.Button(label="DEG")
        self.angle_button.get_style_context().add_class("utility")
        self.angle_button.connect("clicked", self.toggle_angle)
        toolbar.pack_start(self.angle_button, False, False, 0)
        for label, action in (("MC", "memory-clear"), ("MR", "memory-recall"),
                              ("M+", "memory-add"), ("M−", "memory-subtract")):
            button = Gtk.Button(label=label)
            button.get_style_context().add_class("utility")
            button.connect("clicked", self.on_memory, action)
            toolbar.pack_start(button, False, False, 0)
        self.memory_indicator = Gtk.Label(label="")
        self.memory_indicator.set_xalign(1)
        toolbar.pack_end(self.memory_indicator, True, True, 0)

        controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        box.pack_start(controls, True, True, 0)
        scientific = Gtk.Grid(column_spacing=7, row_spacing=7)
        numeric = Gtk.Grid(column_spacing=7, row_spacing=7)
        controls.pack_start(scientific, True, True, 0)
        controls.pack_start(numeric, True, True, 0)
        scientific_keys = [
            [("sin", "sin("), ("cos", "cos("), ("tan", "tan(")],
            [("sin⁻¹", "asin("), ("cos⁻¹", "acos("), ("tan⁻¹", "atan(")],
            [("√", "sqrt("), ("log", "log("), ("ln", "ln(")],
            [("abs", "abs("), ("x²", "^2"), ("xʸ", "^")],
            [("nPr", " npr "), ("nCr", " ncr "), ("x!", "!")],
            [("π", "pi"), ("e", "e"), ("%", "%")],
            [("(", "("), (")", ")"), ("±", "±")],
        ]
        for row, keys in enumerate(scientific_keys):
            for column, (label, value) in enumerate(keys):
                self.attach_key(scientific, label, value, column, row, "function")

        numeric_keys = [
            [("AC", "AC", "danger"), ("DEL", "⌫", "utility"), ("÷", "÷", "operator"), ("×", "×", "operator")],
            [("7", "7", "number"), ("8", "8", "number"), ("9", "9", "number"), ("−", "−", "operator")],
            [("4", "4", "number"), ("5", "5", "number"), ("6", "6", "number"), ("+", "+", "operator")],
            [("1", "1", "number"), ("2", "2", "number"), ("3", "3", "number"), ("=", "=", "accent")],
            [("0", "0", "number"), (".", ".", "number"), ("Ans", "Ans", "utility")],
        ]
        for row, keys in enumerate(numeric_keys):
            for column, (label, value, style) in enumerate(keys):
                self.attach_key(numeric, label, value, column, row, style)
        box.pack_start(Gtk.Label(label="Recent calculations", xalign=0), False, False, 0)
        self.calc_history = Gtk.Label(label="No calculations yet.")
        self.calc_history.set_xalign(0)
        self.calc_history.set_selectable(True)
        box.pack_start(self.calc_history, False, False, 0)
        box.pack_start(
            Gtk.Label(
                label="nPr / nCr: whole numbers with 0 ≤ r ≤ n ≤ 170.  •  DEG/RAD switches angle mode.",
                xalign=0,
            ),
            False, False, 0,
        )
        return box

    def attach_key(self, grid: Gtk.Grid, label: str, value: str, column: int, row: int, style: str) -> None:
        button = Gtk.Button(label=label)
        button.set_hexpand(True)
        button.set_vexpand(True)
        button.set_size_request(-1, 42)
        button.get_style_context().add_class(style)
        button.connect("clicked", self.on_key, value)
        grid.attach(button, column, row, 1, 1)

    def toggle_angle(self, button: Gtk.Button) -> None:
        self.degrees = not self.degrees
        button.set_label("DEG" if self.degrees else "RAD")

    def on_key(self, _button, value: str) -> None:
        current = self.calc_entry.get_text()
        if value == "AC":
            self.calc_entry.set_text("")
        elif value == "⌫":
            self.calc_entry.set_text(current[:-1])
        elif value == "=":
            self.on_calculate()
        elif value == "±":
            self.calc_entry.set_text(f"-({current})" if current else "-")
        elif value == "Ans":
            self.calc_entry.set_text(current + format_number(self.last_answer))
        else:
            self.calc_entry.set_text(current + value)
        self.calc_entry.grab_focus()
        self.calc_entry.set_position(-1)

    def on_memory(self, _button, action: str) -> None:
        if action == "memory-clear":
            self.memory = None
        elif action == "memory-recall":
            if self.memory is None:
                self.memory_indicator.set_text("Memory is empty")
                return
            self.calc_entry.set_text(self.calc_entry.get_text() + format_number(self.memory))
            self.calc_entry.grab_focus()
            self.calc_entry.set_position(-1)
        else:
            try:
                current = ExpressionParser(self.calc_entry.get_text(), degrees=self.degrees).parse()
                self.memory = (self.memory or 0) + (current if action == "memory-add" else -current)
            except ValueError as error:
                self.memory_indicator.set_text(str(error))
                return
        self.memory_indicator.set_text("M" if self.memory is not None else "")

    def on_calculate(self, *_args) -> None:
        def calculate():
            source = self.calc_entry.get_text()
            value = ExpressionParser(source, degrees=self.degrees).parse()
            rendered = format_number(value)
            self.last_answer = value
            self.history.insert(0, f"{source} = {rendered}")
            self.history = self.history[:8]
            self.calc_history.set_text("\n".join(self.history))
            self.calc_result.set_text(rendered)
        try:
            calculate()
        except (ValueError, OverflowError, ZeroDivisionError) as error:
            self.calc_result.set_text(str(error))

    def make_equations(self) -> Gtk.Widget:
        box = self.content_box()
        heading = Gtk.Label(label="Equation solver", xalign=0)
        heading.get_style_context().add_class("heading")
        box.pack_start(heading, False, False, 0)
        self.equation_description = Gtk.Label(xalign=0)
        self.equation_description.set_line_wrap(True)
        self.equation_description.get_style_context().add_class("subheading")
        box.pack_start(self.equation_description, False, False, 0)
        type_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        box.pack_start(type_row, False, False, 0)
        type_label = Gtk.Label(label="Equation type", xalign=0)
        type_label.get_style_context().add_class("field-label")
        type_row.pack_start(type_label, False, False, 0)
        self.equation_kind = Gtk.ComboBoxText()
        self.equation_kind.set_hexpand(False)
        for kind in ("Linear", "Quadratic", "Simultaneous"):
            self.equation_kind.append_text(kind)
        self.equation_kind.set_active(0)
        type_row.pack_start(self.equation_kind, False, False, 0)
        self.equation_rows: list[tuple[Gtk.Box, Gtk.Label, Gtk.Entry, Gtk.Button]] = []
        self.equation_fields = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.equation_scroll = Gtk.ScrolledWindow()
        self.equation_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.equation_scroll.set_size_request(-1, 250)
        self.equation_scroll.add(self.equation_fields)
        box.pack_start(self.equation_scroll, False, False, 0)
        self.add_equation_row()
        self.add_equation_row()
        self.equation_add_button = self.add_button(
            box, "＋ Add another equation", self.on_add_equation
        )
        self.equation_add_button.get_style_context().add_class("utility")
        self.equation_add_button.set_no_show_all(True)
        self.equation_typing = self.add_typing_line(box)
        self.equation_submitted = self.add_typing_line(box, "Equation to solve: —")
        self.equation_result = self.result_label()
        box.pack_start(self.equation_result, False, False, 0)
        self.equation_kind.connect("changed", self.update_equation_inputs)
        self.update_equation_inputs()
        self.add_button(box, "Solve equations", self.on_solve_equation)
        return box

    def add_equation_row(self) -> None:
        index = len(self.equation_rows)
        row = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        row.get_style_context().add_class("equation-card")
        row.set_no_show_all(index > 0)
        self.equation_fields.pack_start(row, False, False, 0)
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        row.pack_start(header, False, False, 0)
        label = Gtk.Label(label=f"Equation {index + 1}", xalign=0)
        label.get_style_context().add_class("field-label")
        header.pack_start(label, True, True, 0)
        remove_button = Gtk.Button(label="Remove")
        remove_button.get_style_context().add_class("utility")
        remove_button.set_no_show_all(True)
        remove_button.connect("clicked", lambda *_args, target=row: self.remove_equation_row(target))
        header.pack_end(remove_button, False, False, 0)
        entry = Gtk.Entry()
        entry.set_input_purpose(Gtk.InputPurpose.FREE_FORM)
        entry.set_hexpand(True)
        row.pack_start(entry, False, False, 0)
        entry.connect("changed", self.update_equation_typing)
        entry.connect("activate", self.on_solve_equation)
        self.equation_rows.append((row, label, entry, remove_button))
        if index == 0:
            row.show_all()

    def remove_equation_row(self, row: Gtk.Box) -> None:
        if len(self.equation_rows) <= 2:
            return
        for equation_row in self.equation_rows:
            if equation_row[0] is row:
                self.equation_rows.remove(equation_row)
                row.destroy()
                break
        self.update_equation_inputs()

    def on_add_equation(self, *_args) -> None:
        self.add_equation_row()
        self.update_equation_inputs()
        self.equation_rows[-1][2].grab_focus()

    def update_equation_typing(self, *_args) -> None:
        simultaneous = self.equation_kind.get_active_text() == "Simultaneous"
        visible_rows = self.equation_rows if simultaneous else self.equation_rows[:1]
        sources = [
            f"Equation {index + 1}: {entry.get_text().strip()}"
            for index, (_, _, entry, _) in enumerate(visible_rows)
            if entry.get_text().strip()
        ]
        self.equation_typing.set_text("Typing:\n" + ("\n".join(sources) or "—"))

    def update_equation_inputs(self, *_args) -> None:
        simultaneous = self.equation_kind.get_active_text() == "Simultaneous"
        if simultaneous:
            self.equation_add_button.show()
        else:
            self.equation_add_button.hide()
        self.equation_description.set_text(
            "Enter one linear equation per row; add as many equations and variables as needed. "
            "Use * to multiply variables; pi and e are constants."
            if simultaneous
            else "Solve a linear or quadratic equation in one variable."
        )
        self.equation_scroll.set_size_request(
            -1,
            min(320, max(100, len(self.equation_rows) * 100))
            if simultaneous
            else 100,
        )
        for index, (row, label, _, remove_button) in enumerate(self.equation_rows):
            label.set_text(
                f"Equation {index + 1}" if simultaneous else "Equation"
            )
            if simultaneous:
                row.show()
                for child in row.get_children():
                    child.show()
                    if isinstance(child, Gtk.Container):
                        for nested_child in child.get_children():
                            nested_child.show()
                if len(self.equation_rows) > 2:
                    remove_button.show()
                else:
                    remove_button.hide()
            else:
                if index == 0:
                    row.show()
                else:
                    row.hide()
        equation_kind = self.equation_kind.get_active_text()
        if simultaneous:
            for index, (_, _, entry, _) in enumerate(self.equation_rows):
                entry.set_placeholder_text(
                    ("e.g. 2t + u = 5" if index == 0 else
                     "e.g. t - u = 1" if index == 1 else
                     "Enter another linear equation")
                )
        elif equation_kind == "Quadratic":
            self.equation_rows[0][2].set_placeholder_text("e.g. t^2 - 5t + 6 = 0")
        else:
            self.equation_rows[0][2].set_placeholder_text("e.g. 2t + 3 = 7")
        self.update_equation_typing()

    def on_solve_equation(self, *_args) -> None:
        simultaneous = self.equation_kind.get_active_text() == "Simultaneous"
        visible_rows = self.equation_rows if simultaneous else self.equation_rows[:1]
        equations = [entry.get_text().strip() for _, _, entry, _ in visible_rows]
        source = "\n".join(equations)
        self.equation_submitted.set_text(f"Equation to solve:\n{source or '—'}")
        if simultaneous and any(not equation for equation in equations):
            self.equation_result.set_text("Complete every equation before solving.")
            return
        self.show_result(self.equation_result, lambda: solve_equation(
            source, self.equation_kind.get_active_text(), self.degrees
        ))

    def make_polynomial(self, factor: bool) -> Gtk.Widget:
        box = self.content_box()
        box.pack_start(Gtk.Label(
            label="Factor a polynomial (degree ≤ 8)" if factor else "Find real roots (degree ≤ 8)",
            xalign=0,
        ), False, False, 0)
        entry = self.labeled_entry(box, "Polynomial", "x^3 - 6x^2 + 11x - 6")
        typing_line = self.add_typing_line(box, entry.get_text())
        self.connect_entry_typing_line(entry, typing_line)
        if not factor:
            submitted_line = self.add_typing_line(box, f"Polynomial to solve: {entry.get_text()}")
        output = self.result_label()
        box.pack_start(output, False, False, 0)
        if factor:
            def action(*_args):
                return factor_text(*polynomial_coefficients(entry.get_text()))
            self.add_button(box, "Factor polynomial", lambda *_: self.show_result(output, action))
        else:
            def action(*_args):
                coefficients, variable = polynomial_coefficients(entry.get_text())
                if len(coefficients) == 1:
                    return "Every real number is a root." if coefficients[0] == 0 else "This non-zero constant has no roots."
                roots = real_roots(coefficients)
                if not roots:
                    return "No real roots."
                return "Real roots: " + ", ".join(f"{variable} = {format_number(root)}" for root in roots)
            def solve_roots(*_args):
                submitted_line.set_text(f"Polynomial to solve:\n{entry.get_text() or '—'}")
                self.show_result(output, action)
            self.add_button(box, "Find roots", solve_roots)
        return box

    def make_graph(self) -> Gtk.Widget:
        box = self.content_box()
        box.pack_start(Gtk.Label(label="Plot a calculator expression", xalign=0), False, False, 0)
        self.graph_expression = self.labeled_entry(box, "Function", "x^2")
        self.graph_typing = self.add_typing_line(box, "f(x) = x^2")
        controls = Gtk.Grid(column_spacing=8, row_spacing=8)
        box.pack_start(controls, False, False, 0)
        controls.attach(Gtk.Label(label="Variable"), 0, 0, 1, 1)
        self.graph_variable = Gtk.Entry()
        self.graph_variable.set_text("x")
        self.graph_variable.set_max_length(1)
        self.graph_variable.set_width_chars(3)
        controls.attach(self.graph_variable, 1, 0, 1, 1)
        controls.attach(Gtk.Label(label="From"), 0, 1, 1, 1)
        self.graph_min = Gtk.SpinButton.new_with_range(-1_000_000, 1_000_000, 0.1)
        self.graph_min.set_digits(2)
        self.graph_min.set_width_chars(7)
        self.graph_min.set_value(-10)
        controls.attach(self.graph_min, 1, 1, 1, 1)
        controls.attach(Gtk.Label(label="to"), 2, 1, 1, 1)
        self.graph_max = Gtk.SpinButton.new_with_range(-1_000_000, 1_000_000, 0.1)
        self.graph_max.set_digits(2)
        self.graph_max.set_width_chars(7)
        self.graph_max.set_value(10)
        controls.attach(self.graph_max, 3, 1, 1, 1)
        self.graph_area = Gtk.DrawingArea()
        self.graph_area.set_size_request(360, 240)
        self.graph_area.connect("draw", self.draw_graph)
        box.pack_start(self.graph_area, True, True, 0)
        self.graph_result = self.result_label()
        box.pack_start(self.graph_result, False, False, 0)
        self.graph_expression.connect("changed", lambda *_: self.graph_area.queue_draw())
        self.graph_expression.connect("changed", self.update_graph_typing)
        self.graph_variable.connect("changed", self.update_graph_typing)
        self.graph_variable.connect("changed", lambda *_: self.graph_area.queue_draw())
        self.graph_min.connect("value-changed", lambda *_: self.graph_area.queue_draw())
        self.graph_max.connect("value-changed", lambda *_: self.graph_area.queue_draw())
        return box

    def update_graph_typing(self, *_args) -> None:
        variable = self.graph_variable.get_text() or "?"
        expression = self.graph_expression.get_text() or "—"
        self.graph_typing.set_text(f"Typing: f({variable}) = {expression}")

    def draw_graph(self, area, context) -> bool:
        width = area.get_allocated_width()
        height = area.get_allocated_height()
        context.set_source_rgb(0.11, 0.13, 0.19)
        context.paint()
        xmin = self.graph_min.get_value()
        xmax = self.graph_max.get_value()
        variable = self.graph_variable.get_text().lower()
        if not re.fullmatch("[a-z]", variable) or xmin >= xmax or xmax - xmin > 200:
            self.graph_result.set_text("Choose one variable letter and an increasing range no wider than 200.")
            return False
        ymin, ymax = -10.0, 10.0
        x_pixel = lambda x: (x - xmin) / (xmax - xmin) * width
        y_pixel = lambda y: height - (y - ymin) / (ymax - ymin) * height
        context.set_line_width(1)
        context.set_source_rgb(0.20, 0.22, 0.29)
        for tick in range(math.ceil(xmin), math.floor(xmax) + 1):
            context.move_to(x_pixel(tick), 0)
            context.line_to(x_pixel(tick), height)
        for tick in range(-10, 11, 2):
            context.move_to(0, y_pixel(tick))
            context.line_to(width, y_pixel(tick))
        context.stroke()
        context.set_source_rgb(0.55, 0.58, 0.67)
        context.set_line_width(1.5)
        if xmin <= 0 <= xmax:
            context.move_to(x_pixel(0), 0)
            context.line_to(x_pixel(0), height)
        context.move_to(0, y_pixel(0))
        context.line_to(width, y_pixel(0))
        context.stroke()
        context.set_source_rgb(0.65, 0.58, 1)
        context.set_line_width(2.5)
        drawing = False
        expression = self.graph_expression.get_text()
        for pixel in range(width + 1):
            x = xmin + pixel / max(width, 1) * (xmax - xmin)
            try:
                y = evaluate_numeric_variable(expression, variable, x, self.degrees)
            except (ValueError, OverflowError, ZeroDivisionError):
                drawing = False
                continue
            if not math.isfinite(y) or y < ymin - 20 or y > ymax + 20:
                drawing = False
                continue
            if drawing:
                context.line_to(pixel, y_pixel(y))
            else:
                context.move_to(pixel, y_pixel(y))
                drawing = True
        context.stroke()
        self.graph_result.set_text(f"f({variable}) = {expression}; visible y-range: −10 to 10.")
        return False

    def make_fraction(self) -> Gtk.Widget:
        box = self.content_box()
        box.pack_start(Gtk.Label(label="Convert fractions, decimals, and mixed numbers", xalign=0), False, False, 0)
        self.fraction_entry = self.labeled_entry(
            box, "Enter a decimal, fraction, or mixed number (e.g. 2.75, 11/4, or 2 3/4)", "2.75"
        )
        self.fraction_typing = self.add_typing_line(box, self.fraction_entry.get_text())
        self.connect_entry_typing_line(self.fraction_entry, self.fraction_typing)
        self.fraction_result = self.result_label()
        box.pack_start(self.fraction_result, False, False, 0)
        self.add_button(box, "Convert", self.on_convert_fraction)
        return box

    def on_convert_fraction(self, *_args) -> None:
        def convert():
            source = self.fraction_entry.get_text().strip()
            if len(source) > 300:
                raise ValueError("Enter a value with no more than 300 characters.")
            mixed = re.fullmatch(r"([+-]?\d+)\s+(\d+)\s*/\s*(\d+)", source)
            if mixed:
                whole, numerator, denominator = (int(part) for part in mixed.groups())
                if denominator == 0:
                    raise ValueError("The denominator cannot be zero.")
                sign = -1 if whole < 0 or mixed.group(1).startswith("-") else 1
                numerator = sign * (abs(whole) * denominator + numerator)
            elif "/" in source:
                pieces = source.split("/")
                if len(pieces) != 2:
                    raise ValueError("Enter a fraction as numerator/denominator.")
                numerator, denominator = (int(piece.strip()) for piece in pieces)
                if denominator == 0:
                    raise ValueError("The denominator cannot be zero.")
                if denominator < 0:
                    numerator, denominator = -numerator, -denominator
                divisor = math.gcd(numerator, denominator)
                numerator //= divisor
                denominator //= divisor
            else:
                if not re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)", source):
                    raise ValueError("Enter a decimal number without an exponent, or a fraction.")
                try:
                    decimal = Decimal(source)
                except InvalidOperation as error:
                    raise ValueError("Enter a valid decimal or fraction.") from error
                if not decimal.is_finite():
                    raise ValueError("Enter a finite decimal.")
                numerator, denominator = decimal.as_integer_ratio()
                divisor = math.gcd(numerator, denominator)
                numerator //= divisor
                denominator //= divisor
            if denominator < 0:
                numerator = -numerator
                denominator = -denominator
            divisor = math.gcd(numerator, denominator)
            numerator //= divisor
            denominator //= divisor
            decimal_value = float(Decimal(numerator) / Decimal(denominator))
            return (
                f"Fraction: {numerator}/{denominator}\n"
                f"Decimal: {format_number(decimal_value)}\n"
                f"Mixed number: {mixed_fraction_text(numerator, denominator)}"
            )
        self.show_result(self.fraction_result, convert)

    def make_matrices(self) -> Gtk.Widget:
        box = self.content_box()
        box.set_border_width(20)
        title = Gtk.Label(label="Matrix calculator", xalign=0)
        title.get_style_context().add_class("heading")
        box.pack_start(title, False, False, 0)
        box.pack_start(
            Gtk.Label(label="Enter square matrices up to 3 × 3, then choose an operation.", xalign=0),
            False, False, 0,
        )
        settings = Gtk.Box(spacing=10)
        box.pack_start(settings, False, False, 0)
        settings.pack_start(Gtk.Label(label="Size"), False, False, 0)
        self.matrix_size = Gtk.ComboBoxText()
        self.matrix_size.append_text("2 × 2")
        self.matrix_size.append_text("3 × 3")
        self.matrix_size.set_active(0)
        settings.pack_start(self.matrix_size, False, False, 0)
        settings.pack_start(Gtk.Label(label="Operation"), False, False, 0)
        self.matrix_operation = Gtk.ComboBoxText()
        for operation in ("Determinant of A", "Inverse of A", "Transpose of A", "A + B", "A − B", "A × B"):
            self.matrix_operation.append_text(operation)
        self.matrix_operation.set_active(0)
        settings.pack_start(self.matrix_operation, True, True, 0)

        self.matrix_fields_area = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        box.pack_start(self.matrix_fields_area, False, False, 0)
        self.matrix_a_frame = Gtk.Frame()
        self.matrix_a_frame.get_style_context().add_class("card")
        self.matrix_b_frame = Gtk.Frame()
        self.matrix_b_frame.get_style_context().add_class("card")
        self.matrix_b_frame.set_no_show_all(True)
        self.matrix_fields_area.pack_start(self.matrix_a_frame, True, True, 0)
        self.matrix_fields_area.pack_start(self.matrix_b_frame, True, True, 0)
        self.matrix_typing = self.add_typing_line(box)
        self.matrix_size.connect("changed", self.rebuild_matrix_fields)
        self.matrix_operation.connect("changed", self.update_matrix_operation)
        self.rebuild_matrix_fields()

        self.matrix_result = self.result_label("Result appears here.")
        box.pack_start(self.matrix_result, False, False, 0)
        self.add_button(box, "Calculate matrix", self.on_matrix_operation)
        return box

    def rebuild_matrix_fields(self, *_args) -> None:
        size = 2 if self.matrix_size.get_active() == 0 else 3
        self.matrix_entries: dict[str, list[list[Gtk.Entry]]] = {"A": [], "B": []}
        for name, frame in (("A", self.matrix_a_frame), ("B", self.matrix_b_frame)):
            old_child = frame.get_child()
            if old_child:
                frame.remove(old_child)
            contents = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
            contents.set_border_width(12)
            heading = Gtk.Label(label=f"Matrix {name}", xalign=0)
            heading.get_style_context().add_class("heading")
            contents.pack_start(heading, False, False, 0)
            grid = Gtk.Grid(column_spacing=6, row_spacing=6)
            contents.pack_start(grid, False, False, 0)
            for row in range(size):
                entries = []
                for column in range(size):
                    entry = Gtk.Entry()
                    entry.set_width_chars(7)
                    entry.set_alignment(1)
                    entry.set_text("1" if row == column else "0")
                    entry.set_input_purpose(Gtk.InputPurpose.NUMBER)
                    entry.connect("changed", self.update_matrix_typing)
                    grid.attach(entry, column, row, 1, 1)
                    entries.append(entry)
                self.matrix_entries[name].append(entries)
            frame.add(contents)
            contents.show_all()
        self.update_matrix_operation()
        self.update_matrix_typing()

    def update_matrix_operation(self, *_args) -> None:
        if not hasattr(self, "matrix_b_frame"):
            return
        operation = self.matrix_operation.get_active_text()
        self.matrix_b_frame.set_visible(operation in ("A + B", "A − B", "A × B"))

    def update_matrix_typing(self, *_args) -> None:
        if not hasattr(self, "matrix_entries"):
            return
        matrices = []
        for name in ("A", "B"):
            rows = [
                "[" + ", ".join(entry.get_text() or "□" for entry in row) + "]"
                for row in self.matrix_entries[name]
            ]
            matrices.append(f"{name} = " + " ".join(rows))
        self.matrix_typing.set_text("Typing: " + "    ".join(matrices))

    def read_matrix(self, name: str) -> list[list[float]]:
        values = []
        for row in self.matrix_entries[name]:
            result_row = []
            for entry in row:
                value = float(ExpressionParser(entry.get_text(), degrees=self.degrees).parse())
                if not math.isfinite(value):
                    raise ValueError("Matrix entries must be finite numbers.")
                result_row.append(value)
            values.append(result_row)
        return values

    def on_matrix_operation(self, *_args) -> None:
        try:
            operation = self.matrix_operation.get_active_text()
            matrix_a = self.read_matrix("A")
            matrix_b = self.read_matrix("B") if operation in ("A + B", "A − B", "A × B") else []
            self.matrix_result.set_text(matrix_operation(operation, matrix_a, matrix_b))
        except (ValueError, OverflowError, ZeroDivisionError) as error:
            self.matrix_result.set_text(str(error))


def evaluate_numeric_variable(source: str, variable: str, value: float, degrees: bool) -> float:
    tokens = tokenize(source)
    position = 0

    def peek():
        return tokens[position] if position < len(tokens) else None

    def accept(symbol):
        nonlocal position
        if peek() and peek()[1] == symbol:
            position += 1
            return True
        return False

    def expression():
        result = term()
        while peek() and peek()[1] in ("+", "-"):
            operator = peek()[1]
            nonlocal_position()
            right = term()
            result = result + right if operator == "+" else result - right
        return result

    def nonlocal_position():
        nonlocal position
        position += 1

    def term():
        result = unary()
        while True:
            if accept("*"):
                result *= unary()
            elif accept("/"):
                divisor = unary()
                if divisor == 0:
                    raise ValueError("Cannot divide by zero.")
                result /= divisor
            elif peek() and (peek()[0] in ("number", "identifier") or peek()[1] == "("):
                result *= unary()
            else:
                return result

    def unary():
        if accept("+"):
            return unary()
        if accept("-"):
            return -unary()
        return power()

    def power():
        result = postfix()
        if accept("^"):
            try:
                result = result**unary()
            except (OverflowError, ValueError, ZeroDivisionError) as error:
                raise ValueError("This power is outside the supported range.") from error
            if isinstance(result, complex) or not math.isfinite(result):
                raise ValueError("This power does not have a finite real result.")
        return result

    def postfix():
        result = primary()
        while True:
            if accept("%"):
                result /= 100
            elif accept("!"):
                if not float(result).is_integer() or not 0 <= result <= 170:
                    raise ValueError("Factorial needs a whole number from 0 to 170.")
                result = math.factorial(int(result))
            else:
                return result

    def primary():
        nonlocal position
        token = peek()
        if not token:
            raise ValueError("Complete the expression.")
        position += 1
        kind, name = token
        if kind == "number":
            return float(name)
        if name == "(":
            result = expression()
            if not accept(")"):
                raise ValueError("Missing closing parenthesis.")
            return result
        if kind != "identifier":
            raise ValueError("Check the expression.")
        if name == variable:
            return value
        if name == "pi":
            return math.pi
        if name == "e":
            return math.e
        if name not in FUNCTIONS:
            raise ValueError(f"Unknown function or variable: {name}")
        if not accept("("):
            raise ValueError(f"Add parentheses after {name}.")
        argument = expression()
        if not accept(")"):
            raise ValueError("Missing closing parenthesis.")
        scale = math.pi / 180 if degrees else 1
        funcs = {
            "sin": lambda x: math.sin(x * scale),
            "cos": lambda x: math.cos(x * scale),
            "tan": lambda x: math.tan(x * scale),
            "asin": lambda x: math.asin(x) / scale,
            "acos": lambda x: math.acos(x) / scale,
            "atan": lambda x: math.atan(x) / scale,
            "sqrt": math.sqrt,
            "log": math.log10,
            "ln": math.log,
            "abs": abs,
        }
        return funcs[name](argument)

    result = expression()
    if position != len(tokens):
        raise ValueError("Check the expression format.")
    return result


def main() -> None:
    window = CalcWindow()
    window.connect("destroy", Gtk.main_quit)
    window.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()
