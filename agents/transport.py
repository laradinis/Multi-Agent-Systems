import uuid
import asyncio
from agents.base import BaseAgent
from config import TRANSPORT_TYPES, HOLD_TIMEOUT_MIN
from spade.behaviour import OneShotBehaviour, CyclicBehaviour

class TransportAgent(BaseAgent):

    def __init__(self, jid, password, world, node, directory, kind):
        super().__init__(jid, password, world, node, directory)

        self.kind = kind          # "truck" ou "drone"

        # Vai buscar as características do transporte ao config
        if self.kind not in TRANSPORT_TYPES:
            raise ValueError(f"Tipo de transporte inválido: {self.kind}")

        self.transport_config = TRANSPORT_TYPES[self.kind]
        self.capacity = self.transport_config["capacity"]

        # Desvio máximo permitido para aceitar novos pedidos (em km)
        self.max_route_detour_km = self.transport_config.get(
            "max_route_detour_km", 2.0
        )

        # Estado atual do transporte
        self.busy = False
        self.current_load = 0
        self.reserved_capacity = 0

        # Guarda os pedidos associados ao transporte, identificados pelo req_id
        self.current_orders = {}

        # Guarda os pedidos aceites que ainda aguardam autorização
        self.pending_reservations = {}

        # Guarda as paragens previstas no percurso
        self.planned_stops = []

        # Guarda o percurso que o transporte está a realizar
        self.current_route = []

    class Hello(OneShotBehaviour):
        async def run(self):
            self.agent.log(f"{self.agent.kind} pronto em {self.agent.node}")
            self.agent.event("agent_ready", role=self.agent.kind, node=self.agent.node)


    # Comportamento que verifica reservas de capacidade expiradas
    class ReservationMonitor(CyclicBehaviour):
        async def run(self):

            # Obtém o tempo simulado atual
            current_time = self.agent.world.now()

            # Percorre as reservas pendentes
            for req_id, reservation in list(
                self.agent.pending_reservations.items()
            ):

                # Calcula há quanto tempo a reserva está ativa
                elapsed_time = (
                    current_time - reservation["created_at"]
                )

                # Verifica se ultrapassou o prazo permitido
                if elapsed_time >= HOLD_TIMEOUT_MIN:

                    # Liberta a capacidade reservada
                    quantity = reservation["accepted_quantity"]

                    self.agent.reserved_capacity -= quantity

                    # Remove a reserva pendente
                    del self.agent.pending_reservations[req_id]

                    self.agent.log(
                        f"Reserva {req_id} expirada | "
                        f"Capacidade libertada: {quantity}"
                    )

            # Atualiza o estado do transporte
            self.agent.busy = bool(
                self.agent.current_orders
                or self.agent.pending_reservations
            )

            # Aguarda um minuto simulado antes da próxima verificação
            await asyncio.sleep(
                self.agent.world.sim_to_real(1)
            )

    # Comportamento responsável por movimentar o transporte
    # e executar as paragens de recolha e entrega
    class MovementBehaviour(CyclicBehaviour):
        async def run(self):

            # Seleciona a próxima paragem ainda por realizar
            pending_stops = [
                stop for stop in self.agent.planned_stops
                if not stop["completed"]
            ]

            # Se não existirem paragens, aguarda
            if not pending_stops:
                await asyncio.sleep(
                    self.agent.world.sim_to_real(0.2)
                )
                return

            # Obtém a próxima paragem do percurso
            next_stop = pending_stops[0]
            destination = next_stop["node"]

            # Desloca o transporte até à paragem
            reached = await self.agent.move_to_node(destination)

            # Só executa a paragem se tiver chegado ao destino
            if reached:
                await self.agent.process_stop(next_stop)

                # Atualiza o percurso depois de executar a paragem
                self.agent.calculate_route()

    async def setup(self):
        # Inicializa os comportamentos comuns do BaseAgent
        await super().setup()

        # Regista os handlers das mensagens que o Transport sabe tratar
        self.register_handler("transport_request", self.handle_transport_request)
        self.register_handler("delivery_authorization", self.handle_delivery_authorization)
        self.register_handler("cancellation", self.handle_cancellation)

        # Adiciona o comportamento específico do Transport
        self.add_behaviour(self.Hello())

        # Ativa a verificação automática das reservas expiradas
        self.add_behaviour(self.ReservationMonitor())

        # Ativa a movimentação e execução das entregas
        self.add_behaviour(self.MovementBehaviour())

    # Regista um pedido autorizado no transporte
    def register_order(self, payload):

        req_id = payload["req_id"]

        # Guarda os dados do pedido associado ao transporte
        self.current_orders[req_id] = {
            "resource": payload["resource"],
            "quantity": payload["quantity"],
            "origins": list(payload["origins"]),
            "source_quantities": dict(payload["source_quantities"]),
            "destination": payload["destination"],
            "status": "authorized",
            "loaded_by_origin": {},
            "delivery_id": str(uuid.uuid4()),
            "attempt": payload.get("attempt"),
        }

        self.log(f"Pedido {req_id} registado no transporte")

    # Regista as paragens ainda necessárias para realizar um pedido
    def register_stops(self, req_id):

        # Vai buscar os dados do pedido
        order = self.current_orders[req_id]

        # Evita criar paragens duplicadas para o mesmo pedido
        self.planned_stops = [
            stop for stop in self.planned_stops
            if stop["req_id"] != req_id
        ]

        # Cria uma paragem de recolha para cada armazém de origem
        for origin in order["origins"]:
            self.planned_stops.append({
                "node": origin,
                "type": "pickup",
                "req_id": req_id,
                "quantity": order["source_quantities"][origin],
                "completed": False
            })

        # Cria a paragem de entrega no destino
        self.planned_stops.append({
            "node": order["destination"],
            "type": "delivery",
            "req_id": req_id,
            "quantity": order["quantity"],
            "completed": False
        })

        self.log(f"Paragens do pedido {req_id} registadas")

    # Calcula um percurso e a distância total para uma sequência de paragens
    def calculate_route_for_stops(self, stops):

        # Começa na localização atual do transporte
        current_node = self.node

        # Inicializa o percurso e a distância total
        route = [current_node]
        total_distance = 0

        # Percorre as paragens pela ordem definida
        for stop in stops:

            destination = stop["node"]

            # Caso o transporte seja um camião
            if self.kind == "truck":

                path, distance = self.world.shortest_path(
                    current_node,
                    destination
                )

                if path is None:
                    return None, float("inf")

                route.extend(path[1:])
                total_distance += distance

            # Caso o transporte seja um drone
            elif self.kind == "drone":

                if not self.world.drone_can_reach(
                    current_node,
                    destination
                ):
                    return None, float("inf")

                route.append(destination)
                total_distance += self.world.air_distance(
                    current_node,
                    destination
                )

            current_node = destination

        return route, total_distance

    # Calcula o percurso considerando apenas as paragens ainda por realizar
    def calculate_route(self):

        # Seleciona apenas as paragens que ainda não foram concluídas
        pending_stops = [
            stop for stop in self.planned_stops
            if not stop["completed"]
        ]

        # Começa na localização atual do transporte
        current_node = self.node

        # Inicializa o percurso com a localização atual
        route = [current_node]

        # Percorre as paragens pendentes pela ordem definida
        for stop in pending_stops:

            destination = stop["node"]

            # Caso o transporte seja um camião
            if self.kind == "truck":

                # Calcula o caminho mais curto pelas estradas disponíveis
                path, distance = self.world.shortest_path(
                    current_node,
                    destination
                )

                # Verifica se existe um caminho possível
                if path is None:
                    self.log(
                        f"Não existe caminho entre {current_node} e {destination}"
                    )
                    return None

                # Adiciona o caminho ao percurso completo
                route.extend(path[1:])

            # Caso o transporte seja um drone
            elif self.kind == "drone":

                # Verifica se o drone consegue alcançar a próxima paragem
                if not self.world.drone_can_reach(current_node, destination):
                    self.log(
                        f"Drone sem alcance entre {current_node} e {destination}"
                    )
                    return None

                # O drone desloca-se diretamente para a paragem
                route.append(destination)

            # Atualiza a localização para calcular o próximo segmento
            current_node = destination

        # Guarda o percurso calculado
        self.current_route = route

        self.log(f"Percurso calculado: {self.current_route}")

        return self.current_route


    # Desloca o transporte desde a localização atual até um nó
    async def move_to_node(self, destination):

        # Se já estiver no destino, não precisa de se deslocar
        if self.node == destination:
            return True

        # Caso seja um camião, calcula o caminho pelas estradas abertas
        if self.kind == "truck":

            path, distance = self.world.shortest_path(
                self.node,
                destination
            )

            # Verifica se existe um caminho possível
            if path is None:
                self.log(
                    f"Movimento impossível entre {self.node} e {destination}"
                )
                return False

            # Percorre cada estrada do caminho calculado
            for next_node in path[1:]:

                # Obtém a distância entre os dois nós
                edge = self.world._key(self.node, next_node)
                distance = self.world.edges[edge]

                # Calcula o tempo de viagem em minutos simulados
                travel_time = self.world.travel_time(
                    distance,
                    self.kind
                )

                self.log(
                    f"A deslocar-se de {self.node} para {next_node} "
                    f"({distance:.2f} km)"
                )

                # Aguarda o tempo correspondente à viagem
                await asyncio.sleep(
                    self.world.sim_to_real(travel_time)
                )

                # Atualiza a localização atual
                self.node = next_node

        # Caso seja um drone, desloca-se diretamente em linha reta
        elif self.kind == "drone":

            # Confirma que o drone consegue alcançar o destino
            if not self.world.drone_can_reach(
                self.node,
                destination
            ):
                self.log(
                    f"Drone sem alcance entre {self.node} e {destination}"
                )
                return False

            # Calcula a distância em linha reta
            distance = self.world.air_distance(
                self.node,
                destination
            )

            # Calcula o tempo de viagem
            travel_time = self.world.travel_time(
                distance,
                self.kind
            )

            self.log(
                f"Drone a deslocar-se de {self.node} para {destination} "
                f"({distance:.2f} km)"
            )

            # Aguarda o tempo correspondente à viagem
            await asyncio.sleep(
                self.world.sim_to_real(travel_time)
            )

            # Atualiza a localização atual
            self.node = destination

        self.log(f"Chegou ao nó {self.node}")

        return True

    # Executa a operação correspondente à paragem atual
    async def process_stop(self, stop):

        req_id = stop["req_id"]
        order = self.current_orders.get(req_id)

        # Verifica se o pedido ainda existe
        if order is None:
            self.log(f"Pedido {req_id} não encontrado")
            stop["completed"] = True
            return

        # Caso seja uma paragem de recolha
        if stop["type"] == "pickup":

            origin = stop["node"]
            quantity = stop["quantity"]

            # Verifica se a recolha já foi efetuada
            if origin in order["loaded_by_origin"]:
                return
            
            # Envia a confirmação da recolha ao armazém
            warehouse_jid = self.directory["warehouses"].get(origin)

            if warehouse_jid is None:
                self.log(f"Não foi encontrado o armazém de origem {origin}")
                return

            await self.send_message(
                receiver=warehouse_jid,
                performative="inform",
                message_type="pickup_completed",
                payload={
                    "req_id": req_id,
                    "attempt": order["attempt"],
                    "transport_id": str(self.jid),
                    "resource": order["resource"],
                    "quantity": quantity,
                    "origin": origin
                }
            )

            # Atualiza a carga do transporte
            self.current_load += quantity

            # Transfere a quantidade da capacidade reservada para a carga atual
            self.reserved_capacity -= quantity

            # Regista a quantidade recolhida neste armazém
            order["loaded_by_origin"][origin] = quantity

            self.log(
                f"Recolhidas {quantity} unidades de "
                f"{order['resource']} em {origin} | "
                f"Carga atual: {self.current_load}/{self.capacity}"
            )

            self.event(
                "cargo_picked_up",
                req_id=req_id,
                origin=origin,
                resource=order["resource"],
                quantity=quantity
            )

        # Caso seja uma paragem de entrega
        elif stop["type"] == "delivery":

            quantity = order["quantity"]

            # Confirma que toda a carga prevista foi recolhida
            loaded_quantity = sum(
                order["loaded_by_origin"].values()
            )

            if loaded_quantity != quantity:
                self.log(
                    f"Entrega {req_id} não executada: "
                    f"recolhidas {loaded_quantity} de {quantity} unidades"
                )
                return

            # Prepara os dados da entrega
            payload = {
                "delivery_id": order["delivery_id"],
                "req_id": req_id,
                "transport_id": str(self.jid),
                "resource": order["resource"],
                "delivered_quantity": quantity,
                "source_quantities": dict(order["loaded_by_origin"]),
                "origins": list(order["origins"]),
                "destination": order["destination"]
            }

            # Notifica todos os armazéns envolvidos na entrega
            for origin in order["origins"]:

                warehouse_jid = self.directory["warehouses"].get(origin)

                if warehouse_jid is None:
                    self.log(
                        f"Não foi encontrado o armazém de origem {origin}"
                    )
                    return

                await self.send_message(
                    receiver=warehouse_jid,
                    performative="inform",
                    message_type="delivery_completed",
                    payload=payload
                )

            self.current_load -= quantity

            # Atualiza o estado do pedido
            order["status"] = "completed"

            self.log(
                f"Entrega {req_id} concluída | "
                f"{quantity} unidades entregues em {order['destination']} | "
                f"Carga restante: {self.current_load}"
            )

            self.event(
                "delivery_completed",
                req_id=req_id,
                resource=order["resource"],
                delivered_quantity=quantity,
                destination=order["destination"]
            )

            # Remove o pedido da lista de pedidos ativos
            del self.current_orders[req_id]

        # Marca a paragem como concluída
        stop["completed"] = True

        # Atualiza o estado do transporte
        self.busy = bool(
            self.current_orders or self.pending_reservations
        )

        # Remove as paragens que já foram concluídas
        self.planned_stops = [
            planned_stop
            for planned_stop in self.planned_stops
            if not planned_stop["completed"]
        ]

    # Trata as autorizações de entrega recebidas dos pontos de distribuição
    async def handle_delivery_authorization(self, message):

        # Vai buscar os dados da autorização
        payload = message["payload"]
        req_id = payload["req_id"]
        quantity = payload["quantity"]

        # Verifica se a autorização se destina a este transporte
        if payload["transport_id"] != str(self.jid):
            self.log(f"Autorização {req_id} destinada a outro transporte")
            return

        # Evita registar duas vezes o mesmo pedido
        if req_id in self.current_orders:
            self.log(f"Pedido {req_id} já se encontra registado")
            return

        # Verifica se existe uma reserva anterior para este pedido
        reservation = self.pending_reservations.get(req_id)

        if reservation is None:
            self.log(
                f"Autorização {req_id} recusada: não existe reserva de capacidade"
            )
            return

        # Confirma que a autorização corresponde à proposta aceite
        if (
            quantity != reservation["accepted_quantity"]
            or payload["origins"] != reservation["origins"]
            or payload["destination"] != reservation["destination"]
        ):
            self.log(
                f"Autorização {req_id} recusada: dados diferentes da proposta aceite"
            )
            return

        # Regista o pedido no transporte
        self.register_order(payload)

        # Cria as paragens de recolha e entrega
        self.register_stops(req_id)

        # Calcula novamente o percurso a partir da localização atual,
        # considerando todas as paragens que ainda estão pendentes
        route = self.calculate_route()

        # Se não existir um percurso possível, remove apenas a nova atribuição
        if route is None:

            del self.current_orders[req_id]

            self.planned_stops = [
                stop for stop in self.planned_stops
                if stop["req_id"] != req_id
            ]

            # Liberta a capacidade que estava reservada
            self.reserved_capacity -= reservation["accepted_quantity"]
            del self.pending_reservations[req_id]

            # Recupera o percurso dos pedidos que já estavam atribuídos
            self.calculate_route()

            self.busy = bool(
                self.current_orders or self.pending_reservations
            )

            self.log(f"Autorização {req_id} cancelada: percurso impossível")
            return

        # A reserva passa a estar associada ao pedido autorizado.
        # Não aumentamos reserved_capacity novamente, porque a capacidade
        # já tinha sido reservada quando o pedido foi aceite.
        del self.pending_reservations[req_id]

        # Atualiza o estado do transporte
        self.busy = True

        self.log(
            f"Autorização {req_id} aceite | "
            f"Quantidade: {quantity} | "
            f"Percurso: {self.current_route}"
        )

    # Avalia se um novo pedido é compatível com a rota atual
    def evaluate_new_request(self, payload):

        # Os drones não recebem novos pedidos durante uma entrega nesta versão
        if self.kind == "drone":
            return False, "Drone já tem uma entrega atribuída"

        # Recolhe as paragens dos pedidos que já estão atribuídos
        existing_stops = [
            stop for stop in self.planned_stops
            if not stop["completed"]
        ]

        # Acrescenta as paragens dos pedidos pendentes de autorização
        for reservation in self.pending_reservations.values():
            existing_stops.extend(reservation["stops"])

        # Calcula a distância do percurso atual
        _, current_distance = self.calculate_route_for_stops(
            existing_stops
        )

        # Verifica se o percurso atual continua a ser possível
        if current_distance == float("inf"):
            return False, "O percurso atual não é possível"

        # Cria as novas paragens de recolha
        new_stops = []

        for origin in payload["origins"]:
            new_stops.append({
                "node": origin,
                "type": "pickup"
            })

        # Adiciona a paragem de entrega no destino
        new_stops.append({
            "node": payload["destination"],
            "type": "delivery"
        })

        # Junta as paragens existentes às novas paragens
        candidate_stops = existing_stops + new_stops

        # Calcula a distância do novo percurso completo
        _, candidate_distance = self.calculate_route_for_stops(
            candidate_stops
        )

        # Verifica se existe um percurso possível
        if candidate_distance == float("inf"):
            return False, "Não existe um percurso possível"

        # Calcula o desvio adicional provocado pelo novo pedido
        detour = candidate_distance - current_distance

        # Verifica se o desvio ultrapassa o limite permitido
        if detour > self.max_route_detour_km:
            return (
                False,
                f"Novo pedido exige um desvio de {detour:.2f} km"
            )

        return True, None

    # Trata os pedidos de transporte recebidos dos pontos de distribuição
    async def handle_transport_request(self, message):

        # Vai buscar os dados do pedido
        payload = message["payload"]
        req_id = payload["req_id"]
        quantity = payload["quantity"]

        accepted_quantity = 0
        status = "rejected"
        reason = None

        # Evita aceitar novamente um pedido já conhecido
        if (
            req_id in self.current_orders
            or req_id in self.pending_reservations
        ):
            reason = "Pedido já recebido anteriormente"

        else:

            # Calcula a capacidade que ainda está disponível
            available_capacity = (
                self.capacity - self.current_load - self.reserved_capacity
            )

            accepted_quantity = min(quantity, available_capacity)

            # Verifica se existe capacidade disponível
            if accepted_quantity <= 0:
                accepted_quantity = 0
                reason = "Sem capacidade disponível"

            # Se o transporte já estiver ocupado, avalia a compatibilidade da rota
            elif self.busy:

                compatible, route_reason = self.evaluate_new_request(payload)

                if not compatible:
                    accepted_quantity = 0
                    reason = route_reason

            # Define o estado da resposta
            if accepted_quantity > 0:

                if accepted_quantity == quantity:
                    status = "accepted"
                else:
                    status = "partially_accepted"
                    reason = (
                        "Capacidade insuficiente para transportar "
                        "a quantidade total"
                    )

                # Cria as paragens previstas para esta reserva
                reservation_stops = []

                for origin in payload["origins"]:
                    reservation_stops.append({
                        "node": origin,
                        "type": "pickup",
                        "req_id": req_id
                    })

                reservation_stops.append({
                    "node": payload["destination"],
                    "type": "delivery",
                    "req_id": req_id
                })

                # Guarda a reserva provisória de capacidade
                self.pending_reservations[req_id] = {
                    "accepted_quantity": accepted_quantity,
                    "origins": list(payload["origins"]),
                    "destination": payload["destination"],
                    "stops": reservation_stops,
                    "created_at": self.world.now(),
                    "attempt": payload.get("attempt"),
                }

                # Reserva imediatamente a capacidade aceite
                self.reserved_capacity += accepted_quantity

                # Atualiza o estado do transporte
                self.busy = True

        remaining_capacity = (
            self.capacity - self.current_load - self.reserved_capacity
        )

        self.log(
            f"Pedido {req_id}: solicitadas {quantity} unidades | "
            f"capacidade restante: {remaining_capacity} | "
            f"quantidade aceite: {accepted_quantity} | "
            f"estado: {status}"
        )

        # Envia a resposta ao ponto de distribuição
        await self.send_message(
            receiver=message["sender"],
            performative="inform",
            message_type="transport_response",
            payload={
                "req_id": req_id,
                "transport_id": str(self.jid),
                "requested_quantity": quantity,
                "accepted_quantity": accepted_quantity,
                "status": status,
                "reason": reason
            }
        )

    # Trata cancelamentos de pedidos que ainda aguardam autorização
    async def handle_cancellation(self, message):

        # Vai buscar os dados do cancelamento
        payload = message["payload"]
        req_id = payload["req_id"]

        # Só é necessário libertar capacidade se o pedido ainda estiver pendente
        reservation = self.pending_reservations.get(req_id)

        if reservation is None:
            self.log(
                f"Cancelamento {req_id} recebido, mas não existe reserva pendente"
            )
            return

        # Liberta a capacidade reservada para este pedido
        self.reserved_capacity -= reservation["accepted_quantity"]

        # Remove a reserva pendente
        del self.pending_reservations[req_id]

        # Atualiza o estado do transporte
        self.busy = bool(
            self.current_orders or self.pending_reservations
        )

        self.log(
            f"Reserva do pedido {req_id} cancelada | "
            f"Capacidade libertada: {reservation['accepted_quantity']}"
        )
