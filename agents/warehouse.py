from spade.behaviour import OneShotBehaviour
from agents.base import BaseAgent

class WarehouseAgent(BaseAgent):
    def __init__(self, jid, password, world, node, directory):
        # chama o __init__ da BaseAgent com os mesmos 5 argumentos (super().__init__)
        # cria self.known_blocked como um set vazio (o mapa próprio do armazém)

        super().__init__(jid, password, world, node, directory)
        self.known_blocked = set()
        self.reservations = {}

        # Guarda os identificadores das entregas já processadas
        self.completed_deliveries = set()
        
        # Guarda as recolhas já processadas para evitar descontos duplicados
        self.completed_pickups = set()

    def known_open_edges(self):
        # devolve as estradas de self.world.edges que NÃO estão em self.known_blocked
        # (é igual ao open_edges do world, mas com known_blocked)

        abertas = {}
        for estrada, km in self.world.edges.items():
            if estrada not in self.known_blocked:
                abertas[estrada] = km
        return abertas

    class Hello(OneShotBehaviour):
        async def run(self):
            node = self.agent.node
            stock = self.agent.world.stock[node]
            self.agent.log(f"pronto em {node} | stock: {stock}")
            self.agent.event("agent_ready", role="warehouse", node=node, stock=stock)
    
    async def setup(self):
        # Inicializa os comportamentos comuns do BaseAgent
        await super().setup()

        # Regista os handlers das mensagens que o Warehouse sabe tratar
        self.register_handler("resource_request", self.handle_resource_request)
        self.register_handler("stock_reservation", self.handle_stock_reservation)
        self.register_handler("cancellation", self.handle_cancellation)
        self.register_handler("pickup_completed", self.handle_pickup_completed)
        
        # Adiciona o comportamento específico do Warehouse
        self.add_behaviour(self.Hello())
    
    # Trata os pedidos de recursos recebidos dos pontos de distribuição
    async def handle_resource_request(self, message):

        # Vai buscar os dados do pedido
        payload = message["payload"]
        req_id = payload["req_id"]
        resource = payload["resource"]
        quantity = payload["quantity"]
        destination = payload["destination"]
        attempt = payload["attempt"]

        # Consulta o stock total existente no armazém
        stock = self.world.stock[self.node].get(resource, 0)

        # Calcula a quantidade de stock que já está reservada
        # para outros pedidos deste mesmo recurso
        reserved_quantity = sum(
            reservation["quantity"]
            for reservation in self.reservations.values()
            if reservation["resource"] == resource
        )

        # Calcula o stock que continua disponível,
        # descontando as quantidades já reservadas
        available_stock = max(0, stock - reserved_quantity)

        # Calcula a quantidade que o armazém consegue disponibilizar
        # sem comprometer reservas que já foram efetuadas
        accepted_quantity = min(available_stock, quantity)

        # Define o estado da resposta
        if accepted_quantity == quantity:
            status = "accepted"
            reason = "Stock suficiente"
        elif accepted_quantity > 0:
            status = "partially_accepted"
            reason = "Stock insuficiente para satisfazer o pedido completo"
        else:
            status = "rejected"
            reason = "Sem stock disponível"

        self.log(
            f"Pedido {req_id}: {quantity} unidades de {resource} "
            f"para {destination} | stock disponível: {available_stock} "
            f"| contribuição possível: {accepted_quantity}"
        )

        # Envia a resposta ao ponto de distribuição
        await self.send_message(
            receiver=message["sender"],
            performative="inform",
            message_type="warehouse_response",
            payload={
                "req_id": req_id,
                "attempt": attempt,
                "status": status,
                "accepted_quantity": accepted_quantity,
                "reason": reason
            }
        )

    # Trata os pedidos de reserva de stock recebidos dos pontos de distribuição
    async def handle_stock_reservation(self, message):

        # Vai buscar os dados do pedido
        payload = message["payload"]
        req_id = payload["req_id"]
        attempt = payload["attempt"]
        resource = payload["resource"]
        quantity = payload["quantity"]
        destination = payload["destination"]

        # Identifica a reserva através do pedido e da tentativa
        reservation_id = (req_id, attempt)

        # Verifica se esta reserva já foi efetuada
        if reservation_id in self.reservations:
            reservation = self.reservations[reservation_id]

            # Verifica se o novo pedido corresponde à reserva original
            if (
                reservation["resource"] == resource
                and reservation["quantity"] == quantity
            ):

                # Se os dados forem iguais, devolve a confirmação anterior
                self.log(
                    f"Reserva duplicada identificada para o pedido {req_id}. "
                    f"A devolver a confirmação anterior."
                )

                status = "reserved"
                reserved_quantity = reservation["quantity"]
                reason = None

            else:
                # Se os dados forem diferentes, rejeita o novo pedido
                self.log(
                    f"Reserva rejeitada para o pedido {req_id}: "
                    f"já existe uma reserva com dados diferentes."
                )

                status = "rejected"
                reserved_quantity = 0
                reason = "Já existe uma reserva com dados diferentes para este pedido"

            # Envia a resposta ao ponto de distribuição
            await self.send_message(
                receiver=message["sender"],
                performative="inform",
                message_type="reservation_response",
                payload={
                    "req_id": req_id,
                    "attempt": attempt,
                    "status": status,
                    "reserved_quantity": reserved_quantity,
                    "reason": reason
                }
            )
            return

        # Consulta o stock total e calcula o stock já reservado
        stock = self.world.stock[self.node].get(resource, 0)

        reserved_quantity = sum(
            reservation["quantity"]
            for reservation in self.reservations.values()
            if reservation["resource"] == resource
        )

        # Calcula o stock que ainda está disponível para reserva
        available_stock = max(0, stock - reserved_quantity)

        # Verifica se existe stock suficiente para a reserva
        if available_stock >= quantity:

            # Guarda a reserva sem alterar o stock físico
            self.reservations[reservation_id] = {
                "resource": resource,
                "quantity": quantity
            }

            status = "reserved"
            reserved_quantity = quantity
            reason = None

            self.log(
                f"Reserva efetuada para o pedido {req_id}: "
                f"{quantity} unidades de {resource}"
            )

        else:
            status = "rejected"
            reserved_quantity = 0
            reason = "Stock disponível insuficiente para efetuar a reserva"

            self.log(
                f"Reserva rejeitada para o pedido {req_id}: "
                f"solicitadas {quantity}, disponíveis {available_stock}"
            )

        # Envia a resposta ao ponto de distribuição
        await self.send_message(
            receiver=message["sender"],
            performative="inform",
            message_type="reservation_response",
            payload={
                "req_id": req_id,
                "attempt": attempt,
                "status": status,
                "reserved_quantity": reserved_quantity,
                "reason": reason
            }
        )

    # Trata os pedidos de cancelamento recebidos dos pontos de distribuição
    async def handle_cancellation(self, message):

        # Vai buscar os dados do cancelamento
        payload = message["payload"]

        req_id = payload["req_id"]
        reason = payload["reason"]

        # Procura todas as reservas associadas a este pedido
        reservations_to_remove = [
            reservation_id
            for reservation_id in self.reservations
            if reservation_id[0] == req_id
        ]

        # Verifica se existem reservas para libertar
        if reservations_to_remove:

            # Percorre todas as reservas encontradas
            for reservation_id in reservations_to_remove:

                # Remove a reserva do registo do armazém
                reservation = self.reservations.pop(reservation_id)

                self.log(
                    f"Reserva libertada para o pedido {req_id}: "
                    f"{reservation['quantity']} unidades de "
                    f"{reservation['resource']}"
                )

            self.log(
                f"Pedido {req_id} cancelado. Motivo: {reason}"
            )

        else:
            # Informa que não foi encontrada nenhuma reserva para este pedido
            self.log(
                f"Cancelamento do pedido {req_id} recebido, "
                f"mas não existem reservas associadas. Motivo: {reason}"
            )

    
    # Trata as confirmações de recolha recebidas dos transportes
    async def handle_pickup_completed(self, message):

        # Vai buscar os dados da recolha
        payload = message["payload"]

        req_id = payload["req_id"]
        transport_id = payload["transport_id"]
        resource = payload["resource"]
        quantity = payload["quantity"]
        origin = payload["origin"]
        attempt = payload.get("attempt")
        pickup_id = (req_id, transport_id, origin, attempt)      # Cria um identificador único para esta recolha

        # Confirma que a recolha pertence a este armazém
        if origin != self.node:
            self.log(
                f"Recolha rejeitada para o pedido {req_id}: "
                f"armazém de origem incorreto."
            )
            return

        # Verifica se esta recolha já foi processada
        if pickup_id in self.completed_pickups:
            self.log(
                f"Recolha duplicada ignorada para o pedido {req_id}, "
                f"transporte {transport_id}."
            )
            return
        
        # Procura a reserva correspondente ao pedido
        reservation_ids = [
            reservation_id
            for reservation_id in self.reservations
            if reservation_id[0] == req_id
        ]

        # Verifica se existe uma reserva associada ao pedido
        if not reservation_ids:
            self.log(
                f"Recolha do pedido {req_id} recebida, "
                f"mas não existe nenhuma reserva neste armazém."
            )
            return

        # Procura a reserva correspondente ao recurso
        reservation_id = next(
            (
                rid for rid in reservation_ids
                if self.reservations[rid]["resource"] == resource
                and (attempt is None or rid[1] == attempt)
            ),
            None
        )

        if reservation_id is None:
            self.log(
                f"Recolha do pedido {req_id} rejeitada: "
                f"não existe reserva para {resource}."
            )
            return

        # Consulta os dados da reserva
        reservation = self.reservations[reservation_id]

        # Confirma que a quantidade recolhida não ultrapassa a reserva
        if quantity > reservation["quantity"]:
            self.log(
                f"Recolha rejeitada para o pedido {req_id}: "
                f"quantidade superior à reservada."
            )
            return

        # Confirma que existe stock físico suficiente
        if self.world.stock[self.node].get(resource, 0) < quantity:
            self.log(
                f"Recolha rejeitada para o pedido {req_id}: "
                f"stock físico insuficiente."
            )
            return

        # Atualiza o stock físico do armazém
        self.world.stock[self.node][resource] -= quantity

        # Liberta a quantidade correspondente da reserva
        if quantity == reservation["quantity"]:
            del self.reservations[reservation_id]
        else:
            reservation["quantity"] -= quantity

        # Regista a recolha para evitar processá-la novamente
        self.completed_pickups.add(pickup_id)

        self.log(
            f"Recolha concluída para o pedido {req_id}: "
            f"{quantity} unidades de {resource} "
            f"recolhidas por {transport_id}. "
            f"Stock restante: {self.world.stock[self.node][resource]}"
        )

        # Regista o acontecimento no histórico da simulação
        self.event(
            "pickup_completed",
            req_id=req_id,
            transport_id=transport_id,
            resource=resource,
            quantity=quantity,
            origin=origin,
            attempt=attempt
        )
