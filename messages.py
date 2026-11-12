import json
from uuid import uuid4          # Para gerar os id's das mensagens praticamente únicos
from copy import deepcopy       # Para criar cópias dos dicionáios
from typing import Any, Mapping
from config import TRANSPORT_TYPES
from datetime import datetime, timezone

# Todas as mensagens trocadas entre os agentes seguem uma estrutura comum:
    # Message Id, Ontology, Performative, Type, Payload, Sender, Receiver, Timestamp

#Message Id é um identificador único para cada mensagem, que permite aos agentes distinguir mensagens diferentes. (String)

# Forma de definir um vocabulário comum que os agentes utilizam para compreender a informação que trocam
# Necessário para distinguir mensagens pertencentes ao nosso sistema de mensagens pertencentes a outro contexto
ontology = "natural-disaster-response"     #todas as mensagens pertencem ao domínio da resposta a catástrofes naturais

# Conjunto de valores permitidos para o campo "performative" das mensagens
PERFORMATIVES = {
    "request",
    "agree",
    "refuse",
    "propose",
    "accept_proposal",
    "reject_proposal",
    "inform",
    "failure",
    "cancel",
}

# Tipo de mensagens que podem ser enviadas e recebidas pelos agentes
MESSAGE_TYPES = {
    "resource_request",
    "warehouse_response",
    "stock_reservation",
    "reservation_response",
    "transport_request",
    "transport_response",
    "delivery_authorization",
    "delivery_completed",
    #"delivery_failed",
    "status_update",
    "road_report",
    "cancellation",
    "pickup_completed"
}

#Payload são a informação específica que o agente quer transmitir ao outro agente, dependendo do tipo de mensagem que está a ser enviada. (Dicionário)

#Sender e Receiver são os identificadores dos agentes que estão a enviare a receber a mensagem. (Strings)

#Timestamp indica quando é que a mensagem foi criada/enviada. (String no formato ISO 8601)

# Exceção personalizada para erros de validação de mensagens (tipo mandar pedidos negativos,...)
# Utilizado mais tarde para levantar exceções quando uma mensagem não estiver de acordo com as regras definidas
class MessageValidationError(Exception):
    pass

# Função para verificar se uma mensagem está corretamente construída antes de ser enviada ou depois de ser recebida.
def validate_message(message: Mapping[str, Any]) -> None:
    if not isinstance(message, Mapping):        # Verifica se a mensagem é um objeto do tipo Mapping (como um dicionário)
        raise MessageValidationError(
            "A mensagem tem de ser um objeto com campos."
        )

    #_____MESSAGE_ID_____

    if "message_id" not in message:             # Verifica se a mensagem contem o campo message_id
        raise MessageValidationError(
            "A mensagem não contém o campo 'message_id'."
        )

    if not isinstance(message["message_id"], str) or not message["message_id"].strip():         # Verifica se o valor do campo message_id é texto e não é uma string vazia
        raise MessageValidationError(
            "O campo 'message_id' tem de conter um identificador válido."
        )

    #_____ONTOLOGY_____

    if "ontology" not in message:               # Verifica se a mensagem contem o campo ontology
        raise MessageValidationError(
            "A mensagem não contém o campo 'ontology'."
        )

    if message["ontology"] != ontology:        # Verifica se o valor do campo ontology é igual ao vocabulário definido no início do ficheiro (natural-disaster-response)
        raise MessageValidationError(
            "A mensagem pertence a uma ontology diferente."
        )

    #_____PERFMORMATIVE_____

    if "performative" not in message:           # Verficia se a mensagem contem o campo performative
        raise MessageValidationError(
            "A mensagem não contém o campo 'performative'."
        )

    if message["performative"] not in PERFORMATIVES:        # Verifica se o valor do campo performative está dentro do conjunto de valores permitidos (Lista de cima)
        raise MessageValidationError(
            "A mensagem contém um performative não permitido."
        )

    #_____TYPE_____

    if "type" not in message:                   # Verifica se a mensagem contem o campo type
        raise MessageValidationError(
            "A mensagem não contém o campo 'type'."
        )

    if message["type"] not in MESSAGE_TYPES:    # Verifica se o valor do campo type está dentro do conjunto de valores permitidos (Lista de cima)
        raise MessageValidationError(
            "A mensagem contém um type não permitido."
        )

    #_____PAYLOAD_____

    if "payload" not in message:                # Verifica se a mensagem contem o campo payload
        raise MessageValidationError(
            "A mensagem não contém o campo 'payload'."
        )

    if not isinstance(message["payload"], dict):        # Verifica se o valor do campo payload é um dicionário
        raise MessageValidationError(
            "O campo 'payload' tem de ser um dicionário."
        )

    #_____SENDER_____

    if "sender" not in message:                 # Verifica se a mensagem contem o campo sender (o agente que envia a mensagem)
        raise MessageValidationError(
            "A mensagem não contém o campo 'sender'."
        )

    if not isinstance(message["sender"], str) or not message["sender"].strip():         # Verifica se o valor do campo sender é texto e não é uma string vazia
        raise MessageValidationError(
            "O campo 'sender' tem de conter um identificador válido."
        )

    #_____RECEIVER_____

    if "receiver" not in message:               # Verifica se a mensagem contem o campo receiver
        raise MessageValidationError(
            "A mensagem não contém o campo 'receiver'."
        )

    if not isinstance(message["receiver"], str) or not message["receiver"].strip():     # Verifica se o valor do campo receiver é texto e não é uma string vazia
        raise MessageValidationError(
            "O campo 'receiver' tem de conter um identificador válido."
        )

    #_____TIMESTAMP_____

    if "timestamp" not in message:              # Verifica se a mensagem contem o campo timestamp
        raise MessageValidationError(
              "A mensagem não contém o campo 'timestamp'."
        )

    # Usamos o datetime para verificar se a data e a hora estão num formato válido.
    try:
        timestamp = datetime.fromisoformat(message["timestamp"])        # Tenta interpretar o valor do campo timestamp como uma data e hora no formato ISO 8601
        
        if timestamp.tzinfo is None:            # Verifica se a data e hora não contém informação de fuso horário (tzinfo). Se não tiver, levanta um MessageValidationError
            raise MessageValidationError
    
    except (MessageValidationError, TypeError, ValueError):
        raise MessageValidationError(
            "O campo 'timestamp' tem de ter um formato de data e hora válido."
        )

    validate_payload(message["type"], message["payload"])

# Função para construir uma mensagem com a estrutura correta
def create_message(performative: str, message_type: str, payload: dict, sender: str, receiver: str) -> dict:
    message = {
        "message_id": str(uuid4()),            # Gera um identificador único para a mensagem
        "ontology": ontology,                  # Define a ontology da mensagem
        "performative": performative,          # Define o performative da mensagem
        "type": message_type,                  # Define o type da mensagem
        "payload": deepcopy(payload),                    # Define o payload da mensagem
        "sender": sender,                      # Define o sender da mensagem
        "receiver": receiver,                  # Define o receiver da mensagem
        "timestamp": datetime.now(timezone.utc).isoformat()  # Define o timestamp da mensagem no formato ISO 8601 com fuso horário UTC
    }

    validate_message(message)                 # Valida a mensagem antes de retorná-la

    return message

# Função para transformar o dicionário numa string JSON
def encode_message(message: dict) -> str:
    validate_message(message)                  # Verificar se está corretamente construída

    return json.dumps(message, ensure_ascii=False)

# Função para transformar a string JSON num dicionário
def decode_message(data: str) -> dict:
    try:
        message = json.loads(data)          # Tenta interpretar a string JSON como um dicionário

    except json.JSONDecodeError:
        raise MessageValidationError(
            "A mensagem recebida não contém um JSON válido."
        )

    validate_message(message)                # Verifica se a mensagem está corretamente construída

    return message

# Já analisámos se a mensagem está corretamente construída, mas temos de de ver se as mensagens têm informação coerente como que os agentes precisam.

#PAYLOAD: cada payload tem campos específicos para cada tipo de mensagem:
    # resource_request:
        #Campos: req_id, resource, quantity, priority, destination, attempt
    # warehouse_response:
        #Campos: req_id, attempt, status, accepted_quantity, reason
            #status: Accepted (quando podemos dar tudo), Rejected(quando não podemos dar nada), Partially_Accepted(quando podemos dar só uma parte)
    # stock_reservation:
        # Campos: req_id, attempt, resource, quantity, destination
    # reservation_response:
        # Campos: req_id, attempt, status, reserved_quantity, reason
            # status: reserved (reserva efetuada), rejected (não foi possível reservar)
    # transport_request:
        #Campos: req_id, resource, quantity, origins, destination
    # transport_response:
        #Campos: req_id, transport_id, requested_quantity, accepted_quantity, status, reason   
            # status: Accepted (quando podemos dar tudo), Rejected(quando não podemos dar nada), Partially_Accepted(quando podemos dar só uma parte) 
    # delivery_authorization:
        #Campos: req_id, transport_id, resource, quantity, origins, destination, source_quantities
    # delivery_completed:
        # Campos: delivery_id, req_id, transport_id, resource, delivered_quantity, source_quantities, origins, destination
    # delivery_failed: --NÃO É UTILIZADO PARA JÁ--
        #Campos: req_id, transport_id, resource, quantity, origins, destination, reason
    # status_update:
        #Campos: transport_id, transport_type, status, current_location, capacity, current_load, available_capacity
            # available_capacity = capacity - current_load
            # status: available (nenhum transporte atribuido), occupied (tem trasnportes, mas pode aceitar + pedidos), unavailable (não pode aceitar + pedidos)
            # transport_type: truck, drone
    # road_report:
        #Campos: road_id, status
            # status: clear, blocked
    # cancellation:
        #Campos: req_id, reason
    # pickup_completed:
        # Campos: req_id, transport_id, resource, quantity, origin
    


# Função para validar os dados específicos de um pedido de recursos
def validate_resource_request(payload: Mapping[str, Any]) -> None:
    if not isinstance(payload, Mapping):
        raise MessageValidationError("O payload tem de ser um dicionário.")

    if not payload:
        raise MessageValidationError("O payload não pode estar vazio.")

    required_fields = ["req_id", "resource", "quantity", "priority", "destination", "attempt"]

    for field in required_fields:
        if field not in payload:
            raise MessageValidationError(f"Campo obrigatório em falta: {field}")

    if not isinstance(payload["req_id"], str) or not payload["req_id"].strip():
        raise MessageValidationError("req_id tem de ser uma string não vazia.")

    if not isinstance(payload["resource"], str) or not payload["resource"].strip():
        raise MessageValidationError("resource tem de ser uma string não vazia.")

    if type(payload["quantity"]) is not int or payload["quantity"] <= 0:
        raise MessageValidationError("quantity tem de ser um inteiro positivo.")

    if type(payload["priority"]) is not int or payload["priority"] <= 0:
        raise MessageValidationError("priority tem de ser um inteiro positivo.")

    if not isinstance(payload["destination"], str) or not payload["destination"].strip():
        raise MessageValidationError("destination tem de ser uma string não vazia.")

    if type(payload["attempt"]) is not int or payload["attempt"] <= 0:
        raise MessageValidationError("attempt tem de ser um inteiro positivo.")

# Função para validar os dados específicos de uma resposta do armazém
def validate_warehouse_response(payload: Mapping[str, Any]) -> None:

    if not isinstance(payload, Mapping):
        raise MessageValidationError("O payload tem de ser um dicionário.")

    if not payload:
        raise MessageValidationError("O payload não pode estar vazio.")

    required_fields = ["req_id", "attempt", "status", "accepted_quantity", "reason"]

    for field in required_fields:
        if field not in payload:
            raise MessageValidationError(f"Campo obrigatório em falta: {field}")

    if not isinstance(payload["req_id"], str) or not payload["req_id"].strip():
        raise MessageValidationError("req_id tem de ser uma string não vazia.")

    if type(payload["attempt"]) is not int or payload["attempt"] <= 0:
        raise MessageValidationError("attempt tem de ser um inteiro positivo.")

    if payload["status"] not in {"accepted", "partially_accepted", "rejected"}:
        raise MessageValidationError("status inválido.")

    if type(payload["accepted_quantity"]) is not int or payload["accepted_quantity"] < 0:
        raise MessageValidationError("accepted_quantity tem de ser um inteiro não negativo.")

    if payload["reason"] is not None and not isinstance(payload["reason"], str):
        raise MessageValidationError("reason tem de ser uma string ou None.")

    if payload["status"] == "accepted" and payload["accepted_quantity"] <= 0:
        raise MessageValidationError("Uma resposta accepted tem de aceitar uma quantidade positiva.")

    if payload["status"] == "partially_accepted" and payload["accepted_quantity"] <= 0:
        raise MessageValidationError("Uma resposta partially_accepted tem de aceitar uma quantidade positiva.")

    if payload["status"] == "rejected" and payload["accepted_quantity"] != 0:
        raise MessageValidationError("Uma resposta rejected tem de ter accepted_quantity igual a zero.")

# Função para validar os dados específicos de um pedido de reserva de stock
def validate_stock_reservation(payload: Mapping[str, Any]) -> None:

    if not isinstance(payload, Mapping):
        raise MessageValidationError("O payload tem de ser um dicionário.")

    if not payload:
        raise MessageValidationError("O payload não pode estar vazio.")

    required_fields = ["req_id", "attempt", "resource", "quantity", "destination"]

    for field in required_fields:
        if field not in payload:
            raise MessageValidationError(f"Campo obrigatório em falta: {field}")

    if not isinstance(payload["req_id"], str) or not payload["req_id"].strip():
        raise MessageValidationError("req_id tem de ser uma string não vazia.")

    if type(payload["attempt"]) is not int or payload["attempt"] <= 0:
        raise MessageValidationError("attempt tem de ser um inteiro positivo.")

    if not isinstance(payload["resource"], str) or not payload["resource"].strip():
        raise MessageValidationError("resource tem de ser uma string não vazia.")

    if type(payload["quantity"]) is not int or payload["quantity"] <= 0:
        raise MessageValidationError("quantity tem de ser um inteiro positivo.")

    if not isinstance(payload["destination"], str) or not payload["destination"].strip():
        raise MessageValidationError("destination tem de ser uma string não vazia.")

# Função para validar os dados específicos de uma resposta de reserva de stock
def validate_reservation_response(payload: Mapping[str, Any]) -> None:

    if not isinstance(payload, Mapping):
        raise MessageValidationError("O payload tem de ser um dicionário.")

    if not payload:
        raise MessageValidationError("O payload não pode estar vazio.")

    required_fields = ["req_id", "attempt", "status", "reserved_quantity", "reason"]

    for field in required_fields:
        if field not in payload:
            raise MessageValidationError(f"Campo obrigatório em falta: {field}")

    if not isinstance(payload["req_id"], str) or not payload["req_id"].strip():
        raise MessageValidationError("req_id tem de ser uma string não vazia.")

    if type(payload["attempt"]) is not int or payload["attempt"] <= 0:
        raise MessageValidationError("attempt tem de ser um inteiro positivo.")

    if payload["status"] not in {"reserved", "rejected"}:
        raise MessageValidationError("status inválido.")

    if type(payload["reserved_quantity"]) is not int or payload["reserved_quantity"] < 0:
        raise MessageValidationError("reserved_quantity tem de ser um inteiro não negativo.")

    if payload["reason"] is not None and not isinstance(payload["reason"], str):
        raise MessageValidationError("reason tem de ser uma string ou None.")

    if payload["status"] == "reserved":
        if payload["reserved_quantity"] <= 0:
            raise MessageValidationError("Uma resposta reserved tem de reservar uma quantidade positiva.")

        if payload["reason"] is not None:
            raise MessageValidationError("Uma resposta reserved não deve ter motivo de rejeição.")

    elif payload["status"] == "rejected":
        if payload["reserved_quantity"] != 0:
            raise MessageValidationError("Uma resposta rejected tem de ter reserved_quantity igual a zero.")

        if not isinstance(payload["reason"], str) or not payload["reason"].strip():
            raise MessageValidationError("Uma resposta rejected deve indicar o motivo.")

# Função para validar os dados específicos de um pedido de transporte
def validate_transport_request(payload: Mapping[str, Any]) -> None:

    if not isinstance(payload, Mapping):
        raise MessageValidationError("O payload tem de ser um dicionario.")

    if not payload:
        raise MessageValidationError("O payload nao pode estar vazio.")

    required_fields = [
        "req_id", "resource", "quantity", "origins", "destination"
    ]

    for field in required_fields:
        if field not in payload:
            raise MessageValidationError(f"Campo obrigatorio em falta: {field}")

    if not isinstance(payload["req_id"], str) or not payload["req_id"].strip():
        raise MessageValidationError("req_id tem de ser uma string nao vazia.")

    if not isinstance(payload["resource"], str) or not payload["resource"].strip():
        raise MessageValidationError("resource tem de ser uma string nao vazia.")

    if type(payload["quantity"]) is not int or payload["quantity"] <= 0:
        raise MessageValidationError("quantity tem de ser um inteiro positivo.")

    if not isinstance(payload["origins"], list) or not payload["origins"]:
        raise MessageValidationError("origins tem de ser uma lista nao vazia.")

    for origin in payload["origins"]:
        if not isinstance(origin, str) or not origin.strip():
            raise MessageValidationError("Cada origem tem de ser uma string nao vazia.")

    if not isinstance(payload["destination"], str) or not payload["destination"].strip():
        raise MessageValidationError("destination tem de ser uma string nao vazia.")

# Função para validar os dados específicos de uma resposta de transporte
def validate_transport_response(payload: Mapping[str, Any]) -> None:

    if not isinstance(payload, Mapping):
        raise MessageValidationError("O payload tem de ser um dicionario.")

    if not payload:
        raise MessageValidationError("O payload nao pode estar vazio.")

    required_fields = [
        "req_id",
        "transport_id",
        "requested_quantity",
        "accepted_quantity",
        "status",
        "reason"
    ]

    for field in required_fields:
        if field not in payload:
            raise MessageValidationError(f"Campo obrigatorio em falta: {field}")

    if not isinstance(payload["req_id"], str) or not payload["req_id"].strip():
        raise MessageValidationError("req_id tem de ser uma string nao vazia.")

    if not isinstance(payload["transport_id"], str) or not payload["transport_id"].strip():
        raise MessageValidationError("transport_id tem de ser uma string nao vazia.")

    if type(payload["requested_quantity"]) is not int or payload["requested_quantity"] <= 0:
        raise MessageValidationError("requested_quantity tem de ser um inteiro positivo.")

    if type(payload["accepted_quantity"]) is not int or payload["accepted_quantity"] < 0:
        raise MessageValidationError("accepted_quantity tem de ser um inteiro nao negativo.")

    if payload["accepted_quantity"] > payload["requested_quantity"]:
        raise MessageValidationError("A quantidade aceite nao pode ultrapassar a solicitada.")

    if payload["status"] not in {"accepted", "partially_accepted", "rejected"}:
        raise MessageValidationError("Status invalido.")

    if payload["reason"] is not None:
        if not isinstance(payload["reason"], str) or not payload["reason"].strip():
            raise MessageValidationError("reason tem de ser uma string nao vazia ou None.")

    if payload["status"] == "accepted":
        if payload["accepted_quantity"] != payload["requested_quantity"]:
            raise MessageValidationError("Uma resposta accepted tem de aceitar toda a quantidade.")

        if payload["reason"] is not None:
            raise MessageValidationError("Uma resposta accepted nao deve ter motivo de rejeicao.")

    elif payload["status"] == "partially_accepted":
        if not (0 < payload["accepted_quantity"] < payload["requested_quantity"]):
            raise MessageValidationError("Uma resposta partially_accepted tem de aceitar apenas uma parte.")

        if payload["reason"] is None:
            raise MessageValidationError("Uma resposta partially_accepted deve indicar o motivo.")

    elif payload["status"] == "rejected":
        if payload["accepted_quantity"] != 0:
            raise MessageValidationError("Uma resposta rejected tem de ter accepted_quantity igual a zero.")

        if payload["reason"] is None:
            raise MessageValidationError("Uma resposta rejected deve indicar o motivo.")

# Função para validar os dados específicos de uma autorização de entrega
def validate_delivery_authorization(payload: Mapping[str, Any]) -> None:

    if not isinstance(payload, Mapping):
        raise MessageValidationError("O payload tem de ser um dicionario.")

    if not payload:
        raise MessageValidationError("O payload nao pode estar vazio.")

    required_fields = [
        "req_id",
        "transport_id",
        "resource",
        "quantity",
        "origins",
        "source_quantities",
        "destination"
    ]

    for field in required_fields:
        if field not in payload:
            raise MessageValidationError(f"Campo obrigatorio em falta: {field}")

    if not isinstance(payload["req_id"], str) or not payload["req_id"].strip():
        raise MessageValidationError("req_id tem de ser uma string nao vazia.")

    if not isinstance(payload["transport_id"], str) or not payload["transport_id"].strip():
        raise MessageValidationError("transport_id tem de ser uma string nao vazia.")

    if not isinstance(payload["resource"], str) or not payload["resource"].strip():
        raise MessageValidationError("resource tem de ser uma string nao vazia.")

    if type(payload["quantity"]) is not int or payload["quantity"] <= 0:
        raise MessageValidationError("quantity tem de ser um inteiro positivo.")

    if not isinstance(payload["origins"], list) or not payload["origins"]:
        raise MessageValidationError("origins tem de ser uma lista nao vazia.")

    for origin in payload["origins"]:
        if not isinstance(origin, str) or not origin.strip():
            raise MessageValidationError("Cada origem tem de ser uma string nao vazia.")

    # Verifica se existem origens repetidas
    if len(payload["origins"]) != len(set(payload["origins"])):
        raise MessageValidationError("A lista de origens não pode conter armazéns repetidos.")

    # Verifica se source_quantities é um dicionário
    if not isinstance(payload["source_quantities"], dict) or not payload["source_quantities"]:
        raise MessageValidationError("source_quantities deve ser um dicionário nao vazio.")

    # Verifica se cada armazém tem um identificador válido
    # e uma quantidade inteira positiva
    for warehouse, quantity in payload["source_quantities"].items():
        if not isinstance(warehouse, str) or not warehouse.strip():
            raise MessageValidationError("Identificador de armazém inválido.")

        if type(quantity) is not int or quantity <= 0:
            raise MessageValidationError("Quantidade por armazém inválida.")

    # Confirma que a soma das quantidades corresponde ao total autorizado
    if sum(payload["source_quantities"].values()) != payload["quantity"]:
        raise MessageValidationError("A distribuição por armazém não corresponde à quantidade autorizada.")

    # Confirma que os armazéns indicados correspondem às origens da entrega
    if set(payload["source_quantities"].keys()) != set(payload["origins"]):
        raise MessageValidationError("As origens não correspondem aos armazéns da distribuição.")

    if not isinstance(payload["destination"], str) or not payload["destination"].strip():
        raise MessageValidationError("destination tem de ser uma string nao vazia.")


# Função para validar os dados específicos de uma entrega concluída
def validate_delivery_completed(payload: Mapping[str, Any]) -> None:

    if not isinstance(payload, Mapping):
        raise MessageValidationError("O payload tem de ser um dicionario.")

    if not payload:
        raise MessageValidationError("O payload nao pode estar vazio.")

    # Define os campos obrigatórios de uma entrega concluída
    required_fields = [
        "delivery_id",
        "req_id",
        "transport_id",
        "resource",
        "delivered_quantity",
        "source_quantities",
        "origins",
        "destination"
    ]

    for field in required_fields:
        if field not in payload:
            raise MessageValidationError(f"Campo obrigatorio em falta: {field}")

    if not isinstance(payload["req_id"], str) or not payload["req_id"].strip():
        raise MessageValidationError("req_id tem de ser uma string nao vazia.")

    if not isinstance(payload["delivery_id"], str) or not payload["delivery_id"].strip():
        raise MessageValidationError("delivery_id tem de ser uma string não vazia.")

    if not isinstance(payload["transport_id"], str) or not payload["transport_id"].strip():
        raise MessageValidationError("transport_id tem de ser uma string nao vazia.")

    if not isinstance(payload["resource"], str) or not payload["resource"].strip():
        raise MessageValidationError("resource tem de ser uma string nao vazia.")

    if type(payload["delivered_quantity"]) is not int or payload["delivered_quantity"] <= 0:
        raise MessageValidationError("delivered_quantity tem de ser um inteiro positivo.")

    # Verifica se source_quantities é um dicionário
    if not isinstance(payload["source_quantities"], dict):
        raise MessageValidationError("source_quantities deve ser um dicionário")

    # Verifica se cada armazém tem um identificador válido
    # e uma quantidade inteira positiva
    for warehouse, quantity in payload["source_quantities"].items():
        if not isinstance(warehouse, str) or not warehouse.strip():
            raise MessageValidationError("Identificador de armazém inválido")

        if type(quantity) is not int or quantity <= 0:
            raise MessageValidationError("Quantidade por armazém inválida")

    # Confirma que a soma das quantidades corresponde ao total entregue
    if sum(payload["source_quantities"].values()) != payload["delivered_quantity"]:
        raise MessageValidationError("A distribuição por armazém não corresponde ao total entregue")

    if not isinstance(payload["origins"], list) or not payload["origins"]:
        raise MessageValidationError("origins tem de ser uma lista nao vazia.")
    
    for origin in payload["origins"]:
        if not isinstance(origin, str) or not origin.strip():
            raise MessageValidationError("Cada origem tem de ser uma string nao vazia.")

    # Verifica se existem origens repetidas
    if len(payload["origins"]) != len(set(payload["origins"])):
        raise MessageValidationError("A lista de origens não pode conter armazéns repetidos.")
    
    # Confirma que todos os armazéns indicados estão nas origens da entrega
    if set(payload["source_quantities"].keys()) != set(payload["origins"]):
        raise MessageValidationError("As origens não correspondem aos armazéns da distribuição")

    if not isinstance(payload["destination"], str) or not payload["destination"].strip():
        raise MessageValidationError("destination tem de ser uma string nao vazia.")

# Função para validar os dados específicos de atualizações de estado dos transportes
def validate_status_update(payload: Mapping[str, Any]) -> None:

    if not isinstance(payload, Mapping):
        raise MessageValidationError("O payload tem de ser um dicionario.")

    if not payload:
        raise MessageValidationError("O payload nao pode estar vazio.")

    required_fields = [
        "transport_id",
        "transport_type",
        "status",
        "current_location",
        "capacity",
        "current_load",
        "available_capacity"
    ]

    for field in required_fields:
        if field not in payload:
            raise MessageValidationError(f"Campo obrigatorio em falta: {field}")

    if not isinstance(payload["transport_id"], str) or not payload["transport_id"].strip():
        raise MessageValidationError("transport_id tem de ser uma string nao vazia.")

    # Verifica se o tipo de transporte está definido no config
    if not isinstance(payload["transport_type"], str) or payload["transport_type"] not in TRANSPORT_TYPES:
        raise MessageValidationError("transport_type inválido.")

    # Vai buscar a capacidade definida no config
    expected_capacity = TRANSPORT_TYPES[payload["transport_type"]]["capacity"]

    if payload["status"] not in {"available", "occupied", "unavailable"}:
        raise MessageValidationError("Status invalido.")

    if not isinstance(payload["current_location"], str) or not payload["current_location"].strip():
        raise MessageValidationError("current_location tem de ser uma string nao vazia.")

    if type(payload["capacity"]) is not int:
        raise MessageValidationError("capacity tem de ser um inteiro.")

    if payload["capacity"] != expected_capacity:
        raise MessageValidationError(
            f"A capacidade de {payload['transport_type']} tem de ser "
            f"{expected_capacity}."
        )

    if type(payload["current_load"]) is not int or payload["current_load"] < 0:
        raise MessageValidationError("current_load tem de ser um inteiro nao negativo.")

    if payload["current_load"] > payload["capacity"]:
        raise MessageValidationError("current_load nao pode ultrapassar a capacidade.")

    if type(payload["available_capacity"]) is not int or payload["available_capacity"] < 0:
        raise MessageValidationError("available_capacity tem de ser um inteiro nao negativo.")

    expected_available = payload["capacity"] - payload["current_load"]

    if payload["available_capacity"] != expected_available:
        raise MessageValidationError(
            "available_capacity tem de ser igual a capacity - current_load."
        )

# Função para validar os dados específicos de relatórios de estradas
def validate_road_report(payload: Mapping[str, Any]) -> None:

    if not isinstance(payload, Mapping):
        raise MessageValidationError("O payload tem de ser um dicionario.")

    if not payload:
        raise MessageValidationError("O payload nao pode estar vazio.")

    required_fields = ["road_id", "status"]

    for field in required_fields:
        if field not in payload:
            raise MessageValidationError(f"Campo obrigatorio em falta: {field}")

    if not isinstance(payload["road_id"], str) or not payload["road_id"].strip():
        raise MessageValidationError("road_id tem de ser uma string nao vazia.")

    if payload["status"] not in {"clear", "blocked"}:
        raise MessageValidationError("O status da estrada tem de ser clear ou blocked.")

# Função para validar os dados específicos de cancelamentos
def validate_cancellation(payload: Mapping[str, Any]) -> None:

    if not isinstance(payload, Mapping):
        raise MessageValidationError("O payload tem de ser um dicionario.")

    if not payload:
        raise MessageValidationError("O payload nao pode estar vazio.")

    required_fields = ["req_id", "reason"]

    for field in required_fields:
        if field not in payload:
            raise MessageValidationError(f"Campo obrigatorio em falta: {field}")

    if not isinstance(payload["req_id"], str) or not payload["req_id"].strip():
        raise MessageValidationError("req_id tem de ser uma string nao vazia.")

    if not isinstance(payload["reason"], str) or not payload["reason"].strip():
        raise MessageValidationError("reason tem de ser uma string nao vazia.")

# Função para validar o payload de acordo com o tipo de mensagem
def validate_payload(message_type: str, payload: Mapping[str, Any]) -> None:

    validators = {
        "resource_request": validate_resource_request,
        "warehouse_response": validate_warehouse_response,
        "stock_reservation": validate_stock_reservation,
        "reservation_response": validate_reservation_response,
        "transport_request": validate_transport_request,
        "transport_response": validate_transport_response,
        "delivery_authorization": validate_delivery_authorization,
        "delivery_completed": validate_delivery_completed,
        "status_update": validate_status_update,
        "road_report": validate_road_report,
        "cancellation": validate_cancellation,
        "pickup_completed": validate_pickup_completed
    }

    validator = validators.get(message_type)

    if validator is None:
        raise MessageValidationError(
            f"Nao existe validacao para o tipo de mensagem: {message_type}"
        )

    validator(payload)

# Função para validar os dados específicos de uma recolha concluída
def validate_pickup_completed(payload: Mapping[str, Any]) -> None:

    if not isinstance(payload, Mapping):
        raise MessageValidationError("O payload tem de ser um dicionario.")

    if not payload:
        raise MessageValidationError("O payload nao pode estar vazio.")

    required_fields = [
        "req_id",
        "attempt",
        "transport_id",
        "resource",
        "quantity",
        "origin"
    ]

    for field in required_fields:
        if field not in payload:
            raise MessageValidationError(f"Campo obrigatorio em falta: {field}")

    for field in ["req_id", "transport_id", "resource", "origin"]:
        if not isinstance(payload[field], str) or not payload[field].strip():
            raise MessageValidationError(f"{field} tem de ser uma string nao vazia.")

    if type(payload["attempt"]) is not int or payload["attempt"] <= 0:
        raise MessageValidationError("attempt tem de ser um inteiro positivo.")

    if type(payload["quantity"]) is not int or payload["quantity"] <= 0:
        raise MessageValidationError("quantity tem de ser um inteiro positivo.")