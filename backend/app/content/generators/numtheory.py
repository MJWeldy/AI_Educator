import random
from collections import Counter
from math import gcd

from .base import ProblemInstance, generator, mc, numeric

PRIMES = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47]


def factorize(n: int) -> Counter:
    out: Counter = Counter()
    d = 2
    while n > 1:
        while n % d == 0:
            out[d] += 1
            n //= d
        d += 1
    return out


def factor_tex(n: int) -> str:
    parts = []
    for p, e in sorted(factorize(n).items()):
        parts.append(f"{p}^{{{e}}}" if e > 1 else str(p))
    return " \\times ".join(parts)


@generator("numtheory.divisibility")
def divisibility(rng: random.Random, difficulty: int) -> ProblemInstance:
    k = rng.choice([2, 3, 4, 5, 6, 9, 10][: 3 + difficulty * 2])
    hi = {1: 200, 2: 2000, 3: 20000}[difficulty]
    n = rng.randint(hi // 10, hi)
    divisible = n % k == 0
    return ProblemInstance(
        statement_md=f"Consider the number ${n:,}$.".replace(",", "{,}"),
        parts=[
            mc(rng, f"Is it divisible by ${k}$?", "yes" if divisible else "no",
               ["no" if divisible else "yes"]),
            numeric(f"What is the remainder when ${n:,}$ is divided by ${k}$?".replace(",", "{,}"), n % k),
        ],
        solution_md=f"${n} = {k} \\times {n // k} + {n % k}$, so the remainder is ${n % k}$.",
    )


@generator("numtheory.primes")
def primes(rng: random.Random, difficulty: int) -> ProblemInstance:
    lo, hi = {1: (2, 30), 2: (20, 60), 3: (40, 120)}[difficulty]
    candidates = [n for n in range(lo, hi)]
    prime_set = {n for n in candidates if all(n % p for p in range(2, int(n**0.5) + 1)) and n > 1}
    p = rng.choice(sorted(prime_set))
    composites = rng.sample(sorted(set(candidates) - prime_set - {1}), 3)
    return ProblemInstance(
        statement_md="Prime numbers have exactly two factors: 1 and themselves.",
        parts=[mc(rng, "Which of these is **prime**?", str(p), [str(c) for c in composites])],
        solution_md=(
            f"${p}$ is prime. The others factor: "
            + ", ".join(f"${c} = {factor_tex(c)}$" for c in composites)
            + "."
        ),
    )


@generator("numtheory.prime_factorization")
def prime_factorization(rng: random.Random, difficulty: int) -> ProblemInstance:
    k = {1: 2, 2: 3, 3: 4}[difficulty]
    n = 1
    for _ in range(k):
        n *= rng.choice(PRIMES[:6])
    while n < 12:
        n *= rng.choice(PRIMES[:4])
    factors = factorize(n)
    largest = max(factors)
    total_count = sum(factors.values())
    return ProblemInstance(
        statement_md=f"Find the prime factorization of ${n}$.",
        parts=[
            numeric("What is the **largest prime factor**?", largest),
            numeric("How many prime factors are there in total (counted with multiplicity)?", total_count),
        ],
        solution_md=f"${n} = {factor_tex(n)}$.",
    )


@generator("numtheory.gcf")
def gcf(rng: random.Random, difficulty: int) -> ProblemInstance:
    base = {1: 6, 2: 12, 3: 18}[difficulty]
    g = rng.choice([2, 3, 4, 6, base])
    a = g * rng.randint(2, 8)
    b = g * rng.randint(2, 8)
    while a == b:
        b = g * rng.randint(2, 8)
    ans = gcd(a, b)
    return ProblemInstance(
        statement_md=f"Find the greatest common factor of ${a}$ and ${b}$.",
        parts=[numeric("GCF:", ans)],
        solution_md=(
            f"${a} = {factor_tex(a)}$ and ${b} = {factor_tex(b)}$. "
            f"Take each shared prime with its smaller exponent: $\\gcd = {ans}$."
        ),
    )


@generator("numtheory.lcm")
def lcm_gen(rng: random.Random, difficulty: int) -> ProblemInstance:
    hi = {1: 10, 2: 15, 3: 25}[difficulty]
    a, b = rng.randint(3, hi), rng.randint(3, hi)
    while a == b:
        b = rng.randint(3, hi)
    ans = a * b // gcd(a, b)
    return ProblemInstance(
        statement_md=f"Find the least common multiple of ${a}$ and ${b}$.",
        parts=[numeric("LCM:", ans)],
        solution_md=(
            f"$\\operatorname{{lcm}}(a,b) = \\dfrac{{a \\times b}}{{\\gcd(a,b)}} "
            f"= \\dfrac{{{a} \\times {b}}}{{{gcd(a,b)}}} = {ans}$."
        ),
    )
