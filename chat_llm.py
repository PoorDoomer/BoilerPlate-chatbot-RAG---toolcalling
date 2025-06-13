from typing import List, Dict
from llm import LLM                      # ta classe de base
from system_prompt import SystemPrompt   # wrapper du prompt système
from tools import make_kpi, make_line, make_table  # helpers dashboard
import os
import logging
import datetime

class ChatLLM(LLM):
    """
    Sur-couche conviviale au moteur LLM de base.
    - Gère l'historique (optionnel) des échanges.
    - Propage automatiquement le prompt système.
    - Garantit que get_completion() reçoit toujours
      une *chaîne* et non une liste Python.
    """

    def __init__(
        self,
        system_prompt: str | None = None,
        history_max: int = 8,            # nombre de tours à remontrer
        max_tool_calls: int = 10,
        debug: bool = False
    ) -> None:
        super().__init__()
        self.history: List[Dict[str, str]] = []   # [ {"role":..., "content":...}, … ]
        self.system_prompt = system_prompt or SystemPrompt().system_prompt
        self.history_max   = history_max
        self.max_tool_calls = max_tool_calls
        self.debug = debug
        
        # Configure logging if debug mode is enabled
        if self.debug:
            self._setup_logging()

    def _setup_logging(self) -> None:
        """Set up logging configuration for debug mode."""
        # Create logs directory if it doesn't exist
        os.makedirs("logs", exist_ok=True)
        
        # Create a timestamped log filename
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = f"logs/chat_llm_debug_{timestamp}.log"
        
        # Configure the logger
        logging.basicConfig(
            filename=log_file,
            level=logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        self.logger = logging.getLogger("ChatLLM")
        self.logger.info(f"Debug logging initialized with system prompt: {self.system_prompt[:50]}...")

    # ─────────────────────────────────────────────
    # Méthodes publiques
    # ─────────────────────────────────────────────
    def chat(self, user_message: str) -> str:
        """
        Ajoute le message utilisateur à l'historique,
        appelle le moteur, stocke la réponse et la renvoie.
        """
        self._push("user", user_message)
        
        if self.debug:
            self.logger.debug(f"User message: {user_message}")

        prompt = self._format_prompt()
        
        if self.debug:
            self.logger.debug(f"Formatted prompt: {prompt}")
            self.logger.debug(f"Calling LLM with system prompt: {self.system_prompt[:50]}...")
        
        response = self.get_completion(
            prompt=prompt,
            system_prompt_override=self.system_prompt,
            max_tool_calls=self.max_tool_calls
        )
        
        if self.debug:
            self.logger.debug(f"LLM response: {response}")

        self._push("assistant", response)
        return response

    def set_system_prompt(self, new_prompt: str) -> None:
        """Modifie dynamiquement le prompt système."""
        if self.debug:
            self.logger.info(f"System prompt changed from: {self.system_prompt[:50]}... to: {new_prompt[:50]}...")
        self.system_prompt = new_prompt

    def reset(self) -> None:
        """Vide complètement l'historique."""
        if self.debug:
            self.logger.info("Chat history reset")
        self.history.clear()
        
    def set_debug(self, debug: bool) -> None:
        """Enable or disable debug mode."""
        if debug and not self.debug:
            self.debug = True
            self._setup_logging()
            self.logger.info("Debug mode enabled")
        elif not debug and self.debug:
            self.logger.info("Debug mode disabled")
            self.debug = False
            
    def create_dashboard_example(self) -> str:
        """
        Exemple d'utilisation des nouveaux outils de dashboard.
        Crée un dashboard simple avec KPIs et graphique.
        
        Returns:
            str: Chemin absolu vers le dashboard généré
        """
        if self.debug:
            self.logger.info("Creating dashboard example")
            
        # Exécuter des requêtes SQL pour obtenir des données
        eaf_total = self.tool_instance.sql_query("SELECT sum(TOTAL_ELEC_EGY) FROM \"02-EAF\"")
        lf_total = self.tool_instance.sql_query("SELECT sum(ELEC_CONS_TOTAL) FROM \"03-LF\"")
        
        # Utiliser les helpers pour créer les composants
        kpi_eaf = make_kpi("Conso EAF totale (kWh)", eaf_total[0][0] if eaf_total and eaf_total[0] else 0)
        kpi_lf = make_kpi("Conso LF totale (kWh)", lf_total[0][0] if lf_total and lf_total[0] else 0)
        kpi_total = make_kpi(
            "Conso totale (kWh)", 
            (eaf_total[0][0] if eaf_total and eaf_total[0] else 0) + 
            (lf_total[0][0] if lf_total and lf_total[0] else 0)
        )
        
        # Assembler le dashboard avec thème et titre personnalisés
        dashboard_path = self.tool_instance.assemble_dashboard(
            components=[kpi_eaf, kpi_lf, kpi_total],
            title="Énergie électrique – synthèse",
            theme="light",
            outfile="energy_dashboard.html"
        )
        
        if self.debug:
            self.logger.info(f"Dashboard created at: {dashboard_path}")
            
        return dashboard_path

    # ─────────────────────────────────────────────
    # Helpers internes
    # ─────────────────────────────────────────────
    def _push(self, role: str, content: str) -> None:
        """Ajoute un message à l'historique en le tronquant si besoin."""
        self.history.append({"role": role, "content": content})
        if len(self.history) > self.history_max * 2:   # user+assistant par tour
            # on garde toujours les derniers échanges
            if self.debug:
                self.logger.debug(f"History truncated from {len(self.history)} to {self.history_max*2} messages")
            self.history = self.history[-self.history_max*2 :]

    def _format_prompt(self) -> str:
        """
        Transforme l'historique en texte brut que l'on passe à get_completion().
        Ici : chaque message sur une ligne `role: content`.
        """
        lines = [f"{msg['role']}: {msg['content']}" for msg in self.history[-self.history_max*2 :]]
        return "\n".join(lines)
