# O fichiero base.py é responsável por definir características que são partilhadas por todos os agentes:
    # init : guarda informações necessárias para o agente funcionar
    # log : mostra mensagens com o tempo simulado e o nome do agente
    # event: regista acontecimentos
    # message handlers: guarda funções responsáveis por tratar cada tipo de mensagem
    # register handler: associa um tipo de mensagem à respetiva função/método

import inspect
from spade.agent import Agent
from spade.message import Message
from spade.behaviour import CyclicBehaviour
from messages import create_message, encode_message, decode_message

class BaseAgent(Agent):
    def __init__(self, jid, password, world, node, directory):
        # Chama o __init__ do Agent do SPADE com jid e password
        super().__init__(jid, password)

        # Guarda as referências necessárias para o funcionamento do agente
        # world     -> o objeto World partilhado
        # node      -> o nó do mapa onde o agente está (ex. "N9")
        # directory -> dicionário com os JIDs de todos os agentes (ver main)
        self.world = world
        self.node = node
        self.directory = directory

        # Dicionário que associa cada tipo de mensagem à função responsável por a processar
        # Cada agente irá registar as suas próprias funções (handlers)
        self.message_handlers = {}

    # Comportamento responsável por ficar continuamente à escuta de mensagens
    class MessageListener(CyclicBehaviour):
        async def run(self):

            # Aguarda uma mensagem durante, no máximo, 1 segundo
            message = await self.receive(timeout=1)

            # Verifica se chegou alguma mensagem
            if message is not None:

                # Tenta descodificar o conteúdo JSON recebido
                try:
                    decoded_message = decode_message(message.body)

                except (ValueError, TypeError) as e:

                    # Regista o erro caso a mensagem seja inválida
                    self.agent.log(f"Mensagem inválida recebida de {message.sender}: {e}")
                    return

                # Tenta processar a mensagem recebida
                try:

                    # Regista quem enviou a mensagem e o seu tipo
                    self.agent.log(
                        f"Mensagem '{decoded_message['type']}' recebida de {decoded_message['sender']}"
                    )

                    # Encaminha a mensagem descodificada para o handler correspondente
                    await self.agent.process_message(decoded_message)

                except Exception as e:

                    # Regista o erro sem terminar o comportamento de receção
                    self.agent.log(f"Erro ao processar mensagem recebida: {e}")
                                
    # Ativa o comportamento responsável por receber mensagens
    def start_message_listener(self):
        self.add_behaviour(self.MessageListener())

    # Inicializa os comportamentos comuns a todos os agentes
    async def setup(self):
        # Ativa o mecanismo de receção de mensagens
        self.start_message_listener()

    # Regista a função que deverá ser executada quando o agente receber determinado tipo de mensagem
    def register_handler(self, message_type, handler):

        # Verifica se o tipo de mensagem é uma string válida
        if not isinstance(message_type, str) or not message_type.strip():
            raise ValueError("O tipo de mensagem tem de ser uma string válida.")

        # Verifica se o handler pode ser chamado
        if not callable(handler):
            raise TypeError("O handler tem de ser uma função.")

        # Associa o tipo de mensagem à respetiva função
        self.message_handlers[message_type] = handler


    # Identifica e executa a função responsável por tratar a mensagem recebida
    async def process_message(self, message):

        # Obtém o tipo da mensagem
        message_type = message["type"]

        # Procura o handler correspondente no dicionário
        handler = self.message_handlers.get(message_type)

        # Verifica se existe um handler registado para este tipo de mensagem
        if handler is None:
            self.log(f"Não existe handler registado para '{message_type}'")
            return

        # Executa o handler responsável por tratar a mensagem
        try:
            result = handler(message)

            # Se o resultado for assíncrono, aguarda a sua conclusão
            if inspect.isawaitable(result):
                await result

        except Exception as e:
            # Regista o erro sem interromper o processamento das próximas mensagens
            self.log(f"Erro ao processar mensagem '{message_type}': {e}")


    # Imprime: minuto simulado (self.world.now(), com 1 casa decimal), nome do agente e o texto
    # O nome do agente obtém-se com str(self.jid)
    def log(self, texto):
        print(f"[{self.world.now():6.1f} min] {self.jid}: {texto}")

    # Regista no EventLog partilhado: minuto simulado, quem foi, o quê
    def event(self, nome, **dados):
        self.world.events.add(self.world.now(), str(self.jid), nome, **dados)
    
    # Envia uma mensagem para outro agente através do SPADE
    async def send_message(self, receiver, performative, message_type, payload):

        # Cria a estrutura da mensagem com o formato definido no messages.py
        message = create_message(
            performative=performative,
            message_type=message_type,
            payload=payload,
            sender=str(self.jid),
            receiver=str(receiver)
        )

        # Converte a mensagem para JSON
        encoded_message = encode_message(message)

        # Cria a mensagem SPADE e define o destinatário
        spade_message = Message(to=str(receiver))

        # Coloca o conteúdo JSON no corpo da mensagem
        spade_message.body = encoded_message

        # Envia efetivamente a mensagem
        # Aguarda que o envio da mensagem seja concluído, sem bloquear a execução das restantes tarefas assíncronas
        await self.send(spade_message)

        # Regista o envio na consola
        self.log(f"Mensagem '{message_type}' enviada para {receiver}")

