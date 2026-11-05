"""SHA-256 et arbre de Merkle (portage de pow.cpp et merkle.js, Atelier 1)."""
import hashlib


def sha256_hex(data: str) -> str:
    """Hash SHA-256 d'une chaine, en hexadecimal."""
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def merkle_root(tx_ids: list[str]) -> str:
    """Racine de Merkle. Comme dans merkle.js : si le nombre de hashes
    est impair, le dernier est duplique."""
    if not tx_ids:
        return sha256_hex("")
    level = [sha256_hex(t) for t in tx_ids]
    while len(level) > 1:
        parents = []
        for i in range(0, len(level), 2):
            left = level[i]
            right = level[i + 1] if i + 1 < len(level) else left
            parents.append(sha256_hex(left + right))
        level = parents
    return level[0]
