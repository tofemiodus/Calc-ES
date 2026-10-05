(() => {
  "use strict";

  const expressionElement = document.querySelector("#expression");
  const resultElement = document.querySelector("#result");
  const historyElement = document.querySelector("#history-list");
  const memoryIndicator = document.querySelector("#memory-indicator");
  const angleLabel = document.querySelector("#angle-mode");
  const statusMessage = document.querySelector("#status-message");
  const equationType = document.querySelector("#equation-type");
  const equationInputs = document.querySelector("#equation-inputs");
  const solverResult = document.querySelector("#solver-result");
  const solverHint = document.querySelector("#solver-hint");
  const workbenchMode = document.querySelector("#workbench-mode");
  const equationTool = document.querySelector("#equation-tool");
  const polynomialTool = document.querySelector("#polynomial-tool");
  const factorTool = document.querySelector("#factor-tool");
  const graphTool = document.querySelector("#graph-tool");
  const fractionTool = document.querySelector("#fraction-tool");
  const countingTool = document.querySelector("#counting-tool");
  const graphCanvas = document.querySelector("#graph-canvas");
  const polynomialResult = document.querySelector("#polynomial-result");
  const factorResult = document.querySelector("#factor-result");
  const graphResult = document.querySelector("#graph-result");
  const fractionResult = document.querySelector("#fraction-result");
  const countingResult = document.querySelector("#counting-result");
  const history = [];
  let expression = "";
  let answer = 0;
  let memory = null;
  let degrees = true;
  let justCalculated = false;

  function formatNumber(value) {
    if (!Number.isFinite(value)) throw new Error("Result is outside the supported range");
    if (Object.is(value, -0)) value = 0;
    if (Math.abs(value) >= 1e12 || (Math.abs(value) > 0 && Math.abs(value) < 1e-8)) {
      return value.toExponential(8).replace(/\.?0+e/, "e");
    }
    return Number(value.toPrecision(12)).toString();
  }

  function tokenize(source) {
    const tokens = [];
    let remaining = source.replaceAll("×", "*").replaceAll("÷", "/").replaceAll("−", "-").trim();

    while (remaining.length) {
      const whitespace = remaining.match(/^\s+/);
      if (whitespace) {
        remaining = remaining.slice(whitespace[0].length);
        continue;
      }
      const number = remaining.match(/^(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?/);
      if (number) {
        tokens.push({ type: "number", value: Number(number[0]) });
        remaining = remaining.slice(number[0].length);
        continue;
      }
      const identifier = remaining.match(/^[a-zA-Z]+/);
      if (identifier) {
        tokens.push({ type: "identifier", value: identifier[0].toLowerCase() });
        remaining = remaining.slice(identifier[0].length);
        continue;
      }
      if ("+-*/^()%!".includes(remaining[0])) {
        tokens.push({ type: "symbol", value: remaining[0] });
        remaining = remaining.slice(1);
        continue;
      }
      throw new Error("Unsupported character");
    }

    return tokens;
  }

  function evaluate(source, variableValue = null, variableName = "x") {
    const tokens = tokenize(source);
    let position = 0;
    const functions = new Set(["sin", "cos", "tan", "asin", "acos", "atan", "sqrt", "log", "ln", "abs"]);

    const peek = () => tokens[position];
    const take = () => tokens[position++];
    const accept = (symbol) => {
      if (peek()?.value === symbol) {
        position++;
        return true;
      }
      return false;
    };

    function parseExpression() {
      let value = parseTerm();
      while (peek()?.value === "+" || peek()?.value === "-") {
        const operator = take().value;
        const right = parseTerm();
        value = operator === "+" ? value + right : value - right;
      }
      return value;
    }

    function startsImplicitTerm(token) {
      return token?.type === "number" || token?.type === "identifier" || token?.value === "(";
    }

    function parseTerm() {
      let value = parseUnary();
      while (true) {
        if (accept("*")) {
          value *= parseUnary();
        } else if (accept("/")) {
          const divisor = parseUnary();
          if (divisor === 0) throw new Error("Cannot divide by zero");
          value /= divisor;
        } else if (startsImplicitTerm(peek())) {
          value *= parseUnary();
        } else {
          return value;
        }
      }
    }

    function parseUnary() {
      if (accept("+")) return parseUnary();
      if (accept("-")) return -parseUnary();
      return parsePower();
    }

    function parsePower() {
      const value = parsePostfix();
      if (accept("^")) return value ** parseUnary();
      return value;
    }

    function parsePostfix() {
      let value = parsePrimary();
      while (true) {
        if (accept("%")) {
          value /= 100;
        } else if (accept("!")) {
          if (!Number.isInteger(value) || value < 0 || value > 170) {
            throw new Error("Factorial needs a whole number from 0 to 170");
          }
          let factorial = 1;
          for (let i = 2; i <= value; i++) factorial *= i;
          value = factorial;
        } else {
          return value;
        }
      }
    }

    function parsePrimary() {
      const token = take();
      if (!token) throw new Error("Enter a number or expression");
      if (token.type === "number") return token.value;

      if (token.value === "(") {
        const value = parseExpression();
        if (!accept(")")) throw new Error("Missing closing parenthesis");
        return value;
      }

      if (token.type !== "identifier") throw new Error("Check the expression");
      if (token.value === variableName && variableValue !== null) return variableValue;
      if (token.value === "pi") return Math.PI;
      if (token.value === "e") return Math.E;
      if (!functions.has(token.value)) throw new Error(`Unknown function: ${token.value}`);
      if (!accept("(")) throw new Error(`Add parentheses after ${token.value}`);
      const input = parseExpression();
      if (!accept(")")) throw new Error("Missing closing parenthesis");
      return applyFunction(token.value, input);
    }

    function applyFunction(name, value) {
      const angle = degrees ? Math.PI / 180 : 1;
      switch (name) {
        case "sin": return Math.sin(value * angle);
        case "cos": return Math.cos(value * angle);
        case "tan":
          if (Math.abs(Math.cos(value * angle)) < 1e-14) throw new Error("Tangent is undefined at this angle");
          return Math.tan(value * angle);
        case "asin":
          if (value < -1 || value > 1) throw new Error("Inverse sine needs a value from −1 to 1");
          return Math.asin(value) / angle;
        case "acos":
          if (value < -1 || value > 1) throw new Error("Inverse cosine needs a value from −1 to 1");
          return Math.acos(value) / angle;
        case "atan": return Math.atan(value) / angle;
        case "sqrt":
          if (value < 0) throw new Error("Square root needs a non-negative value");
          return Math.sqrt(value);
        case "log":
          if (value <= 0) throw new Error("Logarithm needs a positive value");
          return Math.log10(value);
        case "ln":
          if (value <= 0) throw new Error("Natural logarithm needs a positive value");
          return Math.log(value);
        case "abs": return Math.abs(value);
        default: throw new Error("Unknown function");
      }
    }

    if (!tokens.length) throw new Error("Enter a number or expression");
    const value = parseExpression();
    if (position !== tokens.length) throw new Error("Check the expression");
    if (!Number.isFinite(value)) throw new Error("Result is outside the supported range");
    return value;
  }

  function render() {
    expressionElement.textContent = expression;
    resultElement.classList.remove("error");
    if (!expression) {
      resultElement.textContent = "0";
      return;
    }
    try {
      resultElement.textContent = formatNumber(evaluate(expression));
    } catch {
      resultElement.textContent = " ";
    }
  }

  function showError(message) {
    resultElement.textContent = message;
    resultElement.classList.add("error");
  }

  function makePolynomial(source, degreeLimit = 2, variableNames = ["x", "y"]) {
    const tokens = tokenize(source);
    let position = 0;
    const constant = (value) => new Map([["0,0", value]]);
    const variable = (name) => {
      const variableIndex = variableNames.indexOf(name);
      if (variableIndex === -1) throw new Error(`Use ${variableNames.join(" and ")} as the variable${variableNames.length > 1 ? "s" : ""}`);
      return new Map([[variableIndex === 0 ? "1,0" : "0,1", 1]]);
    };
    const readTerm = (polynomial, key) => polynomial.get(key) ?? 0;
    const combine = (left, right, sign = 1) => {
      const result = new Map(left);
      for (const [key, value] of right) {
        const sum = (result.get(key) ?? 0) + sign * value;
        if (Math.abs(sum) < 1e-12) result.delete(key);
        else result.set(key, sum);
      }
      return result;
    };
    const multiply = (left, right) => {
      const result = new Map();
      for (const [leftKey, leftValue] of left) {
        const [leftX, leftY] = leftKey.split(",").map(Number);
        for (const [rightKey, rightValue] of right) {
          const [rightX, rightY] = rightKey.split(",").map(Number);
          if (leftX + leftY + rightX + rightY > degreeLimit) {
            throw new Error(`Polynomials are limited to degree ${degreeLimit}`);
          }
          const key = `${leftX + rightX},${leftY + rightY}`;
          result.set(key, (result.get(key) ?? 0) + leftValue * rightValue);
        }
      }
      return result;
    };
    const peek = () => tokens[position];
    const take = () => tokens[position++];
    const accept = (symbol) => {
      if (peek()?.value === symbol) {
        position++;
        return true;
      }
      return false;
    };

    function parseExpression() {
      let value = parseTerm();
      while (peek()?.value === "+" || peek()?.value === "-") {
        const sign = take().value === "+" ? 1 : -1;
        value = combine(value, parseTerm(), sign);
      }
      return value;
    }

    function parseTerm() {
      let value = parseUnary();
      while (true) {
        if (accept("*")) value = multiply(value, parseUnary());
        else if (accept("/")) {
          const divisor = parseUnary();
          if (divisor.size !== 1 || !divisor.has("0,0") || divisor.get("0,0") === 0) {
            throw new Error("Division is only supported by a non-zero number");
          }
          const number = divisor.get("0,0");
          value = new Map([...value].map(([key, coefficient]) => [key, coefficient / number]));
        } else if (peek()?.type === "number" || peek()?.type === "identifier" || peek()?.value === "(") {
          value = multiply(value, parseUnary());
        } else return value;
      }
    }

    function parseUnary() {
      if (accept("+")) return parseUnary();
      if (accept("-")) return new Map([...parseUnary()].map(([key, value]) => [key, -value]));
      return parsePower();
    }

    function parsePower() {
      const value = parsePrimary();
      if (!accept("^")) return value;
      const exponent = parseUnary();
      if ([...exponent.keys()].some((key) => key !== "0,0")) {
        throw new Error(`Use a whole-number power from 0 to ${degreeLimit}`);
      }
      const power = readTerm(exponent, "0,0");
      if (!Number.isInteger(power) || power < 0 || power > degreeLimit) {
        throw new Error(`Use a whole-number power from 0 to ${degreeLimit}`);
      }
      let result = constant(1);
      for (let index = 0; index < power; index++) result = multiply(result, value);
      return result;
    }

    function parsePrimary() {
      const token = take();
      if (!token) throw new Error("Complete each equation before solving");
      if (token.type === "number") return constant(token.value);
      if (token.type === "identifier") {
        if (token.value.length !== 1) throw new Error("Use single-letter variables");
        return variable(token.value);
      }
      if (token.value === "(") {
        const value = parseExpression();
        if (!accept(")")) throw new Error("Missing closing parenthesis");
        return value;
      }
      throw new Error("Check the equation format");
    }

    if (!tokens.length) throw new Error("Enter an equation before solving");
    const polynomial = parseExpression();
    if (position !== tokens.length) throw new Error("Check the equation format");
    return polynomial;
  }

  function variablesIn(source) {
    return tokenize(source)
      .filter((token) => token.type === "identifier" && token.value.length === 1)
      .map((token) => token.value)
      .filter((name, index, names) => names.indexOf(name) === index);
  }

  function parseEquation(source, variableNames = ["x"]) {
    const sides = source.split("=");
    if (sides.length !== 2 || !sides[0].trim() || !sides[1].trim()) {
      throw new Error("Write each equation with one equals sign, e.g. 2x + 3 = 7");
    }
    return combinePolynomials(
      makePolynomial(sides[0], 2, variableNames),
      makePolynomial(sides[1], 2, variableNames),
      -1
    );
  }

  function combinePolynomials(left, right, sign) {
    const result = new Map(left);
    for (const [key, value] of right) {
      const sum = (result.get(key) ?? 0) + sign * value;
      if (Math.abs(sum) < 1e-12) result.delete(key);
      else result.set(key, sum);
    }
    return result;
  }

  function solveLinear(polynomial, variable = "x") {
    if ([...polynomial.keys()].some((key) => key === "0,1" || key === "1,1" || key === "0,2" || key === "2,0")) {
      throw new Error("A linear equation can only contain one variable to the first power");
    }
    const coefficient = polynomial.get("1,0") ?? 0;
    const value = -(polynomial.get("0,0") ?? 0);
    if (coefficient === 0) return value === 0 ? `Every value of ${variable} is a solution.` : "There is no solution.";
    return `${variable} = ${formatNumber(value / coefficient)}`;
  }

  function solveQuadratic(polynomial, variable = "x") {
    if ([...polynomial.keys()].some((key) => key === "0,1" || key === "1,1" || key === "0,2")) {
      throw new Error("A quadratic equation can only contain one variable");
    }
    const a = polynomial.get("2,0") ?? 0;
    const b = polynomial.get("1,0") ?? 0;
    const c = polynomial.get("0,0") ?? 0;
    if (a === 0) return solveLinear(polynomial, variable);
    const discriminant = b * b - 4 * a * c;
    if (discriminant < -1e-12) return "No real solutions.";
    if (Math.abs(discriminant) <= 1e-12) return `${variable} = ${formatNumber(-b / (2 * a))}`;
    const root = Math.sqrt(discriminant);
    const first = (-b - root) / (2 * a);
    const second = (-b + root) / (2 * a);
    return `${variable} = ${formatNumber(first)} or ${variable} = ${formatNumber(second)}`;
  }

  function solveSimultaneous(first, second, variables = ["x", "y"]) {
    const equations = [first, second];
    for (const polynomial of equations) {
      if ([...polynomial.keys()].some((key) => key === "1,1" || key === "0,2" || key === "2,0")) {
        throw new Error("Simultaneous equations must be linear");
      }
    }
    const [a, b, c] = [first.get("1,0") ?? 0, first.get("0,1") ?? 0, -(first.get("0,0") ?? 0)];
    const [d, e, f] = [second.get("1,0") ?? 0, second.get("0,1") ?? 0, -(second.get("0,0") ?? 0)];
    const determinant = a * e - b * d;
    if (Math.abs(determinant) < 1e-12) {
      if (Math.abs(a * f - c * d) < 1e-12 && Math.abs(b * f - c * e) < 1e-12) {
        return "These equations have infinitely many solutions.";
      }
      return "These equations have no solution.";
    }
    return `${variables[0]} = ${formatNumber((c * e - b * f) / determinant)}, ${variables[1]} = ${formatNumber((a * f - c * d) / determinant)}`;
  }

  function polynomialCoefficients(source) {
    const variables = variablesIn(source);
    if (variables.length > 1) throw new Error("A polynomial must use only one variable letter");
    const variable = variables[0] ?? "x";
    const polynomial = makePolynomial(source, 8, [variable]);
    if ([...polynomial.keys()].some((key) => key.split(",")[1] !== "0")) {
      throw new Error(`Polynomials must use only ${variable}`);
    }
    const coefficients = Array(9).fill(0);
    for (const [key, value] of polynomial) {
      const degree = Number(key.split(",")[0]);
      coefficients[degree] = value;
    }
    if (coefficients.some((coefficient) => !Number.isFinite(coefficient))) {
      throw new Error("Polynomial coefficients must be finite numbers");
    }
    return { coefficients: trimCoefficients(coefficients), variable };
  }

  function trimCoefficients(coefficients) {
    const result = [...coefficients];
    while (result.length > 1 && Math.abs(result.at(-1)) < 1e-12) result.pop();
    return result;
  }

  function evaluatePolynomial(coefficients, x) {
    let value = 0;
    for (let degree = coefficients.length - 1; degree >= 0; degree--) {
      value = value * x + coefficients[degree];
    }
    return value;
  }

  function polynomialTolerance(coefficients, x) {
    const magnitude = coefficients.reduce((sum, coefficient, degree) =>
      sum + Math.abs(coefficient) * Math.abs(x) ** degree, 0);
    return Math.max(1, magnitude) * 1e-10;
  }

  function findRealRoots(input) {
    const coefficients = trimCoefficients(input);
    const degree = coefficients.length - 1;
    if (degree === 0) return [];
    if (degree === 1) return [-coefficients[0] / coefficients[1]];

    const derivative = coefficients.slice(1).map((coefficient, index) => coefficient * (index + 1));
    const criticalPoints = findRealRoots(derivative).sort((a, b) => a - b);
    const leading = Math.abs(coefficients[degree]);
    const bound = 1 + Math.max(...coefficients.slice(0, degree).map((coefficient) => Math.abs(coefficient) / leading));
    if (!Number.isFinite(bound)) throw new Error("This polynomial is too large to solve reliably");
    const points = [-bound, ...criticalPoints.filter((point) => point > -bound && point < bound), bound];
    const roots = [];

    for (const point of criticalPoints) {
      if (Math.abs(evaluatePolynomial(coefficients, point)) <= polynomialTolerance(coefficients, point)) {
        roots.push(point);
      }
    }
    for (let index = 0; index < points.length - 1; index++) {
      let low = points[index];
      let high = points[index + 1];
      let lowValue = evaluatePolynomial(coefficients, low);
      let highValue = evaluatePolynomial(coefficients, high);
      if (!Number.isFinite(lowValue) || !Number.isFinite(highValue) || lowValue === 0 || highValue === 0 ||
          Math.sign(lowValue) === Math.sign(highValue)) continue;
      for (let iteration = 0; iteration < 100; iteration++) {
        const middle = (low + high) / 2;
        const middleValue = evaluatePolynomial(coefficients, middle);
        if (middleValue === 0) {
          low = middle;
          high = middle;
          break;
        }
        if (Math.sign(middleValue) === Math.sign(lowValue)) {
          low = middle;
          lowValue = middleValue;
        } else {
          high = middle;
          highValue = middleValue;
        }
      }
      roots.push((low + high) / 2);
    }
    return roots
      .filter(Number.isFinite)
      .sort((a, b) => a - b)
      .filter((root, index, all) => index === 0 || Math.abs(root - all[index - 1]) > 1e-7 * Math.max(1, Math.abs(root)));
  }

  function formatPolynomial(coefficients) {
    const terms = [];
    for (let degree = coefficients.length - 1; degree >= 0; degree--) {
      const coefficient = coefficients[degree];
      if (Math.abs(coefficient) < 1e-10) continue;
      const magnitude = Math.abs(coefficient);
      const factor = degree === 0 || magnitude !== 1 ? formatNumber(magnitude) : "";
      const variable = degree === 0 ? "" : `x${degree > 1 ? `^${degree}` : ""}`;
      const term = `${factor}${variable}`;
      if (!terms.length) terms.push(coefficient < 0 ? `-${term}` : term);
      else terms.push(`${coefficient < 0 ? " - " : " + "}${term}`);
    }
    return terms.join("") || "0";
  }

  function solvePolynomial() {
    try {
      const { coefficients, variable } = polynomialCoefficients(document.querySelector("#polynomial-expression").value);
      if (coefficients.length === 1) {
        polynomialResult.textContent = coefficients[0] === 0
          ? `Every real number is a root for ${variable}.`
          : "This non-zero constant has no roots.";
      } else {
        const roots = findRealRoots(coefficients);
        polynomialResult.textContent = roots.length
          ? `Real roots for ${variable}: ${roots.map((root) => `${variable} = ${formatNumber(root)}`).join(", ")}`
          : "No real roots.";
      }
      polynomialResult.classList.remove("error");
    } catch (error) {
      polynomialResult.textContent = error.message || "Unable to solve this polynomial";
      polynomialResult.classList.add("error");
    }
  }

  function divideByRoot(coefficients, root) {
    const degree = coefficients.length - 1;
    const quotient = Array(degree).fill(0);
    quotient[degree - 1] = coefficients[degree];
    for (let index = degree - 2; index >= 0; index--) {
      quotient[index] = coefficients[index + 1] + root * quotient[index + 1];
    }
    const remainder = coefficients[0] + root * quotient[0];
    if (Math.abs(remainder) > polynomialTolerance(coefficients, root) * 10) {
      throw new Error("Numerical factorization did not converge; try simpler coefficients");
    }
    return trimCoefficients(quotient);
  }

  function factorPolynomial() {
    try {
      const { coefficients, variable } = polynomialCoefficients(document.querySelector("#factor-expression").value);
      if (coefficients.length === 1) {
        factorResult.textContent = `Constant polynomial: ${formatNumber(coefficients[0])}.`;
        factorResult.classList.remove("error");
        return;
      }
      const originalDegree = coefficients.length - 1;
      let remainder = [...coefficients];
      const factors = [];
      for (const root of findRealRoots(coefficients)) {
        while (remainder.length > 1 &&
          Math.abs(evaluatePolynomial(remainder, root)) <= polynomialTolerance(remainder, root) * 10) {
          factors.push(`(x ${root < 0 ? "+" : "−"} ${formatNumber(Math.abs(root))})`);
          remainder = divideByRoot(remainder, root);
        }
      }
      const leading = coefficients.at(-1);
      const factorText = [
        Math.abs(leading) === 1 ? (leading < 0 ? "−1" : "") : formatNumber(leading),
        ...factors.map((factor) => factor.replaceAll("x", variable)),
        ...(remainder.length > 1 ? [`(${formatPolynomial(remainder).replaceAll("x", variable)})`] : [])
      ].filter(Boolean).join(" ");
      factorResult.textContent = `${formatPolynomial(coefficients).replaceAll("x", variable)} = ${factorText || "1"}`;
      factorResult.classList.remove("error");
    } catch (error) {
      factorResult.textContent = error.message || "Unable to factor this polynomial";
      factorResult.classList.add("error");
    }
  }

  function plotGraph() {
    const context = graphCanvas.getContext("2d");
    if (!context) {
      graphResult.textContent = "Graphing is unavailable in this browser.";
      graphResult.classList.add("error");
      return;
    }
    const source = document.querySelector("#graph-expression").value.trim();
    const variable = document.querySelector("#graph-variable").value.trim().toLowerCase();
    const xMin = Number(document.querySelector("#graph-x-min").value);
    const xMax = Number(document.querySelector("#graph-x-max").value);
    if (!/^[a-z]$/.test(variable)) {
      graphResult.textContent = "Choose a single letter for the graph variable.";
      graphResult.classList.add("error");
      return;
    }
    document.querySelector("#graph-from-label").textContent = `${variable} from`;
    if (!source || !Number.isFinite(xMin) || !Number.isFinite(xMax) || xMin >= xMax ||
        Math.abs(xMin) > 1e6 || Math.abs(xMax) > 1e6 || xMax - xMin > 200) {
      graphResult.textContent = "Enter a function and an increasing x-range within ±1,000,000 and at most 200 units wide.";
      graphResult.classList.add("error");
      return;
    }
    const width = graphCanvas.width;
    const height = graphCanvas.height;
    const yMin = -10;
    const yMax = 10;
    const xPixel = (x) => (x - xMin) / (xMax - xMin) * width;
    const yPixel = (y) => height - (y - yMin) / (yMax - yMin) * height;
    context.clearRect(0, 0, width, height);
    context.fillStyle = getComputedStyle(document.body).getPropertyValue("--panel-raised").trim();
    context.fillRect(0, 0, width, height);
    context.strokeStyle = getComputedStyle(document.body).getPropertyValue("--line").trim();
    context.lineWidth = 1;
    context.font = "12px system-ui, sans-serif";
    context.fillStyle = getComputedStyle(document.body).getPropertyValue("--muted").trim();
    for (let tick = Math.ceil(xMin); tick <= xMax; tick++) {
      const x = xPixel(tick);
      context.beginPath();
      context.moveTo(x, 0);
      context.lineTo(x, height);
      context.stroke();
      if (tick % 2 === 0) context.fillText(String(tick), x + 3, Math.min(height - 5, Math.max(14, yPixel(0) + 16)));
    }
    for (let tick = yMin; tick <= yMax; tick += 2) {
      const y = yPixel(tick);
      context.beginPath();
      context.moveTo(0, y);
      context.lineTo(width, y);
      context.stroke();
      if (tick !== 0) context.fillText(String(tick), 5, y - 3);
    }
    context.strokeStyle = getComputedStyle(document.body).getPropertyValue("--muted").trim();
    context.lineWidth = 1.5;
    if (xMin <= 0 && xMax >= 0) {
      context.beginPath();
      context.moveTo(xPixel(0), 0);
      context.lineTo(xPixel(0), height);
      context.stroke();
    }
    if (yMin <= 0 && yMax >= 0) {
      context.beginPath();
      context.moveTo(0, yPixel(0));
      context.lineTo(width, yPixel(0));
      context.stroke();
    }

    context.strokeStyle = getComputedStyle(document.body).getPropertyValue("--accent").trim();
    context.lineWidth = 2.5;
    context.beginPath();
    let drawing = false;
    for (let pixel = 0; pixel <= width; pixel++) {
      const x = xMin + pixel / width * (xMax - xMin);
      let y;
      try {
        y = evaluate(source, x, variable);
      } catch {
        drawing = false;
        continue;
      }
      if (!Number.isFinite(y) || y < yMin - 20 || y > yMax + 20) {
        drawing = false;
        continue;
      }
      const py = yPixel(y);
      if (drawing) context.lineTo(pixel, py);
      else {
        context.moveTo(pixel, py);
        drawing = true;
      }
    }
    context.stroke();
    graphResult.textContent = `Plotted f(${variable}) = ${source} for ${variable} from ${formatNumber(xMin)} to ${formatNumber(xMax)}. The visible y-range is −10 to 10.`;
    graphResult.classList.remove("error");
  }

  function renderWorkbenchMode() {
    const mode = workbenchMode.value;
    equationTool.hidden = mode !== "equations";
    polynomialTool.hidden = mode !== "polynomial";
    factorTool.hidden = mode !== "factor";
    graphTool.hidden = mode !== "graph";
    fractionTool.hidden = mode !== "fraction";
    countingTool.hidden = mode !== "counting";
    if (mode === "graph") plotGraph();
  }

  function gcd(left, right) {
    let a = left < 0n ? -left : left;
    let b = right < 0n ? -right : right;
    while (b !== 0n) [a, b] = [b, a % b];
    return a;
  }

  function fractionFromDecimal(source) {
    const match = source.match(/^([+-]?)(\d*)(?:\.(\d*))?$/);
    if (!match || (!match[2] && !match[3])) throw new Error("Enter a valid decimal number or fraction.");
    const fractionDigits = match[3] ?? "";
    const digits = `${match[2] || "0"}${fractionDigits}`;
    let numerator = BigInt(digits || "0");
    if (match[1] === "-") numerator = -numerator;
    let denominator = 10n ** BigInt(fractionDigits.length);
    const divisor = gcd(numerator, denominator);
    return [numerator / divisor, denominator / divisor];
  }

  function convertFraction() {
    try {
      const source = document.querySelector("#fraction-input").value.trim();
      if (source.length > 300) throw new Error("Enter a value with no more than 300 characters.");
      let numerator;
      let denominator;
      if (source.includes("/")) {
        const parts = source.split("/");
        if (parts.length !== 2 || !/^[+-]?\d+$/.test(parts[0].trim()) || !/^[+-]?\d+$/.test(parts[1].trim())) {
          throw new Error("Enter a fraction as two whole numbers, e.g. 3/8.");
        }
        numerator = BigInt(parts[0].trim());
        denominator = BigInt(parts[1].trim());
        if (denominator === 0n) throw new Error("The denominator cannot be zero.");
        if (denominator < 0n) {
          numerator = -numerator;
          denominator = -denominator;
        }
        const divisor = gcd(numerator, denominator);
        numerator /= divisor;
        denominator /= divisor;
      } else {
        [numerator, denominator] = fractionFromDecimal(source);
      }
      const decimal = Number(numerator) / Number(denominator);
      if (!Number.isFinite(decimal)) throw new Error("This value is outside the supported numeric range.");
      fractionResult.textContent = `${numerator}/${denominator} = ${formatNumber(decimal)}`;
      fractionResult.classList.remove("error");
    } catch (error) {
      fractionResult.textContent = error.message || "Unable to convert this value.";
      fractionResult.classList.add("error");
    }
  }

  function factorial(value) {
    let result = 1n;
    for (let factor = 2n; factor <= value; factor++) result *= factor;
    return result;
  }

  function calculateCounting() {
    const n = Number(document.querySelector("#count-n").value);
    const r = Number(document.querySelector("#count-r").value);
    if (!Number.isInteger(n) || !Number.isInteger(r) || n < 0 || r < 0 || r > n || n > 1000) {
      countingResult.textContent = "Enter whole numbers satisfying 0 ≤ r ≤ n ≤ 1000.";
      countingResult.classList.add("error");
      return;
    }
    const nBig = BigInt(n);
    const rBig = BigInt(r);
    const permutation = factorial(nBig) / factorial(nBig - rBig);
    let combination = 1n;
    for (let index = 1n; index <= (rBig < nBig - rBig ? rBig : nBig - rBig); index++) {
      combination = combination * (nBig - index + 1n) / index;
    }
    countingResult.textContent = `${n}P${r} = ${permutation.toString()}; ${n}C${r} = ${combination.toString()}`;
    countingResult.classList.remove("error");
  }

  function renderEquationInputs() {
    const type = equationType.value;
    const rows = type === "simultaneous"
      ? [["equation-one", "Equation 1", "2a + b = 5"], ["equation-two", "Equation 2", "a - b = 1"]]
      : [["equation-one", "Equation", type === "quadratic" ? "t^2 - 5t + 6 = 0" : "2t + 3 = 7"]];
    equationInputs.replaceChildren();
    for (const [id, labelText, placeholder] of rows) {
      const row = document.createElement("div");
      row.className = "equation-row";
      const label = document.createElement("label");
      label.htmlFor = id;
      label.textContent = labelText;
      const input = document.createElement("input");
      input.className = "equation-input";
      input.id = id;
      input.type = "text";
      input.autocomplete = "off";
      input.spellcheck = false;
      input.placeholder = placeholder;
      input.setAttribute("aria-label", labelText);
      row.append(label, input);
      equationInputs.append(row);
    }
    solverHint.textContent = type === "simultaneous"
      ? "Enter two linear equations using any two different letters, for example 2a + b = 5 and a - b = 1."
      : type === "quadratic"
        ? "Use any one letter as the unknown. For example, t^2 - 5t + 6 = 0."
        : "Use any one letter as the unknown. For example, 2t + 3 = 7.";
    solverResult.textContent = "Enter an equation to get started.";
    solverResult.classList.remove("error");
  }

  function solveEquations() {
    try {
      const firstSource = document.querySelector("#equation-one").value;
      const equationSources = [firstSource];
      if (equationType.value === "simultaneous") {
        equationSources.push(document.querySelector("#equation-two").value);
      }
      const variables = equationSources.flatMap(variablesIn)
        .filter((name, index, names) => names.indexOf(name) === index);
      if (equationType.value === "simultaneous") {
        if (variables.length !== 2) throw new Error("Simultaneous equations must use exactly two different letters.");
      } else if (variables.length > 1) {
        throw new Error("Use only one variable letter in this equation.");
      }
      const equationVariables = variables.length ? variables : equationType.value === "simultaneous" ? ["x", "y"] : ["x"];
      const first = parseEquation(firstSource, equationVariables);
      let solution;
      if (equationType.value === "simultaneous") {
        const second = parseEquation(equationSources[1], equationVariables);
        solution = solveSimultaneous(first, second, equationVariables);
      } else if (equationType.value === "quadratic") {
        solution = solveQuadratic(first, equationVariables[0]);
      } else {
        solution = solveLinear(first, equationVariables[0]);
      }
      solverResult.textContent = solution;
      solverResult.classList.remove("error");
    } catch (error) {
      solverResult.textContent = error.message || "Unable to solve these equations";
      solverResult.classList.add("error");
    }
  }

  function insert(value) {
    const isContinuation = ["+", "−", "×", "÷", "^", "%", "!", ")"].includes(value);
    if (justCalculated && !isContinuation) expression = "";
    justCalculated = false;
    expression += value;
    statusMessage.textContent = "";
    render();
  }

  function calculate() {
    if (!expression.trim()) return;
    try {
      answer = evaluate(expression);
      const formatted = formatNumber(answer);
      history.unshift({ expression, result: formatted });
      history.splice(12);
      renderHistory();
      resultElement.textContent = formatted;
      resultElement.classList.remove("error");
      justCalculated = true;
      statusMessage.textContent = "";
    } catch (error) {
      showError(error.message || "Unable to calculate this expression");
      statusMessage.textContent = "Check the expression and try again.";
      justCalculated = false;
    }
  }

  function renderHistory() {
    historyElement.replaceChildren();
    if (!history.length) {
      const empty = document.createElement("div");
      empty.className = "history-empty";
      empty.textContent = "Your calculations will appear here.";
      historyElement.append(empty);
      return;
    }
    for (const item of history) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "history-item";
      button.title = "Use this calculation again";
      const expressionText = document.createElement("span");
      expressionText.className = "history-expression";
      expressionText.textContent = item.expression;
      const resultText = document.createElement("span");
      resultText.className = "history-result";
      resultText.textContent = `= ${item.result}`;
      button.append(expressionText, resultText);
      button.addEventListener("click", () => {
        expression = item.expression;
        justCalculated = false;
        render();
      });
      historyElement.append(button);
    }
  }

  function currentValue() {
    if (justCalculated) return answer;
    return expression ? evaluate(expression) : 0;
  }

  document.querySelector(".controls").addEventListener("click", (event) => {
    const button = event.target.closest("button");
    if (!button) return;
    const { action, insert: insertion } = button.dataset;

    if (insertion !== undefined) {
      insert(insertion);
      return;
    }

    switch (action) {
      case "equals":
        calculate();
        break;
      case "clear":
        expression = "";
        justCalculated = false;
        statusMessage.textContent = "";
        render();
        break;
      case "delete":
        expression = justCalculated ? "" : expression.slice(0, -1);
        justCalculated = false;
        render();
        break;
      case "sign":
        if (justCalculated) {
          expression = `-(${formatNumber(answer)})`;
          justCalculated = false;
        } else if (expression) {
          expression = `-(${expression})`;
        } else {
          expression = "−";
        }
        render();
        break;
      case "angle":
        degrees = !degrees;
        angleLabel.textContent = degrees ? "DEG" : "RAD";
        button.textContent = degrees ? "DEG" : "RAD";
        statusMessage.textContent = `Angle mode: ${degrees ? "degrees" : "radians"}`;
        render();
        break;
      case "memory-clear":
        memory = null;
        memoryIndicator.hidden = true;
        statusMessage.textContent = "Memory cleared";
        break;
      case "memory-recall":
        if (memory === null) {
          statusMessage.textContent = "Memory is empty";
        } else {
          insert(formatNumber(memory));
          statusMessage.textContent = "Memory recalled";
        }
        break;
      case "memory-add":
      case "memory-subtract":
        try {
          const value = currentValue();
          memory = (memory ?? 0) + (action === "memory-add" ? value : -value);
          memoryIndicator.hidden = false;
          statusMessage.textContent = action === "memory-add" ? "Added to memory" : "Subtracted from memory";
        } catch {
          statusMessage.textContent = "Enter a valid expression first";
        }
        break;
      default:
        break;
    }
  });

  document.querySelector("#clear-history").addEventListener("click", () => {
    history.length = 0;
    renderHistory();
  });

  document.querySelector("#theme-toggle").addEventListener("click", () => {
    document.body.classList.toggle("light-theme");
  });

  equationType.addEventListener("change", renderEquationInputs);
  workbenchMode.addEventListener("change", renderWorkbenchMode);
  document.querySelector("#solve-equations").addEventListener("click", solveEquations);
  document.querySelector("#solve-polynomial").addEventListener("click", solvePolynomial);
  document.querySelector("#factor-polynomial").addEventListener("click", factorPolynomial);
  document.querySelector("#plot-graph").addEventListener("click", plotGraph);
  document.querySelector("#convert-fraction").addEventListener("click", convertFraction);
  document.querySelector("#calculate-counting").addEventListener("click", calculateCounting);
  for (const id of ["polynomial-expression", "factor-expression"]) {
    document.querySelector(`#${id}`).addEventListener("keydown", (event) => {
      if (event.key === "Enter") id === "polynomial-expression" ? solvePolynomial() : factorPolynomial();
    });
  }
  for (const id of ["graph-expression", "graph-x-min", "graph-x-max"]) {
    document.querySelector(`#${id}`).addEventListener("keydown", (event) => {
      if (event.key === "Enter") plotGraph();
    });
  }
  document.querySelector("#fraction-input").addEventListener("keydown", (event) => {
    if (event.key === "Enter") convertFraction();
  });
  for (const id of ["count-n", "count-r"]) {
    document.querySelector(`#${id}`).addEventListener("keydown", (event) => {
      if (event.key === "Enter") calculateCounting();
    });
  }
  equationInputs.addEventListener("keydown", (event) => {
    if (event.key === "Enter") solveEquations();
  });

  document.addEventListener("keydown", (event) => {
    if (event.ctrlKey || event.metaKey || event.altKey) return;
    if (event.target instanceof Element && event.target.closest("input, textarea, select, [contenteditable='true']")) return;
    if (/^[0-9.]$/.test(event.key)) {
      insert(event.key);
    } else if (event.key === "+") {
      insert("+");
    } else if (event.key === "-") {
      insert("−");
    } else if (event.key === "*") {
      insert("×");
    } else if (event.key === "/") {
      event.preventDefault();
      insert("÷");
    } else if (event.key === "^" || event.key === "(" || event.key === ")" || event.key === "%") {
      insert(event.key);
    } else if (event.key === "!") {
      insert("!");
    } else if (event.key === "Enter" || event.key === "=") {
      event.preventDefault();
      calculate();
    } else if (event.key === "Backspace") {
      expression = justCalculated ? "" : expression.slice(0, -1);
      justCalculated = false;
      render();
    } else if (event.key === "Escape" || event.key === "Delete") {
      expression = "";
      justCalculated = false;
      statusMessage.textContent = "";
      render();
    }
  });

  renderEquationInputs();
  renderWorkbenchMode();
  render();
})();