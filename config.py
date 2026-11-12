#---------------------------------------------------
#   Configuração estática - Tudo o que é comum
#       a todos os mapas e cenários possíveis
#---------------------------------------------------

# ---------------------------------------------------------------------------
# Bens
# ---------------------------------------------------------------------------

# Bens que os armazéns fornecem aos pontos de distribuição. Cada pedido refere
# um único tipo de bem.
#   priority:     urgência do bem (1 é a mais urgente e 3 a menos urgente).
#   deadline_min: prazo de entrega, contado desde a criação do pedido. Uma
#                 entrega feita depois deste prazo conta como atrasada nas
#                 métricas.
GOODS = {
    "medical": {"priority": 1, "deadline_min": 120},
    "food":    {"priority": 2, "deadline_min": 240},
    "shelter": {"priority": 3, "deadline_min": 360},
}

# Stock com que cada armazém começa a simulação, por tipo de bem. Assume-se que
# os armazéns arrancam já abastecidos e que todos têm as mesmas quantidades.
INITIAL_STOCK = {"medical": 70, "food": 90, "shelter": 60}

# Intervalo (mínimo, máximo) da quantidade pedida em cada pedido. A quantidade
# é sorteada neste intervalo e nunca excede a capacidade do maior transporte.
QTY_RANGE = (5, 15)


# ---------------------------------------------------------------------------
# Transportes
# ---------------------------------------------------------------------------

# Características de cada tipo de transporte.
#   capacity:    carga máxima transportada de uma só vez (unidades).
#   speed_kmh:   velocidade de deslocação.
#   flies:       se voa. Um drone viaja em linha reta e não depende do estado
#                das estradas; um camião só circula pelas estradas abertas.
#   fuel_max:    capacidade do depósito (unidades de combustível).
#   fuel_per_km: combustível gasto por quilómetro percorrido.
# O combustível só é tido em conta nos cenários que o ativam.
TRANSPORT_TYPES = {
    "truck": {"capacity": 40, "speed_kmh": 40, "flies": False, "fuel_max": 100, "fuel_per_km": 0.5},
    "drone": {"capacity": 10, "speed_kmh": 90, "flies": True,  "fuel_max": 20,  "fuel_per_km": 0.15},
}

# Margem de segurança sobre o combustível estimado para um percurso. Um
# transporte só aceita um pedido se o seu combustível cobrir a estimativa
# acrescida desta fração, porque os desvios causados por estradas bloqueadas
# podem tornar a estimativa otimista. Só é usada quando o combustível está ativo.
FUEL_SAFETY_MARGIN = 0.10


# ---------------------------------------------------------------------------
# População
# ---------------------------------------------------------------------------

# Número mínimo e máximo de agentes de cada tipo numa simulação.
# Diferenças em relação ao planeamento inicial: armazéns 3-5 (planeado 4-6) e
# couriers 0-2 (planeado 2-3; o valor 0 permite avaliar o sistema sem couriers).
# Os camiões e os drones, em conjunto, somam entre 5 e 8 transportes.
LIMITS = {
    "wh":      {"min": 3, "max": 5},
    "dp":      {"min": 2, "max": 4},
    "truck":   {"min": 4, "max": 6},
    "drone":   {"min": 1, "max": 2},
    "courier": {"min": 0, "max": 2},
}


# ---------------------------------------------------------------------------
# Tempo
# ---------------------------------------------------------------------------

# Segundos reais que dura um minuto simulado (uma hora simulada dura 3 s). Um
# valor mais baixo acelera as execuções, mas a latência das mensagens XMPP
# (alguns milissegundos) passa a pesar nos prazos mais curtos e gera timeouts
# que não existiriam num sistema real. Um valor mais alto torna demasiado
# demorada a campanha de 3 cenários x 10 seeds.
SEC_PER_SIM_MIN = 0.05

# Intervalo com que cada agente acorda para verificar os seus prazos.
TICK_MIN = 1

# Duração de uma simulação.
DURATION_MIN = 600


# ---------------------------------------------------------------------------
# Procura e armazéns
# ---------------------------------------------------------------------------

# Tempo médio entre dois pedidos consecutivos de um ponto de distribuição. Os
# intervalos efetivos são sorteados em torno desta média.
DEMAND_PERIOD_MIN = 60

# Intervalo com que um armazém lê e decide os pedidos que foi acumulando.
WH_READ_INTERVAL_MIN = 2


# ---------------------------------------------------------------------------
# Protocolo: prazos de espera
# ---------------------------------------------------------------------------

# Tempo que um ponto de distribuição espera pela resposta de um armazém (aceita
# ou recusa). Esgotado o prazo, dá o pedido por perdido e tenta o armazém
# seguinte. Tem de ser superior a WH_READ_INTERVAL_MIN, porque o armazém só
# responde quando lê os pedidos.
WH_REPLY_TIMEOUT_MIN = 10

# Tempo que um armazém espera pela resposta de um transporte (aceita ou
# recusa). Esgotado o prazo, tenta o transporte seguinte.
TRANSPORT_REPLY_TIMEOUT_MIN = 8

# Número máximo de transportes que um armazém contacta por pedido. Se nenhum
# aceitar, o armazém devolve o stock e avisa o ponto de distribuição, que passa
# ao armazém seguinte.
MAX_TRANSPORT_TRIES = 3

# Tempo que o ponto de distribuição espera, depois de o armazém aceitar o
# pedido, pelo aviso de que há transporte. Tem de ser superior ao tempo que o
# armazém demora a esgotar as tentativas (MAX_TRANSPORT_TRIES x
# TRANSPORT_REPLY_TIMEOUT_MIN, mais a leitura). Caso contrário, o ponto passaria
# ao armazém seguinte enquanto o primeiro ainda procura, deixando stock reservado
# sem destino.
DISPATCH_TIMEOUT_MIN = 40

# Tempo que um transporte permanece reservado à espera da autorização para
# partir. Esgotado o prazo, liberta-se sozinho, o que evita transportes
# bloqueados por mensagens perdidas. Tem de ser superior a CONFIRM_TIMEOUT_MIN.
HOLD_TIMEOUT_MIN = 30

# Intervalo com que um transporte informa os armazéns da sua posição e estado.
# Entre duas mensagens, a posição que os armazéns conhecem fica desatualizada.
STATUS_PERIOD_MIN = 15

# Tempo que um armazém espera pela confirmação do ponto de distribuição, depois
# de lhe comunicar que encontrou transporte. A confirmação garante que o ponto
# ainda aguarda esta entrega e não passou a outro armazém. Sem resposta, o
# armazém liberta o transporte e o stock.
CONFIRM_TIMEOUT_MIN = 10

# Tempo máximo que o stock fica reservado sem que o pedido avance. Esgotado o
# prazo, o stock volta a estar disponível; é a proteção contra reservas que
# ficariam presas quando se perdem mensagens. Tem de ser superior a
# DISPATCH_TIMEOUT_MIN, para não libertar stock de um pedido que o ponto de
# distribuição ainda espera.
RESERVATION_TTL_MIN = 60

# Tempo que um agente espera pela confirmação de receção (ack) de uma mensagem
# importante antes de a reenviar, e número máximo de reenvios. O tempo total de
# insistência, ACK_TIMEOUT_MIN x (MAX_RESENDS + 1), tem de ser inferior a
# HOLD_TIMEOUT_MIN.
ACK_TIMEOUT_MIN = 3
MAX_RESENDS = 2


# ---------------------------------------------------------------------------
# Couriers
# ---------------------------------------------------------------------------

# Intervalo com que um courier escolhe a próxima estrada a inspecionar.
COURIER_PERIOD_MIN = 30

# Velocidade a que um courier se desloca até à estrada que vai inspecionar.
COURIER_SPEED_KMH = 50


# ---------------------------------------------------------------------------
# Servidor XMPP
# ---------------------------------------------------------------------------

# Domínio e palavra-passe com que os agentes se registam no servidor local
# (iniciado com `spade run`).
XMPP_DOMAIN = "localhost"
XMPP_PASSWORD = "pass"


# ---------------------------------------------------------------------------
# Ficheiros de saída
# ---------------------------------------------------------------------------

# Tabela com uma linha por simulação executada (a base de dados dos resultados).
RESULTS_FILE = "simulacoes.csv"

# Pasta onde se guarda o registo de eventos de cada simulação.
EVENTS_DIR = "resultados"

# Ficheiro com a configuração escolhida em customize.py (mapa, cenário,
# número de agentes e seed).
CHOICE_FILE = "escolha.json"