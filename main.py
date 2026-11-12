import asyncio, time
import spade
from world import World
from config import LIMITS, XMPP_DOMAIN, XMPP_PASSWORD, DURATION_MIN
from agents.warehouse import WarehouseAgent
from agents.dp import DPAgent
from agents.transport import TransportAgent
from agents.scout import ScoutAgent

MAP = "ilha"
SEED = 1
N_BLOCKED = 4
SIM_DURATION_MIN = DURATION_MIN     # Quanto tempo simulado deixar correr
SERVER = XMPP_DOMAIN
PASSWORD = XMPP_PASSWORD


def make_jid(prefix, i, run_id):
    return f"{prefix}{i}_{run_id}@{SERVER}"

async def start_agent(agent, tries=3):
    for attempt in range(1, tries + 1):
        try:
            await agent.start(auto_register=True)
            return True
        except Exception as e:
            print(f"  falhou {agent.jid} (tentativa {attempt}/{tries}): {e}")
            await asyncio.sleep(2)
    return False

async def main():
    run_id = int(time.time())
    world = World(MAP, SEED, N_BLOCKED, run_id=run_id)

    # Quantos transportes e scouts (com o rng do mundo, para depender da seed)
    n_trucks = world.rng.randint(LIMITS["truck"]["min"], LIMITS["truck"]["max"])
    n_drones = world.rng.randint(LIMITS["drone"]["min"], LIMITS["drone"]["max"])
    n_scouts = world.rng.randint(LIMITS["courier"]["min"], LIMITS["courier"]["max"])  # courier = scout

    # Diretório de JIDs: a "lista de contactos" de todos os agentes
    directory = {"warehouses": {}, "dps": {}, "trucks": {}, "drones": {}, "scouts": []}
    agents = []

    # Armazéns
    for i, node in enumerate(world.warehouses):
        jid = make_jid("wh", i, run_id)
        directory["warehouses"][node] = jid
        agents.append(WarehouseAgent(jid, PASSWORD, world, node, directory))

    # Pontos de distribuição
    for i, node in enumerate(world.dps):
        jid = make_jid("dp", i, run_id)
        directory["dps"][node] = jid
        agents.append(DPAgent(jid, PASSWORD, world, node, directory))

    # Camiões e drones: começam num armazém, distribuídos em rotação
    for kind, n, key in [("truck", n_trucks, "trucks"), ("drone", n_drones, "drones")]:
        for i in range(n):
            jid = make_jid(kind, i, run_id)
            node = world.warehouses[i % len(world.warehouses)]
            directory[key][jid] = node
            agents.append(TransportAgent(jid, PASSWORD, world, node, directory, kind))

    # Scouts
    for i in range(n_scouts):
        jid = make_jid("scout", i, run_id)
        directory["scouts"].append(jid)
        agents.append(ScoutAgent(jid, PASSWORD, world, None, directory))

    # Arrancar
    print(f"Mapa {MAP}, seed {SEED} | cortadas: {sorted(world.blocked)}")
    world.events.add(0.0, "world", "run_start", map=MAP, seed=SEED, run_id=run_id,
                     warehouses=world.warehouses, dps=world.dps,
                     trucks=n_trucks, drones=n_drones, scouts=n_scouts)
    for e in sorted(world.blocked):
        world.events.add(0.0, "world", "road_cut", edge=e, initial=True)    
    for a in agents:
        if not await start_agent(a):
            print(f"Não foi possível ligar {a.jid}; a parar.")
            return
        await asyncio.sleep(0.2)
    world.start_clock()     # O tempo simulado só começa com todos ligados
    print(f"Arrancaram: {len(world.warehouses)} armazéns, {len(world.dps)} DPs, "
          f"{n_trucks} camiões, {n_drones} drones, {n_scouts} scouts")

    # Deixar correr
    await asyncio.sleep(world.sim_to_real(SIM_DURATION_MIN))

    world.events.add(world.now(), "world", "run_end")

    # Parar
    for a in agents:
        await a.stop()

    print(world.events.save())

if __name__ == "__main__":
    spade.run(main())