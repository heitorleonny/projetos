"""Expressão aritmética de uma métrica: analisada por um parser próprio, nunca `eval`.

Gramática (descida recursiva, precedência usual):

    expr   := termo (('+' | '-') termo)*
    termo  := fator (('*' | '/') fator)*
    fator  := '-' fator | numero | variavel | '(' expr ')'

Aceita `×` e `÷` como sinônimos de `*` e `/`, e vírgula ou ponto como separador
decimal. Variáveis só do catálogo fechado (`catalogo.VARIAVEIS`). Não há
chamada de função, atributo, indexação nem qualquer outro construto: o texto é
dado, e a árvore resultante só sabe somar, subtrair, multiplicar e dividir.

Limites duros (texto, nós e profundidade) evitam expressões patológicas. Na
avaliação, valor ausente ou divisão por zero produz `None` ("sem valor"), nunca
zero nem exceção.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

from app.metricas.catalogo import VARIAVEIS

LIMITE_TEXTO = 300
LIMITE_NOS = 60
LIMITE_PROFUNDIDADE = 12
LIMITE_NUMERO = 1e12


class ErroExpressao(ValueError):
    """Expressão fora da gramática ou do catálogo; mensagem legível para o gestor."""


@dataclass(frozen=True)
class Numero:
    valor: float


@dataclass(frozen=True)
class Var:
    nome: str


@dataclass(frozen=True)
class Negativo:
    no: "No"


@dataclass(frozen=True)
class Binario:
    op: str
    esq: "No"
    dir: "No"


No = Numero | Var | Negativo | Binario

_TOKEN = re.compile(r"\s*(?:(?P<num>\d+(?:[.,]\d+)?)|(?P<id>[a-z_][a-z0-9_]*)|(?P<op>[-+*/()×÷]))")


def _tokens(texto: str) -> list[tuple[str, str]]:
    tokens, pos = [], 0
    texto = texto.strip()
    while pos < len(texto):
        achado = _TOKEN.match(texto, pos)
        if achado is None or achado.end() == pos:
            trecho = texto[pos:pos + 12].strip()
            raise ErroExpressao(f"Trecho não reconhecido na fórmula: {trecho!r}. Use variáveis do catálogo, números e + − × ÷.")
        tipo = achado.lastgroup
        valor = achado.group(tipo)
        if tipo == "op":
            valor = {"×": "*", "÷": "/"}.get(valor, valor)
        tokens.append((tipo, valor))
        pos = achado.end()
        while pos < len(texto) and texto[pos].isspace():
            pos += 1
    return tokens


class _Parser:
    """Descida recursiva. A recursão é limitada por LIMITE_NOS e LIMITE_PROFUNDIDADE."""

    def __init__(self, tokens):
        self.tokens, self.i, self.nos, self.aninhamento = tokens, 0, 0, 0

    def _olhar(self):
        return self.tokens[self.i] if self.i < len(self.tokens) else (None, None)

    def _novo(self, no):
        self.nos += 1
        if self.nos > LIMITE_NOS:
            raise ErroExpressao(f"Fórmula longa demais (máximo de {LIMITE_NOS} elementos).")
        return no

    def expr(self):
        no = self.termo()
        while self._olhar() in (("op", "+"), ("op", "-")):
            op = self.tokens[self.i][1]
            self.i += 1
            no = self._novo(Binario(op, no, self.termo()))
        return no

    def termo(self):
        no = self.fator()
        while self._olhar() in (("op", "*"), ("op", "/")):
            op = self.tokens[self.i][1]
            self.i += 1
            no = self._novo(Binario(op, no, self.fator()))
        return no

    def fator(self):
        tipo, valor = self._olhar()
        if tipo is None:
            raise ErroExpressao("A fórmula termina antes do esperado.")
        self.i += 1
        if (tipo, valor) == ("op", "-"):
            return self._novo(Negativo(self.fator()))
        if tipo == "num":
            numero = float(valor.replace(",", "."))
            if numero > LIMITE_NUMERO:
                raise ErroExpressao("Número grande demais na fórmula.")
            return self._novo(Numero(numero))
        if tipo == "id":
            if valor not in VARIAVEIS:
                raise ErroExpressao(f"Variável desconhecida: {valor!r}. Escolha uma do catálogo.")
            return self._novo(Var(valor))
        if (tipo, valor) == ("op", "("):
            self.aninhamento += 1
            if self.aninhamento > LIMITE_PROFUNDIDADE:
                raise ErroExpressao("Fórmula com parênteses aninhados demais.")
            no = self.expr()
            if self._olhar() != ("op", ")"):
                raise ErroExpressao("Parêntese aberto sem fechar.")
            self.i += 1
            self.aninhamento -= 1
            return no
        raise ErroExpressao(f"Operador fora do lugar: {valor!r}.")


def analisar(texto: str) -> No:
    if not isinstance(texto, str) or not texto.strip():
        raise ErroExpressao("Escreva a fórmula da métrica.")
    if len(texto) > LIMITE_TEXTO:
        raise ErroExpressao(f"Fórmula com mais de {LIMITE_TEXTO} caracteres.")
    parser = _Parser(_tokens(texto.lower()))
    no = parser.expr()
    if parser.i != len(parser.tokens):
        raise ErroExpressao(f"Sobrou um trecho depois da fórmula: {parser.tokens[parser.i][1]!r}.")
    if not variaveis(no):
        raise ErroExpressao("A fórmula precisa usar ao menos uma variável do catálogo.")
    return no


def variaveis(no: No) -> set[str]:
    if isinstance(no, Var):
        return {no.nome}
    if isinstance(no, Negativo):
        return variaveis(no.no)
    if isinstance(no, Binario):
        return variaveis(no.esq) | variaveis(no.dir)
    return set()


def avaliar(no: No, valores: dict[str, float | None]) -> float | None:
    if isinstance(no, Numero):
        return no.valor
    if isinstance(no, Var):
        valor = valores.get(no.nome)
        return None if valor is None else float(valor)
    if isinstance(no, Negativo):
        valor = avaliar(no.no, valores)
        return None if valor is None else -valor
    esq, dir_ = avaliar(no.esq, valores), avaliar(no.dir, valores)
    if esq is None or dir_ is None:
        return None
    if no.op == "/":
        if dir_ == 0:
            return None
        resultado = esq / dir_
    else:
        resultado = esq + dir_ if no.op == "+" else esq - dir_ if no.op == "-" else esq * dir_
    return resultado if math.isfinite(resultado) else None


_PRECEDENCIA = {"+": 1, "-": 1, "*": 2, "/": 2}


def _numero(valor: float) -> str:
    return str(int(valor)) if valor.is_integer() else f"{valor:g}"


def formatar(no: No, *, legivel: bool = False, pai: int = 0, direita: bool = False) -> str:
    """Texto canônico (`legivel=False`) ou em linguagem de gestor (`legivel=True`)."""
    if isinstance(no, Numero):
        return _numero(no.valor).replace(".", ",") if legivel else _numero(no.valor)
    if isinstance(no, Var):
        return VARIAVEIS[no.nome].rotulo if legivel else no.nome
    if isinstance(no, Negativo):
        return "−" + formatar(no.no, legivel=legivel, pai=3) if legivel else "-" + formatar(no.no, pai=3)
    prec = _PRECEDENCIA[no.op]
    simbolo = {"*": "×", "/": "÷", "-": "−", "+": "+"}[no.op] if legivel else no.op
    texto = (f"{formatar(no.esq, legivel=legivel, pai=prec)} {simbolo} "
             f"{formatar(no.dir, legivel=legivel, pai=prec, direita=True)}")
    precisa = prec < pai or (direita and prec == pai)
    return f"({texto})" if precisa else texto


def unidade_inferida(no: No) -> str:
    """`moeda` só quando o resultado continua sendo reais; o resto é número."""
    def _un(n) -> str | None:
        if isinstance(n, Numero):
            return None
        if isinstance(n, Var):
            return VARIAVEIS[n.nome].unidade
        if isinstance(n, Negativo):
            return _un(n.no)
        e, d = _un(n.esq), _un(n.dir)
        if n.op in "+-":
            return e if e == d or d is None else d if e is None else "numero"
        if n.op == "*":
            return e if d is None else d if e is None else "numero"
        return e if d is None else "numero"
    return _un(no) or "numero"
