from spade.behaviour import OneShotBehaviour
from agents.base import BaseAgent

class DPAgent(BaseAgent):

    class Hello(OneShotBehaviour):
        async def run(self):
            self.agent.log(f"ponto de distribuição pronto em {self.agent.node}")
            self.agent.event("agent_ready", role="dp", node=self.agent.node)

    async def setup(self):
        # Inicializa os comportamentos comuns do BaseAgent
        await super().setup()

        # Adiciona o comportamento específico do DP
        self.add_behaviour(self.Hello())