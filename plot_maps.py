"""Desenha os mapas (grafos) definidos em maps.py.

Uso:
    python plot_mapas.py                 # uma imagem grande por mapa + resumo com os três
    python plot_mapas.py --map anel      # só esse mapa -> mapa_anel.png
    python plot_mapas.py --no-dist       # sem as distâncias nas estradas
    python plot_mapas.py --dir graficos  # grava numa pasta (criada se não existir)
    python plot_mapas.py --show          # abre também as janelas

Os mapas só têm nós genéricos. Para desenhar também onde ficam armazéns e PDs
e estradas bloqueadas (depois de os colocares), usa a função em código:

    from plot_mapas import draw_map, save_map
    save_map("ilha", "layout.png", wh=["N3", "N4"], dp=["N16"], blocked=[("N5", "N7")])
"""

import argparse
import math
import os

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

import maps

C_ROAD, C_BLOCKED, C_WH, C_DP, C_JUNC = "#9aa0a6", "#d93025", "#1a73e8", "#e8710a", "#5f6368"

def draw_map(ax, name, wh=(), dp=(), show_dist=True, blocked=(), big=True):
    """Desenha um mapa. `wh` e `dp`: listas de nós; `blocked`: lista de pares (u, v)."""
    spec = maps.MAPS[name]
    nodes = spec["nodes"]
    blocked = {tuple(sorted(b)) for b in blocked}
    f_node, f_edge, s = (10, 8.5, 1.0) if big else (7, 6.5, 0.6)

    for u, v in spec["edges"]:
        (x1, y1), (x2, y2) = nodes[u], nodes[v]
        is_b = tuple(sorted((u, v))) in blocked
        ax.plot([x1, x2], [y1, y2], color=C_BLOCKED if is_b else C_ROAD,
                lw=(2.4 if is_b else 1.8) * s, ls="--" if is_b else "-", zorder=1)
        if show_dist:
            km = math.dist(nodes[u], nodes[v])
            ax.text((x1 + x2) / 2, (y1 + y2) / 2, f"{km:.0f}", fontsize=f_edge,
                    color=C_BLOCKED if is_b else "#5f6368", ha="center", va="center", zorder=2,
                    bbox=dict(boxstyle="round,pad=0.12", fc="white", ec="none", alpha=0.9))

    for n, (x, y) in nodes.items():
        if n in wh:
            style = dict(marker="s", color=C_WH, s=240 * s)
        elif n in dp:
            style = dict(marker="^", color=C_DP, s=260 * s)
        else:
            style = dict(marker="o", color=C_JUNC, s=110 * s)
        ax.scatter(x, y, zorder=3, edgecolors="white", linewidths=1.2, **style)
        ax.annotate(n, (x, y), textcoords="offset points", xytext=(7, 7),
                    fontsize=f_node, fontweight="bold", zorder=4)

    ax.set_title(f"{name}  ({len(nodes)} nós, {len(spec['edges'])} estradas)",
                 fontsize=14 if big else 11)
    ax.set_aspect("equal")
    ax.invert_yaxis()                 # y cresce para baixo, como num ecrã
    ax.set_xlabel("km")
    ax.margins(0.06)
    ax.grid(alpha=0.15)


def legend_handles(layout=False, blocked=False):
    h = [Line2D([], [], marker="o", ls="", color=C_JUNC, label="cruzamento", markersize=8)]
    if layout:
        h = [Line2D([], [], marker="s", ls="", color=C_WH, label="armazém", markersize=10),
             Line2D([], [], marker="^", ls="", color=C_DP, label="ponto de distribuição", markersize=10)] + h
    if blocked:
        h.append(Line2D([], [], color=C_BLOCKED, ls="--", label="estrada bloqueada"))
    return h


def save_map(name, path, wh=(), dp=(), blocked=(), show_dist=True):
    """Grava uma imagem grande de um mapa (com disposição e bloqueios, se existirem)."""
    fig, ax = plt.subplots(figsize=(12, 8.5))
    draw_map(ax, name, wh, dp, show_dist, blocked, big=True)
    ax.legend(handles=legend_handles(bool(wh or dp), bool(blocked)),
              loc="upper center", bbox_to_anchor=(0.5, -0.07), ncol=4, frameon=False)
    fig.tight_layout()
    fig.savefig(path, dpi=140, bbox_inches="tight")
    return fig


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--map", choices=list(maps.MAPS), help="só este mapa (defeito: todos)")
    ap.add_argument("--no-dist", action="store_true", help="não escrever as distâncias nas estradas")
    ap.add_argument("--dir", default="Images", help="pasta onde gravar as imagens")
    ap.add_argument("--show", action="store_true", help="abrir janelas")
    a = ap.parse_args()
    os.makedirs(a.dir, exist_ok=True)

    names = [a.map] if a.map else list(maps.MAPS)
    for name in names:
        path = os.path.join(a.dir, f"mapa_{name}.png")
        save_map(name, path, show_dist=not a.no_dist)
        print("gravado:", path)

    if len(names) > 1:                          # resumo com todos lado a lado
        fig, axs = plt.subplots(1, len(names), figsize=(8 * len(names), 7), squeeze=False)
        for ax, name in zip(axs[0], names):
            draw_map(ax, name, show_dist=not a.no_dist, big=False)
        fig.tight_layout()
        path = os.path.join(a.dir, "mapas.png")
        fig.savefig(path, dpi=110, bbox_inches="tight")
        print("gravado:", path)
    if a.show:
        plt.show()


if __name__ == "__main__":
    main()