from spade.behaviour import OneShotBehaviour
from agents.base import BaseAgent

class ScoutAgent(BaseAgent):

    class Hello(OneShotBehaviour):
        async def run(self):
            self.agent.log("scout pronto")
            self.agent.event("agent_ready", role="scout")
            
    async def setup(self):
        # Inicializa os comportamentos comuns do BaseAgent
        await super().setup()

        # Adiciona o comportamento específico do Scout
        self.add_behaviour(self.Hello())