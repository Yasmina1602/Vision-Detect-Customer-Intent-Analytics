"""ball = 0.6·vektor + 0.25·atribut moslik (rang/tur) + 0.1·mavjudlik + 0.05·mashhurlik."""
from dataclasses import dataclass

W_VECTOR, W_ATTR, W_STOCK, W_POP = 0.6, 0.25, 0.1, 0.05


@dataclass
class ScoreParts:
    vector: float
    attr: float
    stock: float
    popularity: float

    @property
    def total(self) -> float:
        return round(W_VECTOR * self.vector + W_ATTR * self.attr + W_STOCK * self.stock + W_POP * self.popularity, 4)


def attribute_match(q_color: str | None, q_type: str | None, q_cat: str | None,
                    p_color: str | None, p_type: str | None, p_cat: str | None) -> float:
    """Tur moslik 0.55, rang 0.35, kategoriya 0.10."""
    score = 0.0
    if q_type and p_type and q_type == p_type:
        score += 0.55
    if q_color and p_color and q_color == p_color:
        score += 0.35
    if q_cat and p_cat and q_cat == p_cat:
        score += 0.10
    return score
