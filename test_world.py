from world import World
from plot_maps import save_map

w = World("duas_zonas", seed=1, n_blocked=15)

print("Armazéns:", w.warehouses)
print("DPs:", w.dps)
print("Cortadas:", w.blocked)
print(len(w.open_edges()), "abertas de", len(w.edges))

for dp in w.dps:
    for wh in w.warehouses:
        path, km = w.shortest_path(wh, dp)
        print(f"{wh} -> {dp}: {path} ({km:.1f} km)")

save_map("duas_zonas", "Images/teste_world.png",
         wh=w.warehouses, dp=w.dps, blocked=w.blocked)