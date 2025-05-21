import os
import json
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton

STATS_FILE = "usage_stats.json"


class StatisticsApp(QDialog):
    def __init__(self, font_size=12, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Statistiques d'utilisation")
        self.setStyleSheet(f"* {{ font-size: {font_size}px; }}")
        self.layout = QVBoxLayout(self)
        self.setLayout(self.layout)
        self.load_and_display_stats()
        close_btn = QPushButton("Fermer")
        close_btn.clicked.connect(self.close)
        self.layout.addWidget(close_btn)

    def load_and_display_stats(self):
        if not os.path.exists(STATS_FILE):
            self.layout.addWidget(QLabel("Aucune statistique disponible."))
            return
        with open(STATS_FILE, "r", encoding="utf-8") as f:
            stats = json.load(f)
        total_retrieval = stats.get("retrieval_count", 0)
        total_review = stats.get("review_count", 0)
        total_correct = stats.get("correct_count", 0)
        total_answered = stats.get("answered_count", 0)
        accuracy = (
            f"{(100 * total_correct / total_answered):.1f}%"
            if total_answered
            else "N/A"
        )
        last_dates = stats.get("dates", [])
        self.layout.addWidget(QLabel(f"Éléments parcourus : {total_retrieval}"))
        self.layout.addWidget(QLabel(f"Éléments vus en mode revue : {total_review}"))
        self.layout.addWidget(QLabel(f"Taux d'exactitude : {accuracy}"))
        if last_dates:
            self.layout.addWidget(
                QLabel(f"Dernières sessions : {', '.join(last_dates[-5:])}")
            )
