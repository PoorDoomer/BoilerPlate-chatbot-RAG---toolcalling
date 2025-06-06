      
from typing import Optional
import datetime

class Tools:
    def __init__(self):
        pass

    def calculate_taux_disponibilite(self, temps_requis: float, somme_des_arrets: float) -> float:
        """
        Calculates the Taux de Disponibilité (TD) in percentage.

        Args:
            temps_requis (float): Temps Requis in hours.
            somme_des_arrets (float): Somme des arrêts in hours.

        Returns:
            float: Taux de Disponibilité (TD) in percentage.
        """
        if temps_requis == 0:
            return 0.0  # Avoid division by zero
        return ((temps_requis - somme_des_arrets) / temps_requis) * 100

    def calculate_temps_requis_pourcentage(self, temps_ouverture: float, somme_des_arrets_programmes: float) -> float:
        """
        Calculates the Temps Requis (%) based on Temps d'ouverture and Somme des arrêts programmés.

        Args:
            temps_ouverture (float): Temps d'ouverture in hours.
            somme_des_arrets_programmes (float): Somme des arrêts programmés in hours.

        Returns:
            float: Temps Requis (%)
        """
        if temps_ouverture == 0:
            return 0.0  # Avoid division by zero
        return ((temps_ouverture - somme_des_arrets_programmes) / temps_ouverture) * 100

    def calculate_mtbf(self, temps_requis: float, somme_des_arrets: float, nombre_des_arrets: int) -> float:
        """
        Calculates the Mean Time Between Failures (MTBF).

        Args:
            temps_requis (float): Temps Requis in hours.
            somme_des_arrets (float): Somme des arrêts in hours.
            nombre_des_arrets (int): Nombre d'arrêts.

        Returns:
            float: Mean Time Between Failures (MTBF) in hours.
        """
        return (temps_requis - somme_des_arrets) / (nombre_des_arrets + 1)

    def calculate_mttr(self, somme_des_arrets: float, nombre_des_arrets: int) -> float:
        """
        Calculates the Mean Time To Repair (MTTR).

        Args:
            somme_des_arrets (float): Somme des arrêts in hours.
            nombre_des_arrets (int): Nombre d'arrêts.

        Returns:
            float: Mean Time To Repair (MTTR) in hours.
        """
        if nombre_des_arrets == 0:
            return 0.0
        return somme_des_arrets / nombre_des_arrets

    def calculate_rendement(self, poids_brames: float, poids_ferrailles: float) -> float:
        """
        Calculates the Rendement (%) based on Poids Brames and Poids Ferrailles.

        Args:
            poids_brames (float): Poids Brames in kilograms.
            poids_ferrailles (float): Poids Ferrailles in kilograms.

        Returns:
            float: Rendement (%)
        """
        if poids_ferrailles == 0:
            return 0.0  # Avoid division by zero
        return (poids_brames / poids_ferrailles) * 100

    def calculate_conso_elec(self, cons_elec_eaf: float, cons_elec_lf: float) -> float:
        """
        Calculates the total Consommation Electrique (Conso Elec) by summing Cons Elec (EAF) and Cons Elec (LF).

        Args:
            cons_elec_eaf (float): Consommation Electrique (EAF) in kWh.
            cons_elec_lf (float): Consommation Electrique (LF) in kWh.

        Returns:
            float: Total Consommation Electrique in kWh.
        """
        return cons_elec_eaf + cons_elec_lf

    def calculate_temps_requis(self, temps_ouverture: float, somme_des_arrets_programmes: float) -> float:
        """
        Calculates Temps Requis.

        Args:
            temps_ouverture (float): Temps d'ouverture in hours.
            somme_des_arrets_programmes (float): Somme des arrêts programmés in hours.

        Returns:
            float: Temps Requis in hours.
        """
        return temps_ouverture - somme_des_arrets_programmes

    def convert_to_datetime(self, date_string: str) -> Optional[datetime.datetime]:
        """
        Converts a date string to a datetime object.

        Args:
            date_string (str): The date string to convert.

        Returns:
            Optional[datetime.datetime]: The datetime object, or None if the conversion fails.
        """
        try:
            return datetime.datetime.fromisoformat(date_string.rstrip('Z'))
        except ValueError:
            try:
                return datetime.datetime.strptime(date_string, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                return None


    def calculate_duration_hours(self, start_time: str, end_time: str) -> Optional[float]:
        """
        Calculates the duration in hours between two datetime strings.

        Args:
            start_time (str): The start time in ISO format (YYYY-MM-DD HH:MM:SS).
            end_time (str): The end time in ISO format (YYYY-MM-DD HH:MM:SS).

        Returns:
            Optional[float]: The duration in hours, or None if the conversion fails.
        """
        start_datetime = self.convert_to_datetime(start_time)
        end_datetime = self.convert_to_datetime(end_time)

        if start_datetime is None or end_datetime is None:
            return None

        duration = end_datetime - start_datetime
        return duration.total_seconds() / 3600

    