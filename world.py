import math, random, heapq, time
import maps
from config import LIMITS, TRANSPORT_TYPES, GOODS, INITIAL_STOCK, SEC_PER_SIM_MIN
from eventlog import EventLog

class World:
    def __init__(self, map_name, seed, n_blocked=4, n_wh=None, n_dp=None, run_id="local"):
        self.rng = random.Random(seed)
        spec = maps.MAPS[map_name]
        self.nodes = spec["nodes"]      # {"N1": (x, y), ...}
        self.edges = {self._key(u, v): math.dist(self.nodes[u], self.nodes[v])
                      for u, v in spec["edges"]}        # {("N1","N5"): km}
        self.blocked = set()        # Estado verdadeiro
        self.warehouses, self.dps = self._place_agents(n_wh, n_dp)
        self._block_random(n_blocked)
        self.start = None       # O relógio só começa quando todos os agentes estiverem conetados
        self.events = EventLog(run_id)
        self.stock = self._init_stock()


    @staticmethod
    def _key(u, v):
        return tuple(sorted((u, v)))

    def _place_agents(self, n_wh=None, n_dp=None):
        # Escolher n_wh e n_dp dentro de LIMITS e sortear nós distintos
         n_wh = self.rng.randint(LIMITS["wh"]["min"], LIMITS["wh"]["max"])
         n_dp = self.rng.randint(LIMITS["dp"]["min"], LIMITS["dp"]["max"])
         chosen = self.rng.sample(sorted(self.nodes), n_wh + n_dp)
         return chosen[:n_wh], chosen[n_wh:]

    def open_edges(self):
        return {e: d for e, d in self.edges.items() if e not in self.blocked}

    def shortest_path(self, src, dst, edges=None):
        # Se não forem passadas como argumento, usa as estradas abertas
        if edges is None:
            edges = self.open_edges()

        # Cria um dicionário com uma lista vazia para cada nó do mapa
        adj = {}
        for n in self.nodes:
            adj[n] = []

        # Percorre cada estrada (u, v) e o seu comprimento em km
        # Junta (v, km) à lista de vizinhos de u
        # Junta (u, km) à lista de vizinhos de v (a estrada é de dois sentidos)
        for (u,v), km in edges.items():
            adj[u].append((v,km))
            adj[v].append((u,km))

        # Dijkstra
        dist = {src: 0.0}
        prev = {}
        heap = [(0.0, src)]

        while len(heap) != 0:
            # Tira da fila o par (distância, nó) com menor distância
            (distance, curr) = heapq.heappop(heap)
            # Se esse nó é o destino, pára o ciclo
            if curr == dst: break
            # Se a distância é pior do que a já guardada para esse nó, salta para a próxima volta
            if distance > dist[curr]: continue

            # Para cada vizinho deste nó (e o km da estrada até ele):
            for viz, km in adj[curr]:
                new_dist = distance + km
                # Se a distância nova for melhor do que a guardada para o vizinho (ou se ainda não houver nenhuma):
                if new_dist < dist.get(viz, math.inf):
                    # Guarda a distância nova para o vizinho
                    dist[viz] = new_dist
                    prev[viz] = curr    
                    heapq.heappush(heap, (new_dist, viz))

        # Se o destino nunca recebeu distância, devolve None e infinito
        if dst not in dist:
            return None, math.inf
        
        # Reconstói o caminho de trás para a frente, começando com uma lista só com o destino
        path = [dst]
        while path[-1] != src:
            path.append(prev[path[-1]])
        # Inverte a lista (estava do destino para a origem)
        path.reverse()  
        return path, dist[dst]

    def _block_random(self, n):
        # Cria uma lista com todas as estradas (as chaves de self.edges), ordenada com sorted
        # (ordenar garante que a mesma seed corta sempre as mesmas estradas)
        streets = sorted ([edge for edge in self.edges.keys()])

        if n > len(self.edges):
        # Se n for maior do que o número de estradas, reduz n para esse número
            n = len(self.edges)
        n_cortar = n
        
        # Sorteia n estradas diferentes dessa lista com self.rng.sample
        for _ in range(n_cortar):
            idx = self.rng.randrange(len(streets))
            self.blocked.add(streets.pop(idx))

    def start_clock(self):
        # Põe o relógio a zero (chamar quando todos os agentes estiverem ligados)
        self.start = time.monotonic()

    def now(self):
        # Tempo real que passou desde o start_clock())
        # Divide por SEC_PER_SIM_MIN (segundos reais por minuto simulado)
        # Devolve os minutos simulados

        if self.start is None: return 0.0       # Antes de arrancar, o tempo é 0
        segundos_reais = time.monotonic() - self.start
        return segundos_reais / SEC_PER_SIM_MIN

    def sim_to_real(self, minutes):
        # O contrário: converte minutos simulados em segundos reais
        return minutes * SEC_PER_SIM_MIN

    def travel_time(self, km, transport_type):
        # Vai buscar a velocidade em km/h a TRANSPORT_TYPES[transport_type]
        # Devolve o tempo em MINUTOS (atenção: a velocidade está por hora)
        speed_kmh = TRANSPORT_TYPES[transport_type]["speed_kmh"]
        return km / speed_kmh * 60

    def air_distance(self, a, b):
        # Distância em linha reta entre os nós a e b, com as coordenadas de self.nodes
        return math.dist(self.nodes[a], self.nodes[b])

    def drone_can_reach(self, origin, dest):
        # Alcance máximo do drone = fuel_max / fuel_per_km (do config)
        # Ida e volta = 2 * air_distance(origin, dest)
        # Devolve True se a ida e volta couber no alcance
        drone = TRANSPORT_TYPES["drone"]
        max_range = drone["fuel_max"] / drone["fuel_per_km"]
        return 2*self.air_distance(origin, dest) <= max_range

    def is_blocked(self, u, v):
        # Devolve True se a estrada entre u e v está em self.blocked
        return self._key(u,v) in self.blocked

    def _init_stock(self):
        stock = {}
        for wh in self.warehouses:
            stock[wh] = {}
            for good in GOODS:
                stock[wh][good] = INITIAL_STOCK[good]
        return stock